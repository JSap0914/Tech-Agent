"""
Redis-based rate limiting for API endpoints.
Implements sliding window rate limiting.
"""

from typing import Optional
from datetime import timedelta
from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
import redis.asyncio as redis
import structlog

from src.config import settings

logger = structlog.get_logger(__name__)


# ============= Redis Client =============

class RedisRateLimiter:
    """Redis-based rate limiter using sliding window algorithm."""

    def __init__(self):
        """Initialize Redis connection."""
        self._redis: Optional[redis.Redis] = None

    async def initialize(self):
        """Initialize Redis connection pool."""
        if not settings.redis_enabled:
            logger.warning("Redis disabled - rate limiting will be bypassed")
            return

        try:
            # Parse Redis URL
            self._redis = redis.from_url(
                settings.redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_keepalive=True,
                max_connections=settings.redis_max_connections
            )

            # Test connection
            await self._redis.ping()
            logger.info("Redis connection established",
                       redis_url=settings.redis_url)

        except Exception as e:
            logger.error("Failed to connect to Redis", error=str(e))
            self._redis = None

    async def close(self):
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()
            logger.info("Redis connection closed")

    async def check_rate_limit(
        self,
        key: str,
        max_requests: int,
        window_seconds: int
    ) -> tuple[bool, int, int]:
        """
        Check if request is within rate limit using sliding window.

        Args:
            key: Rate limit key (e.g., user_id or IP address)
            max_requests: Maximum requests allowed in window
            window_seconds: Time window in seconds

        Returns:
            Tuple of (is_allowed, remaining_requests, reset_time_seconds)
        """
        if not self._redis:
            # If Redis unavailable, allow request
            return True, max_requests, 0

        try:
            # Use Redis sorted set with scores as timestamps
            now = await self._get_current_timestamp()
            window_start = now - window_seconds

            # Redis Lua script for atomic rate limiting
            lua_script = """
            local key = KEYS[1]
            local now = tonumber(ARGV[1])
            local window_start = tonumber(ARGV[2])
            local max_requests = tonumber(ARGV[3])
            local window_seconds = tonumber(ARGV[4])

            -- Remove old entries outside the window
            redis.call('ZREMRANGEBYSCORE', key, '-inf', window_start)

            -- Count current requests in window
            local current_requests = redis.call('ZCARD', key)

            if current_requests < max_requests then
                -- Add current request
                redis.call('ZADD', key, now, now)
                redis.call('EXPIRE', key, window_seconds)
                return {1, max_requests - current_requests - 1, window_seconds}
            else
                -- Rate limit exceeded
                local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')[2]
                local reset_time = math.ceil(oldest + window_seconds - now)
                return {0, 0, reset_time}
            end
            """

            result = await self._redis.eval(
                lua_script,
                1,
                f"ratelimit:{key}",
                now,
                window_start,
                max_requests,
                window_seconds
            )

            is_allowed = result[0] == 1
            remaining = int(result[1])
            reset_time = int(result[2])

            if not is_allowed:
                logger.warning(
                    "Rate limit exceeded",
                    key=key,
                    max_requests=max_requests,
                    window_seconds=window_seconds,
                    reset_in_seconds=reset_time
                )

            return is_allowed, remaining, reset_time

        except Exception as e:
            logger.error("Rate limit check failed", error=str(e))
            # On error, allow request (fail open)
            return True, max_requests, 0

    async def _get_current_timestamp(self) -> int:
        """Get current Unix timestamp from Redis."""
        time_info = await self._redis.time()
        return int(time_info[0])


# Global rate limiter instance
rate_limiter = RedisRateLimiter()


# ============= Rate Limit Middleware =============

async def rate_limit_middleware(request: Request, call_next):
    """
    Middleware for global rate limiting.

    Args:
        request: FastAPI request object
        call_next: Next middleware/handler in chain

    Returns:
        Response from next handler or rate limit error
    """
    # Skip rate limiting for health check
    if request.url.path == "/health":
        return await call_next(request)

    # Extract identifier (prefer user_id from auth, fallback to IP)
    identifier = _extract_identifier(request)

    # Check global rate limit
    is_allowed, remaining, reset_time = await rate_limiter.check_rate_limit(
        key=f"global:{identifier}",
        max_requests=settings.rate_limit_global_requests,
        window_seconds=settings.rate_limit_window_seconds
    )

    if not is_allowed:
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "error": "RateLimitExceeded",
                "detail": f"Too many requests. Try again in {reset_time} seconds.",
                "retry_after": reset_time
            },
            headers={
                "Retry-After": str(reset_time),
                "X-RateLimit-Limit": str(settings.rate_limit_global_requests),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(reset_time)
            }
        )

    # Add rate limit headers to response
    response = await call_next(request)

    response.headers["X-RateLimit-Limit"] = str(settings.rate_limit_global_requests)
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    response.headers["X-RateLimit-Reset"] = str(reset_time)

    return response


# ============= Per-User Rate Limiter Dependency =============

class UserRateLimiter:
    """Dependency for per-user rate limiting."""

    def __init__(
        self,
        max_requests: int = 100,
        window_seconds: int = 60
    ):
        """
        Initialize user rate limiter.

        Args:
            max_requests: Maximum requests per user in window
            window_seconds: Time window in seconds
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds

    async def __call__(self, request: Request) -> None:
        """
        Check per-user rate limit.

        Args:
            request: FastAPI request object

        Raises:
            HTTPException: If rate limit exceeded
        """
        # Extract user identifier
        identifier = _extract_identifier(request)

        # Check user-specific rate limit
        is_allowed, remaining, reset_time = await rate_limiter.check_rate_limit(
            key=f"user:{identifier}",
            max_requests=self.max_requests,
            window_seconds=self.window_seconds
        )

        if not is_allowed:
            logger.warning(
                "User rate limit exceeded",
                identifier=identifier,
                limit=self.max_requests,
                window=self.window_seconds
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"User rate limit exceeded. Try again in {reset_time} seconds.",
                headers={
                    "Retry-After": str(reset_time),
                    "X-RateLimit-Limit": str(self.max_requests),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset_time)
                }
            )


# ============= Helper Functions =============

def _extract_identifier(request: Request) -> str:
    """
    Extract identifier for rate limiting from request.
    Prefers user_id from JWT, falls back to client IP.

    Args:
        request: FastAPI request object

    Returns:
        Identifier string (user_id or IP address)
    """
    # Try to get user_id from request state (set by auth middleware)
    if hasattr(request.state, "user") and request.state.user:
        return str(request.state.user.user_id)

    # Fallback to client IP
    client_host = request.client.host if request.client else "unknown"

    # Check for X-Forwarded-For header (proxy/load balancer)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Use first IP in the chain
        client_host = forwarded_for.split(",")[0].strip()

    return f"ip:{client_host}"


# ============= Predefined Rate Limiters =============

# Standard user rate limit: 100 requests per minute
standard_rate_limit = UserRateLimiter(
    max_requests=100,
    window_seconds=60
)

# Strict rate limit for expensive operations: 10 requests per minute
strict_rate_limit = UserRateLimiter(
    max_requests=10,
    window_seconds=60
)

# Generous rate limit for read-only operations: 500 requests per minute
generous_rate_limit = UserRateLimiter(
    max_requests=500,
    window_seconds=60
)
