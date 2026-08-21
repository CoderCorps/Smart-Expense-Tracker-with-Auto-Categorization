# 🧾 Smart Expense Tracker with Auto-Categorization

A Streamlit-based expense tracking application that allows users to upload transaction data through CSV or PDF bank statements.

The application parses the uploaded data, validates the transactions, automatically categorizes expenses using hardcoded keyword rules, stores the processed transactions in SQLite, and displays the stored data through a Streamlit interface.

## 🚀 Week 1 Goal

The Week 1 prototype focuses on building a standalone Streamlit application with the following pipeline:

```text
CSV / PDF
    ↓
Parser
    ↓
Validation
    ↓
Keyword-based Categorization
    ↓
SQLite Database
    ↓
Streamlit Display