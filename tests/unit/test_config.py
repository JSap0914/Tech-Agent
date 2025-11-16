"""Unit tests for configuration management."""

import pytest
from src.config import Settings


def test_settings_load_from_env():
    """Test that settings load from environment variables."""
    # This will use .env if present
    settings = Settings()

    assert settings.environment in ["development", "staging", "production"]
    assert settings.log_level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    assert settings.db_pool_size > 0
    assert settings.jwt_algorithm == "HS256"


def test_settings_validation():
    """Test settings validation."""
    with pytest.raises(ValueError):
        # Invalid environment
        Settings(
            database_url="postgresql+asyncpg://test",
            database_url_sync="postgresql://test",
            anthropic_api_key="test",
            openai_api_key="test",
            tavily_api_key="test",
            anyon_api_base_url="http://test",
            anyon_webhook_secret="test",
            anyon_frontend_url="http://test",
            jwt_secret_key="test",
            environment="invalid"
        )


def test_settings_properties():
    """Test settings helper properties."""
    # Development environment
    settings = Settings(
        database_url="postgresql+asyncpg://test",
        database_url_sync="postgresql://test",
        anthropic_api_key="test",
        openai_api_key="test",
        tavily_api_key="test",
        anyon_api_base_url="http://test",
        anyon_webhook_secret="test",
        anyon_frontend_url="http://test",
        jwt_secret_key="test",
        environment="development"
    )

    assert settings.is_development is True
    assert settings.is_production is False

    # Production environment
    settings.environment = "production"
    assert settings.is_development is False
    assert settings.is_production is True


def test_cors_origins_parsing():
    """Test CORS origins are parsed correctly."""
    settings = Settings(
        database_url="postgresql+asyncpg://test",
        database_url_sync="postgresql://test",
        anthropic_api_key="test",
        openai_api_key="test",
        tavily_api_key="test",
        anyon_api_base_url="http://test",
        anyon_webhook_secret="test",
        anyon_frontend_url="http://test",
        jwt_secret_key="test",
        cors_allowed_origins="http://localhost:3000,https://anyon.platform"
    )

    assert isinstance(settings.cors_allowed_origins, list)
    assert len(settings.cors_allowed_origins) == 2
    assert "http://localhost:3000" in settings.cors_allowed_origins
