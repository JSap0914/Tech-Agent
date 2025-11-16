"""Unit tests for database connection manager."""

import pytest
from src.database.connection import DatabaseManager
from src.config import settings


def test_database_manager_singleton():
    """Test that database manager is a singleton."""
    from src.database.connection import db_manager

    assert db_manager is not None
    assert isinstance(db_manager, DatabaseManager)


def test_database_manager_initialization():
    """Test database manager can be initialized."""
    manager = DatabaseManager()

    assert manager._async_engine is None
    assert manager._sync_engine is None
    assert manager._initialized is False


def test_async_engine_initialization():
    """Test async engine initialization."""
    manager = DatabaseManager()

    # Initialize engine
    manager.initialize_async_engine()

    assert manager._async_engine is not None
    assert manager._async_session_maker is not None
    assert manager._initialized is True

    # Cleanup
    import asyncio
    asyncio.run(manager.close_async_engine())


def test_sync_engine_initialization():
    """Test sync engine initialization."""
    manager = DatabaseManager()

    # Initialize engine
    manager.initialize_sync_engine()

    assert manager._sync_engine is not None
    assert manager._sync_session_maker is not None

    # Cleanup
    manager.close_sync_engine()


@pytest.mark.asyncio
async def test_get_async_session():
    """Test async session context manager."""
    manager = DatabaseManager()
    manager.initialize_async_engine()

    try:
        async with manager.get_async_session() as session:
            assert session is not None
    finally:
        await manager.close_async_engine()


@pytest.mark.asyncio
async def test_session_without_initialization():
    """Test that session fails without initialization."""
    manager = DatabaseManager()

    with pytest.raises(RuntimeError):
        async with manager.get_async_session() as session:
            pass
