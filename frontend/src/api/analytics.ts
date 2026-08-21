import { apiClient } from "./client";

export async function getMetrics(days: number = 30) {
  return apiClient.get("/analytics/metrics", { params: { days } });
}

export async function getRevenueTrend(days: number = 30) {
  return apiClient.get("/analytics/revenue-trend", { params: { days } });
}

export async function getPaymentMethodBreakdown(days: number = 30) {
  return apiClient.get("/analytics/payment-methods", { params: { days } });
}

export async function getDashboard() {
  return apiClient.get("/analytics/dashboard");
}
