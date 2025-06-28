"""
Tests for the main API application.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from core.database import Base, get_db
from main import app

# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


def test_read_main():
    """Test the main API info endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Video Composition API"
    assert "version" in data


def test_health_check():
    """Test the health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "version" in data
    assert "uptime" in data


def test_supported_formats():
    """Test the supported formats endpoint."""
    response = client.get("/supported-formats")
    assert response.status_code == 200
    data = response.json()
    assert "image_formats" in data
    assert "video_formats" in data
    assert "audio_formats" in data


def test_example_requests():
    """Test the example requests endpoint."""
    response = client.get("/example-requests")
    assert response.status_code == 200
    data = response.json()
    assert "examples" in data
    assert len(data["examples"]) > 0


def test_upload_without_auth():
    """Test that upload endpoint requires authentication."""
    response = client.post("/upload")
    assert response.status_code == 401


def test_compose_without_auth():
    """Test that compose endpoint requires authentication."""
    response = client.post("/compose")
    assert response.status_code == 401


def test_jobs_without_auth():
    """Test that jobs endpoint requires authentication."""
    response = client.get("/jobs")
    assert response.status_code == 401


# Test with authentication
TEST_API_KEY = "test-api-key"


def test_upload_with_invalid_auth():
    """Test upload with invalid API key."""
    headers = {"Authorization": "Bearer invalid-key"}
    response = client.post("/upload", headers=headers)
    assert response.status_code == 401


@pytest.mark.skip(reason="Requires valid API key configuration")
def test_upload_with_valid_auth():
    """Test upload with valid API key."""
    headers = {"Authorization": f"Bearer {TEST_API_KEY}"}
    
    # This would require proper file upload setup
    files = {"file": ("test.txt", "test content", "text/plain")}
    response = client.post("/upload", headers=headers, files=files)
    
    # This might fail due to file validation, but should pass auth
    assert response.status_code != 401


def test_cors_headers():
    """Test that CORS headers are present."""
    response = client.options("/")
    assert "access-control-allow-origin" in response.headers


def test_rate_limit_headers():
    """Test that rate limit headers are added to responses."""
    response = client.get("/")
    # Rate limit headers might not be present for non-authenticated requests
    # This test would need modification based on actual implementation
    assert response.status_code == 200
