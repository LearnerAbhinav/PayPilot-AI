import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Float
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.database import Base


class Investigation(Base):
    """
    Persists the full lifecycle of an autonomous AI investigation.
    Ties together anomaly → deterministic telemetry → agent reasoning → findings → proposed action.
    """
    __tablename__ = "investigations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    merchant_id = Column(UUID(as_uuid=True), ForeignKey("merchants.id"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("ai_conversations.id"), nullable=True)
    action_id = Column(UUID(as_uuid=True), ForeignKey("ai_actions.id"), nullable=True, index=True)

    # Status lifecycle: STARTED → ANALYZING → FINDINGS_READY → ACTION_PROPOSED → CLOSED / AI_FAILED
    status = Column(String(50), nullable=False, default="STARTED", index=True)

    title = Column(String(255), nullable=False)
    user_request = Column(Text, nullable=True)
    anomaly_type = Column(String(100), nullable=True)
    severity = Column(String(20), nullable=True, default="high")  # critical | high | medium | low

    # Tool Execution Telemetry & Evidence (Persisted permanently)
    # events: [{ stage, tool_name, start_time, end_time, duration_ms, status, summary, arguments }]
    events = Column(JSONB, nullable=True)
    evidence = Column(JSONB, nullable=True)
    
    # Structured Findings & Provenance
    findings = Column(JSONB, nullable=True)
    root_cause = Column(Text, nullable=True)
    supporting_evidence = Column(JSONB, nullable=True)  # [{ claim, source_tool, metric, change }]
    contradictory_evidence = Column(JSONB, nullable=True)  # [{ claim, counter_indicator }]
    
    # Financial Impact & Recovery Opportunity
    financial_impact = Column(JSONB, nullable=True)  # { revenue_gap, volume_loss, failure_loss, unrealized_revenue }
    recovery_opportunity = Column(JSONB, nullable=True)  # { eligible_transactions, recoverable_amount, policy_version }
    recommendation = Column(Text, nullable=True)

    # Confidence and Risk Classification
    # classification: CONFIRMED | LIKELY | POSSIBLE | INSUFFICIENT_EVIDENCE
    classification = Column(String(50), nullable=True, default="LIKELY")
    confidence_score = Column(Float, nullable=True)  # 0 - 100
    confidence = Column(String(20), nullable=True)   # low | medium | high
    risk = Column(String(20), nullable=True, default="low")  # low | medium | high

    # Agent Synthesis
    agent_summary = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    merchant = relationship("Merchant")
    action = relationship("AIAction", foreign_keys=[action_id])
    conversation = relationship("AIConversation", foreign_keys=[conversation_id])
    anomaly = relationship("Anomaly", back_populates="investigation", foreign_keys="Anomaly.investigation_id", uselist=False)
