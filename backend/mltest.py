from app.services.categorization.ml_classifier import MLCategorizer
from app.services.categorization.training_data import TRAINING_DATA


ml = MLCategorizer()

# Train using the same training data used by the API
ml.train_from_training_data()

print("Model trained successfully!")

print(
    "Training examples:",
    sum(len(examples) for examples in TRAINING_DATA.values())
)

print(
    "Categories:",
    len(TRAINING_DATA)
)


# Test descriptions
test_descriptions = [
    # General test examples
    "swiggy dinner order",
    "uber ride to airport",
    "amazon online purchase",
    "spotify monthly subscription",

    # PDF transactions
    "Sample Employer Payroll Co.",
    "Demo Grocery Mart",
    "Fictional Electric Co.",
    "ATM Withdrawal - Sample Branch",
    "Placeholder Streaming Svc",
    "Demo Rent Holdings LLC",
    "Test Coffee Shop",
    "Online Transfer to Savings",
    "Refund - Demo Retailer",
    "Fictional Gym Membership",
    "Sample Insurance Co.",
]


print("\nPredictions:")

for description in test_descriptions:

    X = ml.vectorizer.transform([description])

    probabilities = ml.model.predict_proba(X)[0]

    best_index = probabilities.argmax()

    category = ml.model.classes_[best_index]

    confidence = probabilities[best_index]

    print(
        f"{description:<40} → "
        f"{category:<20} "
        f"(confidence: {confidence:.2f})"
    )