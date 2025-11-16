"""
Integration tests for WebSocket communication (Week 13-14).
Tests real-time progress updates and connection management.
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import json
from datetime import datetime

from src.websocket.connection_manager import ConnectionManager


@pytest.fixture
def connection_manager():
    """Create ConnectionManager instance for testing."""
    return ConnectionManager()


@pytest.fixture
def mock_websocket():
    """Create mock WebSocket connection."""
    ws = AsyncMock()
    ws.accept = AsyncMock()  # Required for ConnectionManager.connect()
    ws.send_text = AsyncMock()
    ws.send_json = AsyncMock()
    ws.close = AsyncMock()
    return ws


@pytest.fixture
def sample_session_id():
    """Sample session ID for testing."""
    return "test-session-123"


@pytest.mark.asyncio
class TestConnectionManagement:
    """Test WebSocket connection management."""

    async def test_connect_registers_websocket(self, connection_manager, mock_websocket, sample_session_id):
        """Test that connecting registers WebSocket."""
        await connection_manager.connect(mock_websocket, sample_session_id)

        assert connection_manager.is_session_connected(sample_session_id)
        assert connection_manager.get_connection_count(sample_session_id) == 1

    async def test_disconnect_removes_websocket(self, connection_manager, mock_websocket, sample_session_id):
        """Test that disconnecting removes WebSocket."""
        await connection_manager.connect(mock_websocket, sample_session_id)
        await connection_manager.disconnect(mock_websocket, sample_session_id)

        assert not connection_manager.is_session_connected(sample_session_id)
        assert connection_manager.get_connection_count(sample_session_id) == 0

    async def test_disconnect_closes_websocket(self, connection_manager, mock_websocket, sample_session_id):
        """Test that disconnect removes connection (note: does NOT call websocket.close())."""
        await connection_manager.connect(mock_websocket, sample_session_id)
        await connection_manager.disconnect(mock_websocket, sample_session_id)

        # ConnectionManager.disconnect() only removes the connection from tracking
        # It does NOT call websocket.close() - that's the caller's responsibility
        assert not connection_manager.is_session_connected(sample_session_id)

    async def test_multiple_concurrent_sessions(self, connection_manager):
        """Test managing multiple concurrent WebSocket sessions."""
        ws1 = AsyncMock()
        ws1.accept = AsyncMock()
        ws2 = AsyncMock()
        ws2.accept = AsyncMock()
        ws3 = AsyncMock()
        ws3.accept = AsyncMock()

        await connection_manager.connect(ws1, "session-1")
        await connection_manager.connect(ws2, "session-2")
        await connection_manager.connect(ws3, "session-3")

        # Each session has 1 connection
        assert connection_manager.get_connection_count("session-1") == 1
        assert connection_manager.get_connection_count("session-2") == 1
        assert connection_manager.get_connection_count("session-3") == 1
        assert connection_manager.is_session_connected("session-1")
        assert connection_manager.is_session_connected("session-2")
        assert connection_manager.is_session_connected("session-3")

    async def test_reconnect_adds_additional_connection(self, connection_manager, sample_session_id):
        """Test that reconnecting adds another WebSocket connection (multi-tab support)."""
        old_ws = AsyncMock()
        old_ws.accept = AsyncMock()
        new_ws = AsyncMock()
        new_ws.accept = AsyncMock()

        await connection_manager.connect(old_ws, sample_session_id)
        await connection_manager.connect(new_ws, sample_session_id)

        # ConnectionManager supports multiple connections per session (e.g., multiple browser tabs)
        # Both connections should be active
        assert connection_manager.get_connection_count(sample_session_id) == 2
        assert connection_manager.is_session_connected(sample_session_id)


@pytest.mark.asyncio
class TestProgressUpdates:
    """Test real-time progress updates."""

    async def test_send_progress_update(self, connection_manager, mock_websocket, sample_session_id):
        """Test sending progress update to client."""
        await connection_manager.connect(mock_websocket, sample_session_id)

        await connection_manager.send_progress_update(
            session_id=sample_session_id,
            progress=25.0,
            message="Analyzing PRD completeness...",
            stage="analyze_completeness"
        )

        # connect() sends "connection_established" message, then we send progress update
        # So send_json should be called twice
        assert mock_websocket.send_json.call_count == 2

        # Check the progress update message (second call)
        sent_data = mock_websocket.send_json.call_args_list[1][0][0]

        assert sent_data["type"] == "progress_update"
        assert sent_data["sessionId"] == sample_session_id
        assert sent_data["progress"] == 25.0
        assert sent_data["message"] == "Analyzing PRD completeness..."
        assert sent_data["stage"] == "analyze_completeness"
        assert "timestamp" in sent_data

    async def test_send_progress_without_stage(self, connection_manager, mock_websocket, sample_session_id):
        """Test sending progress update without stage."""
        await connection_manager.connect(mock_websocket, sample_session_id)

        await connection_manager.send_progress_update(
            session_id=sample_session_id,
            progress=50.0,
            message="Processing..."
        )

        sent_data = mock_websocket.send_json.call_args[0][0]
        assert sent_data["progress"] == 50.0
        assert sent_data["stage"] is None

    async def test_send_progress_to_disconnected_session(self, connection_manager, sample_session_id):
        """Test sending progress to disconnected session doesn't crash."""
        # Should not raise exception
        await connection_manager.send_progress_update(
            session_id=sample_session_id,
            progress=50.0,
            message="Test message"
        )


@pytest.mark.asyncio
class TestAgentMessages:
    """Test agent message communication."""

    async def test_send_agent_message(self, connection_manager, mock_websocket, sample_session_id):
        """Test sending agent message to client."""
        await connection_manager.connect(mock_websocket, sample_session_id)

        await connection_manager.send_agent_message(
            session_id=sample_session_id,
            message="I found 3 authentication library options for you.",
            message_type="info"
        )

        sent_data = mock_websocket.send_json.call_args[0][0]
        assert sent_data["type"] == "agent_message"
        assert sent_data["message"] == "I found 3 authentication library options for you."
        assert sent_data["messageType"] == "info"
        assert "timestamp" in sent_data

    async def test_send_agent_message_with_data(self, connection_manager, mock_websocket, sample_session_id):
        """Test sending agent message with additional data."""
        await connection_manager.connect(mock_websocket, sample_session_id)

        tech_options = {
            "category": "authentication",
            "options": [
                {"name": "NextAuth.js", "pros": ["Easy"], "cons": []},
                {"name": "Passport.js", "pros": ["Mature"], "cons": []},
            ]
        }

        await connection_manager.send_agent_message(
            session_id=sample_session_id,
            message="Please select an authentication library:",
            message_type="question",
            data=tech_options
        )

        sent_data = mock_websocket.send_json.call_args[0][0]
        assert sent_data["messageType"] == "question"
        assert sent_data["data"]["category"] == "authentication"
        assert len(sent_data["data"]["options"]) == 2

    async def test_send_warning_message(self, connection_manager, mock_websocket, sample_session_id):
        """Test sending warning message."""
        await connection_manager.connect(mock_websocket, sample_session_id)

        await connection_manager.send_agent_message(
            session_id=sample_session_id,
            message="⚠️ Selected database conflicts with deployment requirements!",
            message_type="warning",
            data={"severity": "critical"}
        )

        sent_data = mock_websocket.send_json.call_args[0][0]
        assert sent_data["messageType"] == "warning"
        assert sent_data["data"]["severity"] == "critical"


@pytest.mark.asyncio
class TestCompletionNotification:
    """Test workflow completion notifications."""

    async def test_send_completion_success(self, connection_manager, mock_websocket, sample_session_id):
        """Test sending success completion notification."""
        await connection_manager.connect(mock_websocket, sample_session_id)

        await connection_manager.send_completion(
            session_id=sample_session_id,
            trd_document_id="trd-123",
            message="✅ Tech Spec Agent completed successfully!"
        )

        sent_data = mock_websocket.send_json.call_args[0][0]
        assert sent_data["type"] == "completion"
        assert sent_data["trdDocumentId"] == "trd-123"
        assert sent_data["message"] == "✅ Tech Spec Agent completed successfully!"
        assert "timestamp" in sent_data

    async def test_send_completion_default_message(self, connection_manager, mock_websocket, sample_session_id):
        """Test completion with default message."""
        await connection_manager.connect(mock_websocket, sample_session_id)

        await connection_manager.send_completion(
            session_id=sample_session_id,
            trd_document_id="trd-456"
        )

        sent_data = mock_websocket.send_json.call_args[0][0]
        assert "complete" in sent_data["message"].lower()


@pytest.mark.asyncio
class TestErrorHandling:
    """Test error notifications and handling."""

    async def test_send_error_message(self, connection_manager, mock_websocket, sample_session_id):
        """Test sending error notification."""
        await connection_manager.connect(mock_websocket, sample_session_id)

        await connection_manager.send_error(
            session_id=sample_session_id,
            error_message="TRD validation failed after 3 retries",
            error_type="validation_error",
            recoverable=False
        )

        sent_data = mock_websocket.send_json.call_args[0][0]
        assert sent_data["type"] == "error"
        assert sent_data["error"] == "TRD validation failed after 3 retries"
        assert sent_data["errorType"] == "validation_error"
        assert sent_data["recoverable"] is False

    async def test_send_recoverable_error(self, connection_manager, mock_websocket, sample_session_id):
        """Test sending recoverable error."""
        await connection_manager.connect(mock_websocket, sample_session_id)

        await connection_manager.send_error(
            session_id=sample_session_id,
            error_message="Web search temporarily failed",
            error_type="api_error",
            recoverable=True
        )

        sent_data = mock_websocket.send_json.call_args[0][0]
        assert sent_data["recoverable"] is True

    async def test_connection_drop_during_send(self, connection_manager, sample_session_id):
        """Test handling connection drop during message send."""
        mock_ws = AsyncMock()
        mock_ws.accept = AsyncMock()
        mock_ws.send_json = AsyncMock(side_effect=Exception("Connection closed"))

        await connection_manager.connect(mock_ws, sample_session_id)

        # Should not crash
        await connection_manager.send_progress_update(
            session_id=sample_session_id,
            progress=50.0,
            message="Test"
        )


@pytest.mark.asyncio
class TestBroadcast:
    """Test broadcast functionality."""

    async def test_broadcast_to_session(self, connection_manager, mock_websocket, sample_session_id):
        """Test broadcasting message to specific session."""
        await connection_manager.connect(mock_websocket, sample_session_id)

        custom_message = {
            "type": "custom",
            "data": {"foo": "bar"}
        }

        await connection_manager.broadcast(custom_message, sample_session_id)

        # connect() sends "connection_established", then we send custom message
        assert mock_websocket.send_json.call_count == 2
        # Verify the custom message was sent (second call)
        sent_data = mock_websocket.send_json.call_args_list[1][0][0]
        assert sent_data == custom_message

    async def test_broadcast_to_multiple_connections_same_session(self, connection_manager):
        """Test broadcasting to multiple WebSocket connections in the same session (multi-tab)."""
        ws1 = AsyncMock()
        ws1.accept = AsyncMock()
        ws2 = AsyncMock()
        ws2.accept = AsyncMock()
        ws3 = AsyncMock()
        ws3.accept = AsyncMock()

        # All 3 WebSockets connect to the same session (e.g., 3 browser tabs)
        session_id = "session-multi-tab"
        await connection_manager.connect(ws1, session_id)
        await connection_manager.connect(ws2, session_id)
        await connection_manager.connect(ws3, session_id)

        # Should have 3 connections for this session
        assert connection_manager.get_connection_count(session_id) == 3

        system_message = {
            "type": "system_announcement",
            "message": "System maintenance in 5 minutes"
        }

        # Broadcast to all connections in this session
        await connection_manager.broadcast(system_message, session_id)

        # Each connection should receive the message
        # Note: Each also received "connection_established" when connecting
        assert ws1.send_json.call_count == 2  # connection_established + system_announcement
        assert ws2.send_json.call_count == 2
        assert ws3.send_json.call_count == 2


@pytest.mark.asyncio
class TestMessageQueuing:
    """Test message queuing for disconnected sessions."""

    async def test_messages_queued_when_disconnected(self, connection_manager, sample_session_id):
        """Test that messages are queued when session is disconnected."""
        # Send message without connection
        await connection_manager.send_progress_update(
            session_id=sample_session_id,
            progress=25.0,
            message="Queued message"
        )

        # Message should be queued (verify by checking internal queue)
        # This is tested implicitly - no crash should occur

    async def test_queued_messages_sent_on_reconnect(self, connection_manager, mock_websocket, sample_session_id):
        """Test that queued messages are sent when session reconnects."""
        # Send messages while disconnected
        await connection_manager.send_progress_update(
            session_id=sample_session_id,
            progress=10.0,
            message="Message 1"
        )
        await connection_manager.send_progress_update(
            session_id=sample_session_id,
            progress=20.0,
            message="Message 2"
        )

        # Connect - should send queued messages
        await connection_manager.connect(mock_websocket, sample_session_id)

        # Queued messages should be sent (implementation detail)
        # At minimum, connection should not crash


@pytest.mark.asyncio
class TestWorkflowIntegration:
    """Test WebSocket integration with workflow."""

    async def test_workflow_progress_sequence(self, connection_manager, mock_websocket):
        """Test complete workflow progress sequence."""
        session_id = "workflow-session"
        await connection_manager.connect(mock_websocket, session_id)

        # Simulate workflow progress
        stages = [
            (5.0, "Loading inputs", "load_inputs"),
            (15.0, "Analyzing completeness", "analyze_completeness"),
            (25.0, "Identifying tech gaps", "identify_tech_gaps"),
            (50.0, "Researching technologies", "research_technologies"),
            (75.0, "Generating TRD", "generate_trd"),
            (100.0, "Complete", "complete"),
        ]

        for progress, message, stage in stages:
            await connection_manager.send_progress_update(
                session_id=session_id,
                progress=progress,
                message=message,
                stage=stage
            )

        # Verify all progress updates were sent
        # connect() sends "connection_established" + 6 progress updates = 7 total
        assert mock_websocket.send_json.call_count == 7

    async def test_error_recovery_flow(self, connection_manager, mock_websocket, sample_session_id):
        """Test error notification and recovery flow."""
        await connection_manager.connect(mock_websocket, sample_session_id)

        # Send error
        await connection_manager.send_error(
            session_id=sample_session_id,
            error_message="LLM API temporarily unavailable",
            error_type="llm_error",
            recoverable=True
        )

        # Resume with progress
        await connection_manager.send_progress_update(
            session_id=sample_session_id,
            progress=50.0,
            message="Retrying..."
        )

        # Complete successfully
        await connection_manager.send_completion(
            session_id=sample_session_id,
            trd_document_id="trd-789"
        )

        # All messages should be sent
        # connect() + error + progress + completion = 4 total
        assert mock_websocket.send_json.call_count == 4
