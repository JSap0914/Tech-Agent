"""
Persistence and notification nodes for saving generated documents and triggering next agent.

These nodes handle:
- Saving all generated documents to PostgreSQL
- Recording technology decisions
- Updating project status
- Notifying the Backlog Agent to start its workflow
"""

from datetime import datetime
from typing import Dict, List
import json
import structlog

from src.langgraph.state import TechSpecState
from src.database.connection import get_db_connection
from src.langgraph.error_logging import log_state_errors_to_db

logger = structlog.get_logger()


async def save_to_db_node(state: TechSpecState) -> TechSpecState:
    """
    Save all generated documents and decisions to PostgreSQL.

    Saves to tables:
    - tech_spec_sessions: Update session with completion status
    - tech_research: Save all technology research results
    - tech_conversations: Save all conversation history
    - generated_trd_documents: Save all 5 document types
    - shared.documents: Copy TRD to shared documents table for ANYON platform

    This node is idempotent - can be called multiple times safely.
    """
    logger.info(
        "save_to_db_start",
        session_id=state["session_id"],
        project_id=state["project_id"]
    )

    try:
        async with get_db_connection() as conn:
            async with conn.transaction():
                # 1. Update tech_spec_sessions table
                await _update_session(conn, state)

                # 2. Save technology research results
                await _save_research_results(conn, state)

                # 3. Save conversation history
                await _save_conversations(conn, state)

                # 4. Save generated documents
                await _save_generated_documents(conn, state)

                # 5. Copy final TRD to shared documents table
                await _copy_trd_to_shared_documents(conn, state)

        # 6. Persist all errors to agent_error_logs (outside transaction)
        await _save_error_logs(state)

        state["conversation_history"].append({
            "role": "agent",
            "message": (
                "✅ All documents saved successfully!\n\n"
                "Generated documents:\n"
                "  • Technical Requirements Document (TRD)\n"
                "  • API Specification (OpenAPI 3.0)\n"
                "  • Database Schema (SQL DDL + ERD)\n"
                "  • Architecture Diagram (Mermaid)\n"
                "  • Technology Stack Documentation\n\n"
                "These documents are now available in the ANYON platform."
            ),
            "message_type": "success",
            "timestamp": datetime.now().isoformat()
        })

        state["current_stage"] = "documents_saved"
        state["completion_percentage"] = 95.0

        logger.info(
            "save_to_db_complete",
            session_id=state["session_id"],
            documents_saved=5
        )

    except Exception as e:
        logger.error(
            "save_to_db_error",
            session_id=state["session_id"],
            error=str(e),
            exc_info=True
        )

        state["errors"].append({
            "node": "save_to_db",
            "error_type": type(e).__name__,
            "message": str(e),
            "timestamp": datetime.now().isoformat(),
            "recoverable": False  # Critical failure
        })

        raise  # Re-raise to trigger workflow failure

    return state


async def notify_next_agent_node(state: TechSpecState) -> TechSpecState:
    """
    Notify the Backlog Agent that Tech Spec is complete and ready for processing.

    Uses PostgreSQL NOTIFY/LISTEN for event bus communication between agents.

    Payload includes:
    - project_id: Which project is ready
    - tech_spec_session_id: Session ID for reference
    - trd_document_id: ID of the final TRD document
    - timestamp: When Tech Spec completed

    The Backlog Agent will listen for this notification and start automatically.
    """
    logger.info(
        "notify_next_agent_start",
        session_id=state["session_id"],
        project_id=state["project_id"]
    )

    try:
        async with get_db_connection() as conn:
            # Prepare notification payload
            payload = {
                "project_id": state["project_id"],
                "tech_spec_session_id": state["session_id"],
                "user_id": state["user_id"],
                "design_job_id": state.get("design_job_id"),
                "timestamp": datetime.now().isoformat(),
                "event_type": "tech_spec_complete"
            }

            # Send PostgreSQL NOTIFY
            await conn.execute(
                """
                SELECT pg_notify(
                    'anyon_agent_events',
                    $1::text
                )
                """,
                str(payload)
            )

            # Also update project status in ANYON platform
            await conn.execute(
                """
                UPDATE shared.projects
                SET
                    current_stage = 'backlog',
                    tech_spec_completed_at = NOW(),
                    updated_at = NOW()
                WHERE id = $1
                """,
                state["project_id"]
            )

        state["conversation_history"].append({
            "role": "agent",
            "message": (
                "✅ Backlog Agent has been notified!\n\n"
                "Your project is now moving to the Backlog stage where:\n"
                "  • Epics will be created from the TRD\n"
                "  • User stories will be generated\n"
                "  • Tasks will be broken down\n"
                "  • Development can begin!\n\n"
                "Thank you for using Tech Spec Agent. 🚀"
            ),
            "message_type": "completion",
            "timestamp": datetime.now().isoformat()
        })

        state["current_stage"] = "completed"
        state["completed"] = True
        state["completion_percentage"] = 100.0

        logger.info(
            "notify_next_agent_complete",
            session_id=state["session_id"],
            project_id=state["project_id"],
            notification_sent=True
        )

    except Exception as e:
        logger.error(
            "notify_next_agent_error",
            session_id=state["session_id"],
            error=str(e),
            exc_info=True
        )

        state["errors"].append({
            "node": "notify_next_agent",
            "error_type": type(e).__name__,
            "message": str(e),
            "timestamp": datetime.now().isoformat(),
            "recoverable": True  # Can retry notification
        })

        # Don't fail workflow - documents are already saved
        # User can manually trigger backlog agent if needed

    return state


# Helper functions

async def _update_session(conn, state: TechSpecState):
    """Update tech_spec_sessions table with final status."""
    await conn.execute(
        """
        UPDATE tech_spec_sessions
        SET
            current_stage = $1,
            completion_percentage = $2,
            completeness_score = $3,
            completed_at = NOW(),
            updated_at = NOW(),
            metadata = metadata || $4::jsonb
        WHERE id = $5
        """,
        state["current_stage"],
        state["completion_percentage"],
        state.get("completeness_score", 0.0),
        {
            "total_decisions": state.get("total_decisions", 0),
            "completed_decisions": state.get("completed_decisions", 0),
            "errors_count": len(state.get("errors", [])),
            "inferred_endpoints": len(state.get("inferred_api_spec", {}).get("endpoints", []))
        },
        state["session_id"]
    )


async def _save_research_results(conn, state: TechSpecState):
    """Save all technology research results."""
    research_results = state.get("research_results", [])

    for research in research_results:
        # Find user decision for this category
        user_decision = next(
            (d for d in state.get("user_decisions", [])
             if d.get("category") == research.get("category")),
            None
        )

        selected_option = user_decision.get("technology_name") if user_decision else None
        selection_reason = user_decision.get("reasoning") if user_decision else None

        await conn.execute(
            """
            INSERT INTO tech_research (
                id,
                session_id,
                gap_category,
                gap_description,
                options,
                selected_option,
                selection_reason,
                search_queries,
                created_at
            ) VALUES (
                gen_random_uuid(),
                $1, $2, $3, $4, $5, $6, $7, NOW()
            )
            ON CONFLICT (session_id, gap_category) DO UPDATE
            SET
                options = EXCLUDED.options,
                selected_option = EXCLUDED.selected_option,
                selection_reason = EXCLUDED.selection_reason
            """,
            state["session_id"],
            research.get("category"),
            research.get("question"),
            research.get("options", []),  # JSONB array
            selected_option,
            selection_reason,
            research.get("search_queries", [])  # TEXT array
        )


async def _save_conversations(conn, state: TechSpecState):
    """Save all conversation history."""
    conversations = state.get("conversation_history", [])

    for conv in conversations:
        # Skip if already saved (has database ID)
        if conv.get("_saved"):
            continue

        await conn.execute(
            """
            INSERT INTO tech_conversations (
                id,
                session_id,
                role,
                message,
                message_type,
                token_count,
                created_at
            ) VALUES (
                gen_random_uuid(),
                $1, $2, $3, $4, $5, $6
            )
            """,
            state["session_id"],
            conv.get("role"),
            conv.get("message"),
            conv.get("message_type", "general"),
            conv.get("token_count", 0),
            conv.get("timestamp", datetime.now())
        )

        # Mark as saved
        conv["_saved"] = True


async def _save_generated_documents(conn, state: TechSpecState):
    """
    Save all 5 generated documents to the database.

    Uses the existing schema with columns:
    - trd_content (Text)
    - api_specification (JSONB)
    - database_schema (JSONB)
    - architecture_diagram (Text)
    - tech_stack_document (JSONB)
    - quality_score (Float)
    - validation_report (JSONB)
    - version (Integer) - incremented on updates
    """

    # Prepare validation report with enhanced Week 8 data
    validation_result = state.get("trd_validation_result", {})
    validation_report = {
        "total_score": validation_result.get("total_score", 0.0),
        "scores": validation_result.get("scores", {}),
        "structure_score": validation_result.get("structure_score"),
        "multi_agent_score": validation_result.get("multi_agent_score"),
        "gaps": validation_result.get("gaps", []),
        "recommendations": validation_result.get("recommendations", []),
        "iteration_count": state.get("iteration_count", 1),
        "timestamp": datetime.now().isoformat()
    }

    # Parse API specification (may be string or dict)
    api_spec = state.get("api_specification")
    if isinstance(api_spec, str):
        try:
            api_spec = json.loads(api_spec) if api_spec else None
        except json.JSONDecodeError:
            api_spec = {"raw": api_spec}  # Store as raw if not valid JSON

    # Parse database schema (may be string or dict)
    db_schema = state.get("database_schema")
    if isinstance(db_schema, str):
        # Store SQL DDL as JSONB with a "ddl" key
        db_schema = {"ddl": db_schema} if db_schema else None

    # Parse tech stack document (may be string or dict)
    tech_stack = state.get("tech_stack_document")
    if isinstance(tech_stack, str):
        try:
            tech_stack = json.loads(tech_stack) if tech_stack else None
        except json.JSONDecodeError:
            tech_stack = {"markdown": tech_stack}  # Store as markdown if not valid JSON

    # Check if document already exists
    existing = await conn.fetchrow(
        """
        SELECT version FROM generated_trd_documents
        WHERE session_id = $1
        """,
        state["session_id"]
    )

    if existing:
        # Update existing document (increment version)
        await conn.execute(
            """
            UPDATE generated_trd_documents
            SET
                trd_content = $2,
                api_specification = $3,
                database_schema = $4,
                architecture_diagram = $5,
                tech_stack_document = $6,
                quality_score = $7,
                validation_report = $8,
                version = version + 1
            WHERE session_id = $1
            """,
            state["session_id"],
            state.get("trd_draft"),
            json.dumps(api_spec) if api_spec else None,
            json.dumps(db_schema) if db_schema else None,
            state.get("architecture_diagram"),
            json.dumps(tech_stack) if tech_stack else None,
            validation_result.get("total_score", 0.0),
            json.dumps(validation_report)
        )

        logger.info(
            "Documents updated",
            session_id=state["session_id"],
            version=existing["version"] + 1,
            quality_score=validation_result.get("total_score", 0.0)
        )
    else:
        # Insert new document
        await conn.execute(
            """
            INSERT INTO generated_trd_documents (
                id,
                session_id,
                trd_content,
                api_specification,
                database_schema,
                architecture_diagram,
                tech_stack_document,
                quality_score,
                validation_report,
                version,
                created_at
            ) VALUES (
                gen_random_uuid(),
                $1, $2, $3, $4, $5, $6, $7, $8, 1, NOW()
            )
            """,
            state["session_id"],
            state.get("trd_draft"),
            json.dumps(api_spec) if api_spec else None,
            json.dumps(db_schema) if db_schema else None,
            state.get("architecture_diagram"),
            json.dumps(tech_stack) if tech_stack else None,
            validation_result.get("total_score", 0.0),
            json.dumps(validation_report)
        )

        logger.info(
            "Documents inserted",
            session_id=state["session_id"],
            version=1,
            quality_score=validation_result.get("total_score", 0.0)
        )


async def _copy_trd_to_shared_documents(conn, state: TechSpecState):
    """
    Copy final TRD to shared.documents table for ANYON platform access.

    This allows other agents and the frontend to access the TRD.
    """
    if not state.get("trd_draft"):
        logger.warning("no_trd_draft", session_id=state["session_id"])
        return

    await conn.execute(
        """
        INSERT INTO shared.documents (
            id,
            project_id,
            document_type,
            content,
            version,
            created_by_agent,
            created_at,
            updated_at
        ) VALUES (
            gen_random_uuid(),
            $1, 'trd', $2, 1, 'tech_spec_agent', NOW(), NOW()
        )
        ON CONFLICT (project_id, document_type) WHERE version = (
            SELECT MAX(version) FROM shared.documents
            WHERE project_id = $1 AND document_type = 'trd'
        )
        DO UPDATE SET
            content = EXCLUDED.content,
            version = shared.documents.version + 1,
            updated_at = NOW()
        """,
        state["project_id"],
        state["trd_draft"]
    )


async def _save_error_logs(state: TechSpecState):
    """
    Persist all accumulated errors from state to agent_error_logs table.

    This ensures all errors that occurred during workflow execution
    are saved to the database for debugging and monitoring.
    """
    errors = state.get("errors", [])

    if not errors:
        logger.debug("no_errors_to_save", session_id=state["session_id"])
        return

    # Use helper function to persist all errors
    logged_count = await log_state_errors_to_db(state["session_id"], errors)

    logger.info(
        "errors_persisted",
        session_id=state["session_id"],
        total_errors=len(errors),
        logged_count=logged_count
    )
