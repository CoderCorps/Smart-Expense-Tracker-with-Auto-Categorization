"""
Pytest configuration and shared fixtures for the Smart Expense Tracker backend.

This file provides:
- In-memory SQLite database for testing
- Test database session
- FastAPI TestClient
- Helper fixtures for creating test data
"""

import os
import sys
from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# Put the repo root on sys.path so `backend.app...` resolves the same way it
# does for uvicorn (poe tasks pass --app-dir .. for the same reason).
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.app.db.database import Base, get_db
from backend.app.main import app
from backend.app.models.category import Category, DEFAULT_CATEGORIES
from backend.app.models.transaction import Transaction, TransactionSource, TransactionType
from backend.app.models.user import User


# Use in-memory SQLite for testing (very fast, no disk I/O)
TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="session")
def engine():
    """Create a test database engine."""
    engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="session")
def TestingSessionLocal(engine):
    """Create a session factory for the test database."""
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture
def db(TestingSessionLocal):
    """Provide a fresh database session for each test."""
    connection = TestingSessionLocal.kw["bind"].connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db: Session):
    """Provide a FastAPI TestClient with a test database."""

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def test_user(db: Session) -> User:
    """Create a test user."""
    from backend.app.core.security import hash_password

    user = User(
        email="test@example.com",
        full_name="Test User",
        hashed_password=hash_password("testpass123"),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def test_user_2(db: Session) -> User:
    """Create a second test user (for testing user isolation)."""
    from backend.app.core.security import hash_password

    user = User(
        email="user2@example.com",
        full_name="User Two",
        hashed_password=hash_password("password456"),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def auth_headers(client: TestClient, test_user: User) -> dict:
    """Get authorization headers with a valid JWT token."""
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "test@example.com", "password": "testpass123"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers_user_2(client: TestClient, test_user_2: User) -> dict:
    """Get authorization headers for the second test user."""
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "user2@example.com", "password": "password456"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def seed_categories(db: Session):
    """Seed the database with default categories."""
    for name in DEFAULT_CATEGORIES:
        category = Category(name=name, is_default=True)
        db.add(category)
    db.commit()
    return db.query(Category).all()


@pytest.fixture
def test_transaction(db: Session, test_user: User, seed_categories) -> Transaction:
    """Create a test transaction."""
    txn = Transaction(
        user_id=test_user.id,
        date=date.today(),
        description="Test Transaction",
        raw_description="Test Transaction",
        amount=100.0,
        type=TransactionType.SPEND,
        category_id=None,
        source=TransactionSource.MANUAL,
    )
    db.add(txn)
    db.commit()
    db.refresh(txn)
    return txn


@pytest.fixture
def test_transaction_categorized(
    db: Session, test_user: User, seed_categories
) -> Transaction:
    """Create a test transaction with a category."""
    category = db.query(Category).first()
    txn = Transaction(
        user_id=test_user.id,
        date=date.today(),
        description="Food & Dining",
        raw_description="Starbucks Coffee",
        amount=5.50,
        type=TransactionType.SPEND,
        category_id=category.id,
        source=TransactionSource.MANUAL,
    )
    db.add(txn)
    db.commit()
    db.refresh(txn)
    return txn
