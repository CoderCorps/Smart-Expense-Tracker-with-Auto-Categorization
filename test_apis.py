"""
Manual verification script for Person A backend functionality
"""
import requests
import json
from datetime import date

BASE_URL = "http://127.0.0.1:8000/api/v1"

# Test 1: Signup
print("=" * 60)
print("TEST 1: SIGNUP")
signup_resp = requests.post(f"{BASE_URL}/auth/signup", json={
    "email": "testuser@example.com",
    "full_name": "Test User",
    "password": "testpass123"
})
print(f"Status: {signup_resp.status_code}")
if signup_resp.status_code == 201:
    user = signup_resp.json()
    print(f"✓ User created: {user['email']}")
    user_id = user['id']
else:
    print(f"✗ Failed: {signup_resp.text}")
    user_id = None

# Test 2: Login
print("\n" + "=" * 60)
print("TEST 2: LOGIN")
login_resp = requests.post(f"{BASE_URL}/auth/login", data={
    "username": "testuser@example.com",
    "password": "testpass123"
})
print(f"Status: {login_resp.status_code}")
if login_resp.status_code == 200:
    token_data = login_resp.json()
    access_token = token_data['access_token']
    print(f"✓ Login successful, token acquired")
else:
    print(f"✗ Failed: {login_resp.text}")
    access_token = None

headers = {"Authorization": f"Bearer {access_token}"} if access_token else {}

# Test 3: Get current user
print("\n" + "=" * 60)
print("TEST 3: GET CURRENT USER (/auth/me)")
me_resp = requests.get(f"{BASE_URL}/auth/me", headers=headers)
print(f"Status: {me_resp.status_code}")
if me_resp.status_code == 200:
    print(f"✓ {me_resp.json()}")
else:
    print(f"✗ Failed: {me_resp.text}")

# Test 4: List categories
print("\n" + "=" * 60)
print("TEST 4: LIST CATEGORIES")
cats_resp = requests.get(f"{BASE_URL}/categorization/categories", headers=headers)
print(f"Status: {cats_resp.status_code}")
if cats_resp.status_code == 200:
    cats = cats_resp.json()
    print(f"✓ {len(cats)} categories found")
    if cats:
        print(f"  First: {cats[0]['name']}")
        category_id = cats[0]['id']
else:
    print(f"✗ Failed: {cats_resp.text}")
    category_id = None

# Test 5: Create transaction (uncategorized)
print("\n" + "=" * 60)
print("TEST 5: CREATE UNCATEGORIZED TRANSACTION")
create_tx_resp = requests.post(
    f"{BASE_URL}/transactions",
    json={
        "date": str(date.today()),
        "description": "Coffee at Starbucks",
        "amount": 5.50,
        "type": "spend"
    },
    headers=headers
)
print(f"Status: {create_tx_resp.status_code}")
if create_tx_resp.status_code == 201:
    tx = create_tx_resp.json()
    print(f"✓ Transaction created: {tx['id']}")
    print(f"  - description: {tx['description']}")
    print(f"  - raw_description: {tx['raw_description']}")
    print(f"  - amount: {tx['amount']}")
    print(f"  - type: {tx['type']}")
    print(f"  - category_id: {tx['category_id']}")
    print(f"  - category_source: {tx['category_source']}")
    print(f"  - source: {tx['source']}")
    tx_id = tx['id']
else:
    print(f"✗ Failed: {create_tx_resp.text}")
    tx_id = None

# Test 6: Create transaction (with category)
print("\n" + "=" * 60)
print("TEST 6: CREATE CATEGORIZED TRANSACTION")
if category_id:
    create_tx2_resp = requests.post(
        f"{BASE_URL}/transactions",
        json={
            "date": str(date.today()),
            "description": "Grocery shopping",
            "amount": 75.00,
            "type": "spend",
            "category_id": category_id
        },
        headers=headers
    )
    print(f"Status: {create_tx2_resp.status_code}")
    if create_tx2_resp.status_code == 201:
        tx = create_tx2_resp.json()
        print(f"✓ Transaction created: {tx['id']}")
        print(f"  - category_id: {tx['category_id']}")
        print(f"  - category_name: {tx['category_name']}")
        print(f"  - category_source: {tx['category_source']}")
    else:
        print(f"✗ Failed: {create_tx2_resp.text}")
else:
    print("✗ Skipped (no category found)")

# Test 7: List transactions
print("\n" + "=" * 60)
print("TEST 7: LIST TRANSACTIONS")
list_tx_resp = requests.get(f"{BASE_URL}/transactions", headers=headers)
print(f"Status: {list_tx_resp.status_code}")
if list_tx_resp.status_code == 200:
    txs = list_tx_resp.json()
    print(f"✓ {len(txs)} transactions found")
else:
    print(f"✗ Failed: {list_tx_resp.text}")

# Test 8: Get single transaction
print("\n" + "=" * 60)
print("TEST 8: GET SINGLE TRANSACTION")
if tx_id:
    get_tx_resp = requests.get(f"{BASE_URL}/transactions/{tx_id}", headers=headers)
    print(f"Status: {get_tx_resp.status_code}")
    if get_tx_resp.status_code == 200:
        tx = get_tx_resp.json()
        print(f"✓ Retrieved transaction {tx['id']}")
    else:
        print(f"✗ Failed: {get_tx_resp.text}")
else:
    print("✗ Skipped (no transaction to retrieve)")

# Test 9: Update category
print("\n" + "=" * 60)
print("TEST 9: UPDATE TRANSACTION CATEGORY")
if tx_id and category_id:
    update_resp = requests.put(
        f"{BASE_URL}/transactions/{tx_id}/category",
        json={"category_id": category_id},
        headers=headers
    )
    print(f"Status: {update_resp.status_code}")
    if update_resp.status_code == 200:
        tx = update_resp.json()
        print(f"✓ Transaction updated")
        print(f"  - category_source: {tx['category_source']}")
    else:
        print(f"✗ Failed: {update_resp.text}")
else:
    print("✗ Skipped (missing tx_id or category_id)")

print("\n" + "=" * 60)
print("ALL TESTS COMPLETE")
