import uuid
from decimal import Decimal

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.tools.base import BaseTool, ActionClass
from app.models.customer import Customer
from app.models.refund import Refund
from app.services.analytics import AnalyticsService
from app.services.transaction import TransactionService


class GetTransactionMetricsTool(BaseTool):
    name = "get_transaction_metrics"
    description = (
        "Get key transaction metrics for the merchant including total revenue, "
        "success rate, average transaction value, and refund rate. Use this to "
        "understand overall payment performance."
    )
    parameters = {
        "type": "object",
        "properties": {
            "period": {
                "type": "string",
                "description": "Aggregation period: 'daily', 'weekly', or 'monthly'",
                "enum": ["daily", "weekly", "monthly"],
            },
            "days": {
                "type": "integer",
                "description": "Number of days to look back (default 30)",
            },
        },
        "required": [],
    }
    action_class = ActionClass.READ_ONLY

    async def execute(
        self, db: AsyncSession, merchant_id: uuid.UUID, **kwargs
    ) -> dict:
        period = kwargs.get("period", "daily")
        days = kwargs.get("days", 30)
        return await AnalyticsService.get_revenue_metrics(
            db, merchant_id, period=period, days=days
        )


class GetFailedTransactionsTool(BaseTool):
    name = "get_failed_transactions"
    description = (
        "Get a list of recent failed transactions. Returns transaction details "
        "including amounts, failure codes, and timestamps. Use this to identify "
        "payment issues and patterns."
    )
    parameters = {
        "type": "object",
        "properties": {
            "days": {
                "type": "integer",
                "description": "Number of days to look back (default 7)",
            },
        },
        "required": [],
    }
    action_class = ActionClass.READ_ONLY

    async def execute(
        self, db: AsyncSession, merchant_id: uuid.UUID, **kwargs
    ) -> dict:
        days = kwargs.get("days", 7)
        txns = await TransactionService.get_failed_transactions(
            db, merchant_id, days=days
        )
        failed = []
        for t in txns:
            failed.append({
                "id": str(t.id),
                "amount": float(Decimal(str(t.amount))),
                "currency": t.currency,
                "payment_method": t.payment_method,
                "failure_code": t.failure_code,
                "failure_reason": t.failure_reason,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            })
        return {
            "count": len(failed),
            "days": days,
            "transactions": failed,
        }


class GetRevenueTrendTool(BaseTool):
    name = "get_revenue_trend"
    description = (
        "Get daily revenue trend over a period. Returns an array of daily revenue "
        "figures. Use this to visualize revenue patterns and identify trends."
    )
    parameters = {
        "type": "object",
        "properties": {
            "days": {
                "type": "integer",
                "description": "Number of days of trend data to return (default 30)",
            },
        },
        "required": [],
    }
    action_class = ActionClass.READ_ONLY

    async def execute(
        self, db: AsyncSession, merchant_id: uuid.UUID, **kwargs
    ) -> dict:
        days = kwargs.get("days", 30)
        trend = await AnalyticsService.get_revenue_trend(
            db, merchant_id, days=days
        )
        total_revenue = sum(day["revenue"] for day in trend)
        avg_daily = total_revenue / len(trend) if trend else 0
        max_day = max(trend, key=lambda x: x["revenue"]) if trend else None
        min_day = min(trend, key=lambda x: x["revenue"]) if trend else None
        return {
            "days": days,
            "total_revenue": round(total_revenue, 2),
            "avg_daily_revenue": round(avg_daily, 2),
            "max_revenue_day": max_day,
            "min_revenue_day": min_day,
            "trend": trend,
        }


class GetPaymentMethodBreakdownTool(BaseTool):
    name = "get_payment_method_breakdown"
    description = (
        "Get transaction breakdown by payment method. Shows count, revenue, and "
        "success rate for each payment method. Use this to understand which "
        "payment methods perform best."
    )
    parameters = {
        "type": "object",
        "properties": {
            "days": {
                "type": "integer",
                "description": "Number of days to analyze (default 30)",
            },
        },
        "required": [],
    }
    action_class = ActionClass.READ_ONLY

    async def execute(
        self, db: AsyncSession, merchant_id: uuid.UUID, **kwargs
    ) -> dict:
        days = kwargs.get("days", 30)
        breakdown = await AnalyticsService.get_payment_method_breakdown(
            db, merchant_id, days=days
        )
        return {
            "days": days,
            "methods": breakdown,
            "total_methods": len(breakdown),
        }


class GetRefundSummaryTool(BaseTool):
    name = "get_refund_summary"
    description = (
        "Get a summary of refunds for the merchant including total refunded amount, "
        "count, and a list of recent refunds with reasons. Use this to monitor "
        "refund activity and identify recurring issues."
    )
    parameters = {
        "type": "object",
        "properties": {
            "days": {
                "type": "integer",
                "description": "Number of days to look back (default 30)",
            },
        },
        "required": [],
    }
    action_class = ActionClass.READ_ONLY

    async def execute(
        self, db: AsyncSession, merchant_id: uuid.UUID, **kwargs
    ) -> dict:
        from datetime import datetime, timedelta

        days = kwargs.get("days", 30)
        cutoff = datetime.utcnow() - timedelta(days=days)

        result = await db.execute(
            select(Refund).where(
                and_(
                    Refund.merchant_id == merchant_id,
                    Refund.created_at >= cutoff,
                )
            ).order_by(Refund.created_at.desc())
        )
        refunds = list(result.scalars().all())

        total_amount = sum(Decimal(str(r.amount)) for r in refunds)
        processed = [r for r in refunds if r.status == "processed"]
        processed_amount = sum(Decimal(str(r.amount)) for r in processed)

        reasons: dict[str, int] = {}
        for r in refunds:
            reason = r.reason or "No reason provided"
            reasons[reason] = reasons.get(reason, 0) + 1

        top_reasons = sorted(reasons.items(), key=lambda x: x[1], reverse=True)[:5]

        refund_list = []
        for r in refunds[:20]:
            refund_list.append({
                "id": str(r.id),
                "transaction_id": str(r.transaction_id),
                "amount": float(Decimal(str(r.amount))),
                "status": r.status,
                "reason": r.reason,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            })

        return {
            "total_refunds": len(refunds),
            "total_refund_amount": float(total_amount),
            "processed_count": len(processed),
            "processed_amount": float(processed_amount),
            "pending_count": len(refunds) - len(processed),
            "top_reasons": [{"reason": r, "count": c} for r, c in top_reasons],
            "recent_refunds": refund_list,
        }


class GetCustomerSummaryTool(BaseTool):
    name = "get_customer_summary"
    description = (
        "Get a summary of customers for the merchant including total customer count, "
        "top customers by spend, and average spend. Use this to understand customer "
        "behavior and identify high-value customers."
    )
    parameters = {
        "type": "object",
        "properties": {},
        "required": [],
    }
    action_class = ActionClass.READ_ONLY

    async def execute(
        self, db: AsyncSession, merchant_id: uuid.UUID, **kwargs
    ) -> dict:
        result = await db.execute(
            select(Customer).where(Customer.merchant_id == merchant_id)
        )
        customers = list(result.scalars().all())

        total = len(customers)
        total_orders = sum(c.total_orders or 0 for c in customers)
        total_spent = sum(c.total_spent or 0 for c in customers)
        avg_spent = (total_spent / total) if total > 0 else 0

        top_by_spend = sorted(
            customers, key=lambda c: c.total_spent or 0, reverse=True
        )[:10]

        top_customers = []
        for c in top_by_spend:
            top_customers.append({
                "id": str(c.id),
                "name": c.name,
                "email": c.email,
                "total_orders": c.total_orders or 0,
                "total_spent": float(c.total_spent or 0),
            })

        avg_orders = (total_orders / total) if total > 0 else 0

        return {
            "total_customers": total,
            "total_orders_all_customers": total_orders,
            "total_revenue_all_customers": float(total_spent),
            "avg_revenue_per_customer": round(float(avg_spent), 2),
            "avg_orders_per_customer": round(float(avg_orders), 2),
            "top_customers_by_spend": top_customers,
        }
