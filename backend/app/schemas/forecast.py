from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, Field


class ForecastHorizon(str, Enum):
    WEEK_1 = "1w"
    MONTH_1 = "1m"
    MONTH_3 = "3m"
    MONTH_6 = "6m"


class ForecastRequest(BaseModel):
    horizon: ForecastHorizon = ForecastHorizon.MONTH_1
    metric: str = Field(default="revenue", description="Metric to forecast: revenue, transactions, success_rate")
    include_confidence: bool = True


class ForecastDataPoint(BaseModel):
    date: datetime
    predicted_value: Decimal
    lower_bound: Decimal | None = None
    upper_bound: Decimal | None = None
    confidence_level: float | None = None


class ForecastSummary(BaseModel):
    trend: str = Field(description="upward, downward, or stable")
    total_predicted: Decimal
    avg_predicted: Decimal
    min_predicted: Decimal
    max_predicted: Decimal
    growth_rate_pct: float


class ForecastResponse(BaseModel):
    metric: str
    horizon: ForecastHorizon
    data_points: list[ForecastDataPoint]
    summary: ForecastSummary
    model_accuracy: float | None = Field(default=None, description="R² or MAPE score")
    generated_at: datetime
