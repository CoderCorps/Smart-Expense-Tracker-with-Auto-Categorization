from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base

# Seeded into the DB on startup (see app/main.py). Person A and Person B
# both read from this list — A suggests one of these when mapping a CSV/PDF
# column, B's rule-based classifier maps keywords to these exact names.
# If you need a new category, add it here so everyone stays in sync.
DEFAULT_CATEGORIES = [
    "Food & Dining",
    "Travel & Transport",
    "Shopping",
    "Rent & Housing",
    "Utilities",
    "Entertainment",
    "Health & Fitness",
    "Salary & Income",
    "Others",
]


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    transactions = relationship("Transaction", back_populates="category")
