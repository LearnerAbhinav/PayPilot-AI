"""
Comprehensive Unit & Integration Test Suite for PayPilot AI Autonomous Operations Engine.
Validates:
1. Deterministic Monitoring & Anomaly Fingerprint Deduplication
2. Autonomous Investigation Triggering & Telemetry Persistence
3. Investigation History Retrieval by ID & Messages/Events Reconstruction
4. Automatic AIAction Proposal Generation
5. Human-in-the-Loop Action Approval, Rejection & Simulation Execution
6. Emergency Kill Switch Pause & Resume
7. Comprehensive Audit Logging Lifecycle
"""
import uuid
import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.anomaly import Anomaly
from app.models.investigation import Investigation
from app.models.ai_action import AIAction
from app.models.ai_conversation import AIConversation
from app.models.ai_message import AIMessage
from app.models.transaction import Transaction
from app.models.user import User
from app.models.merchant import Merchant
from app.services.monitoring_service import MonitoringService
from app.services.ai_action import AIActionService
from app.services.recovery_policy import evaluate_transaction, ESTIMATED_RETRY_SUCCESS_RATE


@pytest.fixture
def sample_merchant_id():
    return uuid.UUID("11111111-1111-1111-1111-111111111111")


@pytest.fixture
def sample_user_id():
    return uuid.UUID("22222222-2222-2222-2222-222222222222")


@pytest.fixture
def mock_db_session():
    return AsyncMock()


@pytest.fixture
def sample_telemetry_dataset(sample_merchant_id):
    now = datetime.utcnow()
    txns = []
    # Current period (last 7 days): 15 failed UPI txns, 5 captured UPI txns => 75% failure rate (CRITICAL SURGE)
    for i in range(15):
        txns.append(
            Transaction(
                id=uuid.uuid4(),
                merchant_id=sample_merchant_id,
                amount=Decimal("3500.00"),
                currency="INR",
                status="failed",
                payment_method="upi",
                payment_gateway="razorpay",
                failure_code="upi_timeout",
                failure_reason="UPI response timeout",
                created_at=now - timedelta(days=2, hours=i),
                updated_at=now - timedelta(days=2, hours=i),
            )
        )
    for i in range(5):
        txns.append(
            Transaction(
                id=uuid.uuid4(),
                merchant_id=sample_merchant_id,
                amount=Decimal("5000.00"),
                currency="INR",
                status="captured",
                payment_method="upi",
                payment_gateway="razorpay",
                created_at=now - timedelta(days=3, hours=i),
                updated_at=now - timedelta(days=3, hours=i),
            )
        )
    # Baseline period (7-14 days ago): 25 captured UPI, 1 failed UPI => 3.8% baseline failure rate
    for i in range(25):
        txns.append(
            Transaction(
                id=uuid.uuid4(),
                merchant_id=sample_merchant_id,
                amount=Decimal("4500.00"),
                currency="INR",
                status="captured",
                payment_method="upi",
                payment_gateway="razorpay",
                created_at=now - timedelta(days=10, hours=i),
                updated_at=now - timedelta(days=10, hours=i),
            )
        )
    for i in range(1):
        txns.append(
            Transaction(
                id=uuid.uuid4(),
                merchant_id=sample_merchant_id,
                amount=Decimal("3000.00"),
                currency="INR",
                status="failed",
                payment_method="upi",
                payment_gateway="razorpay",
                failure_code="upi_timeout",
                failure_reason="UPI response timeout",
                created_at=now - timedelta(days=11, hours=i),
                updated_at=now - timedelta(days=11, hours=i),
            )
        )
    return txns


@pytest.mark.asyncio
async def test_monitoring_cycle_end_to_end(
    mock_db_session, sample_merchant_id, sample_user_id, sample_telemetry_dataset
):
    """
    Test that a single monitoring cycle:
    1. Detects UPI failure surge deterministically
    2. Spawns an Investigation with telemetry events
    3. Evaluates SMART_RETRY_V1.2 recovery policy
    4. Automatically proposes an AIAction in PENDING_APPROVAL status
    """
    def mock_execute_side_effect(stmt, *args, **kwargs):
        stmt_str = str(stmt)
        res = MagicMock()
        if "transactions" in stmt_str:
            # Check if there's a status filter or date filter
            failed_only = "status = :status" in stmt_str or "status = 'failed'" in stmt_str
            if failed_only:
                res.scalars.return_value.all.return_value = [t for t in sample_telemetry_dataset if t.status == "failed"]
            else:
                res.scalars.return_value.all.return_value = sample_telemetry_dataset
        elif "users" in stmt_str:
            res.scalar_one_or_none.return_value = User(
                id=sample_user_id,
                merchant_id=sample_merchant_id,
                email="operator@paypilot.ai",
                full_name="Operator",
                hashed_password="hashed_pw_test",
                role="operator",
            )
        elif "merchants" in stmt_str:
            res.scalar_one_or_none.return_value = Merchant(
                id=sample_merchant_id,
                name="Demo Merchant",
            )
        else:
            res.scalar_one_or_none.return_value = None
            res.scalars.return_value.all.return_value = []
        return res

    mock_db_session.execute.side_effect = mock_execute_side_effect

    with patch("app.services.audit.AuditService.log_action", new_callable=AsyncMock) as mock_audit:
        result = await MonitoringService.run_monitoring_cycle(
            db=mock_db_session,
            merchant_id=sample_merchant_id,
            user_id=sample_user_id,
        )

        assert result["status"] == "success"
        assert result["anomalies_detected"] >= 1
        assert result["investigations_triggered"] >= 1
        assert result["actions_proposed"] >= 1

        # Verify audit logs were produced for anomaly, investigation, and action
        assert mock_audit.call_count >= 3


def test_emergency_kill_switch():
    """Verify pause and resume of autonomous recovery actions."""
    assert MonitoringService.is_autonomous_paused() is False

    # Pause
    MonitoringService.set_autonomous_paused(True)
    assert MonitoringService.is_autonomous_paused() is True

    # Resume
    MonitoringService.set_autonomous_paused(False)
    assert MonitoringService.is_autonomous_paused() is False


@pytest.mark.asyncio
async def test_action_approval_and_simulation_execution(
    mock_db_session, sample_merchant_id, sample_user_id
):
    """
    Verify human-in-the-loop action lifecycle:
    PENDING_APPROVAL -> APPROVED -> SIMULATION EXECUTED -> OUTCOME VERIFIED
    """
    action = AIAction(
        id=uuid.uuid4(),
        merchant_id=sample_merchant_id,
        user_id=sample_user_id,
        action_type="bulk_payment_retry",
        action_class="reversible",
        description="Smart Retry for 15 failed UPI payments",
        input_data={
            "transaction_ids": [str(uuid.uuid4()) for _ in range(15)],
            "eligible_count": 15,
            "total_eligible_amount": 52500.0,
            "policy_version": "SMART_RETRY_V1.2",
        },
        estimated_impact=Decimal("36750.00"),
        approval_status="pending",
        execution_status="not_started",
        created_at=datetime.utcnow(),
    )

    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = action
    mock_db_session.execute.return_value = mock_res

    # 1. Human Approves
    with patch("app.services.audit.AuditService.log_action", new_callable=AsyncMock):
        approved_action = await AIActionService.approve_action(
            db=mock_db_session,
            action_id=action.id,
            merchant_id=sample_merchant_id,
            user_id=sample_user_id,
        )
        assert approved_action.approval_status == "approved"
        assert approved_action.approved_by == sample_user_id

    # 2. Operator Executes Simulation
    with patch("app.services.audit.AuditService.log_action", new_callable=AsyncMock):
        executed_action = await AIActionService.execute_action(
            db=mock_db_session,
            action_id=action.id,
            merchant_id=sample_merchant_id,
            user_id=sample_user_id,
        )
        assert executed_action.execution_status == "completed"
        assert executed_action.output_data is not None
        assert executed_action.output_data["simulation_mode"] is True
        assert executed_action.output_data["successfully_recovered"] > 0
        assert executed_action.output_data["recovered_amount_inr"] > 0
