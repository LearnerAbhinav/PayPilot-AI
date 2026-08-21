from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    merchant_id: UUID
    user_id: UUID | None = None
    action: str
    resource_type: str | None = None
    resource_id: str | None = None
    details: dict | None = None
    user_prompt: str | None = None
    agent_decision: str | None = None
    tools_called: list[str] | None = None
    tool_inputs: dict | None = None
    tool_outputs: dict | None = None
    ip_address: str | None = None
    created_at: datetime


class AuditLogListResponse(BaseModel):
    items: list[AuditLogResponse]
    total: int
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)
    total_pages: int
