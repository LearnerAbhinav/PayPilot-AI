import uuid
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transaction import Transaction
from app.models.refund import Refund
from app.models.payment_failure import PaymentFailure


import hashlib


@dataclass
class AnomalyResult:
    type: str
    severity: str
    metric: str
    current_value: float
    baseline: float
    percentage_change: float
    explanation: str
    id: str = ""
    detected_at: str = ""
    baseline_value: float = 0.0
    is_resolved: bool = False

    def __post_init__(self):
        if not self.id:
            hash_input = f"{self.type}-{self.metric}-{self.current_value}-{self.explanation}"
            self.id = f"anom-{hashlib.md5(hash_input.encode()).hexdigest()[:10]}"
        if not self.detected_at:
            self.detected_at = datetime.utcnow().isoformat()
        if not self.baseline_value:
            self.baseline_value = self.baseline


class AnomalyDetectionService:
    @staticmethod
    async def detect_anomalies(
        db: AsyncSession, merchant_id: uuid.UUID
    ) -> list[dict]:
        anomalies = []
        anomalies.extend(
            await AnomalyDetectionService.detect_revenue_anomalies(db, merchant_id)
        )
        anomalies.extend(
            await AnomalyDetectionService.detect_failure_anomalies(db, merchant_id)
        )
        anomalies.extend(
            await AnomalyDetectionService.detect_refund_anomalies(db, merchant_id)
        )
        return anomalies

    @staticmethod
    async def detect_revenue_anomalies(
        db: AsyncSession, merchant_id: uuid.UUID
    ) -> list[dict]:
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        lookback_days = 60
        cutoff = today - timedelta(days=lookback_days)

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
        for t in transactions:
            day_key = t.created_at.strftime("%Y-%m-%d")
            daily_revenue[day_key] = daily_revenue.get(day_key, Decimal("0")) + Decimal(
                str(t.amount)
            )

        all_days = [
            (today - timedelta(days=i)).strftime("%Y-%m-%d")
            for i in range(lookback_days, -1, -1)
        ]
        revenue_series = [daily_revenue.get(d, Decimal("0")) for d in all_days]

        anomalies = []
        if len(revenue_series) < 14:
            return [a.__dict__ for a in anomalies]

        import numpy as np

        arr = np.array([float(v) for v in revenue_series])
        window = 14

        for i in range(window, len(arr)):
            historical = arr[max(0, i - window) : i]
            mean = np.mean(historical)
            std = np.std(historical)
            current = arr[i]

            if std == 0:
                continue

            z_score = (current - mean) / std
            pct_change = ((current - mean) / mean * 100) if mean != 0 else 0.0

            if abs(z_score) > 2.5:
                severity = "critical" if abs(z_score) > 3.5 else "high" if abs(z_score) > 3.0 else "medium"
                direction = "spike" if z_score > 0 else "drop"
                anomalies.append(AnomalyResult(
                    type=f"revenue_{direction}",
                    severity=severity,
                    metric="daily_revenue",
                    current_value=round(current, 2),
                    baseline=round(mean, 2),
                    percentage_change=round(pct_change, 2),
                    explanation=(
                        f"Revenue {direction} detected on {all_days[i]}: "
                        f"₹{current:,.2f} vs baseline ₹{mean:,.2f} "
                        f"(z-score: {z_score:.2f}, change: {pct_change:+.1f}%)"
                    ),
                ))

        today_key = today.strftime("%Y-%m-%d")
        yesterday_key = (today - timedelta(days=1)).strftime("%Y-%m-%d")
        today_rev = daily_revenue.get(today_key, Decimal("0"))
        yesterday_rev = daily_revenue.get(yesterday_key, Decimal("0"))

        if yesterday_rev > 0:
            today_pct = float((today_rev - yesterday_rev) / yesterday_rev * 100)
            if abs(today_pct) > 50:
                anomalies.append(AnomalyResult(
                    type="revenue_today_spike" if today_pct > 0 else "revenue_today_drop",
                    severity="high",
                    metric="today_vs_yesterday",
                    current_value=float(today_rev),
                    baseline=float(yesterday_rev),
                    percentage_change=round(today_pct, 2),
                    explanation=(
                        f"Today's revenue ({today_rev}) is {today_pct:+.1f}% "
                        f"compared to yesterday ({yesterday_rev})"
                    ),
                ))

        return [a.__dict__ for a in anomalies]

    @staticmethod
    async def detect_failure_anomalies(
        db: AsyncSession, merchant_id: uuid.UUID
    ) -> list[dict]:
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        lookback_days = 60
        cutoff = today - timedelta(days=lookback_days)

        result = await db.execute(
            select(Transaction).where(
                and_(
                    Transaction.merchant_id == merchant_id,
                    Transaction.created_at >= cutoff,
                )
            ).order_by(Transaction.created_at.asc())
        )
        transactions = list(result.scalars().all())

        daily_total: dict[str, int] = {}
        daily_failed: dict[str, int] = {}
        for t in transactions:
            day_key = t.created_at.strftime("%Y-%m-%d")
            daily_total[day_key] = daily_total.get(day_key, 0) + 1
            if t.status == "failed":
                daily_failed[day_key] = daily_failed.get(day_key, 0) + 1

        all_days = [
            (today - timedelta(days=i)).strftime("%Y-%m-%d")
            for i in range(lookback_days, -1, -1)
        ]
        failure_rates = []
        for d in all_days:
            total = daily_total.get(d, 0)
            failed = daily_failed.get(d, 0)
            failure_rates.append((failed / total * 100) if total > 0 else 0.0)

        anomalies = []
        if len(failure_rates) < 14:
            return [a.__dict__ for a in anomalies]

        import numpy as np

        arr = np.array(failure_rates)
        window = 14

        for i in range(window, len(arr)):
            historical = arr[max(0, i - window) : i]
            mean = np.mean(historical)
            std = np.std(historical)
            current = arr[i]

            if std == 0:
                continue

            z_score = (current - mean) / std
            pct_change = ((current - mean) / mean * 100) if mean != 0 else 0.0

            if z_score > 2.0:
                severity = "critical" if z_score > 3.5 else "high" if z_score > 2.8 else "medium"
                anomalies.append(AnomalyResult(
                    type="failure_rate_spike",
                    severity=severity,
                    metric="failure_rate",
                    current_value=round(current, 2),
                    baseline=round(float(mean), 2),
                    percentage_change=round(pct_change, 2),
                    explanation=(
                        f"Failure rate spike on {all_days[i]}: "
                        f"{current:.1f}% vs baseline {mean:.1f}% "
                        f"(z-score: {z_score:.2f})"
                    ),
                ))

        today_key = today.strftime("%Y-%m-%d")
        today_total = daily_total.get(today_key, 0)
        today_failed = daily_failed.get(today_key, 0)
        if today_total >= 10:
            today_rate = today_failed / today_total * 100
            hist_avg = np.mean(failure_rates[:-1]) if len(failure_rates) > 1 else 0.0
            if today_rate > hist_avg * 2 and today_rate > 15:
                anomalies.append(AnomalyResult(
                    type="today_failure_spike",
                    severity="high",
                    metric="today_failure_rate",
                    current_value=round(today_rate, 2),
                    baseline=round(float(hist_avg), 2),
                    percentage_change=round(((today_rate - hist_avg) / hist_avg * 100) if hist_avg > 0 else 100.0, 2),
                    explanation=(
                        f"Today's failure rate is {today_rate:.1f}% ({today_failed}/{today_total} "
                        f"transactions) vs historical average {hist_avg:.1f}%"
                    ),
                ))

        return [a.__dict__ for a in anomalies]

    @staticmethod
    async def detect_refund_anomalies(
        db: AsyncSession, merchant_id: uuid.UUID
    ) -> list[dict]:
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        lookback_days = 60
        cutoff = today - timedelta(days=lookback_days)

        tx_result = await db.execute(
            select(Transaction).where(
                and_(
                    Transaction.merchant_id == merchant_id,
                    Transaction.created_at >= cutoff,
                    Transaction.status == "captured",
                )
            )
        )
        transactions = list(tx_result.scalars().all())

        refund_result = await db.execute(
            select(Refund).where(
                and_(
                    Refund.merchant_id == merchant_id,
                    Refund.created_at >= cutoff,
                    Refund.status == "processed",
                )
            )
        )
        refunds = list(refund_result.scalars().all())

        daily_revenue: dict[str, Decimal] = {}
        daily_refunds: dict[str, Decimal] = {}
        for t in transactions:
            day_key = t.created_at.strftime("%Y-%m-%d")
            daily_revenue[day_key] = daily_revenue.get(day_key, Decimal("0")) + Decimal(
                str(t.amount)
            )
        for r in refunds:
            day_key = r.created_at.strftime("%Y-%m-%d")
            daily_refunds[day_key] = daily_refunds.get(day_key, Decimal("0")) + Decimal(
                str(r.amount)
            )

        all_days = [
            (today - timedelta(days=i)).strftime("%Y-%m-%d")
            for i in range(lookback_days, -1, -1)
        ]
        refund_rates = []
        for d in all_days:
            rev = daily_revenue.get(d, Decimal("0"))
            ref = daily_refunds.get(d, Decimal("0"))
            if rev > 0:
                refund_rates.append(float(ref / rev * 100))
            else:
                refund_rates.append(0.0)

        anomalies = []
        if len(refund_rates) < 14:
            return [a.__dict__ for a in anomalies]

        import numpy as np

        arr = np.array(refund_rates)
        window = 14

        for i in range(window, len(arr)):
            historical = arr[max(0, i - window) : i]
            mean = np.mean(historical)
            std = np.std(historical)
            current = arr[i]

            if std == 0:
                continue

            z_score = (current - mean) / std
            pct_change = ((current - mean) / mean * 100) if mean != 0 else 0.0

            if z_score > 2.0:
                severity = "critical" if z_score > 3.5 else "high" if z_score > 2.8 else "medium"
                anomalies.append(AnomalyResult(
                    type="refund_rate_spike",
                    severity=severity,
                    metric="refund_rate",
                    current_value=round(current, 2),
                    baseline=round(float(mean), 2),
                    percentage_change=round(pct_change, 2),
                    explanation=(
                        f"Refund rate spike on {all_days[i]}: "
                        f"{current:.1f}% vs baseline {mean:.1f}% "
                        f"(z-score: {z_score:.2f})"
                    ),
                ))

        total_refund_amount = sum(Decimal(str(r.amount)) for r in refunds)
        total_revenue_amount = sum(Decimal(str(t.amount)) for t in transactions)
        overall_rate = (
            float(total_refund_amount / total_revenue_amount * 100)
            if total_revenue_amount > 0
            else 0.0
        )
        if overall_rate > 10:
            anomalies.append(AnomalyResult(
                type="high_overall_refund_rate",
                severity="high",
                metric="overall_refund_rate",
                current_value=round(overall_rate, 2),
                baseline=5.0,
                percentage_change=round(overall_rate - 5.0, 2),
                explanation=(
                    f"Overall refund rate is {overall_rate:.1f}%, "
                    f"exceeding the recommended threshold of 5%"
                ),
            ))

        return [a.__dict__ for a in anomalies]
