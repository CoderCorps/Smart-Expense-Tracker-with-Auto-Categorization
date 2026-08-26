from datetime import date as date_type

from pydantic import BaseModel

from backend.app.models.transaction import CategorySource, TransactionSource, TransactionType


class TransactionOut(BaseModel):
    id: int
    date: date_type
    description: str
    amount: float
    type: TransactionType
    category_id: int | None = None
    category_name: str | None = None
    category_source: CategorySource
    source: TransactionSource

    model_config = {"from_attributes": True}


class TransactionCreate(BaseModel):
    """Used for manual entry (typed in by the user, not from a file)."""

    date: date_type
    description: str
    amount: float
    type: TransactionType
    category_id: int | None = None


class TransactionCategoryUpdate(BaseModel):
    """
    Used when the user corrects a wrongly-categorized transaction.
    Every call to this endpoint is a labeled example for Person C's ML model —
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
