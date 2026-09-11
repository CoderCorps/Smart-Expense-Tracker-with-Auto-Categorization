"""
app/services/analytics/aggregations.py

Aggregation functions for the analytics dashboard.

All functions receive a list of Transaction model objects (already filtered
by the current user) and return plain Python structures matching the
Pydantic schemas.
"""

import re
from typing import Any, Dict, List, Optional

import pandas as pd
from dateutil.relativedelta import relativedelta

from backend.app.models.transaction import Transaction, TransactionType

_MONTH_PATTERN = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


class InvalidMonth(ValueError):
    """Raised for a month string that isn't YYYY-MM."""


def _validate_month(month: str) -> str:
    """
    Reject a malformed month before it reaches pandas.

    Without this, "2026-13" or "august" surfaces as a 500 from deep
    inside to_datetime instead of a 422 naming the bad parameter.
    """

    if not isinstance(month, str) or not _MONTH_PATTERN.match(month):
        raise InvalidMonth(f"Expected a month as YYYY-MM, got {month!r}")

    return month


def _transactions_to_df(transactions: List[Transaction]) -> pd.DataFrame:
    """
    Convert a list of Transaction objects into a pandas DataFrame
    with columns: date, amount, type, category_name.
    """
    if not transactions:
        return pd.DataFrame(columns=["date", "amount", "type", "category_name"])

    data = []
    for t in transactions:
        cat_name = t.category.name if t.category else "Others"
        data.append({
            "date": t.date,
            "amount": t.amount,
            "type": t.type.value if hasattr(t.type, "value") else str(t.type),
            "category_name": cat_name,
        })
    df = pd.DataFrame(data)
    df["date"] = pd.to_datetime(df["date"])
    return df


def _filter_month(df: pd.DataFrame, month_str: str) -> pd.DataFrame:
    """Filter DataFrame to rows whose date falls in the given month YYYY-MM."""
    start = pd.to_datetime(f"{_validate_month(month_str)}-01")
    next_month = start + pd.offsets.MonthBegin(1)
    return df[(df["date"] >= start) & (df["date"] < next_month)]


def _month_year_from_date(dt: pd.Timestamp) -> str:
    """Return 'YYYY-MM' from a datetime."""
    return dt.strftime("%Y-%m")


def _add_months(dt: pd.Timestamp, months: int) -> pd.Timestamp:
    """Add/subtract months using relativedelta."""
    # dt is a pandas Timestamp; convert to datetime for relativedelta
    dt_dt = dt.to_pydatetime()
    new_dt = dt_dt + relativedelta(months=months)
    return pd.Timestamp(new_dt)


def _to_python_float(value) -> float:
    """Convert numpy or other numeric types to Python float."""
    if hasattr(value, "item"):
        return float(value.item())
    return float(value)


# ---------- Function 1: Monthly Summary ----------

def get_monthly_summary(transactions: List[Transaction], month: str) -> Dict[str, Any]:
    """
    Compute total earned, spent, and balance for a specific month.

    Args:
        transactions: List of Transaction objects.
        month: String in "YYYY-MM" format.

    Returns:
        dict: {
            "total_earned": float,
            "total_spent": float,
            "balance": float,
            "month": str
        }
    """
    _validate_month(month)

    df = _transactions_to_df(transactions)
    if df.empty:
        return {
            "total_earned": 0.0,
            "total_spent": 0.0,
            "balance": 0.0,
            "month": month,
        }

    df_month = _filter_month(df, month)
    if df_month.empty:
        return {
            "total_earned": 0.0,
            "total_spent": 0.0,
            "balance": 0.0,
            "month": month,
        }

    grouped = df_month.groupby("type")["amount"].sum().to_dict()
    total_earned = grouped.get(TransactionType.EARN.value, 0.0)
    total_spent = grouped.get(TransactionType.SPEND.value, 0.0)

    return {
        "total_earned": _to_python_float(total_earned),
        "total_spent": _to_python_float(total_spent),
        "balance": _to_python_float(total_earned - total_spent),
        "month": month,
    }


# ---------- Function 2: Category Breakdown ----------

def get_category_breakdown(transactions: List[Transaction], month: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Compute spending breakdown by category (only SPEND transactions).

    Args:
        transactions: List of Transaction objects.
        month: Optional "YYYY-MM" to filter to a specific month.

    Returns:
        list of dict: [
            {
                "category_name": str,
                "total_amount": float,
                "percentage": float
            }
        ]
    """
    df = _transactions_to_df(transactions)
    if df.empty:
        return []

    df_spend = df[df["type"] == TransactionType.SPEND.value]
    if df_spend.empty:
        return []

    if month:
        df_spend = _filter_month(df_spend, month)
        if df_spend.empty:
            return []

    grouped = df_spend.groupby("category_name")["amount"].sum()
    total_spend = grouped.sum()
    if total_spend == 0:
        return []

    result = []
    for cat, amount in grouped.items():
        pct = (amount / total_spend) * 100
        result.append({
            "category_name": cat,
            "total_amount": _to_python_float(amount),
            "percentage": _to_python_float(pct)
        })

    result.sort(key=lambda x: x["total_amount"], reverse=True)
    return result


# ---------- Function 3: Trend ----------

def get_trend(transactions: List[Transaction], granularity: str = "monthly") -> List[Dict[str, Any]]:
    """
    Compute total earned/spent over time.

    Args:
        transactions: List of Transaction objects.
        granularity: "monthly" or "daily".

    Returns:
        list of dict: [
            {
                "period": str,
                "total_spent": float,
                "total_earned": float
            }
        ]
    """
    df = _transactions_to_df(transactions)
    if df.empty:
        return []

    df_trend = df.copy()
    if granularity == "monthly":
        df_trend["period"] = df_trend["date"].dt.to_period("M").astype(str)
    elif granularity == "daily":
        df_trend["period"] = df_trend["date"].dt.strftime("%Y-%m-%d")
    else:
        raise ValueError("granularity must be 'monthly' or 'daily'")

    grouped = df_trend.groupby(["period", "type"])["amount"].sum().reset_index()
    pivot = grouped.pivot(index="period", columns="type", values="amount").fillna(0)
    earn_col = TransactionType.EARN.value
    spend_col = TransactionType.SPEND.value
    if earn_col not in pivot.columns:
        pivot[earn_col] = 0.0
    if spend_col not in pivot.columns:
        pivot[spend_col] = 0.0

    result = []
    for period, row in pivot.iterrows():
        result.append({
            "period": period,
            "total_spent": _to_python_float(row[spend_col]),
            "total_earned": _to_python_float(row[earn_col]),
        })

    result.sort(key=lambda x: x["period"])
    return result


# ---------- Function 4: Spike Detection ----------

def detect_spikes(transactions: List[Transaction], threshold_multiplier: float = 1.5) -> List[Dict[str, Any]]:
    """
    Detect categories where current month spending is above historical average.

    Args:
        transactions: List of Transaction objects.
        threshold_multiplier: Factor above average to trigger a spike (default 1.5).

    Returns:
        list of dict: [
            {
                "category_name": str,
                "message": str,
                "current_amount": float,
                "average_amount": float,
                "severity": str
            }
        ]
    """
    df = _transactions_to_df(transactions)
    if df.empty:
        return []

    df_spend = df[df["type"] == TransactionType.SPEND.value].copy()
    if df_spend.empty:
        return []

    # Determine current month
    max_date = df_spend["date"].max()
    current_month_start = max_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    current_month_str = _month_year_from_date(current_month_start)

    # Previous 3 calendar months
    prev_months = [
        _month_year_from_date(_add_months(current_month_start, -i))
        for i in range(1, 4)
    ]

    # Build monthly spending per category
    df_spend["month"] = df_spend["date"].dt.to_period("M").astype(str)
    monthly = df_spend.groupby(["month", "category_name"])["amount"].sum().reset_index()
    pivot = monthly.pivot(index="month", columns="category_name", values="amount").fillna(0)

    # Ensure all required months exist (fill missing with zeros)
    all_months = set(pivot.index)
    required_months = set(prev_months + [current_month_str])
    missing = required_months - all_months
    for m in missing:
        pivot.loc[m] = 0
    pivot = pivot.sort_index()

    # A month with no spending in a category counts as a zero, not as a
    # gap — otherwise a category bought in one month out of three looks
    # like it has a high "average" built from a single data point. A
    # category with no history at all averages zero and is skipped below,
    # since a first-ever purchase isn't a spike.

    if current_month_str not in pivot.index:
        return []  # no current month? shouldn't happen

    current_row = pivot.loc[current_month_str]

    # Previous rows (if some months are missing, we filled them with zeros)
    prev_rows = pivot.loc[prev_months]
    avg_prev = prev_rows.mean()  # Series: category -> mean over 3 months

    alerts = []
    for category in current_row.index:
        current_amount = current_row[category]
        avg_amount = avg_prev.get(category, 0.0)

        # Skip if no historical spending (avoids false positives)
        if avg_amount == 0.0:
            continue

        if current_amount > avg_amount * threshold_multiplier:
            pct_increase = ((current_amount - avg_amount) / avg_amount) * 100
            message = (f"{category} spending is {pct_increase:.0f}% higher "
                       f"than its previous 3-month average.")
            alerts.append({
                "category_name": category,
                "message": message,
                "current_amount": _to_python_float(current_amount),
                "average_amount": _to_python_float(avg_amount),
                "severity": "warning"
            })

    alerts.sort(key=lambda x: x["current_amount"], reverse=True)
    return alerts
