"""
Tests for services/analytics/aggregations.py and the /dashboard endpoints.

The aggregation functions take plain Transaction objects, so most of this
needs no database — unsaved model instances with a stub category are
enough, and keeping them in memory makes the arithmetic easy to read.
"""

from datetime import date

import pytest

from backend.app.models.transaction import Transaction, TransactionType
from backend.app.services.analytics.aggregations import (
    InvalidMonth,
    detect_spikes,
    get_category_breakdown,
    get_monthly_summary,
    get_trend,
)


class _StubCategory:
    """Stands in for a Category row; aggregations only read `.name`."""

    def __init__(self, name: str):
        self.name = name


def txn(
    day: date,
    amount: float,
    category: str,
    kind: TransactionType = TransactionType.SPEND,
) -> Transaction:
    return Transaction(
        date=day,
        amount=amount,
        type=kind,
        category=_StubCategory(category),
        description=category,
    )


@pytest.fixture
def four_months() -> list[Transaction]:
    """
    Food and Shopping steady for three months, then August spikes Food
    (110 avg -> 300) while Shopping stays flat. Plus one salary.
    """
    return [
        txn(date(2026, 5, 10), 100.0, "Food & Dining"),
        txn(date(2026, 5, 15), 200.0, "Shopping"),
        txn(date(2026, 6, 5), 120.0, "Food & Dining"),
        txn(date(2026, 6, 20), 220.0, "Shopping"),
        txn(date(2026, 7, 8), 110.0, "Food & Dining"),
        txn(date(2026, 7, 25), 210.0, "Shopping"),
        txn(date(2026, 8, 2), 300.0, "Food & Dining"),
        txn(date(2026, 8, 15), 230.0, "Shopping"),
        txn(date(2026, 8, 20), 5000.0, "Salary & Income", TransactionType.EARN),
    ]


# =========================================================
# Monthly summary
# =========================================================

class TestMonthlySummary:
    def test_totals_and_balance(self, four_months):
        result = get_monthly_summary(four_months, "2026-08")

        assert result["total_earned"] == 5000.0
        assert result["total_spent"] == 530.0
        assert result["balance"] == 4470.0
        assert result["month"] == "2026-08"

    def test_only_counts_the_requested_month(self, four_months):
        assert get_monthly_summary(four_months, "2026-05")["total_spent"] == 300.0

    def test_month_with_no_data_is_zero_not_an_error(self, four_months):
        result = get_monthly_summary(four_months, "2026-01")

        assert result == {
            "total_earned": 0.0,
            "total_spent": 0.0,
            "balance": 0.0,
            "month": "2026-01",
        }

    def test_no_transactions_at_all(self):
        assert get_monthly_summary([], "2026-08")["balance"] == 0.0

    @pytest.mark.parametrize("bad", ["2026-13", "2026-00", "august", "2026", ""])
    def test_malformed_month_raises_invalid_month(self, bad, four_months):
        """
        Callers turn this into a 422. Letting it reach pandas would
        surface as a 500 instead — see endpoints/dashboard.py.
        """
        with pytest.raises(InvalidMonth):
            get_monthly_summary(four_months, bad)


# =========================================================
# Category breakdown
# =========================================================

class TestCategoryBreakdown:
    def test_percentages_sum_to_100(self, four_months):
        result = get_category_breakdown(four_months, "2026-08")

        assert sum(item["percentage"] for item in result) == pytest.approx(100.0)

    def test_sorted_by_amount_descending(self, four_months):
        result = get_category_breakdown(four_months, "2026-08")
        amounts = [item["total_amount"] for item in result]

        assert amounts == sorted(amounts, reverse=True)

    def test_excludes_earnings(self, four_months):
        """A breakdown of spending must not count the salary."""
        result = get_category_breakdown(four_months, "2026-08")
        names = [item["category_name"] for item in result]

        assert "Salary & Income" not in names
        assert sum(item["total_amount"] for item in result) == 530.0

    def test_all_time_when_month_omitted(self, four_months):
        result = get_category_breakdown(four_months)
        by_name = {item["category_name"]: item for item in result}

        assert by_name["Food & Dining"]["total_amount"] == 630.0
        assert by_name["Shopping"]["total_amount"] == 860.0

    def test_empty_input(self):
        assert get_category_breakdown([], "2026-08") == []


# =========================================================
# Trends
# =========================================================

class TestTrend:
    def test_monthly_periods_are_chronological(self, four_months):
        result = get_trend(four_months, "monthly")
        periods = [point["period"] for point in result]

        assert periods == ["2026-05", "2026-06", "2026-07", "2026-08"]

    def test_monthly_splits_spend_from_earn(self, four_months):
        august = next(p for p in get_trend(four_months) if p["period"] == "2026-08")

        assert august["total_spent"] == 530.0
        assert august["total_earned"] == 5000.0

    def test_daily_granularity(self, four_months):
        result = get_trend(four_months, "daily")

        assert result[0]["period"] == "2026-05-10"
        assert all(len(point["period"]) == 10 for point in result)

    def test_period_with_only_spending_reports_zero_earned(self, four_months):
        may = next(p for p in get_trend(four_months) if p["period"] == "2026-05")

        assert may["total_earned"] == 0.0

    def test_unknown_granularity_rejected(self, four_months):
        with pytest.raises(ValueError):
            get_trend(four_months, "hourly")

    def test_empty_input(self):
        assert get_trend([]) == []


# =========================================================
# Spike detection
# =========================================================

class TestDetectSpikes:
    def test_flags_a_category_above_its_average(self, four_months):
        alerts = detect_spikes(four_months)
        by_name = {alert["category_name"]: alert for alert in alerts}

        assert "Food & Dining" in by_name
        assert by_name["Food & Dining"]["current_amount"] == 300.0
        assert by_name["Food & Dining"]["average_amount"] == pytest.approx(110.0)

    def test_does_not_flag_a_steady_category(self, four_months):
        names = [alert["category_name"] for alert in detect_spikes(four_months)]

        assert "Shopping" not in names

    def test_first_ever_purchase_is_not_a_spike(self):
        """
        A category with no history averages zero. Every first purchase
        would clear a multiplier of zero, so these must be skipped or the
        insights list is nothing but noise for a new user.
        """
        transactions = [txn(date(2026, 8, 2), 500.0, "Travel & Transport")]

        assert detect_spikes(transactions) == []

    def test_threshold_is_configurable(self, four_months):
        assert detect_spikes(four_months, threshold_multiplier=5.0) == []

    def test_message_quantifies_the_increase(self, four_months):
        alert = next(
            a for a in detect_spikes(four_months) if a["category_name"] == "Food & Dining"
        )

        assert "%" in alert["message"]
        assert alert["severity"] == "warning"

    def test_empty_input(self):
        assert detect_spikes([]) == []


# =========================================================
# HTTP layer
# =========================================================

class TestDashboardEndpoints:
    def test_summary_requires_auth(self, client):
        assert client.get("/api/v1/dashboard/summary?month=2026-08").status_code == 401

    def test_summary_returns_zeros_for_a_new_user(self, client, auth_headers):
        response = client.get(
            "/api/v1/dashboard/summary", params={"month": "2026-08"}, headers=auth_headers
        )

        assert response.status_code == 200
        assert response.json()["balance"] == 0.0

    def test_malformed_month_is_422_not_500(self, client, auth_headers):
        response = client.get(
            "/api/v1/dashboard/summary", params={"month": "2026-13"}, headers=auth_headers
        )

        assert response.status_code == 422

    def test_trends_rejects_unknown_granularity(self, client, auth_headers):
        response = client.get(
            "/api/v1/dashboard/trends",
            params={"granularity": "hourly"},
            headers=auth_headers,
        )

        assert response.status_code == 422

    def test_endpoints_are_scoped_to_the_current_user(
        self, client, auth_headers, auth_headers_user_2, seed_categories
    ):
        client.post(
            "/api/v1/transactions",
            json={
                "date": "2026-08-02",
                "description": "Groceries",
                "amount": 100.0,
                "type": "spend",
            },
            headers=auth_headers,
        )

        mine = client.get(
            "/api/v1/dashboard/summary", params={"month": "2026-08"}, headers=auth_headers
        ).json()
        theirs = client.get(
            "/api/v1/dashboard/summary",
            params={"month": "2026-08"},
            headers=auth_headers_user_2,
        ).json()

        assert mine["total_spent"] == 100.0
        assert theirs["total_spent"] == 0.0
