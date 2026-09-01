from pydantic import BaseModel


class DashboardSummary(BaseModel):
    total_earned: float
    total_spent: float
    balance: float
    month: str  # "2026-08"


class CategoryBreakdownItem(BaseModel):
    category_name: str
    total_amount: float
    percentage: float


class TrendPoint(BaseModel):
    period: str  # "2026-08" for monthly, "2026-08-24" for daily
    total_spent: float
    total_earned: float


class InsightAlert(BaseModel):
    category_name: str
    message: str
    current_amount: float
    average_amount: float
    severity: str  # "info" | "warning"
