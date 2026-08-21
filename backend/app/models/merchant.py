import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Numeric, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


class Merchant(Base):
    __tablename__ = "merchants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    business_name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    phone = Column(String(20), nullable=True)
    business_type = Column(String(100), nullable=True)
    currency = Column(String(10), default="INR")
    current_balance = Column(Numeric(15, 2), default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    users = relationship("User", back_populates="merchant")
    transactions = relationship("Transaction", back_populates="merchant")
    refunds = relationship("Refund", back_populates="merchant")
    payouts = relationship("Payout", back_populates="merchant")
    cash_flow_events = relationship("CashFlowEvent", back_populates="merchant")
    conversations = relationship("AIConversation", back_populates="merchant")
    audit_logs = relationship("AuditLog", back_populates="merchant")
