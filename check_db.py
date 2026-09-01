import sqlite3

conn = sqlite3.connect('expense_tracker.db')
c = conn.cursor()
c.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = [row[0] for row in c.fetchall()]
print("Tables:", tables)

# Check schema for users table
if 'users' in tables:
    c.execute("PRAGMA table_info(users);")
    print("\nUsers schema:")
    for row in c.fetchall():
        print(f"  {row[1]}: {row[2]}")

# Check schema for transactions table  
if 'transactions' in tables:
    c.execute("PRAGMA table_info(transactions);")
    print("\nTransactions schema:")
    for row in c.fetchall():
        print(f"  {row[1]}: {row[2]}")

# Check schema for categories table
if 'categories' in tables:
    c.execute("PRAGMA table_info(categories);")
    print("\nCategories schema:")
    for row in c.fetchall():
        print(f"  {row[1]}: {row[2]}")

conn.close()
