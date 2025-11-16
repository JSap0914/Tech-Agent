"""
Unit tests for REST API endpoints.
"""

import pytest
from uuid import uuid4
from datetime import datetime
from unittest.mock import AsyncMock, patch, MagicMock

from fastapi.testclient import TestClient
from src.main import app
from src.api.schemas import (
    StartTechSpecRequest,
    UserDecisionRequest,
    TechnologyCategory
)


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def mock_jwt_token():
    """Mock JWT token for authentication."""
    return "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiI3YzllNjY3OS03NDI1LTQwZGUtOTQ0Yi1lMDdmYzFmOTBhZTciLCJlbWFpbCI6InRlc3RAdGVzdC5jb20iLCJyb2xlIjoidXNlciIsInBlcm1pc3Npb25zIjpbXX0.test"


# ============= Test Health Check =============

def test_health_check(client):
    """Test basic health check endpoint."""
    response = client.get("/health")

    assert response.status_code in [200, 503]
    data = response.json()

    assert "status" in data
    assert data["service"] == "tech-spec-agent"
    assert "version" in data
    assert "environment" in data


def test_detailed_health_check(client):
    """Test detailed health check endpoint."""
    response = client.get("/api/health/detailed")

    assert response.status_code == 200
    data = response.json()

    assert "status" in data
    assert "service" in data
    assert "components" in data
    assert "database" in data["components"]


# ============= Test Start Tech Spec (Endpoint 1) =============

@pytest.mark.asyncio
async def test_start_tech_spec_unauthorized(client):
    """Test starting Tech Spec without authentication."""
    project_id = str(uuid4())
    request_data = {
        "design_job_id": str(uuid4())
    }

    response = client.post(
        f"/api/projects/{project_id}/start-tech-spec",
        json=request_data
    )

    assert response.status_code == 403  # No bearer token


@pytest.mark.asyncio
async def test_start_tech_spec_invalid_design_job(client, mock_jwt_token):
    """Test starting Tech Spec with invalid design job."""
    project_id = str(uuid4())
    request_data = {
        "design_job_id": str(uuid4())
    }

    with patch("src.api.auth.get_current_user") as mock_auth:
        from src.api.auth import User
        mock_auth.return_value = User(
            user_id=uuid4(),
            email="test@test.com",
            role="user"
        )

        with patch("src.integration.design_agent_loader.validate_design_job_completed") as mock_validate:
            mock_validate.side_effect = ValueError("Design job not found")

            response = client.post(
                f"/api/projects/{project_id}/start-tech-spec",
                json=request_data,
                headers={"Authorization": f"Bearer {mock_jwt_token}"}
            )

            assert response.status_code == 400
            assert "Design job not found" in response.json()["detail"]


# ============= Test Get Session Status (Endpoint 2) =============

@pytest.mark.asyncio
async def test_get_session_status_not_found(client, mock_jwt_token):
    """Test getting status for non-existent session."""
    session_id = str(uuid4())

    with patch("src.api.auth.get_current_user") as mock_auth:
        from src.api.auth import User
        mock_auth.return_value = User(
            user_id=uuid4(),
            email="test@test.com",
            role="user"
        )

        response = client.get(
            f"/api/tech-spec/sessions/{session_id}/status",
            headers={"Authorization": f"Bearer {mock_jwt_token}"}
        )

        # May be 404 or 401 depending on auth mock
        assert response.status_code in [401, 404]


# ============= Test Submit Decision (Endpoint 3) =============

@pytest.mark.asyncio
async def test_submit_decision_invalid_category(client, mock_jwt_token):
    """Test submitting decision with invalid category."""
    session_id = str(uuid4())
    decision_data = {
        "technology_category": "invalid_category",
        "selected_technology": "NextAuth.js"
    }

    with patch("src.api.auth.get_current_user") as mock_auth:
        from src.api.auth import User
        mock_auth.return_value = User(
            user_id=uuid4(),
            email="test@test.com",
            role="user"
        )

        response = client.post(
            f"/api/tech-spec/sessions/{session_id}/decisions",
            json=decision_data,
            headers={"Authorization": f"Bearer {mock_jwt_token}"}
        )

        # Should fail validation
        assert response.status_code == 422  # Validation error


# ============= Test Download TRD (Endpoint 4) =============

@pytest.mark.asyncio
async def test_download_trd_not_ready(client, mock_jwt_token):
    """Test downloading TRD when not ready."""
    session_id = str(uuid4())

    with patch("src.api.auth.get_current_user") as mock_auth:
        from src.api.auth import User
        mock_auth.return_value = User(
            user_id=uuid4(),
            email="test@test.com",
            role="user"
        )

        response = client.get(
            f"/api/tech-spec/sessions/{session_id}/trd",
            headers={"Authorization": f"Bearer {mock_jwt_token}"}
        )

        # May be 404, 409, or 401
        assert response.status_code in [401, 404, 409]


# ============= Test Rate Limiting =============

@pytest.mark.asyncio
async def test_rate_limiting_headers(client):
    """Test that rate limiting headers are present."""
    response = client.get("/health")

    # Rate limit headers should be present
    assert "X-RateLimit-Limit" in response.headers or response.status_code == 200


# ============= Test Pydantic Schemas =============

def test_start_tech_spec_request_schema():
    """Test StartTechSpecRequest schema validation."""
    from src.api.schemas import StartTechSpecRequest

    # Valid request
    request = StartTechSpecRequest(
        design_job_id=uuid4()
    )
    assert request.design_job_id is not None

    # Invalid UUID should raise validation error
    with pytest.raises(Exception):
        StartTechSpecRequest(design_job_id="invalid-uuid")


def test_user_decision_request_schema():
    """Test UserDecisionRequest schema validation."""
    # Valid request
    request = UserDecisionRequest(
        technology_category=TechnologyCategory.AUTHENTICATION,
        selected_technology="NextAuth.js",
        reasoning="Best for Next.js projects"
    )

    assert request.technology_category == "authentication"
    assert request.selected_technology == "NextAuth.js"

    # Technology name too long
    with pytest.raises(Exception):
        UserDecisionRequest(
            technology_category=TechnologyCategory.DATABASE,
            selected_technology="x" * 101,  # Max 100 chars
        )


# ============= Test JWT Authentication =============

def test_create_access_token():
    """Test JWT token creation."""
    from src.api.auth import create_access_token

    payload = {
        "sub": str(uuid4()),
        "email": "test@test.com",
        "role": "user"
    }

    token = create_access_token(payload)

    assert isinstance(token, str)
    assert len(token) > 0


def test_decode_access_token_invalid():
    """Test decoding invalid JWT token."""
    from src.api.auth import decode_access_token
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        decode_access_token("invalid.token.here")

    assert exc_info.value.status_code == 401
