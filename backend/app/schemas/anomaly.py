from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AnomalyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    merchant_id: UUID
    anomaly_type: str
    severity: str
    description: str
    detected_value: Decimal | None = None
    expected_range_min: Decimal | None = None
    expected_range_max: Decimal | None = None
    is_resolved: bool
    created_at: datetime


class AnomalyDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    merchant_id: UUID
    anomaly_type: str
    severity: str
    description: str
    detected_value: Decimal | None = None
    expected_range_min: Decimal | None = None
    expected_range_max: Decimal | None = None
    affected_transactions: list[UUID] = Field(default_factory=list)
    suggested_actions: list[str] = Field(default_factory=list)
    is_resolved: bool
    resolved_at: datetime | None = None
    resolved_by: UUID | None = None
    created_at: datetime


class AnomalyListResponse(BaseModel):
    items: list[AnomalyResponse]
    total: int
    unresolved_count: int
    critical_count: int
