import { apiClient } from "./client";

export async function getCashFlowForecast(days: number = 7) {
  return apiClient.get("/forecast/cash-flow", { params: { days } });
}
