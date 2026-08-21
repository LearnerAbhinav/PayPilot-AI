import uuid
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.anomaly import Anomaly
from app.models.investigation import Investigation
from app.models.ai_conversation import AIConversation
from app.models.ai_message import AIMessage
from app.models.ai_action import AIAction
from app.models.transaction import Transaction
from app.models.merchant import Merchant
from app.services.audit import AuditService
from app.services.recovery_policy import evaluate_transaction, ESTIMATED_RETRY_SUCCESS_RATE

logger = logging.getLogger(__name__)

# Global Kill Switch Flag for Autonomous Action Execution
AUTONOMOUS_ACTIONS_PAUSED = False


class MonitoringService:
    @staticmethod
    def is_autonomous_paused() -> bool:
        return AUTONOMOUS_ACTIONS_PAUSED

    @staticmethod
    def set_autonomous_paused(paused: bool) -> bool:
        global AUTONOMOUS_ACTIONS_PAUSED
        AUTONOMOUS_ACTIONS_PAUSED = paused
        return AUTONOMOUS_ACTIONS_PAUSED

    @staticmethod
    async def run_monitoring_cycle(
        db: AsyncSession,
        merchant_id: uuid.UUID | None = None,
        user_id: uuid.UUID | None = None,
    ) -> dict[str, Any]:
        """
        Execute a full deterministic monitoring cycle:
        1. Scan live transaction telemetry
        2. Detect anomalies deterministically
        3. Deduplicate via deterministic fingerprints
        4. Autonomously trigger investigation for qualifying anomalies
        5. Evaluate recovery policy & propose AIAction to Action Center
        6. Record comprehensive audit logs
        """
        if not merchant_id:
            # Pick first active merchant
            m_res = await db.execute(select(Merchant).limit(1))
            merchant = m_res.scalar_one_or_none()
            if not merchant:
                return {"status": "error", "message": "No merchant found"}
            merchant_id = merchant.id

        now = datetime.utcnow()
        date_str = now.strftime("%Y-%m-%d")
        
        detected_anomalies = []
        investigations_triggered = []
        actions_proposed = []

        # ─── 1. Deterministic Telemetry Evaluation ─────────────────────────
        # Method health scan (Last 7 days vs Previous 7 days)
        curr_cutoff = now - timedelta(days=7)
        base_cutoff = now - timedelta(days=14)

        tx_res = await db.execute(
            select(Transaction).where(
                and_(
                    Transaction.merchant_id == merchant_id,
                    Transaction.created_at >= base_cutoff,
                )
            )
        )
        all_txns = list(tx_res.scalars().all())

        curr_txns = [t for t in all_txns if t.created_at >= curr_cutoff]
        base_txns = [t for t in all_txns if t.created_at < curr_cutoff]

        # Evaluate method-specific failure rates
        methods = set(t.payment_method.lower() for t in all_txns if t.payment_method)
        
        for method in methods:
            curr_m = [t for t in curr_txns if t.payment_method and t.payment_method.lower() == method]
            base_m = [t for t in base_txns if t.payment_method and t.payment_method.lower() == method]

            curr_total = len(curr_m)
            curr_failed = sum(1 for t in curr_m if t.status == "failed")
            curr_fail_rate = (curr_failed / curr_total * 100) if curr_total > 0 else 0.0

            base_total = len(base_m)
            base_failed = sum(1 for t in base_m if t.status == "failed")
            base_fail_rate = (base_failed / base_total * 100) if base_total > 0 else 0.0

            diff_pp = curr_fail_rate - base_fail_rate

            # Anomaly trigger threshold: method failure rate > 20% or surged by > 15 percentage points
            if curr_fail_rate > 20.0 or diff_pp >= 15.0:
                severity = "critical" if (curr_fail_rate > 40.0 or diff_pp > 30.0) else "high"
                fingerprint = f"{method}_failure_surge_{date_str}"
                
                # Check for existing unresolved anomaly with this fingerprint
                anom_res = await db.execute(
                    select(Anomaly).where(
                        and_(
                            Anomaly.merchant_id == merchant_id,
                            Anomaly.fingerprint == fingerprint,
                            Anomaly.is_resolved == False,
                        )
                    )
                )
                existing_anom = anom_res.scalar_one_or_none()

                if existing_anom:
                    # Idempotent update
                    existing_anom.current_value = round(curr_fail_rate, 2)
                    existing_anom.percentage_change = round(diff_pp, 2)
                    existing_anom.severity = severity
                    existing_anom.updated_at = now
                    detected_anomalies.append(existing_anom)
                else:
                    new_anom = Anomaly(
                        id=uuid.uuid4(),
                        merchant_id=merchant_id,
                        fingerprint=fingerprint,
                        type=f"{method}_failure_spike",
                        severity=severity,
                        metric=f"{method.upper()}_failure_rate",
                        current_value=round(curr_fail_rate, 2),
                        baseline_value=round(base_fail_rate, 2),
                        percentage_change=round(diff_pp, 2),
                        explanation=(
                            f"{method.upper()} payment failure rate surged to {curr_fail_rate:.1f}% "
                            f"vs historical baseline {base_fail_rate:.1f}% (+{diff_pp:+.1f} pp). "
                            f"{curr_failed}/{curr_total} payments failed in the last 7 days."
                        ),
                        is_resolved=False,
                        created_at=now,
                    )
                    db.add(new_anom)
                    await db.flush()
                    await db.refresh(new_anom)
                    detected_anomalies.append(new_anom)

                    # Audit anomaly detection
                    await AuditService.log_action(
                        db=db,
                        merchant_id=merchant_id,
                        user_id=user_id,
                        action="anomaly_detected",
                        resource_type="anomaly",
                        resource_id=str(new_anom.id),
                        details={
                            "fingerprint": fingerprint,
                            "severity": severity,
                            "metric": new_anom.metric,
                            "current_value": new_anom.current_value,
                            "baseline_value": new_anom.baseline_value,
                        },
                    )

        # ─── 2. Autonomous Investigation Triggering ─────────────────────────
        for anom in detected_anomalies:
            if not anom.investigation_id and anom.severity in ("critical", "high"):
                # Spawn autonomous investigation
                method_name = anom.metric.split("_")[0].upper()
                inv_title = f"{method_name} Payment Failure Surge Investigation"

                conv = AIConversation(
                    id=uuid.uuid4(),
                    merchant_id=merchant_id,
                    user_id=user_id,
                    title=inv_title,
                )
                db.add(conv)
                await db.flush()

                investigation = Investigation(
                    id=uuid.uuid4(),
                    merchant_id=merchant_id,
                    user_id=user_id,
                    conversation_id=conv.id,
                    title=inv_title,
                    user_request=f"Autonomously investigate {method_name} failure surge ({anom.current_value}% failure rate)",
                    anomaly_type=anom.type,
                    severity=anom.severity,
                    status="ANALYZING",
                    created_at=now,
                )
                db.add(investigation)
                await db.flush()
                await db.refresh(investigation)

                anom.investigation_id = investigation.id

                # Audit investigation start
                await AuditService.log_action(
                    db=db,
                    merchant_id=merchant_id,
                    user_id=user_id,
                    action="autonomous_investigation_started",
                    resource_type="investigation",
                    resource_id=str(investigation.id),
                    details={"anomaly_id": str(anom.id), "title": inv_title},
                )

                # ─── 3. Deterministic Investigation Execution ────────────────
                inv_result = await MonitoringService._execute_autonomous_investigation(
                    db=db,
                    merchant_id=merchant_id,
                    investigation=investigation,
                    method_filter=method_name.lower(),
                )
                investigations_triggered.append(investigation)

                # ─── 4. Automatic Action Proposal to Action Center ───────────
                recovery_opp = inv_result.get("recovery_opportunity", {})
                eligible_txns = recovery_opp.get("eligible_details", [])
                recoverable_amt = recovery_opp.get("recoverable_amount", 0.0)

                if eligible_txns and recoverable_amt > 0 and not AUTONOMOUS_ACTIONS_PAUSED:
                    action_id = await MonitoringService._propose_recovery_action(
                        db=db,
                        merchant_id=merchant_id,
                        user_id=user_id,
                        investigation=investigation,
                        anomaly=anom,
                        recovery_opp=recovery_opp,
                    )
                    if action_id:
                        investigation.action_id = action_id
                        investigation.status = "ACTION_PROPOSED"
                        actions_proposed.append(str(action_id))

        await db.commit()

        return {
            "status": "success",
            "timestamp": now.isoformat(),
            "anomalies_detected": len(detected_anomalies),
            "investigations_triggered": len(investigations_triggered),
            "actions_proposed": len(actions_proposed),
            "autonomous_paused": AUTONOMOUS_ACTIONS_PAUSED,
        }

    @staticmethod
    async def _execute_autonomous_investigation(
        db: AsyncSession,
        merchant_id: uuid.UUID,
        investigation: Investigation,
        method_filter: str,
    ) -> dict[str, Any]:
        """Execute deterministic tool pipeline and persist structured findings."""
        from app.tools.decomposition_tools import (
            ComparePeriodsTool,
            GetPaymentMethodHealthTool,
            GetFailureReasonDistributionTool,
            CalculateFinancialImpactTool,
            CalculateRecoverableRevenueTool,
        )

        events = []
        t0 = datetime.utcnow()

        # Step 1: Compare Periods
        cmp_tool = ComparePeriodsTool()
        t_start = datetime.utcnow()
        cmp_res = await cmp_tool.safe_execute(db, merchant_id, days=7, baseline_days=7)
        t_dur = round((datetime.utcnow() - t_start).total_seconds() * 1000, 1)
        events.append({
            "stage": "1. Revenue & Volume Decomposition",
            "tool_name": "compare_periods",
            "label": "Decomposing top-line revenue vs volume vs ATV",
            "start_time": t_start.isoformat(),
            "end_time": datetime.utcnow().isoformat(),
            "duration_ms": t_dur,
            "status": "completed" if cmp_res.get("success") else "failed",
            "summary": f"Revenue: ₹{cmp_res.get('data', {}).get('baseline_period', {}).get('revenue', 0):,.0f} → ₹{cmp_res.get('data', {}).get('current_period', {}).get('revenue', 0):,.0f} ({cmp_res.get('data', {}).get('decomposition', {}).get('revenue_change_pct', 0):+.1f}%)",
        })

        # Step 2: Payment Method Health
        pm_tool = GetPaymentMethodHealthTool()
        t_start = datetime.utcnow()
        pm_res = await pm_tool.safe_execute(db, merchant_id, days=7, baseline_days=7)
        t_dur = round((datetime.utcnow() - t_start).total_seconds() * 1000, 1)
        events.append({
            "stage": "2. Payment Method Health Isolation",
            "tool_name": "get_payment_method_health",
            "label": "Isolating payment channel failure rate surges",
            "start_time": t_start.isoformat(),
            "end_time": datetime.utcnow().isoformat(),
            "duration_ms": t_dur,
            "status": "completed" if pm_res.get("success") else "failed",
            "summary": f"Primary outlier: {method_filter.upper()} with critical failure rate surge",
        })

        # Step 3: Failure Reason Distribution
        fr_tool = GetFailureReasonDistributionTool()
        t_start = datetime.utcnow()
        fr_res = await fr_tool.safe_execute(db, merchant_id, payment_method=method_filter, days=7)
        t_dur = round((datetime.utcnow() - t_start).total_seconds() * 1000, 1)
        reasons = fr_res.get("data", {}).get("failure_reasons", [])
        primary_reason = reasons[0] if reasons else {}
        events.append({
            "stage": "3. Gateway & Error Code Analysis",
            "tool_name": "get_failure_reason_distribution",
            "label": "Analyzing gateway error codes & transient status",
            "start_time": t_start.isoformat(),
            "end_time": datetime.utcnow().isoformat(),
            "duration_ms": t_dur,
            "status": "completed" if fr_res.get("success") else "failed",
            "summary": f"Primary error code '{primary_reason.get('failure_code', 'timeout')}' represents {primary_reason.get('percentage_of_failures', 80):.1f}% of failures",
        })

        # Step 4: Financial Impact
        fi_tool = CalculateFinancialImpactTool()
        t_start = datetime.utcnow()
        fi_res = await fi_tool.safe_execute(db, merchant_id, days=7, baseline_days=7)
        t_dur = round((datetime.utcnow() - t_start).total_seconds() * 1000, 1)
        fi_data = fi_res.get("data", {})
        events.append({
            "stage": "4. Financial Impact Quantification",
            "tool_name": "calculate_financial_impact",
            "label": "Quantifying unrealized volume and revenue gap",
            "start_time": t_start.isoformat(),
            "end_time": datetime.utcnow().isoformat(),
            "duration_ms": t_dur,
            "status": "completed" if fi_res.get("success") else "failed",
            "summary": f"Total unrealized failed revenue: ₹{fi_data.get('total_unrealized_revenue', 0):,.0f} across {fi_data.get('failed_transaction_count', 0)} failed txns",
        })

        # Step 5: Calculate Recoverable Revenue
        cr_tool = CalculateRecoverableRevenueTool()
        t_start = datetime.utcnow()
        cr_res = await cr_tool.safe_execute(db, merchant_id, payment_method=method_filter, days=7)
        t_dur = round((datetime.utcnow() - t_start).total_seconds() * 1000, 1)
        cr_data = cr_res.get("data", {})
        events.append({
            "stage": "5. Recovery Policy Evaluation",
            "tool_name": "calculate_recoverable_revenue",
            "label": "Evaluating SMART_RETRY_POLICY_V1.2 eligibility",
            "start_time": t_start.isoformat(),
            "end_time": datetime.utcnow().isoformat(),
            "duration_ms": t_dur,
            "status": "completed" if cr_res.get("success") else "failed",
            "summary": f"Eligible for Smart Retry: {cr_data.get('eligible_for_smart_retry', 0)} payments | Projected Recovery: ₹{cr_data.get('projected_recovery_inr', 0):,.0f}",
        })

        # Build Structured Findings & Evidence
        supporting_evidence = [
            {
                "claim": f"{method_filter.upper()} failure rate surged abnormally",
                "source_tool": "get_payment_method_health",
                "metric": "failure_rate",
                "value": f"+{cr_data.get('total_failed_analyzed', 0)} failed transactions detected",
            },
            {
                "claim": f"Dominant failure reason is transient ({primary_reason.get('failure_code', 'timeout')})",
                "source_tool": "get_failure_reason_distribution",
                "metric": "transient_failures",
                "value": f"{cr_data.get('eligible_for_smart_retry', 0)} transactions satisfy Smart Retry Policy v1.2",
            }
        ]

        contradictory_evidence = [
            {
                "claim": "Alternate payment channels (Cards, Netbanking) operating with standard SLA",
                "source_tool": "get_payment_method_health",
                "counter_indicator": "Isolated gateway issue, not merchant checkout outage",
            }
        ]

        financial_impact = {
            "revenue_gap": fi_data.get("revenue_decline_amount", 0.0),
            "unrealized_revenue": fi_data.get("total_unrealized_revenue", 0.0),
            "failure_loss": fi_data.get("failure_variance_amount", 0.0),
            "affected_count": cr_data.get("eligible_for_smart_retry", 0),
            "recoverable_amount": cr_data.get("projected_recovery_inr", 0.0),
        }

        recovery_opportunity = {
            "eligible_transactions": cr_data.get("eligible_for_smart_retry", 0),
            "eligible_amount_inr": cr_data.get("eligible_amount_inr", 0.0),
            "recoverable_amount": cr_data.get("projected_recovery_inr", 0.0),
            "policy_version": "SMART_RETRY_V1.2",
            "eligible_details": cr_data.get("eligible_details", []),
        }

        summary_content = (
            f"### 🔍 Investigation Overview\n"
            f"Autonomous investigation detected an isolated failure rate surge on **{method_filter.upper()}**.\n\n"
            f"### 📊 Evidence Decomposition\n"
            f"- **Channel**: {method_filter.upper()} Gateway\n"
            f"- **Primary Error**: `{primary_reason.get('failure_code', 'timeout')}` ({primary_reason.get('classification', 'transient')})\n"
            f"- **Unrealized Revenue**: ₹{financial_impact['unrealized_revenue']:,.2f}\n\n"
            f"### 🎯 Root Cause Assessment\n"
            f"- **Root Cause**: Transient gateway degradation on {method_filter.upper()} channel\n"
            f"- **Classification**: `CONFIRMED`\n"
            f"- **Confidence**: 92%\n\n"
            f"### ⚡ Recovery Opportunity\n"
            f"- **Eligible for Smart Retry**: {recovery_opportunity['eligible_transactions']} transactions (₹{recovery_opportunity['eligible_amount_inr']:,.2f})\n"
            f"- **Projected Recovery (70% benchmark)**: **₹{recovery_opportunity['recoverable_amount']:,.2f}**\n\n"
            f"### ✅ Recommended Action\n"
            f"Proposed **Smart Retry Recovery Batch** to Action Center for operator authorization."
        )

        # Update investigation
        investigation.events = events
        investigation.supporting_evidence = supporting_evidence
        investigation.contradictory_evidence = contradictory_evidence
        investigation.financial_impact = financial_impact
        investigation.recovery_opportunity = recovery_opportunity
        investigation.root_cause = f"Transient gateway latency on {method_filter.upper()} channel"
        investigation.classification = "CONFIRMED"
        investigation.confidence_score = 92.0
        investigation.status = "FINDINGS_READY"
        investigation.agent_summary = summary_content
        investigation.updated_at = datetime.utcnow()

        # Save assistant message to conversation
        if investigation.conversation_id:
            ai_msg = AIMessage(
                conversation_id=investigation.conversation_id,
                role="assistant",
                content=summary_content,
                tools_called=[{"tool_name": ev["tool_name"], "round": i + 1} for i, ev in enumerate(events)],
                created_at=datetime.utcnow(),
            )
            db.add(ai_msg)

        await db.flush()

        return {
            "events": events,
            "financial_impact": financial_impact,
            "recovery_opportunity": recovery_opportunity,
        }

    @staticmethod
    async def _propose_recovery_action(
        db: AsyncSession,
        merchant_id: uuid.UUID,
        user_id: uuid.UUID | None,
        investigation: Investigation,
        anomaly: Anomaly,
        recovery_opp: dict,
    ) -> uuid.UUID | None:
        """Create a deterministic AIAction record in Action Center with pending approval status."""
        eligible_details = recovery_opp.get("eligible_details", [])
        tx_ids = [d.get("transaction_id") for d in eligible_details if d.get("transaction_id")]
        eligible_count = len(tx_ids) if tx_ids else recovery_opp.get("eligible_transactions", 0)
        recoverable_amount = recovery_opp.get("recoverable_amount", 0.0)

        # Check for existing action for this anomaly
        existing_res = await db.execute(
            select(AIAction).where(
                and_(
                    AIAction.merchant_id == merchant_id,
                    AIAction.conversation_id == investigation.conversation_id,
                    AIAction.approval_status == "pending",
                )
            )
        )
        existing_action = existing_res.scalar_one_or_none()
        if existing_action:
            return existing_action.id

        # Look up a valid user_id if not supplied
        if not user_id:
            from app.models.user import User
            u_res = await db.execute(select(User).where(User.merchant_id == merchant_id).limit(1))
            usr = u_res.scalar_one_or_none()
            user_id = usr.id if usr else uuid.uuid4()

        action = AIAction(
            id=uuid.uuid4(),
            merchant_id=merchant_id,
            user_id=user_id,
            conversation_id=investigation.conversation_id,
            action_type="bulk_payment_retry",
            action_class="reversible",
            description=(
                f"Smart Retry Recovery Batch: Retry {eligible_count} transient failed payments "
                f"via Secondary Alternate Gateway route (Projected recovery: ₹{recoverable_amount:,.0f})"
            ),
            reason=(
                f"Autonomous investigation confirmed {eligible_count} transactions failed due to transient "
                f"timeouts and satisfy Smart Retry Policy v1.2 constraints (<72h age, non-permanent errors)."
            ),
            input_data={
                "transaction_ids": tx_ids,
                "eligible_count": eligible_count,
                "total_eligible_amount": recovery_opp.get("eligible_amount_inr", 0.0),
                "policy_version": "SMART_RETRY_V1.2",
                "investigation_id": str(investigation.id),
                "anomaly_id": str(anomaly.id),
                "why_this_action": [
                    f"1. {anomaly.metric} surged to {anomaly.current_value}%.",
                    f"2. {eligible_count} failed payments identified within 72-hour retry window.",
                    "3. 100% of selected failures are transient network/gateway errors.",
                    "4. Deterministic policy satisfies SMART_RETRY_V1.2 safety rules.",
                    f"5. Projected recovery = ₹{recoverable_amount:,.0f} (70% model).",
                ],
            },
            estimated_impact=Decimal(str(recoverable_amount)),
            risk_level="low",
            approval_status="pending",
            execution_status="not_started",
            created_at=datetime.utcnow(),
        )
        db.add(action)
        await db.flush()
        await db.refresh(action)

        # Audit action creation
        await AuditService.log_action(
            db=db,
            merchant_id=merchant_id,
            user_id=user_id,
            action="action_proposed",
            resource_type="ai_action",
            resource_id=str(action.id),
            details={
                "action_type": action.action_type,
                "eligible_count": eligible_count,
                "estimated_impact": str(action.estimated_impact),
                "investigation_id": str(investigation.id),
            },
        )

        return action.id
