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
from backend.app.services.categorization.ml_classifier import MLCategorizer

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

    ml_model = MLCategorizer()
    prediction = ml_model.predict(txn.description)

    if prediction:
        category_name = prediction.category_name
        category_source = CategorySource.ML
    else:
        category_name = categorize(txn.description)
        category_source = CategorySource.RULE_BASED

    category = db.query(Category).filter(
        Category.name == category_name
    ).first()

    txn.category_id = category.id if category else None
    txn.category_source = category_source
    db.commit()

    return {"transaction_id": txn.id, "category_name": category_name}


@router.post("/train")
def train_ml_model(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Train the ML categorizer using this user's manual corrections.
    """

    transactions = (
        db.query(Transaction)
        .filter(
            Transaction.user_id == current_user.id,
            Transaction.category_source == CategorySource.MANUAL_CORRECTION,
            Transaction.category_id.isnot(None),
        )
        .all()
    )

    if len(transactions) < 2:
        raise HTTPException(
            status_code=400,
            detail="Not enough manual corrections to train the model",
        )

    descriptions = [txn.description for txn in transactions]
    category_names = [
        txn.category.name
        for txn in transactions
        if txn.category
    ]

    if len(descriptions) != len(category_names):
        raise HTTPException(
            status_code=400,
            detail="Some training transactions have missing categories",
        )

    model = MLCategorizer()
    model.train(descriptions, category_names)

    return {
        "message": "ML model trained successfully",
        "training_examples": len(descriptions),
    }
