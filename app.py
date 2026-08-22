import streamlit as st
import pandas as pd
from datetime import date

from database import (
    create_table,
    get_transactions,
    add_transaction,
    get_current_balance,
    set_current_balance
)

from classifier import categorize_transaction


# ==========================================
# PAGE CONFIG
# ==========================================

st.set_page_config(
    page_title="Smart Expense Tracker",
    page_icon="💰"
)


# ==========================================
# CREATE DATABASE TABLES
# ==========================================

create_table()


# ==========================================
# TITLE
# ==========================================

st.title("💰 Smart Expense Tracker")

st.write(
    "Track your income and expenses in one place."
)


# ==========================================
# CHOOSE INPUT METHOD
# ==========================================

option = st.radio(
    "How do you want to add transactions?",
    ["📝 Manual Entry", "📂 Upload CSV"]
)


# ============================================================
# MANUAL ENTRY
# ============================================================

if option == "📝 Manual Entry":

    st.subheader("📝 Manual Entry")

    st.write(
        "Set your initial balance and add transactions manually."
    )

    # ==========================================
    # GET CURRENT BALANCE
    # ==========================================

    current_balance = get_current_balance()


    # ==========================================
    # SET STARTING BALANCE
    # ==========================================

    st.subheader("💰 Set Starting Balance")

    starting_balance = st.number_input(
        "Enter your initial balance",
        min_value=0.0,
        value=float(current_balance),
        step=100.0
    )

    if st.button("Set Balance"):

        set_current_balance(starting_balance)

        st.success(
            f"Balance set to ₹{starting_balance:,.2f}"
        )

        st.rerun()


    # ==========================================
    # AVAILABLE BALANCE
    # ==========================================

    current_balance = get_current_balance()

    st.subheader("💳 Current Balance")

    st.metric(
        "Available Balance",
        f"₹{current_balance:,.2f}"
    )


    # ==========================================
    # TRANSACTION TYPE
    # ==========================================

    st.subheader("➕ Add Transaction")

    transaction_type = st.radio(
        "Transaction Type",
        ["Spend", "Earn"],
        horizontal=True
    )


    # ==========================================
    # DESCRIPTION
    # ==========================================

    description = st.text_input(
        "Description",
        placeholder="Example: Swiggy"
    )


    # ==========================================
    # AMOUNT
    # ==========================================

    amount = st.number_input(
        "Amount",
        min_value=0.0,
        step=100.0
    )


    # ==========================================
    # ADD TRANSACTION
    # ==========================================

    if st.button("Add Transaction"):

        # --------------------------------------
        # Validate description
        # --------------------------------------

        if not description.strip():

            st.warning(
                "Please enter a description."
            )


        # --------------------------------------
        # Validate amount
        # --------------------------------------

        elif amount <= 0:

            st.warning(
                "Please enter a valid amount."
            )


        # --------------------------------------
        # Check insufficient balance
        # --------------------------------------

        elif (
            transaction_type == "Spend"
            and amount > current_balance
        ):

            st.error(
                f"⚠️ Insufficient balance! "
                f"Available balance: "
                f"₹{current_balance:,.2f}"
            )


        # --------------------------------------
        # PROCESS TRANSACTION
        # --------------------------------------

        else:

            # Categorize transaction
            category = categorize_transaction(
                description
            )


            # ----------------------------------
            # Calculate new balance
            # ----------------------------------

            if transaction_type == "Spend":

                new_balance = (
                    current_balance - amount
                )

            else:

                new_balance = (
                    current_balance + amount
                )


            # ----------------------------------
            # Get existing transactions
            # ----------------------------------

            existing_transactions = (
                get_transactions()
            )


            # ----------------------------------
            # Generate transaction ID
            # ----------------------------------

            transaction_number = (
                len(existing_transactions) + 1
            )

            transaction_id = (
                f"T{transaction_number:03d}"
            )


            # ----------------------------------
            # Save transaction to database
            # ----------------------------------

            add_transaction(
                transaction_id,
                str(date.today()),
                description,
                transaction_type,
                amount,
                new_balance,
                category
            )


            # ----------------------------------
            # Update current balance
            # ----------------------------------

            set_current_balance(
                new_balance
            )


            st.success(
                f"✅ {transaction_type} of "
                f"₹{amount:,.2f} added successfully!"
            )


            # Refresh application
            st.rerun()


# ============================================================
# CSV UPLOAD
# ============================================================

elif option == "📂 Upload CSV":

    st.subheader("📂 Upload Transactions")

    st.write(
        "Upload your transaction CSV file."
    )


    # ==========================================
    # FILE UPLOADER
    # ==========================================

    uploaded_file = st.file_uploader(
        "Upload a CSV file",
        type=["csv"]
    )


    if uploaded_file is not None:

        try:

            # ----------------------------------
            # Read uploaded CSV
            # ----------------------------------

            uploaded_df = pd.read_csv(
                uploaded_file
            )


            st.write("Uploaded data:")

            st.dataframe(
                uploaded_df,
                width="stretch"
            )


            # ----------------------------------
            # Required columns
            # ----------------------------------

            required_columns = [
                "transaction_id",
                "date",
                "description",
                "transaction_type",
                "amount",
                "balance"
            ]


            # ----------------------------------
            # Check missing columns
            # ----------------------------------

            missing_columns = [
                column
                for column in required_columns
                if column not in uploaded_df.columns
            ]


            if missing_columns:

                st.error(
                    f"❌ Missing columns: "
                    f"{', '.join(missing_columns)}"
                )


            elif uploaded_df.empty:

                st.warning(
                    "The uploaded CSV is empty."
                )


            else:

                # ----------------------------------
                # IMPORT CSV
                # ----------------------------------

                if st.button(
                    "Import CSV Transactions"
                ):

                    try:

                        for _, row in uploaded_df.iterrows():

                            # --------------------------
                            # Categorize transaction
                            # --------------------------

                            category = (
                                categorize_transaction(
                                    str(row["description"])
                                )
                            )


                            # --------------------------
                            # Add transaction
                            # --------------------------

                            add_transaction(
                                str(row["transaction_id"]),
                                str(row["date"]),
                                str(row["description"]),
                                str(row["transaction_type"]),
                                float(row["amount"]),
                                float(row["balance"]),
                                category
                            )


                        # ----------------------------------
                        # Update current balance
                        # ----------------------------------

                        latest_balance = float(
                            uploaded_df.iloc[-1]["balance"]
                        )

                        set_current_balance(
                            latest_balance
                        )


                        st.success(
                            "✅ CSV transactions "
                            "imported successfully!"
                        )


                        # Refresh application
                        st.rerun()


                    except Exception as e:

                        st.error(
                            f"❌ Error importing CSV: {e}"
                        )


        except Exception as e:

            st.error(
                f"❌ Error reading CSV: {e}"
            )


# ============================================================
# TRANSACTION TABLE
# ============================================================

st.subheader("📋 Transactions")

df = get_transactions()


if df.empty:

    st.info(
        "No transactions yet. "
        "Add a transaction or upload a CSV file."
    )

else:

    st.dataframe(
        df,
        width="stretch"
    )


# ============================================================
# THIS MONTH'S SUMMARY
# ============================================================

st.subheader("📊 This Month's Summary")


# Default values
monthly_earn = 0.0
monthly_spend = 0.0


if not df.empty:

    # Make a copy
    monthly_df = df.copy()

    # ------------------------------------------
    # Convert date column
    # ------------------------------------------

    monthly_df["date"] = pd.to_datetime(
        monthly_df["date"],
        errors="coerce"
    )

    # If some dates were not parsed,
    # try DD-MM-YYYY format
    missing_dates = monthly_df["date"].isna()

    if missing_dates.any():

        monthly_df.loc[missing_dates, "date"] = (
            pd.to_datetime(
                df.loc[missing_dates, "date"],
                format="%d-%m-%Y",
                errors="coerce"
            )
        )


    # ------------------------------------------
    # Current month and year
    # ------------------------------------------

    today = date.today()

    current_month = today.month
    current_year = today.year


    # ------------------------------------------
    # Filter current month
    # ------------------------------------------

    monthly_df = monthly_df[
        (monthly_df["date"].dt.month == current_month)
        &
        (monthly_df["date"].dt.year == current_year)
    ]


    # ------------------------------------------
    # Make transaction type consistent
    # ------------------------------------------

    monthly_df["transaction_type"] = (
        monthly_df["transaction_type"]
        .astype(str)
        .str.strip()
        .str.lower()
    )


    # ------------------------------------------
    # Convert amount to numeric
    # ------------------------------------------

    monthly_df["amount"] = pd.to_numeric(
        monthly_df["amount"],
        errors="coerce"
    )


    # ------------------------------------------
    # THIS MONTH EARN
    # ------------------------------------------

    monthly_earn = monthly_df.loc[
        monthly_df["transaction_type"] == "earn",
        "amount"
    ].sum()


    # ------------------------------------------
    # THIS MONTH SPEND
    # ------------------------------------------

    monthly_spend = monthly_df.loc[
        monthly_df["transaction_type"] == "spend",
        "amount"
    ].sum()


# ============================================================
# DISPLAY MONTHLY SUMMARY
# ============================================================

col1, col2 = st.columns(2)


with col1:

    st.metric(
        "This Month Earn",
        f"₹{monthly_earn:,.2f}"
    )


with col2:

    st.metric(
        "This Month Spend",
        f"₹{monthly_spend:,.2f}"
    )