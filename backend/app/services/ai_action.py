import uuid
from datetime import datetime
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_action import AIAction


class AIActionService:
    @staticmethod
    async def create_action(
        db: AsyncSession,
        merchant_id: uuid.UUID,
        user_id: uuid.UUID,
        action_data: dict,
    ) -> AIAction:
        action = AIAction(
            merchant_id=merchant_id,
            user_id=user_id,
            conversation_id=action_data.get("conversation_id"),
            action_type=action_data["action_type"],
            action_class=action_data.get("action_class", "recommendation"),
            description=action_data["description"],
            reason=action_data.get("reason"),
            input_data=action_data.get("input_data"),
            estimated_impact=action_data.get("estimated_impact"),
            risk_level=action_data.get("risk_level", "low"),
            approval_status="pending",
            execution_status="not_started",
            created_at=datetime.utcnow(),
        )
        db.add(action)
        await db.flush()
        await db.refresh(action)

        from app.services.audit import AuditService
        await AuditService.log_action(
            db=db,
            merchant_id=merchant_id,
            user_id=user_id,
            action="action_proposed",
            resource_type="ai_action",
            resource_id=str(action.id),
            details={
                "action_type": action.action_type,
                "description": action.description,
                "risk_level": action.risk_level,
                "estimated_impact": str(action.estimated_impact) if action.estimated_impact else None,
            },
        )
        return action

    @staticmethod
    async def approve_action(
        db: AsyncSession,
        action_id: uuid.UUID,
        merchant_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> AIAction:
        result = await db.execute(
            select(AIAction).where(AIAction.id == action_id)
        )
        action = result.scalar_one_or_none()
        if not action or action.merchant_id != merchant_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Action not found",
            )
        if action.approval_status != "pending":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Action is already {action.approval_status}",
            )
        action.approval_status = "approved"
        action.approved_by = user_id
        action.approved_at = datetime.utcnow()
        await db.flush()
        await db.refresh(action)

        from app.services.audit import AuditService
        await AuditService.log_action(
            db=db,
            merchant_id=merchant_id,
            user_id=user_id,
            action="action_approved",
            resource_type="ai_action",
            resource_id=str(action.id),
            details={
                "action_type": action.action_type,
                "approved_by": str(user_id),
                "estimated_impact": str(action.estimated_impact) if action.estimated_impact else None,
            },
        )
        return action

    @staticmethod
    async def execute_action(
        db: AsyncSession,
        action_id: uuid.UUID,
        merchant_id: uuid.UUID,
        user_id: uuid.UUID | None = None,
    ) -> AIAction:
        result = await db.execute(
            select(AIAction).where(AIAction.id == action_id)
        )
        action = result.scalar_one_or_none()
        if not action or action.merchant_id != merchant_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Action not found",
            )
        if action.approval_status != "approved":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Action must be approved before execution",
            )
        if action.execution_status == "completed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Action has already been executed",
            )

        action.execution_status = "in_progress"
        await db.flush()

        try:
            now_iso = datetime.utcnow().isoformat()

            if action.action_type in ("bulk_payment_retry", "payment_retry", "simulate_payment_recovery"):
                output = await AIActionService._simulate_bulk_retry(db, action, now_iso)

            elif action.action_type in ("configure_routing", "payment_method_toggle"):
                output = {
                    "status": "success",
                    "executed_at": now_iso,
                    "route_updated": True,
                    "primary_gateway": "Razorpay Alternate Pool",
                    "traffic_allocated_pct": 100,
                    "latency_impact_ms": -140,
                    "simulation_mode": True,
                }
            else:
                output = {
                    "status": "success",
                    "executed_at": now_iso,
                    "receipt": f"EXEC-{uuid.uuid4().hex[:8].upper()}",
                    "details": "Automated workflow completed successfully.",
                    "simulation_mode": True,
                }

            action.execution_status = "completed"
            action.executed_at = datetime.utcnow()
            action.output_data = output

            from app.services.audit import AuditService
            await AuditService.log_action(
                db=db,
                merchant_id=merchant_id,
                user_id=user_id or action.approved_by,
                action="action_executed",
                resource_type="ai_action",
                resource_id=str(action.id),
                details={
                    "action_type": action.action_type,
                    "execution_status": "completed",
                    "output_summary": {
                        k: v for k, v in output.items()
                        if k in ("status", "total_retried", "successfully_recovered", "recovered_amount_inr", "recovery_rate_pct")
                    },
                },
            )

        except Exception as e:
            action.execution_status = "failed"
            action.output_data = {
                "error": str(e),
                "failed_at": datetime.utcnow().isoformat(),
                "simulation_mode": True,
            }
            await db.flush()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Action execution failed: {e}",
            )

        await db.flush()
        await db.refresh(action)
        return action

    @staticmethod
    async def _simulate_bulk_retry(
        db: AsyncSession, action: AIAction, now_iso: str
    ) -> dict:
        """
        Simulate recovery against REAL transaction IDs from input_data.
        Derives outcomes from actual transaction amounts — not hardcoded values.
        """
        from app.models.transaction import Transaction
        from app.services.recovery_policy import ESTIMATED_RETRY_SUCCESS_RATE, evaluate_transaction

        input_data = action.input_data or {}
        transaction_ids_raw = input_data.get("transaction_ids", [])
        eligible_count = input_data.get("eligible_count", 0)
        total_eligible_amount = input_data.get("total_eligible_amount", 0.0)

        # If we have real transaction IDs, verify them against the DB
        actual_recovered_count = 0
        actual_recovered_amount = Decimal("0")
        breakdown_by_code: dict = {}

        if transaction_ids_raw:
            try:
                tx_ids = [uuid.UUID(str(tid)) for tid in transaction_ids_raw[:200]]
            except (ValueError, AttributeError):
                tx_ids = []

            if tx_ids:
                tx_result = await db.execute(
                    select(Transaction).where(Transaction.id.in_(tx_ids))
                )
                txns = list(tx_result.scalars().all())

                for t in txns:
                    decision = evaluate_transaction(t)
                    if decision.eligible:
                        # Simulate success at policy rate (deterministic per transaction)
                        # Use amount hash for reproducible simulation
                        import hashlib
                        tx_hash = int(hashlib.md5(str(t.id).encode()).hexdigest()[:8], 16)
                        simulated_success = (tx_hash % 100) < int(ESTIMATED_RETRY_SUCCESS_RATE * 100)
                        if simulated_success:
                            actual_recovered_count += 1
                            actual_recovered_amount += Decimal(str(t.amount))
                            code = t.failure_code or "unknown"
                            breakdown_by_code[code] = breakdown_by_code.get(code, 0) + 1

        # Fallback to estimates if no real transactions found
        if actual_recovered_count == 0 and eligible_count > 0:
            actual_recovered_count = int(eligible_count * ESTIMATED_RETRY_SUCCESS_RATE)
            actual_recovered_amount = Decimal(str(total_eligible_amount)) * Decimal(str(ESTIMATED_RETRY_SUCCESS_RATE))

        recovery_rate = (
            round(actual_recovered_count / max(eligible_count, 1) * 100, 1)
            if eligible_count > 0 else 0.0
        )

        return {
            "status": "success",
            "executed_at": now_iso,
            "simulation_mode": True,
            "total_retried": eligible_count or len(transaction_ids_raw),
            "successfully_recovered": actual_recovered_count,
            "recovered_amount_inr": float(actual_recovered_amount),
            "recovery_rate_pct": recovery_rate,
            "breakdown_by_failure_code": breakdown_by_code,
            "gateway_route": "Backup Gateway (Razorpay Secondary)",
            "settlement_status": "Queued for next settlement cycle (SIMULATION)",
            "note": (
                "⚠️ SIMULATION MODE: Outcomes derived from transaction dataset with "
                f"{int(ESTIMATED_RETRY_SUCCESS_RATE * 100)}% success rate model. "
                "No real payments were processed."
            ),
        }

    @staticmethod
    async def get_actions(
        db: AsyncSession,
        merchant_id: uuid.UUID,
        status_filter: str | None = None,
    ) -> list[AIAction]:
        query = select(AIAction).where(AIAction.merchant_id == merchant_id)
        if status_filter:
            query = query.where(AIAction.approval_status == status_filter)
        query = query.order_by(AIAction.created_at.desc())
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def get_action(
        db: AsyncSession,
        action_id: uuid.UUID,
    ) -> AIAction:
        result = await db.execute(
            select(AIAction).where(AIAction.id == action_id)
        )
        action = result.scalar_one_or_none()
        if not action:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Action not found",
            )
        return action
