import uuid
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.tools.base import BaseTool, ActionClass
from app.models.transaction import Transaction
from app.services.recovery_policy import (
    evaluate_transaction,
    ESTIMATED_RETRY_SUCCESS_RATE,
    get_policy_summary,
)


class GenerateRecoveryPlanTool(BaseTool):
    name = "generate_recovery_plan"
    description = (
        "Analyze failed transactions and generate a structured recovery plan with "
        "actionable recommendations. Estimates potential revenue recovery and identifies "
        "root causes. Use this to understand failure patterns and plan recovery strategies "
        "BEFORE creating an approval-required recovery action."
    )
    parameters = {
        "type": "object",
        "properties": {
            "days": {
                "type": "integer",
                "description": "Number of days of failed transactions to analyze (default 7)",
            },
        },
        "required": [],
    }
    action_class = ActionClass.READ_ONLY

    async def execute(
        self, db: AsyncSession, merchant_id: uuid.UUID, **kwargs
    ) -> dict:
        days = kwargs.get("days", 7)
        cutoff = datetime.utcnow() - timedelta(days=days)

        result = await db.execute(
            select(Transaction).where(
                and_(
                    Transaction.merchant_id == merchant_id,
                    Transaction.status == "failed",
                    Transaction.created_at >= cutoff,
                )
            ).order_by(Transaction.created_at.desc())
        )
        failed = list(result.scalars().all())

        if not failed:
            return {
                "total_failed": 0,
                "estimated_recovery_amount": 0,
                "failure_causes": [],
                "recommendations": [],
                "priority_actions": [],
            }

        total_failed_amount = sum(Decimal(str(t.amount)) for t in failed)

        by_method: dict[str, dict] = {}
        for t in failed:
            pm = t.payment_method
            if pm not in by_method:
                by_method[pm] = {"count": 0, "amount": Decimal("0"), "codes": {}}
            by_method[pm]["count"] += 1
            by_method[pm]["amount"] += Decimal(str(t.amount))
            code = t.failure_code or "unknown"
            by_method[pm]["codes"][code] = by_method[pm]["codes"].get(code, 0) + 1

        by_code: dict[str, int] = {}
        for t in failed:
            code = t.failure_code or "unknown"
            by_code[code] = by_code.get(code, 0) + 1

        top_codes = sorted(by_code.items(), key=lambda x: x[1], reverse=True)[:5]

        # Use policy engine to assess recoverability
        eligible = [t for t in failed if evaluate_transaction(t).eligible]
        eligible_amount = sum(Decimal(str(t.amount)) for t in eligible)
        estimated_recoverable = eligible_amount * Decimal(str(ESTIMATED_RETRY_SUCCESS_RATE))

        recommendations = []
        for code, count in top_codes:
            from app.services.recovery_policy import RETRYABLE_FAILURE_CODES, NON_RETRYABLE_CODES
            if code in RETRYABLE_FAILURE_CODES:
                recommendations.append({
                    "action": "Smart Retry — transient failure eligible for automated retry",
                    "target": f"Transactions with failure code: {code}",
                    "estimated_recovery_rate": f"{int(ESTIMATED_RETRY_SUCCESS_RATE * 100)}%",
                    "priority": "high" if count > 10 else "medium",
                    "retryable": True,
                })
            elif code in NON_RETRYABLE_CODES:
                recommendations.append({
                    "action": "Customer outreach required — permanent failure, cannot auto-retry",
                    "target": f"Transactions with failure code: {code}",
                    "estimated_recovery_rate": "0% auto / 40-60% manual",
                    "priority": "medium",
                    "retryable": False,
                })
            else:
                recommendations.append({
                    "action": f"Investigate and resolve: {code}",
                    "target": f"Transactions with failure code: {code}",
                    "estimated_recovery_rate": "Unknown",
                    "priority": "low",
                    "retryable": False,
                })

        method_breakdown = [
            {
                "method": method,
                "count": data["count"],
                "total_amount": float(data["amount"]),
                "top_failure_codes": data["codes"],
            }
            for method, data in sorted(by_method.items(), key=lambda x: x[1]["count"], reverse=True)
        ]

        return {
            "total_failed": len(failed),
            "total_failed_amount": float(total_failed_amount),
            "eligible_for_retry": len(eligible),
            "estimated_recoverable_amount": float(estimated_recoverable),
            "analysis_period_days": days,
            "failure_causes": [{"code": c, "count": n} for c, n in top_codes],
            "method_breakdown": method_breakdown,
            "recommendations": recommendations,
            "priority_actions": [r for r in recommendations if r["priority"] == "high"],
            "policy": get_policy_summary(),
        }


class SimulatePaymentRecoveryTool(BaseTool):
    name = "simulate_payment_recovery"
    description = (
        "⚠️ SIMULATION MODE — Creates a Smart Retry recovery plan for eligible failed transactions. "
        "This tool evaluates transactions against the PayPilot Recovery Policy, "
        "persists a recovery action to the database requiring HUMAN APPROVAL before execution, "
        "and returns estimated recovery figures. "
        "Use this when the user explicitly wants to create a recovery action."
    )
    parameters = {
        "type": "object",
        "properties": {
            "days": {
                "type": "integer",
                "description": "Number of days to look back for failed transactions (default 7)",
            },
            "payment_method": {
                "type": "string",
                "description": "Target specific payment method (e.g. 'upi') — leave empty for all",
            },
            "failure_code": {
                "type": "string",
                "description": "Target specific failure code (e.g. 'upi_timeout') — leave empty for all",
            },
            "max_transactions": {
                "type": "integer",
                "description": "Maximum number of transactions to include in the recovery batch (default 200)",
            },
        },
        "required": [],
    }
    action_class = ActionClass.REQUIRES_APPROVAL

    async def execute(
        self, db: AsyncSession, merchant_id: uuid.UUID, **kwargs
    ) -> dict:
        days = kwargs.get("days", 7)
        payment_method_filter = kwargs.get("payment_method")
        failure_code_filter = kwargs.get("failure_code")
        max_transactions = kwargs.get("max_transactions", 200)
        cutoff = datetime.utcnow() - timedelta(days=days)

        conditions = [
            Transaction.merchant_id == merchant_id,
            Transaction.status == "failed",
            Transaction.created_at >= cutoff,
        ]
        if payment_method_filter:
            conditions.append(Transaction.payment_method == payment_method_filter)
        if failure_code_filter:
            conditions.append(Transaction.failure_code == failure_code_filter)

        result = await db.execute(
            select(Transaction).where(and_(*conditions)).order_by(Transaction.amount.desc())
        )
        all_failed = list(result.scalars().all())

        # Apply policy engine to each transaction (deterministic — AI cannot override this)
        eligible = []
        for t in all_failed:
            decision = evaluate_transaction(t)
            if decision.eligible:
                eligible.append(t)
            if len(eligible) >= max_transactions:
                break

        if not eligible:
            return {
                "eligible_count": 0,
                "message": "No transactions eligible for Smart Retry under current recovery policy.",
                "policy": get_policy_summary(),
            }

        total_eligible_amount = sum(Decimal(str(t.amount)) for t in eligible)
        estimated_recovery = total_eligible_amount * Decimal(str(ESTIMATED_RETRY_SUCCESS_RATE))

        eligible_details = [
            {
                "id": str(t.id),
                "amount": float(Decimal(str(t.amount))),
                "currency": t.currency,
                "payment_method": t.payment_method,
                "failure_code": t.failure_code,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t in eligible[:20]  # Show first 20 in details
        ]

        # Persist the AIAction to the database (requires human approval before execution)
        from app.services.ai_action import AIActionService

        filter_desc = ""
        if payment_method_filter:
            filter_desc += f" for {payment_method_filter.upper()}"
        if failure_code_filter:
            filter_desc += f" ({failure_code_filter})"

        action = await AIActionService.create_action(
            db=db,
            merchant_id=merchant_id,
            user_id=merchant_id,  # System-initiated via agent — user_id = merchant for now
            action_data={
                "action_type": "bulk_payment_retry",
                "action_class": "requires_approval",
                "description": (
                    f"Smart Retry{filter_desc}: {len(eligible)} failed transactions "
                    f"worth ₹{total_eligible_amount:,.2f}. "
                    f"Estimated recovery: ₹{estimated_recovery:,.2f} "
                    f"({int(ESTIMATED_RETRY_SUCCESS_RATE * 100)}% simulated success rate)."
                ),
                "reason": (
                    f"PayPilot Recovery Policy identified {len(eligible)} transactions "
                    f"with retryable failure codes from the last {days} days{filter_desc}."
                ),
                "input_data": {
                    "transaction_ids": [str(t.id) for t in eligible],
                    "days": days,
                    "payment_method_filter": payment_method_filter,
                    "failure_code_filter": failure_code_filter,
                    "eligible_count": len(eligible),
                    "total_eligible_amount": float(total_eligible_amount),
                },
                "estimated_impact": float(estimated_recovery),
                "risk_level": "low",
            },
        )

        return {
            "eligible_count": len(eligible),
            "total_eligible_amount": float(total_eligible_amount),
            "estimated_recovery_amount": float(estimated_recovery),
            "estimated_recovery_rate_pct": int(ESTIMATED_RETRY_SUCCESS_RATE * 100),
            "action_id": str(action.id),
            "action_approval_status": action.approval_status,
            "transactions": eligible_details,
            "policy": get_policy_summary(),
            "message": (
                f"✅ Recovery plan created for {len(eligible)} eligible transactions. "
                f"Action ID: {action.id} — requires your approval in the Actions tab before execution. "
                f"⚠️ SIMULATION MODE: No real money will be moved."
            ),
        }
