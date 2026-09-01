"""
Test authorization and user isolation.

These tests verify that:
- User A cannot access User B's transactions
- User A cannot update User B's transactions
- User A cannot delete User B's transactions
- Authorization checks are enforced at all endpoints
"""

import pytest
from fastapi.testclient import TestClient


class TestUserIsolation:
    """Test that users cannot access each other's data."""

    def test_user_cannot_access_other_users_transaction(
        self,
        client: TestClient,
        auth_headers: dict,
        auth_headers_user_2: dict,
        test_user,
        test_user_2,
        db,
    ):
        """User A cannot retrieve User B's transaction."""
        from app.models.transaction import Transaction, TransactionSource, TransactionType
        from datetime import date

        # User 2 creates a transaction
        txn = Transaction(
            user_id=test_user_2.id,
            date=date.today(),
            description="User 2's transaction",
            amount=100.0,
            type=TransactionType.SPEND,
            source=TransactionSource.MANUAL,
        )
        db.add(txn)
        db.commit()
        db.refresh(txn)

        # User 1 tries to retrieve User 2's transaction
        response = client.get(
            f"/api/v1/transactions/{txn.id}", headers=auth_headers
        )

        assert response.status_code == 404

    def test_user_cannot_update_other_users_transaction(
        self,
        client: TestClient,
        auth_headers: dict,
        auth_headers_user_2: dict,
        test_user_2,
        seed_categories,
        db,
    ):
        """User A cannot update User B's transaction."""
        from app.models.transaction import Transaction, TransactionSource, TransactionType
        from datetime import date

        # User 2 creates a transaction
        txn = Transaction(
            user_id=test_user_2.id,
            date=date.today(),
            description="User 2's transaction",
            amount=100.0,
            type=TransactionType.SPEND,
            source=TransactionSource.MANUAL,
        )
        db.add(txn)
        db.commit()
        db.refresh(txn)

        # User 1 tries to update User 2's transaction
        response = client.put(
            f"/api/v1/transactions/{txn.id}/category",
            json={"category_id": seed_categories[0].id},
            headers=auth_headers,
        )

        assert response.status_code == 404

    def test_user_cannot_delete_other_users_transaction(
        self,
        client: TestClient,
        auth_headers: dict,
        auth_headers_user_2: dict,
        test_user_2,
        db,
    ):
        """User A cannot delete User B's transaction."""
        from app.models.transaction import Transaction, TransactionSource, TransactionType
        from datetime import date

        # User 2 creates a transaction
        txn = Transaction(
            user_id=test_user_2.id,
            date=date.today(),
            description="User 2's transaction",
            amount=100.0,
            type=TransactionType.SPEND,
            source=TransactionSource.MANUAL,
        )
        db.add(txn)
        db.commit()
        db.refresh(txn)

        # User 1 tries to delete User 2's transaction
        response = client.delete(
            f"/api/v1/transactions/{txn.id}", headers=auth_headers
        )

        assert response.status_code == 404

    def test_user_list_only_sees_own_transactions(
        self,
        client: TestClient,
        auth_headers: dict,
        auth_headers_user_2: dict,
        test_user,
        test_user_2,
        db,
    ):
        """User A only sees their own transactions in list."""
        from app.models.transaction import Transaction, TransactionSource, TransactionType
        from datetime import date

        # Create transaction for User 1
        txn1 = Transaction(
            user_id=test_user.id,
            date=date.today(),
            description="User 1's transaction",
            amount=100.0,
            type=TransactionType.SPEND,
            source=TransactionSource.MANUAL,
        )
        db.add(txn1)

        # Create transaction for User 2
        txn2 = Transaction(
            user_id=test_user_2.id,
            date=date.today(),
            description="User 2's transaction",
            amount=200.0,
            type=TransactionType.SPEND,
            source=TransactionSource.MANUAL,
        )
        db.add(txn2)
        db.commit()

        # User 1 lists transactions
        response = client.get("/api/v1/transactions", headers=auth_headers)

        assert response.status_code == 200
        transactions = response.json()
        assert len(transactions) == 1
        assert transactions[0]["description"] == "User 1's transaction"

        # User 2 lists transactions
        response = client.get("/api/v1/transactions", headers=auth_headers_user_2)

        assert response.status_code == 200
        transactions = response.json()
        assert len(transactions) == 1
        assert transactions[0]["description"] == "User 2's transaction"


class TestAuthenticationRequired:
    """Test that authentication is required for protected endpoints."""

    def test_create_transaction_requires_auth(self, client: TestClient):
        """Create transaction requires authentication."""
        from datetime import date

        response = client.post(
            "/api/v1/transactions",
            json={
                "date": str(date.today()),
                "description": "Test",
                "amount": 10.00,
                "type": "spend",
            },
        )

        assert response.status_code == 401  # Unauthorized

    def test_list_transactions_requires_auth(self, client: TestClient):
        """List transactions requires authentication."""
        response = client.get("/api/v1/transactions")

        assert response.status_code == 401  # Unauthorized

    def test_get_transaction_requires_auth(self, client: TestClient):
        """Get transaction requires authentication."""
        response = client.get("/api/v1/transactions/1")

        assert response.status_code == 401  # Unauthorized

    def test_update_transaction_requires_auth(self, client: TestClient):
        """Update transaction requires authentication."""
        response = client.put(
            "/api/v1/transactions/1/category", json={"category_id": 1}
        )

        assert response.status_code == 401  # Unauthorized

    def test_delete_transaction_requires_auth(self, client: TestClient):
        """Delete transaction requires authentication."""
        response = client.delete("/api/v1/transactions/1")

        assert response.status_code == 401

    def test_invalid_token_rejected(self, client: TestClient):
        """Invalid token is rejected."""
        response = client.get(
            "/api/v1/transactions",
            headers={"Authorization": "Bearer invalid.token.here"},
        )

        assert response.status_code == 401
