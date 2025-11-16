"""
Pydantic schemas for API request/response validation.
Following ANYON API contract specification.
"""

from typing import List, Dict, Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field, UUID4, field_validator
from enum import Enum


# ============= Enums =============

class SessionStatus(str, Enum):
    """Tech Spec session status values."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class TechnologyCategory(str, Enum):
    """Technology category values."""
    AUTHENTICATION = "authentication"
    DATABASE = "database"
    FILE_UPLOAD = "file_upload"
    EMAIL = "email"
    PAYMENTS = "payments"
    FRONTEND_FRAMEWORK = "frontend_framework"
    BACKEND_FRAMEWORK = "backend_framework"
    CACHING = "caching"
    REAL_TIME = "real_time"
    DEPLOYMENT = "deployment"


# ============= Request Schemas =============

class StartTechSpecRequest(BaseModel):
    """Request to start a new Tech Spec session."""

    design_job_id: UUID4 = Field(
        ...,
        description="Design Agent job ID that this Tech Spec session is based on"
    )
    user_id: Optional[UUID4] = Field(
        None,
        description="User ID initiating the session (extracted from JWT if not provided)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "design_job_id": "550e8400-e29b-41d4-a716-446655440000",
                "user_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7"
            }
        }


class UserDecisionRequest(BaseModel):
    """User decision for a technology choice."""

    technology_category: TechnologyCategory = Field(
        ...,
        description="Category of technology being decided"
    )
    selected_technology: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Name of the selected technology"
    )
    reasoning: Optional[str] = Field(
        None,
        max_length=500,
        description="User's reasoning for the selection"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "technology_category": "authentication",
                "selected_technology": "NextAuth.js",
                "reasoning": "Best fit for Next.js project with good documentation"
            }
        }


# ============= Response Schemas =============

class StartTechSpecResponse(BaseModel):
    """Response after starting a Tech Spec session."""

    session_id: UUID4 = Field(..., description="Unique session identifier")
    project_id: UUID4 = Field(..., description="Associated project ID")
    status: SessionStatus = Field(..., description="Initial session status")
    websocket_url: str = Field(
        ...,
        description="WebSocket URL for real-time updates"
    )
    created_at: datetime = Field(..., description="Session creation timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "project_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
                "status": "pending",
                "websocket_url": "wss://anyon.com/tech-spec/a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "created_at": "2025-01-14T10:30:00Z"
            }
        }


class TechnologyOptionSchema(BaseModel):
    """Technology option presented to user."""

    name: str = Field(..., description="Technology name")
    description: str = Field(..., description="Brief description")
    pros: List[str] = Field(..., description="Advantages")
    cons: List[str] = Field(..., description="Disadvantages")
    popularity: str = Field(..., description="Popularity level (High/Medium/Low)")
    recommendation: bool = Field(..., description="Agent recommendation")


class TechnologyGapSchema(BaseModel):
    """Identified technology gap."""

    category: TechnologyCategory = Field(..., description="Technology category")
    description: str = Field(..., description="Gap description")
    required: bool = Field(..., description="Whether this technology is required")
    options: List[TechnologyOptionSchema] = Field(
        ...,
        description="Available technology options"
    )


class SessionStatusResponse(BaseModel):
    """Current status of a Tech Spec session."""

    session_id: UUID4 = Field(..., description="Session identifier")
    project_id: UUID4 = Field(..., description="Associated project ID")
    design_job_id: UUID4 = Field(..., description="Design Agent job ID")
    status: SessionStatus = Field(..., description="Current session status")
    current_stage: Optional[str] = Field(None, description="Current processing stage")
    progress_percentage: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Completion progress (0-100)"
    )

    # Technology gaps and decisions
    gaps_identified: Optional[int] = Field(
        None,
        description="Number of technology gaps identified"
    )
    decisions_made: Optional[int] = Field(
        None,
        description="Number of user decisions made"
    )
    pending_decisions: Optional[List[TechnologyGapSchema]] = Field(
        None,
        description="Technology decisions awaiting user input"
    )

    # Timestamps
    created_at: datetime = Field(..., description="Session creation time")
    updated_at: datetime = Field(..., description="Last update time")
    completed_at: Optional[datetime] = Field(None, description="Completion time")

    # WebSocket
    websocket_url: str = Field(..., description="WebSocket URL for updates")

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "project_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
                "design_job_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "in_progress",
                "current_stage": "awaiting_user_decision",
                "progress_percentage": 45.0,
                "gaps_identified": 5,
                "decisions_made": 2,
                "pending_decisions": [
                    {
                        "category": "authentication",
                        "description": "User authentication system needed",
                        "required": True,
                        "options": [
                            {
                                "name": "NextAuth.js",
                                "description": "Authentication for Next.js",
                                "pros": ["Easy setup", "Built-in providers"],
                                "cons": ["Tied to Next.js"],
                                "popularity": "High",
                                "recommendation": True
                            }
                        ]
                    }
                ],
                "created_at": "2025-01-14T10:30:00Z",
                "updated_at": "2025-01-14T10:45:00Z",
                "completed_at": None,
                "websocket_url": "wss://anyon.com/tech-spec/a1b2c3d4-e5f6-7890-abcd-ef1234567890"
            }
        }


class TRDDocumentSchema(BaseModel):
    """Generated TRD document details."""

    trd_content: str = Field(..., description="Full TRD markdown content")
    api_specification: Optional[str] = Field(
        None,
        description="OpenAPI/Swagger specification (JSON)"
    )
    database_schema: Optional[str] = Field(
        None,
        description="Database schema DDL (SQL)"
    )
    architecture_diagram: Optional[str] = Field(
        None,
        description="Architecture diagram (Mermaid code)"
    )
    tech_stack_document: Optional[str] = Field(
        None,
        description="Technology stack summary (Markdown)"
    )
    quality_score: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Document quality score (0-100)"
    )
    validation_report: Optional[Dict[str, Any]] = Field(
        None,
        description="Validation report with completeness metrics"
    )


class TRDDownloadResponse(BaseModel):
    """Response containing generated TRD documents."""

    session_id: UUID4 = Field(..., description="Session identifier")
    document: TRDDocumentSchema = Field(..., description="TRD document details")
    version: int = Field(..., description="Document version number")
    created_at: datetime = Field(..., description="Document creation timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "document": {
                    "trd_content": "# Technical Requirements Document\n\n...",
                    "api_specification": '{"openapi": "3.0.0", ...}',
                    "database_schema": "CREATE TABLE users (...);",
                    "architecture_diagram": "graph TD\n  A[Frontend] --> B[API]",
                    "tech_stack_document": "# Technology Stack\n\n- Frontend: Next.js",
                    "quality_score": 95.5,
                    "validation_report": {
                        "completeness": 98.0,
                        "technical_accuracy": 95.0,
                        "requirements_coverage": 97.0
                    }
                },
                "version": 1,
                "created_at": "2025-01-14T11:00:00Z"
            }
        }


class UserDecisionResponse(BaseModel):
    """Response after submitting a user decision."""

    session_id: UUID4 = Field(..., description="Session identifier")
    decision_accepted: bool = Field(..., description="Whether decision was accepted")
    message: str = Field(..., description="Response message")
    next_action: Optional[str] = Field(
        None,
        description="Next action required (e.g., 'await_more_decisions', 'generating_trd')"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "decision_accepted": True,
                "message": "Decision recorded successfully. Proceeding with next technology gap.",
                "next_action": "await_more_decisions"
            }
        }


# ============= Error Schemas =============

class ErrorDetail(BaseModel):
    """Error detail information."""

    code: str = Field(..., description="Error code")
    message: str = Field(..., description="Human-readable error message")
    field: Optional[str] = Field(None, description="Field that caused the error")


class ErrorResponse(BaseModel):
    """Standard error response."""

    error: str = Field(..., description="Error type")
    details: List[ErrorDetail] = Field(..., description="Error details")
    request_id: Optional[str] = Field(None, description="Request tracking ID")

    class Config:
        json_schema_extra = {
            "example": {
                "error": "ValidationError",
                "details": [
                    {
                        "code": "invalid_design_job",
                        "message": "Design job not found or not completed",
                        "field": "design_job_id"
                    }
                ],
                "request_id": "req_abc123"
            }
        }


# ============= Health Check Schema =============

class HealthCheckResponse(BaseModel):
    """Health check response."""

    status: str = Field(..., description="Service status (healthy/unhealthy)")
    service: str = Field(..., description="Service name")
    version: str = Field(..., description="Service version")
    environment: str = Field(..., description="Environment (development/staging/production)")
    database: Optional[str] = Field(None, description="Database connection status")
    redis: Optional[str] = Field(None, description="Redis connection status")
    timestamp: datetime = Field(..., description="Current server time")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "service": "tech-spec-agent",
                "version": "1.0.0",
                "environment": "production",
                "database": "connected",
                "redis": "connected",
                "timestamp": "2025-01-14T10:30:00Z"
            }
        }
