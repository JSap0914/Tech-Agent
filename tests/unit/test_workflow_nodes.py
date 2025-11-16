"""
Unit tests for LangGraph workflow nodes (Week 6).

Tests cover:
- Code analysis nodes (parse_ai_studio_code, infer_api_spec)
- Persistence nodes (save_to_db, notify_next_agent)
- Workflow conditional branches
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from src.langgraph.state import create_initial_state
from src.langgraph.nodes.code_analysis_nodes import (
    parse_ai_studio_code_node,
    infer_api_spec_node
)
from src.langgraph.nodes.persistence_nodes import (
    save_to_db_node,
    notify_next_agent_node
)
from src.langgraph.workflow import (
    _check_tech_gaps_exist,
    _check_options_to_present,
    _check_decision_conflicts,
    _check_trd_quality
)


# =============================================================================
# Code Analysis Node Tests
# =============================================================================

@pytest.mark.asyncio
async def test_parse_ai_studio_code_node_no_code():
    """Test parse_ai_studio_code_node when no code path provided."""
    state = create_initial_state(
        session_id="test-session",
        project_id="test-project",
        user_id="test-user",
        design_job_id="test-design"
    )

    # No google_ai_studio_code_path set
    result = await parse_ai_studio_code_node(state)

    assert result["current_stage"] == "code_analysis_skipped"
    assert result["completion_percentage"] == 55.0
    assert len(result["conversation_history"]) > 0
    assert "No Google AI Studio code" in result["conversation_history"][-1]["message"]


@pytest.mark.asyncio
async def test_parse_ai_studio_code_node_with_code(tmp_path):
    """Test parse_ai_studio_code_node with actual code file."""
    import zipfile

    # Create mock ZIP file with React component
    zip_path = tmp_path / "ai_studio_code.zip"
    component_code = """
    import React, { useState } from 'react';

    interface UserProfileProps {
        userId: string;
        name: string;
        email: string;
    }

    export function UserProfile({ userId, name, email }: UserProfileProps) {
        const [loading, setLoading] = useState(false);

        const handleFetch = async () => {
            const response = await fetch(`/api/users/${userId}`, {
                method: 'GET'
            });
        };

        return <div>{name}</div>;
    }
    """

    with zipfile.ZipFile(zip_path, 'w') as zf:
        zf.writestr("components/UserProfile.tsx", component_code)

    state = create_initial_state(
        session_id="test-session",
        project_id="test-project",
        user_id="test-user",
        design_job_id="test-design"
    )
    state["google_ai_studio_code_path"] = str(zip_path)

    result = await parse_ai_studio_code_node(state)

    assert result["current_stage"] == "code_parsed"
    assert result["google_ai_studio_data"] is not None
    assert len(result["google_ai_studio_data"]["components"]) > 0

    # Check component was parsed
    component = result["google_ai_studio_data"]["components"][0]
    assert component["name"] == "UserProfile"
    assert len(component["api_calls"]) > 0
    assert component["api_calls"][0]["method"] == "GET"


@pytest.mark.asyncio
async def test_infer_api_spec_node_from_code():
    """Test infer_api_spec_node with parsed component data."""
    state = create_initial_state(
        session_id="test-session",
        project_id="test-project",
        user_id="test-user",
        design_job_id="test-design"
    )

    # Mock parsed component data
    state["google_ai_studio_data"] = {
        "components": [
            {
                "name": "UserProfile",
                "api_calls": [
                    {
                        "type": "fetch",
                        "url": "/api/users/:id",
                        "method": "GET"
                    },
                    {
                        "type": "axios",
                        "url": "/api/users/:id",
                        "method": "PUT"
                    }
                ],
                "props_interface": {
                    "userId": "string",
                    "name": "string"
                }
            }
        ]
    }

    result = await infer_api_spec_node(state)

    assert result["current_stage"] == "api_inferred"
    assert result["inferred_api_spec"] is not None
    assert len(result["inferred_api_spec"]["endpoints"]) == 2

    # Check endpoints were inferred
    endpoints = result["inferred_api_spec"]["endpoints"]
    methods = {ep["method"] for ep in endpoints}
    assert "GET" in methods
    assert "PUT" in methods


@pytest.mark.asyncio
async def test_infer_api_spec_node_from_design_docs():
    """Test infer_api_spec_node falling back to design docs."""
    state = create_initial_state(
        session_id="test-session",
        project_id="test-project",
        user_id="test-user",
        design_job_id="test-design"
    )

    # No code data, but have design docs
    state["design_docs"] = {
        "user_flow": "List of users with create user form and delete user button"
    }

    result = await infer_api_spec_node(state)

    assert result["current_stage"] == "api_inferred"
    assert result["inferred_api_spec"] is not None

    # Should infer basic CRUD endpoints from design text
    endpoints = result["inferred_api_spec"]["endpoints"]
    assert len(endpoints) > 0


# =============================================================================
# Persistence Node Tests
# =============================================================================

@pytest.mark.asyncio
@patch('src.langgraph.nodes.persistence_nodes.get_db_connection')
async def test_save_to_db_node(mock_db):
    """Test save_to_db_node successfully saves all documents."""
    # Mock database connection
    mock_conn = AsyncMock()
    mock_transaction = AsyncMock()
    mock_transaction.__aenter__ = AsyncMock(return_value=mock_transaction)
    mock_transaction.__aexit__ = AsyncMock(return_value=None)
    mock_conn.transaction.return_value = mock_transaction
    mock_conn.execute = AsyncMock()

    mock_db.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_db.return_value.__aexit__ = AsyncMock()

    state = create_initial_state(
        session_id="test-session",
        project_id="test-project",
        user_id="test-user",
        design_job_id="test-design"
    )

    # Mock generated documents
    state["final_trd"] = "# TRD Document Content"
    state["api_specification"] = "openapi: 3.0.0..."
    state["database_schema"] = "CREATE TABLE users..."
    state["architecture_diagram"] = "graph TD..."
    state["tech_stack_document"] = "# Tech Stack"
    state["research_results"] = []
    state["conversation_history"] = []

    result = await save_to_db_node(state)

    assert result["current_stage"] == "documents_saved"
    assert result["completion_percentage"] == 95.0
    assert mock_conn.execute.called


@pytest.mark.asyncio
@patch('src.langgraph.nodes.persistence_nodes.get_db_connection')
async def test_notify_next_agent_node(mock_db):
    """Test notify_next_agent_node sends PostgreSQL NOTIFY."""
    mock_conn = AsyncMock()
    mock_conn.execute = AsyncMock()

    mock_db.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_db.return_value.__aexit__ = AsyncMock()

    state = create_initial_state(
        session_id="test-session",
        project_id="test-project",
        user_id="test-user",
        design_job_id="test-design"
    )

    result = await notify_next_agent_node(state)

    assert result["current_stage"] == "completed"
    assert result["completed"] is True
    assert result["completion_percentage"] == 100.0

    # Verify NOTIFY was called
    assert mock_conn.execute.called
    call_args = mock_conn.execute.call_args_list

    # Check for pg_notify call
    notify_called = any(
        "pg_notify" in str(call[0][0]) for call in call_args
    )
    assert notify_called, "PostgreSQL NOTIFY should be called"


# =============================================================================
# Workflow Conditional Branch Tests
# =============================================================================

def test_check_tech_gaps_exist_with_gaps():
    """Test _check_tech_gaps_exist returns 'has_gaps' when gaps identified."""
    state = create_initial_state(
        session_id="test-session",
        project_id="test-project",
        user_id="test-user",
        design_job_id="test-design"
    )

    state["identified_gaps"] = [
        {"category": "authentication", "description": "User auth system"}
    ]

    result = _check_tech_gaps_exist(state)
    assert result == "has_gaps"


def test_check_tech_gaps_exist_no_gaps():
    """Test _check_tech_gaps_exist returns 'no_gaps' when no gaps."""
    state = create_initial_state(
        session_id="test-session",
        project_id="test-project",
        user_id="test-user",
        design_job_id="test-design"
    )

    state["identified_gaps"] = []

    result = _check_tech_gaps_exist(state)
    assert result == "no_gaps"


def test_check_options_to_present_has_options():
    """Test _check_options_to_present returns 'has_options' when decisions pending."""
    state = create_initial_state(
        session_id="test-session",
        project_id="test-project",
        user_id="test-user",
        design_job_id="test-design"
    )

    state["identified_gaps"] = [
        {"category": "authentication"},
        {"category": "database"}
    ]
    state["user_decisions"] = [
        {"category": "authentication", "technology_name": "NextAuth.js"}
    ]

    result = _check_options_to_present(state)
    assert result == "has_options"


def test_check_options_to_present_no_options():
    """Test _check_options_to_present returns 'no_options' when all decided."""
    state = create_initial_state(
        session_id="test-session",
        project_id="test-project",
        user_id="test-user",
        design_job_id="test-design"
    )

    state["identified_gaps"] = [
        {"category": "authentication"}
    ]
    state["user_decisions"] = [
        {"category": "authentication", "technology_name": "NextAuth.js"}
    ]
    state["pending_decisions"] = []
    state["current_research_category"] = None

    result = _check_options_to_present(state)
    assert result == "no_options"


def test_check_decision_conflicts_has_conflicts():
    """Test _check_decision_conflicts detects critical conflicts."""
    state = create_initial_state(
        session_id="test-session",
        project_id="test-project",
        user_id="test-user",
        design_job_id="test-design"
    )

    state["decision_warnings"] = [
        {
            "severity": "critical",
            "message": "Technology conflict detected"
        }
    ]

    result = _check_decision_conflicts(state)
    assert result == "has_conflicts"


def test_check_decision_conflicts_no_conflicts():
    """Test _check_decision_conflicts returns 'no_conflicts'."""
    state = create_initial_state(
        session_id="test-session",
        project_id="test-project",
        user_id="test-user",
        design_job_id="test-design"
    )

    state["decision_warnings"] = []

    result = _check_decision_conflicts(state)
    assert result == "no_conflicts"


def test_check_trd_quality_valid():
    """Test _check_trd_quality returns 'valid' when score >= 90."""
    state = create_initial_state(
        session_id="test-session",
        project_id="test-project",
        user_id="test-user",
        design_job_id="test-design"
    )

    state["trd_validation"] = {"total_score": 92.5}
    state["iteration_count"] = 1

    result = _check_trd_quality(state)
    assert result == "valid"


def test_check_trd_quality_invalid_retry():
    """Test _check_trd_quality returns 'invalid_retry' when score < 90."""
    state = create_initial_state(
        session_id="test-session",
        project_id="test-project",
        user_id="test-user",
        design_job_id="test-design"
    )

    state["trd_validation"] = {"total_score": 85.0}
    state["iteration_count"] = 1

    result = _check_trd_quality(state)
    assert result == "invalid_retry"


def test_check_trd_quality_force_pass():
    """Test _check_trd_quality force passes after 3 retries."""
    state = create_initial_state(
        session_id="test-session",
        project_id="test-project",
        user_id="test-user",
        design_job_id="test-design"
    )

    state["trd_validation"] = {"total_score": 85.0}
    state["iteration_count"] = 3  # Max retries reached

    result = _check_trd_quality(state)
    assert result == "invalid_force_pass"


# =============================================================================
# Integration: Full Node Execution
# =============================================================================

@pytest.mark.asyncio
async def test_code_analysis_pipeline(tmp_path):
    """Test full code analysis pipeline: parse → infer."""
    import zipfile

    # Create test ZIP
    zip_path = tmp_path / "code.zip"
    code = """
    export function Dashboard() {
        const data = await fetch('/api/dashboard/stats', { method: 'GET' });
        return <div>Dashboard</div>;
    }
    """

    with zipfile.ZipFile(zip_path, 'w') as zf:
        zf.writestr("Dashboard.tsx", code)

    state = create_initial_state(
        session_id="test",
        project_id="test",
        user_id="test",
        design_job_id="test"
    )
    state["google_ai_studio_code_path"] = str(zip_path)

    # Execute pipeline
    state = await parse_ai_studio_code_node(state)
    state = await infer_api_spec_node(state)

    # Verify pipeline results
    assert state["current_stage"] == "api_inferred"
    assert state["inferred_api_spec"] is not None
    assert len(state["inferred_api_spec"]["endpoints"]) > 0

    endpoint = state["inferred_api_spec"]["endpoints"][0]
    assert "/api/dashboard/stats" in endpoint["path"]
    assert endpoint["method"] == "GET"
