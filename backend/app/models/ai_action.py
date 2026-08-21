import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Numeric
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.database import Base


class AIAction(Base):
    __tablename__ = "ai_actions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    merchant_id = Column(UUID(as_uuid=True), ForeignKey("merchants.id"), nullable=False, index=True)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("ai_conversations.id"), nullable=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    action_type = Column(String(100), nullable=False)
    action_class = Column(String(50), nullable=False)
    description = Column(Text, nullable=False)
    reason = Column(Text, nullable=True)
    input_data = Column(JSONB, nullable=True)
    output_data = Column(JSONB, nullable=True)
    estimated_impact = Column(Numeric(15, 2), nullable=True)
    risk_level = Column(String(20), nullable=True)
    approval_status = Column(String(50), nullable=False, default="pending")
    execution_status = Column(String(50), nullable=False, default="not_started")
    approved_by = Column(UUID(as_uuid=True), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    executed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    merchant = relationship("Merchant")
