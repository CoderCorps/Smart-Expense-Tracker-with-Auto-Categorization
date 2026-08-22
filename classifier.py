def categorize_transaction(description):

    description = description.lower()

    if "salary" in description or "freelance" in description or "bonus" in description:
        return "Income"

    elif "swiggy" in description or "zomato" in description:
        return "Food"

    elif "uber" in description or "ola" in description:
        return "Travel"

    elif "amazon" in description or "flipkart" in description:
        return "Shopping"

    elif "rent" in description:
        return "Rent"

    elif "electricity" in description or "water" in description:
        return "Utilities"

    else:
        return "Other"

print(categorize_transaction("Salary payment"))
print(categorize_transaction("Swiggy dinner"))
print(categorize_transaction("Uber ride"))
print(categorize_transaction("Amazon purchase"))
print(categorize_transaction("Electricity bill"))