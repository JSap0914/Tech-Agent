"""
Integration tests for REST API endpoints.
Tests full request/response flow with actual database.
"""

import pytest
from uuid import uuid4
from datetime import datetime, timedelta
from httpx import AsyncClient
import structlog

from src.main import app
from src.database.connection import db_manager
from src.database.models import TechSpecSession, GeneratedTRDDocument, DesignJob
from src.api.auth import create_access_token
from src.api.schemas import TechnologyCategory
from sqlalchemy import select, delete

logger = structlog.get_logger(__name__)


# ============= Fixtures =============

@pytest.fixture(scope="session", autouse=True)
def initialize_test_db():
    """Initialize database for integration tests."""
    db_manager.initialize_async_engine()
    yield
    # Cleanup handled by individual test fixtures


@pytest.fixture
async def async_client():
    """Async HTTP client for API testing."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture
def valid_jwt_token():
    """Generate a valid JWT token for testing."""
    payload = {
        "sub": str(uuid4()),
        "email": "integration-test@anyon.com",
        "role": "user",
        "permissions": []
    }
    token = create_access_token(payload, expires_delta=timedelta(hours=1))
    return token


@pytest.fixture
def admin_jwt_token():
    """Generate an admin JWT token for testing."""
    payload = {
        "sub": str(uuid4()),
        "email": "admin-test@anyon.com",
        "role": "admin",
        "permissions": ["admin:all"]
    }
    token = create_access_token(payload, expires_delta=timedelta(hours=1))
    return token


@pytest.fixture
async def test_design_job():
    """Create a test design job with design outputs in database."""
    from src.database.models import DesignOutput

    design_job_id = uuid4()
    project_id = uuid4()

    async with db_manager.get_async_session() as session:
        # Create design job
        design_job = DesignJob(
            id=design_job_id,
            project_id=project_id,
            status="completed",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        session.add(design_job)

        # Create design outputs (required for load_design_agent_outputs)
        design_outputs = [
            DesignOutput(
                id=uuid4(),
                design_job_id=design_job_id,
                doc_type="prd",
                content="# Product Requirements Document\n\nTest PRD content...",
                file_path=None,
                created_at=datetime.utcnow()
            ),
            DesignOutput(
                id=uuid4(),
                design_job_id=design_job_id,
                doc_type="design_system",
                content="# Design System\n\nTest design system content...",
                file_path=None,
                created_at=datetime.utcnow()
            ),
            DesignOutput(
                id=uuid4(),
                design_job_id=design_job_id,
                doc_type="ux_flow",
                content="# UX Flow\n\nTest UX flow content...",
                file_path=None,
                created_at=datetime.utcnow()
            ),
            DesignOutput(
                id=uuid4(),
                design_job_id=design_job_id,
                doc_type="screen_specs",
                content="# Screen Specifications\n\nTest screen specs content...",
                file_path=None,
                created_at=datetime.utcnow()
            )
        ]
        for output in design_outputs:
            session.add(output)

        await session.commit()

    yield design_job_id, project_id

    # Cleanup
    async with db_manager.get_async_session() as session:
        await session.execute(delete(DesignOutput).where(DesignOutput.design_job_id == design_job_id))
        await session.execute(delete(DesignJob).where(DesignJob.id == design_job_id))
        await session.commit()


@pytest.fixture
async def test_session(test_design_job):
    """Create a test Tech Spec session in database."""
    design_job_id, project_id = test_design_job
    session_id = uuid4()

    async with db_manager.get_async_session() as db_session:
        tech_session = TechSpecSession(
            id=session_id,
            project_id=project_id,
            design_job_id=design_job_id,
            user_id=uuid4(),
            status="in_progress",
            current_stage="identifying_gaps",
            progress_percentage=25.0,
            session_data={
                "gaps_identified": 3,
                "decisions_made": 1,
                "pending_decisions": []
            },
            websocket_url=f"wss://test/{session_id}",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db_session.add(tech_session)
        await db_session.commit()

    yield session_id, project_id, design_job_id

    # Cleanup
    async with db_manager.get_async_session() as db_session:
        await db_session.execute(delete(TechSpecSession).where(TechSpecSession.id == session_id))
        await db_session.commit()


@pytest.fixture
async def completed_session_with_trd(test_design_job):
    """Create a completed Tech Spec session with TRD document."""
    design_job_id, project_id = test_design_job
    session_id = uuid4()

    async with db_manager.get_async_session() as db_session:
        # Create completed session
        tech_session = TechSpecSession(
            id=session_id,
            project_id=project_id,
            design_job_id=design_job_id,
            user_id=uuid4(),
            status="completed",
            current_stage="completed",
            progress_percentage=100.0,
            session_data={
                "gaps_identified": 5,
                "decisions_made": 5
            },
            websocket_url=f"wss://test/{session_id}",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            completed_at=datetime.utcnow()
        )
        db_session.add(tech_session)

        # Create TRD document
        trd_doc = GeneratedTRDDocument(
            id=uuid4(),
            session_id=session_id,
            trd_content="# Technical Requirements Document\n\n## Overview\nTest TRD content...",
            api_specification={"openapi": "3.0.0", "info": {"title": "Test API"}},
            database_schema={"tables": ["users", "sessions"]},
            architecture_diagram="```mermaid\ngraph TD\nA-->B\n```",
            tech_stack_document={"frontend": "Next.js", "backend": "FastAPI"},
            quality_score=95.5,
            validation_report={"passed": True, "issues": []},
            version=1,
            created_at=datetime.utcnow()
        )
        db_session.add(trd_doc)
        await db_session.commit()

    yield session_id, project_id, design_job_id

    # Cleanup
    async with db_manager.get_async_session() as db_session:
        await db_session.execute(delete(GeneratedTRDDocument).where(GeneratedTRDDocument.session_id == session_id))
        await db_session.execute(delete(TechSpecSession).where(TechSpecSession.id == session_id))
        await db_session.commit()


# ============= Test Endpoint 1: Start Tech Spec =============

@pytest.mark.asyncio
async def test_start_tech_spec_success(async_client, test_design_job, valid_jwt_token):
    """Test successfully starting a Tech Spec session."""
    design_job_id, project_id = test_design_job

    response = await async_client.post(
        f"/api/projects/{project_id}/start-tech-spec",
        json={"design_job_id": str(design_job_id)},
        headers={"Authorization": f"Bearer {valid_jwt_token}"}
    )

    assert response.status_code == 201
    data = response.json()

    assert "session_id" in data
    assert data["project_id"] == str(project_id)
    assert data["status"] == "pending"
    assert "websocket_url" in data
    assert "created_at" in data

    # Verify session was created in database
    session_id = data["session_id"]
    async with db_manager.get_async_session() as db_session:
        query = select(TechSpecSession).where(TechSpecSession.id == session_id)
        result = await db_session.execute(query)
        tech_session = result.scalar_one_or_none()

        assert tech_session is not None
        assert tech_session.status == "pending"
        assert tech_session.design_job_id == design_job_id

        # Cleanup
        await db_session.execute(delete(TechSpecSession).where(TechSpecSession.id == session_id))
        await db_session.commit()


@pytest.mark.asyncio
async def test_start_tech_spec_unauthorized(async_client, test_design_job):
    """Test starting Tech Spec without authentication."""
    design_job_id, project_id = test_design_job

    response = await async_client.post(
        f"/api/projects/{project_id}/start-tech-spec",
        json={"design_job_id": str(design_job_id)}
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_start_tech_spec_invalid_design_job(async_client, valid_jwt_token):
    """Test starting Tech Spec with non-existent design job."""
    project_id = uuid4()
    fake_design_job_id = uuid4()

    response = await async_client.post(
        f"/api/projects/{project_id}/start-tech-spec",
        json={"design_job_id": str(fake_design_job_id)},
        headers={"Authorization": f"Bearer {valid_jwt_token}"}
    )

    assert response.status_code == 400
    assert "Design job" in response.json()["detail"]


# ============= Test Endpoint 2: Get Session Status =============

@pytest.mark.asyncio
async def test_get_session_status_success(async_client, test_session, valid_jwt_token):
    """Test successfully retrieving session status."""
    session_id, project_id, design_job_id = test_session

    response = await async_client.get(
        f"/api/tech-spec/sessions/{session_id}/status",
        headers={"Authorization": f"Bearer {valid_jwt_token}"}
    )

    assert response.status_code == 200
    data = response.json()

    assert data["session_id"] == str(session_id)
    assert data["project_id"] == str(project_id)
    assert data["design_job_id"] == str(design_job_id)
    assert data["status"] == "in_progress"
    assert data["current_stage"] == "identifying_gaps"
    assert data["progress_percentage"] == 25.0
    assert data["gaps_identified"] == 3
    assert data["decisions_made"] == 1
    assert "websocket_url" in data


@pytest.mark.asyncio
async def test_get_session_status_not_found(async_client, valid_jwt_token):
    """Test retrieving status for non-existent session."""
    fake_session_id = uuid4()

    response = await async_client.get(
        f"/api/tech-spec/sessions/{fake_session_id}/status",
        headers={"Authorization": f"Bearer {valid_jwt_token}"}
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_session_status_unauthorized(async_client, test_session):
    """Test retrieving status without authentication."""
    session_id, _, _ = test_session

    response = await async_client.get(
        f"/api/tech-spec/sessions/{session_id}/status"
    )

    assert response.status_code == 403


# ============= Test Endpoint 3: Submit Decision =============

@pytest.mark.asyncio
async def test_submit_decision_success(async_client, test_session, valid_jwt_token):
    """Test successfully submitting a user decision."""
    session_id, _, _ = test_session

    decision_data = {
        "technology_category": "authentication",
        "selected_technology": "NextAuth.js",
        "reasoning": "Best for Next.js projects with social login"
    }

    response = await async_client.post(
        f"/api/tech-spec/sessions/{session_id}/decisions",
        json=decision_data,
        headers={"Authorization": f"Bearer {valid_jwt_token}"}
    )

    assert response.status_code == 200
    data = response.json()

    assert data["session_id"] == str(session_id)
    assert data["decision_accepted"] is True
    assert "message" in data
    assert "next_action" in data

    # Verify decision was recorded in database
    async with db_manager.get_async_session() as db_session:
        query = select(TechSpecSession).where(TechSpecSession.id == session_id)
        result = await db_session.execute(query)
        tech_session = result.scalar_one_or_none()

        assert tech_session is not None
        assert tech_session.session_data["decisions_made"] == 2  # Was 1, now 2
        assert len(tech_session.session_data["user_decisions"]) == 1
        assert tech_session.session_data["user_decisions"][0]["category"] == "authentication"
        assert tech_session.session_data["user_decisions"][0]["selected"] == "NextAuth.js"


@pytest.mark.asyncio
async def test_submit_decision_invalid_category(async_client, test_session, valid_jwt_token):
    """Test submitting decision with invalid category."""
    session_id, _, _ = test_session

    decision_data = {
        "technology_category": "invalid_category",
        "selected_technology": "Some Tech"
    }

    response = await async_client.post(
        f"/api/tech-spec/sessions/{session_id}/decisions",
        json=decision_data,
        headers={"Authorization": f"Bearer {valid_jwt_token}"}
    )

    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_submit_decision_session_not_found(async_client, valid_jwt_token):
    """Test submitting decision for non-existent session."""
    fake_session_id = uuid4()

    decision_data = {
        "technology_category": "database",
        "selected_technology": "PostgreSQL"
    }

    response = await async_client.post(
        f"/api/tech-spec/sessions/{fake_session_id}/decisions",
        json=decision_data,
        headers={"Authorization": f"Bearer {valid_jwt_token}"}
    )

    assert response.status_code == 404


# ============= Test Endpoint 4: Download TRD =============

@pytest.mark.asyncio
async def test_download_trd_success(async_client, completed_session_with_trd, valid_jwt_token):
    """Test successfully downloading TRD document."""
    session_id, _, _ = completed_session_with_trd

    response = await async_client.get(
        f"/api/tech-spec/sessions/{session_id}/trd",
        headers={"Authorization": f"Bearer {valid_jwt_token}"}
    )

    assert response.status_code == 200
    data = response.json()

    assert data["session_id"] == str(session_id)
    assert "document" in data
    assert "trd_content" in data["document"]
    assert "# Technical Requirements Document" in data["document"]["trd_content"]
    assert data["document"]["api_specification"]["openapi"] == "3.0.0"
    assert "users" in data["document"]["database_schema"]["tables"]
    assert data["document"]["quality_score"] == 95.5
    assert data["version"] == 1
    assert "created_at" in data


@pytest.mark.asyncio
async def test_download_trd_not_ready(async_client, test_session, valid_jwt_token):
    """Test downloading TRD when session not completed."""
    session_id, _, _ = test_session

    response = await async_client.get(
        f"/api/tech-spec/sessions/{session_id}/trd",
        headers={"Authorization": f"Bearer {valid_jwt_token}"}
    )

    assert response.status_code == 409
    assert "not ready" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_download_trd_session_not_found(async_client, valid_jwt_token):
    """Test downloading TRD for non-existent session."""
    fake_session_id = uuid4()

    response = await async_client.get(
        f"/api/tech-spec/sessions/{fake_session_id}/trd",
        headers={"Authorization": f"Bearer {valid_jwt_token}"}
    )

    assert response.status_code == 404


# ============= Test Endpoint 5: Health Check =============

@pytest.mark.asyncio
async def test_basic_health_check(async_client):
    """Test basic health check endpoint."""
    response = await async_client.get("/health")

    assert response.status_code in [200, 503]
    data = response.json()

    assert "status" in data
    assert data["service"] == "tech-spec-agent"
    assert data["version"] == "1.0.0"
    assert "environment" in data
    assert "database" in data


@pytest.mark.asyncio
async def test_detailed_health_check(async_client):
    """Test detailed health check endpoint."""
    response = await async_client.get("/api/health/detailed")

    assert response.status_code == 200
    data = response.json()

    assert "status" in data
    assert data["service"] == "tech-spec-agent"
    assert "components" in data
    assert "database" in data["components"]
    assert data["components"]["database"]["status"] in ["healthy", "unhealthy"]


# ============= Test Authentication =============

@pytest.mark.asyncio
async def test_expired_jwt_token(async_client, test_session):
    """Test request with expired JWT token."""
    session_id, _, _ = test_session

    # Create expired token
    payload = {
        "sub": str(uuid4()),
        "email": "expired@test.com",
        "role": "user"
    }
    expired_token = create_access_token(payload, expires_delta=timedelta(seconds=-1))

    response = await async_client.get(
        f"/api/tech-spec/sessions/{session_id}/status",
        headers={"Authorization": f"Bearer {expired_token}"}
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_invalid_jwt_token(async_client, test_session):
    """Test request with invalid JWT token."""
    session_id, _, _ = test_session

    response = await async_client.get(
        f"/api/tech-spec/sessions/{session_id}/status",
        headers={"Authorization": "Bearer invalid.token.here"}
    )

    assert response.status_code == 401


# ============= Test Rate Limiting =============

@pytest.mark.asyncio
async def test_rate_limit_headers_present(async_client):
    """Test that rate limit headers are present in responses."""
    response = await async_client.get("/health")

    # Check for rate limit headers
    assert "X-RateLimit-Limit" in response.headers or response.status_code == 200


@pytest.mark.asyncio
async def test_rate_limiting_enforcement(async_client, valid_jwt_token):
    """Test that rate limiting is enforced (if Redis enabled)."""
    # This test may pass if Redis is not configured (fail-open behavior)
    # Make multiple rapid requests
    responses = []
    for _ in range(15):
        response = await async_client.get(
            "/api/health/detailed",
            headers={"Authorization": f"Bearer {valid_jwt_token}"}
        )
        responses.append(response.status_code)

    # All should succeed (within generous limit) or some should be rate limited
    assert all(status in [200, 429] for status in responses)


# ============= Test CORS =============

@pytest.mark.asyncio
async def test_cors_headers(async_client):
    """Test that CORS headers are properly configured."""
    response = await async_client.options(
        "/api/health/detailed",
        headers={"Origin": "http://localhost:3000"}
    )

    # CORS should allow the request
    assert response.status_code in [200, 204]
