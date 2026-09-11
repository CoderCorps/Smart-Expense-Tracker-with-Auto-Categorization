"""
Keyword-based categorization.

This is the floor: every transaction gets a category the moment it's
saved, so nothing is ever left uncategorized. The ML classifier in
ml_classifier.py takes precedence wherever it's confident, and falls back
here whenever it isn't — see categorize_transaction() in upload.py.

Matching is substring-based and case-insensitive, which is what makes it
survive real statement text ("SWIGGY*ORDER 99213", "NEFT-HDFC0001-SALARY",
"AMZN Mktp IN") rather than only clean sample data. Adding keywords is the
cheapest way to improve categorization; see tests/test_categorization.py.
"""

# category_name -> keywords that, if found (case-insensitive) in the
# description, mean this category. First match wins, so put more specific
# keywords before generic ones if you add to this.

CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "Food & Dining": [
        "swiggy",
        "zomato",
        "restaurant",
        "cafe",
        "bakery",
        "food",
        "pizza",
        "dominos",
        "mcdonalds",
        "mcd",
        "kfc",
        "starbucks",
        "subway",
        "dining",
        "hotel",
        "canteen",
        "grocery",
        "groceries",
    ],

    "Travel & Transport": [
        "uber",
        "ola",
        "rapido",
        "irctc",
        "metro",
        "bus",
        "flight",
        "airline",
        "airport",
        "fuel",
        "petrol",
        "diesel",
        "toll",
        "parking",
        "transport",
        "cab",
        "taxi",
        "train",
        "railway",
        "travel",
    ],

    "Shopping": [
        "amazon",
        "amzn",
        "flipkart",
        "myntra",
        "meesho",
        "ajio",
        "snapdeal",
        "nykaa",
        "mall",
        "retail",
        "store",
        "shopping",
        "marketplace",
        "mktplace",
        "purchase",
    ],

    "Rent & Housing": [
        "rent",
        "rental",
        "landlord",
        "house rent",
        "home rent",
        "housing",
        "maintenance",
    ],

    "Utilities": [
        "electricity",
        "electric bill",
        "electric bill payment",
        "water bill",
        "water payment",
        "broadband",
        "internet",
        "wifi",
        "recharge",
        "mobile recharge",
        "phone recharge",
        "gas bill",
        "lpg",
        "utility",
        "utility bill",
        "power bill",
        "power payment",
    ],

    "Entertainment": [
        "netflix",
        "spotify",
        "prime video",
        "amazon prime",
        "hotstar",
        "disney+",
        "youtube premium",
        "movie",
        "cinema",
        "theatre",
        "pvr",
        "inox",
        "bookmyshow",
        "gaming",
        "game",
        "music subscription",
        "subscription",
    ],

    "Health & Fitness": [
        "pharmacy",
        "hospital",
        "gym",
        "doctor",
        "clinic",
        "medical",
        "medicine",
        "apollo pharmacy",
        "medplus",
        "health",
        "diagnostic",
        "laboratory",
        "lab",
        "fitness",
    ],

    "Salary & Income": [
        "salary",
        "payroll",
        "stipend",
        "income",
        "salary credit",
        "salary payment",
        "salary credited",
        "credit salary",
        "wages",
        "bonus",
    ],
}


DEFAULT_CATEGORY = "Others"


def categorize(description: str) -> str:
    """
    Categorize a transaction description using keyword matching.

    Returns a category name.
    If no keyword matches, returns 'Others'.
    """

    # Handle empty or missing descriptions safely.
    if not description:
        return DEFAULT_CATEGORY

    text = description.lower().strip()

    for category, keywords in CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            if keyword in text:
                return category

    return DEFAULT_CATEGORY