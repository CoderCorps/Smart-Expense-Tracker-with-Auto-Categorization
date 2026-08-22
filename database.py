"""
database.py

SQLite database layer for the Smart Expense Tracker.

Responsible for:
- Creating the SQLite database
- Creating the transactions table
- Inserting categorized transactions
- Retrieving stored transactions
- Clearing transactions during development/testing
"""

import sqlite3
from pathlib import Path

import pandas as pd


# -------------------- Database Configuration --------------------

BASE_DIR = Path(__file__).resolve().parent
DB_DIR = BASE_DIR / "database"
DB_PATH = DB_DIR / "expenses.db"


# -------------------- Connection --------------------

def get_connection():
    """
    Create and return a connection to the SQLite database.

    The database directory is created automatically if it
    does not already exist.
    """

    DB_DIR.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(DB_PATH)

    return connection


# -------------------- Table Creation --------------------

def create_table():
    """
    Create the transactions table if it does not already exist.
    """

    create_sql = """
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,
        description TEXT NOT NULL,
        amount REAL NOT NULL,
        category TEXT NOT NULL
    );
    """

    connection = get_connection()

    try:
        connection.execute(create_sql)
        connection.commit()

    except sqlite3.Error as error:
        raise sqlite3.Error(
            f"Failed to create transactions table: {error}"
        ) from error

    finally:
        connection.close()


# -------------------- Insert Transactions --------------------

def insert_transactions(df):
    """
    Insert transactions from a pandas DataFrame into SQLite.

    Required columns:
        date
        description
        amount
        category

    Returns:
        int: Number of rows inserted.
    """

    required_columns = [
        "date",
        "description",
        "amount",
        "category"
    ]

    if not isinstance(df, pd.DataFrame):
        raise ValueError(
            "Input must be a pandas DataFrame."
        )

    missing_columns = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"DataFrame is missing required columns: "
            f"{', '.join(missing_columns)}"
        )

    if df.empty:
        return 0

    # Make sure the database/table exists
    create_table()

    # Keep only the columns required by the database
    data = df[required_columns].copy()

    # Convert DataFrame rows into tuples
    records = list(
        data.itertuples(
            index=False,
            name=None
        )
    )

    connection = get_connection()

    insert_sql = """
    INSERT INTO transactions
    (date, description, amount, category)
    VALUES (?, ?, ?, ?)
    """

    try:
        cursor = connection.cursor()

        cursor.executemany(
            insert_sql,
            records
        )

        connection.commit()

        return cursor.rowcount

    except sqlite3.Error as error:
        connection.rollback()

        raise sqlite3.Error(
            f"Failed to insert transactions: {error}"
        ) from error

    finally:
        connection.close()


# -------------------- Retrieve Transactions --------------------

def get_transactions():
    """
    Retrieve all stored transactions.

    Returns:
        pandas.DataFrame:
            Columns:
            id, date, description, amount, category
    """

    create_table()

    connection = get_connection()

    query = """
    SELECT
        id,
        date,
        description,
        amount,
        category
    FROM transactions
    ORDER BY date DESC, id DESC
    """

    try:
        return pd.read_sql_query(
            query,
            connection
        )

    except sqlite3.Error as error:
        raise sqlite3.Error(
            f"Failed to retrieve transactions: {error}"
        ) from error

    finally:
        connection.close()


# -------------------- Clear Transactions --------------------

def clear_transactions():
    """
    Delete all transactions.

    This function is intended for development/testing only.

    Returns:
        int: Number of deleted rows.
    """

    create_table()

    connection = get_connection()

    try:
        cursor = connection.execute(
            "DELETE FROM transactions"
        )

        connection.commit()

        return cursor.rowcount

    except sqlite3.Error as error:
        connection.rollback()

        raise sqlite3.Error(
            f"Failed to clear transactions: {error}"
        ) from error

    finally:
        connection.close()


# -------------------- Demo / Test --------------------

if __name__ == "__main__":

    sample_data = pd.DataFrame({
        "date": [
            "2026-08-20",
            "2026-08-21",
            "2026-08-22"
        ],

        "description": [
            "Swiggy Order",
            "Uber Ride",
            "Amazon Purchase"
        ],

        "amount": [
            450.0,
            220.0,
            1200.0
        ],

        "category": [
            "Food",
            "Travel",
            "Shopping"
        ]
    })

    print("================================")
    print(" Testing database.py")
    print("================================")

    # Create database/table
    print("\nCreating database and table...")
    create_table()
    print("Table ready.")

    # Clear previous test data
    print("\nClearing previous test data...")
    deleted = clear_transactions()
    print(f"Deleted rows: {deleted}")

    # Insert sample data
    print("\nInserting sample transactions...")
    inserted = insert_transactions(sample_data)
    print(f"Inserted rows: {inserted}")

    # Retrieve data
    print("\nStored transactions:")

    stored_data = get_transactions()

    print(
        stored_data.to_string(index=False)
    )

    print("\n================================")
    print(" Database test completed!")
    print("================================")