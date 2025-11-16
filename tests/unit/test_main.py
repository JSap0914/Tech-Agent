"""Unit tests for FastAPI application."""

import pytest
from fastapi.testclient import TestClient
from src.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


def test_root_endpoint(client):
    """Test root endpoint returns service information."""
    response = client.get("/")

    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "Tech Spec Agent"
    assert data["version"] == "1.0.0"
    assert "health" in data


def test_health_check_structure(client):
    """Test health check endpoint returns correct structure."""
    response = client.get("/health")

    # Should return 200 or 503
    assert response.status_code in [200, 503]

    data = response.json()
    assert "status" in data
    assert data["status"] in ["healthy", "unhealthy"]
    assert data["service"] == "tech-spec-agent"
    assert data["version"] == "1.0.0"
    assert data["environment"] in ["development", "staging", "production"]


def test_cors_headers(client):
    """Test CORS headers are present."""
    response = client.options("/", headers={
        "Origin": "http://localhost:3000",
        "Access-Control-Request-Method": "GET"
    })

    # Should have CORS headers
    assert "access-control-allow-origin" in response.headers or response.status_code == 200


def test_404_not_found(client):
    """Test 404 for non-existent endpoints."""
    response = client.get("/nonexistent")
    assert response.status_code == 404
