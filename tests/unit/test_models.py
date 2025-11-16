"""Unit tests for database models."""

import pytest
from datetime import datetime
from uuid import uuid4

from src.database.models import (
    TechSpecSession,
    TechResearch,
    TechConversation,
    GeneratedTRDDocument,
    AgentErrorLog,
    get_table_names,
)


def test_get_table_names():
    """Test getting all table names."""
    tables = get_table_names()

    assert len(tables) == 5
    assert "tech_spec_sessions" in tables
    assert "tech_research" in tables
    assert "tech_conversations" in tables
    assert "generated_trd_documents" in tables
    assert "agent_error_logs" in tables


def test_tech_spec_session_model():
    """Test TechSpecSession model structure."""
    session = TechSpecSession(
        id=uuid4(),
        project_id=uuid4(),
        design_job_id=uuid4(),
        status="pending",
        progress_percentage=0.0,
    )

    assert session.status == "pending"
    assert session.progress_percentage == 0.0
    assert session.created_at is None  # Will be set by database default


def test_tech_research_model():
    """Test TechResearch model structure."""
    research = TechResearch(
        id=uuid4(),
        session_id=uuid4(),
        technology_category="authentication",
        researched_options=[{"name": "NextAuth.js", "score": 95}],
    )

    assert research.technology_category == "authentication"
    assert isinstance(research.researched_options, list)


def test_tech_conversation_model():
    """Test TechConversation model structure."""
    conversation = TechConversation(
        id=uuid4(),
        session_id=uuid4(),
        role="user",
        message="I prefer NextAuth.js",
        message_type="decision_response",
    )

    assert conversation.role == "user"
    assert conversation.message == "I prefer NextAuth.js"


def test_generated_trd_document_model():
    """Test GeneratedTRDDocument model structure."""
    doc = GeneratedTRDDocument(
        id=uuid4(),
        session_id=uuid4(),
        trd_content="# Technical Requirements Document\n...",
        quality_score=92.5,
        version=1,
    )

    assert doc.quality_score == 92.5
    assert doc.version == 1


def test_agent_error_log_model():
    """Test AgentErrorLog model structure."""
    error = AgentErrorLog(
        id=uuid4(),
        session_id=uuid4(),
        node="research_technologies",
        error_type="api_error",
        message="Tavily API rate limit exceeded",
        retry_count=1,
        recovered=False,
    )

    assert error.node == "research_technologies"
    assert error.error_type == "api_error"
    assert error.retry_count == 1
    assert error.recovered is False


def test_model_relationships():
    """Test that models define proper relationships."""
    # Check TechSpecSession has relationships
    assert hasattr(TechSpecSession, "tech_research")
    assert hasattr(TechSpecSession, "conversations")
    assert hasattr(TechSpecSession, "trd_documents")
    assert hasattr(TechSpecSession, "error_logs")

    # Check TechResearch has relationships
    assert hasattr(TechResearch, "session")
    assert hasattr(TechResearch, "conversations")

    # Check TechConversation has relationships
    assert hasattr(TechConversation, "session")
    assert hasattr(TechConversation, "research")
