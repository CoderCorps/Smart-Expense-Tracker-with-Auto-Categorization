"""
Shared normalization for values pulled out of a statement.

Both import paths need these: pdf_parser.py reads them out of a PDF's
cells, and upload.py reads them out of a CSV's. They used to be
implemented separately, which is how the two paths ended up disagreeing
about what "02/08/2026" means. One implementation, one answer.
"""

import re
from datetime import date, datetime

# Bank date formats, day-first before month-first. Indian and European
# statements write 02/08/2026 as 2 August; US statements are the ones
# that write it as February 8, and they overwhelmingly use the
# unambiguous "Aug 2, 2026" or an ISO date instead. Guessing day-first
# is therefore right far more often than pandas' month-first default.
DATE_FORMATS = [
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%d-%m-%Y",
    "%d/%m/%Y",
    "%d-%m-%y",
    "%d/%m/%y",
    "%d-%b-%Y",
    "%d/%b/%Y",
    "%d %b %Y",
    "%d-%B-%Y",
    "%d %B %Y",
    "%b %d %Y",
    "%b %d, %Y",
    "%B %d, %Y",
    "%m/%d/%Y",
]

_CURRENCY_PATTERN = re.compile(r"\b(?:INR|Rs\.?|USD|EUR|GBP)\b", re.IGNORECASE)
_DASHES = {"-", "—", "–", "−"}


def clean_text(value) -> str:
    """Collapse whitespace and coerce to a stripped string."""

    if value is None:
        return ""

    return re.sub(r"\s+", " ", str(value).replace("\n", " ")).strip()


def parse_money(value) -> float | None:
    """
    Convert a statement's money cell into a float.

    Handles currency symbols and codes, thousands separators, an
    explicit minus, and accounting-style parentheses for negatives.
    Returns None for blanks and for the lone dash banks print in an
    empty debit/credit column.

        "$1,500.00" -> 1500.0
        "(500.00)"  -> -500.0
        "Rs. 500"   -> 500.0
        "-"         -> None
    """

    text = clean_text(value)

    if not text or text in _DASHES:
        return None

    negative = False

    if text.startswith("(") and text.endswith(")"):
        negative = True

    if any(dash in text for dash in ("-", "−")):
        negative = True

    text = _CURRENCY_PATTERN.sub("", text)
    text = text.replace(",", "").replace("$", "").replace("₹", "")

    # Keep digits and a decimal point; everything else was formatting.
    text = re.sub(r"[^0-9.]", "", text)

    if not text or text == ".":
        return None

    try:
        amount = float(text)
    except ValueError:
        return None

    return -abs(amount) if negative else amount


def parse_date(value) -> date | None:
    """
    Convert a statement's date cell into a date.

    Tries the known formats in DATE_FORMATS order. Returns None rather
    than guessing when none of them fit, so the caller can skip the row
    and report it instead of inventing a date.
    """

    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    text = clean_text(value)

    if not text:
        return None

    # Drop a trailing time component ("2026-08-02 00:00:00"), which is
    # what pandas hands back when it has already parsed the column.
    text = text.split()[0] if re.match(r"^\d{4}-\d{2}-\d{2}[ T]", text) else text

    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue

    return None
