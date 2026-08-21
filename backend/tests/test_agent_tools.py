import uuid

import pytest

from app.tools.base import BaseTool, ActionClass, ToolValidationError
from app.tools.transaction_tools import (
    GetTransactionMetricsTool,
    GetFailedTransactionsTool,
    GetRevenueTrendTool,
    GetPaymentMethodBreakdownTool,
    GetRefundSummaryTool,
    GetCustomerSummaryTool,
)
from app.tools.analytics_tools import DetectAnomaliesTool
from app.tools.forecast_tools import ForecastCashFlowTool
from app.tools.recommendation_tools import (
    GenerateRecoveryPlanTool,
    SimulatePaymentRecoveryTool,
)
from app.tools.notification_tools import CreateAlertTool
from app.agent.orchestrator import AIAgentOrchestrator


def test_tool_registration():
    orchestrator = AIAgentOrchestrator(
        llm_api_key="test-key",
        llm_model="gpt-4o",
        llm_provider="openai",
    )
    assert len(orchestrator.tools) > 0

    expected_tools = [
        "get_transaction_metrics",
        "get_failed_transactions",
        "get_revenue_trend",
        "get_payment_method_breakdown",
        "get_refund_summary",
        "get_customer_summary",
        "detect_anomalies",
        "forecast_cash_flow",
        "generate_recovery_plan",
        "simulate_payment_recovery",
        "create_alert",
    ]
    for tool_name in expected_tools:
        assert tool_name in orchestrator.tools, f"Tool '{tool_name}' not registered"


def test_get_transaction_metrics_tool():
    tool = GetTransactionMetricsTool()
    assert tool.name == "get_transaction_metrics"
    assert tool.action_class == ActionClass.READ_ONLY
    assert "type" in tool.parameters
    assert tool.parameters["type"] == "object"

    definition = tool.get_definition()
    assert definition["type"] == "function"
    assert definition["function"]["name"] == "get_transaction_metrics"
    assert "description" in definition["function"]
    assert "parameters" in definition["function"]


def test_tool_validates_merchant_id():
    tool = GetTransactionMetricsTool()

    validated = tool.validate_inputs(period="daily", days=30)
    assert validated["period"] == "daily"
    assert validated["days"] == 30

    validated = tool.validate_inputs()
    assert validated == {}

    with pytest.raises(ToolValidationError, match="Missing required parameter"):
        required_tool = CreateAlertTool()
        required_tool.validate_inputs()
