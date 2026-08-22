import streamlit as st
import pandas as pd

from src.csv_parser import read_csv
from src.insights import generate_insights

from src.pdf_parser import (
    extract_text_from_pdf,
    parse_transactions_from_pdf
)

from src.classifier import classify_transaction

from src.database import (
    create_table,
    insert_expenses,
    get_expenses,
    clear_expenses
)


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Smart Expense Tracker",
    page_icon="💰",
    layout="wide"
)


# ============================================================
# INITIALIZE DATABASE
# ============================================================

create_table()


# ============================================================
# CUSTOM CSS
# ============================================================

st.markdown(
    """
    <style>

    .main-title {
        font-size: 38px;
        font-weight: 700;
        margin-bottom: 0px;
    }

    .subtitle {
        color: #666666;
        font-size: 16px;
        margin-bottom: 25px;
    }

    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# HEADER
# ============================================================

st.markdown(
    '<div class="main-title">💰 Smart Expense Tracker</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">'
    'Upload your transactions, automatically categorize them, '
    'and analyze your finances.'
    '</div>',
    unsafe_allow_html=True
)


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.title("📌 Navigation")

page = st.sidebar.radio(
    "Go to",
    [
        "📊 Dashboard",
        "📂 Upload Transactions",
        "📋 Transactions"
    ]
)


# ============================================================
# LOAD STORED DATA
# ============================================================

stored_df = get_expenses()


# ============================================================
# DASHBOARD
# ============================================================

if page == "📊 Dashboard":

    st.header("📊 Financial Dashboard")

    # --------------------------------------------------------
    # NO DATA
    # --------------------------------------------------------

    if stored_df.empty:

        st.info(
            "No transactions found in the database."
        )

        st.write(
            "Go to **📂 Upload Transactions** and upload "
            "a CSV or PDF bank statement."
        )

        st.stop()


    # --------------------------------------------------------
    # DATA PREPARATION
    # --------------------------------------------------------

    stored_df["amount"] = pd.to_numeric(
        stored_df["amount"],
        errors="coerce"
    )

    stored_df["date"] = pd.to_datetime(
        stored_df["date"],
        errors="coerce"
    )


    # --------------------------------------------------------
    # FINANCIAL CALCULATIONS
    # --------------------------------------------------------

    total_income = stored_df.loc[
        stored_df["type"] == "Income",
        "amount"
    ].sum()


    total_expenses = stored_df.loc[
        stored_df["type"] == "Expense",
        "amount"
    ].sum()


    balance = (
        total_income -
        total_expenses
    )


    total_transactions = len(
        stored_df
    )


    # --------------------------------------------------------
    # KPI CARDS
    # --------------------------------------------------------

    col1, col2, col3, col4 = st.columns(4)


    with col1:

        st.metric(
            label="💵 Total Income",
            value=f"₹{total_income:,.2f}"
        )


    with col2:

        st.metric(
            label="💸 Total Expenses",
            value=f"₹{total_expenses:,.2f}"
        )


    with col3:

        st.metric(
            label="💰 Balance",
            value=f"₹{balance:,.2f}"
        )


    with col4:

        st.metric(
            label="🧾 Transactions",
            value=total_transactions
        )


    st.divider()


    # ========================================================
    # EXPENSE CATEGORY ANALYSIS
    # ========================================================

    col1, col2 = st.columns(2)


    # --------------------------------------------------------
    # CATEGORY SPENDING
    # --------------------------------------------------------

    with col1:

        st.subheader(
            "💳 Spending by Category"
        )

        expense_df = stored_df[
            stored_df["type"] == "Expense"
        ]

        if not expense_df.empty:

            category_summary = (
                expense_df
                .groupby("category")["amount"]
                .sum()
                .sort_values(
                    ascending=False
                )
            )

            st.bar_chart(
                category_summary
            )

        else:

            st.info(
                "No expense data available."
            )


    # --------------------------------------------------------
    # INCOME VS EXPENSE
    # --------------------------------------------------------

    with col2:

        st.subheader(
            "📈 Income vs Expense"
        )

        income_expense = pd.DataFrame(
            {
                "Amount": [
                    total_income,
                    total_expenses
                ]
            },
            index=[
                "Income",
                "Expense"
            ]
        )

        st.bar_chart(
            income_expense
        )


    st.divider()


    # ========================================================
    # TOP EXPENSE CATEGORIES
    # ========================================================

    st.subheader(
        "🏆 Top Spending Categories"
    )

    if not expense_df.empty:

        category_summary = (
            expense_df
            .groupby("category")["amount"]
            .sum()
            .sort_values(
                ascending=False
            )
        )

        total_expense_amount = (
            category_summary.sum()
        )


        for category, amount in category_summary.items():

            percentage = (
                amount /
                total_expense_amount *
                100
            )

            st.write(
                f"**{category}** — "
                f"₹{amount:,.2f} "
                f"({percentage:.1f}%)"
            )


    st.divider()


    # ========================================================
    # RECENT TRANSACTIONS
    # ========================================================

    st.subheader(
        "🕒 Recent Transactions"
    )


    recent_df = (
        stored_df
        .sort_values(
            "date",
            ascending=False
        )
        .head(10)
        .copy()
    )


    recent_df["date"] = (
        recent_df["date"]
        .dt.strftime("%Y-%m-%d")
    )


    st.dataframe(
        recent_df[
            [
                "date",
                "description",
                "amount",
                "type",
                "category"
            ]
        ],
        use_container_width=True,
        hide_index=True
    )

    # ========================================================
    # MONTHLY FINANCIAL ANALYSIS
    # ========================================================

    st.divider()

    st.subheader(
        "📅 Monthly Financial Analysis"
    )

    monthly_df = stored_df.copy()

    monthly_df["date"] = pd.to_datetime(
        monthly_df["date"],
        errors="coerce"
    )

    monthly_df["month"] = (
        monthly_df["date"]
        .dt.to_period("M")
        .astype(str)
    )


    # ========================================================
    # FINANCIAL INSIGHTS
    # ========================================================

    st.divider()

    st.subheader(
        "🤖 Financial Insights"
    )

    insights = generate_insights(
        stored_df
    )

    if insights:

        for insight in insights:

            st.info(
                insight
            )

    else:

        st.info(
            "Not enough transaction data "
            "to generate financial insights."
        )


    # ========================================================
    # MONTHLY INCOME
    # ========================================================

    monthly_income = (
        monthly_df[
            monthly_df["type"] == "Income"
        ]
        .groupby("month")["amount"]
        .sum()
    )


    # ========================================================
    # MONTHLY EXPENSE
    # ========================================================

    monthly_expenses = (
        monthly_df[
            monthly_df["type"] == "Expense"
        ]
        .groupby("month")["amount"]
        .sum()
    )


    # ========================================================
    # COMBINE
    # ========================================================

    monthly_analysis = pd.DataFrame(
        {
            "Income": monthly_income,
            "Expenses": monthly_expenses
        }
    ).fillna(0)


    monthly_analysis["Savings"] = (
        monthly_analysis["Income"]
        - monthly_analysis["Expenses"]
    )


    # ========================================================
    # DISPLAY TABLE
    # ========================================================

    st.dataframe(
        monthly_analysis,
        use_container_width=True
    )


    # ========================================================
    # MONTHLY TREND CHART
    # ========================================================

    st.subheader(
        "📈 Income vs Expenses Over Time"
    )

    st.line_chart(
        monthly_analysis[
            [
                "Income",
                "Expenses"
            ]
        ]
    )


    # ========================================================
    # SAVINGS TREND
    # ========================================================

    st.subheader(
        "💰 Monthly Savings"
    )

    st.bar_chart(
        monthly_analysis[
            ["Savings"]
        ]
    )


    # ========================================================
    # BEST / WORST MONTH
    # ========================================================

    if not monthly_analysis.empty:

        highest_saving_month = (
            monthly_analysis[
                "Savings"
            ].idxmax()
        )

        highest_saving_amount = (
            monthly_analysis.loc[
                highest_saving_month,
                "Savings"
            ]
        )


        highest_expense_month = (
            monthly_analysis[
                "Expenses"
            ].idxmax()
        )

        highest_expense_amount = (
            monthly_analysis.loc[
                highest_expense_month,
                "Expenses"
            ]
        )


        col1, col2 = st.columns(2)


        with col1:

            st.metric(
                "🏆 Best Saving Month",
                highest_saving_month,
                f"₹{highest_saving_amount:,.2f}"
            )


        with col2:

            st.metric(
                "⚠️ Highest Spending Month",
                highest_expense_month,
                f"₹{highest_expense_amount:,.2f}"
            )


# ============================================================
# UPLOAD TRANSACTIONS
# ============================================================

elif page == "📂 Upload Transactions":

    st.header(
        "📂 Upload Transaction Data"
    )

    st.write(
        "Upload a CSV or PDF bank statement."
    )


    uploaded_file = st.file_uploader(
        "Choose a CSV or PDF file",
        type=[
            "csv",
            "pdf"
        ]
    )


    if uploaded_file is not None:

        file_name = uploaded_file.name.lower()


        try:

            # =================================================
            # CSV
            # =================================================

            if file_name.endswith(".csv"):

                st.info(
                    "📄 Processing CSV..."
                )

                df = read_csv(
                    uploaded_file
                )


            # =================================================
            # PDF
            # =================================================

            elif file_name.endswith(".pdf"):

                st.info(
                    "📄 Processing PDF..."
                )

                text = extract_text_from_pdf(
                    uploaded_file
                )

                df = parse_transactions_from_pdf(
                    text
                )


                if df.empty:

                    st.warning(
                        "No transactions could be detected "
                        "from this PDF."
                    )

                    st.stop()


            else:

                st.error(
                    "Unsupported file type."
                )

                st.stop()


            # =================================================
            # CHECK DATA
            # =================================================

            if df.empty:

                st.warning(
                    "No transactions found."
                )

                st.stop()


            # =================================================
            # CLASSIFICATION
            # =================================================

            classification = (
                df["description"]
                .apply(
                    classify_transaction
                )
            )


            df["type"] = classification.apply(
                lambda x: x[0]
            )


            df["category"] = classification.apply(
                lambda x: x[1]
            )


            # =================================================
            # COLUMN ORDER
            # =================================================

            df = df[
                [
                    "date",
                    "amount",
                    "type",
                    "description",
                    "category"
                ]
            ]


            # =================================================
            # SHOW RESULT
            # =================================================

            st.success(
                f"Successfully processed "
                f"{len(df)} transactions."
            )


            st.subheader(
                "📋 Processed Transactions"
            )


            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True
            )


            # =================================================
            # SAVE
            # =================================================

            st.subheader(
                "💾 Save to Database"
            )


            if st.button(
                "Save Transactions"
            ):

                inserted_count, duplicate_count = (
                    insert_expenses(df)
                )


                if inserted_count > 0:

                    st.success(
                        f"✅ {inserted_count} new "
                        "transactions saved."
                    )


                if duplicate_count > 0:

                    st.warning(
                        f"⚠️ {duplicate_count} duplicate "
                        "transactions skipped."
                    )


                if (
                    inserted_count == 0
                    and duplicate_count > 0
                ):

                    st.info(
                        "All transactions already "
                        "exist in the database."
                    )


        except Exception as e:

            st.error(
                f"Error processing file: {str(e)}"
            )


# ============================================================
# TRANSACTIONS PAGE
# ============================================================

elif page == "📋 Transactions":

    st.header(
        "📋 All Stored Transactions"
    )


    stored_df = get_expenses()


    if stored_df.empty:

        st.info(
            "No transactions stored yet."
        )

        st.stop()


    # --------------------------------------------------------
    # SEARCH
    # --------------------------------------------------------

    search = st.text_input(
        "🔎 Search transactions",
        placeholder="Search by description or category..."
    )


    filtered_df = stored_df.copy()


    if search:

        search_lower = search.lower()

        filtered_df = filtered_df[
            filtered_df[
                "description"
            ]
            .astype(str)
            .str.lower()
            .str.contains(
                search_lower,
                na=False
            )
            |
            filtered_df[
                "category"
            ]
            .astype(str)
            .str.lower()
            .str.contains(
                search_lower,
                na=False
            )
        ]


    # --------------------------------------------------------
    # TYPE FILTER
    # --------------------------------------------------------

    transaction_type = st.selectbox(
        "Transaction Type",
        [
            "All",
            "Income",
            "Expense"
        ]
    )


    if transaction_type != "All":

        filtered_df = filtered_df[
            filtered_df["type"]
            == transaction_type
        ]


    # --------------------------------------------------------
    # DISPLAY
    # --------------------------------------------------------

    st.dataframe(
        filtered_df,
        use_container_width=True,
        hide_index=True
    )


    st.write(
        f"Showing {len(filtered_df)} "
        "transactions."
    )


    # --------------------------------------------------------
    # DOWNLOAD
    # --------------------------------------------------------

    csv_data = filtered_df.to_csv(
        index=False
    ).encode("utf-8")


    st.download_button(
        label="⬇️ Download Transactions",
        data=csv_data,
        file_name="transactions.csv",
        mime="text/csv"
    )


    st.divider()


    # ========================================================
    # DATABASE MANAGEMENT
    # ========================================================

    st.subheader(
        "⚠️ Database Management"
    )


    if st.button(
        "🗑️ Clear All Transactions"
    ):

        clear_expenses()

        st.success(
            "All transactions have been deleted."
        )

        st.rerun()