from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.routers.auth import get_current_user_dependency
from app.services.forecast import ForecastService

router = APIRouter(prefix="/api/forecast", tags=["Forecast"])


@router.get("/cash-flow")
async def forecast_cash_flow(
    days: int = Query(7, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user_dependency),
):
    return await ForecastService.forecast_cash_flow(
        db, current_user.merchant_id, days=days
    )
