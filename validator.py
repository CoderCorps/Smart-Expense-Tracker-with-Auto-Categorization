"""
validator.py

Data validation and cleaning module for the Smart Expense Tracker.

Takes a pandas DataFrame containing transaction data, validates the structure,
cleans row‑level issues (dates, descriptions, amounts), and returns a clean
DataFrame ready for categorisation and storage.
"""

import pandas as pd


def validate_transactions(df):
    """
    Validate and clean a transaction DataFrame.

    Expected input columns (case‑insensitive):
        - date         (convertible to a date)
        - description  (non‑empty string)
        - amount       (numeric, with optional commas)

    The function:
        1. Normalises column names to lowercase and strips whitespace.
        2. Checks that all three required columns exist; raises ValueError if not.
        3. Removes completely empty rows (all three required columns missing).
        4. Converts dates to YYYY-MM-DD; drops rows with invalid dates.
        5. Strips whitespace from descriptions; drops rows with empty descriptions.
        6. Converts amounts to float (removing commas); drops rows with invalid amounts.
        7. Drops any remaining rows with null values in the core columns.
        8. Returns a clean DataFrame with only ['date', 'description', 'amount'].

    Args:
        df (pd.DataFrame): Raw transaction data.

    Returns:
        tuple: (cleaned_df, stats)
            - cleaned_df: pandas DataFrame with cleaned transactions.
            - stats: dict with counts of removed rows per issue.

    Raises:
        ValueError: If required columns are missing.
    """
    # -------------------- Initial checks --------------------
    if df is None:
        raise ValueError("Input DataFrame is None.")
    if df.empty:
        empty_df = pd.DataFrame(columns=['date', 'description', 'amount'])
        stats = {
            'original_rows': 0,
            'removed_empty_rows': 0,
            'removed_invalid_date': 0,
            'removed_empty_description': 0,
            'removed_invalid_amount': 0,
            'final_rows': 0,
        }
        return empty_df, stats

    # Work on a copy to avoid mutating the original
    df = df.copy()
    original_count = len(df)

    # -------------------- Column normalisation --------------------
    df.columns = df.columns.str.strip().str.lower()

    required = ['date', 'description', 'amount']
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}")

    # -------------------- Remove completely empty rows --------------------
    empty_rows_mask = df[required].isnull().all(axis=1)
    empty_rows_count = empty_rows_mask.sum()
    df = df[~empty_rows_mask].copy()

    # -------------------- Date validation --------------------
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    invalid_date_mask = df['date'].isna()
    invalid_date_count = invalid_date_mask.sum()
    df = df[~invalid_date_mask].copy()
    df['date'] = df['date'].dt.strftime('%Y-%m-%d')

    # -------------------- Description validation (FIXED) --------------------
    # Convert NaN to empty string, then strip whitespace, and keep only non‑empty
    df['description'] = df['description'].fillna('').astype(str).str.strip()
    empty_desc_mask = df['description'].eq('')
    empty_desc_count = empty_desc_mask.sum()
    df = df[~empty_desc_mask].copy()

    # -------------------- Amount validation --------------------
    df['amount'] = df['amount'].astype(str).str.replace(',', '', regex=False)
    df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
    invalid_amount_mask = df['amount'].isna()
    invalid_amount_count = invalid_amount_mask.sum()
    df = df[~invalid_amount_mask].copy()

    # -------------------- Final cleaning --------------------
    df = df.dropna(subset=required)
    df = df[required].copy()

    # -------------------- Statistics --------------------
    final_count = len(df)
    stats = {
        'original_rows': original_count,
        'removed_empty_rows': empty_rows_count,
        'removed_invalid_date': invalid_date_count,
        'removed_empty_description': empty_desc_count,
        'removed_invalid_amount': invalid_amount_count,
        'final_rows': final_count,
    }

    return df, stats


# -------------------- Demo / Test Section --------------------
if __name__ == "__main__":
    sample_data = pd.DataFrame({
        'Date': ['2026-08-20', 'invalid date', '2026-08-21', '2026-08-22', '2026-08-23'],
        'Description': ['Swiggy Order', 'Uber Ride', '', 'Amazon Purchase', 'Netflix'],
        'Amount': ['450', '220', '500', '1,200', 'abc'],
    })
    print("Original DataFrame:")
    print(sample_data)
    print("\n" + "-" * 50)

    clean_df, stats = validate_transactions(sample_data)
    print("\nCleaned DataFrame:")
    print(clean_df)
    print("\nValidation statistics:")
    for key, value in stats.items():
        print(f"  {key}: {value}")