from app.services.categorization.rule_based import categorize


test_transactions = [
    "SWIGGY*ORDER 99213",
    "NEFT-HDFC0001-SALARY",
    "AMZN Mktp IN",
    "UBER*TRIP 4821",
    "NETFLIX.COM",
    "APOLLO PHARMACY",
]


for description in test_transactions:
    category = categorize(description)
    print(f"{description:<35} → {category}")