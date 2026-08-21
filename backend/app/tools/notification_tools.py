import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.tools.base import BaseTool, ActionClass
from app.services.audit import AuditService


class CreateAlertTool(BaseTool):
    name = "create_alert"
    description = (
        "Create an alert entry in the audit log. Use this to flag important "
        "findings, anomalies, or situations that need the merchant's attention. "
        "Alerts are recorded for tracking and follow-up."
    )
    parameters = {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "Short alert title summarizing the issue",
            },
            "message": {
                "type": "string",
                "description": "Detailed alert message with context",
            },
            "severity": {
                "type": "string",
                "description": "Alert severity level",
                "enum": ["info", "warning", "critical"],
            },
            "category": {
                "type": "string",
                "description": "Alert category for grouping",
                "enum": ["anomaly", "payment_failure", "revenue", "security", "system"],
            },
        },
        "required": ["title", "message", "severity"],
    }
    action_class = ActionClass.READ_ONLY

    async def execute(
        self, db: AsyncSession, merchant_id: uuid.UUID, **kwargs
    ) -> dict:
        title = kwargs["title"]
        message = kwargs["message"]
        severity = kwargs.get("severity", "info")
        category = kwargs.get("category", "system")

        log = await AuditService.log_action(
            db=db,
            merchant_id=merchant_id,
            user_id=None,
            action="ai_alert",
            resource_type="alert",
            details={
                "title": title,
                "message": message,
                "severity": severity,
                "category": category,
                "source": "ai_agent",
                "created_at": datetime.utcnow().isoformat(),
            },
        )

        return {
            "alert_id": str(log.id),
            "title": title,
            "message": message,
            "severity": severity,
            "category": category,
            "created_at": log.created_at.isoformat() if log.created_at else None,
            "status": "created",
        }
