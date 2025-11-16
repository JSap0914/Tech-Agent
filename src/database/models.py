"""
SQLAlchemy models for Tech Spec Agent.
Defines all database tables with proper relationships and foreign keys.
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    Boolean,
    DateTime,
    Text,
    ForeignKey,
    CheckConstraint,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import declarative_base, relationship
import uuid

Base = declarative_base()


# ============= Shared Tables (from Design Agent) =============
# These are references to existing tables, not created by Tech Spec Agent

class DesignJob(Base):
    """Reference to Design Agent jobs (shared.design_jobs)."""
    __tablename__ = "design_jobs"
    __table_args__ = {"schema": "shared"}

    job_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(String(255), nullable=False)  # Design Agent uses VARCHAR
    user_id = Column(String(255), nullable=True)
    prd_content = Column(Text)
    trd_content = Column(Text)
    status = Column(String(20), default="pending")
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)


class DesignOutput(Base):
    """Reference to Design Agent outputs (shared.design_outputs)."""
    __tablename__ = "design_outputs"
    __table_args__ = {"schema": "shared"}

    output_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(UUID(as_uuid=True), ForeignKey("shared.design_jobs.job_id"))
    document_type = Column(String(50))
    file_name = Column(String(255))
    content = Column(Text)
    version = Column(String(20))
    output_metadata = Column("metadata", JSONB)  # Map to 'metadata' column in DB
    created_at = Column(DateTime, default=datetime.utcnow)


class DesignDecision(Base):
    """Reference to Design Agent decisions (shared.design_decisions)."""
    __tablename__ = "design_decisions"
    __table_args__ = {"schema": "shared"}

    decision_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(UUID(as_uuid=True), ForeignKey("shared.design_jobs.job_id"))
    decision_type = Column(String(50))
    decision_value = Column(Text)
    reasoning = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class DesignProgress(Base):
    """Reference to Design Agent progress (shared.design_progress)."""
    __tablename__ = "design_progress"
    __table_args__ = {"schema": "shared"}

    progress_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(UUID(as_uuid=True), ForeignKey("shared.design_jobs.job_id"))
    stage = Column(String(50))
    progress = Column(Float)
    updated_at = Column(DateTime, default=datetime.utcnow)


# ============= Tech Spec Agent Tables =============

class TechSpecSession(Base):
    """
    Tech Spec Agent sessions.
    Main table linking to Design Agent jobs.
    """
    __tablename__ = "tech_spec_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    design_job_id = Column(
        UUID(as_uuid=True),
        ForeignKey("shared.design_jobs.job_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(UUID(as_uuid=True), nullable=True)

    status = Column(
        String(20),
        default="pending",
        nullable=False,
        index=True,
    )
    current_stage = Column(String(50))
    progress_percentage = Column(Float, default=0.00)

    session_data = Column(JSONB)  # LangGraph state
    websocket_url = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'in_progress', 'paused', 'completed', 'failed')",
            name="valid_status"
        ),
        CheckConstraint(
            "progress_percentage >= 0 AND progress_percentage <= 100",
            name="valid_progress"
        ),
    )

    # Relationships
    tech_research = relationship("TechResearch", back_populates="session", cascade="all, delete-orphan")
    conversations = relationship("TechConversation", back_populates="session", cascade="all, delete-orphan")
    trd_documents = relationship("GeneratedTRDDocument", back_populates="session", cascade="all, delete-orphan")
    error_logs = relationship("AgentErrorLog", back_populates="session", cascade="all, delete-orphan")


class TechResearch(Base):
    """
    Technology research results for each gap category.
    """
    __tablename__ = "tech_research"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tech_spec_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    technology_category = Column(String(50), nullable=False, index=True)
    gap_description = Column(Text)
    researched_options = Column(JSONB)  # Array of technology options
    selected_technology = Column(String(100))
    selection_reasoning = Column(Text)
    decision_timestamp = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    session = relationship("TechSpecSession", back_populates="tech_research")
    conversations = relationship("TechConversation", back_populates="research")


class TechConversation(Base):
    """
    Conversation history between user and agent.
    """
    __tablename__ = "tech_conversations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tech_spec_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    research_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tech_research.id", ondelete="SET NULL"),
        nullable=True,
    )

    role = Column(String(20), nullable=False)
    message = Column(Text, nullable=False)
    message_type = Column(String(50))
    message_metadata = Column(JSONB)  # Renamed from 'metadata' (SQLAlchemy reserved attribute)

    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "role IN ('user', 'agent', 'system')",
            name="valid_role"
        ),
    )

    # Relationships
    session = relationship("TechSpecSession", back_populates="conversations")
    research = relationship("TechResearch", back_populates="conversations")


class GeneratedTRDDocument(Base):
    """
    Generated Technical Requirements Documents and related artifacts.
    """
    __tablename__ = "generated_trd_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tech_spec_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    trd_content = Column(Text)  # Full TRD (markdown)
    api_specification = Column(JSONB)  # OpenAPI/Swagger JSON object
    database_schema = Column(JSONB)  # Database schema JSON object
    architecture_diagram = Column(Text)  # Mermaid diagram (text)
    tech_stack_document = Column(JSONB)  # Tech stack JSON object

    quality_score = Column(Float, index=True)
    validation_report = Column(JSONB)
    version = Column(Integer, default=1)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    session = relationship("TechSpecSession", back_populates="trd_documents")


class AgentErrorLog(Base):
    """
    Error logs for tracking and recovery.
    Critical for error handling and retry logic.
    """
    __tablename__ = "agent_error_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tech_spec_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    node = Column(String(100), nullable=False, index=True)
    error_type = Column(String(50), nullable=False)
    message = Column(Text, nullable=False)
    stack_trace = Column(Text)

    retry_count = Column(Integer, default=0)
    recovered = Column(Boolean, default=False, index=True)
    recovery_strategy = Column(String(100))

    created_at = Column(DateTime, default=datetime.utcnow)

    # Constraints
    __table_args__ = (
        CheckConstraint("retry_count >= 0", name="valid_retry_count"),
    )

    # Relationships
    session = relationship("TechSpecSession", back_populates="error_logs")


# ============= Helper Functions =============

def get_table_names():
    """Get all table names defined in this module."""
    return [
        "tech_spec_sessions",
        "tech_research",
        "tech_conversations",
        "generated_trd_documents",
        "agent_error_logs",
    ]


def create_indexes():
    """
    Additional indexes for performance optimization.
    These are created in addition to the indexes defined in columns.
    """
    return [
        # Composite index for session + status queries
        Index("idx_session_status_created",
              TechSpecSession.status,
              TechSpecSession.created_at.desc()),

        # Composite index for session + category queries
        Index("idx_research_session_category",
              TechResearch.session_id,
              TechResearch.technology_category),

        # Index for conversation timeline queries
        Index("idx_conversation_session_timestamp",
              TechConversation.session_id,
              TechConversation.timestamp.desc()),

        # Index for error analysis queries
        Index("idx_error_node_recovered",
              AgentErrorLog.node,
              AgentErrorLog.recovered),
    ]
