from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.routers.auth import get_current_user_dependency
from app.services.anomaly import AnomalyDetectionService

router = APIRouter(prefix="/api/anomalies", tags=["Anomalies"])


@router.get("/detect")
async def detect_anomalies(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user_dependency),
):
    anomalies = await AnomalyDetectionService.detect_anomalies(
        db, current_user.merchant_id
    )
    unresolved = [a for a in anomalies if not a.get("is_resolved")]
    critical = [a for a in anomalies if a.get("severity") == "critical"]
    return {
        "items": anomalies,
        "total": len(anomalies),
        "unresolved_count": len(unresolved),
        "critical_count": len(critical),
    }


@router.get("/")
async def list_anomalies(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user_dependency),
):
    anomalies = await AnomalyDetectionService.detect_anomalies(
        db, current_user.merchant_id
    )
    unresolved = [a for a in anomalies if not a.get("is_resolved")]
    critical = [a for a in anomalies if a.get("severity") == "critical"]
    return {
        "items": anomalies,
        "total": len(anomalies),
        "unresolved_count": len(unresolved),
        "critical_count": len(critical),
    }
