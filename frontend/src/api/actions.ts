import { apiClient } from "./client";

export interface ActionTransactionItem {
  id: string;
  amount: number;
  currency: string;
  payment_method: string;
  failure_code: string;
  failure_reason: string;
  created_at: string;
  eligible: boolean;
  eligibility_reason: string;
  policy_passed_rules: number;
}

export interface ActionTransactionsResponse {
  action_id: string;
  policy_version: string;
  total_eligible_count: number;
  total_eligible_amount: number;
  why_this_action: string[];
  transactions: ActionTransactionItem[];
}

export async function getActions(status?: string) {
  return apiClient.get("/actions/", { params: status ? { status_filter: status } : undefined });
}

export async function getAction(id: string) {
  return apiClient.get(`/actions/${id}`);
}

export async function getActionTransactions(id: string): Promise<ActionTransactionsResponse> {
  return apiClient.get(`/actions/${id}/transactions`);
}

export async function approveAction(id: string) {
  return apiClient.post(`/actions/${id}/approve`);
}

export async function rejectAction(id: string) {
  return apiClient.post(`/actions/${id}/reject`);
}

export async function executeAction(id: string) {
  return apiClient.post(`/actions/${id}/execute`);
}
