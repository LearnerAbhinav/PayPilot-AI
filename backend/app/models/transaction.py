import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Numeric, ForeignKey, Integer, Text, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    merchant_id = Column(UUID(as_uuid=True), ForeignKey("merchants.id"), nullable=False, index=True)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=True, index=True)
    amount = Column(Numeric(15, 2), nullable=False)
    currency = Column(String(10), default="INR")
    status = Column(String(50), nullable=False, index=True)
    payment_method = Column(String(50), nullable=False, index=True)
    payment_gateway = Column(String(50), default="razorpay")
    failure_code = Column(String(100), nullable=True)
    failure_reason = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    metadata_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    merchant = relationship("Merchant", back_populates="transactions")
    customer = relationship("Customer", back_populates="transactions")
    refunds = relationship("Refund", back_populates="transaction")

    __table_args__ = (
        Index("idx_transactions_merchant_created", "merchant_id", "created_at"),
        Index("idx_transactions_status_created", "status", "created_at"),
    )
