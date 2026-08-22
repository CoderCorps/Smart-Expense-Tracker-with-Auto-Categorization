import sqlite3
import pandas as pd


DATABASE_PATH = "db/expenses.db"


# ==========================================
# CREATE DATABASE TABLES
# ==========================================

def create_table():

    connection = sqlite3.connect(DATABASE_PATH)
    cursor = connection.cursor()

    # Transactions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            transaction_id TEXT PRIMARY KEY,
            date TEXT,
            description TEXT,
            transaction_type TEXT,
            amount REAL,
            balance REAL,
            category TEXT
        )
    """)

    # Account table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS account (
            id INTEGER PRIMARY KEY,
            current_balance REAL
        )
    """)

    # Create account with 0 balance if it doesn't exist
    cursor.execute("""
        INSERT OR IGNORE INTO account
        (id, current_balance)
        VALUES (1, 0.0)
    """)

    connection.commit()
    connection.close()


# ==========================================
# GET CURRENT BALANCE
# ==========================================

def get_current_balance():

    connection = sqlite3.connect(DATABASE_PATH)
    cursor = connection.cursor()

    cursor.execute("""
        SELECT current_balance
        FROM account
        WHERE id = 1
    """)

    result = cursor.fetchone()

    connection.close()

    if result:
        return float(result[0])

    return 0.0


# ==========================================
# SET CURRENT BALANCE
# ==========================================

def set_current_balance(new_balance):

    connection = sqlite3.connect(DATABASE_PATH)
    cursor = connection.cursor()

    cursor.execute("""
        UPDATE account
        SET current_balance = ?
        WHERE id = 1
    """, (new_balance,))

    connection.commit()
    connection.close()


# ==========================================
# ADD TRANSACTION
# ==========================================

def add_transaction(
    transaction_id,
    transaction_date,
    description,
    transaction_type,
    amount,
    balance,
    category
):

    connection = sqlite3.connect(DATABASE_PATH)
    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO transactions
        (
            transaction_id,
            date,
            description,
            transaction_type,
            amount,
            balance,
            category
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        transaction_id,
        transaction_date,
        description,
        transaction_type,
        amount,
        balance,
        category
    ))

    connection.commit()
    connection.close()


# ==========================================
# GET ALL TRANSACTIONS
# ==========================================

def get_transactions():

    connection = sqlite3.connect(DATABASE_PATH)

    df = pd.read_sql_query("""
        SELECT
            transaction_id,
            date,
            description,
            transaction_type,
            amount,
            balance,
            category
        FROM transactions
        ORDER BY rowid
    """, connection)

    connection.close()

    return df