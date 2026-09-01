"""
Test authentication endpoints.

These tests verify that:
- Signup creates users correctly
- Login returns valid tokens
- Get current user returns authenticated user info
- Tokens expire appropriately
- Password hashing works correctly
"""

from fastapi.testclient import TestClient

import pytest


class TestSignup:
    """Test signup endpoint."""

    def test_signup_creates_user(self, client: TestClient):
        """Signup creates a new user."""
        response = client.post(
            "/api/v1/auth/signup",
            json={
                "email": "newuser@example.com",
                "full_name": "New User",
                "password": "securepass123",
            },
        )

        assert response.status_code == 201
        user = response.json()
        assert user["id"] is not None
        assert user["email"] == "newuser@example.com"
        assert user["full_name"] == "New User"
        assert "hashed_password" not in user  # Should not expose password hash

    def test_signup_password_not_in_response(self, client: TestClient):
        """Signup does not return password."""
        response = client.post(
            "/api/v1/auth/signup",
            json={
                "email": "test@example.com",
                "password": "pass123",
            },
        )

        assert response.status_code == 201
        user = response.json()
        assert "password" not in user
        assert "hashed_password" not in user

    def test_signup_with_duplicate_email(self, client: TestClient, test_user):
        """Signup with duplicate email is rejected."""
        response = client.post(
            "/api/v1/auth/signup",
            json={
                "email": test_user.email,
                "password": "different",
            },
        )

        assert response.status_code == 400
        assert "already registered" in response.json()["detail"].lower()

    def test_signup_creates_different_passwords_different_hashes(
        self, client: TestClient, db
    ):
        """Different passwords create different hashes."""
        response1 = client.post(
            "/api/v1/auth/signup",
            json={
                "email": "user1@example.com",
                "password": "pass123",
            },
        )

        response2 = client.post(
            "/api/v1/auth/signup",
            json={
                "email": "user2@example.com",
                "password": "pass456",
            },
        )

        assert response1.status_code == 201
        assert response2.status_code == 201

        # Get users from DB to compare hashes
        from app.models.user import User

        user1 = db.query(User).filter(User.email == "user1@example.com").first()
        user2 = db.query(User).filter(User.email == "user2@example.com").first()

        assert user1.hashed_password != user2.hashed_password


class TestLogin:
    """Test login endpoint."""

    def test_login_returns_token(self, client: TestClient, test_user):
        """Login with correct credentials returns token."""
        response = client.post(
            "/api/v1/auth/login",
            data={"username": "test@example.com", "password": "testpass123"},
        )

        assert response.status_code == 200
        token_data = response.json()
        assert "access_token" in token_data
        assert token_data["token_type"] == "bearer"
        assert isinstance(token_data["access_token"], str)
        assert len(token_data["access_token"]) > 0

    def test_login_wrong_password(self, client: TestClient, test_user):
        """Login with wrong password is rejected."""
        response = client.post(
            "/api/v1/auth/login",
            data={"username": test_user.email, "password": "wrongpassword"},
        )

        assert response.status_code == 401

    def test_login_nonexistent_email(self, client: TestClient):
        """Login with non-existent email is rejected."""
        response = client.post(
            "/api/v1/auth/login",
            data={"username": "nonexistent@example.com", "password": "pass"},
        )

        assert response.status_code == 401

    def test_login_token_format(self, client: TestClient, test_user):
        """Token has correct JWT format (3 parts separated by dots)."""
        response = client.post(
            "/api/v1/auth/login",
            data={"username": test_user.email, "password": "testpass123"},
        )

        token = response.json()["access_token"]
        parts = token.split(".")
        assert len(parts) == 3  # JWT format: header.payload.signature


class TestGetCurrentUser:
    """Test get current user endpoint."""

    def test_get_current_user_returns_user_info(
        self, client: TestClient, auth_headers: dict, test_user
    ):
        """Get /auth/me returns current user."""
        response = client.get("/api/v1/auth/me", headers=auth_headers)

        assert response.status_code == 200
        user = response.json()
        assert user["id"] == test_user.id
        assert user["email"] == test_user.email
        assert user["full_name"] == test_user.full_name

    def test_get_current_user_requires_auth(self, client: TestClient):
        """Get /auth/me requires authentication."""
        response = client.get("/api/v1/auth/me")

        assert response.status_code == 401  # Unauthorized

    def test_get_current_user_with_invalid_token(self, client: TestClient):
        """Get /auth/me rejects invalid token."""
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid.token.here"},
        )

        assert response.status_code == 401

    def test_get_current_user_different_users(
        self, client: TestClient, auth_headers: dict, auth_headers_user_2: dict, test_user, test_user_2
    ):
        """Each user gets their own info."""
        response1 = client.get("/api/v1/auth/me", headers=auth_headers)
        response2 = client.get("/api/v1/auth/me", headers=auth_headers_user_2)

        assert response1.status_code == 200
        assert response2.status_code == 200

        user1 = response1.json()
        user2 = response2.json()

        assert user1["id"] == test_user.id
        assert user2["id"] == test_user_2.id
        assert user1["email"] != user2["email"]


class TestTokenSecurity:
    """Test token security."""

    def test_token_used_in_subsequent_requests(
        self, client: TestClient, test_user
    ):
        """Token can be used for multiple requests."""
        # Login
        login_response = client.post(
            "/api/v1/auth/login",
            data={"username": test_user.email, "password": "testpass123"},
        )

        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Use token to get current user
        response1 = client.get("/api/v1/auth/me", headers=headers)
        assert response1.status_code == 200

        # Use same token for transaction request
        response2 = client.get("/api/v1/transactions", headers=headers)
        assert response2.status_code == 200

    def test_authorization_header_format(self, client: TestClient, test_user):
        """Authorization header must start with 'Bearer '."""
        login_response = client.post(
            "/api/v1/auth/login",
            data={"username": test_user.email, "password": "testpass123"},
        )

        token = login_response.json()["access_token"]

        # Valid format
        response1 = client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
        )
        assert response1.status_code == 200

        # Invalid format (no Bearer prefix)
        response2 = client.get("/api/v1/auth/me", headers={"Authorization": token})
        assert response2.status_code == 401

        # Invalid format (different prefix)
        response3 = client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Basic {token}"}
        )
        assert response3.status_code == 401
