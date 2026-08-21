import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.routers.auth import get_current_user_dependency
from app.schemas.transaction import TransactionResponse, TransactionListResponse
from app.services.transaction import TransactionService

router = APIRouter(prefix="/api/transactions", tags=["Transactions"])


@router.get("/", response_model=TransactionListResponse)
async def list_transactions(
    status_filter: str | None = Query(None, alias="status"),
    payment_method: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user_dependency),
):
    merchant_id = current_user.merchant_id
    filters = {
        "status": status_filter,
        "payment_method": payment_method,
        "start_date": date_from,
        "end_date": date_to,
        "page": page,
        "page_size": page_size,
    }
    transactions = await TransactionService.get_transactions(db, merchant_id, filters)
    total = await TransactionService.count_transactions(
        db,
        merchant_id,
        status=status_filter,
        date_range=(date_from, date_to) if date_from and date_to else None,
    )
    total_pages = (total + page_size - 1) // page_size

    return TransactionListResponse(
        items=[TransactionResponse.model_validate(tx) for tx in transactions],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/failed", response_model=list[TransactionResponse])
async def get_failed_transactions(
    days: int = Query(7, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user_dependency),
):
    transactions = await TransactionService.get_failed_transactions(
        db, current_user.merchant_id, days=days
    )
    return [TransactionResponse.model_validate(tx) for tx in transactions]


@router.get("/{transaction_id}", response_model=TransactionResponse)
async def get_transaction(
    transaction_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user_dependency),
):
    tx = await TransactionService.get_transaction(
        db, current_user.merchant_id, transaction_id
    )
    if not tx:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found",
        )
    return TransactionResponse.model_validate(tx)
