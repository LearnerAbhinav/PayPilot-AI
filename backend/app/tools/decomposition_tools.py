"""
PayPilot AI - Specialized Revenue & Financial Decomposition Tools

Implements mathematically rigorous decomposition for financial operations investigations:
Revenue Drop -> Volume vs ATV -> Success Rate -> Payment Method Health -> Failure Reasons -> Financial Impact -> Recovery Opportunity
"""
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.tools.base import BaseTool, ActionClass
from app.models.transaction import Transaction
from app.services.recovery_policy import (
    evaluate_transaction,
    ESTIMATED_RETRY_SUCCESS_RATE,
    get_policy_summary,
)


class ComparePeriodsTool(BaseTool):
    name = "compare_periods"
    description = (
        "Decompose and compare revenue performance between current period and baseline period. "
        "Calculates revenue change (%), transaction volume change (%), average transaction value (ATV) change (%), "
        "and payment success/failure rates. Identifies whether a revenue drop is driven by volume, ATV, or payment failures. "
        "MUST be the first tool called when investigating any revenue drop or top-line anomaly."
    )
    parameters = {
        "type": "object",
        "properties": {
            "days": {
                "type": "integer",
                "description": "Current period in days to analyze (default 7)",
            },
            "baseline_days": {
                "type": "integer",
                "description": "Baseline period in days (default 7, immediately preceding current period)",
            },
        },
        "required": [],
    }
    action_class = ActionClass.READ_ONLY

    async def execute(
        self, db: AsyncSession, merchant_id: uuid.UUID, **kwargs
    ) -> dict:
        days = kwargs.get("days", 7)
        baseline_days = kwargs.get("baseline_days", 7)

        now = datetime.utcnow()
        current_start = now - timedelta(days=days)
        baseline_start = current_start - timedelta(days=baseline_days)

        # Current period
        current_res = await db.execute(
            select(Transaction).where(
                and_(
                    Transaction.merchant_id == merchant_id,
                    Transaction.created_at >= current_start,
                )
            )
        )
        current_txns = list(current_res.scalars().all())

        # Baseline period
        baseline_res = await db.execute(
            select(Transaction).where(
                and_(
                    Transaction.merchant_id == merchant_id,
                    Transaction.created_at >= baseline_start,
                    Transaction.created_at < current_start,
                )
            )
        )
        baseline_txns = list(baseline_res.scalars().all())

        def analyze_period(txns: list) -> dict:
            total_count = len(txns)
            successful = [t for t in txns if t.status == "captured"]
            failed = [t for t in txns if t.status == "failed"]
            revenue = sum(Decimal(str(t.amount)) for t in successful)
            failed_amount = sum(Decimal(str(t.amount)) for t in failed)
            
            successful_count = len(successful)
            failed_count = len(failed)
            atv = (revenue / Decimal(str(successful_count))) if successful_count > 0 else Decimal("0")
            success_rate = (successful_count / total_count * 100) if total_count > 0 else 0.0
            failure_rate = (failed_count / total_count * 100) if total_count > 0 else 0.0

            return {
                "total_count": total_count,
                "successful_count": successful_count,
                "failed_count": failed_count,
                "revenue": float(revenue),
                "failed_amount": float(failed_amount),
                "atv": float(atv),
                "success_rate": round(success_rate, 2),
                "failure_rate": round(failure_rate, 2),
            }

        curr = analyze_period(current_txns)
        base = analyze_period(baseline_txns)

        # Calculate deltas
        rev_change_amt = curr["revenue"] - base["revenue"]
        rev_change_pct = ((rev_change_amt / base["revenue"]) * 100) if base["revenue"] > 0 else 0.0
        
        vol_change_pct = (
            ((curr["total_count"] - base["total_count"]) / base["total_count"] * 100)
            if base["total_count"] > 0 else 0.0
        )
        
        atv_change_pct = (
            ((curr["atv"] - base["atv"]) / base["atv"] * 100)
            if base["atv"] > 0 else 0.0
        )

        failure_rate_change_pp = curr["failure_rate"] - base["failure_rate"]
        success_rate_change_pp = curr["success_rate"] - base["success_rate"]

        # Determine primary decomposition driver
        drivers = []
        if failure_rate_change_pp > 3.0:
            drivers.append("payment_failure_surge")
        if vol_change_pct < -5.0:
            drivers.append("transaction_volume_drop")
        if atv_change_pct < -5.0:
            drivers.append("atv_drop")

        primary_driver = "mixed_factors"
        if len(drivers) == 1:
            primary_driver = drivers[0]
        elif "payment_failure_surge" in drivers and failure_rate_change_pp > 10.0:
            primary_driver = "payment_failure_surge"
        elif not drivers:
            primary_driver = "stable_within_thresholds"

        return {
            "period_days": days,
            "baseline_days": baseline_days,
            "current_period": {
                "revenue": curr["revenue"],
                "total_volume": curr["total_count"],
                "successful_volume": curr["successful_count"],
                "failed_volume": curr["failed_count"],
                "atv": curr["atv"],
                "success_rate": curr["success_rate"],
                "failure_rate": curr["failure_rate"],
            },
            "baseline_period": {
                "revenue": base["revenue"],
                "total_volume": base["total_count"],
                "successful_volume": base["successful_count"],
                "failed_volume": base["failed_count"],
                "atv": base["atv"],
                "success_rate": base["success_rate"],
                "failure_rate": base["failure_rate"],
            },
            "decomposition": {
                "revenue_change_amount": round(rev_change_amt, 2),
                "revenue_change_pct": round(rev_change_pct, 2),
                "volume_change_pct": round(vol_change_pct, 2),
                "atv_change_pct": round(atv_change_pct, 2),
                "failure_rate_change_pp": round(failure_rate_change_pp, 2),
                "success_rate_change_pp": round(success_rate_change_pp, 2),
                "primary_driver": primary_driver,
                "unrealized_failed_revenue": round(curr["failed_amount"], 2),
            },
        }


class GetPaymentMethodHealthTool(BaseTool):
    name = "get_payment_method_health"
    description = (
        "Analyze the health and failure rate deviations across payment methods (UPI, Card, Netbanking, Wallet, EMI). "
        "Compares current failure rate against baseline to isolate specifically which payment method is abnormal. "
        "Call this immediately after compare_periods if payment failures or revenue dropped."
    )
    parameters = {
        "type": "object",
        "properties": {
            "days": {
                "type": "integer",
                "description": "Current period in days (default 7)",
            },
            "baseline_days": {
                "type": "integer",
                "description": "Baseline period in days (default 7)",
            },
        },
        "required": [],
    }
    action_class = ActionClass.READ_ONLY

    async def execute(
        self, db: AsyncSession, merchant_id: uuid.UUID, **kwargs
    ) -> dict:
        days = kwargs.get("days", 7)
        baseline_days = kwargs.get("baseline_days", 7)

        now = datetime.utcnow()
        current_start = now - timedelta(days=days)
        baseline_start = current_start - timedelta(days=baseline_days)

        current_res = await db.execute(
            select(Transaction).where(
                and_(
                    Transaction.merchant_id == merchant_id,
                    Transaction.created_at >= current_start,
                )
            )
        )
        current_txns = list(current_res.scalars().all())

        baseline_res = await db.execute(
            select(Transaction).where(
                and_(
                    Transaction.merchant_id == merchant_id,
                    Transaction.created_at >= baseline_start,
                    Transaction.created_at < current_start,
                )
            )
        )
        baseline_txns = list(baseline_res.scalars().all())

        def compute_methods(txns: list) -> dict:
            stats: dict[str, dict] = {}
            for t in txns:
                pm = (t.payment_method or "unknown").lower()
                if pm not in stats:
                    stats[pm] = {"total": 0, "failed": 0, "failed_amount": Decimal("0")}
                stats[pm]["total"] += 1
                if t.status == "failed":
                    stats[pm]["failed"] += 1
                    stats[pm]["failed_amount"] += Decimal(str(t.amount))
            return stats

        curr_methods = compute_methods(current_txns)
        base_methods = compute_methods(baseline_txns)

        method_reports = []
        for pm, curr in curr_methods.items():
            curr_rate = (curr["failed"] / curr["total"] * 100) if curr["total"] > 0 else 0.0
            base = base_methods.get(pm, {"total": 0, "failed": 0, "failed_amount": Decimal("0")})
            base_rate = (base["failed"] / base["total"] * 100) if base["total"] > 0 else 0.0
            rate_delta = curr_rate - base_rate

            status = "HEALTHY"
            if rate_delta > 15.0 or curr_rate > 35.0:
                status = "CRITICAL_FAILURE_SURGE"
            elif rate_delta > 3.0:
                status = "ELEVATED_FAILURES"

            method_reports.append({
                "payment_method": pm.upper(),
                "current_total": curr["total"],
                "current_failed": curr["failed"],
                "current_failure_rate_pct": round(curr_rate, 2),
                "baseline_failure_rate_pct": round(base_rate, 2),
                "failure_rate_change_pp": round(rate_delta, 2),
                "amount_at_risk": float(curr["failed_amount"]),
                "status": status,
            })

        method_reports.sort(key=lambda x: x["failure_rate_change_pp"], reverse=True)
        critical_methods = [m for m in method_reports if m["status"] in ("CRITICAL_FAILURE_SURGE", "ELEVATED_FAILURES")]

        return {
            "methods_analyzed": len(method_reports),
            "methods": method_reports,
            "abnormal_methods": critical_methods,
            "primary_offending_method": method_reports[0]["payment_method"] if method_reports else None,
            "total_at_risk_amount": round(sum(m["amount_at_risk"] for m in method_reports), 2),
        }


class GetFailureReasonDistributionTool(BaseTool):
    name = "get_failure_reason_distribution"
    description = (
        "Get the exact distribution of failure codes and gateway error messages for a specific payment method "
        "or across all failed transactions. Categorizes failures into transient (retryable) vs permanent (customer action required). "
        "Use this after identifying an abnormal payment method to establish verified root cause."
    )
    parameters = {
        "type": "object",
        "properties": {
            "payment_method": {
                "type": "string",
                "description": "Specific payment method to analyze (e.g. 'upi', 'card', 'wallet') — leave empty for all",
            },
            "days": {
                "type": "integer",
                "description": "Number of days to analyze (default 7)",
            },
        },
        "required": [],
    }
    action_class = ActionClass.READ_ONLY

    async def execute(
        self, db: AsyncSession, merchant_id: uuid.UUID, **kwargs
    ) -> dict:
        pm_filter = kwargs.get("payment_method")
        days = kwargs.get("days", 7)
        cutoff = datetime.utcnow() - timedelta(days=days)

        conditions = [
            Transaction.merchant_id == merchant_id,
            Transaction.status == "failed",
            Transaction.created_at >= cutoff,
        ]
        if pm_filter:
            conditions.append(Transaction.payment_method == pm_filter.lower())

        res = await db.execute(select(Transaction).where(and_(*conditions)))
        failed_txns = list(res.scalars().all())

        if not failed_txns:
            return {
                "payment_method_filter": pm_filter,
                "total_failures": 0,
                "failure_reasons": [],
                "primary_failure_code": None,
            }

        by_code: dict[str, dict] = {}
        for t in failed_txns:
            code = (t.failure_code or "unknown").lower()
            decision = evaluate_transaction(t)
            
            if code not in by_code:
                by_code[code] = {
                    "count": 0,
                    "amount": Decimal("0"),
                    "category": decision.failure_category,
                    "is_retryable": decision.eligible,
                    "sample_reasons": set(),
                }
            by_code[code]["count"] += 1
            by_code[code]["amount"] += Decimal(str(t.amount))
            if t.failure_reason:
                by_code[code]["sample_reasons"].add(t.failure_reason)

        total_count = len(failed_txns)
        reasons_list = []
        for code, info in by_code.items():
            pct = (info["count"] / total_count * 100) if total_count > 0 else 0.0
            reasons_list.append({
                "failure_code": code,
                "count": info["count"],
                "percentage_of_failures": round(pct, 2),
                "amount_lost": float(info["amount"]),
                "classification": "transient_network_or_gateway" if info["is_retryable"] else "permanent_declined_or_funds",
                "is_retryable": info["is_retryable"],
                "description": list(info["sample_reasons"])[0] if info["sample_reasons"] else code,
            })

        reasons_list.sort(key=lambda x: x["count"], reverse=True)
        primary = reasons_list[0] if reasons_list else None

        return {
            "payment_method": pm_filter.upper() if pm_filter else "ALL",
            "total_failures": total_count,
            "total_amount_lost": round(sum(r["amount_lost"] for r in reasons_list), 2),
            "primary_failure_code": primary["failure_code"] if primary else None,
            "primary_failure_percentage": primary["percentage_of_failures"] if primary else 0.0,
            "failure_reasons": reasons_list[:6],
        }


class CalculateFinancialImpactTool(BaseTool):
    name = "calculate_financial_impact"
    description = (
        "Calculate the total financial impact of an anomaly or failure surge. "
        "Separates realized revenue vs unrealized failed revenue, and details the revenue variance. "
        "Grounds impact figures in real database sums."
    )
    parameters = {
        "type": "object",
        "properties": {
            "days": {
                "type": "integer",
                "description": "Period in days to analyze (default 7)",
            },
        },
        "required": [],
    }
    action_class = ActionClass.READ_ONLY

    async def execute(
        self, db: AsyncSession, merchant_id: uuid.UUID, **kwargs
    ) -> dict:
        days = kwargs.get("days", 7)
        now = datetime.utcnow()
        current_start = now - timedelta(days=days)
        baseline_start = current_start - timedelta(days=days)

        curr_res = await db.execute(
            select(Transaction).where(
                and_(
                    Transaction.merchant_id == merchant_id,
                    Transaction.created_at >= current_start,
                )
            )
        )
        curr_txns = list(curr_res.scalars().all())

        base_res = await db.execute(
            select(Transaction).where(
                and_(
                    Transaction.merchant_id == merchant_id,
                    Transaction.created_at >= baseline_start,
                    Transaction.created_at < current_start,
                )
            )
        )
        base_txns = list(base_res.scalars().all())

        curr_captured = [t for t in curr_txns if t.status == "captured"]
        curr_failed = [t for t in curr_txns if t.status == "failed"]
        base_captured = [t for t in base_txns if t.status == "captured"]

        curr_rev = sum(Decimal(str(t.amount)) for t in curr_captured)
        base_rev = sum(Decimal(str(t.amount)) for t in base_captured)
        failed_volume = sum(Decimal(str(t.amount)) for t in curr_failed)

        rev_gap = float(base_rev - curr_rev)

        return {
            "analysis_window_days": days,
            "current_revenue": float(curr_rev),
            "baseline_revenue": float(base_rev),
            "revenue_decline_amount": round(rev_gap, 2) if rev_gap > 0 else 0.0,
            "failed_transaction_volume": float(failed_volume),
            "failed_transaction_count": len(curr_failed),
            "total_unrealized_revenue": round(float(failed_volume), 2),
        }


class CalculateRecoverableRevenueTool(BaseTool):
    name = "calculate_recoverable_revenue"
    description = (
        "Deterministically calculate the exact recoverable revenue from failed transactions using the "
        "PayPilot Recovery Policy Engine. Returns eligible transactions, policy constraints, and guaranteed calculations. "
        "MUST be called before proposing any recovery action."
    )
    parameters = {
        "type": "object",
        "properties": {
            "days": {
                "type": "integer",
                "description": "Period in days (default 7)",
            },
            "payment_method": {
                "type": "string",
                "description": "Filter by payment method (e.g. 'upi')",
            },
        },
        "required": [],
    }
    action_class = ActionClass.READ_ONLY

    async def execute(
        self, db: AsyncSession, merchant_id: uuid.UUID, **kwargs
    ) -> dict:
        days = kwargs.get("days", 7)
        pm = kwargs.get("payment_method")
        cutoff = datetime.utcnow() - timedelta(days=days)

        conditions = [
            Transaction.merchant_id == merchant_id,
            Transaction.status == "failed",
            Transaction.created_at >= cutoff,
        ]
        if pm:
            conditions.append(Transaction.payment_method == pm.lower())

        res = await db.execute(select(Transaction).where(and_(*conditions)))
        failed = list(res.scalars().all())

        eligible = [t for t in failed if evaluate_transaction(t).eligible]
        eligible_amount = sum(Decimal(str(t.amount)) for t in eligible)
        projected_recovery = eligible_amount * Decimal(str(ESTIMATED_RETRY_SUCCESS_RATE))

        eligible_details = [
            {
                "transaction_id": str(t.id),
                "amount": float(t.amount),
                "failure_code": t.failure_code,
                "payment_method": t.payment_method,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t in eligible
        ]

        return {
            "total_failed_analyzed": len(failed),
            "eligible_for_smart_retry": len(eligible),
            "ineligible_count": len(failed) - len(eligible),
            "eligible_amount_inr": float(eligible_amount),
            "projected_recovery_inr": round(float(projected_recovery), 2),
            "simulated_recovery_rate_pct": int(ESTIMATED_RETRY_SUCCESS_RATE * 100),
            "policy": get_policy_summary(),
            "eligible_details": eligible_details,
        }

