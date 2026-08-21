import uuid
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import select, func, and_, case, cast, Float
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transaction import Transaction
from app.models.refund import Refund


class AnalyticsService:
    @staticmethod
    async def get_revenue_metrics(
        db: AsyncSession,
        merchant_id: uuid.UUID,
        period: str = "daily",
        days: int = 30,
    ) -> dict:
        cutoff = datetime.utcnow() - timedelta(days=days)

        base_query = select(Transaction).where(
            and_(
                Transaction.merchant_id == merchant_id,
                Transaction.created_at >= cutoff,
            )
        )
        result = await db.execute(base_query)
        transactions = list(result.scalars().all())

        successful = [t for t in transactions if t.status == "captured"]
        failed = [t for t in transactions if t.status == "failed"]
        total = len(transactions)

        total_revenue = sum(Decimal(str(t.amount)) for t in successful)
        success_count = len(successful)
        failure_count = len(failed)
        success_rate = (Decimal(success_count) / Decimal(total) * 100).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        ) if total > 0 else Decimal("0.00")
        avg_transaction_value = (total_revenue / Decimal(success_count)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        ) if success_count > 0 else Decimal("0.00")

        refund_result = await db.execute(
            select(func.coalesce(func.sum(Refund.amount), 0)).where(
                and_(
                    Refund.merchant_id == merchant_id,
                    Refund.created_at >= cutoff,
                    Refund.status == "processed",
                )
            )
        )
        total_refunds = Decimal(str(refund_result.scalar() or 0))
        refund_rate = (total_refunds / total_revenue * 100).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        ) if total_revenue > 0 else Decimal("0.00")

        return {
            "total_revenue": float(total_revenue),
            "success_count": success_count,
            "failure_count": failure_count,
            "total_count": total,
            "success_rate": float(success_rate),
            "avg_transaction_value": float(avg_transaction_value),
            "total_refunds": float(total_refunds),
            "refund_rate": float(refund_rate),
            "period_days": days,
        }

    @staticmethod
    async def get_revenue_trend(
        db: AsyncSession,
        merchant_id: uuid.UUID,
        days: int = 30,
    ) -> list[dict]:
        cutoff = datetime.utcnow() - timedelta(days=days)

        result = await db.execute(
            select(Transaction).where(
                and_(
                    Transaction.merchant_id == merchant_id,
                    Transaction.created_at >= cutoff,
                    Transaction.status == "captured",
                )
            ).order_by(Transaction.created_at.asc())
        )
        transactions = list(result.scalars().all())

        daily_revenue: dict[str, Decimal] = {}
        daily_transactions: dict[str, int] = {}
        for t in transactions:
            day_key = t.created_at.strftime("%Y-%m-%d")
            daily_revenue[day_key] = daily_revenue.get(day_key, Decimal("0")) + Decimal(
                str(t.amount)
            )
            daily_transactions[day_key] = daily_transactions.get(day_key, 0) + 1

        trend = []
        for i in range(days):
            day = (datetime.utcnow() - timedelta(days=days - 1 - i)).strftime("%Y-%m-%d")
            trend.append({
                "date": day,
                "revenue": float(daily_revenue.get(day, Decimal("0"))),
                "transactions": daily_transactions.get(day, 0),
            })

        return trend

    @staticmethod
    async def get_payment_method_breakdown(
        db: AsyncSession,
        merchant_id: uuid.UUID,
        days: int = 30,
    ) -> list[dict]:
        cutoff = datetime.utcnow() - timedelta(days=days)

        result = await db.execute(
            select(Transaction).where(
                and_(
                    Transaction.merchant_id == merchant_id,
                    Transaction.created_at >= cutoff,
                )
            )
        )
        transactions = list(result.scalars().all())

        methods: dict[str, dict] = {}
        for t in transactions:
            pm = t.payment_method
            if pm not in methods:
                methods[pm] = {"count": 0, "success": 0, "revenue": Decimal("0")}
            methods[pm]["count"] += 1
            if t.status == "captured":
                methods[pm]["success"] += 1
                methods[pm]["revenue"] += Decimal(str(t.amount))

        breakdown = []
        for method, data in methods.items():
            count = data["count"]
            success_rate = (
                (Decimal(data["success"]) / Decimal(count) * 100).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
                if count > 0
                else Decimal("0.00")
            )
            breakdown.append({
                "method": method,
                "count": count,
                "revenue": float(data["revenue"]),
                "success_rate": float(success_rate),
            })

        return sorted(breakdown, key=lambda x: x["revenue"], reverse=True)

    @staticmethod
    async def compare_periods(
        db: AsyncSession,
        merchant_id: uuid.UUID,
        current_start: datetime,
        current_end: datetime,
        prev_start: datetime,
        prev_end: datetime,
    ) -> dict:
        async def _get_period_stats(start: datetime, end: datetime) -> dict:
            result = await db.execute(
                select(Transaction).where(
                    and_(
                        Transaction.merchant_id == merchant_id,
                        Transaction.created_at >= start,
                        Transaction.created_at <= end,
                    )
                )
            )
            txns = list(result.scalars().all())
            successful = [t for t in txns if t.status == "captured"]
            total = len(txns)
            revenue = sum(Decimal(str(t.amount)) for t in successful)
            return {
                "total_transactions": total,
                "successful_transactions": len(successful),
                "failed_transactions": total - len(successful),
                "total_revenue": float(revenue),
                "success_rate": float(
                    (Decimal(len(successful)) / Decimal(total) * 100).quantize(
                        Decimal("0.01"), rounding=ROUND_HALF_UP
                    )
                ) if total > 0 else 0.0,
                "avg_transaction": float(
                    (revenue / Decimal(len(successful))).quantize(
                        Decimal("0.01"), rounding=ROUND_HALF_UP
                    )
                ) if successful else 0.0,
            }

        current = await _get_period_stats(current_start, current_end)
        previous = await _get_period_stats(prev_start, prev_end)

        def _pct_change(curr: float, prev: float) -> float:
            if prev == 0:
                return 100.0 if curr > 0 else 0.0
            return round(((curr - prev) / prev) * 100, 2)

        return {
            "current_period": current,
            "previous_period": previous,
            "changes": {
                "revenue_change_pct": _pct_change(
                    current["total_revenue"], previous["total_revenue"]
                ),
                "transaction_change_pct": _pct_change(
                    current["total_transactions"], previous["total_transactions"]
                ),
                "success_rate_change": round(
                    current["success_rate"] - previous["success_rate"], 2
                ),
            },
        }

    @staticmethod
    async def get_dashboard_summary(
        db: AsyncSession,
        merchant_id: uuid.UUID,
    ) -> dict:
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)

        async def _period_stats(start: datetime, end: datetime) -> dict:
            result = await db.execute(
                select(Transaction).where(
                    and_(
                        Transaction.merchant_id == merchant_id,
                        Transaction.created_at >= start,
                        Transaction.created_at <= end,
                    )
                )
            )
            txns = list(result.scalars().all())
            successful = [t for t in txns if t.status == "captured"]
            revenue = sum(Decimal(str(t.amount)) for t in successful)
            return {
                "revenue": float(revenue),
                "total": len(txns),
                "successful": len(successful),
                "failed": len(txns) - len(successful),
            }

        today_stats = await _period_stats(today, today + timedelta(days=1))
        week_stats = await _period_stats(week_ago, today + timedelta(days=1))
        month_stats = await _period_stats(month_ago, today + timedelta(days=1))

        prev_month_start = month_ago - timedelta(days=30)
        prev_month_stats = await _period_stats(prev_month_start, month_ago)

        revenue_change = (
            round(
                ((month_stats["revenue"] - prev_month_stats["revenue"])
                 / prev_month_stats["revenue"]) * 100, 2
            )
            if prev_month_stats["revenue"] > 0
            else 0.0
        )

        return {
            "today": today_stats,
            "this_week": week_stats,
            "this_month": month_stats,
            "revenue_change_pct": revenue_change,
            "active_today": today_stats["total"],
        }
