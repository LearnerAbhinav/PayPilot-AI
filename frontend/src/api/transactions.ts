import type { TransactionListResponse, TransactionFilters } from "../types";
import { apiClient } from "./client";

export async function getTransactions(
  filters: TransactionFilters = {},
): Promise<TransactionListResponse> {
  return apiClient.get<TransactionListResponse>("/transactions/", { params: filters as Record<string, string | number> });
}

export async function getTransaction(id: string) {
  return apiClient.get(`/transactions/${id}`);
}

export async function getFailedTransactions(days: number = 7) {
  return apiClient.get(`/transactions/failed`, { params: { days } });
}
