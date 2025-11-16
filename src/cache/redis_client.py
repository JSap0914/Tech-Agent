"""
Redis caching client for Tech Spec Agent.
Provides caching for technology research results and parsed code data.
"""

import json
from typing import Any, Optional
import structlog
import redis.asyncio as redis
from redis.asyncio.connection import ConnectionPool

from src.config import settings
from src.monitoring import track_cache_hit, track_cache_miss, track_cache_set

logger = structlog.get_logger(__name__)


class RedisClient:
    """
    Async Redis client for caching technology research and code analysis.

    Cache Keys:
    - tech_research:{category}:{language} -> Technology research results
    - code_analysis:{file_hash} -> Parsed component data
    - api_inference:{project_id} -> Inferred API specifications
    """

    def __init__(self):
        self._pool: Optional[ConnectionPool] = None
        self._client: Optional[redis.Redis] = None
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize Redis connection pool."""
        if self._initialized:
            logger.warning("Redis client already initialized")
            return

        if not settings.enable_caching:
            logger.info("Caching disabled, skipping Redis initialization")
            return

        try:
            logger.info(
                "Initializing Redis client",
                url=settings.redis_url,
                max_connections=settings.redis_max_connections
            )

            # Create connection pool
            self._pool = ConnectionPool.from_url(
                settings.redis_url,
                max_connections=settings.redis_max_connections,
                decode_responses=True,  # Auto-decode bytes to str
                socket_timeout=5,
                socket_connect_timeout=5,
                retry_on_timeout=True,
            )

            # Create Redis client
            self._client = redis.Redis(connection_pool=self._pool)

            # Test connection
            await self._client.ping()

            self._initialized = True
            logger.info("Redis client initialized successfully")

        except Exception as e:
            logger.error("Failed to initialize Redis client", error=str(e), exc_info=True)
            # Don't fail app startup if Redis is unavailable
            # Caching will be skipped gracefully
            self._client = None

    async def close(self) -> None:
        """Close Redis connection and cleanup resources."""
        if self._client:
            logger.info("Closing Redis client")
            await self._client.close()
            self._client = None

        if self._pool:
            await self._pool.disconnect()
            self._pool = None

        self._initialized = False
        logger.info("Redis client closed")

    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value (parsed from JSON) or None if not found
        """
        if not self._client:
            return None

        try:
            value = await self._client.get(key)
            if value is None:
                logger.debug("Cache miss", key=key)
                track_cache_miss()  # Week 12: Metrics
                return None

            logger.debug("Cache hit", key=key)
            track_cache_hit()  # Week 12: Metrics
            return json.loads(value)

        except Exception as e:
            logger.warning("Redis get error", key=key, error=str(e))
            track_cache_miss()  # Week 12: Metrics (treat errors as misses)
            return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> bool:
        """
        Set value in cache with optional TTL.

        Args:
            key: Cache key
            value: Value to cache (will be JSON-serialized)
            ttl: Time-to-live in seconds (default: tech_spec_cache_ttl from config)

        Returns:
            True if successful, False otherwise
        """
        if not self._client:
            return False

        try:
            ttl_seconds = ttl if ttl is not None else settings.tech_spec_cache_ttl
            serialized = json.dumps(value)

            await self._client.set(key, serialized, ex=ttl_seconds)

            logger.debug(
                "Cache set",
                key=key,
                ttl=ttl_seconds,
                size=len(serialized)
            )
            track_cache_set(success=True)  # Week 12: Metrics
            return True

        except Exception as e:
            logger.warning("Redis set error", key=key, error=str(e))
            track_cache_set(success=False)  # Week 12: Metrics
            return False

    async def delete(self, key: str) -> bool:
        """
        Delete key from cache.

        Args:
            key: Cache key

        Returns:
            True if key was deleted, False otherwise
        """
        if not self._client:
            return False

        try:
            deleted = await self._client.delete(key)
            logger.debug("Cache delete", key=key, deleted=bool(deleted))
            return bool(deleted)

        except Exception as e:
            logger.warning("Redis delete error", key=key, error=str(e))
            return False

    async def exists(self, key: str) -> bool:
        """
        Check if key exists in cache.

        Args:
            key: Cache key

        Returns:
            True if key exists, False otherwise
        """
        if not self._client:
            return False

        try:
            exists = await self._client.exists(key)
            return bool(exists)

        except Exception as e:
            logger.warning("Redis exists error", key=key, error=str(e))
            return False

    async def get_tech_research(
        self,
        category: str,
        language: str = "python"
    ) -> Optional[dict]:
        """
        Get cached technology research results.

        Args:
            category: Technology category (e.g., "authentication", "database")
            language: Programming language

        Returns:
            Cached research results or None
        """
        key = f"tech_research:{category}:{language}"
        return await self.get(key)

    async def set_tech_research(
        self,
        category: str,
        research_results: dict,
        language: str = "python",
        ttl: Optional[int] = None
    ) -> bool:
        """
        Cache technology research results.

        Args:
            category: Technology category
            research_results: Research results to cache
            language: Programming language
            ttl: Cache TTL in seconds (default: 24 hours)

        Returns:
            True if successful
        """
        key = f"tech_research:{category}:{language}"
        return await self.set(key, research_results, ttl)

    async def health_check(self) -> bool:
        """
        Check Redis connection health.

        Returns:
            True if Redis is healthy, False otherwise
        """
        if not self._client:
            return False

        try:
            await self._client.ping()
            return True
        except Exception as e:
            logger.error("Redis health check failed", error=str(e))
            return False


# Global Redis client instance
redis_client = RedisClient()
