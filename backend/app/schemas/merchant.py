from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class MerchantCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    business_name: str = Field(min_length=1, max_length=255)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=20)
    business_type: str | None = Field(default=None, max_length=100)
    currency: str = Field(default="INR", max_length=10)


class MerchantResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    business_name: str
    email: str
    phone: str | None = None
    business_type: str | None = None
    currency: str
    current_balance: Decimal
    created_at: datetime
    updated_at: datetime
