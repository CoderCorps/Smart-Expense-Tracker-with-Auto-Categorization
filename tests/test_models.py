"""
Test data models and their fields.

These tests verify that:
- All model fields exist and have correct types
- Enum values are correct
- Relationships work properly
"""

from datetime import datetime

import pytest
from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.transaction import CategorySource, Transaction, TransactionSource, TransactionType
from app.models.user import User


class TestUserModel:
    """Test User model fields and constraints."""

    def test_user_has_required_fields(self, test_user: User):
        """Verify User has all required fields."""
        assert hasattr(test_user, "id")
        assert hasattr(test_user, "email")
        assert hasattr(test_user, "full_name")
        assert hasattr(test_user, "hashed_password")
        assert hasattr(test_user, "created_at")

    def test_user_id_is_primary_key(self, test_user: User):
        """Verify user id is set (primary key)."""
        assert test_user.id is not None
        assert isinstance(test_user.id, int)

    def test_user_email_is_stored(self, test_user: User):
        """Verify email is stored correctly."""
        assert test_user.email == "test@example.com"

    def test_user_full_name_optional(self, db: Session):
        """Verify full_name is optional."""
        from app.core.security import hash_password

        user = User(
            email="noname@example.com", hashed_password=hash_password("pass")
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        assert user.full_name is None

    def test_user_created_at_set_automatically(self, test_user: User):
        """Verify created_at is set automatically."""
        assert test_user.created_at is not None
        assert isinstance(test_user.created_at, datetime)

    def test_user_password_hashed(self, test_user: User):
        """Verify password is hashed, not plaintext."""
        assert test_user.hashed_password != "testpass123"
        assert len(test_user.hashed_password) > 20  # Bcrypt hashes are long


class TestCategoryModel:
    """Test Category model fields and constraints."""

    def test_category_has_required_fields(self, seed_categories):
        """Verify Category has all required fields."""
        category = seed_categories[0]
        assert hasattr(category, "id")
        assert hasattr(category, "name")
        assert hasattr(category, "description")
        assert hasattr(category, "is_default")
        assert hasattr(category, "created_at")

    def test_category_id_is_primary_key(self, seed_categories):
        """Verify category id is set (primary key)."""
        category = seed_categories[0]
        assert category.id is not None
        assert isinstance(category.id, int)

    def test_category_name_unique(self, db: Session, seed_categories):
        """Verify category name is unique."""
        existing = seed_categories[0]

        duplicate = Category(name=existing.name, is_default=True)
        db.add(duplicate)

        with pytest.raises(Exception):  # IntegrityError on duplicate name
            db.commit()

    def test_category_description_nullable(self, db: Session):
        """Verify category description is nullable."""
        category = Category(name="Test Category", description=None)
        db.add(category)
        db.commit()
        db.refresh(category)

        assert category.description is None

    def test_category_is_default_flag(self, db: Session):
        """Verify is_default flag works."""
        default_cat = Category(name="Default", is_default=True)
        custom_cat = Category(name="Custom", is_default=False)

        db.add(default_cat)
        db.add(custom_cat)
        db.commit()
        db.refresh(default_cat)
        db.refresh(custom_cat)

        assert default_cat.is_default is True
        assert custom_cat.is_default is False

    def test_category_created_at_set_automatically(self, seed_categories):
        """Verify created_at is set automatically."""
        category = seed_categories[0]
        assert category.created_at is not None
        assert isinstance(category.created_at, datetime)


class TestTransactionModel:
    """Test Transaction model fields and constraints."""

    def test_transaction_has_required_fields(self, test_transaction: Transaction):
        """Verify Transaction has all required fields."""
        assert hasattr(test_transaction, "id")
        assert hasattr(test_transaction, "user_id")
        assert hasattr(test_transaction, "date")
        assert hasattr(test_transaction, "description")
        assert hasattr(test_transaction, "raw_description")
        assert hasattr(test_transaction, "amount")
        assert hasattr(test_transaction, "type")
        assert hasattr(test_transaction, "category_id")
        assert hasattr(test_transaction, "category_source")
        assert hasattr(test_transaction, "source")
        assert hasattr(test_transaction, "created_at")

    def test_transaction_id_is_primary_key(self, test_transaction: Transaction):
        """Verify transaction id is set (primary key)."""
        assert test_transaction.id is not None
        assert isinstance(test_transaction.id, int)

    def test_transaction_type_enum(self, test_transaction: Transaction):
        """Verify transaction type is correct enum."""
        assert test_transaction.type == TransactionType.SPEND
        assert isinstance(test_transaction.type, TransactionType)

    def test_transaction_amount_positive(self, test_transaction: Transaction):
        """Verify amount is positive number."""
        assert test_transaction.amount > 0
        assert isinstance(test_transaction.amount, float)

    def test_transaction_category_id_nullable(self, test_transaction: Transaction):
        """Verify category_id can be null."""
        assert test_transaction.category_id is None

    def test_transaction_category_id_set(self, test_transaction_categorized: Transaction):
        """Verify category_id can be set."""
        assert test_transaction_categorized.category_id is not None
        assert isinstance(test_transaction_categorized.category_id, int)

    def test_transaction_source_enum(self, test_transaction: Transaction):
        """Verify transaction source is correct enum."""
        assert test_transaction.source == TransactionSource.MANUAL
        assert isinstance(test_transaction.source, TransactionSource)

    def test_transaction_category_source_default(self, test_transaction: Transaction):
        """Verify category_source has default value."""
        assert test_transaction.category_source is not None
        # Should be set when created (either UNCATEGORIZED or MANUAL_CORRECTION)
        assert isinstance(test_transaction.category_source, CategorySource)

    def test_all_transaction_sources(self, db: Session, test_user: User, seed_categories):
        """Verify all TransactionSource enum values work."""
        from datetime import date as date_type
        for source in TransactionSource:
            txn = Transaction(
                user_id=test_user.id,
                date=date_type(2026, 1, 1),
                description=f"Test {source.value}",
                amount=50.0,
                type=TransactionType.SPEND,
                source=source,
            )
            db.add(txn)
        db.commit()

        all_txns = db.query(Transaction).all()
        sources = {t.source for t in all_txns}
        assert len(sources) == len(TransactionSource)

    def test_all_category_sources(self, db: Session, test_user: User):
        """Verify all CategorySource enum values work."""
        from datetime import date as date_type
        for cat_source in CategorySource:
            txn = Transaction(
                user_id=test_user.id,
                date=date_type(2026, 1, 1),
                description=f"Test {cat_source.value}",
                amount=50.0,
                type=TransactionType.SPEND,
                category_source=cat_source,
                source=TransactionSource.MANUAL,
            )
            db.add(txn)
        db.commit()

        all_txns = db.query(Transaction).all()
        cat_sources = {t.category_source for t in all_txns}
        assert len(cat_sources) == len(CategorySource)

    def test_transaction_created_at_set_automatically(self, test_transaction: Transaction):
        """Verify created_at is set automatically."""
        assert test_transaction.created_at is not None
        assert isinstance(test_transaction.created_at, datetime)
