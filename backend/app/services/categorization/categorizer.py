from app.services.categorization.ml_classifier import MLCategorizer
from app.services.categorization.rule_based import categorize as rule_categorize


ml_categorizer = MLCategorizer()


def categorize_transaction(description: str) -> tuple[str, str]:
    """
    Categorize a transaction using ML first.

    If the ML model is not confident enough,
    fall back to the rule-based categorizer.

    Returns:
        (category_name, category_source)
    """

    prediction = ml_categorizer.predict(description)

    if prediction is not None:
        return prediction.category_name, "ml"

    return rule_categorize(description), "rule_based"