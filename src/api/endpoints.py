"""
REST API endpoints for Tech Spec Agent.
Implements ANYON platform API contract.
"""

import asyncio
from typing import Optional
from uuid import uuid4, UUID
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, status, Path, Body, BackgroundTasks
from sqlalchemy import select

from src.api.schemas import (
    StartTechSpecRequest,
    StartTechSpecResponse,
    SessionStatusResponse,
    UserDecisionRequest,
    UserDecisionResponse,
    TRDDownloadResponse,
    ErrorResponse,
)
from src.api.auth import get_current_user, User
from src.api.rate_limit import standard_rate_limit, strict_rate_limit, generous_rate_limit
from src.database.connection import db_manager
from src.database.models import TechSpecSession, GeneratedTRDDocument
from src.integration.design_agent_loader import (
    validate_design_job_completed,
    load_design_agent_outputs
)
from src.api.workflow_executor import execute_workflow, resume_workflow
import structlog

logger = structlog.get_logger(__name__)

router = APIRouter()


# ============= Endpoint 1: Start Tech Spec Session =============

@router.post(
    "/api/projects/{project_id}/start-tech-spec",
    response_model=StartTechSpecResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start Tech Spec Generation",
    description="Initialize a new Tech Spec session from a completed Design Agent job",
    responses={
        201: {"description": "Session created successfully"},
        400: {"model": ErrorResponse, "description": "Invalid request"},
        401: {"description": "Unauthorized"},
        404: {"description": "Project or Design Job not found"},
        429: {"description": "Rate limit exceeded"}
    },
    dependencies=[Depends(standard_rate_limit)]
)
async def start_tech_spec(
    project_id: UUID = Path(..., description="Project ID"),
    request: StartTechSpecRequest = Body(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    current_user: User = Depends(get_current_user)
):
    """
    Start a new Tech Spec session.

    This endpoint:
    1. Validates the Design Agent job is completed
    2. Loads PRD and design documents
    3. Creates a new Tech Spec session
    4. Returns WebSocket URL for real-time updates
    """
    logger.info(
        "Starting Tech Spec session",
        project_id=str(project_id),
        design_job_id=str(request.design_job_id),
        user_id=str(current_user.user_id)
    )

    try:
        # Validate Design Agent job is completed
        await validate_design_job_completed(str(request.design_job_id))

        # Load design documents
        design_outputs = await load_design_agent_outputs(str(request.design_job_id))
        logger.info("Design outputs loaded", doc_types=list(design_outputs.keys()))

        # Create new Tech Spec session
        session_id = uuid4()
        websocket_url = f"{settings.websocket_base_url}/tech-spec/{session_id}"

        async with db_manager.get_async_session() as db_session:
            tech_session = TechSpecSession(
                id=session_id,
                project_id=project_id,
                design_job_id=request.design_job_id,
                user_id=request.user_id or current_user.user_id,
                status="pending",
                current_stage="initializing",
                progress_percentage=0.0,
                session_data={
                    "prd_loaded": True,
                    "design_docs_loaded": True,
                    "gaps_identified": 0,
                    "decisions_made": 0
                },
                websocket_url=websocket_url,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )

            db_session.add(tech_session)
            await db_session.commit()
            await db_session.refresh(tech_session)

        logger.info("Tech Spec session created", session_id=str(session_id))

        # Extract PRD content
        prd_content = design_outputs.get("prd", "")

        # Extract design documents (keys match design_agent_loader output)
        design_docs = {
            "design_system": design_outputs.get("design_system", ""),
            "ux_flow": design_outputs.get("ux_flow", ""),
            "screen_specs": design_outputs.get("screen_specs", "")
        }

        # Trigger LangGraph workflow in background
        background_tasks.add_task(
            execute_workflow,
            session_id=str(session_id),
            project_id=str(project_id),
            user_id=str(current_user.user_id),
            design_job_id=str(request.design_job_id),
            prd_content=prd_content,
            design_docs=design_docs,
            google_ai_studio_code_path=None  # Will be provided later if available
        )

        logger.info(
            "Workflow execution started in background",
            session_id=str(session_id)
        )

        return StartTechSpecResponse(
            session_id=session_id,
            project_id=project_id,
            status="pending",
            websocket_url=websocket_url,
            created_at=tech_session.created_at
        )

    except ValueError as e:
        # Design job validation failed
        logger.warning("Design job validation failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    except Exception as e:
        logger.error("Failed to start Tech Spec session", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start Tech Spec session"
        )


# ============= Endpoint 2: Get Session Status =============

@router.get(
    "/api/tech-spec/sessions/{session_id}/status",
    response_model=SessionStatusResponse,
    summary="Get Session Status",
    description="Retrieve current status and progress of a Tech Spec session",
    responses={
        200: {"description": "Session status retrieved"},
        401: {"description": "Unauthorized"},
        404: {"description": "Session not found"},
        429: {"description": "Rate limit exceeded"}
    },
    dependencies=[Depends(generous_rate_limit)]  # Read operations get higher limit
)
async def get_session_status(
    session_id: UUID = Path(..., description="Tech Spec session ID"),
    current_user: User = Depends(get_current_user)
):
    """
    Get current status of a Tech Spec session.

    Returns:
    - Session status and progress
    - Identified technology gaps
    - Pending user decisions
    - Completion percentage
    """
    logger.info("Fetching session status", session_id=str(session_id))

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

        # Extract session data
        session_data = tech_session.session_data or {}
        gaps_identified = session_data.get("gaps_identified", 0)
        decisions_made = session_data.get("decisions_made", 0)
        pending_gaps = session_data.get("pending_decisions", [])

        return SessionStatusResponse(
            session_id=tech_session.id,
            project_id=tech_session.project_id,
            design_job_id=tech_session.design_job_id,
            status=tech_session.status,
            current_stage=tech_session.current_stage,
            progress_percentage=tech_session.progress_percentage,
            gaps_identified=gaps_identified,
            decisions_made=decisions_made,
            pending_decisions=pending_gaps,
            created_at=tech_session.created_at,
            updated_at=tech_session.updated_at,
            completed_at=tech_session.completed_at,
            websocket_url=tech_session.websocket_url
        )


# ============= Endpoint 3: Submit User Decision =============

@router.post(
    "/api/tech-spec/sessions/{session_id}/decisions",
    response_model=UserDecisionResponse,
    summary="Submit User Decision",
    description="Submit user's technology choice decision",
    responses={
        200: {"description": "Decision recorded successfully"},
        400: {"model": ErrorResponse, "description": "Invalid decision"},
        401: {"description": "Unauthorized"},
        404: {"description": "Session not found"},
        429: {"description": "Rate limit exceeded"}
    },
    dependencies=[Depends(standard_rate_limit)]
)
async def submit_user_decision(
    session_id: UUID = Path(..., description="Tech Spec session ID"),
    decision: UserDecisionRequest = Body(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    current_user: User = Depends(get_current_user)
):
    """
    Submit a user decision for technology choice.

    This endpoint:
    1. Validates the session is awaiting decisions
    2. Records the decision in database
    3. Triggers continuation of LangGraph workflow
    4. Returns next action required
    """
    logger.info(
        "Submitting user decision",
        session_id=str(session_id),
        category=decision.technology_category,
        technology=decision.selected_technology
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

        # Validate session status
        if tech_session.status not in ["in_progress", "paused"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot submit decision for session with status: {tech_session.status}"
            )

        # Update session data
        session_data = tech_session.session_data or {}
        decisions_made = session_data.get("decisions_made", 0)

        # Record decision
        session_data["decisions_made"] = decisions_made + 1
        session_data.setdefault("user_decisions", []).append({
            "category": decision.technology_category,
            "selected": decision.selected_technology,
            "reasoning": decision.reasoning,
            "timestamp": datetime.utcnow().isoformat()
        })

        tech_session.session_data = session_data
        tech_session.updated_at = datetime.utcnow()

        await db_session.commit()

    logger.info("Decision recorded", session_id=str(session_id))

    # Prepare user decision for workflow
    user_decision = {
        "category": decision.technology_category.value,
        "selected_technology": decision.selected_technology,
        "reasoning": decision.reasoning
    }

    # Resume workflow with user decision
    background_tasks.add_task(
        resume_workflow,
        session_id=str(session_id),
        user_decision=user_decision
    )

    logger.info(
        "Workflow continuation triggered",
        session_id=str(session_id),
        category=decision.technology_category
    )

    # Determine next action
    remaining_gaps = session_data.get("gaps_identified", 0) - session_data["decisions_made"]
    next_action = "await_more_decisions" if remaining_gaps > 0 else "generating_trd"

    return UserDecisionResponse(
        session_id=session_id,
        decision_accepted=True,
        message=f"Decision recorded successfully. {remaining_gaps} decisions remaining.",
        next_action=next_action
    )


# ============= Endpoint 4: Download TRD =============

@router.get(
    "/api/tech-spec/sessions/{session_id}/trd",
    response_model=TRDDownloadResponse,
    summary="Download TRD",
    description="Download generated Technical Requirements Document",
    responses={
        200: {"description": "TRD document retrieved"},
        401: {"description": "Unauthorized"},
        404: {"description": "Session or TRD not found"},
        409: {"description": "TRD not ready yet"},
        429: {"description": "Rate limit exceeded"}
    },
    dependencies=[Depends(generous_rate_limit)]
)
async def download_trd(
    session_id: UUID = Path(..., description="Tech Spec session ID"),
    current_user: User = Depends(get_current_user)
):
    """
    Download the generated TRD document.

    Returns:
    - Full TRD content (Markdown)
    - API specification (OpenAPI/Swagger JSON)
    - Database schema (SQL DDL)
    - Architecture diagram (Mermaid)
    - Technology stack document
    - Quality score and validation report
    """
    logger.info("Downloading TRD", session_id=str(session_id))

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

        # Check if TRD is ready
        if tech_session.status != "completed":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"TRD not ready. Session status: {tech_session.status}. Progress: {tech_session.progress_percentage}%"
            )

        # Fetch TRD document
        trd_query = select(GeneratedTRDDocument).where(
            GeneratedTRDDocument.session_id == session_id
        ).order_by(GeneratedTRDDocument.version.desc())

        trd_result = await db_session.execute(trd_query)
        trd_doc = trd_result.scalar_one_or_none()

        if not trd_doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"TRD document not found for session {session_id}"
            )

        from src.api.schemas import TRDDocumentSchema

        return TRDDownloadResponse(
            session_id=session_id,
            document=TRDDocumentSchema(
                trd_content=trd_doc.trd_content or "",
                api_specification=trd_doc.api_specification,
                database_schema=trd_doc.database_schema,
                architecture_diagram=trd_doc.architecture_diagram,
                tech_stack_document=trd_doc.tech_stack_document,
                quality_score=trd_doc.quality_score or 0.0,
                validation_report=trd_doc.validation_report
            ),
            version=trd_doc.version or 1,
            created_at=trd_doc.created_at
        )


# ============= Endpoint 5: Health Check (Enhanced) =============

# Note: Basic health check already exists in src/main.py
# This is an enhanced version with detailed component status

@router.get(
    "/api/health/detailed",
    summary="Detailed Health Check",
    description="Detailed health check with component status",
    include_in_schema=True
)
async def detailed_health_check():
    """
    Detailed health check endpoint.

    Checks:
    - Database connectivity
    - Redis connectivity
    - Service status
    """
    health_status = {
        "status": "healthy",
        "service": "tech-spec-agent",
        "timestamp": datetime.utcnow().isoformat(),
        "components": {}
    }

    # Check database
    try:
        db_healthy = await db_manager.check_connection()
        health_status["components"]["database"] = {
            "status": "healthy" if db_healthy else "unhealthy",
            "message": "Database connection OK" if db_healthy else "Database connection failed"
        }
    except Exception as e:
        health_status["components"]["database"] = {
            "status": "unhealthy",
            "message": f"Database error: {str(e)}"
        }
        health_status["status"] = "degraded"

    # Check Redis (if enabled)
    try:
        from src.api.rate_limit import rate_limiter
        if rate_limiter._redis:
            await rate_limiter._redis.ping()
            health_status["components"]["redis"] = {
                "status": "healthy",
                "message": "Redis connection OK"
            }
        else:
            health_status["components"]["redis"] = {
                "status": "disabled",
                "message": "Redis not configured"
            }
    except Exception as e:
        health_status["components"]["redis"] = {
            "status": "unhealthy",
            "message": f"Redis error: {str(e)}"
        }
        health_status["status"] = "degraded"

    # Overall status
    if health_status["status"] == "degraded":
        return health_status

    return health_status


# Import settings at the end to avoid circular imports
from src.config import settings
