"""
Categorization over HTTP.

Kept thin — the actual logic lives in services/categorization/, so it can
be unit-tested (and reused by upload.py) without spinning up the API.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.api.deps import get_current_user, get_db
from backend.app.models.category import Category
from backend.app.models.transaction import CategorySource, Transaction
from backend.app.models.user import User
from backend.app.schemas.category import CategoryOut, TrainingResult
from backend.app.services.categorization.ml_classifier import (
    MIN_TRAINING_EXAMPLES,
    MLCategorizer,
    NotEnoughTrainingData,
)
from backend.app.services.categorization.rule_based import categorize

router = APIRouter(prefix="/categorization", tags=["categorization"])


@router.get("/categories", response_model=list[CategoryOut])
def list_categories(db: Session = Depends(get_db)):
    return db.query(Category).order_by(Category.name).all()


@router.post("/recategorize/{transaction_id}")
def recategorize_transaction(
    transaction_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Re-run categorization on a single transaction.

    Useful for testing changes to the keyword rules, and for applying a
    newly trained model without re-uploading the statement.
    """

    txn = db.get(Transaction, transaction_id)
    if not txn or txn.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Transaction not found")

    prediction = MLCategorizer(current_user.id).predict(txn.description)

    if prediction:
        category_name = prediction.category_name
        category_source = CategorySource.ML
    else:
        category_name = categorize(txn.description)
        category_source = CategorySource.RULE_BASED

    category = db.query(Category).filter(Category.name == category_name).first()

    txn.category_id = category.id if category else None
    txn.category_source = category_source
    db.commit()

    return {
        "transaction_id": txn.id,
        "category_name": category_name,
        "category_source": category_source.value,
    }


@router.post("/train", response_model=TrainingResult)
def train_ml_model(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Train this user's categorizer on the corrections they've made.

    Only rows the user explicitly re-categorized count as training data —
    training on the categorizer's own output would just teach the model to
    repeat the keyword rules, including their mistakes.
    """

    transactions = (
        db.query(Transaction)
        .join(Category, Transaction.category_id == Category.id)
        .filter(
            Transaction.user_id == current_user.id,
            Transaction.category_source == CategorySource.MANUAL_CORRECTION,
        )
        .all()
    )

    descriptions = [txn.description for txn in transactions]
    category_names = [txn.category.name for txn in transactions]

    try:
        trained_on = MLCategorizer(current_user.id).train(descriptions, category_names)
    except NotEnoughTrainingData as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return TrainingResult(
        message="Model trained. New imports will use it when it's confident.",
        training_examples=trained_on,
        categories_covered=len(set(category_names)),
    )


@router.get("/training-status", response_model=TrainingResult)
def training_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    How close this user is to being able to train — what the frontend
    needs to decide whether to offer the button.
    """

    corrections = (
        db.query(Transaction)
        .join(Category, Transaction.category_id == Category.id)
        .filter(
            Transaction.user_id == current_user.id,
            Transaction.category_source == CategorySource.MANUAL_CORRECTION,
        )
        .all()
    )

    categories_covered = len({txn.category.name for txn in corrections})
    is_trained = MLCategorizer(current_user.id).is_trained

    if is_trained:
        message = "A trained model is in use for your transactions."
    elif len(corrections) < MIN_TRAINING_EXAMPLES:
        remaining = MIN_TRAINING_EXAMPLES - len(corrections)
        message = (
            f"Correct {remaining} more categor"
            f"{'y' if remaining == 1 else 'ies'} to unlock training."
        )
    else:
        message = "Ready to train."

    return TrainingResult(
        message=message,
        training_examples=len(corrections),
        categories_covered=categories_covered,
        is_trained=is_trained,
        minimum_examples=MIN_TRAINING_EXAMPLES,
    )
