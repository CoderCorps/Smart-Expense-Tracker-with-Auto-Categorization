"""
Person B - Rule Based Transaction Categorization

Baseline categorization system for transaction descriptions.

The goal is to handle both clean descriptions and messy bank
narrations such as:

    SWIGGY*ORDER 99213
    UPI-SWIGGY-12345
    AMZN Mktp IN
    NEFT-HDFC0001-SALARY
    UBER INDIA
    NETFLIX.COM

This remains the fallback categorizer even after the ML model
is introduced.
"""

import re


# More specific categories/keywords should appear before generic ones.
CATEGORY_KEYWORDS = {
    "Food & Dining": [
        "swiggy",
        "zomato",
        "restaurant",
        "cafe",
        "food",
        "dominos",
        "pizza",
        "mcdonald",
        "kfc",
    ],

    "Travel & Transport": [
        "uber",
        "ola",
        "irctc",
        "flight",
        "fuel",
        "petrol",
        "diesel",
        "metro",
        "rapido",
        "cab",
        "bus",
    ],

    "Shopping": [
        "amazon",
        "amzn",
        "flipkart",
        "myntra",
        "mall",
        "ajio",
        "meesho",
    ],

    "Rent & Housing": [
        "rent",
        "landlord",
        "housing",
    ],

    "Utilities": [
        "electricity",
        "water bill",
        "broadband",
        "recharge",
        "gas bill",
        "mobile bill",
        "internet",
    ],

    "Entertainment": [
        "netflix",
        "spotify",
        "prime video",
        "hotstar",
        "movie",
        "cinema",
        "bookmyshow",
    ],

    "Health & Fitness": [
        "pharmacy",
        "hospital",
        "gym",
        "doctor",
        "medical",
        "apollo",
    ],

    "Salary & Income": [
        "salary",
        "payroll",
        "stipend",
        "income",
        "salary credit",
    ],
}


DEFAULT_CATEGORY = "Others"


def _normalize_description(description: str) -> str:
    """
    Normalize bank narration so keyword matching works with
    different punctuation, spacing and casing.
    """

    if not description:
        return ""

    text = str(description).lower().strip()

    # Replace punctuation/separators with spaces.
    text = re.sub(r"[^a-z0-9]+", " ", text)

    # Collapse repeated whitespace.
    text = re.sub(r"\s+", " ", text).strip()

    return text


def categorize(description: str) -> str:
    text = description.lower()

    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            return category

    return DEFAULT_CATEGORY