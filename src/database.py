import sqlite3
import os
import pandas as pd


# ============================================================
# DATABASE CONFIGURATION
# ============================================================

DB_PATH = "database/expenses.db"


# ============================================================
# CREATE / UPDATE DATABASE
# ============================================================

def create_table():
    """
    Create the expenses table and automatically add
    missing columns if an older database exists.
    """

    # Create database folder
    os.makedirs(
        "database",
        exist_ok=True
    )

    connection = sqlite3.connect(
        DB_PATH
    )

    cursor = connection.cursor()

    # Create table if it doesn't exist
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            amount REAL NOT NULL,
            type TEXT,
            description TEXT NOT NULL,
            category TEXT
        )
    """)

    # --------------------------------------------------------
    # Check existing columns
    # --------------------------------------------------------

    cursor.execute(
        "PRAGMA table_info(expenses)"
    )

    existing_columns = [
        row[1]
        for row in cursor.fetchall()
    ]

    # --------------------------------------------------------
    # Add missing 'type' column
    # --------------------------------------------------------

    if "type" not in existing_columns:

        cursor.execute("""
            ALTER TABLE expenses
            ADD COLUMN type TEXT
        """)

        # Existing records are assumed to be expenses
        cursor.execute("""
            UPDATE expenses
            SET type = 'Expense'
            WHERE type IS NULL
        """)

    # --------------------------------------------------------
    # Add missing 'category' column if necessary
    # --------------------------------------------------------

    if "category" not in existing_columns:

        cursor.execute("""
            ALTER TABLE expenses
            ADD COLUMN category TEXT
        """)

    connection.commit()

    connection.close()


# ============================================================
# INSERT TRANSACTIONS
# ============================================================
def insert_expenses(df):
    """
    Insert transactions into SQLite while preventing duplicates.

    A transaction is considered duplicate when:
    date + amount + type + description + category
    are all the same.
    """

    create_table()

    connection = sqlite3.connect(
        DB_PATH
    )

    cursor = connection.cursor()

    inserted_count = 0
    duplicate_count = 0

    for _, row in df.iterrows():

        # Check whether transaction already exists
        cursor.execute(
            """
            SELECT id
            FROM expenses
            WHERE date = ?
              AND amount = ?
              AND type = ?
              AND description = ?
              AND category = ?
            """,
            (
                str(row["date"]),
                float(row["amount"]),
                str(row["type"]),
                str(row["description"]),
                str(row["category"])
            )
        )

        existing_transaction = cursor.fetchone()

        # --------------------------------------------
        # Transaction already exists
        # --------------------------------------------

        if existing_transaction:

            duplicate_count += 1

        # --------------------------------------------
        # New transaction
        # --------------------------------------------

        else:

            cursor.execute(
                """
                INSERT INTO expenses
                (
                    date,
                    amount,
                    type,
                    description,
                    category
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    str(row["date"]),
                    float(row["amount"]),
                    str(row["type"]),
                    str(row["description"]),
                    str(row["category"])
                )
            )

            inserted_count += 1

    connection.commit()

    connection.close()

    return inserted_count, duplicate_count
# ============================================================
# GET TRANSACTIONS
# ============================================================

def get_expenses():
    """
    Retrieve all stored transactions.
    """

    create_table()

    connection = sqlite3.connect(
        DB_PATH
    )

    df = pd.read_sql_query(
        """
        SELECT
            id,
            date,
            amount,
            type,
            description,
            category
        FROM expenses
        ORDER BY date DESC
        """,
        connection
    )

    connection.close()

    return df


# ============================================================
# CLEAR DATABASE
# ============================================================

def clear_expenses():
    """
    Delete all stored transactions.
    """

    create_table()

    connection = sqlite3.connect(
        DB_PATH
    )

    connection.execute(
        "DELETE FROM expenses"
    )

    connection.commit()

    connection.close()