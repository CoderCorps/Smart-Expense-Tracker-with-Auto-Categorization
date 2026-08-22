import re
import pandas as pd
from pypdf import PdfReader


def extract_text_from_pdf(file):
    """
    Extract text from uploaded PDF.
    """

    reader = PdfReader(file)

    text = ""

    for page in reader.pages:
        page_text = page.extract_text()

        if page_text:
            text += page_text + "\n"

    return text


def parse_transactions_from_pdf(text):
    """
    Parse bank statement where PDF extraction places
    date, description and amounts on separate lines.
    """

    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    transactions = []

    # Date formats supported:
    # 01-Aug-2026
    # 01/08/2026
    # 2026-08-01

    date_pattern = re.compile(
        r"^(?:"
        r"\d{2}-[A-Za-z]{3}-\d{4}"
        r"|"
        r"\d{2}/\d{2}/\d{4}"
        r"|"
        r"\d{4}-\d{2}-\d{2}"
        r")$"
    )

    amount_pattern = re.compile(
        r"^(?:₹\s*)?"
        r"-?\d[\d,]*(?:\.\d{2})?"
        r"$"
    )

    i = 0

    while i < len(lines):

        # ---------------------------------
        # Look for transaction date
        # ---------------------------------

        if not date_pattern.match(lines[i]):
            i += 1
            continue

        date = lines[i]

        i += 1

        # ---------------------------------
        # Get description
        # ---------------------------------

        if i >= len(lines):
            break

        description = lines[i]

        # Ignore PDF headers
        if description.lower() in [
            "transaction details",
            "description",
            "particulars",
            "date"
        ]:
            i += 1
            continue

        i += 1

        # ---------------------------------
        # Find amounts after description
        # ---------------------------------

        amounts = []

        while i < len(lines):

            current = lines[i]

            # If next transaction starts,
            # stop current transaction.
            if date_pattern.match(current):
                break

            # Stop at note/footer
            if current.lower().startswith("note:"):
                break

            # Check whether current line is amount
            if amount_pattern.match(current):

                clean_amount = (
                    current
                    .replace(",", "")
                    .replace("₹", "")
                    .strip()
                )

                try:
                    amounts.append(
                        float(clean_amount)
                    )
                except ValueError:
                    pass

            i += 1

        # ---------------------------------
        # We need at least one amount
        # ---------------------------------

        if not amounts:
            continue

        # In our bank statement:
        #
        # Expense:
        # amount + balance
        #
        # Income:
        # credit amount + balance
        #
        # Therefore the FIRST amount is
        # the transaction amount.

        transaction_amount = amounts[0]

        transactions.append({
            "date": date,
            "amount": transaction_amount,
            "description": description
        })

    # ---------------------------------
    # Create DataFrame
    # ---------------------------------

    df = pd.DataFrame(
        transactions,
        columns=[
            "date",
            "amount",
            "description"
        ]
    )

    # ---------------------------------
    # Clean dates
    # ---------------------------------

    if not df.empty:

        df["date"] = pd.to_datetime(
            df["date"],
            errors="coerce",
            dayfirst=True
        )

        df = df.dropna(
            subset=["date"]
        )

        df["date"] = df["date"].dt.strftime(
            "%Y-%m-%d"
        )

    return df