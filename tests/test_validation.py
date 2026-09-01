"""
Test input validation on schemas.

These tests verify that:
- Invalid data is rejected with appropriate status codes
- Valid data passes through
- Enum values are enforced
- Optional fields are truly optional
- Email validation works
"""

from datetime import date

import pytest
from fastapi.testclient import TestClient


class TestTransactionValidation:
    """Test transaction validation."""

    def test_create_transaction_missing_required_fields(
        self, client: TestClient, auth_headers: dict
    ):
        """Missing required fields should return 422."""
        # Missing description
        response = client.post(
            "/api/v1/transactions",
            json={"date": str(date.today()), "amount": 10.00, "type": "spend"},
            headers=auth_headers,
        )

        assert response.status_code == 422

    def test_create_transaction_invalid_type(
        self, client: TestClient, auth_headers: dict
    ):
        """Invalid transaction type should return 422."""
        response = client.post(
            "/api/v1/transactions",
            json={
                "date": str(date.today()),
                "description": "Test",
                "amount": 10.00,
                "type": "invalid",
            },
            headers=auth_headers,
        )

        assert response.status_code == 422

    def test_create_transaction_valid_type_spend(
        self, client: TestClient, auth_headers: dict
    ):
        """Type 'spend' is valid."""
        response = client.post(
            "/api/v1/transactions",
            json={
                "date": str(date.today()),
                "description": "Test",
                "amount": 10.00,
                "type": "spend",
            },
            headers=auth_headers,
        )

        assert response.status_code == 201

    def test_create_transaction_valid_type_earn(
        self, client: TestClient, auth_headers: dict
    ):
        """Type 'earn' is valid."""
        response = client.post(
            "/api/v1/transactions",
            json={
                "date": str(date.today()),
                "description": "Test",
                "amount": 10.00,
                "type": "earn",
            },
            headers=auth_headers,
        )

        assert response.status_code == 201

    def test_create_transaction_amount_string(
        self, client: TestClient, auth_headers: dict
    ):
        """Amount as string should be coerced to float."""
        response = client.post(
            "/api/v1/transactions",
            json={
                "date": str(date.today()),
                "description": "Test",
                "amount": "10.50",
                "type": "spend",
            },
            headers=auth_headers,
        )

        assert response.status_code == 201
        assert response.json()["amount"] == 10.50

    def test_create_transaction_amount_negative_stored_as_positive(
        self, client: TestClient, auth_headers: dict
    ):
        """Negative amount should be stored as positive."""
        response = client.post(
            "/api/v1/transactions",
            json={
                "date": str(date.today()),
                "description": "Test",
                "amount": -50.00,
                "type": "spend",
            },
            headers=auth_headers,
        )

        assert response.status_code == 201
        assert response.json()["amount"] == 50.00

    def test_create_transaction_optional_category_id(
        self, client: TestClient, auth_headers: dict
    ):
        """category_id is optional."""
        response = client.post(
            "/api/v1/transactions",
            json={
                "date": str(date.today()),
                "description": "Test",
                "amount": 10.00,
                "type": "spend",
            },
            headers=auth_headers,
        )

        assert response.status_code == 201
        assert response.json()["category_id"] is None

    def test_update_transaction_category_requires_category_id(
        self, client: TestClient, auth_headers: dict, test_transaction
    ):
        """category_id is required for category update."""
        response = client.put(
            f"/api/v1/transactions/{test_transaction.id}/category",
            json={},  # Missing category_id
            headers=auth_headers,
        )

        assert response.status_code == 422


class TestAuthValidation:
    """Test authentication validation."""

    def test_signup_missing_email(self, client: TestClient):
        """Missing email should return 422."""
        response = client.post(
            "/api/v1/auth/signup",
            json={"full_name": "Test", "password": "pass123"},
        )

        assert response.status_code == 422

    def test_signup_invalid_email(self, client: TestClient):
        """Invalid email should return 422."""
        response = client.post(
            "/api/v1/auth/signup",
            json={"email": "not-an-email", "password": "pass123"},
        )

        assert response.status_code == 422

    def test_signup_missing_password(self, client: TestClient):
        """Missing password should return 422."""
        response = client.post(
            "/api/v1/auth/signup",
            json={"email": "test@example.com", "full_name": "Test"},
        )

        assert response.status_code == 422

    def test_signup_valid_with_optional_full_name(self, client: TestClient):
        """full_name is optional."""
        response = client.post(
            "/api/v1/auth/signup",
            json={"email": "newuser@example.com", "password": "pass123"},
        )

        assert response.status_code == 201
        assert response.json()["full_name"] is None

    def test_signup_valid_with_full_name(self, client: TestClient):
        """full_name can be provided."""
        response = client.post(
            "/api/v1/auth/signup",
            json={
                "email": "another@example.com",
                "full_name": "Full Name",
                "password": "pass123",
            },
        )

        assert response.status_code == 201
        assert response.json()["full_name"] == "Full Name"

    def test_signup_duplicate_email_rejected(self, client: TestClient, test_user):
        """Duplicate email returns 400."""
        response = client.post(
            "/api/v1/auth/signup",
            json={
                "email": test_user.email,
                "password": "different",
            },
        )

        assert response.status_code == 400

    def test_login_missing_credentials(self, client: TestClient):
        """Missing credentials returns 422."""
        response = client.post("/api/v1/auth/login", data={})

        assert response.status_code == 422

    def test_login_invalid_credentials(self, client: TestClient, test_user):
        """Invalid email/password returns 401."""
        response = client.post(
            "/api/v1/auth/login",
            data={"username": test_user.email, "password": "wrongpassword"},
        )

        assert response.status_code == 401

    def test_login_nonexistent_email(self, client: TestClient):
        """Non-existent email returns 401."""
        response = client.post(
            "/api/v1/auth/login",
            data={"username": "nonexistent@example.com", "password": "pass"},
        )

        assert response.status_code == 401

    def test_login_valid_credentials(self, client: TestClient, test_user):
        """Valid credentials return 200 with token."""
        response = client.post(
            "/api/v1/auth/login",
            data={"username": test_user.email, "password": "testpass123"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"


class TestCategorySourceValues:
    """Test category_source enum values."""

    def test_category_source_uncategorized(
        self, client: TestClient, auth_headers: dict
    ):
        """Transaction without category has uncategorized source."""
        response = client.post(
            "/api/v1/transactions",
            json={
                "date": str(date.today()),
                "description": "Test",
                "amount": 10.00,
                "type": "spend",
            },
            headers=auth_headers,
        )

        assert response.status_code == 201
        assert response.json()["category_source"] == "uncategorized"

    def test_category_source_manual_correction(
        self, client: TestClient, auth_headers: dict, test_transaction, seed_categories
    ):
        """Manual category update sets manual_correction source."""
        response = client.put(
            f"/api/v1/transactions/{test_transaction.id}/category",
            json={"category_id": seed_categories[0].id},
            headers=auth_headers,
        )

        assert response.status_code == 200
        assert response.json()["category_source"] == "manual_correction"


class TestTransactionSourceValues:
    """Test transaction source enum values."""

    def test_manual_source_on_create(self, client: TestClient, auth_headers: dict):
        """Transaction created via API has manual source."""
        response = client.post(
            "/api/v1/transactions",
            json={
                "date": str(date.today()),
                "description": "Test",
                "amount": 10.00,
                "type": "spend",
            },
            headers=auth_headers,
        )

        assert response.status_code == 201
        assert response.json()["source"] == "manual"
