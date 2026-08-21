from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: UUID
    merchant_id: UUID | None = None
    role: str


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=255)
    business_name: str = Field(min_length=1, max_length=255)
    business_type: str | None = Field(default=None, max_length=100)
    phone: str | None = Field(default=None, max_length=20)
