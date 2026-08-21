import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.tools.base import BaseTool, ActionClass
from app.services.anomaly import AnomalyDetectionService


class DetectAnomaliesTool(BaseTool):
    name = "detect_anomalies"
    description = (
        "Run anomaly detection across the merchant's payment data. Analyzes revenue "
        "patterns, failure rates, and refund rates to identify unusual activity. "
        "Returns detected anomalies with severity levels and explanations."
    )
    parameters = {
        "type": "object",
        "properties": {},
        "required": [],
    }
    action_class = ActionClass.READ_ONLY

    async def execute(
        self, db: AsyncSession, merchant_id: uuid.UUID, **kwargs
    ) -> dict:
        anomalies = await AnomalyDetectionService.detect_anomalies(db, merchant_id)

        by_severity: dict[str, list] = {}
        for a in anomalies:
            sev = a.get("severity", "unknown")
            if sev not in by_severity:
                by_severity[sev] = []
            by_severity[sev].append(a)

        by_type: dict[str, int] = {}
        for a in anomalies:
            t = a.get("type", "unknown")
            by_type[t] = by_type.get(t, 0) + 1

        return {
            "total_anomalies": len(anomalies),
            "anomalies": anomalies,
            "by_severity": {k: len(v) for k, v in by_severity.items()},
            "by_type": by_type,
            "has_critical": any(a.get("severity") == "critical" for a in anomalies),
        }
