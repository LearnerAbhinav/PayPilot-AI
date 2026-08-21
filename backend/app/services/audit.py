import uuid
from datetime import datetime

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog


class AuditService:
    @staticmethod
    async def log_action(
        db: AsyncSession,
        merchant_id: uuid.UUID,
        user_id: uuid.UUID | None,
        action: str,
        details: dict | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
    ) -> AuditLog:
        log = AuditLog(
            merchant_id=merchant_id,
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            created_at=datetime.utcnow(),
        )
        db.add(log)
        await db.flush()
        await db.refresh(log)
        return log

    @staticmethod
    async def log_ai_action(
        db: AsyncSession,
        merchant_id: uuid.UUID,
        user_id: uuid.UUID | None,
        prompt: str,
        decision: str,
        tools: list[str] | None = None,
        inputs: dict | None = None,
        outputs: dict | None = None,
    ) -> AuditLog:
        log = AuditLog(
            merchant_id=merchant_id,
            user_id=user_id,
            action="ai_action",
            resource_type="ai_agent",
            details={
                "prompt": prompt,
                "decision": decision,
            },
            user_prompt=prompt,
            agent_decision=decision,
            tools_called=tools,
            tool_inputs=inputs,
            tool_outputs=outputs,
            created_at=datetime.utcnow(),
        )
        db.add(log)
        await db.flush()
        await db.refresh(log)
        return log

    @staticmethod
    async def get_audit_logs(
        db: AsyncSession,
        merchant_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> list[AuditLog]:
        result = await db.execute(
            select(AuditLog)
            .where(AuditLog.merchant_id == merchant_id)
            .order_by(AuditLog.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_audit_log_count(db: AsyncSession, merchant_id: uuid.UUID) -> int:
        result = await db.execute(
            select(func.count(AuditLog.id)).where(
                AuditLog.merchant_id == merchant_id
            )
        )
        return result.scalar() or 0
