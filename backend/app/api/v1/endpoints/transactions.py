"""
Core transaction CRUD. Fully implemented as shared foundation — everyone's
work reads from or writes to this table, so it's built once, carefully,
rather than split across people. If you need transaction data for your
feature, query the Transaction model directly (see analytics/aggregations.py
for an example) rather than calling these HTTP endpoints internally.
"""

from datetime import date as date_type

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session, joinedload

from backend.app.api.deps import get_current_user, get_db
from backend.app.models.category import Category
from backend.app.models.transaction import (
    CategorySource,
    Transaction,
    TransactionSource,
    TransactionType,
)
from backend.app.models.user import User
from backend.app.schemas.transaction import TransactionCategoryUpdate, TransactionCreate, TransactionOut

router = APIRouter(prefix="/transactions", tags=["transactions"])


def _to_transaction_out(txn: Transaction) -> TransactionOut:
    return TransactionOut(
        id=txn.id,
        date=txn.date,
        description=txn.description,
        raw_description=txn.raw_description,
        amount=txn.amount,
        type=txn.type,
        category_id=txn.category_id,
        category_name=txn.category.name if txn.category else None,
        category_source=txn.category_source,
        source=txn.source,
    )


@router.get("", response_model=list[TransactionOut])
def list_transactions(
    response: Response,
    start_date: date_type | None = None,
    end_date: date_type | None = None,
    category_id: int | None = None,
    type: TransactionType | None = None,
    search: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Filtered, paginated list for the current user.

    The total number of matching rows (ignoring pagination) is returned in
    the `X-Total-Count` header so the frontend can render real page counts
    without changing this endpoint's array response shape.
    """
    query = (
        db.query(Transaction)
        .options(joinedload(Transaction.category))
        .filter(Transaction.user_id == current_user.id)
    )

    if start_date:
        query = query.filter(Transaction.date >= start_date)
    if end_date:
        query = query.filter(Transaction.date <= end_date)
    if category_id:
        query = query.filter(Transaction.category_id == category_id)
    if type:
        query = query.filter(Transaction.type == type)
    if search:
        query = query.filter(Transaction.description.ilike(f"%{search}%"))

    response.headers["X-Total-Count"] = str(query.count())

    # id is the tiebreaker: without it, rows sharing a date can shuffle
    # between pages and the same transaction shows up twice (or never).
    query = query.order_by(Transaction.date.desc(), Transaction.id.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    return [_to_transaction_out(t) for t in query.all()]


@router.post("", response_model=TransactionOut, status_code=201)
def create_transaction(
    payload: TransactionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Manual entry. `description` arrives already cleaned and `amount` already
    positive — TransactionCreate's validators enforce that, so the same
    invariants hold here as on the CSV/PDF import path in upload.py.

    There's no external source text for a typed-in transaction, so
    raw_description mirrors the description the user entered.
    """
    if payload.category_id is not None and not db.get(Category, payload.category_id):
        raise HTTPException(status_code=404, detail="Category not found")

    transaction = Transaction(
        user_id=current_user.id,
        date=payload.date,
        description=payload.description,
        raw_description=payload.description,
        amount=payload.amount,
        type=payload.type,
        category_id=payload.category_id,
        category_source=(
            CategorySource.MANUAL_CORRECTION if payload.category_id else CategorySource.UNCATEGORIZED
        ),
        source=TransactionSource.MANUAL,
    )
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    return _to_transaction_out(transaction)


@router.get("/{transaction_id}", response_model=TransactionOut)
def get_transaction(
    transaction_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    txn = _get_owned_transaction(db, transaction_id, current_user)
    return _to_transaction_out(txn)


@router.put("/{transaction_id}/category", response_model=TransactionOut)
def update_transaction_category(
    transaction_id: int,
    payload: TransactionCategoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    The user correcting a wrong auto-category. This is intentionally its own
    endpoint (not part of a general PATCH) because every call here is also a
    labeled training example for the ML classifier — see
    CategorySource.MANUAL_CORRECTION in app/models/transaction.py.
    """
    txn = _get_owned_transaction(db, transaction_id, current_user)

    category = db.get(Category, payload.category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    txn.category_id = payload.category_id
    txn.category_source = CategorySource.MANUAL_CORRECTION
    db.commit()
    db.refresh(txn)
    return _to_transaction_out(txn)


@router.delete("/{transaction_id}", status_code=204)
def delete_transaction(
    transaction_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    txn = _get_owned_transaction(db, transaction_id, current_user)
    db.delete(txn)
    db.commit()


def _get_owned_transaction(db: Session, transaction_id: int, current_user: User) -> Transaction:
    txn = db.get(Transaction, transaction_id)
    if not txn or txn.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return txn
