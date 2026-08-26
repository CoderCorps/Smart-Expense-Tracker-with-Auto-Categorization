"""
PERSON C OWNS THIS FILE. Keep it thin — the actual pandas aggregation logic
lives in services/analytics/aggregations.py, this file just fetches the
current user's transactions from the DB and hands them to those functions.
"""

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.app.api.deps import get_current_user, get_db
from backend.app.models.transaction import Transaction
from backend.app.models.user import User
from backend.app.schemas.dashboard import CategoryBreakdownItem, DashboardSummary, InsightAlert, TrendPoint
from backend.app.services.analytics.aggregations import (
    detect_spikes,
    get_category_breakdown,
    get_monthly_summary,
    get_trend,
)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _user_transactions(db: Session, user: User) -> list[Transaction]:
    return db.query(Transaction).filter(Transaction.user_id == user.id).all()


@router.get("/summary", response_model=DashboardSummary)
def dashboard_summary(
    month: str = Query(..., description="Format: YYYY-MM, e.g. 2026-08"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    transactions = _user_transactions(db, current_user)
    result = get_monthly_summary(transactions, month)
    return DashboardSummary(**result)


@router.get("/category-breakdown", response_model=list[CategoryBreakdownItem])
def category_breakdown(
    month: str | None = Query(None, description="Format: YYYY-MM. Omit for all-time."),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    transactions = _user_transactions(db, current_user)
    results = get_category_breakdown(transactions, month)
    return [CategoryBreakdownItem(**r) for r in results]


@router.get("/trends", response_model=list[TrendPoint])
def trends(
    granularity: str = Query("monthly", pattern="^(monthly|daily)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    transactions = _user_transactions(db, current_user)
    results = get_trend(transactions, granularity)
    return [TrendPoint(**r) for r in results]


@router.get("/insights", response_model=list[InsightAlert])
def insights(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    transactions = _user_transactions(db, current_user)
    results = detect_spikes(transactions)
    return [InsightAlert(**r) for r in results]
