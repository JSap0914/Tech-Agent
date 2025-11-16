"""
Workflow execution API routes for Tech Spec Agent.

Provides endpoints for workflow control:
- Execute workflow
- Resume from checkpoint
- Pause workflow
- Cancel workflow
- Get workflow state
"""

import asyncio
from typing import Dict, Optional
from uuid import UUID
from fastapi import APIRouter, HTTPException, Depends, status, Path, Body, BackgroundTasks
from pydantic import BaseModel, Field
import structlog

from src.api.auth import get_current_user, User
from src.api.rate_limit import standard_rate_limit, strict_rate_limit
from src.api.workflow_executor import (
    execute_workflow,
    resume_workflow,
    pause_workflow,
    cancel_workflow,
    get_workflow_state
)
from src.database.connection import db_manager, get_db_connection
from src.database.models import TechSpecSession
from sqlalchemy import select

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/tech-spec", tags=["Workflow Control"])


# ============= Request/Response Schemas =============

class ExecuteWorkflowRequest(BaseModel):
    """Request to execute workflow."""

    google_ai_studio_code_path: Optional[str] = Field(
        None,
        description="Path to Google AI Studio generated code ZIP file"
    )
    force_restart: bool = Field(
        False,
        description="Force restart if workflow already in progress"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "google_ai_studio_code_path": "/uploads/design-job-123/ai-studio-code.zip",
                "force_restart": False
            }
        }


class ExecuteWorkflowResponse(BaseModel):
    """Response after starting workflow execution."""

    session_id: UUID = Field(..., description="Session ID")
    status: str = Field(..., description="Workflow status")
    message: str = Field(..., description="Status message")
    websocket_url: str = Field(..., description="WebSocket URL for live updates")

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "status": "in_progress",
                "message": "Workflow execution started successfully",
                "websocket_url": "wss://anyon.com/tech-spec/a1b2c3d4-e5f6-7890-abcd-ef1234567890"
            }
        }


class ResumeWorkflowRequest(BaseModel):
    """Request to resume paused workflow."""

    user_decision: Optional[Dict] = Field(
        None,
        description="User technology decision (if resuming from decision point)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "user_decision": {
                    "category": "authentication",
                    "selected_technology": "NextAuth.js",
                    "reasoning": "Best fit for Next.js project"
                }
            }
        }


class ResumeWorkflowResponse(BaseModel):
    """Response after resuming workflow."""

    session_id: UUID = Field(..., description="Session ID")
    status: str = Field(..., description="Workflow status")
    message: str = Field(..., description="Status message")

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "status": "in_progress",
                "message": "Workflow resumed successfully"
            }
        }


class WorkflowStateResponse(BaseModel):
    """Current workflow state from checkpoint."""

    session_id: UUID = Field(..., description="Session ID")
    status: str = Field(..., description="Workflow status")
    current_stage: str = Field(..., description="Current stage")
    progress_percentage: float = Field(..., ge=0.0, le=100.0, description="Progress")
    next_node: Optional[str] = Field(None, description="Next node to execute")
    checkpoint_exists: bool = Field(..., description="Whether checkpoint exists")

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "status": "paused",
                "current_stage": "waiting_user_decision",
                "progress_percentage": 45.0,
                "next_node": "validate_decision",
                "checkpoint_exists": True
            }
        }


# ============= Endpoints =============

@router.post(
    "/sessions/{session_id}/execute",
    response_model=ExecuteWorkflowResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Execute Workflow",
    description="Start execution of the Tech Spec workflow",
    responses={
        202: {"description": "Workflow execution started"},
        400: {"description": "Invalid request or workflow already running"},
        401: {"description": "Unauthorized"},
        404: {"description": "Session not found"},
        429: {"description": "Rate limit exceeded"}
    },
    dependencies=[Depends(standard_rate_limit)]
)
async def execute_workflow_endpoint(
    session_id: UUID = Path(..., description="Tech Spec session ID"),
    request: ExecuteWorkflowRequest = Body(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    current_user: User = Depends(get_current_user)
):
    """
    Start workflow execution in background.

    This endpoint:
    1. Validates session exists and is in valid state
    2. Loads PRD and design documents
    3. Starts workflow execution in background task
    4. Returns immediately with 202 Accepted
    5. Client receives progress via WebSocket

    Workflow execution happens asynchronously. Monitor progress via:
    - WebSocket connection (real-time)
    - GET /sessions/{session_id}/status (polling)
    """
    logger.info(
        "Execute workflow request",
        session_id=str(session_id),
        user_id=str(current_user.user_id)
    )

    async with db_manager.get_async_session() as db_session:
        # Fetch session
        query = select(TechSpecSession).where(TechSpecSession.id == session_id)
        result = await db_session.execute(query)
        tech_session = result.scalar_one_or_none()

        if not tech_session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found"
            )

        # Check if workflow already running
        if tech_session.status == "in_progress" and not request.force_restart:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Workflow already in progress. Use force_restart=true to restart."
            )

        # Load PRD and design documents
        prd_content, design_docs = await _load_session_inputs(tech_session)

        # Start workflow in background
        background_tasks.add_task(
            execute_workflow,
            session_id=str(session_id),
            project_id=str(tech_session.project_id),
            user_id=str(tech_session.user_id),
            design_job_id=str(tech_session.design_job_id),
            prd_content=prd_content,
            design_docs=design_docs,
            google_ai_studio_code_path=request.google_ai_studio_code_path
        )

        logger.info(
            "Workflow execution started in background",
            session_id=str(session_id)
        )

        return ExecuteWorkflowResponse(
            session_id=session_id,
            status="in_progress",
            message="Workflow execution started successfully. Connect to WebSocket for real-time updates.",
            websocket_url=tech_session.websocket_url
        )


@router.post(
    "/sessions/{session_id}/resume",
    response_model=ResumeWorkflowResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Resume Workflow",
    description="Resume paused workflow from checkpoint",
    responses={
        202: {"description": "Workflow resumed"},
        400: {"description": "Invalid request or session not paused"},
        401: {"description": "Unauthorized"},
        404: {"description": "Session or checkpoint not found"},
        429: {"description": "Rate limit exceeded"}
    },
    dependencies=[Depends(standard_rate_limit)]
)
async def resume_workflow_endpoint(
    session_id: UUID = Path(..., description="Tech Spec session ID"),
    request: ResumeWorkflowRequest = Body(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    current_user: User = Depends(get_current_user)
):
    """
    Resume workflow from checkpoint.

    Use cases:
    1. Resume after user submits technology decision
    2. Resume after manual pause
    3. Resume after system failure (if checkpoint exists)

    Workflow resumes from the last checkpoint and continues execution.
    """
    logger.info(
        "Resume workflow request",
        session_id=str(session_id),
        has_decision=request.user_decision is not None
    )

    async with db_manager.get_async_session() as db_session:
        # Fetch session
        query = select(TechSpecSession).where(TechSpecSession.id == session_id)
        result = await db_session.execute(query)
        tech_session = result.scalar_one_or_none()

        if not tech_session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found"
            )

        # Check if session is in resumable state
        if tech_session.status not in ["paused", "failed"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot resume session with status: {tech_session.status}. Session must be paused or failed."
            )

        # Check if checkpoint exists
        state = await get_workflow_state(str(session_id))
        if not state:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No checkpoint found for session {session_id}. Cannot resume."
            )

        # Resume workflow in background
        background_tasks.add_task(
            resume_workflow,
            session_id=str(session_id),
            user_decision=request.user_decision
        )

        logger.info("Workflow resumed", session_id=str(session_id))

        return ResumeWorkflowResponse(
            session_id=session_id,
            status="in_progress",
            message="Workflow resumed successfully. Connect to WebSocket for updates."
        )


@router.post(
    "/sessions/{session_id}/pause",
    status_code=status.HTTP_200_OK,
    summary="Pause Workflow",
    description="Manually pause workflow execution",
    responses={
        200: {"description": "Workflow paused"},
        400: {"description": "Cannot pause workflow in current state"},
        401: {"description": "Unauthorized"},
        404: {"description": "Session not found"},
        429: {"description": "Rate limit exceeded"}
    },
    dependencies=[Depends(standard_rate_limit)]
)
async def pause_workflow_endpoint(
    session_id: UUID = Path(..., description="Tech Spec session ID"),
    current_user: User = Depends(get_current_user)
):
    """
    Pause workflow execution.

    Note: Workflow will pause at the next checkpoint.
    Current node execution will complete before pausing.
    """
    logger.info("Pause workflow request", session_id=str(session_id))

    async with db_manager.get_async_session() as db_session:
        query = select(TechSpecSession).where(TechSpecSession.id == session_id)
        result = await db_session.execute(query)
        tech_session = result.scalar_one_or_none()

        if not tech_session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found"
            )

        if tech_session.status != "in_progress":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot pause workflow with status: {tech_session.status}"
            )

        await pause_workflow(str(session_id))

        return {
            "session_id": session_id,
            "status": "paused",
            "message": "Workflow will pause at next checkpoint"
        }


@router.post(
    "/sessions/{session_id}/cancel",
    status_code=status.HTTP_200_OK,
    summary="Cancel Workflow",
    description="Cancel workflow execution permanently",
    responses={
        200: {"description": "Workflow cancelled"},
        401: {"description": "Unauthorized"},
        404: {"description": "Session not found"},
        429: {"description": "Rate limit exceeded"}
    },
    dependencies=[Depends(strict_rate_limit)]
)
async def cancel_workflow_endpoint(
    session_id: UUID = Path(..., description="Tech Spec session ID"),
    current_user: User = Depends(get_current_user)
):
    """
    Cancel workflow execution permanently.

    WARNING: This action cannot be undone.
    The workflow will be marked as cancelled and cannot be resumed.
    """
    logger.info("Cancel workflow request", session_id=str(session_id))

    async with db_manager.get_async_session() as db_session:
        query = select(TechSpecSession).where(TechSpecSession.id == session_id)
        result = await db_session.execute(query)
        tech_session = result.scalar_one_or_none()

        if not tech_session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found"
            )

        await cancel_workflow(str(session_id))

        return {
            "session_id": session_id,
            "status": "cancelled",
            "message": "Workflow cancelled successfully"
        }


@router.get(
    "/sessions/{session_id}/state",
    response_model=WorkflowStateResponse,
    summary="Get Workflow State",
    description="Get current workflow state from checkpoint",
    responses={
        200: {"description": "Workflow state retrieved"},
        401: {"description": "Unauthorized"},
        404: {"description": "Session or checkpoint not found"},
        429: {"description": "Rate limit exceeded"}
    },
    dependencies=[Depends(standard_rate_limit)]
)
async def get_workflow_state_endpoint(
    session_id: UUID = Path(..., description="Tech Spec session ID"),
    current_user: User = Depends(get_current_user)
):
    """
    Get current workflow state from checkpoint.

    Returns:
    - Current workflow status and stage
    - Progress percentage
    - Next node to be executed
    - Whether checkpoint exists (for resumability)

    This is useful for:
    - Debugging workflow execution
    - Understanding where workflow paused
    - Determining if workflow can be resumed
    """
    logger.info("Get workflow state request", session_id=str(session_id))

    async with db_manager.get_async_session() as db_session:
        query = select(TechSpecSession).where(TechSpecSession.id == session_id)
        result = await db_session.execute(query)
        tech_session = result.scalar_one_or_none()

        if not tech_session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found"
            )

        # Get checkpoint state
        state = await get_workflow_state(str(session_id))

        return WorkflowStateResponse(
            session_id=session_id,
            status=tech_session.status,
            current_stage=tech_session.current_stage,
            progress_percentage=tech_session.progress_percentage,
            next_node=state["next_node"] if state else None,
            checkpoint_exists=state is not None
        )


# ============= Helper Functions =============

async def _load_session_inputs(tech_session: TechSpecSession) -> tuple[str, Dict[str, str]]:
    """
    Load PRD and design documents for a session.

    Returns:
        (prd_content, design_docs)
    """
    from src.integration.design_agent_loader import load_design_agent_outputs

    try:
        # Load design outputs (includes PRD)
        design_outputs = await load_design_agent_outputs(str(tech_session.design_job_id))

        # Extract PRD
        prd_content = design_outputs.get("prd", "")

        # Extract design documents (keys match design_agent_loader output)
        design_docs = {
            "design_system": design_outputs.get("design_system", ""),
            "ux_flow": design_outputs.get("ux_flow", ""),
            "screen_specs": design_outputs.get("screen_specs", "")
        }

        return prd_content, design_docs

    except Exception as e:
        logger.error(
            "Failed to load session inputs",
            session_id=str(tech_session.id),
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load session inputs: {str(e)}"
        )
