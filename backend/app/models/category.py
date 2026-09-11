from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.database import Base

# Seeded into the DB on startup (see app/main.py). rule_based.py maps its
# keywords to these exact names, and the import path looks up category ids
# by them — so add a category here rather than inserting one directly, or
# the categorizer and the database will disagree about what exists.
DEFAULT_CATEGORIES: dict[str, str] = {
    "Food & Dining": "Restaurants, groceries, cafes and food delivery",
    "Travel & Transport": "Cabs, fuel, flights, trains and public transport",
    "Shopping": "Retail, e-commerce, clothing and electronics",
    "Rent & Housing": "Rent, maintenance and home services",
    "Utilities": "Electricity, water, internet, mobile and gas bills",
    "Entertainment": "Streaming, movies, games and events",
    "Health & Fitness": "Pharmacy, doctors, gyms and insurance",
    "Salary & Income": "Salary, refunds, interest and other income",
    "Others": "Anything that doesn't fit the categories above",
}


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    # Shown as helper text in the frontend's category pickers. Nullable so a
    # user-created category doesn't have to supply one.
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
