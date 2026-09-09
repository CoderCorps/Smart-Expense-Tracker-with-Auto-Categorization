"""
PERSON B OWNS THIS FILE (along with pdf_parser.py and column_mapper.py).

CSV parser for transaction uploads.

The parser:
- Reads CSV files
- Normalizes common column names
- Handles comma-separated amounts such as "1,200.00"
- Automatically creates a `type` column when the CSV does not provide one
- Infers spend/earn from the transaction description when possible
"""

import io
import re

import pandas as pd


# Words that strongly indicate money coming into the account.
INCOME_KEYWORDS = [
    "salary",
    "payroll",
    "stipend",
    "income",
    "bonus",
    "wages",
    "salary credit",
    "salary credited",
    "credit salary",
    "refund",
    "cashback",
    "cash back",
]


def _normalize_column_name(column: str) -> str:
    """Normalize a CSV column name for easier matching."""
    column = str(column).strip().lower()
    column = re.sub(r"[^a-z0-9]+", "_", column)
    return column.strip("_")


def _infer_transaction_type(description: str, amount) -> str:
    """
    Infer transaction type when the CSV does not contain a type column.

    Returns:
        'earn' for obvious income/refund transactions.
        'spend' otherwise.
    """
    description_text = str(description).strip().lower()

    # Strong income/refund indicators.
    for keyword in INCOME_KEYWORDS:
        if keyword in description_text:
            return "earn"

    # If amount is negative, treat it as spending.
    try:
        numeric_amount = float(
            str(amount)
            .replace(",", "")
            .replace("₹", "")
            .strip()
        )

        if numeric_amount < 0:
            return "spend"

    except (ValueError, TypeError):
        pass

    # Most expense CSVs contain positive transaction amounts.
    return "spend"


def _add_missing_type_column(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add amount + type columns for different CSV layouts.

    Supports:
    1. date + amount + description
    2. date + debit + credit + narration
    """

    normalized = {
        _normalize_column_name(col): col
        for col in df.columns
    }

    # Already has type
    if "type" in normalized:
        return df

    # ----------------------------
    # BANK FORMAT (Debit/Credit)
    # ----------------------------
    if "debit" in normalized or "credit" in normalized:

        debit_col = normalized.get("debit")
        credit_col = normalized.get("credit")

        # Create unified amount column
        amounts = []
        types = []

        for _, row in df.iterrows():

            debit = (
                str(row[debit_col]).replace(",", "").strip()
                if debit_col else ""
            )

            credit = (
                str(row[credit_col]).replace(",", "").strip()
                if credit_col else ""
            )

            debit = "" if debit.lower() == "nan" else debit
            credit = "" if credit.lower() == "nan" else credit

            if credit:
                amounts.append(float(credit))
                types.append("earn")
            elif debit:
                amounts.append(float(debit))
                types.append("spend")
            else:
                amounts.append(0.0)
                types.append("spend")

        df["amount"] = amounts
        df["type"] = types

    # ----------------------------
    # SIMPLE FORMAT
    # ----------------------------
    else:

        description_col = None
        amount_col = None

        for col in df.columns:

            n = _normalize_column_name(col)

            if n in {
                "description",
                "narration",
                "details",
                "remarks",
                "particulars",
            }:
                description_col = col

            if n in {
                "amount",
                "transaction_amount",
            }:
                amount_col = col

        if amount_col:
            df["type"] = [
                _infer_transaction_type(desc, amt)
                for desc, amt in zip(
                    df[description_col],
                    df[amount_col],
                )
            ]

    return df
    # No type information exists, so infer it from description + amount.
    description_column = None

    for column in df.columns:
        normalized = _normalize_column_name(column)

        if normalized in {
            "description",
            "details",
            "transaction_description",
            "narration",
            "particulars",
            "remarks",
        }:
            description_column = column
            break

    # Find amount column.
    amount_column = None

    for column in df.columns:
        normalized = _normalize_column_name(column)

        if normalized in {
            "amount",
            "transaction_amount",
            "value",
            "debit",
            "credit",
        }:
            amount_column = column
            break

    if description_column is None:
        description_column = df.columns[0]

    if amount_column is None:
        df["type"] = "spend"
    else:
        df["type"] = [
            _infer_transaction_type(description, amount)
            for description, amount in zip(
                df[description_column],
                df[amount_column],
            )
        ]

    return df


def parse_csv(file_bytes: bytes) -> pd.DataFrame:
    """
    Parse an uploaded CSV and return a DataFrame.

    If the CSV does not contain a transaction `type` column,
    one is automatically generated.
    """

    df = pd.read_csv(
        io.BytesIO(file_bytes),
        thousands=",",
    )

    df = _add_missing_type_column(df)

    return df