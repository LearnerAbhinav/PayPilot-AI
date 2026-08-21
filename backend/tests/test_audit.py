import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.audit_log import AuditLog
from app.services.audit import AuditService


@pytest.mark.asyncio
async def test_log_action(mock_db_session):
    merchant_id = uuid.uuid4()
    user_id = uuid.uuid4()

    log = await AuditService.log_action(
        db=mock_db_session,
        merchant_id=merchant_id,
        user_id=user_id,
        action="action_approved",
        resource_type="ai_action",
        resource_id=str(uuid.uuid4()),
        details={"approved_by": str(user_id)},
    )

    assert log.merchant_id == merchant_id
    assert log.action == "action_approved"
    assert log.resource_type == "ai_action"
    assert mock_db_session.add.called
    assert mock_db_session.flush.called


@pytest.mark.asyncio
async def test_log_ai_action_with_tools(mock_db_session):
    merchant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    prompt = "Why did UPI transactions fail today?"
    decision = "Detected elevated timeouts from issuer bank."
    tools = ["get_transaction_metrics", "detect_anomalies"]
    outputs = {"detect_anomalies": {"spike": True}}

    log = await AuditService.log_ai_action(
        db=mock_db_session,
        merchant_id=merchant_id,
        user_id=user_id,
        prompt=prompt,
        decision=decision,
        tools=tools,
        outputs=outputs,
    )

    assert log.merchant_id == merchant_id
    assert log.action == "ai_action"
    assert log.user_prompt == prompt
    assert log.agent_decision == decision
    assert log.tools_called == tools
    assert log.tool_outputs == outputs
    assert mock_db_session.add.called
    assert mock_db_session.flush.called


@pytest.mark.asyncio
async def test_get_audit_logs(mock_db_session):
    merchant_id = uuid.uuid4()
    mock_logs = [
        AuditLog(
            id=uuid.uuid4(),
            merchant_id=merchant_id,
            action="action_executed",
            created_at=datetime.utcnow(),
        )
    ]

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = mock_logs
    mock_db_session.execute.return_value = mock_result

    logs = await AuditService.get_audit_logs(mock_db_session, merchant_id, limit=10, offset=0)

    assert len(logs) == 1
    assert logs[0].action == "action_executed"
