"""
WebSocket connection management for real-time communication with Tech Spec Agent.

Provides:
- Real-time progress updates to frontend
- Agent-user conversation streaming
- Technology decision collection
- Session status monitoring
- Reconnection support with message queueing
"""

from typing import Dict, Set, List, Optional, Any
from fastapi import WebSocket, WebSocketDisconnect
from collections import defaultdict, deque
import asyncio
import json
import structlog
from datetime import datetime

logger = structlog.get_logger()


class ConnectionManager:
    """
    Manages WebSocket connections for Tech Spec sessions with message queueing.

    Features:
    - Multiple WebSocket connections per session (user can have multiple tabs open)
    - Message queueing for offline/reconnecting clients
    - Automatic reconnection handling
    - Broadcast to all connections for a session
    - Connection heartbeat/keepalive

    Usage:
        >>> manager = ConnectionManager()
        >>> await manager.connect(websocket, session_id="uuid")
        >>> await manager.send_progress_update(session_id, 50, "Generating TRD...")
        >>> await manager.disconnect(websocket, session_id)
    """

    def __init__(self, max_queue_size: int = 100):
        """
        Initialize connection manager.

        Args:
            max_queue_size: Maximum number of messages to queue per session
        """
        # Active WebSocket connections: session_id -> Set[WebSocket]
        self.active_connections: Dict[str, Set[WebSocket]] = defaultdict(set)

        # Message queues for offline clients: session_id -> deque[message]
        self.message_queues: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_queue_size))

        # Connection metadata: websocket -> {session_id, connected_at, ...}
        self.connection_metadata: Dict[WebSocket, Dict[str, Any]] = {}

        # Lock for thread-safe operations
        self._lock = asyncio.Lock()

        logger.info("connection_manager_initialized", max_queue_size=max_queue_size)

    async def connect(self, websocket: WebSocket, session_id: str):
        """
        Accept and register new WebSocket connection.

        Args:
            websocket: FastAPI WebSocket instance
            session_id: Tech Spec session ID
        """
        await websocket.accept()

        async with self._lock:
            self.active_connections[session_id].add(websocket)
            self.connection_metadata[websocket] = {
                "session_id": session_id,
                "connected_at": datetime.now().isoformat(),
                "messages_sent": 0
            }

        logger.info(
            "websocket_connected",
            session_id=session_id,
            total_connections=len(self.active_connections[session_id])
        )

        # Send queued messages to newly connected client
        await self._send_queued_messages(websocket, session_id)

        # Send connection confirmation
        await self.send_message({
            "type": "connection_established",
            "sessionId": session_id,
            "timestamp": datetime.now().isoformat(),
            "queuedMessages": len(self.message_queues[session_id])
        }, session_id, websocket)

    async def disconnect(self, websocket: WebSocket, session_id: str):
        """
        Unregister WebSocket connection.

        Args:
            websocket: FastAPI WebSocket instance
            session_id: Tech Spec session ID
        """
        async with self._lock:
            self.active_connections[session_id].discard(websocket)
            metadata = self.connection_metadata.pop(websocket, {})

            # Clean up empty session
            if not self.active_connections[session_id]:
                del self.active_connections[session_id]

        logger.info(
            "websocket_disconnected",
            session_id=session_id,
            messages_sent=metadata.get("messages_sent", 0),
            duration_seconds=(
                (datetime.now() - datetime.fromisoformat(metadata.get("connected_at", datetime.now().isoformat()))).total_seconds()
                if metadata.get("connected_at") else 0
            )
        )

    async def send_message(
        self,
        message: dict,
        session_id: str,
        websocket: Optional[WebSocket] = None
    ):
        """
        Send message to specific WebSocket or broadcast to all connections.

        Args:
            message: Message dict to send
            session_id: Tech Spec session ID
            websocket: Specific WebSocket (if None, broadcasts to all)
        """
        if websocket:
            # Send to specific WebSocket
            try:
                await websocket.send_json(message)
                self.connection_metadata[websocket]["messages_sent"] += 1
            except Exception as e:
                logger.warning(
                    "websocket_send_error",
                    session_id=session_id,
                    error=str(e)
                )
        else:
            # Broadcast to all connections for this session
            await self.broadcast(message, session_id)

    async def broadcast(self, message: dict, session_id: str):
        """
        Broadcast message to all WebSocket connections for a session.

        If no active connections exist, queue message for later delivery.

        Args:
            message: Message dict to broadcast
            session_id: Tech Spec session ID
        """
        connections = self.active_connections.get(session_id, set())

        if not connections:
            # No active connections - queue message
            self.message_queues[session_id].append(message)
            logger.debug(
                "message_queued",
                session_id=session_id,
                queue_size=len(self.message_queues[session_id])
            )
            return

        # Send to all active connections
        disconnected = []
        for websocket in connections:
            try:
                await websocket.send_json(message)
                self.connection_metadata[websocket]["messages_sent"] += 1
            except Exception as e:
                logger.warning(
                    "broadcast_error",
                    session_id=session_id,
                    error=str(e)
                )
                disconnected.append(websocket)

        # Clean up disconnected WebSockets
        for websocket in disconnected:
            await self.disconnect(websocket, session_id)

    async def _send_queued_messages(self, websocket: WebSocket, session_id: str):
        """Send all queued messages to newly connected WebSocket."""
        queue = self.message_queues[session_id]

        if not queue:
            return

        logger.info(
            "sending_queued_messages",
            session_id=session_id,
            count=len(queue)
        )

        for message in list(queue):
            try:
                await websocket.send_json(message)
                self.connection_metadata[websocket]["messages_sent"] += 1
            except Exception as e:
                logger.error(
                    "queued_message_send_error",
                    session_id=session_id,
                    error=str(e)
                )
                break

        # Clear queue after successful delivery
        queue.clear()

    # =========================================================================
    # Helper methods for common message types
    # =========================================================================

    async def send_progress_update(
        self,
        session_id: str,
        progress: float,
        message: str,
        stage: Optional[str] = None
    ):
        """
        Send progress update to frontend.

        Args:
            session_id: Tech Spec session ID
            progress: Completion percentage (0-100)
            message: Status message
            stage: Current workflow stage (optional)
        """
        await self.broadcast({
            "type": "progress_update",
            "sessionId": session_id,
            "progress": progress,
            "message": message,
            "stage": stage,
            "timestamp": datetime.now().isoformat()
        }, session_id)

    async def send_agent_message(
        self,
        session_id: str,
        message: str,
        message_type: str = "general",
        data: Optional[dict] = None
    ):
        """
        Send agent conversation message to frontend.

        Args:
            session_id: Tech Spec session ID
            message: Agent message text
            message_type: Type of message (question, info, warning, etc.)
            data: Additional structured data
        """
        await self.broadcast({
            "type": "agent_message",
            "sessionId": session_id,
            "message": message,
            "messageType": message_type,
            "data": data or {},
            "timestamp": datetime.now().isoformat()
        }, session_id)

    async def send_completion(
        self,
        session_id: str,
        trd_document_id: str,
        message: str = "TRD generation complete!"
    ):
        """
        Send workflow completion notification.

        Args:
            session_id: Tech Spec session ID
            trd_document_id: ID of generated TRD document
            message: Completion message
        """
        await self.broadcast({
            "type": "completion",
            "sessionId": session_id,
            "trdDocumentId": trd_document_id,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }, session_id)

    async def send_error(
        self,
        session_id: str,
        error_message: str,
        error_type: str = "general",
        recoverable: bool = True
    ):
        """
        Send error notification to frontend.

        Args:
            session_id: Tech Spec session ID
            error_message: Error description
            error_type: Type of error
            recoverable: Whether error can be recovered
        """
        await self.broadcast({
            "type": "error",
            "sessionId": session_id,
            "error": error_message,
            "errorType": error_type,
            "recoverable": recoverable,
            "timestamp": datetime.now().isoformat()
        }, session_id)

    def get_connection_count(self, session_id: str) -> int:
        """Get number of active connections for a session."""
        return len(self.active_connections.get(session_id, set()))

    def is_session_connected(self, session_id: str) -> bool:
        """Check if session has any active connections."""
        return self.get_connection_count(session_id) > 0


# Global connection manager instance
manager = ConnectionManager(max_queue_size=100)
