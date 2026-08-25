# Smart-Expense-Tracker-with-Auto-Categorization
Smart Expense Tracker is a Streamlit app for cleaning, categorizing, and exploring bank transactions from CSV or PDF statements.

Features
Upload CSV and PDF transaction statements
Clean dates, descriptions, and currency-formatted amounts
Categorize transactions using keyword matching
View dashboard metrics and spending charts
Search and filter the transaction ledger
Explore category distribution, top merchants, and monthly movement
Requirements
Python 3.10 or newer
Setup
Create and activate a virtual environment, then install the dependencies:

python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
Run the app
streamlit run app.py
Open http://localhost:8501 in your browser.

Input format
CSV files must include these columns:

date,description,amount
PDF statements should contain a transaction table with equivalent column names. Amounts may include currency symbols and commas.

Run tests
From the project directory:

pytest
Project structure
app.py                    Streamlit user interface
categorizer.py            Keyword-based categorization
file_handler.py           CSV/PDF parsing and data cleaning
data/sample_transactions.csv
tests/                    Automated tests
screenshots/              Application screenshots
