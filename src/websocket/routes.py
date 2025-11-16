"""
FastAPI WebSocket routes for Tech Spec Agent real-time communication.

Provides:
- WebSocket endpoint for session-based communication
- User decision collection via WebSocket
- Real-time workflow status updates
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Query
from typing import Dict
import json
import structlog

from src.websocket.connection_manager import manager
from src.database.connection import get_db_connection
from src.auth.jwt import get_current_user_from_ws_token
from src.workers.job_processor import job_processor
from src.workers.decision_parser import parse_user_decision
from datetime import datetime

logger = structlog.get_logger()

router = APIRouter(prefix="/ws", tags=["websocket"])


@router.websocket("/tech-spec/{session_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    session_id: str,
    token: str = Query(..., description="JWT authentication token")
):
    """
    WebSocket endpoint for Tech Spec Agent session communication.

    **URL:** `ws://localhost:8000/ws/tech-spec/{session_id}`

    **Client → Server Messages:**
    ```json
    {
        "type": "user_decision",
        "category": "authentication",
        "technologyName": "NextAuth.js",
        "reasoning": "Best for Next.js projects"
    }
    ```

    **Server → Client Messages:**
    ```json
    {
        "type": "progress_update",
        "sessionId": "uuid",
        "progress": 45,
        "message": "Researching authentication options...",
        "stage": "research",
        "timestamp": "2025-11-15T10:30:00Z"
    }
    ```

    **Message Types (Server → Client):**
    - `connection_established`: Initial connection confirmation
    - `progress_update`: Workflow progress (0-100%)
    - `agent_message`: Agent conversation message
    - `completion`: Workflow finished successfully
    - `error`: Error occurred

    **Message Types (Client → Server):**
    - `user_decision`: Technology choice from user
    - `user_message`: General user input/clarification
    - `ping`: Heartbeat/keepalive

    **Authentication:**
    - Requires valid JWT token passed as query parameter: `?token=<jwt>`
    - Token must contain valid user_id
    - User must own the specified session
    - Connection closed with 1008 status code if authentication fails
    """
    # Step 1: Authenticate user from JWT token
    try:
        user = await get_current_user_from_ws_token(token)
        logger.info(
            "websocket_auth_success",
            session_id=session_id,
            user_id=user.id
        )
    except Exception as e:
        logger.warning(
            "websocket_auth_failed",
            session_id=session_id,
            error=str(e)
        )
        await websocket.close(code=1008, reason="Authentication failed")
        return

    # Step 2: Verify session exists and user owns it
    try:
        async with get_db_connection() as conn:
            session = await conn.fetchrow(
                "SELECT id, project_id, user_id FROM tech_spec_sessions WHERE id = $1",
                session_id
            )

            if not session:
                logger.warning("websocket_session_not_found", session_id=session_id)
                await websocket.close(code=4004, reason="Session not found")
                return

            # Verify session ownership
            if str(session["user_id"]) != user.id:
                logger.warning(
                    "websocket_unauthorized_access",
                    session_id=session_id,
                    user_id=user.id,
                    session_owner=str(session["user_id"])
                )
                await websocket.close(code=1008, reason="Unauthorized: Session does not belong to user")
                return

        # Connect WebSocket
        await manager.connect(websocket, session_id)

        logger.info(
            "websocket_session_start",
            session_id=session_id,
            project_id=session["project_id"]
        )

        try:
            # Listen for client messages
            while True:
                # Receive message from client
                data = await websocket.receive_text()

                try:
                    message = json.loads(data)
                    await handle_client_message(message, session_id, websocket)

                except json.JSONDecodeError as e:
                    logger.warning(
                        "invalid_json",
                        session_id=session_id,
                        error=str(e)
                    )
                    await manager.send_error(
                        session_id,
                        "Invalid JSON format",
                        error_type="invalid_input"
                    )

        except WebSocketDisconnect:
            logger.info("websocket_disconnect", session_id=session_id)

    except Exception as e:
        logger.error(
            "websocket_error",
            session_id=session_id,
            error=str(e),
            exc_info=True
        )

    finally:
        await manager.disconnect(websocket, session_id)


async def handle_client_message(message: Dict, session_id: str, websocket: WebSocket):
    """
    Handle incoming client messages.

    Routes messages to appropriate handlers based on type.
    """
    message_type = message.get("type")

    if message_type == "user_decision":
        await handle_user_decision(message, session_id)

    elif message_type == "user_message":
        await handle_user_message(message, session_id)

    elif message_type == "ping":
        await handle_ping(message, session_id, websocket)

    else:
        logger.warning(
            "unknown_message_type",
            session_id=session_id,
            type=message_type
        )


async def handle_user_decision(message: Dict, session_id: str):
    """
    Handle user technology decision.

    Stores decision in database and triggers workflow to continue.
    """
    try:
        # Step 1: Parse user decision
        decision = await parse_user_decision(message)

        logger.info(
            "user_decision_received",
            session_id=session_id,
            category=decision.category,
            technology=decision.selected_technology
        )

        # Step 2: Save decision to tech_research table (update selected_option)
        async with get_db_connection() as conn:
            await conn.execute(
                """
                UPDATE tech_research
                SET
                    selected_option = $1,
                    selection_reason = $2,
                    updated_at = NOW()
                WHERE session_id = $3 AND gap_category = $4
                """,
                decision.selected_technology,
                decision.reasoning,
                session_id,
                decision.category
            )

        # Step 3: Send confirmation to user
        await manager.send_agent_message(
            session_id,
            f"✅ {decision.selected_technology} selected for {decision.category}",
            message_type="decision_confirmation",
            data={
                "category": decision.category,
                "technology": decision.selected_technology,
                "confidence": decision.confidence
            }
        )

        # Step 4: Resume workflow execution (CRITICAL - was missing)
        # This call unblocks the LangGraph state machine and continues execution
        await job_processor.process_user_decision(session_id, decision)

        logger.info(
            "workflow_resumption_triggered",
            session_id=session_id,
            category=decision.category
        )

    except ValueError as e:
        # Invalid decision format
        logger.warning(
            "invalid_decision_format",
            session_id=session_id,
            error=str(e)
        )
        await manager.send_error(
            session_id,
            f"Invalid decision: {str(e)}",
            error_type="invalid_input"
        )

    except Exception as e:
        # Unexpected error
        logger.error(
            "decision_handling_failed",
            session_id=session_id,
            error=str(e),
            exc_info=True
        )
        await manager.send_error(
            session_id,
            "Failed to process decision. Please try again.",
            error_type="server_error",
            recoverable=True
        )


async def handle_user_message(message: Dict, session_id: str):
    """
    Handle general user message (clarification, question, etc.).
    """
    user_text = message.get("message", "")

    if not user_text:
        return

    logger.info(
        "user_message_received",
        session_id=session_id,
        message_length=len(user_text)
    )

    # Save to conversation history
    async with get_db_connection() as conn:
        await conn.execute(
            """
            INSERT INTO tech_conversations (
                id,
                session_id,
                role,
                message,
                message_type,
                created_at
            ) VALUES (
                gen_random_uuid(),
                $1, 'user', $2, 'clarification', NOW()
            )
            """,
            session_id,
            user_text
        )

    # Echo back to confirm receipt
    await manager.send_message({
        "type": "message_received",
        "sessionId": session_id,
        "timestamp": datetime.now().isoformat()
    }, session_id)


async def handle_ping(message: Dict, session_id: str, websocket: WebSocket):
    """Handle ping/keepalive message."""
    await websocket.send_json({
        "type": "pong",
        "sessionId": session_id,
        "timestamp": datetime.now().isoformat()
    })
