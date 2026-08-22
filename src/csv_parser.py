import pandas as pd
import re
import csv
from io import BytesIO, StringIO


# ============================================================
# COLUMN NAME NORMALIZATION
# ============================================================

def normalize_column_name(column):
    """
    Convert different bank CSV column names into
    a standard comparable format.
    """

    column = str(column).strip().lower()

    # Remove special characters
    column = re.sub(
        r"[^a-z0-9]+",
        " ",
        column
    )

    # Remove extra spaces
    column = re.sub(
        r"\s+",
        " ",
        column
    ).strip()

    return column


# ============================================================
# COLUMN ALIASES
# ============================================================

DATE_COLUMNS = [
    "date",
    "transaction date",
    "txn date",
    "transaction_date",
    "txn_date",
    "value date",
    "posting date",
    "posted date",
    "transaction datetime",
    "transaction time"
]


DESCRIPTION_COLUMNS = [
    "description",
    "transaction description",
    "txn description",
    "transaction details",
    "transaction detail",
    "details",
    "narration",
    "particulars",
    "remarks",
    "merchant",
    "merchant name",
    "payee",
    "memo"
]


AMOUNT_COLUMNS = [
    "amount",
    "transaction amount",
    "txn amount",
    "transaction_amount",
    "txn_amount"
]


DEBIT_COLUMNS = [
    "debit",
    "debit amount",
    "withdrawal",
    "withdrawal amount",
    "withdrawals",
    "dr",
    "dr amount",
    "expense",
    "expenses"
]


CREDIT_COLUMNS = [
    "credit",
    "credit amount",
    "deposit",
    "deposit amount",
    "deposits",
    "cr",
    "cr amount",
    "income",
    "credits"
]


BALANCE_COLUMNS = [
    "balance",
    "closing balance",
    "available balance",
    "running balance",
    "account balance"
]


# ============================================================
# FIND COLUMN
# ============================================================

def find_column(columns, aliases):
    """
    Find a matching column using normalized column names.
    """

    normalized_columns = {
        normalize_column_name(col): col
        for col in columns
    }

    # Exact match
    for alias in aliases:

        normalized_alias = normalize_column_name(
            alias
        )

        if normalized_alias in normalized_columns:

            return normalized_columns[
                normalized_alias
            ]

    # Partial match
    for normalized_col, original_col in normalized_columns.items():

        for alias in aliases:

            normalized_alias = normalize_column_name(
                alias
            )

            if (
                normalized_alias in normalized_col
                or normalized_col in normalized_alias
            ):

                return original_col

    return None


# ============================================================
# CLEAN AMOUNT
# ============================================================

def clean_amount(value):
    """
    Convert messy currency values into float.

    Examples:

    ₹1,200.50 -> 1200.50
    Rs. 500 -> 500
    1,500 -> 1500
    -500 -> -500
    """

    if pd.isna(value):
        return None

    value = str(value).strip()

    if not value:
        return None

    # Remove currency symbols and text
    value = re.sub(
        r"(₹|rs\.?|inr)",
        "",
        value,
        flags=re.IGNORECASE
    )

    # Remove spaces
    value = value.replace(
        " ",
        ""
    )

    # Handle parentheses as negative
    if value.startswith("(") and value.endswith(")"):

        value = "-" + value[1:-1]

    # Remove commas
    value = value.replace(
        ",",
        ""
    )

    # Remove anything except digits, decimal point and minus
    value = re.sub(
        r"[^0-9.\-]",
        "",
        value
    )

    if not value:
        return None

    try:

        return float(value)

    except ValueError:

        return None


# ============================================================
# CLEAN DESCRIPTION
# ============================================================

def clean_description(value):
    """
    Clean transaction description.
    """

    if pd.isna(value):

        return ""

    value = str(value)

    # Remove extra spaces
    value = re.sub(
        r"\s+",
        " ",
        value
    ).strip()

    return value


# ============================================================
# FIND HEADER ROW
# ============================================================

def detect_header_row(file_bytes):
    """
    Detect the CSV header row.

    This helps when CSV files contain information above
    the actual transaction table.
    """

    try:

        text = file_bytes.decode(
            "utf-8-sig",
            errors="replace"
        )

    except Exception:

        text = file_bytes.decode(
            "latin-1",
            errors="replace"
        )

    lines = text.splitlines()

    for index, line in enumerate(lines):

        normalized = normalize_column_name(
            line
        )

        # Header should contain a date-like field
        # and transaction/amount-related field.

        has_date = any(
            normalize_column_name(alias)
            in normalized
            for alias in DATE_COLUMNS
        )

        has_description = any(
            normalize_column_name(alias)
            in normalized
            for alias in DESCRIPTION_COLUMNS
        )

        has_amount = any(
            normalize_column_name(alias)
            in normalized
            for alias in (
                AMOUNT_COLUMNS
                + DEBIT_COLUMNS
                + CREDIT_COLUMNS
            )
        )

        if has_date and (
            has_description or has_amount
        ):

            return index

    return 0


# ============================================================
# READ CSV
# ============================================================

def read_csv(file):
    """
    Read and normalize a CSV bank statement.

    Supports:

    date + amount + description

    date + debit + credit + description

    date + withdrawal + deposit + narration

    messy headers

    currency symbols

    commas in amounts

    extra rows above the header
    """

    # --------------------------------------------------------
    # Read uploaded file
    # --------------------------------------------------------

    file.seek(0)

    file_bytes = file.read()

    # --------------------------------------------------------
    # Detect header row
    # --------------------------------------------------------

    header_row = detect_header_row(
        file_bytes
    )

    # --------------------------------------------------------
    # Try multiple encodings
    # --------------------------------------------------------

    df = None

    encodings = [
        "utf-8-sig",
        "utf-8",
        "cp1252",
        "latin-1"
    ]

    for encoding in encodings:

        try:

            text = file_bytes.decode(
                encoding
            )

            df = pd.read_csv(
                StringIO(text),
                header=header_row
            )

            break

        except Exception:

            continue

    if df is None:

        raise ValueError(
            "Could not read the CSV file. "
            "Please check the file encoding or format."
        )

    # --------------------------------------------------------
    # Remove completely empty rows/columns
    # --------------------------------------------------------

    df = df.dropna(
        axis=0,
        how="all"
    )

    df = df.dropna(
        axis=1,
        how="all"
    )

    if df.empty:

        raise ValueError(
            "The CSV file contains no transaction data."
        )

    # --------------------------------------------------------
    # Find important columns
    # --------------------------------------------------------

    date_col = find_column(
        df.columns,
        DATE_COLUMNS
    )

    description_col = find_column(
        df.columns,
        DESCRIPTION_COLUMNS
    )

    amount_col = find_column(
        df.columns,
        AMOUNT_COLUMNS
    )

    debit_col = find_column(
        df.columns,
        DEBIT_COLUMNS
    )

    credit_col = find_column(
        df.columns,
        CREDIT_COLUMNS
    )

    # --------------------------------------------------------
    # Validate date
    # --------------------------------------------------------

    if date_col is None:

        raise ValueError(
            "Could not detect a date column. "
            "Expected something like: "
            "Date, Transaction Date, Txn Date or Value Date."
        )

    # --------------------------------------------------------
    # Validate description
    # --------------------------------------------------------

    if description_col is None:

        raise ValueError(
            "Could not detect a description column. "
            "Expected something like: "
            "Description, Narration, Particulars or Details."
        )

    # --------------------------------------------------------
    # Validate amount structure
    # --------------------------------------------------------

    if (
        amount_col is None
        and debit_col is None
        and credit_col is None
    ):

        raise ValueError(
            "Could not detect an amount column. "
            "Expected Amount, Debit/Credit, "
            "Withdrawal/Deposit or similar columns."
        )

    # ========================================================
    # CREATE STANDARD DATAFRAME
    # ========================================================

    result = pd.DataFrame()

    # --------------------------------------------------------
    # Date
    # --------------------------------------------------------

    result["date"] = pd.to_datetime(
        df[date_col],
        errors="coerce",
        dayfirst=False
    )

    # --------------------------------------------------------
    # Description
    # --------------------------------------------------------

    result["description"] = (
        df[description_col]
        .apply(clean_description)
    )

    # ========================================================
    # AMOUNT
    # ========================================================

    if amount_col is not None:

        # Single amount column
        result["amount"] = (
            df[amount_col]
            .apply(clean_amount)
        )

    else:

        # --------------------------------------------
        # Debit / Credit structure
        # --------------------------------------------

        debit_values = pd.Series(
            0.0,
            index=df.index
        )

        credit_values = pd.Series(
            0.0,
            index=df.index
        )

        if debit_col is not None:

            debit_values = (
                df[debit_col]
                .apply(clean_amount)
                .fillna(0)
            )

        if credit_col is not None:

            credit_values = (
                df[credit_col]
                .apply(clean_amount)
                .fillna(0)
            )

        # Expense/debit = positive amount
        # Income/credit = positive amount
        #
        # We keep amount positive here.
        # The classifier will determine Income/Expense
        # using the description.

        result["amount"] = (
            debit_values
            + credit_values
        )

    # ========================================================
    # CLEAN DATA
    # ========================================================

    # Remove rows without valid date
    result = result.dropna(
        subset=["date"]
    )

    # Remove rows without description
    result = result[
        result["description"].str.len() > 0
    ]

    # Remove rows without amount
    result = result.dropna(
        subset=["amount"]
    )

    # Remove zero-amount rows
    result = result[
        result["amount"] != 0
    ]

    # --------------------------------------------------------
    # Convert date to standard format
    # --------------------------------------------------------

    result["date"] = result[
        "date"
    ].dt.strftime(
        "%Y-%m-%d"
    )

    # --------------------------------------------------------
    # Make amount numeric
    # --------------------------------------------------------

    result["amount"] = pd.to_numeric(
        result["amount"],
        errors="coerce"
    )

    # --------------------------------------------------------
    # Reset index
    # --------------------------------------------------------

    result = result.reset_index(
        drop=True
    )

    # ========================================================
    # FINAL VALIDATION
    # ========================================================

    if result.empty:

        raise ValueError(
            "No valid transactions could be detected "
            "from the CSV file."
        )

    return result