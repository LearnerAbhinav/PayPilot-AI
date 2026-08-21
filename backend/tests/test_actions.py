import uuid
from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from fastapi import HTTPException

from app.models.ai_action import AIAction
from app.services.ai_action import AIActionService


@pytest.mark.asyncio
async def test_create_and_get_action(mock_db_session):
    merchant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    action_data = {
        "action_type": "bulk_payment_retry",
        "action_class": "reversible",
        "description": "Retry failed UPI transactions",
        "reason": "Elevated UPI timeout rate",
        "estimated_impact": Decimal("345000.00"),
        "risk_level": "low",
    }

    action = await AIActionService.create_action(
        mock_db_session, merchant_id, user_id, action_data
    )

    assert action.merchant_id == merchant_id
    assert action.action_type == "bulk_payment_retry"
    assert action.approval_status == "pending"
    assert action.execution_status == "not_started"
    assert mock_db_session.add.called
    assert mock_db_session.flush.called


@pytest.mark.asyncio
async def test_approve_action(mock_db_session):
    action_id = uuid.uuid4()
    merchant_id = uuid.uuid4()
    user_id = uuid.uuid4()

    mock_action = AIAction(
        id=action_id,
        merchant_id=merchant_id,
        user_id=user_id,
        action_type="bulk_payment_retry",
        action_class="reversible",
        description="Retry failed UPI transactions",
        approval_status="pending",
        execution_status="not_started",
        created_at=datetime.utcnow(),
    )

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_action
    mock_db_session.execute.return_value = mock_result

    approved = await AIActionService.approve_action(
        mock_db_session, action_id, merchant_id, user_id
    )

    assert approved.approval_status == "approved"
    assert approved.approved_by == user_id
    assert approved.approved_at is not None


@pytest.mark.asyncio
async def test_tenant_isolation_on_approval(mock_db_session):
    action_id = uuid.uuid4()
    merchant_a = uuid.uuid4()
    merchant_b = uuid.uuid4()
    user_id = uuid.uuid4()

    mock_action = AIAction(
        id=action_id,
        merchant_id=merchant_a,  # Belongs to merchant A
        user_id=user_id,
        action_type="bulk_payment_retry",
        action_class="reversible",
        description="Retry failed transactions",
        approval_status="pending",
        execution_status="not_started",
    )

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_action
    mock_db_session.execute.return_value = mock_result

    # Merchant B tries to approve Merchant A's action -> should raise 404
    with pytest.raises(HTTPException) as exc_info:
        await AIActionService.approve_action(
            mock_db_session, action_id, merchant_b, user_id
        )

    assert exc_info.value.status_code == 404
    assert mock_action.approval_status == "pending"  # No mutation occurred!


@pytest.mark.asyncio
async def test_execute_action_lifecycle(mock_db_session):
    action_id = uuid.uuid4()
    merchant_id = uuid.uuid4()
    user_id = uuid.uuid4()

    mock_action = AIAction(
        id=action_id,
        merchant_id=merchant_id,
        user_id=user_id,
        action_type="bulk_payment_retry",
        action_class="reversible",
        description="Retry failed transactions",
        input_data={"eligible_count": 50, "target_failure_code": "upi_timeout"},
        approval_status="approved",
        approved_by=user_id,
        execution_status="not_started",
        created_at=datetime.utcnow(),
    )

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_action
    mock_db_session.execute.return_value = mock_result

    executed = await AIActionService.execute_action(
        mock_db_session, action_id, merchant_id, user_id
    )

    assert executed.execution_status == "completed"
    assert executed.executed_at is not None
    assert executed.output_data is not None
    assert executed.output_data["status"] == "success"
    assert executed.output_data["successfully_recovered"] == 35  # 70% of 50
