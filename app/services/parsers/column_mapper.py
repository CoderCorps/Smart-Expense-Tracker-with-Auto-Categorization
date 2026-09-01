"""
PERSON A OWNS THIS FILE.

Guesses which raw column in an uploaded file corresponds to each of our
standard fields (date, description, amount, type). This is what lets a
user upload literally any bank's CSV export without us hardcoding column
names — different banks call things differently ("Txn Date" vs "Date"
vs "Value Date", "Narration" vs "Description" vs "Particulars", etc).

A basic version is implemented below using simple alias matching. It will
work fine for the sample data and most common bank exports. Ways to make
it meaningfully better (pick one or more as time allows):
  - Add more aliases as you test against real bank statement exports
  - Use difflib.get_close_matches() for fuzzy matching instead of exact
    alias lookup, to catch near-misses like "Trans_Date"
  - Detect the `type` field even when it's not a separate column — some
    banks put spend as negative numbers and earn as positive in a single
    "amount" column instead of a separate type column. Worth handling.
"""

from typing import Optional

# Add to these lists as you encounter real-world column names during testing.
FIELD_ALIASES: dict[str, list[str]] = {
    "date": ["date", "txn date", "transaction date", "value date", "posting date"],
    "description": [
        "description",
        "narration",
        "particulars",
        "details",
        "transaction details",
        "remarks",
    ],
    "amount": ["amount", "transaction amount", "value", "amt"],
    "type": ["type", "transaction type", "dr/cr", "debit/credit"],
}


def suggest_mapping(raw_headers: list[str]) -> dict[str, Optional[str]]:
    """
    Returns e.g. {"date": "Txn Date", "description": "Narration",
    "amount": "Amount", "type": None} — None means we couldn't guess and
    the frontend should ask the user to pick manually.
    """
    mapping: dict[str, Optional[str]] = {}
    normalized_headers = {h.strip().lower(): h for h in raw_headers}

    for field, aliases in FIELD_ALIASES.items():
        matched = None
        for alias in aliases:
            if alias in normalized_headers:
                matched = normalized_headers[alias]
                break
        mapping[field] = matched

    return mapping
