"""
Unit tests for Redis cache client (Week 12).
Tests caching functionality for technology research and code analysis.
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import json

from src.cache.redis_client import RedisClient


@pytest.fixture
def redis_client():
    """Create Redis client instance for testing."""
    return RedisClient()


@pytest.mark.asyncio
class TestRedisClientInitialization:
    """Test Redis client initialization and connection management."""

    async def test_initialize_creates_connection_pool(self, redis_client):
        """Test that initialization creates connection pool."""
        with patch("src.cache.redis_client.ConnectionPool") as mock_pool_class:
            with patch("src.cache.redis_client.redis.Redis") as mock_redis_class:
                mock_pool = MagicMock()
                mock_pool_class.from_url.return_value = mock_pool

                mock_redis_instance = AsyncMock()
                mock_redis_instance.ping = AsyncMock()
                mock_redis_class.return_value = mock_redis_instance

                await redis_client.initialize()

                # Verify pool was created
                mock_pool_class.from_url.assert_called_once()
                # Verify Redis client was created with pool
                mock_redis_class.assert_called_once_with(connection_pool=mock_pool)
                # Verify ping was called to test connection
                mock_redis_instance.ping.assert_called_once()

    async def test_initialize_when_already_initialized(self, redis_client, caplog):
        """Test that re-initialization logs warning."""
        with patch("src.cache.redis_client.ConnectionPool"):
            with patch("src.cache.redis_client.redis.Redis") as mock_redis_class:
                mock_redis_instance = AsyncMock()
                mock_redis_instance.ping = AsyncMock()
                mock_redis_class.return_value = mock_redis_instance

                # Initialize twice
                await redis_client.initialize()
                await redis_client.initialize()

                # Should log warning
                assert "already initialized" in caplog.text.lower()

    async def test_initialize_when_caching_disabled(self, redis_client):
        """Test initialization when caching is disabled in settings."""
        with patch("src.cache.redis_client.settings") as mock_settings:
            mock_settings.enable_caching = False

            await redis_client.initialize()

            # Should not create client
            assert redis_client._client is None

    async def test_initialize_connection_failure_graceful(self, redis_client, caplog):
        """Test that connection failure doesn't crash, just logs error."""
        with patch("src.cache.redis_client.ConnectionPool") as mock_pool_class:
            mock_pool_class.from_url.side_effect = Exception("Connection failed")

            # Should not raise exception
            await redis_client.initialize()

            # Should log error
            assert "failed to initialize" in caplog.text.lower()
            # Client should be None
            assert redis_client._client is None


@pytest.mark.asyncio
class TestRedisClientOperations:
    """Test basic Redis operations (get, set, delete)."""

    async def test_get_cache_hit(self, redis_client):
        """Test successful cache retrieval."""
        test_data = {"key": "value", "number": 42}

        redis_client._client = AsyncMock()
        redis_client._client.get = AsyncMock(return_value=json.dumps(test_data))

        result = await redis_client.get("test_key")

        assert result == test_data
        redis_client._client.get.assert_called_once_with("test_key")

    async def test_get_cache_miss(self, redis_client):
        """Test cache miss returns None."""
        redis_client._client = AsyncMock()
        redis_client._client.get = AsyncMock(return_value=None)

        result = await redis_client.get("nonexistent_key")

        assert result is None

    async def test_get_when_client_not_initialized(self, redis_client):
        """Test get returns None when client not initialized."""
        redis_client._client = None

        result = await redis_client.get("test_key")

        assert result is None

    async def test_get_handles_json_decode_error(self, redis_client):
        """Test get handles invalid JSON gracefully."""
        redis_client._client = AsyncMock()
        redis_client._client.get = AsyncMock(return_value="invalid json {")

        result = await redis_client.get("test_key")

        # Should return None on error (logged but not raised)
        assert result is None

    async def test_set_success(self, redis_client):
        """Test successful cache set."""
        test_data = {"foo": "bar"}

        redis_client._client = AsyncMock()
        redis_client._client.set = AsyncMock()

        with patch("src.cache.redis_client.settings") as mock_settings:
            mock_settings.tech_spec_cache_ttl = 86400

            result = await redis_client.set("test_key", test_data)

            assert result is True
            redis_client._client.set.assert_called_once()

            # Verify data was JSON serialized
            call_args = redis_client._client.set.call_args
            assert call_args[0][0] == "test_key"
            assert json.loads(call_args[0][1]) == test_data
            assert call_args[1]["ex"] == 86400

    async def test_set_with_custom_ttl(self, redis_client):
        """Test set with custom TTL."""
        redis_client._client = AsyncMock()
        redis_client._client.set = AsyncMock()

        await redis_client.set("test_key", {"data": "value"}, ttl=3600)

        call_args = redis_client._client.set.call_args
        assert call_args[1]["ex"] == 3600

    async def test_set_when_client_not_initialized(self, redis_client):
        """Test set returns False when client not initialized."""
        redis_client._client = None

        result = await redis_client.set("test_key", {"data": "value"})

        assert result is False

    async def test_delete_success(self, redis_client):
        """Test successful key deletion."""
        redis_client._client = AsyncMock()
        redis_client._client.delete = AsyncMock(return_value=1)

        result = await redis_client.delete("test_key")

        assert result is True
        redis_client._client.delete.assert_called_once_with("test_key")

    async def test_delete_key_not_exist(self, redis_client):
        """Test delete returns False when key doesn't exist."""
        redis_client._client = AsyncMock()
        redis_client._client.delete = AsyncMock(return_value=0)

        result = await redis_client.delete("nonexistent_key")

        assert result is False

    async def test_exists_true(self, redis_client):
        """Test exists returns True for existing key."""
        redis_client._client = AsyncMock()
        redis_client._client.exists = AsyncMock(return_value=1)

        result = await redis_client.exists("test_key")

        assert result is True

    async def test_exists_false(self, redis_client):
        """Test exists returns False for non-existing key."""
        redis_client._client = AsyncMock()
        redis_client._client.exists = AsyncMock(return_value=0)

        result = await redis_client.exists("nonexistent_key")

        assert result is False


@pytest.mark.asyncio
class TestDomainSpecificMethods:
    """Test domain-specific caching methods."""

    async def test_get_tech_research(self, redis_client):
        """Test technology research cache retrieval."""
        research_data = {
            "category": "authentication",
            "options": [{"name": "NextAuth.js", "pros": [], "cons": []}]
        }

        redis_client._client = AsyncMock()
        redis_client._client.get = AsyncMock(return_value=json.dumps(research_data))

        result = await redis_client.get_tech_research("authentication", "python")

        assert result == research_data
        # Verify cache key format
        redis_client._client.get.assert_called_once_with("tech_research:authentication:python")

    async def test_set_tech_research(self, redis_client):
        """Test technology research cache storage."""
        research_data = {"category": "database", "options": []}

        redis_client._client = AsyncMock()
        redis_client._client.set = AsyncMock()

        with patch("src.cache.redis_client.settings") as mock_settings:
            mock_settings.tech_spec_cache_ttl = 86400

            result = await redis_client.set_tech_research("database", research_data, "python")

            assert result is True
            call_args = redis_client._client.set.call_args
            assert call_args[0][0] == "tech_research:database:python"

    async def test_get_code_analysis(self, redis_client):
        """Test code analysis cache retrieval."""
        analysis_data = {
            "file_path": "/path/to/file.tsx",
            "api_calls": [{"url": "/api/users", "method": "GET"}]
        }

        redis_client._client = AsyncMock()
        redis_client._client.get = AsyncMock(return_value=json.dumps(analysis_data))

        file_hash = "abc123def456"
        result = await redis_client.get_code_analysis(file_hash)

        assert result == analysis_data
        redis_client._client.get.assert_called_once_with(f"code_analysis:{file_hash}")

    async def test_set_code_analysis(self, redis_client):
        """Test code analysis cache storage."""
        analysis_data = {"components": [], "api_calls": []}

        redis_client._client = AsyncMock()
        redis_client._client.set = AsyncMock()

        file_hash = "abc123def456"
        result = await redis_client.set_code_analysis(file_hash, analysis_data, ttl=3600)

        assert result is True
        call_args = redis_client._client.set.call_args
        assert call_args[0][0] == f"code_analysis:{file_hash}"
        assert call_args[1]["ex"] == 3600

    async def test_get_api_inference(self, redis_client):
        """Test API inference cache retrieval."""
        api_spec = {
            "endpoints": [
                {"method": "GET", "path": "/api/users"},
                {"method": "POST", "path": "/api/users"}
            ]
        }

        redis_client._client = AsyncMock()
        redis_client._client.get = AsyncMock(return_value=json.dumps(api_spec))

        result = await redis_client.get_api_inference("project_123")

        assert result == api_spec
        redis_client._client.get.assert_called_once_with("api_inference:project_123")

    async def test_set_api_inference(self, redis_client):
        """Test API inference cache storage."""
        api_spec = {"endpoints": []}

        redis_client._client = AsyncMock()
        redis_client._client.set = AsyncMock()

        result = await redis_client.set_api_inference("project_123", api_spec, ttl=7200)

        assert result is True
        call_args = redis_client._client.set.call_args
        assert call_args[0][0] == "api_inference:project_123"
        assert call_args[1]["ex"] == 7200


@pytest.mark.asyncio
class TestHealthCheck:
    """Test health check functionality."""

    async def test_health_check_healthy(self, redis_client):
        """Test health check returns True when Redis is healthy."""
        redis_client._client = AsyncMock()
        redis_client._client.ping = AsyncMock()

        result = await redis_client.health_check()

        assert result is True
        redis_client._client.ping.assert_called_once()

    async def test_health_check_unhealthy(self, redis_client):
        """Test health check returns False on connection error."""
        redis_client._client = AsyncMock()
        redis_client._client.ping = AsyncMock(side_effect=Exception("Connection failed"))

        result = await redis_client.health_check()

        assert result is False

    async def test_health_check_when_not_initialized(self, redis_client):
        """Test health check returns False when client not initialized."""
        redis_client._client = None

        result = await redis_client.health_check()

        assert result is False


@pytest.mark.asyncio
class TestCleanup:
    """Test cleanup and resource management."""

    async def test_close_closes_client_and_pool(self, redis_client):
        """Test close properly cleans up resources."""
        mock_client = AsyncMock()
        mock_pool = AsyncMock()

        redis_client._client = mock_client
        redis_client._pool = mock_pool

        await redis_client.close()

        # Verify cleanup
        mock_client.close.assert_called_once()
        mock_pool.disconnect.assert_called_once()
        assert redis_client._client is None
        assert redis_client._pool is None

    async def test_close_when_not_initialized(self, redis_client):
        """Test close handles None client gracefully."""
        redis_client._client = None
        redis_client._pool = None

        # Should not raise exception
        await redis_client.close()


@pytest.mark.asyncio
class TestMetricsIntegration:
    """Test Prometheus metrics integration."""

    async def test_get_tracks_cache_hit(self, redis_client):
        """Test that cache hits are tracked in metrics."""
        redis_client._client = AsyncMock()
        redis_client._client.get = AsyncMock(return_value=json.dumps({"data": "value"}))

        with patch("src.cache.redis_client.track_cache_hit") as mock_track_hit:
            await redis_client.get("test_key")

            mock_track_hit.assert_called_once()

    async def test_get_tracks_cache_miss(self, redis_client):
        """Test that cache misses are tracked in metrics."""
        redis_client._client = AsyncMock()
        redis_client._client.get = AsyncMock(return_value=None)

        with patch("src.cache.redis_client.track_cache_miss") as mock_track_miss:
            await redis_client.get("test_key")

            mock_track_miss.assert_called_once()

    async def test_set_tracks_success(self, redis_client):
        """Test that successful cache sets are tracked."""
        redis_client._client = AsyncMock()
        redis_client._client.set = AsyncMock()

        with patch("src.cache.redis_client.track_cache_set") as mock_track_set:
            with patch("src.cache.redis_client.settings") as mock_settings:
                mock_settings.tech_spec_cache_ttl = 86400

                await redis_client.set("test_key", {"data": "value"})

                mock_track_set.assert_called_once_with(success=True)

    async def test_set_tracks_failure(self, redis_client):
        """Test that failed cache sets are tracked."""
        redis_client._client = AsyncMock()
        redis_client._client.set = AsyncMock(side_effect=Exception("Set failed"))

        with patch("src.cache.redis_client.track_cache_set") as mock_track_set:
            await redis_client.set("test_key", {"data": "value"})

            mock_track_set.assert_called_once_with(success=False)
