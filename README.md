# Smart Expense Tracker with Auto-Categorization

A Streamlit-based expense tracker that allows users to manage income and expenses, maintain their available balance, automatically categorize transactions, and upload transaction data through CSV files.

## Features

* Manual transaction entry
* Starting balance management
* Spend and Earn transactions
* Automatic balance calculation
* Insufficient balance validation
* Automatic transaction categorization
* SQLite database for storing transactions
* CSV transaction upload
* Transaction history table
* Monthly Earn and Spend summary

## Technologies Used

* Python
* Streamlit
* Pandas
* SQLite

## Project Structure

```text
Smart-Expense-Tracker-with-Auto-Categorization/
│
├── app.py
├── database.py
├── classifier.py
├── requirements.txt
├── Data/
│   └── sample_transaction.csv
├── db/
└── README.md
```

## How to Run

1. Clone the repository.

2. Create and activate a virtual environment.

3. Install the required packages:

```bash
pip install -r requirements.txt
```

4. Run the Streamlit application:

```bash
streamlit run app.py
```

## Usage

1. Choose **Manual Entry** or **Upload CSV**.
2. For Manual Entry, set the starting balance.
3. Add **Spend** or **Earn** transactions.
4. The available balance updates automatically.
5. View transactions in the transaction table.
6. View the current month's total Earn and Spend.
7. For CSV upload, upload a transaction file and import the data.
