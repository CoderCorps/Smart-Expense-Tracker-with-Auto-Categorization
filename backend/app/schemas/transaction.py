from datetime import date as date_type

from pydantic import BaseModel, field_validator

from backend.app.models.transaction import CategorySource, TransactionSource, TransactionType


class TransactionOut(BaseModel):
    id: int
    date: date_type
    description: str
    # The original source text, before cleaning. Exposed so the UI can show
    # what the bank actually wrote when a categorization looks wrong.
    raw_description: str | None = None
    amount: float
    type: TransactionType
    category_id: int | None = None
    category_name: str | None = None
    category_source: CategorySource
    source: TransactionSource

    model_config = {"from_attributes": True}


class TransactionCreate(BaseModel):
    """
    Used for manual entry (typed in by the user, not from a file).

    The two validators below enforce the invariants documented in
    docs/data_model.md: `amount` is always stored as a positive magnitude
    (direction lives in `type`), and `description` is stored cleaned. The
    CSV/PDF import path applies the same rules — see upload.py — so a
    transaction means the same thing however it got here.
    """

    date: date_type
    description: str
    amount: float
    type: TransactionType
    category_id: int | None = None

    @field_validator("description")
    @classmethod
    def _clean_description(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if not cleaned:
            raise ValueError("description must not be blank")
        return cleaned

    @field_validator("amount")
    @classmethod
    def _positive_magnitude(cls, value: float) -> float:
        if value == 0:
            raise ValueError("amount must not be zero")
        return abs(value)


class TransactionCategoryUpdate(BaseModel):
    """
    Used when the user corrects a wrongly-categorized transaction.
    Every call to this endpoint is a labeled example for the ML classifier —
    see CategorySource.MANUAL_CORRECTION in app/models/transaction.py.
    """

    category_id: int


class TransactionFilters(BaseModel):
    """Query params for GET /transactions — all optional."""

    start_date: date_type | None = None
    end_date: date_type | None = None
    category_id: int | None = None
    type: TransactionType | None = None
    search: str | None = None
    page: int = 1
    page_size: int = 50
