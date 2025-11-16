"""
Error logging utility for persisting errors to agent_error_logs table.

Provides centralized error persistence for all LangGraph nodes.
"""

from datetime import datetime
from typing import Dict, Optional
import structlog

from src.database.connection import get_db_connection

logger = structlog.get_logger()


async def log_error_to_db(
    session_id: str,
    node_name: str,
    error: Exception,
    context: Optional[Dict] = None,
    recoverable: bool = True
) -> bool:
    """
    Persist error to agent_error_logs table.

    Args:
        session_id: Tech Spec session ID
        node_name: Name of the node where error occurred
        error: The exception that was raised
        context: Additional context (state data, parameters, etc.)
        recoverable: Whether the workflow can continue despite this error

    Returns:
        True if error was successfully logged, False otherwise

    Example:
        >>> try:
        ...     result = await some_operation()
        ... except Exception as e:
        ...     await log_error_to_db(
        ...         session_id="uuid",
        ...         node_name="generate_trd",
        ...         error=e,
        ...         context={"iteration": 2},
        ...         recoverable=True
        ...     )
    """
    try:
        async with get_db_connection() as conn:
            await conn.execute(
                """
                INSERT INTO agent_error_logs (
                    id,
                    session_id,
                    node_name,
                    error_type,
                    error_message,
                    stack_trace,
                    context,
                    recoverable,
                    occurred_at
                ) VALUES (
                    gen_random_uuid(),
                    $1, $2, $3, $4, $5, $6, $7, NOW()
                )
                """,
                session_id,
                node_name,
                type(error).__name__,
                str(error),
                None,  # Stack trace can be added if needed
                context or {},
                recoverable
            )

        logger.info(
            "error_logged_to_db",
            session_id=session_id,
            node=node_name,
            error_type=type(error).__name__
        )

        return True

    except Exception as db_error:
        logger.error(
            "failed_to_log_error",
            session_id=session_id,
            node=node_name,
            original_error=str(error),
            db_error=str(db_error),
            exc_info=True
        )
        return False


async def log_state_errors_to_db(session_id: str, state_errors: list) -> int:
    """
    Persist all accumulated errors from state["errors"] to database.

    This is typically called in save_to_db_node to persist all errors
    that occurred during workflow execution.

    Args:
        session_id: Tech Spec session ID
        state_errors: List of error dicts from state["errors"]

    Returns:
        Number of errors successfully logged

    Example:
        >>> errors = state["errors"]
        >>> logged_count = await log_state_errors_to_db(session_id, errors)
    """
    if not state_errors:
        return 0

    logged_count = 0

    try:
        async with get_db_connection() as conn:
            for error_dict in state_errors:
                # Skip if already logged (has _logged flag)
                if error_dict.get("_logged"):
                    continue

                try:
                    await conn.execute(
                        """
                        INSERT INTO agent_error_logs (
                            id,
                            session_id,
                            node_name,
                            error_type,
                            error_message,
                            stack_trace,
                            context,
                            recoverable,
                            occurred_at
                        ) VALUES (
                            gen_random_uuid(),
                            $1, $2, $3, $4, $5, $6, $7, $8
                        )
                        """,
                        session_id,
                        error_dict.get("node", "unknown"),
                        error_dict.get("error_type", "UnknownError"),
                        error_dict.get("message", ""),
                        error_dict.get("stack_trace"),
                        error_dict.get("context", {}),
                        error_dict.get("recoverable", True),
                        error_dict.get("timestamp", datetime.now())
                    )

                    # Mark as logged
                    error_dict["_logged"] = True
                    logged_count += 1

                except Exception as e:
                    logger.warning(
                        "error_log_failed",
                        session_id=session_id,
                        error=str(e)
                    )
                    continue

        logger.info(
            "state_errors_logged",
            session_id=session_id,
            total_errors=len(state_errors),
            logged_count=logged_count
        )

    except Exception as e:
        logger.error(
            "failed_to_log_state_errors",
            session_id=session_id,
            error=str(e),
            exc_info=True
        )

    return logged_count


async def get_session_errors(session_id: str) -> list:
    """
    Retrieve all errors for a session from database.

    Args:
        session_id: Tech Spec session ID

    Returns:
        List of error dicts

    Example:
        >>> errors = await get_session_errors("uuid")
        >>> for error in errors:
        ...     print(f"{error['node_name']}: {error['error_message']}")
    """
    try:
        async with get_db_connection() as conn:
            rows = await conn.fetch(
                """
                SELECT
                    node_name,
                    error_type,
                    error_message,
                    stack_trace,
                    context,
                    recoverable,
                    occurred_at
                FROM agent_error_logs
                WHERE session_id = $1
                ORDER BY occurred_at ASC
                """,
                session_id
            )

            return [dict(row) for row in rows]

    except Exception as e:
        logger.error(
            "failed_to_get_session_errors",
            session_id=session_id,
            error=str(e),
            exc_info=True
        )
        return []


async def count_session_errors(session_id: str) -> Dict[str, int]:
    """
    Get error statistics for a session.

    Args:
        session_id: Tech Spec session ID

    Returns:
        Dict with error counts by category

    Example:
        >>> stats = await count_session_errors("uuid")
        >>> print(f"Total: {stats['total']}, Recoverable: {stats['recoverable']}")
    """
    try:
        async with get_db_connection() as conn:
            row = await conn.fetchrow(
                """
                SELECT
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE recoverable = true) as recoverable,
                    COUNT(*) FILTER (WHERE recoverable = false) as critical,
                    COUNT(DISTINCT node_name) as affected_nodes
                FROM agent_error_logs
                WHERE session_id = $1
                """,
                session_id
            )

            return dict(row) if row else {
                "total": 0,
                "recoverable": 0,
                "critical": 0,
                "affected_nodes": 0
            }

    except Exception as e:
        logger.error(
            "failed_to_count_errors",
            session_id=session_id,
            error=str(e)
        )
        return {"total": 0, "recoverable": 0, "critical": 0, "affected_nodes": 0}
