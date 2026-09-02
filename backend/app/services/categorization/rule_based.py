"""
PERSON B OWNS THIS FILE (along with ml_classifier.py).

Keyword-based categorization. This is the fallback that always runs first —
every transaction gets a category the moment it's saved, using this. Once
ml_classifier.py is trained (see that file), the categorization pipeline in
upload.py can be switched to try ML first and fall back to this when the ML
model isn't confident.

This works fine as a baseline but the keyword list below is intentionally
small. Expanding it against real transaction descriptions is the actual
Week 2 task here — test it against messy real-world text ("SWIGGY*ORDER
99213", "NEFT-HDFC0001-SALARY", "AMZN Mktp IN") not just clean sample data.
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