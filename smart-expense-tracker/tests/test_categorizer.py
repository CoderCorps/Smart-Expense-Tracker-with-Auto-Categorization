import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from categorizer import categorize_transaction, categorize_dataframe
import pandas as pd


def test_food_category():
	assert categorize_transaction("SWIGGY BANGALORE ORDER") == "Food"


def test_transport_category():
	assert categorize_transaction("UBER TRIP HSR LAYOUT") == "Transport"


def test_shopping_category():
	assert categorize_transaction("AMAZON PAY ONLINE SHOPPING") == "Shopping"


def test_unknown_defaults_to_other():
	assert categorize_transaction("RANDOM UNKNOWN TEXT") == "Other"


def test_empty_description_defaults_to_other():
	assert categorize_transaction("") == "Other"
	assert categorize_transaction(None) == "Other"


def test_categorize_dataframe_adds_category_column():
	df = pd.DataFrame({
		"description": ["SWIGGY ORDER", "UBER RIDE", "UNKNOWN TEXT"]
	})
	result = categorize_dataframe(df)
	assert list(result["category"]) == ["Food", "Transport", "Other"]
