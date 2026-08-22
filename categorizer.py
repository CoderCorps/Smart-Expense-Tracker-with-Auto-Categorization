"""
categorizer.py

Rule‑based transaction categorisation for the Smart Expense Tracker.

This module provides a single function `categorize_transaction(description)`
that assigns a category (Food, Travel, Shopping, Rent, Utilities, Other)
based on hard‑coded keywords.

No external libraries beyond the Python standard library are used.
"""

import re
from collections import defaultdict

# ----------------------------------------------------------------------
# CATEGORY RULES
# Add or modify keywords as needed. Multi‑word phrases are supported.
# Keywords are case‑insensitive during matching.
# ----------------------------------------------------------------------
CATEGORY_RULES = {
    "Food": [
        "swiggy", "zomato", "restaurant", "food", "dominos", "pizza",
        "mcdonald", "kfc", "starbucks", "coffee", "uber eats",  # multi‑word
    ],
    "Travel": [
        "uber", "ola", "metro", "cab", "irctc", "flight", "railway",
        "bus", "train", "airline",
    ],
    "Shopping": [
        "amazon", "flipkart", "myntra", "ajio", "shopping",
        "nykaa", "meesho", "ebay",
    ],
    "Rent": [
        "rent", "landlord", "lease", "apartment",
    ],
    "Utilities": [
        "electricity", "water", "gas", "internet", "airtel", "jio", "vi",
        "netflix", "spotify", "broadband", "phone", "mobile", "bill",
    ],
}

# Pre‑sort keywords by length (longest first) to help with multi‑word phrases,
# though the scoring system already gives each keyword equal weight.
# Sorting is not strictly necessary for correctness, but it can be useful
# if we later adopt a first‑match strategy. We keep it for clarity.
for cat in CATEGORY_RULES:
    CATEGORY_RULES[cat] = sorted(CATEGORY_RULES[cat], key=len, reverse=True)


def categorize_transaction(description):
    """
    Assign a category to a transaction based on its description.

    Args:
        description (str or None): The transaction description.

    Returns:
        str: One of 'Food', 'Travel', 'Shopping', 'Rent', 'Utilities', or 'Other'.
    """
    # Safely convert to string and lower‑case
    if description is None:
        desc = ""
    else:
        desc = str(description).lower()

    # If description is empty after trimming, return "Other" early
    if not desc.strip():
        return "Other"

    # Count how many keywords from each category appear in the description
    scores = defaultdict(int)

    for category, keywords in CATEGORY_RULES.items():
        for kw in keywords:
            # Match the keyword only as a whole word.
            # \b matches at word boundaries (letters, digits, underscore vs. non‑word).
            # For multi‑word keywords like "uber eats", the space is a non‑word char,
            # so \b...\b works correctly around the whole phrase.
            pattern = rf'(?<![a-z]){re.escape(kw)}(?![a-z])'
            # re.search scans the entire string; we don't need to count multiple
            # occurrences of the same keyword – we just add 1 if it appears at least once.
            if re.search(pattern, desc):
                scores[category] += 1

    # If no category got any match, return "Other"
    if not scores:
        return "Other"

    # Find the category with the highest score.
    # In case of a tie, we return the one that appears first in CATEGORY_RULES
    # (Python preserves insertion order from 3.7+).
    # We can also break ties by additional criteria if needed.
    max_score = max(scores.values())
    # Collect all categories that have the max score
    winners = [cat for cat, sc in scores.items() if sc == max_score]
    # Return the first such category (according to the order in CATEGORY_RULES)
    # We'll iterate over CATEGORY_RULES to preserve order.
    for category in CATEGORY_RULES:
        if category in winners:
            return category

    # Fallback (should never happen)
    return "Other"


# ----------------------------------------------------------------------
# TEST SECTION
# Run `python categorizer.py` to see demo output.
# ----------------------------------------------------------------------
if __name__ == "__main__":
    test_descriptions = [
        "Swiggy food order",                 # Food
        "Uber ride to college",              # Travel (single "uber")
        "Uber Eats - dinner",                # Food (multi‑word "uber eats")
        "Amazon purchase",                   # Shopping
        "Electricity bill payment",          # Utilities
        "Paid monthly rent",                 # Rent
        "Netflix monthly subscription",      # Utilities
        "Ola cab to airport",                # Travel (both "ola" and "cab")
        "Dinner at a restaurant",            # Food
        "Monthly broadband bill",            # Utilities
        "Random XYZ transaction",            # Other
        "Cable TV service",                  # Other (does not contain "cab" as whole word)
        "",                                  # Other
        None,                                # Other
        "12345",                             # Other
        "Swiggy pizza and Uber ride",        # Multiple keywords: Food (2) vs Travel (1) → Food
        "Myntra shopping clothes",           # Shopping
    ]

    print("Transaction Description".ljust(40), "→ Category")
    print("-" * 60)
    for desc in test_descriptions:
        cat = categorize_transaction(desc)
        print(f"{str(desc).ljust(40)} → {cat}")