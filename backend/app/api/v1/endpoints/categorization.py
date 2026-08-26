"""
PERSON B OWNS THIS FILE. Keep it thin — actual categorization logic lives in
services/categorization/, this file just exposes it over HTTP. That split
matters: it means the logic can be unit-tested (and reused by upload.py)
without spinning up the API.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.api.deps import get_current_user, get_db
from backend.app.models.category import Category
from backend.app.models.transaction import CategorySource, Transaction
from backend.app.models.user import User
from backend.app.services.categorization.rule_based import categorize

router = APIRouter(prefix="/categorization", tags=["categorization"])


@router.get("/categories")
def list_categories(db: Session = Depends(get_db)):
    categories = db.query(Category).order_by(Category.name).all()
    return [{"id": c.id, "name": c.name} for c in categories]


@router.post("/recategorize/{transaction_id}")
def recategorize_transaction(
    transaction_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Re-runs categorization on a single transaction. Useful for testing
    changes to the keyword rules, and later, for re-running the ML model
    after retraining without re-uploading the whole file.

    TODO (Person B, once ml_classifier.py works): try MLCategorizer.predict()
    first here, fall back to categorize() (rule-based) if the ML model
    isn't confident or hasn't been trained yet.
    """
    txn = db.get(Transaction, transaction_id)
    if not txn or txn.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Transaction not found")

    category_name = categorize(txn.description)
    category = db.query(Category).filter(Category.name == category_name).first()

    txn.category_id = category.id if category else None
    txn.category_source = CategorySource.RULE_BASED
    db.commit()

    return {"transaction_id": txn.id, "category_name": category_name}


@router.post("/train")
def train_ml_model(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    TODO (Person B, Week 3-4 stretch goal): pull all transactions with
    category_source == MANUAL_CORRECTION for this user (or across all users,
    if you want more training data), call MLCategorizer.train() on them,
    and return how many examples it trained on. See
    services/categorization/ml_classifier.py for the full plan.
    """
    raise HTTPException(status_code=501, detail="ML training not implemented yet")
