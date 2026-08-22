import pandas as pd


# ============================================================
# FINANCIAL INSIGHTS ENGINE
# ============================================================

def generate_insights(df):
    """
    Generate rule-based financial insights
    from transaction data.
    """

    insights = []

    if df.empty:
        return insights

    data = df.copy()

    # --------------------------------------------------------
    # Clean data
    # --------------------------------------------------------

    data["amount"] = pd.to_numeric(
        data["amount"],
        errors="coerce"
    )

    data["date"] = pd.to_datetime(
        data["date"],
        errors="coerce"
    )

    data = data.dropna(
        subset=["amount", "date"]
    )

    if data.empty:
        return insights

    # ========================================================
    # TOTAL INCOME / EXPENSE
    # ========================================================

    income = data[
        data["type"] == "Income"
    ]

    expenses = data[
        data["type"] == "Expense"
    ]

    total_income = income["amount"].sum()

    total_expenses = expenses["amount"].sum()


    # ========================================================
    # SAVINGS RATE
    # ========================================================

    if total_income > 0:

        savings = (
            total_income -
            total_expenses
        )

        savings_rate = (
            savings /
            total_income
        ) * 100

        if savings_rate >= 50:

            insights.append(
                f"💰 Excellent savings rate: "
                f"{savings_rate:.1f}% of your income "
                f"is being saved."
            )

        elif savings_rate >= 20:

            insights.append(
                f"👍 Your savings rate is "
                f"{savings_rate:.1f}%, which is a "
                f"healthy level."
            )

        elif savings_rate >= 0:

            insights.append(
                f"⚠️ Your savings rate is only "
                f"{savings_rate:.1f}%. Consider "
                f"reducing unnecessary expenses."
            )

        else:

            insights.append(
                "🚨 Your expenses are higher "
                "than your income."
            )


    # ========================================================
    # HIGHEST SPENDING CATEGORY
    # ========================================================

    if not expenses.empty:

        category_summary = (
            expenses
            .groupby("category")["amount"]
            .sum()
            .sort_values(
                ascending=False
            )
        )

        if not category_summary.empty:

            top_category = (
                category_summary.index[0]
            )

            top_category_amount = (
                category_summary.iloc[0]
            )

            if total_expenses > 0:

                category_percentage = (
                    top_category_amount /
                    total_expenses
                ) * 100

                insights.append(
                    f"💡 Your highest spending "
                    f"category is {top_category}, "
                    f"accounting for "
                    f"{category_percentage:.1f}% "
                    f"of your total expenses "
                    f"(₹{top_category_amount:,.2f})."
                )


    # ========================================================
    # LARGE TRANSACTION DETECTION
    # ========================================================

    if not expenses.empty:

        average_expense = (
            expenses["amount"].mean()
        )

        large_transactions = expenses[
            expenses["amount"]
            >= average_expense * 3
        ]

        if not large_transactions.empty:

            largest = (
                large_transactions
                .sort_values(
                    "amount",
                    ascending=False
                )
                .iloc[0]
            )

            insights.append(
                f"🔔 Large transaction detected: "
                f"₹{largest['amount']:,.2f} "
                f"for {largest['description']}."
            )


    # ========================================================
    # MONTHLY EXPENSE COMPARISON
    # ========================================================

    data["month"] = (
        data["date"]
        .dt.to_period("M")
    )

    monthly_expenses = (
        expenses.assign(
            month=expenses["date"]
            .dt.to_period("M")
        )
        .groupby("month")["amount"]
        .sum()
        .sort_index()
    )

    if len(monthly_expenses) >= 2:

        current_month = (
            monthly_expenses.iloc[-1]
        )

        previous_month = (
            monthly_expenses.iloc[-2]
        )

        if previous_month > 0:

            change = (
                (
                    current_month -
                    previous_month
                )
                /
                previous_month
            ) * 100

            if change > 10:

                insights.append(
                    f"📈 Your expenses increased "
                    f"by {change:.1f}% compared with "
                    f"the previous month."
                )

            elif change < -10:

                insights.append(
                    f"🎉 Your expenses decreased "
                    f"by {abs(change):.1f}% compared "
                    f"with the previous month."
                )

            else:

                insights.append(
                    f"📊 Your monthly expenses are "
                    f"relatively stable "
                    f"({change:+.1f}% change)."
                )


    # ========================================================
    # HIGHEST SPENDING MONTH
    # ========================================================

    if not monthly_expenses.empty:

        highest_month = (
            monthly_expenses.idxmax()
        )

        highest_month_amount = (
            monthly_expenses.max()
        )

        insights.append(
            f"📅 Your highest spending month "
            f"was {highest_month} with "
            f"₹{highest_month_amount:,.2f} "
            f"in expenses."
        )


    return insights