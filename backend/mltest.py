from app.services.categorization.ml_classifier import MLCategorizer


descriptions = [
    "swiggy order",
    "zomato food",
    "restaurant payment",
    "uber ride",
    "ola cab",
    "irctc ticket",
    "amazon purchase",
    "flipkart order",
    "myntra shopping",
    "netflix subscription",
    "spotify premium",
    "movie ticket",
]

categories = [
    "Food & Dining",
    "Food & Dining",
    "Food & Dining",
    "Travel & Transport",
    "Travel & Transport",
    "Travel & Transport",
    "Shopping",
    "Shopping",
    "Shopping",
    "Entertainment",
    "Entertainment",
    "Entertainment",
]


ml = MLCategorizer()

# Train
ml.train(descriptions, categories)

print("Model trained successfully!")

# Predict
test_descriptions = [
    "swiggy dinner order",
    "uber ride to airport",
    "amazon online purchase",
    "spotify monthly subscription",
]

for description in test_descriptions:
    prediction = ml.predict(description)

    if prediction:
        print(
            f"{description:<35} → "
            f"{prediction.category_name} "
            f"(confidence: {prediction.confidence:.2f})"
        )
    else:
        print(f"{description:<35} → No confident prediction")