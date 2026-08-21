from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.routers.auth import get_current_user_dependency
from app.services.analytics import AnalyticsService

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])


@router.get("/metrics")
async def get_metrics(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user_dependency),
):
    return await AnalyticsService.get_revenue_metrics(
        db, current_user.merchant_id, days=days
    )


@router.get("/revenue-trend")
async def get_revenue_trend(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user_dependency),
):
    return await AnalyticsService.get_revenue_trend(
        db, current_user.merchant_id, days=days
    )


@router.get("/payment-methods")
async def get_payment_methods(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user_dependency),
):
    return await AnalyticsService.get_payment_method_breakdown(
        db, current_user.merchant_id, days=days
    )


@router.get("/compare")
async def compare_periods(
    current_start: datetime = Query(...),
    current_end: datetime = Query(...),
    previous_start: datetime = Query(..., alias="prev_start"),
    previous_end: datetime = Query(..., alias="prev_end"),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user_dependency),
):
    return await AnalyticsService.compare_periods(
        db,
        current_user.merchant_id,
        current_start,
        current_end,
        previous_start,
        previous_end,
    )


@router.get("/dashboard")
async def get_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user_dependency),
):
    return await AnalyticsService.get_dashboard_summary(db, current_user.merchant_id)
