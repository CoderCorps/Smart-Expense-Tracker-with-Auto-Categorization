from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

from app.api.deps import get_db
from app.db.database import Base
from app.main import app
from app.models.category import Category, DEFAULT_CATEGORIES


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = session_factory()
    db.add_all([Category(name=name, is_default=True) for name in DEFAULT_CATEGORIES])
    db.commit()

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()
    db.close()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def test_core_api_flow(client: TestClient):
    signup = client.post(
        "/api/v1/auth/signup",
        json={
            "email": "testuser@example.com",
            "full_name": "Test User",
            "password": "testpass123",
        },
    )
    assert signup.status_code == 201

    login = client.post(
        "/api/v1/auth/login",
        data={"username": "testuser@example.com", "password": "testpass123"},
    )
    assert login.status_code == 200
    access_token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    assert client.get("/").status_code == 200

    categories = client.get(
        "/api/v1/categorization/categories", headers=headers
    )
    assert categories.status_code == 200
    category_id = categories.json()[0]["id"]

    categorized = client.post(
        "/api/v1/transactions",
        json={
            "date": str(date.today()),
            "description": "Grocery shopping",
            "amount": 75.00,
            "type": "spend",
            "category_id": category_id,
        },
        headers=headers,
    )
    assert categorized.status_code == 201

    uncategorized = client.post(
        "/api/v1/transactions",
        json={
            "date": str(date.today()),
            "description": "Coffee at Starbucks",
            "amount": 5.50,
            "type": "spend",
            "category_id": None,
        },
        headers=headers,
    )
    assert uncategorized.status_code == 201
    assert uncategorized.json()["category_id"] is None

    transactions = client.get("/api/v1/transactions", headers=headers)
    assert transactions.status_code == 200
    assert len(transactions.json()) == 2
