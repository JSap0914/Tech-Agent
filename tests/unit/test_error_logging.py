"""
Unit tests for error logging to agent_error_logs table.

Tests the fix for Week 5 Issue #4: Error log persistence.
"""

import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime

from src.langgraph.error_logging import (
    log_error_to_db,
    log_state_errors_to_db,
    get_session_errors,
    count_session_errors
)


@pytest.mark.asyncio
@patch('src.langgraph.error_logging.get_db_connection')
async def test_log_error_to_db(mock_db):
    """Test logging a single error to database."""
    # Mock database connection
    mock_conn = AsyncMock()
    mock_conn.execute = AsyncMock()

    mock_db.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_db.return_value.__aexit__ = AsyncMock()

    # Create test error
    test_error = ValueError("Test error message")

    # Log error
    result = await log_error_to_db(
        session_id="test-session-123",
        node_name="generate_trd",
        error=test_error,
        context={"iteration": 2},
        recoverable=True
    )

    # Verify
    assert result is True
    assert mock_conn.execute.called

    # Check SQL parameters
    call_args = mock_conn.execute.call_args
    assert "test-session-123" in call_args[0]
    assert "generate_trd" in call_args[0]
    assert "ValueError" in call_args[0]
    assert "Test error message" in call_args[0]


@pytest.mark.asyncio
@patch('src.langgraph.error_logging.get_db_connection')
async def test_log_state_errors_to_db(mock_db):
    """Test logging multiple errors from state["errors"]."""
    # Mock database connection
    mock_conn = AsyncMock()
    mock_conn.execute = AsyncMock()

    mock_db.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_db.return_value.__aexit__ = AsyncMock()

    # Create test errors
    state_errors = [
        {
            "node": "generate_trd",
            "error_type": "ValueError",
            "message": "Error 1",
            "timestamp": datetime.now().isoformat(),
            "recoverable": True
        },
        {
            "node": "validate_trd",
            "error_type": "ValidationError",
            "message": "Error 2",
            "timestamp": datetime.now().isoformat(),
            "recoverable": False
        }
    ]

    # Log errors
    logged_count = await log_state_errors_to_db("test-session", state_errors)

    # Verify
    assert logged_count == 2
    assert mock_conn.execute.call_count == 2

    # Verify errors are marked as logged
    assert state_errors[0]["_logged"] is True
    assert state_errors[1]["_logged"] is True


@pytest.mark.asyncio
@patch('src.langgraph.error_logging.get_db_connection')
async def test_log_state_errors_skips_already_logged(mock_db):
    """Test that already logged errors are skipped."""
    mock_conn = AsyncMock()
    mock_conn.execute = AsyncMock()

    mock_db.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_db.return_value.__aexit__ = AsyncMock()

    # Create errors with one already logged
    state_errors = [
        {
            "node": "node1",
            "error_type": "Error",
            "message": "Already logged",
            "timestamp": datetime.now().isoformat(),
            "_logged": True  # Already logged
        },
        {
            "node": "node2",
            "error_type": "Error",
            "message": "New error",
            "timestamp": datetime.now().isoformat()
        }
    ]

    # Log errors
    logged_count = await log_state_errors_to_db("test-session", state_errors)

    # Verify only 1 was logged (the new one)
    assert logged_count == 1
    assert mock_conn.execute.call_count == 1


@pytest.mark.asyncio
@patch('src.langgraph.error_logging.get_db_connection')
async def test_get_session_errors(mock_db):
    """Test retrieving errors for a session."""
    # Mock database connection
    mock_conn = AsyncMock()
    mock_conn.fetch = AsyncMock(return_value=[
        {
            "node_name": "generate_trd",
            "error_type": "ValueError",
            "error_message": "Test error",
            "stack_trace": None,
            "context": {},
            "recoverable": True,
            "occurred_at": datetime.now()
        }
    ])

    mock_db.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_db.return_value.__aexit__ = AsyncMock()

    # Get errors
    errors = await get_session_errors("test-session")

    # Verify
    assert len(errors) == 1
    assert errors[0]["node_name"] == "generate_trd"
    assert errors[0]["error_type"] == "ValueError"


@pytest.mark.asyncio
@patch('src.langgraph.error_logging.get_db_connection')
async def test_count_session_errors(mock_db):
    """Test counting session errors."""
    # Mock database connection
    mock_conn = AsyncMock()
    mock_conn.fetchrow = AsyncMock(return_value={
        "total": 5,
        "recoverable": 3,
        "critical": 2,
        "affected_nodes": 3
    })

    mock_db.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_db.return_value.__aexit__ = AsyncMock()

    # Count errors
    stats = await count_session_errors("test-session")

    # Verify
    assert stats["total"] == 5
    assert stats["recoverable"] == 3
    assert stats["critical"] == 2
    assert stats["affected_nodes"] == 3


@pytest.mark.asyncio
@patch('src.langgraph.error_logging.get_db_connection')
async def test_log_error_handles_db_failure(mock_db):
    """Test that database failures are handled gracefully."""
    # Mock database to raise exception
    mock_db.return_value.__aenter__ = AsyncMock(
        side_effect=Exception("Database connection failed")
    )

    # Log error should not raise, but return False
    result = await log_error_to_db(
        session_id="test-session",
        node_name="test_node",
        error=ValueError("Test"),
        recoverable=True
    )

    # Verify it failed gracefully
    assert result is False


@pytest.mark.asyncio
async def test_empty_errors_list():
    """Test that empty errors list is handled correctly."""
    # Should return 0 without attempting DB operations
    logged_count = await log_state_errors_to_db("test-session", [])
    assert logged_count == 0
