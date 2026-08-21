import { apiClient } from "./client";

export interface InvestigationStartRequest {
  message: string;
  anomaly_type?: string;
  severity?: string;
  title?: string;
}

export interface InvestigationEvent {
  id?: string;
  stage?: string;
  tool_name?: string;
  label?: string;
  start_time?: string;
  end_time?: string;
  duration_ms?: number;
  status?: string;
  summary?: string;
  arguments?: Record<string, unknown>;
}

export interface InvestigationEvidenceClaim {
  claim: string;
  source_tool: string;
  metric?: string;
  value?: string;
  counter_indicator?: string;
}

export interface InvestigationMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  tools_called?: Array<{ tool_name: string; round: number }>;
  created_at: string;
}

export interface InvestigationResponse {
  id: string;
  title: string;
  status: string;
  severity: string;
  anomaly_type?: string | null;
  user_request?: string | null;
  events?: InvestigationEvent[] | null;
  evidence?: Array<Record<string, unknown>> | null;
  findings?: Record<string, unknown> | null;
  root_cause?: string | null;
  supporting_evidence?: InvestigationEvidenceClaim[] | null;
  contradictory_evidence?: InvestigationEvidenceClaim[] | null;
  classification?: string | null;
  confidence_score?: number | null;
  financial_impact?: {
    revenue_gap?: number;
    volume_loss?: number;
    failure_loss?: number;
    unrealized_revenue?: number;
    affected_count?: number;
    affected_amount?: number;
    recoverable_amount?: number;
  } | null;
  recovery_opportunity?: {
    eligible_transactions?: number;
    eligible_amount_inr?: number;
    recoverable_amount?: number;
    policy_version?: string;
  } | null;
  recommendation?: string | null;
  agent_summary?: string | null;
  confidence?: string | null;
  risk?: string | null;
  action_id?: string | null;
  action?: Record<string, unknown> | null;
  conversation_id?: string | null;
  messages?: InvestigationMessage[] | null;
  created_at: string;
  updated_at?: string | null;
}

export interface MonitoringStatusResponse {
  status: string;
  autonomous_mode: boolean;
  actions_paused: boolean;
  last_scan: string;
  metrics_monitored: number;
  active_anomalies: number;
  investigations_count: number;
  pending_actions_count: number;
  freshness: {
    transactions_sec: number;
    payment_telemetry_sec: number;
    cash_flow_sec: number;
  };
  simulation_mode: boolean;
}

export async function startInvestigation(
  req: InvestigationStartRequest
): Promise<{ id: string; conversation_id: string; title: string; status: string; created_at: string }> {
  return apiClient.post("/investigations", req);
}

export async function getInvestigations(status?: string): Promise<InvestigationResponse[]> {
  const url = status ? `/investigations?status=${status}` : "/investigations";
  return apiClient.get(url);
}

export async function getInvestigation(id: string): Promise<InvestigationResponse> {
  return apiClient.get(`/investigations/${id}`);
}

export async function runMonitoringCycle(): Promise<{
  status: string;
  timestamp: string;
  anomalies_detected: number;
  investigations_triggered: number;
  actions_proposed: number;
  autonomous_paused: boolean;
}> {
  return apiClient.post("/monitoring/run", {});
}

export async function getMonitoringStatus(): Promise<MonitoringStatusResponse> {
  return apiClient.get("/monitoring/status");
}

export async function toggleAutonomousActions(): Promise<{
  status: string;
  actions_paused: boolean;
  message: string;
}> {
  return apiClient.post("/monitoring/toggle-pause", {});
}

export interface AgentStreamEvent {
  type:
    | "started"
    | "tool_start"
    | "tool_end"
    | "finding"
    | "complete"
    | "error";
  data: Record<string, unknown>;
}

export async function streamInvestigationWithAuth(
  investigationId: string,
  onEvent: (event: AgentStreamEvent) => void,
  onDone: () => void,
  onError: (err: string) => void
): Promise<void> {
  const token = localStorage.getItem("paypilot_token");
  const baseUrl = import.meta.env.VITE_API_URL || "/api";
  const url = `${baseUrl}/investigations/${investigationId}/stream`;

  let response: Response;
  try {
    response = await fetch(url, {
      headers: {
        Authorization: token ? `Bearer ${token}` : "",
        Accept: "text/event-stream",
      },
    });
  } catch (err) {
    onError(`Connection failed: ${err}`);
    return;
  }

  if (!response.ok) {
    onError(`Stream error: HTTP ${response.status}`);
    return;
  }

  const reader = response.body?.getReader();
  if (!reader) {
    onError("No response body");
    return;
  }

  const decoder = new TextDecoder();
  let buffer = "";

  // eslint-disable-next-line no-constant-condition
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";

    let currentEvent = "";
    let currentData = "";

    for (const line of lines) {
      if (line.startsWith("event: ")) {
        currentEvent = line.slice(7).trim();
      } else if (line.startsWith("data: ")) {
        currentData = line.slice(6).trim();
      } else if (line === "" && currentEvent && currentData) {
        try {
          const parsed = JSON.parse(currentData);
          onEvent({ type: currentEvent as AgentStreamEvent["type"], data: parsed });
          if (currentEvent === "complete" || currentEvent === "error") {
            onDone();
            reader.cancel();
            return;
          }
        } catch {
          // ignore parse errors
        }
        currentEvent = "";
        currentData = "";
      }
    }
  }

  onDone();
}
