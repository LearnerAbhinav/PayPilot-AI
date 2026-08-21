export interface User {
  id: string;
  email: string;
  name?: string;
  full_name?: string;
  role: string;
  merchant_id?: string;
  is_active?: boolean;
}

export interface AuthResponse {
  token: string;
  user: User;
}

export interface Transaction {
  id: string;
  merchant_id?: string;
  customer_id?: string | null;
  amount: number;
  currency: string;
  status: 'captured' | 'failed' | 'pending' | 'refunded' | 'authorized';
  payment_method: string;
  payment_gateway?: string | null;
  failure_code?: string | null;
  failure_reason?: string | null;
  customer_name?: string;
  customer_email?: string;
  description?: string | null;
  metadata_json?: string | null;
  created_at: string;
  updated_at: string;
}

export interface TransactionListResponse {
  items: Transaction[];
  transactions?: Transaction[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface TransactionFilters {
  status?: string;
  payment_method?: string;
  payment_gateway?: string;
  start_date?: string;
  end_date?: string;
  customer_id?: string;
  page?: number;
  page_size?: number;
}

export interface MetricSummary {
  label: string;
  value: number;
  change: number;
  change_label: string;
}

export interface RevenueTrendPoint {
  date: string;
  revenue: number;
  transactions?: number;
  successful_transactions?: number;
}

export interface PaymentMethodBreakdown {
  method: string;
  count: number;
  revenue?: number;
  amount?: number;
  percentage: number;
  success_rate?: number;
}

export interface AnalyticsSummary {
  total_revenue: number;
  total_transactions: number;
  success_rate: number;
  failed_payments: number;
  refunds: number;
  avg_transaction_value: number;
}

export interface PeriodComparison {
  current: number;
  previous: number;
  change: number;
  label: string;
}

export interface AnalyticsResponse {
  summary: AnalyticsSummary;
  revenue_trend: RevenueTrendPoint[];
  payment_methods: PaymentMethodBreakdown[];
  metrics: MetricSummary[];
  period_comparisons: PeriodComparison[];
}

export interface ForecastPoint {
  date: string;
  actual: number | null;
  predicted: number | null;
  lower_bound: number;
  upper_bound: number;
}

export interface CashFlowForecast {
  current_balance: number;
  forecast: ForecastPoint[];
  total_inflow: number;
  total_outflow: number;
  net_flow: number;
  risk_level: 'low' | 'medium' | 'high';
  overall_risk_level?: 'low' | 'medium' | 'high';
  assumptions: string[];
}

export interface Anomaly {
  id: string;
  type: string;
  metric: string;
  current_value: number;
  baseline_value: number;
  baseline?: number;
  percentage_change: number;
  severity: 'critical' | 'high' | 'warning' | 'medium' | 'info';
  explanation: string;
  detected_at: string;
  is_resolved?: boolean;
}

export interface AnomalyDetectionResponse {
  items: Anomaly[];
  anomalies?: Anomaly[];
  total: number;
  unresolved_count?: number;
  critical_count?: number;
  detected_at?: string;
}

export interface DashboardResponse {
  summary: AnalyticsSummary;
  revenue_trend: RevenueTrendPoint[];
  payment_methods: PaymentMethodBreakdown[];
  recent_anomalies: Anomaly[];
  cash_flow_summary: {
    current_balance: number;
    risk_level: string;
    net_flow: number;
  };
}

export interface ActionResponse {
  id: string;
  merchant_id?: string;
  conversation_id?: string | null;
  user_id?: string;
  action_type: string;
  type?: string;
  action_class: string;
  description: string;
  reason?: string | null;
  input_data?: Record<string, any> | null;
  output_data?: Record<string, any> | null;
  estimated_impact?: number | string | null;
  risk_level?: 'low' | 'medium' | 'high' | 'critical' | string | null;
  approval_status: 'pending' | 'approved' | 'rejected' | 'expired' | string;
  execution_status: 'not_started' | 'in_progress' | 'completed' | 'failed' | string;
  status?: 'pending' | 'approved' | 'rejected' | 'executed' | 'completed' | string;
  approved_by?: string | null;
  approved_at?: string | null;
  executed_at?: string | null;
  created_at: string;
}

export interface ChatRequest {
  message: string;
  conversation_id: string | null;
}

export interface MessageResponse {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  tools_called?: any[];
  token_count?: number;
}

export interface ChatResponse {
  conversation_id: string;
  message: MessageResponse;
  tools_called?: any[];
  suggestions?: string[];
  id?: string;
  response?: string;
  created_at?: string;
}

export interface ConversationResponse {
  id: string;
  merchant_id?: string;
  user_id?: string;
  title: string;
  messages?: MessageResponse[];
  created_at: string;
  updated_at: string;
}

export interface AuditLogListResponse {
  items: AuditLogEntry[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface AuditLogEntry {
  id: string;
  merchant_id?: string;
  user_id?: string | null;
  action: string;
  resource_type?: string | null;
  resource_id?: string | null;
  details?: Record<string, any> | string | null;
  user_prompt?: string | null;
  agent_decision?: string | null;
  tools_called?: string[] | null;
  tool_inputs?: Record<string, any> | null;
  tool_outputs?: Record<string, any> | null;
  ip_address?: string | null;
  created_at: string;
  user?: string;
  entity_type?: string;
  entity_id?: string;
}
