"""
Workflow executor for running LangGraph Tech Spec workflow in background.

Provides async execution, checkpointing, error handling, and state management
for the 17-node Tech Spec Agent workflow.
"""

import asyncio
from typing import Dict, Optional
from uuid import UUID
from datetime import datetime
import structlog

from src.langgraph.workflow import create_tech_spec_workflow
from src.langgraph.state import create_initial_state, TechSpecState
from src.langgraph.checkpointer import create_checkpointer, get_checkpoint_config
from src.database.connection import get_db_connection
from src.websocket.connection_manager import manager as websocket_manager
from src.config import settings

logger = structlog.get_logger(__name__)


# Global workflow instance (created once and reused)
_workflow = None
_checkpointer = None


async def initialize_workflow():
    """
    Initialize LangGraph workflow with PostgreSQL checkpointer.
    Should be called once during application startup.
    """
    global _workflow, _checkpointer

    if _workflow is None:
        logger.info("Initializing LangGraph workflow with checkpointer")
        _checkpointer = create_checkpointer(database_url=settings.database_url_sync)
        _workflow = create_tech_spec_workflow(checkpointer=_checkpointer)
        logger.info("LangGraph workflow initialized successfully")


async def get_workflow():
    """Get the initialized workflow instance."""
    if _workflow is None:
        await initialize_workflow()
    return _workflow


async def execute_workflow(
    session_id: str,
    project_id: str,
    user_id: str,
    design_job_id: str,
    prd_content: str,
    design_docs: Dict[str, str],
    ai_studio_code_path: Optional[str] = None
) -> None:
    """
    Execute Tech Spec workflow in background.

    This function runs the complete 17-node workflow asynchronously,
    sending progress updates via WebSocket.

    Args:
        session_id: Tech Spec session ID
        project_id: ANYON project ID
        user_id: User ID
        design_job_id: Design Agent job ID
        prd_content: Product Requirements Document content
        design_docs: Dictionary of design documents (3 types)
        ai_studio_code_path: Optional path to Google AI Studio ZIP

    Flow:
        1. Create initial state
        2. Execute workflow with checkpointing
        3. Send progress updates via WebSocket
        4. Handle errors and persist to database
        5. Update session status in PostgreSQL
    """
    logger.info(
        "Starting workflow execution",
        session_id=session_id,
        project_id=project_id
    )

    try:
        # Update session status to in_progress
        await _update_session_status(
            session_id=session_id,
            status="in_progress",
            current_stage="workflow_started"
        )

        # Send WebSocket notification
        await websocket_manager.broadcast(
            {
                "type": "workflow_started",
                "session_id": session_id,
                "message": "Tech Spec workflow started",
                "timestamp": datetime.now().isoformat()
            },
            session_id=session_id
        )

        # Create initial state
        state = create_initial_state(
            session_id=session_id,
            project_id=project_id,
            user_id=user_id,
            design_job_id=design_job_id
        )

        # Populate state with inputs
        state.update({
            "prd_content": prd_content,
            "design_docs": design_docs,
            "ai_studio_code_path": ai_studio_code_path
        })

        # Get workflow
        workflow = await get_workflow()

        # Get checkpoint config for resumability
        config = get_checkpoint_config(session_id)

        # Execute workflow with streaming
        logger.info("Invoking workflow", session_id=session_id)

        async for event in workflow.astream(state, config=config):
            # event is a dict with node names as keys
            for node_name, node_output in event.items():
                logger.info(
                    "Workflow node completed",
                    session_id=session_id,
                    node=node_name,
                    stage=node_output.get("current_stage"),
                    progress=node_output.get("progress_percentage")
                )

                # Update database
                await _update_session_status(
                    session_id=session_id,
                    status="in_progress",
                    current_stage=node_output.get("current_stage", "processing"),
                    progress=node_output.get("progress_percentage", 0.0),
                    session_data=_extract_session_data(node_output)
                )

                # Send progress via WebSocket
                await websocket_manager.broadcast(
                    {
                        "type": "progress_update",
                        "session_id": session_id,
                        "node": node_name,
                        "stage": node_output.get("current_stage"),
                        "progress": node_output.get("progress_percentage", 0.0),
                        "message": _get_last_conversation_message(node_output),
                        "timestamp": datetime.now().isoformat()
                    },
                    session_id=session_id
                )

                # Check if workflow paused for user decision
                if node_output.get("paused") and node_output.get("current_stage") == "wait_user_decision":
                    logger.info(
                        "Workflow paused for user decision",
                        session_id=session_id,
                        category=node_output.get("current_research_category")
                    )

                    await _update_session_status(
                        session_id=session_id,
                        status="paused",
                        current_stage="wait_user_decision",
                        session_data=_extract_session_data(node_output)
                    )

                    # Extract options from technology_options dict
                    current_category = node_output.get("current_research_category")
                    technology_options = node_output.get("technology_options", {})
                    options = technology_options.get(current_category, []) if current_category else []

                    await websocket_manager.broadcast(
                        {
                            "type": "waiting_user_decision",
                            "session_id": session_id,
                            "category": current_category,
                            "options": options,
                            "message": "Waiting for user technology selection",
                            "timestamp": datetime.now().isoformat()
                        },
                        session_id=session_id
                    )

                    # Workflow will resume when user submits decision
                    return

        # Workflow completed successfully
        logger.info("Workflow completed successfully", session_id=session_id)

        await _update_session_status(
            session_id=session_id,
            status="completed",
            current_stage="completed",
            progress=100.0
        )

        await websocket_manager.broadcast(
            {
                "type": "workflow_completed",
                "session_id": session_id,
                "message": "Tech Spec generation completed successfully",
                "timestamp": datetime.now().isoformat()
            },
            session_id=session_id
        )

    except Exception as e:
        logger.error(
            "Workflow execution failed",
            session_id=session_id,
            error=str(e),
            exc_info=True
        )

        # Update session to failed status
        await _update_session_status(
            session_id=session_id,
            status="failed",
            current_stage="failed",
            error_message=str(e)
        )

        # Notify via WebSocket
        await websocket_manager.broadcast(
            {
                "type": "workflow_failed",
                "session_id": session_id,
                "error": str(e),
                "message": "Workflow execution failed. Please contact support.",
                "timestamp": datetime.now().isoformat()
            },
            session_id=session_id
        )

        # Re-raise for background task error handling
        raise


async def resume_workflow(
    session_id: str,
    user_decision: Optional[Dict] = None
) -> None:
    """
    Resume workflow from checkpoint.

    This is called when:
    1. User submits a technology decision
    2. User manually resumes a paused workflow
    3. System recovers from a failure

    Args:
        session_id: Tech Spec session ID
        user_decision: Optional user decision to apply to state
    """
    logger.info("Resuming workflow", session_id=session_id)

    try:
        # Get workflow
        workflow = await get_workflow()

        # Get checkpoint config
        config = get_checkpoint_config(session_id)

        # Get current state from checkpoint
        state = await workflow.aget_state(config)

        if state is None:
            raise ValueError(f"No checkpoint found for session {session_id}")

        # Apply user decision if provided
        if user_decision:
            logger.info(
                "Applying user decision",
                session_id=session_id,
                category=user_decision.get("category")
            )

            # Update state with decision
            current_state = state.values
            current_state["user_decisions"].append({
                "category": user_decision["category"],
                "technology_name": user_decision["selected_technology"],
                "reasoning": user_decision.get("reasoning", ""),
                "timestamp": datetime.now().isoformat()
            })

            # Unpause workflow
            current_state["paused"] = False

        # Update session status
        await _update_session_status(
            session_id=session_id,
            status="in_progress",
            current_stage="resuming"
        )

        await websocket_manager.broadcast(
            {
                "type": "workflow_resumed",
                "session_id": session_id,
                "message": "Workflow resumed",
                "timestamp": datetime.now().isoformat()
            },
            session_id=session_id
        )

        # Continue workflow execution
        async for event in workflow.astream(None, config=config):
            for node_name, node_output in event.items():
                logger.info(
                    "Workflow node completed",
                    session_id=session_id,
                    node=node_name
                )

                # Update progress (same as execute_workflow)
                await _update_session_status(
                    session_id=session_id,
                    status="in_progress",
                    current_stage=node_output.get("current_stage", "processing"),
                    progress=node_output.get("progress_percentage", 0.0),
                    session_data=_extract_session_data(node_output)
                )

                await websocket_manager.broadcast(
                    {
                        "type": "progress_update",
                        "session_id": session_id,
                        "node": node_name,
                        "stage": node_output.get("current_stage"),
                        "progress": node_output.get("progress_percentage", 0.0),
                        "message": _get_last_conversation_message(node_output),
                        "timestamp": datetime.now().isoformat()
                    },
                    session_id=session_id
                )

                # Check if paused again for another decision
                if node_output.get("paused"):
                    await _update_session_status(
                        session_id=session_id,
                        status="paused",
                        current_stage="waiting_user_decision"
                    )
                    return

        # Workflow completed
        await _update_session_status(
            session_id=session_id,
            status="completed",
            current_stage="completed",
            progress=100.0
        )

        await websocket_manager.broadcast(
            {
                "type": "workflow_completed",
                "session_id": session_id,
                "message": "Tech Spec generation completed",
                "timestamp": datetime.now().isoformat()
            },
            session_id=session_id
        )

    except Exception as e:
        logger.error(
            "Failed to resume workflow",
            session_id=session_id,
            error=str(e),
            exc_info=True
        )

        await _update_session_status(
            session_id=session_id,
            status="failed",
            current_stage="failed",
            error_message=str(e)
        )

        raise


async def pause_workflow(session_id: str) -> None:
    """
    Manually pause workflow execution.

    Note: Workflow will pause at next checkpoint.
    """
    logger.info("Pausing workflow", session_id=session_id)

    await _update_session_status(
        session_id=session_id,
        status="paused",
        current_stage="manually_paused"
    )

    await websocket_manager.broadcast(
        {
            "type": "workflow_paused",
            "session_id": session_id,
            "message": "Workflow paused by user",
            "timestamp": datetime.now().isoformat()
        },
        session_id=session_id
    )


async def cancel_workflow(session_id: str) -> None:
    """
    Cancel workflow execution.

    This stops the workflow and marks the session as cancelled.
    """
    logger.info("Cancelling workflow", session_id=session_id)

    await _update_session_status(
        session_id=session_id,
        status="cancelled",
        current_stage="cancelled"
    )

    await websocket_manager.broadcast(
        {
            "type": "workflow_cancelled",
            "session_id": session_id,
            "message": "Workflow cancelled by user",
            "timestamp": datetime.now().isoformat()
        },
        session_id=session_id
    )


async def get_workflow_state(session_id: str) -> Optional[Dict]:
    """
    Get current workflow state from checkpoint.

    Returns:
        Current state dict or None if no checkpoint exists
    """
    try:
        workflow = await get_workflow()
        config = get_checkpoint_config(session_id)
        state = await workflow.aget_state(config)

        if state is None:
            return None

        return {
            "session_id": session_id,
            "state": state.values,
            "next_node": state.next,
            "config": state.config,
            "created_at": state.created_at.isoformat() if state.created_at else None
        }

    except Exception as e:
        logger.error(
            "Failed to get workflow state",
            session_id=session_id,
            error=str(e)
        )
        return None


# Helper functions

async def _update_session_status(
    session_id: str,
    status: str,
    current_stage: str,
    progress: float = 0.0,
    session_data: Optional[Dict] = None,
    error_message: Optional[str] = None
):
    """Update tech_spec_sessions table with current status."""
    try:
        async with get_db_connection() as conn:
            update_query = """
                UPDATE tech_spec_sessions
                SET
                    status = $1,
                    current_stage = $2,
                    progress_percentage = $3,
                    session_data = COALESCE($4, session_data),
                    error_message = $5,
                    updated_at = NOW(),
                    completed_at = CASE WHEN $1 = 'completed' THEN NOW() ELSE completed_at END
                WHERE id = $6
            """

            await conn.execute(
                update_query,
                status,
                current_stage,
                progress,
                session_data,
                error_message,
                session_id
            )

    except Exception as e:
        logger.error(
            "Failed to update session status",
            session_id=session_id,
            error=str(e)
        )


def _extract_session_data(state: TechSpecState) -> Dict:
    """Extract relevant session data from workflow state."""
    return {
        "gaps_identified": len(state.get("identified_gaps", [])),
        "decisions_made": len(state.get("user_decisions", [])),
        "pending_decisions": [
            gap["category"] for gap in state.get("identified_gaps", [])
            if gap["category"] not in [d.get("category") for d in state.get("user_decisions", [])]
        ],
        "current_research_category": state.get("current_research_category"),
        "inferred_endpoints": len(state.get("inferred_api_spec", {}).get("endpoints", [])),
        "errors_count": len(state.get("errors", []))
    }


def _get_last_conversation_message(state: TechSpecState) -> str:
    """Get last agent message from conversation history."""
    conversation = state.get("conversation_history", [])
    if not conversation:
        return ""

    # Find last agent message
    for msg in reversed(conversation):
        if msg.get("role") == "agent":
            return msg.get("message", "")

    return ""
