"""
PostgreSQL checkpointer configuration for LangGraph workflow state persistence.

The checkpointer enables:
- Workflow state persistence across sessions
- Resume capability if user disconnects
- State recovery after errors
- Audit trail of all workflow executions
"""

import os
from typing import Optional
from langgraph.checkpoint.postgres import PostgresSaver
from psycopg_pool import ConnectionPool
import structlog

logger = structlog.get_logger()


def create_checkpointer(database_url: Optional[str] = None) -> PostgresSaver:
    """
    Create PostgreSQL checkpointer for LangGraph workflow.

    The checkpointer automatically creates a table:
        - `checkpoints`: Stores serialized workflow states

    Args:
        database_url: PostgreSQL connection string. If not provided,
                     reads from DATABASE_URL environment variable.

    Returns:
        PostgresSaver instance configured for Tech Spec Agent

    Example:
        >>> checkpointer = create_checkpointer()
        >>> workflow = create_tech_spec_workflow(checkpointer=checkpointer)
        >>> result = await workflow.ainvoke(initial_state, config={
        ...     "configurable": {"thread_id": session_id}
        ... })
    """
    if not database_url:
        database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise ValueError(
            "DATABASE_URL not found in environment. "
            "Please set DATABASE_URL or pass database_url parameter."
        )

    logger.info("creating_checkpointer", database_url=database_url[:30] + "...")

    # Create PostgreSQL connection pool using psycopg
    connection_pool = ConnectionPool(database_url, min_size=1, max_size=10, kwargs={"autocommit": True})

    # Create checkpointer with connection pool
    checkpointer = PostgresSaver(connection_pool)

    # Initialize checkpoints table if not exists
    checkpointer.setup()

    logger.info("checkpointer_created", status="ready")

    return checkpointer


async def close_checkpointer(checkpointer: PostgresSaver):
    """
    Close checkpointer and clean up resources.

    Args:
        checkpointer: PostgresSaver instance to close
    """
    if checkpointer and checkpointer.conn:
        await checkpointer.conn.close()
        logger.info("checkpointer_closed")


# =============================================================================
# Checkpointer usage helpers
# =============================================================================

def get_checkpoint_config(session_id: str, recursion_limit: int = 200) -> dict:
    """
    Get LangGraph config dict for checkpoint management.

    Args:
        session_id: Tech Spec session ID (UUID)
        recursion_limit: Maximum LangGraph steps before raising recursion error

    Returns:
        Config dict with thread_id for checkpointing

    Example:
        >>> config = get_checkpoint_config("550e8400-e29b-41d4-a716-446655440000")
        >>> workflow.ainvoke(state, config=config)
    """
    return {
        "recursion_limit": recursion_limit,
        "configurable": {
            "thread_id": session_id,
            "checkpoint_ns": "tech_spec_agent"
        }
    }


async def get_checkpoint_state(
    checkpointer: PostgresSaver,
    session_id: str
) -> Optional[dict]:
    """
    Retrieve saved checkpoint state for a session.

    Args:
        checkpointer: PostgresSaver instance
        session_id: Tech Spec session ID

    Returns:
        Saved state dict if exists, None otherwise

    Example:
        >>> state = await get_checkpoint_state(checkpointer, session_id)
        >>> if state:
        ...     # Resume workflow from saved state
        ...     workflow.ainvoke(state, config=get_checkpoint_config(session_id))
    """
    config = get_checkpoint_config(session_id)

    try:
        checkpoint = await checkpointer.aget(config)
        if checkpoint:
            return checkpoint.get("state")
    except Exception as e:
        logger.warning(
            "checkpoint_retrieve_error",
            session_id=session_id,
            error=str(e)
        )

    return None


async def delete_checkpoint(checkpointer: PostgresSaver, session_id: str):
    """
    Delete checkpoint state for a session.

    Useful for cleanup after workflow completion.

    Args:
        checkpointer: PostgresSaver instance
        session_id: Tech Spec session ID
    """
    config = get_checkpoint_config(session_id)

    try:
        await checkpointer.adelete(config)
        logger.info("checkpoint_deleted", session_id=session_id)
    except Exception as e:
        logger.warning(
            "checkpoint_delete_error",
            session_id=session_id,
            error=str(e)
        )
