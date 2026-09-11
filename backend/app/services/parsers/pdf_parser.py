"""
PDF bank-statement parser.

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

Each page is tried three ways, stopping at the first that
yields rows: ruled-table extraction, then word coordinates
(which preserve column positions), then flat text. See
parse_pdf() for why that order matters.

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
    - descriptions wrapped across two lines
"""


import io
import re

import pdfplumber

from backend.app.services.parsers.normalize import clean_text, parse_date, parse_money


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
    """Clean extracted PDF text. See services/parsers/normalize.py."""

    return clean_text(value)


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
    """Convert a money cell into a float. See parsers/normalize.py."""

    return parse_money(value)


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
    """
    Convert a bank date into YYYY-MM-DD.

    Falls back to the original text when the format isn't recognised;
    _looks_like_date() has already vetted the cell by this point, so
    this only happens for a format nobody has taught the parser yet.
    """

    parsed = parse_date(value)

    return parsed.isoformat() if parsed else _clean_text(value)


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

    # Keep the FIRST column for each canonical header. Statements routinely
    # carry both "Date" and "Value Date", which normalize to the same name —
    # zipping into a dict would silently let the value date win and shift
    # every transaction onto the wrong day.
    data: dict[str, str] = {}
    for header, value in zip(headers, values):
        if header not in data or not data[header]:
            data[header] = value

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
# WORD-POSITION PARSER
#
# The most reliable fallback when pdfplumber can't find a
# ruled table. Plain text extraction collapses a statement
# row into a single line, which throws away the one signal
# that tells a debit from a credit: which COLUMN a number
# sits in. An unsigned 86.42 under "Debit" and an unsigned
# 86.42 under "Credit" produce identical text.
#
# extract_words() keeps each word's x coordinates, so we can
# rebuild the columns from the header row's positions and put
# every number back in the column it came from.
# =========================================================

# Words whose vertical positions are within this many points
# belong to the same visual row.
_ROW_TOLERANCE = 3.0

# Horizontal gap (in points) that separates two header labels
# rather than two words of one label — it keeps "Value Date"
# together while splitting "Debit    Credit".
_HEADER_GAP = 8.0


def _group_words_into_lines(words: list[dict]) -> list[list[dict]]:
    """Bucket words into visual rows, each sorted left to right."""

    lines: dict[int, list[dict]] = {}

    for word in words:
        key = int(round(word["top"] / _ROW_TOLERANCE))
        lines.setdefault(key, []).append(word)

    return [
        sorted(line, key=lambda w: w["x0"])
        for _, line in sorted(lines.items())
    ]


def _header_columns(line: list[dict]) -> list[dict] | None:
    """
    Turn a header row into column definitions.

    Returns a list of {"label", "x0", "x1"}, or None when this
    line doesn't look like a header.
    """

    groups: list[list[dict]] = []

    for word in line:
        if groups and word["x0"] - groups[-1][-1]["x1"] <= _HEADER_GAP:
            groups[-1].append(word)
        else:
            groups.append([word])

    columns = []

    for group in groups:
        label = _normalize_header(
            " ".join(word["text"] for word in group)
        )
        columns.append(
            {
                "label": label,
                "x0": group[0]["x0"],
                "x1": group[-1]["x1"],
            }
        )

    labels = {column["label"] for column in columns}

    useful = labels & {
        "date",
        "description",
        "amount",
        "type",
        "debit",
        "credit",
        "balance",
    }

    if "date" not in useful or len(useful) < 2:
        return None

    return columns


def _column_boundaries(columns: list[dict]) -> list[float]:
    """Midpoints between adjacent columns, used to place a word."""

    return [
        (columns[index]["x1"] + columns[index + 1]["x0"]) / 2
        for index in range(len(columns) - 1)
    ]


def _cells_from_line(line: list[dict], columns: list[dict]) -> list[str]:
    """Distribute a row's words across the header's columns."""

    boundaries = _column_boundaries(columns)

    buckets: list[list[str]] = [[] for _ in columns]

    for word in line:
        centre = (word["x0"] + word["x1"]) / 2

        index = 0
        for boundary in boundaries:
            if centre < boundary:
                break
            index += 1

        buckets[index].append(word["text"])

    return [_clean_text(" ".join(bucket)) for bucket in buckets]


def _wrapped_description(cells: list[str], labels: list[str]) -> str | None:
    """
    Return this row's continuation text if it is the tail of a
    wrapped description, else None.

    A continuation line has text in the description column and
    nothing anywhere else — no date, no amounts. Anything else
    is a subtotal, a footer, or a row we failed to parse, and
    must not be glued onto the previous transaction.
    """

    description = ""

    for label, value in zip(labels, cells):
        if label == "description":
            description = description or value
        elif value:
            return None

    return description or None


def _rows_from_words(
    page,
    previous_columns: list[dict] | None,
) -> tuple[list[dict], list[dict] | None]:
    """
    Parse one page using word coordinates.

    Returns (transactions, columns). `columns` is handed back
    in for the next page, because continuation pages routinely
    drop the header row entirely.
    """

    try:
        words = page.extract_words(
            keep_blank_chars=False,
            use_text_flow=False,
        )
    except Exception:
        return [], previous_columns

    if not words:
        return [], previous_columns

    columns = previous_columns
    transactions: list[dict] = []

    # Index of the transaction a continuation line appends to.
    last_index: int | None = None

    for line in _group_words_into_lines(words):

        header = _header_columns(line)

        if header:
            columns = header
            last_index = None
            continue

        if not columns:
            continue

        labels = [column["label"] for column in columns]
        cells = _cells_from_line(line, columns)

        transaction = _normalize_row(cells, labels)

        if transaction:
            transactions.append(transaction)
            last_index = len(transactions) - 1
            continue

        if last_index is None:
            continue

        wrapped = _wrapped_description(cells, labels)

        if wrapped:
            previous = transactions[last_index]
            previous["description"] = _clean_text(
                previous["description"] + " " + wrapped
            )

    return transactions, columns


# =========================================================
# TEXT PARSER HELPERS
#
# Last-resort path, used only when a page yields neither a
# table nor usable word coordinates.
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


# One whitespace-delimited token that reads as money.
_MONEY_TOKEN_REGEX = re.compile(
    r"""
    ^
    [\(\-−+]?
    (?:\$|₹|Rs\.?|INR)?
    \d[\d,]*
    (?:\.\d{1,2})?
    \)?
    $
    """,
    re.IGNORECASE | re.VERBOSE,
)


def _split_trailing_amounts(text: str) -> tuple[str, list[str]]:
    """
    Split a row into (description, money tokens).

    Money columns are right-aligned, so the amounts are always
    the trailing run of numeric tokens. Scanning from the end
    and stopping at the first non-numeric token is what keeps a
    reference number inside a description ("UPI/1234567/SWIGGY
    250.00") from being mistaken for an amount.
    """

    tokens = text.split()

    index = len(tokens)

    while index > 0 and _MONEY_TOKEN_REGEX.match(tokens[index - 1]):
        index -= 1

    return " ".join(tokens[:index]), tokens[index:]


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

    remaining = line[match.end():].strip()

    return date_text, remaining


def _looks_like_header_line(line: str) -> bool:
    """Ignore PDF table header lines when using text extraction."""

    normalized = re.sub(r"[^a-z/ ]", " ", line.lower())
    normalized = re.sub(r"\s+", " ", normalized).strip()

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

    matches = sum(1 for word in header_words if word in normalized)

    return matches >= 2


_OPENING_BALANCE_REGEX = re.compile(
    r"opening balance|balance brought forward",
    re.IGNORECASE,
)


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

    return any(word in text for word in noise_words)


# =========================================================
# TEXT LAYOUT DETECTION
# =========================================================

def _detect_text_layout(lines: list[str]) -> str:
    """
    Guess whether the text PDF is:

        debit_credit = separate debit and credit columns
        amount       = one signed amount column
        type         = an explicit debit/credit type column
    """

    # Only the header line decides the layout. Scanning the
    # whole page would let the word "type" in a footer, or a
    # "DEBIT CARD PURCHASE" description, pick the layout for
    # every row on the page.
    header = next(
        (line for line in lines if _looks_like_header_line(line)),
        None,
    )

    text = (header or "\n".join(lines)).lower()

    if re.search(r"\btype\b|dr\s*/\s*cr", text):
        return "type"

    if "debit" in text and "credit" in text:
        return "debit_credit"

    return "amount"


# =========================================================
# BALANCE TRACKING
#
# In the debit/credit layout an empty column disappears from
# the extracted text, so a row collapses to "86.42 4913.58" —
# indistinguishable from a credit of the same size. The
# running balance disambiguates it: if the balance went down,
# the row was a debit.
# =========================================================

class _BalanceTracker:
    """Infers spend/earn from consecutive balance readings."""

    def __init__(self) -> None:
        self.balance: float | None = None

    def seed(self, balance: float | None) -> None:
        if balance is not None:
            self.balance = balance

    def direction(self, balance: float | None, amount: float) -> str | None:
        """
        Compare this row's closing balance against the previous
        one. Returns None when the delta doesn't reconcile with
        the amount — that means a column was misread, and the
        answer shouldn't be trusted.
        """

        if balance is None or self.balance is None:
            return None

        delta = balance - self.balance

        if abs(abs(delta) - abs(amount)) > 0.01:
            return None

        return "spend" if delta < 0 else "earn"

    def match(
        self,
        balance: float | None,
        candidates: list[float],
    ) -> tuple[int, float, str] | None:
        """
        Pick which of several trailing numbers is the actual
        transaction amount, by finding the one that explains
        the move in the running balance.

        Returns (index, amount, "spend" | "earn"), or None when
        no candidate reconciles — in which case the caller must
        fall back to guessing from column position.
        """

        if balance is None or self.balance is None:
            return None

        delta = balance - self.balance

        if abs(delta) < 0.01:
            return None

        direction = "spend" if delta < 0 else "earn"

        for index, value in enumerate(candidates):
            if abs(abs(value) - abs(delta)) <= 0.01:
                return index, abs(value), direction

        return None


# =========================================================
# TEXT LAYOUT: DEBIT / CREDIT COLUMNS
# =========================================================

def _parse_text_debit_credit_line(
    date_text: str,
    remainder: str,
    tracker: "_BalanceTracker",
) -> dict | None:
    """
    Parse:

        Date Description Debit Credit Balance

    Only one of debit/credit carries a value on a real row, so
    the text form is usually "<description> <amount> <balance>"
    with nothing to say which column the amount came from.

    Two things recover the missing information, in order:

      1. The running balance. If the closing balance moved by
         exactly one of the trailing numbers, that number is
         the transaction and the direction of the move is its
         type. This also survives a reference number sitting
         between the description and the amounts, which is
         common and which position-based parsing gets wrong.
      2. Failing that, column position among the trailing
         numbers, and finally an explicit minus sign.
    """

    description, amounts = _split_trailing_amounts(remainder)

    if len(amounts) < 2:
        return None

    values = [_parse_amount(token) for token in amounts]

    if any(value is None for value in values):
        return None

    balance = values[-1]
    candidates = values[:-1]

    # --- 1. Reconcile against the running balance ------------

    matched = tracker.match(balance, candidates)

    if matched is not None:
        index, amount, txn_type = matched

        # Whatever sat to the left of the real amount is part
        # of the description (a cheque or reference number),
        # not money. Put it back.
        leftover = amounts[:index]

        tracker.seed(balance)

        return {
            "date": _normalize_date(date_text),
            "description": _clean_text(
                " ".join([description, *leftover])
            ),
            "amount": amount,
            "type": txn_type,
        }

    # --- 2. Fall back to position and sign -------------------

    description = _clean_text(description)

    if not description:
        return None

    # Only the last two numbers before the balance can be the
    # debit/credit pair; anything earlier is a reference number.
    candidates = candidates[-2:]

    if len(candidates) == 2:
        debit, credit = candidates

        if abs(credit) > 0:
            amount, txn_type = abs(credit), "earn"
        else:
            amount, txn_type = abs(debit), "spend"

    else:
        value = candidates[0]
        amount = abs(value)

        if value < 0:
            # An explicit minus sign is authoritative.
            txn_type = "spend"
        else:
            # Nothing left to go on. Debits dominate a personal
            # statement, so that is the less-wrong default — and
            # it only applies on a page with no table, no word
            # coordinates, and no usable running balance.
            txn_type = "spend"

    tracker.seed(balance)

    return {
        "date": _normalize_date(date_text),
        "description": description,
        "amount": amount,
        "type": txn_type,
    }


# =========================================================
# TEXT LAYOUT: SINGLE SIGNED AMOUNT
# =========================================================

def _parse_text_amount_line(
    date_text: str,
    remainder: str,
    tracker: "_BalanceTracker",
) -> dict | None:
    """
    Parse:

        Date Description Amount Balance

    Example:

        02-08-2026 Grocery Store -$86.42 $4913.58
    """

    description, amounts = _split_trailing_amounts(remainder)

    if len(amounts) < 2:
        return None

    description = _clean_text(description)

    if not description:
        return None

    raw_amount = _parse_amount(amounts[-2])
    balance = _parse_amount(amounts[-1])

    if raw_amount is None:
        return None

    if raw_amount < 0:
        txn_type = "spend"
    else:
        # A positive number in a signed-amount column is an
        # earn, unless the balance says otherwise — which
        # happens when a statement prints magnitudes only.
        txn_type = tracker.direction(balance, raw_amount) or "earn"

    tracker.seed(balance)

    return {
        "date": _normalize_date(date_text),
        "description": description,
        "amount": abs(raw_amount),
        "type": txn_type,
    }


# =========================================================
# TEXT LAYOUT: EXPLICIT TYPE COLUMN
# =========================================================

def _parse_text_type_line(
    date_text: str,
    remainder: str,
    tracker: "_BalanceTracker",
) -> dict | None:
    """
    Parse:

        Date Description Type Amount Balance

    Example:

        01/08/2026 Salary Deposit $1500.00 $5000.00
        02/08/2026 Grocery Store Debit $86.42 $4913.58
    """

    before_amounts, amounts = _split_trailing_amounts(remainder)

    if len(amounts) < 2:
        return None

    raw_amount = _parse_amount(amounts[-2])
    balance = _parse_amount(amounts[-1])

    if raw_amount is None:
        return None

    words = before_amounts.split()

    if not words:
        return None

    txn_type = None

    # Search from the end: the type sits immediately before the
    # amount and can run to a few words ("transfer out").
    for count in range(min(4, len(words)), 0, -1):

        candidate = " ".join(words[-count:])

        normalized = _normalize_type(candidate)

        if normalized:
            txn_type = normalized
            words = words[:-count]
            break

    if txn_type is None:
        return None

    description = _clean_text(" ".join(words))

    if not description:
        return None

    tracker.seed(balance)

    return {
        "date": _normalize_date(date_text),
        "description": description,
        "amount": abs(raw_amount),
        "type": txn_type,
    }


# =========================================================
# TEXT TRANSACTION PARSER
# =========================================================

def _parse_text_transactions(text: str) -> list[dict]:
    """
    Fallback for PDFs where neither table extraction nor word
    coordinates are available.

    Supports the debit/credit, signed-amount and explicit-type
    layouts, and stitches wrapped descriptions back onto the
    transaction they belong to.
    """

    if not text:
        return []

    lines = [line.strip() for line in text.splitlines() if line.strip()]

    if not lines:
        return []

    parsers = {
        "debit_credit": _parse_text_debit_credit_line,
        "type": _parse_text_type_line,
        "amount": _parse_text_amount_line,
    }

    parse_line = parsers[_detect_text_layout(lines)]

    tracker = _BalanceTracker()

    transactions: list[dict] = []

    # A date line we couldn't parse yet, held back in case the
    # next line completes it — a wrapped description pushes the
    # amounts onto the second line.
    pending: tuple[str, str] | None = None

    for line in lines:

        if _looks_like_header_line(line):
            pending = None
            continue

        if _is_noise_line(line):
            # An opening balance line is noise as a transaction,
            # but it seeds the running balance, which is what
            # lets the first real row's direction be inferred.
            if _OPENING_BALANCE_REGEX.search(line):
                _, amounts = _split_trailing_amounts(line)
                if amounts:
                    tracker.seed(_parse_amount(amounts[-1]))
            pending = None
            continue

        date_result = _extract_date_from_line(line)

        if date_result:

            date_text, remainder = date_result

            transaction = parse_line(date_text, remainder, tracker)

            if transaction:
                transactions.append(transaction)
                pending = None
            else:
                # Hold it: the amounts may be on the next line.
                pending = (date_text, remainder)

            continue

        if pending:
            # Continuation of a wrapped row — join it to the
            # held date line and retry. This is the case the
            # first version dropped on the floor.
            date_text, remainder = pending

            joined = _clean_text(remainder + " " + line)

            transaction = parse_line(date_text, joined, tracker)

            if transaction:
                transactions.append(transaction)
                pending = None
            else:
                pending = (date_text, joined)

            continue

        if transactions:
            # Continuation of a row that already parsed: the
            # tail of its description wrapped onto this line.
            extra, amounts = _split_trailing_amounts(line)

            if extra and not amounts:
                transactions[-1]["description"] = _clean_text(
                    transactions[-1]["description"] + " " + extra
                )

    return transactions


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

class PdfParseError(Exception):
    """Raised when a file can't be opened as a PDF at all."""


def parse_pdf(file_bytes: bytes, max_pages: int = 50) -> list[dict]:
    """
    Extract transactions from a bank statement PDF.

    Each page is tried three ways, cheapest and most reliable
    first, stopping at the first one that yields rows:

        1. Ruled-table extraction. Works when the statement
           draws actual table borders.
        2. Word coordinates. Rebuilds the columns from the
           header's x positions — this is what keeps a debit
           from being read as a credit when one of the two
           columns is blank.
        3. Flat text. Last resort; see _parse_text_transactions
           for the heuristics and their limits.

    Results from every page are combined and de-duplicated.

    Raises:
        PdfParseError: the bytes aren't a readable PDF.

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

    # Carried across pages: continuation pages usually repeat
    # neither the table header nor the column labels.
    previous_headers: list[str] | None = None
    previous_columns: list[dict] | None = None

    try:
        pdf = pdfplumber.open(io.BytesIO(file_bytes))
    except Exception as exc:
        raise PdfParseError(str(exc)) from exc

    with pdf:

        for page in pdf.pages[:max_pages]:

            # -------------------------------------------------
            # 1. Ruled tables
            # -------------------------------------------------

            page_transactions, previous_headers = _rows_from_tables(
                page,
                previous_headers,
            )

            # -------------------------------------------------
            # 2. Word coordinates
            # -------------------------------------------------

            if not page_transactions:
                page_transactions, previous_columns = _rows_from_words(
                    page,
                    previous_columns,
                )

            # -------------------------------------------------
            # 3. Flat text
            # -------------------------------------------------

            if not page_transactions:
                try:
                    text = page.extract_text()
                except Exception:
                    text = None

                if text:
                    page_transactions = _parse_text_transactions(text)

            all_transactions.extend(page_transactions)

    return _deduplicate_transactions(all_transactions)


def _rows_from_tables(
    page,
    previous_headers: list[str] | None,
) -> tuple[list[dict], list[str] | None]:
    """Parse one page's ruled tables. Returns (rows, headers)."""

    try:
        tables = page.extract_tables()
    except Exception:
        return [], previous_headers

    transactions: list[dict] = []

    for table in tables or []:

        if not table:
            continue

        header_result = _find_header(table)

        if header_result:
            header_index, headers = header_result
            previous_headers = headers
            rows = table[header_index + 1:]

        elif previous_headers:
            headers = previous_headers
            rows = table

        else:
            continue

        for row in rows:
            transaction = _normalize_row(row, headers)

            if transaction:
                transactions.append(transaction)

    return transactions, previous_headers
