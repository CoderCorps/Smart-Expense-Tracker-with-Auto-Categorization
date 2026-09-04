"""
Test database initialization and configuration.

These tests verify that:
- Database engine is properly configured
- Session factory works correctly
- Default categories are seeded on startup
"""

import pytest
from sqlalchemy.orm import Session

from backend.app.models.category import Category, DEFAULT_CATEGORIES
from backend.app.models.transaction import Transaction
from backend.app.models.user import User


class TestDatabase:
    """Test database setup and initialization."""

    def test_database_creates_tables(self, db: Session):
        """Verify that all required tables are created."""
        # Get all table names
        from sqlalchemy import inspect
        inspector = inspect(db.connection())
        tables = inspector.get_table_names()

        assert "users" in tables
        assert "categories" in tables
        assert "transactions" in tables

    def test_database_session_yields_and_closes(self, db: Session):
        """Verify database session is properly managed."""
        # If we got here without an error, the session was created and yielded
        assert db is not None
        assert db.is_active

    def test_seed_default_categories(self, db: Session, seed_categories):
        """Verify default categories are seeded."""
        categories = db.query(Category).all()
        category_names = {c.name for c in categories}

        for expected_name in DEFAULT_CATEGORIES:
            assert expected_name in category_names

        assert len(categories) == len(DEFAULT_CATEGORIES)

    def test_categories_are_marked_default(self, db: Session, seed_categories):
        """Verify seeded categories have is_default=True."""
        categories = db.query(Category).all()
        for category in categories:
            assert category.is_default is True

    def test_category_descriptions_nullable(self, db: Session, seed_categories):
        """Verify category descriptions can be null."""
        category = db.query(Category).first()
        # Default categories don't have descriptions set
        # This should be allowed (nullable)
        assert category.description is None or isinstance(category.description, str)

    def test_user_table_has_constraints(self, db: Session, test_user: User):
        """Verify user table constraints."""
        # Email should be unique
        from sqlalchemy import text

        # Try to insert duplicate email
        from backend.app.core.security import hash_password

        duplicate_user = User(
            email=test_user.email,  # Same email
            full_name="Another User",
            hashed_password=hash_password("differentpass"),
        )
        db.add(duplicate_user)
        with pytest.raises(Exception):  # SQLAlchemy will raise IntegrityError
            db.commit()

    def test_transaction_table_foreign_keys(self, db: Session):
        """Verify transaction foreign key constraints."""
        from backend.app.models.transaction import TransactionSource, TransactionType

        # Try to create transaction with invalid user_id
        invalid_txn = Transaction(
            user_id=99999,  # Non-existent user
            date="2026-01-01",
            description="Invalid",
            amount=100.0,
            type=TransactionType.SPEND,
            source=TransactionSource.MANUAL,
        )
        db.add(invalid_txn)
        # This will fail on commit due to foreign key constraint
        with pytest.raises(Exception):
            db.commit()
