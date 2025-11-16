"""
Database connection management for Tech Spec Agent.
Adapted from Design Agent patterns with async support.
"""

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from sqlalchemy import create_engine, Engine, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool
from sqlalchemy.engine.url import make_url
import structlog

from src.config import settings

logger = structlog.get_logger(__name__)


class DatabaseManager:
    """
    Manages database connections for Tech Spec Agent.
    Supports both async (runtime) and sync (migrations) connections.
    """

    def __init__(self):
        self._async_engine: Optional[AsyncEngine] = None
        self._sync_engine: Optional[Engine] = None
        self._async_session_maker: Optional[async_sessionmaker] = None
        self._sync_session_maker: Optional[sessionmaker] = None
        self._initialized = False

    def initialize_async_engine(self) -> None:
        """
        Initialize async database engine for runtime operations.
        Should be called once at application startup.
        """
        if self._async_engine is not None:
            logger.warning("Async engine already initialized")
            return

        try:
            # Parse and validate database URL
            parsed_url = make_url(settings.database_url)
            logger.info(
                "Initializing async database engine",
                host=parsed_url.host,
                port=parsed_url.port,
                database=parsed_url.database,
            )

            # Create async engine with connection pooling
            self._async_engine = create_async_engine(
                settings.database_url,
                pool_size=settings.db_pool_size,
                max_overflow=settings.db_max_overflow,
                pool_timeout=settings.db_pool_timeout,
                pool_recycle=settings.db_pool_recycle,
                pool_pre_ping=True,  # Verify connections before using
                echo=settings.debug,  # Log SQL in debug mode
            )

            # Create session maker
            self._async_session_maker = async_sessionmaker(
                self._async_engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )

            self._initialized = True
            logger.info("Async database engine initialized successfully")

        except Exception as e:
            logger.error("Failed to initialize async database engine", error=str(e))
            raise

    def initialize_sync_engine(self) -> None:
        """
        Initialize sync database engine for Alembic migrations.
        Only needed when running migrations.
        """
        if self._sync_engine is not None:
            logger.warning("Sync engine already initialized")
            return

        try:
            logger.info("Initializing sync database engine")

            self._sync_engine = create_engine(
                settings.database_url_sync,
                pool_size=5,
                max_overflow=10,
                pool_pre_ping=True,
                echo=settings.debug,
            )

            self._sync_session_maker = sessionmaker(
                self._sync_engine,
                class_=Session,
                expire_on_commit=False,
            )

            logger.info("Sync database engine initialized successfully")

        except Exception as e:
            logger.error("Failed to initialize sync database engine", error=str(e))
            raise

    @asynccontextmanager
    async def get_async_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Context manager for async database sessions.

        Usage:
            async with db_manager.get_async_session() as session:
                result = await session.execute(query)
                await session.commit()
        """
        if not self._initialized or self._async_session_maker is None:
            raise RuntimeError(
                "Async engine not initialized. Call initialize_async_engine() first."
            )

        session = self._async_session_maker()
        try:
            yield session
        except Exception as e:
            await session.rollback()
            logger.error("Database session error", error=str(e))
            raise
        finally:
            await session.close()

    def get_sync_session(self) -> Session:
        """
        Get sync database session for migrations.

        Usage:
            with db_manager.get_sync_session() as session:
                result = session.execute(query)
                session.commit()
        """
        if self._sync_session_maker is None:
            raise RuntimeError(
                "Sync engine not initialized. Call initialize_sync_engine() first."
            )

        return self._sync_session_maker()

    async def close_async_engine(self) -> None:
        """Close async database engine and all connections."""
        if self._async_engine:
            logger.info("Closing async database engine")
            await self._async_engine.dispose()
            self._async_engine = None
            self._async_session_maker = None
            self._initialized = False
            logger.info("Async database engine closed")

    def close_sync_engine(self) -> None:
        """Close sync database engine."""
        if self._sync_engine:
            logger.info("Closing sync database engine")
            self._sync_engine.dispose()
            self._sync_engine = None
            self._sync_session_maker = None
            logger.info("Sync database engine closed")

    async def check_connection(self) -> bool:
        """
        Check if database connection is healthy.
        Returns True if connection is successful.
        """
        try:
            async with self.get_async_session() as session:
                await session.execute(text("SELECT 1"))
                return True
        except Exception as e:
            logger.error("Database health check failed", error=str(e))
            return False

    @property
    def async_engine(self) -> Optional[AsyncEngine]:
        """Get async engine instance."""
        return self._async_engine

    @property
    def sync_engine(self) -> Optional[Engine]:
        """Get sync engine instance."""
        return self._sync_engine


# Global database manager instance
db_manager = DatabaseManager()


# ============= Helper Functions =============

@asynccontextmanager
async def get_db_connection():
    """
    Helper function for direct asyncpg-style database connections.

    This is a wrapper around SQLAlchemy's async session that provides
    a connection object compatible with asyncpg execute() patterns.

    Usage:
        async with get_db_connection() as conn:
            await conn.execute("SELECT * FROM table")
            await conn.fetch("SELECT * FROM table")
    """
    async with db_manager.get_async_session() as session:
        # Get the underlying connection from SQLAlchemy session
        async with session.begin():
            conn = await session.connection()
            # Yield the raw connection for asyncpg-style operations
            yield conn.connection
