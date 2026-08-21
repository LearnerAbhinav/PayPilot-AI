import { apiClient } from "./client";

export async function getAuditLogs(page?: number, pageSize?: number) {
  return apiClient.get("/audit/", { params: { page, page_size: pageSize } });
}
