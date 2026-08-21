import uuid
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transaction import Transaction
from app.models.cash_flow import CashFlowEvent
from app.models.merchant import Merchant


class ForecastService:
    @staticmethod
    async def get_current_balance(db: AsyncSession, merchant_id: uuid.UUID) -> Decimal:
        result = await db.execute(
            select(Merchant.current_balance).where(Merchant.id == merchant_id)
        )
        balance = result.scalar_one_or_none()
        return Decimal(str(balance)) if balance is not None else Decimal("0")

    @staticmethod
    async def forecast_cash_flow(
        db: AsyncSession, merchant_id: uuid.UUID, days: int = 7
    ) -> dict:
        lookback = max(days * 4, 60)
        cutoff = datetime.utcnow() - timedelta(days=lookback)

        tx_result = await db.execute(
            select(Transaction).where(
                and_(
                    Transaction.merchant_id == merchant_id,
                    Transaction.created_at >= cutoff,
                )
            ).order_by(Transaction.created_at.asc())
        )
        transactions = list(tx_result.scalars().all())

        cf_result = await db.execute(
            select(CashFlowEvent).where(
                and_(
                    CashFlowEvent.merchant_id == merchant_id,
                    CashFlowEvent.created_at >= cutoff,
                )
            ).order_by(CashFlowEvent.created_at.asc())
        )
        cash_flow_events = list(cf_result.scalars().all())

        daily_inflow: dict[str, Decimal] = {}
        daily_outflow: dict[str, Decimal] = {}
        for t in transactions:
            day_key = t.created_at.strftime("%Y-%m-%d")
            if t.status == "captured":
                daily_inflow[day_key] = daily_inflow.get(day_key, Decimal("0")) + Decimal(
                    str(t.amount)
                )
        for cf in cash_flow_events:
            day_key = cf.created_at.strftime("%Y-%m-%d")
            amount = Decimal(str(cf.amount))
            if cf.type == "inflow":
                daily_inflow[day_key] = daily_inflow.get(day_key, Decimal("0")) + amount
            elif cf.type == "outflow":
                daily_outflow[day_key] = daily_outflow.get(day_key, Decimal("0")) + amount

        all_days = sorted(set(list(daily_inflow.keys()) + list(daily_outflow.keys())))
        inflow_series = [daily_inflow.get(d, Decimal("0")) for d in all_days]
        outflow_series = [daily_outflow.get(d, Decimal("0")) for d in all_days]

        def _moving_average(series: list[Decimal], window: int = 7) -> Decimal:
            if not series:
                return Decimal("0")
            w = min(window, len(series))
            recent = series[-w:]
            return sum(recent) / Decimal(len(recent))

        def _trend(series: list[Decimal], window: int = 7) -> Decimal:
            if len(series) < 2:
                return Decimal("0")
            w = min(window, len(series) - 1)
            recent = series[-w:]
            older = series[-(w + 1) : -1] if len(series) >= w + 1 else series[: len(recent) - 1]
            if not older or not recent:
                return Decimal("0")
            recent_avg = sum(recent[-len(older) :]) / Decimal(len(older))
            older_avg = sum(older) / Decimal(len(older))
            if older_avg == 0:
                return Decimal("0")
            return (recent_avg - older_avg) / Decimal(len(older))

        base_inflow = _moving_average(inflow_series)
        trend_inflow = _trend(inflow_series)
        base_outflow = _moving_average(outflow_series)
        trend_outflow = _trend(outflow_series)

        current_balance = await ForecastService.get_current_balance(db, merchant_id)

        daily_predictions = []
        running_balance = current_balance
        min_samples = 7
        confidence_factor = min(len(all_days) / 30, Decimal("1")) if all_days else Decimal("0.3")

        for i in range(1, days + 1):
            pred_date = datetime.utcnow() + timedelta(days=i)
            day_key = pred_date.strftime("%Y-%m-%d")

            predicted_inflow = (base_inflow + trend_inflow * Decimal(i)).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            predicted_outflow = (base_outflow + trend_outflow * Decimal(i)).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )

            predicted_inflow = max(predicted_inflow, Decimal("0"))
            predicted_outflow = max(predicted_outflow, Decimal("0"))

            net_flow = predicted_inflow - predicted_outflow
            running_balance = running_balance + net_flow

            if len(all_days) < min_samples:
                confidence = float(confidence_factor * Decimal("0.5"))
                risk_level = "high"
            else:
                confidence = float(confidence_factor * Decimal("0.85"))
                risk_level = "low"

                if running_balance < Decimal("0"):
                    risk_level = "critical"
                    confidence *= 0.7
                elif running_balance < current_balance * Decimal("0.2"):
                    risk_level = "high"
                    confidence *= 0.8

            daily_predictions.append({
                "date": day_key,
                "predicted_inflow": float(predicted_inflow),
                "predicted_outflow": float(predicted_outflow),
                "net_flow": float(net_flow),
                "predicted_balance": float(running_balance.quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )),
                "confidence": round(confidence, 3),
                "risk_level": risk_level,
            })

        final_confidence = (
            sum(d["confidence"] for d in daily_predictions) / len(daily_predictions)
            if daily_predictions else 0.0
        )

        return {
            "current_balance": float(current_balance),
            "forecast_days": days,
            "daily_predictions": daily_predictions,
            "overall_confidence": round(final_confidence, 3),
            "overall_risk_level": (
                "critical" if any(d["risk_level"] == "critical" for d in daily_predictions)
                else "high" if any(d["risk_level"] == "high" for d in daily_predictions)
                else "medium" if any(d["risk_level"] == "medium" for d in daily_predictions)
                else "low"
            ),
            "assumptions": [
                "Forecast uses 7-day simple moving average with trend extrapolation",
                f"Based on {len(all_days)} days of historical data",
                "Does not account for seasonality or one-time events",
                "Confidence decreases with longer forecast horizons",
                "Past performance does not guarantee future results",
            ],
        }
