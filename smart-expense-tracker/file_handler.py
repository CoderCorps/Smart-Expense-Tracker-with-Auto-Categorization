import pandas as pd
import pdfplumber
import re


def read_csv_file(uploaded_file):
	"""
	Reads an uploaded CSV file and returns a cleaned pandas DataFrame.
	Raises a ValueError with a friendly message if the file is invalid.
	"""
	try:
		df = pd.read_csv(uploaded_file)
	except Exception as e:
		raise ValueError(f"Could not read CSV file: {e}")

	df.columns = df.columns.str.lower().str.strip()

	required_columns = {"date", "description", "amount"}
	if not required_columns.issubset(set(df.columns)):
		raise ValueError(
			f"CSV is missing required columns. Expected: {required_columns}"
		)

	return _clean_dataframe(df)


def read_pdf_file(uploaded_file):
	"""
	Reads an uploaded PDF bank statement and extracts transaction rows.
	Expects a table with columns roughly matching Date, Description, Amount.
	Raises a ValueError with a friendly message if extraction fails.
	"""
	rows = []

	try:
		with pdfplumber.open(uploaded_file) as pdf:
			for page in pdf.pages:
				table = page.extract_table()
				if table is None:
					continue

				headers = [str(h).lower().strip() for h in table[0]]

				for row in table[1:]:
					row_dict = dict(zip(headers, row))
					rows.append(row_dict)

	except Exception as e:
		raise ValueError(f"Could not read PDF file: {e}")

	if not rows:
		raise ValueError("No transaction table could be found in this PDF.")

	df = pd.DataFrame(rows)
	df.columns = df.columns.str.lower().str.strip()

	required_columns = {"date", "description", "amount"}
	if not required_columns.issubset(set(df.columns)):
		raise ValueError(
			f"PDF table is missing required columns. Expected: {required_columns}"
		)

	return _clean_dataframe(df)


def _clean_dataframe(df):
	"""
	Standardizes a transactions DataFrame: strips whitespace, parses dates,
	converts amount to numeric, and drops empty/garbage rows.
	"""
	df = df.copy()

	df["description"] = df["description"].astype(str).str.strip()

	df["amount"] = (
		df["amount"]
		.astype(str)
		.apply(lambda x: re.sub(r"[^\d.\-]", "", x))
	)
	df["amount"] = pd.to_numeric(df["amount"], errors="coerce")

	df["date"] = pd.to_datetime(df["date"], errors="coerce")

	df = df.dropna(subset=["date", "description", "amount"])
	df = df[df["description"].str.strip() != ""]

	df = df.reset_index(drop=True)

	if df.empty:
		raise ValueError("No valid transactions found after cleaning the data.")

	return df
