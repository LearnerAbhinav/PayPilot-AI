import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Numeric, ForeignKey, Text, Index
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class PaymentFailure(Base):
    __tablename__ = "payment_failures"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    transaction_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    merchant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    error_code = Column(String(100), nullable=False)
    error_message = Column(Text, nullable=True)
    payment_method = Column(String(50), nullable=False)
    amount = Column(Numeric(15, 2), nullable=False)
    is_retryable = Column(String(10), default="true")
    recovered = Column(String(10), default="false")
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_payment_failures_merchant_created", "merchant_id", "created_at"),
    )
