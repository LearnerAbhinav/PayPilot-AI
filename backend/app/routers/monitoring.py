import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.database import get_db
from app.routers.auth import get_current_user_dependency
from app.services.monitoring_service import MonitoringService
from app.models.anomaly import Anomaly
from app.models.investigation import Investigation
from app.models.ai_action import AIAction

router = APIRouter(prefix="/api/monitoring", tags=["Autonomous Monitoring Engine"])


@router.post("/run")
async def run_monitoring_cycle(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user_dependency),
):
    """
    Manually trigger a full deterministic monitoring cycle.
    Evaluates telemetry, detects anomalies, spawns autonomous investigations,
    and proposes recovery actions to the Action Center.
    """
    result = await MonitoringService.run_monitoring_cycle(
        db=db,
        merchant_id=current_user.merchant_id,
        user_id=current_user.id,
    )
    return result


@router.get("/status")
async def get_monitoring_status(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user_dependency),
):
    """Get autonomous monitoring engine status and operational health metrics."""
    # Count active/unresolved anomalies
    anom_count = await db.scalar(
        select(func.count(Anomaly.id)).where(
            and_(
                Anomaly.merchant_id == current_user.merchant_id,
                Anomaly.is_resolved == False,
            )
        )
    )

    # Count investigations
    inv_count = await db.scalar(
        select(func.count(Investigation.id)).where(
            Investigation.merchant_id == current_user.merchant_id
        )
    )

    # Count pending actions
    act_count = await db.scalar(
        select(func.count(AIAction.id)).where(
            and_(
                AIAction.merchant_id == current_user.merchant_id,
                AIAction.approval_status == "pending",
            )
        )
    )

    now = datetime.utcnow()
    return {
        "status": "OPERATIONAL",
        "autonomous_mode": True,
        "actions_paused": MonitoringService.is_autonomous_paused(),
        "last_scan": now.isoformat(),
        "metrics_monitored": 42,
        "active_anomalies": anom_count or 0,
        "investigations_count": inv_count or 0,
        "pending_actions_count": act_count or 0,
        "freshness": {
            "transactions_sec": 8,
            "payment_telemetry_sec": 14,
            "cash_flow_sec": 30,
        },
        "simulation_mode": True,
    }


@router.post("/toggle-pause")
async def toggle_autonomous_actions(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user_dependency),
):
    """Emergency kill switch: toggle pause on autonomous recovery action creation."""
    current_state = MonitoringService.is_autonomous_paused()
    new_state = MonitoringService.set_autonomous_paused(not current_state)
    return {
        "status": "success",
        "actions_paused": new_state,
        "message": "Autonomous recovery actions PAUSED" if new_state else "Autonomous recovery actions ACTIVE",
    }
