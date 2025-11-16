"""
Load inputs node for Tech Spec Agent workflow.
Loads PRD and design documents from Design Agent shared tables.
"""

from typing import Dict
import structlog
from datetime import datetime

from src.langgraph.state import TechSpecState
from src.integration.design_agent_loader import (
    load_design_agent_outputs,
    validate_design_job_completed,
    load_design_decisions
)

logger = structlog.get_logger(__name__)


async def load_inputs_node(state: TechSpecState) -> TechSpecState:
    """
    Load PRD and design documents from Design Agent.

    This is the entry point of the Tech Spec workflow.
    Validates that Design Agent has completed successfully
    and loads all required documents.

    If inputs are already provided (e.g., CLI mode), skips database operations.

    Args:
        state: Current workflow state with session metadata

    Returns:
        Updated state with loaded documents

    Raises:
        ValueError: If Design Agent job is not completed or documents are missing
    """
    logger.info(
        "Loading inputs",
        session_id=state["session_id"],
        design_job_id=state.get("design_job_id")
    )

    # Check if inputs are already provided (CLI mode)
    if state.get("prd_content") and state.get("design_docs"):
        logger.info(
            "Inputs already provided (CLI mode), skipping database load",
            session_id=state["session_id"],
            prd_length=len(state["prd_content"]),
            design_docs_count=len([v for v in state["design_docs"].values() if v])
        )

        # Update state with progress
        state.update({
            "current_stage": "load_inputs",
            "progress_percentage": 5.0,
            "updated_at": datetime.now().isoformat()
        })

        # Add conversation message
        doc_count = len([v for v in state["design_docs"].values() if v])
        state["conversation_history"].append({
            "role": "agent",
            "message": f"✅ Successfully loaded PRD and {doc_count} design documents. Starting analysis...",
            "timestamp": datetime.now().isoformat(),
            "metadata": {
                "node": "load_inputs",
                "action": "inputs_already_loaded",
                "mode": "cli"
            }
        })

        return state

    # Otherwise, load from database (web API mode)
    logger.info(
        "Loading inputs from Design Agent database",
        session_id=state["session_id"],
        design_job_id=state["design_job_id"]
    )

    try:
        # Step 1: Validate Design Agent job is completed
        await validate_design_job_completed(state["design_job_id"])

        # Step 2: Load design outputs
        outputs = await load_design_agent_outputs(state["design_job_id"])

        # Step 3: Load design decisions (user choices from Design Agent)
        decisions = await load_design_decisions(state["design_job_id"])

        # Step 4: Update state
        state.update({
            "prd_content": outputs.get("prd", ""),
            "design_docs": {
                "design_system": outputs.get("design_system", ""),
                "ux_flow": outputs.get("ux_flow", ""),
                "screen_specs": outputs.get("screen_specs", ""),
                "wireframes": outputs.get("wireframes", ""),
                "component_library": outputs.get("component_library", "")
            },
            "ai_studio_code_path": outputs.get("ai_studio_code_path", ""),
            "design_decisions": decisions,
            "current_stage": "load_inputs",
            "progress_percentage": 5.0,
            "updated_at": datetime.now().isoformat()
        })

        # Step 5: Log successful load
        doc_count = sum(1 for v in state["design_docs"].values() if v)
        logger.info(
            "Successfully loaded inputs",
            session_id=state["session_id"],
            prd_length=len(state["prd_content"]),
            design_docs_count=doc_count,
            has_ai_studio_code=bool(state["ai_studio_code_path"]),
            design_decisions_count=len(decisions)
        )

        # Step 6: Add conversation message
        state["conversation_history"].append({
            "role": "agent",
            "message": f"✅ Successfully loaded PRD and {doc_count} design documents. Starting analysis...",
            "timestamp": datetime.now().isoformat(),
            "metadata": {
                "node": "load_inputs",
                "action": "inputs_loaded"
            }
        })

        return state

    except Exception as e:
        logger.error(
            "Failed to load inputs",
            session_id=state["session_id"],
            design_job_id=state["design_job_id"],
            error=str(e)
        )

        # Add error to state
        state["errors"].append({
            "node": "load_inputs",
            "error_type": type(e).__name__,
            "message": str(e),
            "timestamp": datetime.now().isoformat(),
            "recoverable": False
        })

        raise
