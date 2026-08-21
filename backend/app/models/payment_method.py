import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Numeric, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class PaymentMethod(Base):
    __tablename__ = "payment_methods"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    merchant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    type = Column(String(50), nullable=False)
    is_active = Column(String(10), default="true")
    success_rate = Column(Numeric(5, 2), default=100.00)
    total_transactions = Column(Numeric(15, 2), default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
