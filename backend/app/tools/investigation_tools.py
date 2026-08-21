"""
Investigation-specific tools for PayPilot AI agent.

These tools power the core agentic investigation loop:
OBSERVE → DETECT → INVESTIGATE → QUANTIFY → RECOMMEND
"""
import uuid
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.tools.base import BaseTool, ActionClass
from app.models.transaction import Transaction
from app.services.recovery_policy import evaluate_transaction, ESTIMATED_RETRY_SUCCESS_RATE, get_policy_summary


class GetFailureBreakdownByMethodTool(BaseTool):
    name = "get_failure_breakdown_by_method"
    description = (
        "Get a detailed breakdown of payment failures grouped by payment method. "
        "Compares current failure rates against historical baseline. "
        "Use this to identify which payment method is causing elevated failures and "
        "quantify the deviation from normal. Essential for root cause analysis."
    )
    parameters = {
        "type": "object",
        "properties": {
            "days": {
                "type": "integer",
                "description": "Current period in days to analyze (default 3 for recent spike analysis)",
            },
            "baseline_days": {
                "type": "integer",
                "description": "Historical baseline period in days (default 30)",
            },
        },
        "required": [],
    }
    action_class = ActionClass.READ_ONLY

    async def execute(
        self, db: AsyncSession, merchant_id: uuid.UUID, **kwargs
    ) -> dict:
        days = kwargs.get("days", 3)
        baseline_days = kwargs.get("baseline_days", 30)

        now = datetime.utcnow()
        current_cutoff = now - timedelta(days=days)
        baseline_cutoff = now - timedelta(days=baseline_days)

        # Current period transactions
        current_result = await db.execute(
            select(Transaction).where(
                and_(
                    Transaction.merchant_id == merchant_id,
                    Transaction.created_at >= current_cutoff,
                )
            )
        )
        current_txns = list(current_result.scalars().all())

        # Baseline period transactions (excluding current period to avoid overlap)
        baseline_result = await db.execute(
            select(Transaction).where(
                and_(
                    Transaction.merchant_id == merchant_id,
                    Transaction.created_at >= baseline_cutoff,
                    Transaction.created_at < current_cutoff,
                )
            )
        )
        baseline_txns = list(baseline_result.scalars().all())

        def compute_by_method(txns: list) -> dict:
            by_method: dict[str, dict] = {}
            for t in txns:
                pm = t.payment_method
                if pm not in by_method:
                    by_method[pm] = {"total": 0, "failed": 0, "amount_lost": Decimal("0"), "failure_codes": {}}
                by_method[pm]["total"] += 1
                if t.status == "failed":
                    by_method[pm]["failed"] += 1
                    by_method[pm]["amount_lost"] += Decimal(str(t.amount))
                    code = t.failure_code or "unknown"
                    by_method[pm]["failure_codes"][code] = by_method[pm]["failure_codes"].get(code, 0) + 1
            return by_method

        current_by_method = compute_by_method(current_txns)
        baseline_by_method = compute_by_method(baseline_txns)

        methods = []
        for method, curr in current_by_method.items():
            curr_rate = (curr["failed"] / curr["total"] * 100) if curr["total"] > 0 else 0
            base = baseline_by_method.get(method, {"total": 0, "failed": 0})
            base_rate = (base["failed"] / base["total"] * 100) if base["total"] > 0 else 0
            change_pct = curr_rate - base_rate

            # Find top failure code in current period
            top_code = max(curr["failure_codes"].items(), key=lambda x: x[1], default=("N/A", 0))

            methods.append({
                "method": method,
                "current_total": curr["total"],
                "current_failed": curr["failed"],
                "failure_rate": round(curr_rate, 2),
                "baseline_failure_rate": round(base_rate, 2),
                "rate_change": round(change_pct, 2),
                "amount_at_risk": float(curr["amount_lost"]),
                "top_failure_code": top_code[0],
                "top_failure_code_count": top_code[1],
                "failure_codes": curr["failure_codes"],
                "is_elevated": change_pct > 1.5,  # > 1.5% above baseline
            })

        methods.sort(key=lambda m: m["rate_change"], reverse=True)

        elevated = [m for m in methods if m["is_elevated"]]
        total_amount_at_risk = sum(m["amount_at_risk"] for m in methods)

        return {
            "analysis_period_days": days,
            "baseline_period_days": baseline_days,
            "methods": methods,
            "elevated_methods": elevated,
            "total_amount_at_risk": round(total_amount_at_risk, 2),
            "most_impacted_method": methods[0]["method"] if methods else None,
        }


class GetRecoverableTransactionsTool(BaseTool):
    name = "get_recoverable_transactions"
    description = (
        "Identify failed transactions that are eligible for Smart Retry based on the "
        "PayPilot Recovery Policy. The policy engine deterministically evaluates each "
        "transaction — the AI does not override eligibility decisions. "
        "Returns eligible transactions with recovery estimates. "
        "Use this before recommending any recovery action."
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
                "description": "Filter by payment method (e.g. 'upi', 'card') — leave empty for all methods",
            },
            "failure_code": {
                "type": "string",
                "description": "Filter by specific failure code (e.g. 'upi_timeout') — leave empty for all",
            },
        },
        "required": [],
    }
    action_class = ActionClass.READ_ONLY

    async def execute(
        self, db: AsyncSession, merchant_id: uuid.UUID, **kwargs
    ) -> dict:
        days = kwargs.get("days", 7)
        payment_method_filter = kwargs.get("payment_method")
        failure_code_filter = kwargs.get("failure_code")
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
            select(Transaction).where(and_(*conditions)).order_by(Transaction.created_at.desc())
        )
        all_failed = list(result.scalars().all())

        eligible = []
        ineligible = []
        for t in all_failed:
            decision = evaluate_transaction(t)
            entry = {
                "id": str(t.id),
                "amount": float(Decimal(str(t.amount))),
                "payment_method": t.payment_method,
                "failure_code": t.failure_code,
                "failure_reason": t.failure_reason,
                "created_at": t.created_at.isoformat() if t.created_at else None,
                "policy_reason": decision.reason,
                "failure_category": decision.failure_category,
            }
            if decision.eligible:
                eligible.append(entry)
            else:
                ineligible.append(entry)

        total_eligible_amount = sum(t["amount"] for t in eligible)
        estimated_recovery = total_eligible_amount * ESTIMATED_RETRY_SUCCESS_RATE

        # Group eligible by failure code
        by_code: dict[str, dict] = {}
        for t in eligible:
            code = t["failure_code"] or "unknown"
            if code not in by_code:
                by_code[code] = {"count": 0, "amount": 0.0}
            by_code[code]["count"] += 1
            by_code[code]["amount"] += t["amount"]

        return {
            "analysis_period_days": days,
            "total_failed": len(all_failed),
            "eligible_count": len(eligible),
            "ineligible_count": len(ineligible),
            "total_eligible_amount": round(total_eligible_amount, 2),
            "estimated_recovery_amount": round(estimated_recovery, 2),
            "estimated_recovery_rate_pct": int(ESTIMATED_RETRY_SUCCESS_RATE * 100),
            "by_failure_code": [
                {"code": code, "count": v["count"], "amount": round(v["amount"], 2)}
                for code, v in sorted(by_code.items(), key=lambda x: x[1]["count"], reverse=True)
            ],
            "eligible_transactions": eligible[:50],  # Return first 50 for display
            "policy": get_policy_summary(),
        }


class VerifyRecoveryResultTool(BaseTool):
    name = "verify_recovery_result"
    description = (
        "Verify the outcome of a completed recovery action by comparing before/after metrics. "
        "Calculates the actual improvement in success rate and amount recovered. "
        "Use this after a recovery action has been executed to confirm the impact."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action_id": {
                "type": "string",
                "description": "The ID of the executed AIAction to verify",
            },
            "comparison_days": {
                "type": "integer",
                "description": "Days to compare for before/after metrics (default 7)",
            },
        },
        "required": ["action_id"],
    }
    action_class = ActionClass.READ_ONLY

    async def execute(
        self, db: AsyncSession, merchant_id: uuid.UUID, **kwargs
    ) -> dict:
        action_id_str = kwargs.get("action_id", "")
        comparison_days = kwargs.get("comparison_days", 7)

        from app.models.ai_action import AIAction
        from sqlalchemy import select

        try:
            action_id = uuid.UUID(action_id_str)
        except (ValueError, AttributeError):
            return {"success": False, "error": "Invalid action_id format"}

        action_result = await db.execute(
            select(AIAction).where(
                and_(AIAction.id == action_id, AIAction.merchant_id == merchant_id)
            )
        )
        action = action_result.scalar_one_or_none()
        if not action:
            return {"success": False, "error": "Action not found"}

        if action.execution_status != "completed":
            return {
                "success": False,
                "error": f"Action not yet completed (status: {action.execution_status})",
            }

        # Get metrics before action was created
        before_cutoff = action.created_at - timedelta(days=comparison_days)
        before_result = await db.execute(
            select(Transaction).where(
                and_(
                    Transaction.merchant_id == merchant_id,
                    Transaction.created_at >= before_cutoff,
                    Transaction.created_at < action.created_at,
                )
            )
        )
        before_txns = list(before_result.scalars().all())

        # Get metrics after execution
        after_result = await db.execute(
            select(Transaction).where(
                and_(
                    Transaction.merchant_id == merchant_id,
                    Transaction.created_at >= action.executed_at,
                )
            )
        )
        after_txns = list(after_result.scalars().all())

        def compute_stats(txns: list) -> dict:
            if not txns:
                return {"total": 0, "successful": 0, "success_rate": 0.0, "revenue": 0.0}
            successful = [t for t in txns if t.status == "captured"]
            revenue = sum(float(t.amount) for t in successful)
            return {
                "total": len(txns),
                "successful": len(successful),
                "success_rate": round(len(successful) / len(txns) * 100, 2) if txns else 0,
                "revenue": round(revenue, 2),
            }

        before_stats = compute_stats(before_txns)
        after_stats = compute_stats(after_txns)

        output = action.output_data or {}
        recovered_amount = output.get("recovered_amount_inr", 0)
        recovered_count = output.get("successfully_recovered", 0)

        return {
            "action_id": str(action.id),
            "action_type": action.action_type,
            "executed_at": action.executed_at.isoformat() if action.executed_at else None,
            "before_success_rate": before_stats["success_rate"],
            "after_success_rate": after_stats["success_rate"],
            "success_rate_improvement": round(after_stats["success_rate"] - before_stats["success_rate"], 2),
            "before_revenue": before_stats["revenue"],
            "after_revenue": after_stats["revenue"],
            "recovered_amount": float(recovered_amount),
            "recovered_count": int(recovered_count),
            "simulation_note": "⚠️ SIMULATION MODE: These figures represent simulated outcomes, not real money recovered.",
        }
