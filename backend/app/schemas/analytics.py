from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class MetricsResponse(BaseModel):
    total_revenue: Decimal
    total_transactions: int
    success_rate: float
    average_transaction_value: Decimal
    total_refunds: Decimal
    refund_rate: float
    active_customers: int
    new_customers: int
    revenue_growth_pct: float | None = None
    transaction_growth_pct: float | None = None


class PeriodComparison(BaseModel):
    current_period: MetricsResponse
    previous_period: MetricsResponse
    revenue_change_pct: float
    transaction_change_pct: float
    success_rate_change: float


class RevenueTrend(BaseModel):
    date: datetime
    revenue: Decimal
    transactions: int
    refunds: Decimal


class PaymentMethodBreakdown(BaseModel):
    payment_method: str
    count: int
    total_amount: Decimal
    percentage: float
    success_rate: float


class TimeSeriesData(BaseModel):
    label: str
    timestamp: datetime
    value: Decimal
    secondary_value: float | None = None
