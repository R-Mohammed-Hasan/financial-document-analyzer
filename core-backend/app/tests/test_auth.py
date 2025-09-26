"""
Authentication tests.

This module contains tests for authentication-related functionality.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from main import app
from db.base import Base
from db.session import get_db
from core.config import settings


# Test database setup
@pytest.fixture
def test_db():
    """Create test database."""
    engine = create_engine(
        "sqlite:///./test.db",
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

    yield TestingSessionLocal()

    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


def test_login_success(client):
    """Test successful login."""
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": "testpassword123"},
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


def test_login_invalid_credentials(client):
    """Test login with invalid credentials."""
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": "wrongpassword"},
    )

    assert response.status_code == 401
    assert "Incorrect email or password" in response.json()["detail"]


def test_login_missing_fields(client):
    """Test login with missing fields."""
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "test@example.com"
            # Missing password
        },
    )

    assert response.status_code == 422


def test_register_success(client):
    """Test successful registration."""
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "newuser@example.com",
            "username": "newuser",
            "password": "newpassword123",
            "first_name": "New",
            "last_name": "User",
            "accept_terms": True,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["user_id"] == 1
    assert data["email"] == "newuser@example.com"


def test_register_existing_email(client):
    """Test registration with existing email."""
    # First register a user
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "existing@example.com",
            "username": "existinguser",
            "password": "password123",
            "accept_terms": True,
        },
    )

    # Try to register with same email
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "existing@example.com",
            "username": "anotheruser",
            "password": "password123",
            "accept_terms": True,
        },
    )

    assert response.status_code == 400
    assert "User with this email already exists" in response.json()["detail"]


def test_register_weak_password(client):
    """Test registration with weak password."""
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "weak@example.com",
            "username": "weakuser",
            "password": "123",  # Too short
            "accept_terms": True,
        },
    )

    assert response.status_code == 422


def test_refresh_token_success(client):
    """Test successful token refresh."""
    # First login to get refresh token
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": "testpassword123"},
    )

    refresh_token = login_response.json()["refresh_token"]

    # Refresh token
    response = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": refresh_token}
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_refresh_invalid_token(client):
    """Test refresh with invalid token."""
    response = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": "invalid_token"}
    )

    assert response.status_code == 401
    assert "Invalid refresh token" in response.json()["detail"]


def test_logout(client):
    """Test logout."""
    response = client.post("/api/v1/auth/logout")

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "Logged out successfully" in data["message"]


def test_password_reset_request(client):
    """Test password reset request."""
    response = client.post(
        "/api/v1/auth/password-reset", json={"email": "test@example.com"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "Password reset instructions sent" in data["message"]


def test_get_current_user(client):
    """Test getting current user info."""
    # First login to get token
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": "testpassword123"},
    )

    token = login_response.json()["access_token"]

    # Get current user
    response = client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 1
    assert data["email"] == "user_1@example.com"
    assert data["username"] == "user_1"


def test_get_current_user_invalid_token(client):
    """Test getting current user with invalid token."""
    response = client.get(
        "/api/v1/auth/me", headers={"Authorization": "Bearer invalid_token"}
    )

    assert response.status_code == 401
    assert "Invalid authentication token" in response.json()["detail"]
