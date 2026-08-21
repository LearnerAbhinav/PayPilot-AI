import { apiClient } from "./client";

export async function detectAnomalies() {
  return apiClient.get("/anomalies/detect");
}

export async function getAnomalies() {
  return apiClient.get("/anomalies/");
}
