from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ActionClass(str, Enum):
    PAYMENT_RETRY = "payment_retry"
    REFUND_PROCESS = "refund_process"
    PAYOUT_SCHEDULE = "payout_schedule"
    PAYMENT_METHOD_TOGGLE = "payment_method_toggle"
    NOTIFICATION_SEND = "notification_send"
    ACCOUNT_ADJUSTMENT = "account_adjustment"


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class ExecutionStatus(str, Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ActionProposal(BaseModel):
    action_type: str = Field(max_length=100)
    action_class: ActionClass
    description: str
    reason: str | None = None
    input_data: dict | None = None
    estimated_impact: Decimal | None = None
    risk_level: RiskLevel = RiskLevel.LOW
    conversation_id: UUID | None = None


class ActionApprovalRequest(BaseModel):
    action_id: UUID
    approved: bool
    notes: str | None = Field(default=None, max_length=1000)


class ActionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    merchant_id: UUID
    conversation_id: UUID | None = None
    user_id: UUID
    action_type: str
    action_class: str
    description: str
    reason: str | None = None
    input_data: dict | None = None
    output_data: dict | None = None
    estimated_impact: Decimal | None = None
    risk_level: str | None = None
    approval_status: str
    execution_status: str
    approved_by: UUID | None = None
    approved_at: datetime | None = None
    executed_at: datetime | None = None
    created_at: datetime


class ActionResult(BaseModel):
    action_id: UUID
    execution_status: ExecutionStatus
    output_data: dict | None = None
    error_message: str | None = None
    completed_at: datetime | None = None
