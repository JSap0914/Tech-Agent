"""Unit tests for LangGraph state schema."""

import pytest
from src.langgraph.state import TechSpecState, create_initial_state


def test_create_initial_state():
    """Test creating initial state with correct structure."""
    state = create_initial_state(
        session_id="test-session-123",
        project_id="test-project-456",
        user_id="test-user-789",
        design_job_id="test-design-job-101"
    )

    # Check metadata
    assert state["session_id"] == "test-session-123"
    assert state["project_id"] == "test-project-456"
    assert state["user_id"] == "test-user-789"
    assert state["design_job_id"] == "test-design-job-101"

    # Check initial values
    assert state["progress_percentage"] == 0.0
    assert state["iteration_count"] == 0
    assert state["max_iterations"] == 3
    assert state["paused"] is False
    assert state["completed"] is False
    assert state["current_stage"] == "load_inputs"

    # Check empty lists
    assert state["research_results"] == []
    assert state["user_decisions"] == []
    assert state["errors"] == []
    assert state["conversation_history"] == []

    # Check timestamps exist
    assert "started_at" in state
    assert "updated_at" in state
    assert state["completed_at"] is None


def test_initial_state_types():
    """Test that initial state has correct types."""
    state = create_initial_state("s1", "p1", "u1", "d1")

    assert isinstance(state["session_id"], str)
    assert isinstance(state["progress_percentage"], float)
    assert isinstance(state["iteration_count"], int)
    assert isinstance(state["paused"], bool)
    assert isinstance(state["research_results"], list)
    assert isinstance(state["user_decisions"], list)
    assert isinstance(state["technology_options"], dict)
