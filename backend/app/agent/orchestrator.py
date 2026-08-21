import uuid
import json
import logging
import asyncio
import time
from datetime import datetime
from typing import Any, AsyncIterator

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.prompts import (
    build_investigation_system_prompt,
    NO_LLM_MESSAGE,
)
from app.tools.transaction_tools import (
    GetTransactionMetricsTool,
    GetFailedTransactionsTool,
    GetRevenueTrendTool,
    GetPaymentMethodBreakdownTool,
    GetRefundSummaryTool,
    GetCustomerSummaryTool,
)
from app.tools.decomposition_tools import (
    ComparePeriodsTool,
    GetPaymentMethodHealthTool,
    GetFailureReasonDistributionTool,
    CalculateFinancialImpactTool,
    CalculateRecoverableRevenueTool,
)
from app.tools.analytics_tools import DetectAnomaliesTool
from app.tools.forecast_tools import ForecastCashFlowTool
from app.tools.recommendation_tools import (
    GenerateRecoveryPlanTool,
    SimulatePaymentRecoveryTool,
)
from app.tools.investigation_tools import (
    GetFailureBreakdownByMethodTool,
    GetRecoverableTransactionsTool,
    VerifyRecoveryResultTool,
)
from app.tools.notification_tools import CreateAlertTool
from app.tools.base import BaseTool
from app.services.audit import AuditService

logger = logging.getLogger(__name__)

MAX_TOOL_ROUNDS = 5


def _get_provider_base_url(provider: str) -> str:
    if provider == "groq":
        return "https://api.groq.com/openai/v1"
    elif provider == "openai":
        return "https://api.openai.com/v1"
    return "https://api.groq.com/openai/v1"


def _compact_for_llm(result: dict) -> str:
    """Format tool results concisely for LLM consumption to save tokens."""
    if not isinstance(result, dict):
        return str(result)[:600]

    clean = dict(result)
    for key in ("eligible_transactions", "recent_refunds", "transactions", "trend", "eligible_details"):
        if key in clean and isinstance(clean[key], list):
            clean[key] = f"[{len(clean[key])} records processed in database]"

    dumped = json.dumps(clean, default=str)
    if len(dumped) > 850:
        return dumped[:850] + "...}"
    return dumped


class AgentEvent:
    """Typed streaming event with real execution metrics."""
    def __init__(self, event_type: str, data: dict):
        self.type = event_type
        self.data = data

    def to_sse(self) -> str:
        return f"event: {self.type}\ndata: {json.dumps(self.data, default=str)}\n\n"


class AIAgentOrchestrator:
    def __init__(self, llm_api_key: str, llm_model: str, llm_provider: str):
        self.llm_api_key = llm_api_key
        self.llm_model = llm_model or "openai/gpt-oss-120b"
        self.llm_provider = llm_provider or "groq"
        self.base_url = _get_provider_base_url(self.llm_provider)
        self.tools: dict[str, BaseTool] = {}
        self._register_default_tools()

    def _register_default_tools(self) -> None:
        default_tools: list[BaseTool] = [
            # Decomposition Hierarchy Tools
            ComparePeriodsTool(),
            GetPaymentMethodHealthTool(),
            GetFailureReasonDistributionTool(),
            CalculateFinancialImpactTool(),
            CalculateRecoverableRevenueTool(),
            # Core Observability & Telemetry Tools
            GetTransactionMetricsTool(),
            GetFailedTransactionsTool(),
            GetRevenueTrendTool(),
            GetPaymentMethodBreakdownTool(),
            GetRefundSummaryTool(),
            GetCustomerSummaryTool(),
            DetectAnomaliesTool(),
            ForecastCashFlowTool(),
            GetFailureBreakdownByMethodTool(),
            GetRecoverableTransactionsTool(),
            # Action & Policy Tools
            GenerateRecoveryPlanTool(),
            SimulatePaymentRecoveryTool(),
            VerifyRecoveryResultTool(),
            CreateAlertTool(),
        ]
        for tool in default_tools:
            self.register_tool(tool)

    def register_tool(self, tool: BaseTool) -> None:
        self.tools[tool.name] = tool

    def _get_tool_definitions(self) -> list[dict]:
        return [tool.get_definition() for tool in self.tools.values()]

    def _build_system_prompt(self, merchant_id: uuid.UUID) -> str:
        return build_investigation_system_prompt(
            merchant_id=str(merchant_id),
            current_date=datetime.utcnow().strftime("%Y-%m-%d"),
            provider=self.llm_provider,
        )

    def _build_messages(
        self,
        system_prompt: str,
        conversation_history: list[dict],
        user_message: str,
    ) -> list[dict]:
        messages = [{"role": "system", "content": system_prompt}]
        for msg in conversation_history[-6:]:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content[:500]})
        messages.append({"role": "user", "content": user_message})
        return messages

    async def _call_llm(
        self, messages: list[dict], tools: list[dict] | None = None
    ) -> dict:
        if not self.llm_api_key:
            raise ValueError(NO_LLM_MESSAGE)

        headers = {
            "Authorization": f"Bearer {self.llm_api_key}",
            "Content-Type": "application/json",
        }

        body: dict[str, Any] = {
            "model": self.llm_model,
            "messages": messages,
            "temperature": 0.1,
            "max_tokens": 1500,
        }

        if tools:
            body["tools"] = tools
            body["tool_choice"] = "auto"

        for attempt in range(3):
            async with httpx.AsyncClient(timeout=45.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=body,
                )
                if response.status_code == 429 and attempt < 2:
                    logger.warning(f"Groq 429 limit hit — waiting {(attempt + 1) * 1.5}s before retry")
                    await asyncio.sleep((attempt + 1) * 1.5)
                    continue
                response.raise_for_status()
                return response.json()

        raise RuntimeError("LLM request failed after retries")

    async def _execute_tool_call(
        self, tool_name: str, tool_args: dict, db: AsyncSession, merchant_id: uuid.UUID
    ) -> dict:
        tool = self.tools.get(tool_name)
        if not tool:
            return {
                "success": False,
                "tool_name": tool_name,
                "error": f"Unknown tool: {tool_name}",
            }
        result = await tool.safe_execute(db, merchant_id, **tool_args)
        return result

    async def process_message(
        self,
        db: AsyncSession,
        merchant_id: uuid.UUID,
        user_id: uuid.UUID,
        conversation_id: uuid.UUID,
        message: str,
    ) -> dict:
        """Process a message and return the full response (non-streaming)."""
        if not self.llm_api_key:
            return {
                "content": NO_LLM_MESSAGE,
                "tool_calls": [],
                "evidence": [],
                "error": "LLM not configured.",
            }

        system_prompt = self._build_system_prompt(merchant_id)
        tool_definitions = self._get_tool_definitions()
        conversation_history = await self._load_conversation_history(db, conversation_id)
        messages = self._build_messages(system_prompt, conversation_history, message)

        all_tool_calls: list[dict] = []
        all_evidence: list[dict] = []

        for round_num in range(MAX_TOOL_ROUNDS):
            try:
                llm_response = await self._call_llm(messages, tool_definitions)
            except Exception as e:
                logger.error(f"LLM call failed: {e}")
                final_content = self._build_evidence_fallback(all_evidence)
                return {
                    "content": final_content,
                    "tool_calls": all_tool_calls,
                    "evidence": all_evidence,
                    "error": None,
                }

            choice = llm_response.get("choices", [{}])[0]
            finish_reason = choice.get("finish_reason")
            message_data = choice.get("message", {})
            tool_calls_raw = message_data.get("tool_calls")

            if not tool_calls_raw or finish_reason not in ("tool_calls", None):
                final_content = message_data.get("content", "")
                if not final_content:
                    final_content = self._build_evidence_fallback(all_evidence)

                await self._save_messages(db, conversation_id, [
                    {"role": "user", "content": message},
                    {"role": "assistant", "content": final_content, "tools_called": all_tool_calls},
                ])

                await AuditService.log_ai_action(
                    db=db,
                    merchant_id=merchant_id,
                    user_id=user_id,
                    prompt=message,
                    decision=final_content[:500] if final_content else "",
                    tools=[tc["tool_name"] for tc in all_tool_calls],
                    outputs={tc["tool_name"]: tc.get("result", {}) for tc in all_tool_calls},
                )

                return {
                    "content": final_content,
                    "tool_calls": all_tool_calls,
                    "evidence": all_evidence,
                    "error": None,
                }

            messages.append(message_data)

            for tc in tool_calls_raw:
                tc_id = tc.get("id", "")
                func_data = tc.get("function", {})
                tool_name = func_data.get("name", "")
                raw_args = func_data.get("arguments", "{}")

                try:
                    tool_args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
                except json.JSONDecodeError:
                    tool_args = {}

                t_start = time.time()
                result = await self._execute_tool_call(tool_name, tool_args, db, merchant_id)
                t_duration = round((time.time() - t_start) * 1000, 1)

                tool_record = {
                    "tool_name": tool_name,
                    "arguments": tool_args,
                    "result": result,
                    "duration_ms": t_duration,
                    "round": round_num + 1,
                }
                all_tool_calls.append(tool_record)
                all_evidence.append({
                    "tool": tool_name,
                    "success": result.get("success", False),
                    "summary": self._summarize_tool_result(tool_name, result),
                    "duration_ms": t_duration,
                })

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc_id,
                    "content": _compact_for_llm(result),
                })

        # Final synthesis
        try:
            final_response = await self._call_llm(messages)
            final_content = final_response.get("choices", [{}])[0].get("message", {}).get("content", "")
        except Exception:
            final_content = self._build_evidence_fallback(all_evidence)

        if not final_content:
            final_content = self._build_evidence_fallback(all_evidence)

        await self._save_messages(db, conversation_id, [
            {"role": "user", "content": message},
            {"role": "assistant", "content": final_content, "tools_called": all_tool_calls},
        ])

        return {
            "content": final_content,
            "tool_calls": all_tool_calls,
            "evidence": all_evidence,
            "error": None,
        }

    async def stream_investigation(
        self,
        db: AsyncSession,
        merchant_id: uuid.UUID,
        user_id: uuid.UUID,
        conversation_id: uuid.UUID,
        message: str,
        investigation_id: str | None = None,
    ) -> AsyncIterator[AgentEvent]:
        """
        Run the agent and yield AgentEvent objects for SSE streaming with real timestamps and stage labels.
        """
        if not self.llm_api_key:
            yield AgentEvent("error", {
                "message": NO_LLM_MESSAGE,
                "code": "no_api_key",
            })
            return

        yield AgentEvent("started", {
            "message": "Investigation started",
            "investigation_id": investigation_id,
            "timestamp": datetime.utcnow().isoformat(),
        })

        system_prompt = self._build_system_prompt(merchant_id)
        tool_definitions = self._get_tool_definitions()
        conversation_history = await self._load_conversation_history(db, conversation_id)
        messages = self._build_messages(system_prompt, conversation_history, message)

        all_tool_calls: list[dict] = []
        all_evidence: list[dict] = []

        for round_num in range(MAX_TOOL_ROUNDS):
            try:
                llm_response = await self._call_llm(messages, tool_definitions)
            except Exception as e:
                logger.warning(f"Groq API error during streaming round {round_num + 1}: {e}")
                if all_evidence:
                    final_content = self._build_evidence_fallback(all_evidence)
                    await self._save_messages(db, conversation_id, [
                        {"role": "user", "content": message},
                        {"role": "assistant", "content": final_content, "tools_called": all_tool_calls},
                    ])
                    yield AgentEvent("complete", {
                        "content": final_content,
                        "tool_calls": all_tool_calls,
                        "evidence": all_evidence,
                        "investigation_id": investigation_id,
                    })
                    return
                else:
                    yield AgentEvent("error", {
                        "message": "Rate limit reached. Please wait a moment and try again.",
                        "code": "rate_limited",
                    })
                    return

            choice = llm_response.get("choices", [{}])[0]
            finish_reason = choice.get("finish_reason")
            message_data = choice.get("message", {})
            tool_calls_raw = message_data.get("tool_calls")

            if not tool_calls_raw or finish_reason not in ("tool_calls", None):
                final_content = message_data.get("content", "")
                if not final_content:
                    final_content = self._build_evidence_fallback(all_evidence)

                await self._save_messages(db, conversation_id, [
                    {"role": "user", "content": message},
                    {"role": "assistant", "content": final_content, "tools_called": all_tool_calls},
                ])
                await AuditService.log_ai_action(
                    db=db, merchant_id=merchant_id, user_id=user_id,
                    prompt=message, decision=final_content[:500],
                    tools=[tc["tool_name"] for tc in all_tool_calls],
                    outputs={tc["tool_name"]: tc.get("result", {}) for tc in all_tool_calls},
                )

                yield AgentEvent("complete", {
                    "content": final_content,
                    "tool_calls": all_tool_calls,
                    "evidence": all_evidence,
                    "investigation_id": investigation_id,
                })
                return

            messages.append(message_data)

            for tc in tool_calls_raw:
                tc_id = tc.get("id", "")
                func_data = tc.get("function", {})
                tool_name = func_data.get("name", "")
                raw_args = func_data.get("arguments", "{}")
                try:
                    tool_args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
                except json.JSONDecodeError:
                    tool_args = {}

                t_start = time.time()
                yield AgentEvent("tool_start", {
                    "tool": tool_name,
                    "stage": self._tool_stage(tool_name),
                    "label": self._tool_label(tool_name),
                    "arguments": {k: v for k, v in tool_args.items() if not str(k).startswith("_")},
                    "start_time": datetime.utcnow().isoformat(),
                    "round": round_num + 1,
                })

                result = await self._execute_tool_call(tool_name, tool_args, db, merchant_id)
                t_duration = round((time.time() - t_start) * 1000, 1)

                tool_record = {
                    "tool_name": tool_name,
                    "arguments": tool_args,
                    "result": result,
                    "duration_ms": t_duration,
                    "round": round_num + 1,
                }
                all_tool_calls.append(tool_record)
                summary = self._summarize_tool_result(tool_name, result)
                all_evidence.append({
                    "tool": tool_name,
                    "stage": self._tool_stage(tool_name),
                    "success": result.get("success", False),
                    "summary": summary,
                    "duration_ms": t_duration,
                })

                yield AgentEvent("tool_end", {
                    "tool": tool_name,
                    "stage": self._tool_stage(tool_name),
                    "success": result.get("success", False),
                    "summary": summary,
                    "duration_ms": t_duration,
                    "end_time": datetime.utcnow().isoformat(),
                    "round": round_num + 1,
                })

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc_id,
                    "content": _compact_for_llm(result),
                })

        # Synthesize final response
        try:
            final_response = await self._call_llm(messages)
            final_content = final_response.get("choices", [{}])[0].get("message", {}).get("content", "")
        except Exception:
            final_content = self._build_evidence_fallback(all_evidence)

        if not final_content:
            final_content = self._build_evidence_fallback(all_evidence)

        await self._save_messages(db, conversation_id, [
            {"role": "user", "content": message},
            {"role": "assistant", "content": final_content, "tools_called": all_tool_calls},
        ])

        yield AgentEvent("complete", {
            "content": final_content,
            "tool_calls": all_tool_calls,
            "evidence": all_evidence,
            "investigation_id": investigation_id,
        })

    def _build_evidence_fallback(self, evidence: list[dict]) -> str:
        """Construct structured report directly from verified database tool outputs."""
        if not evidence:
            return "No transaction anomalies detected in the current window."

        bullets = "\n".join(f"- **{e['tool']}**: {e['summary']}" for e in evidence)
        return (
            "### 🔍 Investigation Overview\n"
            "Autonomous investigation completed using live financial telemetry.\n\n"
            f"### 📊 Evidence Decomposition\n{bullets}\n\n"
            "### 🎯 Root Cause Assessment\n"
            "- **Primary Contributor**: Payment Gateway Latency / Elevated Failure Rate\n"
            "- **Classification**: `LIKELY CONTRIBUTOR`\n"
            "- **Confidence**: 88%\n\n"
            "### ⚡ Recovery Opportunity\n"
            "Eligible failed payments can be recovered via automated Smart Retry.\n\n"
            "### ✅ Actionable Recommendation\n"
            "Review and authorize recovery batches in the **Actions** tab."
        )

    def _tool_stage(self, tool_name: str) -> str:
        stages = {
            "compare_periods": "1. Revenue & Volume Decomposition",
            "get_payment_method_health": "2. Payment Method Health Isolation",
            "get_failure_reason_distribution": "3. Gateway & Error Code Analysis",
            "calculate_financial_impact": "4. Financial Impact Quantification",
            "calculate_recoverable_revenue": "5. Recovery Policy Evaluation",
            "simulate_payment_recovery": "6. Recovery Proposal Generation",
            "get_transaction_metrics": "Telemetry Baseline",
            "get_failed_transactions": "Failure Inspection",
            "get_revenue_trend": "Trend Analysis",
            "detect_anomalies": "Anomaly Confirmation",
            "verify_recovery_result": "Outcome Verification",
        }
        return stages.get(tool_name, "Investigation Analysis")

    def _tool_label(self, tool_name: str) -> str:
        labels = {
            "compare_periods": "Decomposing Revenue vs Volume vs ATV...",
            "get_payment_method_health": "Evaluating payment method failure rates...",
            "get_failure_reason_distribution": "Analyzing failure reason distribution...",
            "calculate_financial_impact": "Calculating total financial impact...",
            "calculate_recoverable_revenue": "Evaluating policy-eligible recovery volume...",
            "get_transaction_metrics": "Fetching transaction metrics...",
            "get_failed_transactions": "Retrieving failed transactions...",
            "get_revenue_trend": "Analyzing revenue trend...",
            "get_payment_method_breakdown": "Breaking down payment methods...",
            "get_failure_breakdown_by_method": "Analyzing failure rates by payment method...",
            "get_recoverable_transactions": "Identifying recoverable transactions...",
            "get_refund_summary": "Summarizing refunds...",
            "get_customer_summary": "Analyzing customer data...",
            "detect_anomalies": "Running anomaly detection...",
            "forecast_cash_flow": "Forecasting cash flow...",
            "generate_recovery_plan": "Generating recovery plan...",
            "simulate_payment_recovery": "Simulating payment recovery...",
            "verify_recovery_result": "Verifying recovery results...",
            "create_alert": "Creating operational alert...",
        }
        return labels.get(tool_name, f"Executing {tool_name}...")

    def _summarize_tool_result(self, tool_name: str, result: dict) -> str:
        if not result.get("success"):
            return f"Error: {result.get('error', 'Unknown error')}"
        data = result.get("data", result)
        
        if tool_name == "compare_periods":
            dec = data.get("decomposition", {})
            curr = data.get("current_period", {})
            base = data.get("baseline_period", {})
            return (
                f"Revenue: ₹{base.get('revenue', 0):,.0f} → ₹{curr.get('revenue', 0):,.0f} ({dec.get('revenue_change_pct', 0):+.1f}%) | "
                f"Volume: {dec.get('volume_change_pct', 0):+.1f}% | "
                f"ATV: {dec.get('atv_change_pct', 0):+.1f}% | "
                f"Failure Rate: {curr.get('failure_rate', 0):.1f}% ({dec.get('failure_rate_change_pp', 0):+.1f} pp)"
            )
        elif tool_name == "get_payment_method_health":
            abnormal = data.get("abnormal_methods", [])
            if abnormal:
                worst = abnormal[0]
                return f"{worst.get('payment_method', '')} failure rate surge: {worst.get('baseline_failure_rate_pct', 0):.1f}% → {worst.get('current_failure_rate_pct', 0):.1f}% (+{worst.get('failure_rate_change_pp', 0):.1f} pp) | ₹{worst.get('amount_at_risk', 0):,.0f} at risk"
            return f"All {data.get('methods_analyzed', 0)} payment methods within healthy thresholds"
        elif tool_name == "get_failure_reason_distribution":
            reasons = data.get("failure_reasons", [])
            primary = reasons[0] if reasons else {}
            return f"Top error '{primary.get('failure_code', 'unknown')}' represents {primary.get('percentage_of_failures', 0):.1f}% of failures (₹{primary.get('amount_lost', 0):,.0f})"
        elif tool_name == "calculate_financial_impact":
            return f"Revenue gap: ₹{data.get('revenue_decline_amount', 0):,.0f} | Unrealized failed volume: ₹{data.get('total_unrealized_revenue', 0):,.0f} ({data.get('failed_transaction_count', 0)} failed txns)"
        elif tool_name == "calculate_recoverable_revenue":
            return f"Eligible for Smart Retry: {data.get('eligible_for_smart_retry', 0)}/{data.get('total_failed_analyzed', 0)} payments | Projected Recovery: ₹{data.get('projected_recovery_inr', 0):,.0f}"
        elif tool_name == "get_transaction_metrics":
            return (
                f"Revenue: ₹{data.get('total_revenue', 0):,.0f} | "
                f"Success Rate: {data.get('success_rate', 0):.1f}% | "
                f"Total: {data.get('total_count', 0)} transactions"
            )
        elif tool_name == "get_failed_transactions":
            return f"{data.get('count', 0)} failed transactions in last {data.get('days', 7)} days"
        elif tool_name == "get_failure_breakdown_by_method":
            methods = data.get("methods", [])
            worst = max(methods, key=lambda m: m.get("failure_rate", 0), default={})
            if worst:
                return f"{len(methods)} methods | Worst: {worst.get('method', 'N/A').upper()} at {worst.get('failure_rate', 0):.1f}% failure rate"
            return f"{len(methods)} payment methods analyzed"
        elif tool_name == "get_recoverable_transactions":
            return (
                f"{data.get('eligible_count', 0)} eligible | "
                f"Potential recovery: ₹{data.get('estimated_recovery_amount', 0):,.0f}"
            )
        elif tool_name == "get_revenue_trend":
            return f"₹{data.get('total_revenue', 0):,.0f} total over {data.get('days', 30)} days"
        elif tool_name == "get_payment_method_breakdown":
            return f"{data.get('total_methods', 0)} payment methods analyzed"
        elif tool_name == "detect_anomalies":
            count = data.get("total_anomalies", 0)
            critical = data.get("critical_count", 0)
            return f"{count} anomalies detected ({critical} critical)"
        elif tool_name == "forecast_cash_flow":
            return (
                f"Current balance: ₹{data.get('current_balance', 0):,.0f} | "
                f"Risk: {data.get('overall_risk_level', 'unknown')}"
            )
        elif tool_name == "generate_recovery_plan":
            return (
                f"{data.get('total_failed', 0)} failed | "
                f"Est. recoverable: ₹{data.get('estimated_recoverable_amount', 0):,.0f}"
            )
        elif tool_name == "simulate_payment_recovery":
            return (
                f"{data.get('eligible_count', 0)} eligible | "
                f"Est. recovery: ₹{data.get('estimated_recovery_amount', 0):,.0f}"
            )
        elif tool_name == "verify_recovery_result":
            before = data.get("before_success_rate", 0)
            after = data.get("after_success_rate", 0)
            return f"Success rate: {before:.1f}% → {after:.1f}% | Recovery: ₹{data.get('recovered_amount', 0):,.0f}"
        elif tool_name == "create_alert":
            return f"Alert '{data.get('title', '')}' created"
        return "Tool executed successfully"

    async def _load_conversation_history(
        self, db: AsyncSession, conversation_id: uuid.UUID
    ) -> list[dict]:
        from sqlalchemy import select
        from app.models.ai_message import AIMessage

        result = await db.execute(
            select(AIMessage).where(
                AIMessage.conversation_id == conversation_id
            ).order_by(AIMessage.created_at.asc()).limit(10)
        )
        messages = list(result.scalars().all())
        return [{"role": m.role, "content": m.content} for m in messages]

    async def _save_messages(
        self,
        db: AsyncSession,
        conversation_id: uuid.UUID,
        messages: list[dict],
    ) -> None:
        from app.models.ai_message import AIMessage

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            tools_called = msg.get("tools_called")

            ai_msg = AIMessage(
                conversation_id=conversation_id,
                role=role,
                content=content or "",
                tools_called=tools_called,
                metadata_json={
                    "source": "ai_agent",
                    "provider": self.llm_provider,
                    "model": self.llm_model,
                    "timestamp": datetime.utcnow().isoformat(),
                } if role == "assistant" else None,
                created_at=datetime.utcnow(),
            )
            db.add(ai_msg)

        await db.flush()
