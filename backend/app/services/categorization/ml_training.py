"""
PERSON B OWNS THIS FILE.

Builds the ML training dataset from transactions that users
have manually corrected.

Training flow:

    Database
        ↓
    MANUAL_CORRECTION transactions
        ↓
    description + category
        ↓
    MLCategorizer.train()
        ↓
    Saved ML model
"""

from sqlalchemy.orm import Session

from app.models.transaction import (
    CategorySource,
    Transaction,
)

from app.models.category import Category

from app.services.categorization.ml_classifier import (
    MLCategorizer,
)


def get_training_data(
    db: Session,
    user_id: int | None = None,
) -> tuple[list[str], list[str]]:
    """
    Get manually corrected transactions from the database.

    Returns:

        descriptions = [
            "UPI RAHUL",
            "AMAZON PAYMENT",
            ...
        ]

        categories = [
            "Food & Dining",
            "Shopping",
            ...
        ]
    """

    query = (
        db.query(Transaction, Category)
        .join(
            Category,
            Transaction.category_id == Category.id,
        )
        .filter(
            Transaction.category_source
            == CategorySource.MANUAL_CORRECTION
        )
    )

    # If user_id is provided, only use that user's
    # corrections for training.
    if user_id is not None:
        query = query.filter(
            Transaction.user_id == user_id
        )

    rows = query.all()

    descriptions = []
    categories = []

    for transaction, category in rows:

        description = transaction.description

        if not description:
            continue

        if not description.strip():
            continue

        if not category:
            continue

        descriptions.append(
            description.strip()
        )

        categories.append(
            category.name
        )

    return descriptions, categories


def train_model(
    db: Session,
    user_id: int | None = None,
) -> dict:
    """
    Train the ML categorizer using manually corrected
    transactions.
    """

    descriptions, categories = get_training_data(
        db=db,
        user_id=user_id,
    )

    training_count = len(descriptions)

    if training_count < 2:
        return {
            "success": False,
            "message": (
                "Not enough manually corrected "
                "transactions to train the model."
            ),
            "training_count": training_count,
        }

    unique_categories = set(categories)

    if len(unique_categories) < 2:
        return {
            "success": False,
            "message": (
                "Training requires manually corrected "
                "transactions from at least 2 categories."
            ),
            "training_count": training_count,
            "category_count": len(unique_categories),
        }

    categorizer = MLCategorizer()

    categorizer.train(
        descriptions=descriptions,
        category_names=categories,
    )

    return {
        "success": True,
        "message": "ML model trained successfully.",
        "training_count": training_count,
        "category_count": len(unique_categories),
        "categories": sorted(unique_categories),
    }