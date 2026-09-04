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
    "Food & Dining": ["swiggy", "zomato", "restaurant", "cafe", "food"],
    "Travel & Transport": ["uber", "ola", "irctc", "flight", "fuel", "petrol"],
    "Shopping": ["amazon", "flipkart", "myntra", "mall"],
    "Rent & Housing": ["rent", "landlord"],
    "Utilities": ["electricity", "water bill", "broadband", "recharge", "gas bill"],
    "Entertainment": ["netflix", "spotify", "prime video", "hotstar", "movie"],
    "Health & Fitness": ["pharmacy", "hospital", "gym", "doctor"],
    "Salary & Income": ["salary", "payroll", "stipend"],
}

DEFAULT_CATEGORY = "Others"


def categorize(description: str) -> str:
    """Returns a category name (always succeeds — falls back to 'Others')."""
    text = description.lower()

    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            return category

    return DEFAULT_CATEGORY
