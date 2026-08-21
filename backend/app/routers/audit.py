import math

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.routers.auth import get_current_user_dependency
from app.schemas.audit import AuditLogResponse, AuditLogListResponse
from app.services.audit import AuditService

router = APIRouter(prefix="/api/audit", tags=["Audit Logs"])


@router.get("/", response_model=AuditLogListResponse)
async def list_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user_dependency),
):
    offset = (page - 1) * page_size
    logs = await AuditService.get_audit_logs(
        db, current_user.merchant_id, limit=page_size, offset=offset
    )
    total = await AuditService.get_audit_log_count(db, current_user.merchant_id)
    total_pages = math.ceil(total / page_size) if total > 0 else 1

    return AuditLogListResponse(
        items=[AuditLogResponse.model_validate(log) for log in logs],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/count")
async def get_audit_log_count(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user_dependency),
):
    total = await AuditService.get_audit_log_count(db, current_user.merchant_id)
    return {"total": total}
