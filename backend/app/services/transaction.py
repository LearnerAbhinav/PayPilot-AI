import uuid
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transaction import Transaction


class TransactionService:
    @staticmethod
    async def get_transactions(
        db: AsyncSession,
        merchant_id: uuid.UUID,
        filters: dict | None = None,
    ) -> list[Transaction]:
        query = select(Transaction).where(Transaction.merchant_id == merchant_id)

        if filters:
            status = filters.get("status")
            if status:
                query = query.where(Transaction.status == status)

            payment_method = filters.get("payment_method")
            if payment_method:
                query = query.where(Transaction.payment_method == payment_method)

            start_date = filters.get("start_date")
            if start_date:
                query = query.where(Transaction.created_at >= start_date)

            end_date = filters.get("end_date")
            if end_date:
                query = query.where(Transaction.created_at <= end_date)

            min_amount = filters.get("min_amount")
            if min_amount is not None:
                query = query.where(Transaction.amount >= Decimal(str(min_amount)))

            max_amount = filters.get("max_amount")
            if max_amount is not None:
                query = query.where(Transaction.amount <= Decimal(str(max_amount)))

        page = filters.get("page", 1) if filters else 1
        page_size = filters.get("page_size", 20) if filters else 20
        offset = (page - 1) * page_size

        query = query.order_by(Transaction.created_at.desc()).offset(offset).limit(page_size)

        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def get_transaction(
        db: AsyncSession, merchant_id: uuid.UUID, transaction_id: uuid.UUID
    ) -> Transaction:
        result = await db.execute(
            select(Transaction).where(
                Transaction.id == transaction_id,
                Transaction.merchant_id == merchant_id,
            )
        )
        tx = result.scalar_one_or_none()
        if not tx:
            return None
        return tx

    @staticmethod
    async def get_transactions_by_date_range(
        db: AsyncSession,
        merchant_id: uuid.UUID,
        start: datetime,
        end: datetime,
    ) -> list[Transaction]:
        result = await db.execute(
            select(Transaction).where(
                and_(
                    Transaction.merchant_id == merchant_id,
                    Transaction.created_at >= start,
                    Transaction.created_at <= end,
                )
            ).order_by(Transaction.created_at.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def count_transactions(
        db: AsyncSession,
        merchant_id: uuid.UUID,
        status: str | None = None,
        date_range: tuple[datetime, datetime] | None = None,
    ) -> int:
        query = select(func.count(Transaction.id)).where(
            Transaction.merchant_id == merchant_id
        )
        if status:
            query = query.where(Transaction.status == status)
        if date_range:
            start, end = date_range
            query = query.where(
                and_(Transaction.created_at >= start, Transaction.created_at <= end)
            )
        result = await db.execute(query)
        return result.scalar() or 0

    @staticmethod
    async def get_failed_transactions(
        db: AsyncSession, merchant_id: uuid.UUID, days: int = 7
    ) -> list[Transaction]:
        cutoff = datetime.utcnow() - timedelta(days=days)
        result = await db.execute(
            select(Transaction).where(
                and_(
                    Transaction.merchant_id == merchant_id,
                    Transaction.status == "failed",
                    Transaction.created_at >= cutoff,
                )
            ).order_by(Transaction.created_at.desc())
        )
        return list(result.scalars().all())
