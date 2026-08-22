KEYWORD_RULES = {
    "Food": [
        "swiggy",
        "zomato",
        "restaurant",
        "food",
        "mcdonald",
        "dominos",
        "pizza",
        "cafe",
    ],

    "Shopping": [
        "amazon",
        "flipkart",
        "myntra",
        "ajio",
        "shopping",
    ],

    "Transport": [
        "uber",
        "ola",
        "rapido",
        "metro",
        "bus",
        "train",
        "fuel",
        "petrol",
        "diesel",
    ],

    "Entertainment": [
        "netflix",
        "spotify",
        "prime video",
        "youtube",
        "hotstar",
        "movie",
        "cinema",
    ],

    "Utilities": [
        "electricity",
        "water bill",
        "gas bill",
        "mobile bill",
        "internet",
        "recharge",
        "broadband",
    ],

    "Housing": [
        "rent",
        "maintenance",
    ],

    "Income": [
        "salary",
        "income",
        "credited",
        "credit",
    ],
}


def categorize(description):
    """
    Categorize transaction using keyword rules.
    """

    description = str(description).lower().strip()

    for category, keywords in KEYWORD_RULES.items():

        for keyword in keywords:

            if keyword in description:
                return category

    return "Other"


def classify_transaction(description):
    """
    Return both transaction type and category.
    """

    description = str(description).lower().strip()

    # Income keywords
    income_keywords = [
        "salary",
        "income",
        "credited",
        "credit",
        "refund",
        "cashback",
    ]

    for keyword in income_keywords:

        if keyword in description:

            return "Income", "Income"

    # Otherwise treat as expense
    return "Expense", categorize(description)