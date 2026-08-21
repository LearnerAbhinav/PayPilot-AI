"""
Unit and integration tests for Evidence-Driven Financial Operations Investigation.
Validates mathematical decomposition, stage chaining, policy grounding, and tool integrity.
"""
import uuid
import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.transaction import Transaction
from app.tools.decomposition_tools import (
    ComparePeriodsTool,
    GetPaymentMethodHealthTool,
    GetFailureReasonDistributionTool,
    CalculateFinancialImpactTool,
    CalculateRecoverableRevenueTool,
)
from app.agent.orchestrator import AIAgentOrchestrator
from app.services.recovery_policy import evaluate_transaction, ESTIMATED_RETRY_SUCCESS_RATE


@pytest.fixture
def sample_merchant_id():
    return uuid.UUID("11111111-1111-1111-1111-111111111111")


@pytest.fixture
def mock_db_session():
    return AsyncMock()


@pytest.fixture
def sample_transactions(sample_merchant_id):
    now = datetime.utcnow()
    txns = []
    # Current period (last 7 days): 10 captured (₹50,000 total, ATV ₹5,000), 10 failed (UPI timeouts)
    for i in range(10):
        txns.append(
            Transaction(
                id=uuid.uuid4(),
                merchant_id=sample_merchant_id,
                amount=Decimal("5000.00"),
                currency="INR",
                status="captured",
                payment_method="upi",
                payment_gateway="razorpay",
                created_at=now - timedelta(days=2, hours=i),
                updated_at=now - timedelta(days=2, hours=i),
            )
        )
    for i in range(10):
        txns.append(
            Transaction(
                id=uuid.uuid4(),
                merchant_id=sample_merchant_id,
                amount=Decimal("4000.00"),
                currency="INR",
                status="failed",
                payment_method="upi",
                payment_gateway="razorpay",
                failure_code="upi_timeout",
                failure_reason="UPI response timeout",
                created_at=now - timedelta(days=1, hours=i),
                updated_at=now - timedelta(days=1, hours=i),
            )
        )
    # Baseline period (7-14 days ago): 20 captured (₹120,000 total, ATV ₹6,000), 2 failed
    for i in range(20):
        txns.append(
            Transaction(
                id=uuid.uuid4(),
                merchant_id=sample_merchant_id,
                amount=Decimal("6000.00"),
                currency="INR",
                status="captured",
                payment_method="upi",
                payment_gateway="razorpay",
                created_at=now - timedelta(days=10, hours=i),
                updated_at=now - timedelta(days=10, hours=i),
            )
        )
    for i in range(2):
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
async def test_compare_periods_decomposition(mock_db_session, sample_merchant_id, sample_transactions):
    tool = ComparePeriodsTool()
    
    # Split sample transactions into current vs baseline
    now = datetime.utcnow()
    current_txns = [t for t in sample_transactions if t.created_at >= now - timedelta(days=7)]
    baseline_txns = [t for t in sample_transactions if t.created_at < now - timedelta(days=7)]

    # Mock execute returns
    mock_curr_result = MagicMock()
    mock_curr_result.scalars.return_value.all.return_value = current_txns

    mock_base_result = MagicMock()
    mock_base_result.scalars.return_value.all.return_value = baseline_txns

    mock_db_session.execute.side_effect = [mock_curr_result, mock_base_result]

    result = await tool.execute(mock_db_session, sample_merchant_id, days=7, baseline_days=7)

    assert result["current_period"]["revenue"] == 50000.0
    assert result["baseline_period"]["revenue"] == 120000.0
    assert result["decomposition"]["revenue_change_amount"] == -70000.0
    assert result["decomposition"]["revenue_change_pct"] < -50.0
    assert result["current_period"]["failure_rate"] == 50.0  # 10 failed out of 20 total
    assert result["baseline_period"]["failure_rate"] < 10.0
    assert result["decomposition"]["primary_driver"] == "payment_failure_surge"


@pytest.mark.asyncio
async def test_payment_method_health_isolation(mock_db_session, sample_merchant_id, sample_transactions):
    tool = GetPaymentMethodHealthTool()

    now = datetime.utcnow()
    current_txns = [t for t in sample_transactions if t.created_at >= now - timedelta(days=7)]
    baseline_txns = [t for t in sample_transactions if t.created_at < now - timedelta(days=7)]

    mock_curr = MagicMock()
    mock_curr.scalars.return_value.all.return_value = current_txns

    mock_base = MagicMock()
    mock_base.scalars.return_value.all.return_value = baseline_txns

    mock_db_session.execute.side_effect = [mock_curr, mock_base]

    result = await tool.execute(mock_db_session, sample_merchant_id, days=7, baseline_days=7)

    assert result["methods_analyzed"] >= 1
    assert result["primary_offending_method"] == "UPI"
    assert len(result["abnormal_methods"]) >= 1
    assert result["abnormal_methods"][0]["status"] == "CRITICAL_FAILURE_SURGE"


@pytest.mark.asyncio
async def test_failure_reason_distribution(mock_db_session, sample_merchant_id, sample_transactions):
    tool = GetFailureReasonDistributionTool()
    failed_txns = [t for t in sample_transactions if t.status == "failed"]

    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = failed_txns
    mock_db_session.execute.return_value = mock_res

    result = await tool.execute(mock_db_session, sample_merchant_id, payment_method="upi", days=7)

    assert result["total_failures"] == len(failed_txns)
    assert result["primary_failure_code"] == "upi_timeout"
    assert len(result["failure_reasons"]) >= 1
    assert result["failure_reasons"][0]["is_retryable"] is True
    assert result["failure_reasons"][0]["classification"] == "transient_network_or_gateway"


@pytest.mark.asyncio
async def test_calculate_recoverable_revenue(mock_db_session, sample_merchant_id, sample_transactions):
    tool = CalculateRecoverableRevenueTool()
    failed_txns = [t for t in sample_transactions if t.status == "failed"]

    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = failed_txns
    mock_db_session.execute.return_value = mock_res

    result = await tool.execute(mock_db_session, sample_merchant_id, payment_method="upi", days=7)

    assert result["total_failed_analyzed"] == len(failed_txns)
    assert result["eligible_for_smart_retry"] == 10  # 10 within 72h window
    assert result["ineligible_count"] == 2  # 2 older than 72h window rejected by policy
    assert result["eligible_amount_inr"] > 0
    assert result["projected_recovery_inr"] == round(result["eligible_amount_inr"] * ESTIMATED_RETRY_SUCCESS_RATE, 2)


def test_orchestrator_tool_registration():
    orchestrator = AIAgentOrchestrator(
        llm_api_key="test_key",
        llm_model="openai/gpt-oss-120b",
        llm_provider="groq",
    )
    
    # Must have all core decomposition, telemetry, and policy tools registered
    assert "compare_periods" in orchestrator.tools
    assert "get_payment_method_health" in orchestrator.tools
    assert "get_failure_reason_distribution" in orchestrator.tools
    assert "calculate_financial_impact" in orchestrator.tools
    assert "calculate_recoverable_revenue" in orchestrator.tools
    assert "get_transaction_metrics" in orchestrator.tools
    assert "simulate_payment_recovery" in orchestrator.tools
    assert len(orchestrator.tools) >= 18
