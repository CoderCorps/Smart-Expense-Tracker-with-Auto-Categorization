import enum
from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, Enum, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class TransactionType(str, enum.Enum):
    SPEND = "spend"
    EARN = "earn"


class TransactionSource(str, enum.Enum):
    MANUAL = "manual"
    CSV = "csv"
    PDF = "pdf"


class CategorySource(str, enum.Enum):
    """
    How this transaction got its category. This matters a lot for Person B's
    ML work in Week 3-4: every row where category_source == 'manual_correction'
    is a labeled training example — the user told us the auto-categorizer
    was wrong and what the right answer was. That's the training set.
    """

    RULE_BASED = "rule_based"
    ML = "ml"
    MANUAL_CORRECTION = "manual_correction"
    UNCATEGORIZED = "uncategorized"


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)

    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    description: Mapped[str] = mapped_column(String, nullable=False)
    # The original, un-cleaned text from the CSV/PDF row, kept for debugging
    # parsing/categorization issues and for training the ML classifier later.
    raw_description: Mapped[str | None] = mapped_column(String, nullable=True)

    amount: Mapped[float] = mapped_column(Float, nullable=False)
    type: Mapped[TransactionType] = mapped_column(Enum(TransactionType), nullable=False)

    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"), nullable=True)
    category_source: Mapped[CategorySource] = mapped_column(
        Enum(CategorySource), default=CategorySource.UNCATEGORIZED
    )

    source: Mapped[TransactionSource] = mapped_column(Enum(TransactionSource), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    owner = relationship("User", back_populates="transactions")
    category = relationship("Category", back_populates="transactions")
