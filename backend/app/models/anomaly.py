import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Float, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


class Anomaly(Base):
    """
    Persisted anomaly detected by the deterministic monitoring engine.
    Uses unique deterministic fingerprinting to ensure idempotency.
    """
    __tablename__ = "anomalies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    merchant_id = Column(UUID(as_uuid=True), ForeignKey("merchants.id"), nullable=False, index=True)
    
    # Deterministic fingerprint: metric + payment_method + date_window + type
    fingerprint = Column(String(255), nullable=False, index=True)
    
    type = Column(String(100), nullable=False)
    severity = Column(String(20), nullable=False, default="medium", index=True)  # critical | high | medium | low
    metric = Column(String(100), nullable=False)
    
    current_value = Column(Float, nullable=False)
    baseline_value = Column(Float, nullable=False)
    percentage_change = Column(Float, nullable=False)
    
    explanation = Column(Text, nullable=False)
    is_resolved = Column(Boolean, default=False, index=True)
    
    investigation_id = Column(UUID(as_uuid=True), ForeignKey("investigations.id"), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    merchant = relationship("Merchant")
    investigation = relationship("Investigation", back_populates="anomaly", foreign_keys=[investigation_id])
