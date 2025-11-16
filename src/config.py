"""
Configuration management for Tech Spec Agent.
Uses Pydantic Settings for type-safe environment variable loading.
"""

from typing import List
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ============= Database =============
    database_url: str = Field(..., description="Async PostgreSQL connection string")
    database_url_sync: str = Field(..., description="Sync PostgreSQL connection string for Alembic")
    db_pool_size: int = Field(default=20, description="Database connection pool size")
    db_max_overflow: int = Field(default=10, description="Max connections beyond pool size")
    db_pool_timeout: int = Field(default=30, description="Pool checkout timeout in seconds")
    db_pool_recycle: int = Field(default=3600, description="Connection recycle time in seconds")

    # ============= LLM APIs =============
    anthropic_api_key: str = Field(..., description="Anthropic API key for Claude")
    openai_api_key: str = Field(..., description="OpenAI API key for Google AI Studio")
    openai_org_id: str = Field(default="", description="OpenAI organization ID")

    # ============= External Services =============
    redis_url: str = Field(default="redis://localhost:6379/0", description="Redis connection URL")
    redis_max_connections: int = Field(default=50, description="Redis connection pool size")
    tavily_api_key: str = Field(..., description="Tavily API key for web search")

    # ============= Tech Spec Agent Configuration =============
    tech_spec_session_timeout: int = Field(default=3600, description="Session timeout in seconds")
    tech_spec_max_retries: int = Field(default=3, description="Max retry attempts for failed operations")
    tech_spec_max_iterations: int = Field(default=3, description="Max TRD generation iterations")

    tech_spec_web_search_timeout: int = Field(default=30, description="Web search timeout in seconds")
    tech_spec_min_options_per_gap: int = Field(default=2, description="Minimum technology options per gap")
    tech_spec_max_options_per_gap: int = Field(default=3, description="Maximum technology options per gap")
    tech_spec_cache_ttl: int = Field(default=86400, description="Cache TTL in seconds (24 hours)")

    tech_spec_trd_validation_threshold: float = Field(default=90.0, description="Minimum TRD quality score")
    tech_spec_max_trd_generation_retries: int = Field(default=2, description="Max TRD regeneration attempts")

    tech_spec_max_components_to_parse: int = Field(default=100, description="Max components to parse from code")
    tech_spec_parse_timeout: int = Field(default=10, description="Code parsing timeout in seconds")

    # ============= ANYON Platform Integration =============
    anyon_api_base_url: str = Field(..., description="ANYON platform API base URL")
    anyon_webhook_secret: str = Field(..., description="ANYON webhook secret for verification")
    anyon_frontend_url: str = Field(..., description="ANYON frontend URL for CORS")

    # ============= Security =============
    jwt_secret_key: str = Field(..., description="JWT secret key for token signing")
    jwt_algorithm: str = Field(default="HS256", description="JWT algorithm")
    jwt_access_token_expire_minutes: int = Field(default=60, description="JWT expiration time")
    jwt_expiration_minutes: int = Field(default=60, description="JWT expiration time (alias)")

    cors_allowed_origins: str = Field(
        default="https://anyon.platform,http://localhost:3000",
        description="Comma-separated CORS allowed origins"
    )
    cors_allow_credentials: bool = Field(default=True, description="Allow CORS credentials")

    # ============= WebSocket =============
    websocket_base_url: str = Field(
        default="wss://anyon.platform",
        description="WebSocket base URL for real-time connections"
    )

    # ============= Monitoring & Logging =============
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(default="json", description="Log format (json or text)")
    structlog_enabled: bool = Field(default=True, description="Enable structured logging")

    prometheus_enabled: bool = Field(default=True, description="Enable Prometheus metrics")
    prometheus_port: int = Field(default=9090, description="Prometheus metrics port")

    langsmith_enabled: bool = Field(default=False, description="Enable LangSmith tracing")
    langsmith_api_key: str = Field(default="", description="LangSmith API key")
    langsmith_project: str = Field(default="tech-spec-agent", description="LangSmith project name")

    # ============= Feature Flags =============
    enable_rate_limiting: bool = Field(default=True, description="Enable rate limiting")
    rate_limit_per_minute: int = Field(default=100, description="Rate limit per user per minute")
    rate_limit_global_per_minute: int = Field(default=1000, description="Global rate limit per minute")
    rate_limit_global_requests: int = Field(default=1000, description="Global rate limit requests")
    rate_limit_window_seconds: int = Field(default=60, description="Rate limit window in seconds")

    enable_caching: bool = Field(default=True, description="Enable Redis caching")
    redis_enabled: bool = Field(default=True, description="Enable Redis (alias)")
    enable_web_search: bool = Field(default=True, description="Enable web search for technology research")
    enable_error_recovery: bool = Field(default=True, description="Enable automatic error recovery")

    # ============= Environment =============
    environment: str = Field(default="development", description="Environment (development/staging/production)")
    debug: bool = Field(default=False, description="Enable debug mode")
    reload: bool = Field(default=True, description="Enable auto-reload (dev only)")
    testing: bool = Field(default=False, description="Testing mode flag")
    test_database_url: str = Field(default="", description="Test database URL")

    @field_validator("cors_allowed_origins")
    @classmethod
    def parse_cors_origins(cls, v: str) -> List[str]:
        """Parse comma-separated CORS origins into list."""
        return [origin.strip() for origin in v.split(",") if origin.strip()]

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level is one of the allowed values."""
        allowed = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v_upper = v.upper()
        if v_upper not in allowed:
            raise ValueError(f"log_level must be one of {allowed}")
        return v_upper

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Validate environment is one of the allowed values."""
        allowed = ["development", "staging", "production"]
        v_lower = v.lower()
        if v_lower not in allowed:
            raise ValueError(f"environment must be one of {allowed}")
        return v_lower

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment == "development"

    @property
    def is_testing(self) -> bool:
        """Check if running in testing mode."""
        return self.testing or self.environment == "testing"


# Global settings instance
settings = Settings()
