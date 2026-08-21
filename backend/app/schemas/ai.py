from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=10000)
    conversation_id: UUID | None = None


class ToolCallInfo(BaseModel):
    name: str
    arguments: dict | None = None
    output: str | None = None
    status: str | None = None
    execution_time_ms: int | None = None


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    role: str
    content: str
    tools_called: list[ToolCallInfo] | None = None
    token_count: int | None = None
    created_at: datetime


class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    merchant_id: UUID
    user_id: UUID
    title: str | None = None
    messages: list[MessageResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class ChatResponse(BaseModel):
    conversation_id: UUID
    message: MessageResponse
    tools_called: list[ToolCallInfo] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
