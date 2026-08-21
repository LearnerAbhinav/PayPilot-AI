import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.tools.base import BaseTool, ActionClass
from app.services.forecast import ForecastService


class ForecastCashFlowTool(BaseTool):
    name = "forecast_cash_flow"
    description = (
        "Generate a cash flow forecast for the merchant. Predicts daily inflows, "
        "outflows, and balance over the forecast horizon. Includes confidence levels "
        "and risk assessment. Use this for financial planning and early warnings."
    )
    parameters = {
        "type": "object",
        "properties": {
            "days": {
                "type": "integer",
                "description": "Number of days to forecast ahead (default 7, max 30)",
            },
        },
        "required": [],
    }
    action_class = ActionClass.READ_ONLY

    async def execute(
        self, db: AsyncSession, merchant_id: uuid.UUID, **kwargs
    ) -> dict:
        days = kwargs.get("days", 7)
        days = min(max(days, 1), 30)
        forecast = await ForecastService.forecast_cash_flow(db, merchant_id, days=days)

        critical_days = [
            d for d in forecast.get("daily_predictions", [])
            if d.get("risk_level") in ("critical", "high")
        ]

        return {
            "current_balance": forecast["current_balance"],
            "forecast_days": forecast["forecast_days"],
            "overall_confidence": forecast["overall_confidence"],
            "overall_risk_level": forecast["overall_risk_level"],
            "critical_or_high_risk_days": critical_days,
            "daily_predictions": forecast["daily_predictions"],
            "assumptions": forecast["assumptions"],
        }
