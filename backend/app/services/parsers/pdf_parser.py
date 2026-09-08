"""
Robust PDF bank-statement parser for Person-B.

Goal:
    Convert different bank statement PDF layouts into:

    {
        "date": "...",
        "description": "...",
        "amount": 123.45,
        "type": "spend" / "earn"
    }

Supported layouts:

    Layout A/B:
        Date + Description + Debit + Credit + Balance

    Layout C:
        Date + Description + Amount + Balance
        where negative amount = spend
        and positive amount = earn

    Layout D:
        Date + Description + Type + Amount + Balance
        where Type can be:
            debit
            credit
            deposit
            withdrawal
            transfer out
            transfer in

The parser first tries pdfplumber table extraction.
If no table can be extracted, it falls back to text extraction.

Also handles:
    - multiple pages
    - repeated headers
    - pages without repeated headers
    - currency symbols
    - commas in amounts
    - negative amounts
    - parentheses for negative amounts
    - debit / credit
    - deposit / withdrawal
    - common date formats
    - simple wrapped descriptions
"""


import io
import re
from datetime import datetime

import pdfplumber


# =========================================================
# HEADER NORMALIZATION
# =========================================================

HEADER_ALIASES = {
    "date": {
        "date",
        "transaction date",
        "txn date",
        "value date",
        "posting date",
        "transaction_date",
        "txn_date",
    },

    "description": {
        "description",
        "transaction description",
        "transaction details",
        "transaction detail",
        "details",
        "narration",
        "narration / details",
        "particulars",
        "remarks",
        "payee",
        "merchant",
        "memo",
        "description / narration",
    },

    "amount": {
        "amount",
        "transaction amount",
        "txn amount",
        "value",
        "amt",
    },

    "type": {
        "type",
        "transaction type",
        "txn type",
        "dr/cr",
        "debit/credit",
        "dr / cr",
    },

    "debit": {
        "debit",
        "withdrawal",
        "withdrawals",
        "debits",
        "payment",
        "payments",
    },

    "credit": {
        "credit",
        "credits",
        "deposit",
        "deposits",
    },

    "balance": {
        "balance",
        "running balance",
        "available balance",
        "closing balance",
    },
}


def _clean_text(value) -> str:
    """Clean extracted PDF text."""

    if value is None:
        return ""

    text = str(value)

    text = text.replace("\n", " ")
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def _normalize_header(value: str) -> str:
    """Convert a raw PDF header into a canonical header name."""

    text = _clean_text(value).lower()

    text = text.replace("(", "")
    text = text.replace(")", "")
    text = text.replace(".", "")

    # Normalize spacing around slashes.
    text = re.sub(r"\s*/\s*", "/", text)

    # Normalize repeated whitespace.
    text = re.sub(r"\s+", " ", text).strip()

    for canonical, aliases in HEADER_ALIASES.items():

        normalized_aliases = set()

        for alias in aliases:
            alias = alias.lower()
            alias = alias.replace(".", "")
            alias = re.sub(r"\s*/\s*", "/", alias)
            alias = re.sub(r"\s+", " ", alias).strip()

            normalized_aliases.add(alias)

        if text in normalized_aliases:
            return canonical

    return text


# =========================================================
# DATE DETECTION
# =========================================================

DATE_PATTERNS = [
    r"^\d{1,2}[-/]\d{1,2}[-/]\d{2,4}$",
    r"^\d{4}[-/]\d{1,2}[-/]\d{1,2}$",
    r"^\d{1,2}[-/][A-Za-z]{3}[-/]\d{2,4}$",
    r"^\d{1,2}\s+[A-Za-z]{3}\s+\d{2,4}$",
    r"^[A-Za-z]{3}\s+\d{1,2},?\s+\d{4}$",
]


def _looks_like_date(value: str) -> bool:
    text = _clean_text(value)

    if not text:
        return False

    return any(
        re.match(pattern, text, re.IGNORECASE)
        for pattern in DATE_PATTERNS
    )


# =========================================================
# AMOUNT PARSING
# =========================================================

def _parse_amount(value: str) -> float | None:
    """
    Convert:

        $1,500.00
        -$86.42
        ₹1,200.50
        Rs. 500
        INR 500
        1,200.00
        (500.00)
        -
        blank

    into float.
    """

    text = _clean_text(value)

    if not text:
        return None

    if text in {"-", "—", "–", "−"}:
        return None

    negative = False

    # Parentheses mean negative.
    if text.startswith("(") and text.endswith(")"):
        negative = True

    # Explicit minus.
    if "-" in text or "−" in text:
        negative = True

    text = text.replace(",", "")
    text = text.replace("$", "")
    text = text.replace("₹", "")

    text = re.sub(
        r"\bINR\b",
        "",
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(
        r"\bRs\.?\b",
        "",
        text,
        flags=re.IGNORECASE,
    )

    # Keep digits and decimal point.
    text = re.sub(r"[^0-9.]", "", text)

    if not text:
        return None

    try:
        amount = float(text)

        if negative:
            amount = -abs(amount)

        return amount

    except ValueError:
        return None


# =========================================================
# TRANSACTION TYPE
# =========================================================

def _normalize_type(value: str) -> str | None:
    """
    Convert bank-specific transaction types into:

        spend
        earn
    """

    text = _clean_text(value).lower()

    if not text:
        return None

    spend_values = {
        "debit",
        "dr",
        "withdrawal",
        "withdraw",
        "payment",
        "purchase",
        "spent",
        "expense",
        "transfer out",
        "transfer-out",
        "transferout",
    }

    earn_values = {
        "credit",
        "cr",
        "deposit",
        "deposited",
        "income",
        "received",
        "salary",
        "transfer in",
        "transfer-in",
        "transferin",
    }

    if text in spend_values:
        return "spend"

    if text in earn_values:
        return "earn"

    if "debit" in text or "withdraw" in text:
        return "spend"

    if "credit" in text or "deposit" in text:
        return "earn"

    if "transfer out" in text:
        return "spend"

    if "transfer in" in text:
        return "earn"

    return None


# =========================================================
# DATE NORMALIZATION
# =========================================================

def _normalize_date(value: str) -> str:
    """Convert common bank date formats into YYYY-MM-DD."""

    text = _clean_text(value)

    formats = [
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%d-%b-%Y",
        "%d/%b/%Y",
        "%d %b %Y",
        "%b %d %Y",
        "%b %d, %Y",
        "%d-%m-%y",
        "%d/%m/%y",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(
                text,
                fmt,
            ).date().isoformat()

        except ValueError:
            continue

    return text


# =========================================================
# TABLE HEADER DETECTION
# =========================================================

def _find_header(table: list[list]) -> tuple[int, list[str]] | None:
    """
    Find the header row in an extracted PDF table.
    """

    for index, row in enumerate(table[:6]):

        normalized = [
            _normalize_header(cell)
            for cell in row
        ]

        useful_headers = {
            "date",
            "description",
            "amount",
            "type",
            "debit",
            "credit",
            "balance",
        }

        matches = set(normalized) & useful_headers

        if "date" in matches and len(matches) >= 2:
            return index, normalized

    return None


# =========================================================
# TABLE ROW NORMALIZATION
# =========================================================

def _normalize_row(
    row: list,
    headers: list[str],
) -> dict | None:

    values = [
        _clean_text(value)
        for value in row
    ]

    # Ignore completely empty rows.
    if not any(values):
        return None

    # Make row and header lengths equal.
    if len(values) < len(headers):
        values.extend([""] * (len(headers) - len(values)))

    if len(values) > len(headers):
        values = values[:len(headers)]

    data = dict(zip(headers, values))

    # -----------------------------------------------------
    # DATE
    # -----------------------------------------------------

    raw_date = data.get("date", "")

    if not _looks_like_date(raw_date):
        return None

    date = _normalize_date(raw_date)

    # -----------------------------------------------------
    # DESCRIPTION
    # -----------------------------------------------------

    description = (
        data.get("description")
        or data.get("details")
        or data.get("particulars")
        or data.get("payee")
        or data.get("merchant")
        or ""
    )

    description = _clean_text(description)

    if not description:
        return None

    # -----------------------------------------------------
    # TYPE
    # -----------------------------------------------------

    txn_type = None

    if data.get("type"):
        txn_type = _normalize_type(data["type"])

    # -----------------------------------------------------
    # DEBIT / CREDIT FORMAT
    #
    # Layout B:
    #
    # Date | Value Date | Description | Ref | Debit | Credit | Balance
    #
    # We intentionally ignore:
    # Value Date
    # Chq./Ref No.
    # Balance
    # -----------------------------------------------------

    debit = _parse_amount(data.get("debit", ""))
    credit = _parse_amount(data.get("credit", ""))

    if debit is not None or credit is not None:

        if credit is not None and debit is None:
            amount = abs(credit)
            txn_type = "earn"

        elif debit is not None and credit is None:
            amount = abs(debit)
            txn_type = "spend"

        else:
            # If both somehow contain values,
            # prefer the non-zero transaction amount.
            if abs(credit or 0) > 0:
                amount = abs(credit)
                txn_type = "earn"
            else:
                amount = abs(debit or 0)
                txn_type = "spend"

    # -----------------------------------------------------
    # SINGLE AMOUNT FORMAT
    #
    # Layout C:
    # Date | Description | Type | Amount | Balance
    #
    # Layout D:
    # Date | Narration | Amount | DR/CR
    # -----------------------------------------------------

    else:

        raw_amount = data.get("amount", "")

        parsed_amount = _parse_amount(raw_amount)

        if parsed_amount is None:
            return None

        amount = abs(parsed_amount)

        # Explicit DR/CR/type has priority.
        if txn_type is None:

            # Negative amount means spending.
            if parsed_amount < 0:
                txn_type = "spend"

            # Positive amount means earning.
            else:
                txn_type = "earn"

    # -----------------------------------------------------
    # FINAL VALIDATION
    # -----------------------------------------------------

    if txn_type not in {"spend", "earn"}:
        return None

    return {
        "date": date,
        "description": description,
        "amount": amount,
        "type": txn_type,
    }


# =========================================================
# TEXT PARSER HELPERS
# =========================================================

TEXT_DATE_REGEX = re.compile(
    r"""
    ^
    (
        \d{1,2}[-/]\d{1,2}[-/]\d{2,4}
        |
        \d{4}[-/]\d{1,2}[-/]\d{1,2}
        |
        \d{1,2}[-/][A-Za-z]{3}[-/]\d{2,4}
        |
        \d{1,2}\s+[A-Za-z]{3}\s+\d{2,4}
        |
        [A-Za-z]{3}\s+\d{1,2},?\s+\d{4}
    )
    \b
    """,
    re.IGNORECASE | re.VERBOSE,
)


AMOUNT_TOKEN_REGEX = re.compile(
    r"""
    (?:
        [\(\-−]?
        (?:
            (?:\$|₹|Rs\.?|INR)\s*
        )?
        \d[\d,]*(?:\.\d+)?
        \)?
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)


def _extract_date_from_line(line: str) -> tuple[str, str] | None:
    """
    Extract a date appearing at the beginning of a line.

    Returns:
        (date_text, remaining_text)
    """

    line = line.strip()

    match = TEXT_DATE_REGEX.match(line)

    if not match:
        return None

    date_text = match.group(1)

    remaining = line[
        match.end():
    ].strip()

    return date_text, remaining


def _extract_amount_tokens(text: str) -> list[str]:
    """Find monetary values in a text line."""

    return [
        match.group(0).strip()
        for match in AMOUNT_TOKEN_REGEX.finditer(text)
    ]


def _remove_amount_tokens(
    text: str,
) -> str:

    return AMOUNT_TOKEN_REGEX.sub(
        " ",
        text,
    ).strip()


def _looks_like_header_line(line: str) -> bool:
    """
    Ignore PDF table header lines when using text extraction.
    """

    normalized = re.sub(
        r"[^a-z/ ]",
        " ",
        line.lower(),
    )

    normalized = re.sub(
        r"\s+",
        " ",
        normalized,
    ).strip()

    header_words = {
        "date",
        "transaction date",
        "txn date",
        "posting date",
        "description",
        "narration",
        "particulars",
        "details",
        "amount",
        "transaction amount",
        "type",
        "debit",
        "credit",
        "balance",
        "running balance",
        "available balance",
    }

    if normalized in header_words:
        return True

    # Lines containing multiple known column headers.
    matches = 0

    for word in header_words:
        if word in normalized:
            matches += 1

    return matches >= 2


def _is_noise_line(line: str) -> bool:
    """Identify common non-transaction PDF lines."""

    text = _clean_text(line).lower()

    if not text:
        return True

    noise_words = [
        "account number",
        "account no",
        "statement period",
        "customer name",
        "opening balance",
        "closing balance",
        "page ",
        "generated on",
        "bank statement",
    ]

    return any(
        word in text
        for word in noise_words
    )


# =========================================================
# TEXT LAYOUT DETECTION
# =========================================================

def _detect_text_layout(lines: list[str]) -> str:
    """
    Guess whether the text PDF is:

        layout_b  = debit / credit
        layout_c  = signed amount
        layout_d  = explicit type
    """

    text = "\n".join(lines).lower()

    has_debit = "debit" in text
    has_credit = "credit" in text

    has_type = (
        "transaction type" in text
        or re.search(
            r"\btype\b",
            text,
        )
        is not None
    )

    if has_type:
        return "type"

    if has_debit and has_credit:
        return "debit_credit"

    return "amount"


# =========================================================
# TEXT LAYOUT B
# =========================================================

def _parse_text_debit_credit_line(
    date_text: str,
    remainder: str,
) -> dict | None:
    """
    Parse:

        Date Description Debit Credit Balance

    Example:

        02/08/2026 Grocery Store -$86.42 $4913.58
    """

    amounts = _extract_amount_tokens(
        remainder
    )

    if len(amounts) < 2:
        return None

    # Usually:
    #
    # debit
    # credit
    # balance
    #
    # We take the final monetary value as
    # balance and the preceding values as
    # transaction amount(s).

    transaction_amounts = amounts[:-1]

    if not transaction_amounts:
        return None

    debit = None
    credit = None

    if len(transaction_amounts) >= 2:

        debit = _parse_amount(
            transaction_amounts[0]
        )

        credit = _parse_amount(
            transaction_amounts[1]
        )

    else:

        value = _parse_amount(
            transaction_amounts[0]
        )

        if value is None:
            return None

        if value < 0:
            debit = abs(value)
        else:
            credit = abs(value)

    description = _remove_amount_tokens(
        remainder
    )

    description = _clean_text(
        description
    )

    if not description:
        return None

    if credit is not None and debit is None:

        amount = abs(credit)
        txn_type = "earn"

    elif debit is not None and credit is None:

        amount = abs(debit)
        txn_type = "spend"

    elif credit is not None and debit is not None:

        if credit > 0:
            amount = abs(credit)
            txn_type = "earn"
        else:
            amount = abs(debit)
            txn_type = "spend"

    else:
        return None

    return {
        "date": _normalize_date(date_text),
        "description": description,
        "amount": amount,
        "type": txn_type,
    }


# =========================================================
# TEXT LAYOUT C
# =========================================================

def _parse_text_amount_line(
    date_text: str,
    remainder: str,
) -> dict | None:
    """
    Parse:

        Date Description Amount Balance

    Example:

        02-08-2026 Grocery Store -$86.42 $4913.58
    """

    amounts = _extract_amount_tokens(
        remainder
    )

    if len(amounts) < 2:
        return None

    # Last amount is normally balance.
    transaction_amount_text = amounts[-2]

    raw_amount = _parse_amount(
        transaction_amount_text
    )

    if raw_amount is None:
        return None

    description = _remove_amount_tokens(
        remainder
    )

    description = _clean_text(
        description
    )

    if not description:
        return None

    if raw_amount < 0:
        txn_type = "spend"
    else:
        txn_type = "earn"

    return {
        "date": _normalize_date(date_text),
        "description": description,
        "amount": abs(raw_amount),
        "type": txn_type,
    }


# =========================================================
# TEXT LAYOUT D
# =========================================================

def _parse_text_type_line(
    date_text: str,
    remainder: str,
) -> dict | None:
    """
    Parse:

        Date Description Type Amount Balance

    Example:

        01/08/2026 Salary Credit Deposit $1500.00 $5000.00

    or:

        02/08/2026 Grocery Store Debit $86.42 $4913.58
    """

    amounts = _extract_amount_tokens(
        remainder
    )

    if len(amounts) < 2:
        return None

    transaction_amount_text = amounts[-2]

    raw_amount = _parse_amount(
        transaction_amount_text
    )

    if raw_amount is None:
        return None

    before_amount = remainder

    # Remove transaction amount and balance.
    before_amount = _remove_amount_tokens(
        before_amount
    )

    words = before_amount.split()

    if not words:
        return None

    txn_type = None

    # Search from the end because type normally
    # appears immediately before amount.
    for count in range(
        min(4, len(words)),
        0,
        -1,
    ):

        candidate = " ".join(
            words[-count:]
        )

        normalized = _normalize_type(
            candidate
        )

        if normalized:
            txn_type = normalized
            words = words[:-count]
            break

    if txn_type is None:
        return None

    description = _clean_text(
        " ".join(words)
    )

    if not description:
        return None

    return {
        "date": _normalize_date(date_text),
        "description": description,
        "amount": abs(raw_amount),
        "type": txn_type,
    }


# =========================================================
# TEXT TRANSACTION PARSER
# =========================================================

def _parse_text_transactions(
    text: str,
) -> list[dict]:
    """
    Fallback parser for PDFs where pdfplumber cannot
    detect a table.

    Supports B/C/D layouts.
    """

    if not text:
        return []

    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    if not lines:
        return []

    layout = _detect_text_layout(
        lines
    )

    transactions = []

    current_transaction = None

    for line in lines:

        if _looks_like_header_line(line):
            continue

        if _is_noise_line(line):
            continue

        date_result = _extract_date_from_line(
            line
        )

        # -------------------------------------------------
        # New transaction line
        # -------------------------------------------------

        if date_result:

            date_text, remainder = date_result

            if layout == "debit_credit":

                transaction = (
                    _parse_text_debit_credit_line(
                        date_text,
                        remainder,
                    )
                )

            elif layout == "type":

                transaction = (
                    _parse_text_type_line(
                        date_text,
                        remainder,
                    )
                )

            else:

                transaction = (
                    _parse_text_amount_line(
                        date_text,
                        remainder,
                    )
                )

            if transaction:

                transactions.append(
                    transaction
                )

                current_transaction = transaction

                continue

            # If this is a date line but the transaction
            # couldn't be parsed, remember it for possible
            # wrapped description handling.

            current_transaction = {
                "date": _normalize_date(
                    date_text
                ),
                "_pending_description": remainder,
            }

            continue

        # -------------------------------------------------
        # Wrapped description
        # -------------------------------------------------

        if current_transaction:

            pending = current_transaction.get(
                "_pending_description"
            )

            if pending is not None:

                current_transaction[
                    "_pending_description"
                ] = _clean_text(
                    f"{pending} {line}"
                )

    # Remove internal helper fields.
    cleaned_transactions = []

    for transaction in transactions:

        transaction.pop(
            "_pending_description",
            None,
        )

        cleaned_transactions.append(
            transaction
        )

    return cleaned_transactions


# =========================================================
# DUPLICATE REMOVAL
# =========================================================

def _deduplicate_transactions(
    transactions: list[dict],
) -> list[dict]:
    """
    Prevent duplicate transactions when a PDF contains
    repeated headers or duplicated extraction regions.
    """

    unique = []
    seen = set()

    for transaction in transactions:

        key = (
            transaction.get("date"),
            transaction.get("description"),
            transaction.get("amount"),
            transaction.get("type"),
        )

        if key in seen:
            continue

        seen.add(key)
        unique.append(transaction)

    return unique


# =========================================================
# MAIN PDF PARSER
# =========================================================

def parse_pdf(file_bytes: bytes) -> list[dict]:
    """
    Extract transactions from a bank statement PDF.

    Strategy:

        1. Try normal pdfplumber table extraction.
        2. If tables are found, use table parser.
        3. If a page has no table, use text extraction.
        4. Combine results.
        5. Remove duplicates.

    Returns:

        [
            {
                "date": "2026-08-01",
                "description": "SWIGGY ORDER",
                "amount": 500.0,
                "type": "spend"
            }
        ]
    """

    all_transactions: list[dict] = []

    previous_headers: list[str] | None = None

    with pdfplumber.open(
        io.BytesIO(file_bytes)
    ) as pdf:

        for page in pdf.pages:

            page_transactions = []

            # =================================================
            # FIRST: NORMAL TABLE EXTRACTION
            # =================================================

            try:
                tables = page.extract_tables()
            except Exception:
                tables = []

            if tables:

                for table in tables:

                    if not table:
                        continue

                    header_result = _find_header(
                        table
                    )

                    if header_result:

                        header_index, headers = (
                            header_result
                        )

                        previous_headers = headers

                        rows = table[
                            header_index + 1:
                        ]

                    elif previous_headers:

                        headers = previous_headers
                        rows = table

                    else:
                        continue

                    for row in rows:

                        transaction = (
                            _normalize_row(
                                row,
                                headers,
                            )
                        )

                        if transaction:
                            page_transactions.append(
                                transaction
                            )

            # =================================================
            # SECOND: TEXT FALLBACK
            # =================================================

            #
            # If the page produced no transactions,
            # use text extraction.
            #
            if not page_transactions:

                try:
                    text = page.extract_text()
                except Exception:
                    text = None

                if text:

                    page_transactions = (
                        _parse_text_transactions(
                            text
                        )
                    )

            all_transactions.extend(
                page_transactions
            )

    return _deduplicate_transactions(
        all_transactions
    )