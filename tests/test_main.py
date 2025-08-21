"""
Test the main FastAPI application.
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_root_endpoint():
    """Test the root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "CreatorPulse API"
    assert data["version"] == "1.0.0"


def test_health_check():
    """Test the basic health check endpoint."""
    response = client.get("/health/")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["status"] == "healthy"
    assert "timestamp" in data["data"]
    assert data["data"]["version"] == "1.0.0"


def test_api_v1_info():
    """Test the API v1 info endpoint."""
    response = client.get("/v1/")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "CreatorPulse API v1"
    assert data["version"] == "1.0.0"
    assert "endpoints" in data