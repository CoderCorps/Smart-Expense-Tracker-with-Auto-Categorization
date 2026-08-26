"""
PERSON A OWNS THIS FILE (along with pdf_parser.py and column_mapper.py).

CSV parsing is implemented as a working baseline. Things worth hardening
as you go (this is real Week 2-3 work, not just polish):
  - Handle different date formats (dd/mm/yyyy vs mm/dd/yyyy vs yyyy-mm-dd)
    instead of assuming pandas guesses right
  - Handle CSVs that use ',' as a thousands separator in amount ("1,200.00")
  - Reject / report rows with missing required fields instead of silently
    dropping them (see the `errors` list in UploadResult)
  - File size limits and a friendly error for non-CSV files
"""

import io

import pandas as pd


def parse_csv(file_bytes: bytes) -> pd.DataFrame:
    """Returns a DataFrame with the raw columns exactly as found in the file."""
    return pd.read_csv(io.BytesIO(file_bytes))
