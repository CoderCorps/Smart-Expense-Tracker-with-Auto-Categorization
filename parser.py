"""
parser.py

File parsing module for the Smart Expense Tracker.

Responsible only for extracting transaction data from CSV and PDF files.

Output structure:

date | description | amount

Validation, categorization, and database storage are handled
by other modules.
"""

import io
import re

import pandas as pd
from pypdf import PdfReader


# ============================================================
# DATE PATTERNS
# ============================================================

DATE_PATTERNS = [
    r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
    r"\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b",
]


# ============================================================
# AMOUNT PATTERN
# ============================================================

# Supports:
#
# 450
# 450.00
# 1200
# 1200.00
# 1800
# 8000
# 1,200
# 1,200.50
# ₹1,200
# ₹1,200.50
# $1,200.50
#
# The important fix here is that numbers can now have
# any number of digits, not just 1-3 digits.

AMOUNT_PATTERN = (
    r"(?:₹|\$)?"
    r"[+-]?"
    r"\d+"
    r"(?:,\d{3})*"
    r"(?:\.\d{1,2})?"
)


# ============================================================
# MAIN FILE PARSER
# ============================================================

def parse_file(uploaded_file):
    """
    Parse a CSV or PDF uploaded file.

    Args:
        uploaded_file:
            Streamlit UploadedFile-like object.

    Returns:
        pandas.DataFrame:
            Raw transaction data containing:
            date, description, amount

    Raises:
        ValueError:
            If the file is missing or unsupported.
    """

    if uploaded_file is None:
        raise ValueError("No file was provided.")

    file_name = getattr(
        uploaded_file,
        "name",
        ""
    ).lower()

    if file_name.endswith(".csv"):
        return parse_csv(uploaded_file)

    if file_name.endswith(".pdf"):
        return parse_pdf(uploaded_file)

    raise ValueError(
        "Unsupported file type. "
        "Please upload a CSV or PDF file."
    )


# ============================================================
# CSV PARSER
# ============================================================

def parse_csv(uploaded_file):
    """
    Parse a CSV file into a transaction DataFrame.

    The parser attempts to identify:
        date
        description
        amount

    Column names are matched case-insensitively.

    Returns:
        pandas.DataFrame
    """

    try:
        content = uploaded_file.read()

        # Try UTF-8 first
        try:
            text = content.decode("utf-8")

        except UnicodeDecodeError:
            # Fallback for common legacy encodings
            text = content.decode("latin-1")

        df = pd.read_csv(
            io.StringIO(text),
            engine="python"
        )

    except Exception as error:
        raise ValueError(
            f"Failed to parse CSV: {error}"
        ) from error

    if df.empty:
        raise ValueError(
            "The CSV file is empty."
        )

    # Normalize column names
    df.columns = (
        df.columns
        .astype(str)
        .str.strip()
        .str.lower()
    )

    # --------------------------------------------------------
    # Identify columns
    # --------------------------------------------------------

    date_col = None
    description_col = None
    amount_col = None

    for column in df.columns:

        # Date column
        if (
            "date" in column
            and date_col is None
        ):
            date_col = column

        # Description / narration column
        elif (
            any(
                word in column
                for word in [
                    "description",
                    "desc",
                    "narration",
                    "particular",
                    "details"
                ]
            )
            and description_col is None
        ):
            description_col = column

        # Amount column
        elif (
            any(
                word in column
                for word in [
                    "amount",
                    "amt"
                ]
            )
            and amount_col is None
        ):
            amount_col = column

    # --------------------------------------------------------
    # Check required columns
    # --------------------------------------------------------

    missing = []

    if date_col is None:
        missing.append("date")

    if description_col is None:
        missing.append("description")

    if amount_col is None:
        missing.append("amount")

    if missing:
        raise ValueError(
            "Could not identify required CSV columns: "
            + ", ".join(missing)
            + f". Found columns: {list(df.columns)}"
        )

    # --------------------------------------------------------
    # Return standard structure
    # --------------------------------------------------------

    result = df[
        [
            date_col,
            description_col,
            amount_col
        ]
    ].copy()

    result.columns = [
        "date",
        "description",
        "amount"
    ]

    return result


# ============================================================
# PDF PARSER
# ============================================================

def parse_pdf(uploaded_file):
    """
    Parse a text-based PDF bank statement.

    Supports:

    1. Single-line transactions:

        20/08/2026 SWIGGY FOOD ORDER 450.00

    2. Multi-line PDF table extraction:

        20/08/2026
        SWIGGY FOOD ORDER
        450.00

    Returns:
        pandas.DataFrame containing:
        date, description, amount

    Raises:
        ValueError:
            If the PDF cannot be read, contains no text,
            or no transaction rows can be identified.
    """

    # --------------------------------------------------------
    # Read PDF
    # --------------------------------------------------------

    try:
        content = uploaded_file.read()

        reader = PdfReader(
            io.BytesIO(content)
        )

    except Exception as error:
        raise ValueError(
            f"Failed to read PDF: {error}"
        ) from error

    # --------------------------------------------------------
    # Extract text from every page
    # --------------------------------------------------------

    full_text = ""

    for page in reader.pages:

        try:
            text = page.extract_text()

        except Exception:
            text = None

        if text:
            full_text += text + "\n"

    # --------------------------------------------------------
    # Check for extractable text
    # --------------------------------------------------------

    if not full_text.strip():

        raise ValueError(
            "Could not extract text from PDF. "
            "The PDF may be scanned/image-based "
            "or unsupported."
        )

    # --------------------------------------------------------
    # Convert text into clean lines
    # --------------------------------------------------------

    lines = [
        line.strip()
        for line in full_text.splitlines()
        if line.strip()
    ]

    # Compile regex patterns
    date_regex = re.compile(
        "|".join(DATE_PATTERNS)
    )

    amount_regex = re.compile(
        AMOUNT_PATTERN
    )

    transactions = []

    # ========================================================
    # METHOD 1
    #
    # Single-line transactions
    #
    # Example:
    #
    # 20/08/2026 SWIGGY FOOD ORDER 450.00
    #
    # ========================================================

    for line in lines:

        date_match = date_regex.search(line)

        if not date_match:
            continue

        amount_matches = list(
            amount_regex.finditer(line)
        )

        if not amount_matches:
            continue

        # Usually the rightmost amount is the transaction amount.
        amount_match = amount_matches[-1]

        description = line[
            date_match.end():
            amount_match.start()
        ].strip()

        # Normalize spaces
        description = re.sub(
            r"\s+",
            " ",
            description
        )

        # Ignore empty descriptions
        if len(description) < 2:
            continue

        # Clean amount
        amount_clean = (
            amount_match.group(0)
            .replace(",", "")
            .replace("₹", "")
            .replace("$", "")
            .strip()
        )

        try:
            amount = float(
                amount_clean
            )

        except ValueError:
            continue

        transactions.append({
            "date": date_match.group(0),
            "description": description,
            "amount": amount
        })

    # ========================================================
    # METHOD 2
    #
    # Multi-line / table-style PDF extraction
    #
    # Example:
    #
    # 20/08/2026
    # SWIGGY FOOD ORDER
    # 450.00
    #
    # 21/08/2026
    # UBER RIDE
    # 220.00
    #
    # ========================================================

    if not transactions:

        i = 0

        while i < len(lines):

            # Check for date
            date_match = date_regex.fullmatch(
                lines[i]
            )

            if not date_match:
                i += 1
                continue

            date_text = date_match.group(0)

            # Need at least:
            #
            # date
            # description
            # amount

            if i + 2 >= len(lines):
                break

            description = lines[
                i + 1
            ].strip()

            amount_text = lines[
                i + 2
            ].strip()

            # Check whether the next line is an amount
            amount_match = amount_regex.fullmatch(
                amount_text
            )

            if not amount_match:
                i += 1
                continue

            # Normalize description
            description = re.sub(
                r"\s+",
                " ",
                description
            )

            # Ignore obvious table headers
            if description.lower() in {
                "date",
                "description",
                "amount",
                "transaction",
                "details",
                "narration"
            }:
                i += 1
                continue

            # Clean amount
            amount_clean = (
                amount_match.group(0)
                .replace(",", "")
                .replace("₹", "")
                .replace("$", "")
                .strip()
            )

            try:
                amount = float(
                    amount_clean
                )

            except ValueError:
                i += 1
                continue

            transactions.append({
                "date": date_text,
                "description": description,
                "amount": amount
            })

            # Move to next possible transaction
            i += 3

    # ========================================================
    # FINAL CHECK
    # ========================================================

    if not transactions:

        raise ValueError(
            "No transaction rows could be extracted "
            "from the PDF."
        )

    return pd.DataFrame(
        transactions,
        columns=[
            "date",
            "description",
            "amount"
        ]
    )


# ============================================================
# TEST SECTION
# ============================================================

if __name__ == "__main__":

    print("=" * 60)
    print("Testing parser.py")
    print("=" * 60)

    # --------------------------------------------------------
    # CSV TEST
    # --------------------------------------------------------

    csv_content = """Date,Description,Amount
2026-08-20,Swiggy Food Order,450
2026-08-21,Uber Ride,220
2026-08-22,Amazon Purchase,1200
2026-08-23,Electricity Bill,1800
2026-08-24,Monthly Rent,8000
"""

    class MockFile:

        def __init__(
            self,
            name,
            content
        ):
            self.name = name
            self.content = content

        def read(self):
            return self.content.encode(
                "utf-8"
            )

    csv_file = MockFile(
        "sample.csv",
        csv_content
    )

    print("\nCSV TEST")
    print("-" * 40)

    try:

        csv_df = parse_file(
            csv_file
        )

        print(
            csv_df.to_string(
                index=False
            )
        )

    except Exception as error:

        print(
            f"CSV Error: {error}"
        )

    # --------------------------------------------------------
    # PDF LOGIC TEST
    # --------------------------------------------------------

    print("\nPDF LOGIC TEST")
    print("-" * 40)

    sample_pdf_text = """
    Sample Bank Statement

    Date
    Description
    Amount

    20/08/2026
    SWIGGY FOOD ORDER
    450.00

    21/08/2026
    UBER RIDE
    220.00

    22/08/2026
    AMAZON PURCHASE
    1200.00

    23/08/2026
    ELECTRICITY BILL
    1800.00

    24/08/2026
    MONTHLY RENT
    8000.00

    25/08/2026
    RANDOM EXPENSE
    500.00
    """

    test_lines = [
        line.strip()
        for line in sample_pdf_text.splitlines()
        if line.strip()
    ]

    date_regex = re.compile(
        "|".join(DATE_PATTERNS)
    )

    amount_regex = re.compile(
        AMOUNT_PATTERN
    )

    extracted = []

    i = 0

    while i < len(test_lines):

        date_match = date_regex.fullmatch(
            test_lines[i]
        )

        if not date_match:
            i += 1
            continue

        if i + 2 >= len(test_lines):
            break

        description = test_lines[
            i + 1
        ].strip()

        amount_text = test_lines[
            i + 2
        ].strip()

        amount_match = amount_regex.fullmatch(
            amount_text
        )

        if not amount_match:
            i += 1
            continue

        if description.lower() in {
            "date",
            "description",
            "amount"
        }:
            i += 1
            continue

        amount = (
            amount_match.group(0)
            .replace(",", "")
            .replace("₹", "")
            .replace("$", "")
        )

        try:
            amount = float(amount)

        except ValueError:
            i += 1
            continue

        extracted.append({
            "date": date_match.group(0),
            "description": description,
            "amount": amount
        })

        i += 3

    pdf_test_df = pd.DataFrame(
        extracted
    )

    print(
        pdf_test_df.to_string(
            index=False
        )
    )

    print("\n" + "=" * 60)
    print("Parser tests completed.")
    print("=" * 60)