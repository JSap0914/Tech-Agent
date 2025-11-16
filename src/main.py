"""
Tech Spec Agent - FastAPI Application
Main entry point for the Tech Spec Agent API server.
"""

from contextlib import asynccontextmanager
from typing import Dict

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
import structlog
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from src.config import settings
from src.database.connection import db_manager
from src.cache import redis_client  # Week 12: Use shared Redis client
from src.api.endpoints import router as api_router
from src.api.workflow_routes import router as workflow_router
from src.websocket.routes import router as websocket_router
from src.api.rate_limit import rate_limiter, rate_limit_middleware
from src.api.error_middleware import register_error_handlers
from src.api.workflow_executor import initialize_workflow

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles startup and shutdown events.
    """
    # Startup
    logger.info("Starting Tech Spec Agent", environment=settings.environment)

    try:
        # Initialize database
        logger.info("Initializing database connection")
        db_manager.initialize_async_engine()

        # Test database connection
        db_healthy = await db_manager.check_connection()
        if not db_healthy:
            logger.error("Database connection check failed")
            raise RuntimeError("Database connection failed")
        logger.info("Database connection established")

        # Week 12: Initialize Redis cache client
        if settings.enable_caching:
            logger.info("Initializing Redis cache client")
            await redis_client.initialize()

            # Test Redis connection
            redis_healthy = await redis_client.health_check()
            if redis_healthy:
                logger.info("Redis cache client initialized successfully")
            else:
                logger.warning("Redis cache client initialization failed - caching disabled")

        # Initialize rate limiter
        await rate_limiter.initialize()
        logger.info("Rate limiter initialized")

        # Initialize LangGraph workflow
        logger.info("Initializing LangGraph workflow")
        await initialize_workflow()
        logger.info("LangGraph workflow initialized")

        logger.info("Tech Spec Agent started successfully")

    except Exception as e:
        logger.error("Failed to start Tech Spec Agent", error=str(e))
        raise

    yield

    # Shutdown
    logger.info("Shutting down Tech Spec Agent")

    try:
        # Close database connections
        await db_manager.close_async_engine()
        logger.info("Database connections closed")

        # Week 12: Close Redis cache client
        if settings.enable_caching:
            await redis_client.close()
            logger.info("Redis cache client closed")

        # Close rate limiter
        await rate_limiter.close()
        logger.info("Rate limiter closed")

        logger.info("Tech Spec Agent shutdown complete")

    except Exception as e:
        logger.error("Error during shutdown", error=str(e))


# Create FastAPI application
app = FastAPI(
    title="Tech Spec Agent API",
    description="Technical Specification Agent for ANYON Platform - Automated TRD Generation",
    version="1.0.0",
    docs_url="/docs" if settings.is_development else None,  # Disable in production
    redoc_url="/redoc" if settings.is_development else None,
    lifespan=lifespan,
)


# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Auth middleware to set request.state.user for per-user rate limiting
@app.middleware("http")
async def auth_middleware(request, call_next):
    """
    Middleware to extract user from JWT and set request.state.user.
    This enables per-user rate limiting.
    """
    from src.api.auth import decode_access_token, User

    # Try to extract JWT token
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        try:
            payload = decode_access_token(token)
            if payload:
                # Create minimal user object
                request.state.user = User(
                    user_id=payload.get("user_id", ""),
                    email=payload.get("email", ""),
                    role=payload.get("role", "user"),
                    permissions=payload.get("permissions", [])
                )
            else:
                request.state.user = None
        except Exception:
            # Invalid token - continue without user
            request.state.user = None
    else:
        request.state.user = None

    response = await call_next(request)
    return response


# Add rate limiting middleware
app.middleware("http")(rate_limit_middleware)

# Register error handlers
register_error_handlers(app)

# Register API routers
app.include_router(api_router, tags=["Tech Spec API"])
app.include_router(workflow_router, tags=["Workflow Control"])
app.include_router(websocket_router, tags=["WebSocket"])


# ============= API Endpoints =============

@app.get("/health")
async def health_check() -> Dict:
    """
    Health check endpoint for orchestration and monitoring.

    Returns:
        {
            "status": "healthy" | "unhealthy",
            "service": "tech-spec-agent",
            "version": "1.0.0",
            "environment": "development" | "staging" | "production",
            "database": "connected" | "disconnected",
            "redis": "connected" | "disconnected"
        }
    """
    health_status = {
        "status": "healthy",
        "service": "tech-spec-agent",
        "version": "1.0.0",
        "environment": settings.environment,
    }

    try:
        # Check database
        db_healthy = await db_manager.check_connection()
        health_status["database"] = "connected" if db_healthy else "disconnected"

        if not db_healthy:
            health_status["status"] = "unhealthy"

        # Week 12: Check Redis cache health
        if settings.enable_caching:
            redis_healthy = await redis_client.health_check()
            health_status["redis"] = "connected" if redis_healthy else "disconnected"

            if not redis_healthy:
                logger.warning("Redis cache health check failed")
                # Don't mark as unhealthy - caching is optional
        else:
            health_status["redis"] = "disabled"

    except Exception as e:
        logger.error("Health check error", error=str(e))
        health_status["status"] = "unhealthy"
        health_status["error"] = str(e)

    # Return 503 if unhealthy
    if health_status["status"] == "unhealthy":
        return JSONResponse(
            status_code=503,
            content=health_status
        )

    return health_status


@app.get("/")
async def root() -> Dict:
    """Root endpoint with API information."""
    return {
        "service": "Tech Spec Agent",
        "version": "1.0.0",
        "description": "Technical Specification Agent for ANYON Platform",
        "docs": "/docs" if settings.is_development else "Documentation disabled in production",
        "health": "/health",
        "metrics": "/metrics" if settings.prometheus_enabled else "Metrics disabled",
    }


@app.get("/metrics")
async def metrics() -> Response:
    """
    Prometheus metrics endpoint.

    Week 12: Performance monitoring with Prometheus metrics.

    Returns:
        Prometheus metrics in text format
    """
    if not settings.prometheus_enabled:
        return JSONResponse(
            status_code=404,
            content={"error": "Metrics disabled"}
        )

    # Generate Prometheus metrics
    metrics_output = generate_latest()

    return Response(
        content=metrics_output,
        media_type=CONTENT_TYPE_LATEST
    )


# ============= Error Handlers =============

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for unhandled errors."""
    logger.error(
        "Unhandled exception",
        error=str(exc),
        path=request.url.path,
        method=request.method,
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": str(exc) if settings.is_development else "An unexpected error occurred",
        }
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.reload and settings.is_development,
        log_level=settings.log_level.lower(),
    )
