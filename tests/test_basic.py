"""
Basic tests for Clyrdia API
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_root_endpoint():
    """Test root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "Clyrdia Contract Intelligence API" in data["message"]


def test_health_endpoint():
    """Test health endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] == "healthy"


def test_api_docs_disabled_in_production():
    """Test that API docs are disabled in production"""
    # This test assumes production environment
    response = client.get("/docs")
    assert response.status_code == 404


def test_cors_headers():
    """Test CORS headers are present"""
    response = client.options("/")
    assert "access-control-allow-origin" in response.headers


def test_metrics_endpoint():
    """Test metrics endpoint"""
    response = client.get("/metrics")
    assert response.status_code == 200
    # Should contain Prometheus metrics
    assert "http_requests_total" in response.text 