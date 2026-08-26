"""
PERSON C OWNS THIS FILE.

All the pandas aggregation logic behind the dashboard endpoints lives here,
kept separate from the endpoint functions themselves (app/api/v1/endpoints/
dashboard.py just calls these and returns the result — it shouldn't contain
any pandas logic itself).

Each function below takes a list of Transaction model instances (already
fetched from the DB for the current user) and returns plain data the
endpoint can drop straight into its response schema. Keeping DB fetching
out of these functions makes them easy to unit test with fake data.
"""

from backend.app.models.transaction import Transaction


def get_monthly_summary(transactions: list[Transaction], month: str) -> dict:
    """
    TODO: filter `transactions` to the given month ("2026-08"), sum up
    amounts where type == EARN vs type == SPEND, return:
    {"total_earned": ..., "total_spent": ..., "balance": ..., "month": month}

    Suggested approach: convert to a pandas DataFrame first (pd.DataFrame
    of the fields you need), it'll make the groupby/sum logic much less
    painful than looping in plain Python.
    """
    raise NotImplementedError


def get_category_breakdown(transactions: list[Transaction], month: str | None = None) -> list[dict]:
    """
    TODO: group SPEND transactions by category, sum amounts, compute each
    category's percentage of total spend. Return a list of dicts matching
    CategoryBreakdownItem in app/schemas/dashboard.py. Optionally filter to
    a single month first if `month` is provided.
    """
    raise NotImplementedError


def get_trend(transactions: list[Transaction], granularity: str = "monthly") -> list[dict]:
    """
    TODO: group by month (or day, if granularity == "daily"), sum spend and
    earn per period, return a list matching TrendPoint in
    app/schemas/dashboard.py, sorted chronologically. This powers the line
    chart on the dashboard.
    """
    raise NotImplementedError


def detect_spikes(transactions: list[Transaction], threshold_multiplier: float = 1.5) -> list[dict]:
    """
    TODO: for each category, compare the current month's spend against the
    average of the previous 3 months. If current > average * threshold_multiplier,
    that's a spike — return it as an InsightAlert-shaped dict (see
    app/schemas/dashboard.py).

    Keep this simple — a rolling average comparison is genuinely enough here.
    This does NOT need to be a machine learning model; a basic statistical
    threshold is the right tool for this job and is much easier to explain
    and debug than an ML anomaly detector would be.
    """
    raise NotImplementedError
