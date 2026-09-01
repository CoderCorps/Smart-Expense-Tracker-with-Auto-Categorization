"""
Test transaction CRUD operations through the API.

These tests verify that:
- Create transaction endpoint works
- Read single transaction endpoint works
- List transactions endpoint works with filters and pagination
- Update transaction category endpoint works
- Delete transaction endpoint works
- All operations return correct status codes and response data
"""

from datetime import date

import pytest
from fastapi.testclient import TestClient


class TestTransactionCreate:
    """Test creating transactions."""

    def test_create_transaction_uncategorized(self, client: TestClient, auth_headers: dict):
        """Create a transaction without a category."""
        response = client.post(
            "/api/v1/transactions",
            json={
                "date": str(date.today()),
                "description": "Coffee at Starbucks",
                "amount": 5.50,
                "type": "spend",
            },
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["id"] is not None
        assert data["description"] == "Coffee at Starbucks"
        assert data["amount"] == 5.50
        assert data["type"] == "spend"
        assert data["category_id"] is None
        assert data["category_source"] == "uncategorized"
        assert data["source"] == "manual"

    def test_create_transaction_with_category(
        self, client: TestClient, auth_headers: dict, seed_categories
    ):
        """Create a transaction with a category."""
        response = client.post(
            "/api/v1/transactions",
            json={
                "date": str(date.today()),
                "description": "Grocery shopping at Costco",
                "amount": 75.00,
                "type": "spend",
                "category_id": seed_categories[0].id,
            },
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["category_id"] == seed_categories[0].id
        assert data["category_name"] == seed_categories[0].name
        assert data["category_source"] == "manual_correction"  # Set when category provided on create

    def test_create_transaction_earn_type(self, client: TestClient, auth_headers: dict):
        """Create an earn transaction."""
        response = client.post(
            "/api/v1/transactions",
            json={
                "date": str(date.today()),
                "description": "Salary deposit",
                "amount": 5000.00,
                "type": "earn",
            },
            headers=auth_headers,
        )

        assert response.status_code == 201
        assert response.json()["type"] == "earn"

    def test_create_transaction_description_stripped(
        self, client: TestClient, auth_headers: dict
    ):
        """Verify description whitespace is stripped."""
        response = client.post(
            "/api/v1/transactions",
            json={
                "date": str(date.today()),
                "description": "  Padded description  ",
                "amount": 10.00,
                "type": "spend",
            },
            headers=auth_headers,
        )

        assert response.status_code == 201
        assert response.json()["description"] == "Padded description"

    def test_create_transaction_raw_description_set(
        self, client: TestClient, auth_headers: dict
    ):
        """Verify raw_description is stored."""
        description = "Test transaction"
        response = client.post(
            "/api/v1/transactions",
            json={
                "date": str(date.today()),
                "description": description,
                "amount": 10.00,
                "type": "spend",
            },
            headers=auth_headers,
        )

        assert response.status_code == 201
        assert response.json()["raw_description"] == description

    def test_create_transaction_requires_auth(self, client: TestClient):
        """Verify authentication is required."""
        response = client.post(
            "/api/v1/transactions",
            json={
                "date": str(date.today()),
                "description": "Test",
                "amount": 10.00,
                "type": "spend",
            },
        )

        assert response.status_code == 401  # Unauthorized without auth


class TestTransactionRead:
    """Test reading transactions."""

    def test_get_single_transaction(
        self, client: TestClient, auth_headers: dict, test_transaction
    ):
        """Retrieve a single transaction by ID."""
        response = client.get(
            f"/api/v1/transactions/{test_transaction.id}", headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_transaction.id
        assert data["description"] == test_transaction.description
        assert data["amount"] == test_transaction.amount

    def test_get_transaction_not_found(self, client: TestClient, auth_headers: dict):
        """Try to retrieve non-existent transaction."""
        response = client.get("/api/v1/transactions/99999", headers=auth_headers)

        assert response.status_code == 404

    def test_list_transactions_empty(self, client: TestClient, auth_headers: dict):
        """List transactions when none exist."""
        response = client.get("/api/v1/transactions", headers=auth_headers)

        assert response.status_code == 200
        assert response.json() == []

    def test_list_transactions(
        self, client: TestClient, auth_headers: dict, test_transaction
    ):
        """List transactions for authenticated user."""
        response = client.get("/api/v1/transactions", headers=auth_headers)

        assert response.status_code == 200
        transactions = response.json()
        assert len(transactions) == 1
        assert transactions[0]["id"] == test_transaction.id

    def test_list_transactions_pagination(
        self, client: TestClient, auth_headers: dict, db, test_user
    ):
        """Test pagination in list transactions."""
        from app.models.transaction import TransactionSource, TransactionType
        from datetime import date

        # Create multiple transactions
        for i in range(5):
            from app.models.transaction import Transaction

            txn = Transaction(
                user_id=test_user.id,
                date=date.today(),
                description=f"Transaction {i}",
                amount=float(i * 10),
                type=TransactionType.SPEND,
                source=TransactionSource.MANUAL,
            )
            db.add(txn)
        db.commit()

        # Get first page (default page_size=50, so all 5 should appear)
        response = client.get("/api/v1/transactions?page=1", headers=auth_headers)
        assert response.status_code == 200
        assert len(response.json()) == 5

        # Get with custom page size
        response = client.get(
            "/api/v1/transactions?page=1&page_size=2", headers=auth_headers
        )
        assert response.status_code == 200
        assert len(response.json()) == 2

    def test_list_transactions_filter_by_category(
        self, client: TestClient, auth_headers: dict, test_transaction_categorized, seed_categories
    ):
        """Filter transactions by category."""
        cat_id = test_transaction_categorized.category_id
        response = client.get(
            f"/api/v1/transactions?category_id={cat_id}", headers=auth_headers
        )

        assert response.status_code == 200
        transactions = response.json()
        assert len(transactions) == 1
        assert transactions[0]["category_id"] == cat_id

    def test_list_transactions_filter_by_type(
        self, client: TestClient, auth_headers: dict, test_transaction
    ):
        """Filter transactions by type."""
        response = client.get(
            "/api/v1/transactions?type=spend", headers=auth_headers
        )

        assert response.status_code == 200
        transactions = response.json()
        for txn in transactions:
            assert txn["type"] == "spend"

    def test_list_transactions_search_description(
        self, client: TestClient, auth_headers: dict, test_transaction
    ):
        """Search transactions by description."""
        response = client.get(
            "/api/v1/transactions?search=Test", headers=auth_headers
        )

        assert response.status_code == 200
        transactions = response.json()
        assert len(transactions) == 1


class TestTransactionUpdate:
    """Test updating transactions."""

    def test_update_transaction_category(
        self, client: TestClient, auth_headers: dict, test_transaction, seed_categories
    ):
        """Update transaction category."""
        new_category_id = seed_categories[0].id

        response = client.put(
            f"/api/v1/transactions/{test_transaction.id}/category",
            json={"category_id": new_category_id},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["category_id"] == new_category_id
        assert data["category_source"] == "manual_correction"

    def test_update_transaction_category_not_found(
        self, client: TestClient, auth_headers: dict, test_transaction
    ):
        """Try to update with non-existent category."""
        response = client.put(
            f"/api/v1/transactions/{test_transaction.id}/category",
            json={"category_id": 99999},
            headers=auth_headers,
        )

        assert response.status_code == 404

    def test_update_nonexistent_transaction(
        self, client: TestClient, auth_headers: dict, seed_categories
    ):
        """Try to update non-existent transaction."""
        response = client.put(
            "/api/v1/transactions/99999/category",
            json={"category_id": seed_categories[0].id},
            headers=auth_headers,
        )

        assert response.status_code == 404


class TestTransactionDelete:
    """Test deleting transactions."""

    def test_delete_transaction(
        self, client: TestClient, auth_headers: dict, test_transaction
    ):
        """Delete a transaction."""
        response = client.delete(
            f"/api/v1/transactions/{test_transaction.id}", headers=auth_headers
        )

        assert response.status_code == 204

        # Verify it's deleted
        get_response = client.get(
            f"/api/v1/transactions/{test_transaction.id}", headers=auth_headers
        )
        assert get_response.status_code == 404

    def test_delete_nonexistent_transaction(self, client: TestClient, auth_headers: dict):
        """Try to delete non-existent transaction."""
        response = client.delete(
            "/api/v1/transactions/99999", headers=auth_headers
        )

        assert response.status_code == 404
