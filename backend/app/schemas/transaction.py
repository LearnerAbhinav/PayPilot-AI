from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    merchant_id: UUID
    customer_id: UUID | None = None
    amount: Decimal
    currency: str
    status: str
    payment_method: str
    payment_gateway: str | None = None
    failure_code: str | None = None
    failure_reason: str | None = None
    description: str | None = None
    metadata_json: str | None = None
    created_at: datetime
    updated_at: datetime


class TransactionListResponse(BaseModel):
    items: list[TransactionResponse]
    total: int
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)
    total_pages: int


class TransactionFilter(BaseModel):
    status: str | None = None
    payment_method: str | None = None
    payment_gateway: str | None = None
    min_amount: Decimal | None = Field(default=None, ge=0)
    max_amount: Decimal | None = Field(default=None, ge=0)
    start_date: datetime | None = None
    end_date: datetime | None = None
    customer_id: UUID | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
