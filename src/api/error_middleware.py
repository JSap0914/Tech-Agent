"""
Error handling middleware for Tech Spec Agent API.

Provides:
- Workflow-specific error handlers
- Database error persistence
- User-friendly error messages
- Error logging and monitoring
"""

from typing import Callable
from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import structlog
from datetime import datetime

from src.database.connection import get_db_connection
from src.websocket.connection_manager import manager as websocket_manager

logger = structlog.get_logger(__name__)


# ============= Error Types =============

class WorkflowExecutionError(Exception):
    """Raised when workflow execution fails."""

    def __init__(self, session_id: str, node_name: str, message: str, recoverable: bool = False):
        self.session_id = session_id
        self.node_name = node_name
        self.message = message
        self.recoverable = recoverable
        super().__init__(message)


class CheckpointNotFoundError(Exception):
    """Raised when checkpoint is not found for resumption."""

    def __init__(self, session_id: str):
        self.session_id = session_id
        super().__init__(f"No checkpoint found for session {session_id}")


class DesignJobNotCompletedError(Exception):
    """Raised when Design Agent job is not completed."""

    def __init__(self, design_job_id: str, current_status: str):
        self.design_job_id = design_job_id
        self.current_status = current_status
        super().__init__(
            f"Design job {design_job_id} not completed. Current status: {current_status}"
        )


class TechnologyDecisionConflictError(Exception):
    """Raised when user's technology choice conflicts with requirements."""

    def __init__(self, category: str, selected_tech: str, conflict_reason: str):
        self.category = category
        self.selected_tech = selected_tech
        self.conflict_reason = conflict_reason
        super().__init__(
            f"Technology {selected_tech} for {category} conflicts with requirements: {conflict_reason}"
        )


# ============= Error Handlers =============

async def workflow_execution_error_handler(request: Request, exc: WorkflowExecutionError):
    """
    Handle workflow execution errors.

    Logs error to database and sends notification via WebSocket.
    """
    logger.error(
        "Workflow execution error",
        session_id=exc.session_id,
        node=exc.node_name,
        error=exc.message,
        recoverable=exc.recoverable
    )

    # Persist error to database
    await _log_workflow_error(
        session_id=exc.session_id,
        node_name=exc.node_name,
        error_message=exc.message,
        recoverable=exc.recoverable
    )

    # Notify via WebSocket
    await websocket_manager.broadcast(
        {
            "type": "workflow_error",
            "session_id": exc.session_id,
            "node": exc.node_name,
            "error": exc.message,
            "recoverable": exc.recoverable,
            "timestamp": datetime.now().isoformat()
        },
        session_id=exc.session_id
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "WorkflowExecutionError",
            "session_id": exc.session_id,
            "node": exc.node_name,
            "message": exc.message if exc.recoverable else "Workflow execution failed. Please contact support.",
            "recoverable": exc.recoverable,
            "details": {
                "help": "Check session errors at GET /api/tech-spec/sessions/{session_id}/errors",
                "retry": "Use POST /api/tech-spec/sessions/{session_id}/resume to retry" if exc.recoverable else None
            }
        }
    )


async def checkpoint_not_found_error_handler(request: Request, exc: CheckpointNotFoundError):
    """Handle missing checkpoint errors."""
    logger.warning(
        "Checkpoint not found",
        session_id=exc.session_id
    )

    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "error": "CheckpointNotFound",
            "session_id": exc.session_id,
            "message": "No checkpoint found for this session. Cannot resume workflow.",
            "details": {
                "help": "Start a new workflow execution at POST /api/tech-spec/sessions/{session_id}/execute"
            }
        }
    )


async def design_job_not_completed_error_handler(request: Request, exc: DesignJobNotCompletedError):
    """Handle design job validation errors."""
    logger.warning(
        "Design job not completed",
        design_job_id=exc.design_job_id,
        current_status=exc.current_status
    )

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": "DesignJobNotCompleted",
            "design_job_id": exc.design_job_id,
            "current_status": exc.current_status,
            "message": f"Design job must be completed before starting Tech Spec. Current status: {exc.current_status}",
            "details": {
                "help": "Complete the Design Agent workflow first, then retry Tech Spec"
            }
        }
    )


async def technology_decision_conflict_error_handler(request: Request, exc: TechnologyDecisionConflictError):
    """Handle technology decision conflict errors."""
    logger.warning(
        "Technology decision conflict",
        category=exc.category,
        selected_tech=exc.selected_tech,
        conflict=exc.conflict_reason
    )

    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={
            "error": "TechnologyDecisionConflict",
            "category": exc.category,
            "selected_technology": exc.selected_tech,
            "conflict_reason": exc.conflict_reason,
            "message": f"Selected technology conflicts with project requirements",
            "details": {
                "help": "Choose a different technology or adjust project requirements",
                "severity": "warning"
            }
        }
    )


async def http_exception_handler(request: Request, exc: HTTPException):
    """
    Custom handler for HTTPException to provide consistent error format.
    """
    logger.warning(
        "HTTP exception",
        status_code=exc.status_code,
        detail=exc.detail,
        path=request.url.path
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "HTTPException",
            "status_code": exc.status_code,
            "message": exc.detail,
            "path": request.url.path,
            "timestamp": datetime.now().isoformat()
        }
    )


async def validation_error_handler(request: Request, exc: RequestValidationError):
    """
    Handle request validation errors (Pydantic).
    """
    logger.warning(
        "Validation error",
        errors=exc.errors(),
        path=request.url.path
    )

    # Format validation errors
    formatted_errors = []
    for error in exc.errors():
        formatted_errors.append({
            "field": ".".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"]
        })

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "ValidationError",
            "message": "Request validation failed",
            "validation_errors": formatted_errors,
            "path": request.url.path,
            "timestamp": datetime.now().isoformat()
        }
    )


async def generic_exception_handler(request: Request, exc: Exception):
    """
    Catch-all handler for unhandled exceptions.
    """
    logger.error(
        "Unhandled exception",
        error=str(exc),
        error_type=type(exc).__name__,
        path=request.url.path,
        method=request.method,
        exc_info=True
    )

    # Don't expose internal error details in production
    from src.config import settings

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "InternalServerError",
            "message": str(exc) if settings.is_development else "An unexpected error occurred",
            "error_type": type(exc).__name__ if settings.is_development else None,
            "path": request.url.path,
            "timestamp": datetime.now().isoformat(),
            "details": {
                "help": "Please contact support if this error persists"
            }
        }
    )


# ============= Error Logging =============

async def _log_workflow_error(
    session_id: str,
    node_name: str,
    error_message: str,
    recoverable: bool
):
    """
    Persist workflow error to agent_error_logs table.
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
                    recoverable,
                    occurred_at
                ) VALUES (
                    gen_random_uuid(),
                    $1, $2, $3, $4, $5, NOW()
                )
                """,
                session_id,
                node_name,
                "WorkflowExecutionError",
                error_message,
                recoverable
            )

        logger.info(
            "Workflow error logged to database",
            session_id=session_id,
            node=node_name
        )

    except Exception as e:
        logger.error(
            "Failed to log workflow error to database",
            session_id=session_id,
            error=str(e)
        )


# ============= Middleware =============

async def error_logging_middleware(request: Request, call_next: Callable) -> Response:
    """
    Middleware to log all requests and errors.
    """
    # Log request
    logger.info(
        "Incoming request",
        method=request.method,
        path=request.url.path,
        client=request.client.host if request.client else None
    )

    try:
        response = await call_next(request)

        # Log response
        logger.info(
            "Request completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code
        )

        return response

    except Exception as e:
        logger.error(
            "Request failed",
            method=request.method,
            path=request.url.path,
            error=str(e),
            exc_info=True
        )
        raise


# ============= Error Registration Helper =============

def register_error_handlers(app):
    """
    Register all custom error handlers with FastAPI app.

    Usage:
        from src.api.error_middleware import register_error_handlers
        register_error_handlers(app)
    """
    # Custom exception handlers
    app.add_exception_handler(WorkflowExecutionError, workflow_execution_error_handler)
    app.add_exception_handler(CheckpointNotFoundError, checkpoint_not_found_error_handler)
    app.add_exception_handler(DesignJobNotCompletedError, design_job_not_completed_error_handler)
    app.add_exception_handler(TechnologyDecisionConflictError, technology_decision_conflict_error_handler)

    # Standard exception handlers
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(Exception, generic_exception_handler)

    # Add error logging middleware
    app.middleware("http")(error_logging_middleware)

    logger.info("Error handlers registered successfully")
