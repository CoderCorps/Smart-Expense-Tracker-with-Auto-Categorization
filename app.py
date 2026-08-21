"""
app.py

Streamlit user interface for the Smart Expense Tracker.

Orchestrates the entire pipeline:
    upload → parse → validate → categorise → store → display
"""

import streamlit as st

from parser import parse_file
from validator import validate_transactions
from categorizer import categorize_transaction
from database import (
    create_table,
    insert_transactions,
    get_transactions,
    clear_transactions
)


def main():
    st.set_page_config(page_title="Smart Expense Tracker", layout="wide")
    st.title("🧾 Smart Expense Tracker")
    st.markdown("Upload a CSV or PDF bank statement, and the app will parse, validate, categorise, and store the transactions.")

    try:
        create_table()
    except Exception as e:
        st.error(f"Database initialization failed: {e}")
        return

    uploaded_file = st.file_uploader(
        "Choose a CSV or PDF file",
        type=["csv", "pdf"],
        help="Upload a CSV or PDF containing transaction data."
    )

    col1, col2 = st.columns(2)

    with col1:
        if st.button("🚀 Process & Save Transactions"):
            if uploaded_file is None:
                st.warning("Please upload a file first.")
            else:
                try:
                    with st.spinner("Parsing file..."):
                        raw_df = parse_file(uploaded_file)

                    with st.spinner("Validating data..."):
                        clean_df, stats = validate_transactions(raw_df)

                    if clean_df.empty:
                        st.warning("No valid transactions found after validation. Nothing to save.")
                        st.session_state['stats'] = stats
                        st.session_state['processed'] = False
                    else:
                        with st.spinner("Categorising transactions..."):
                            clean_df['category'] = clean_df['description'].apply(categorize_transaction)

                        with st.spinner("Saving to database..."):
                            inserted = insert_transactions(clean_df)

                        st.success(f"✅ Successfully inserted {inserted} transactions.")
                        st.session_state['stats'] = stats
                        st.session_state['processed'] = True

                except Exception as e:
                    st.error(f"❌ Error processing file: {e}")

    with col2:
        confirm_clear = st.checkbox("☑️ I confirm I want to delete all transactions", key="confirm_clear")
        if st.button("🗑️ Clear All Data", disabled=not confirm_clear):
            try:
                deleted = clear_transactions()
                st.info(f"Cleared {deleted} transactions from database.")
                st.session_state['processed'] = False
                st.rerun()
            except Exception as e:
                st.error(f"Error clearing data: {e}")

    if 'stats' in st.session_state and st.session_state.get('processed', False):
        stats = st.session_state['stats']
        st.subheader("📊 Validation Statistics")
        col_stats1, col_stats2 = st.columns(2)
        with col_stats1:
            st.metric("Original rows", stats['original_rows'])
            st.metric("Removed invalid dates", stats['removed_invalid_date'])
            st.metric("Removed empty descriptions", stats['removed_empty_description'])
        with col_stats2:
            st.metric("Removed empty rows", stats['removed_empty_rows'])
            st.metric("Removed invalid amounts", stats['removed_invalid_amount'])
            st.metric("Final rows inserted", stats['final_rows'])

    st.divider()
    st.subheader("📋 Stored Transactions")

    try:
        df = get_transactions()
        if df.empty:
            st.info("No transactions in the database. Upload and process a file to add data.")
        else:
            st.dataframe(df, width='stretch')   # fixed deprecation
            st.subheader("📈 Category Summary")
            summary = df['category'].value_counts().reset_index()
            summary.columns = ['Category', 'Count']
            st.dataframe(summary, width='stretch')  # fixed deprecation
    except Exception as e:
        st.error(f"Error reading from database: {e}")


if __name__ == "__main__":
    main()