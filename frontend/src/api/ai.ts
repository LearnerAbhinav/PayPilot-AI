import { apiClient } from "./client";

export async function sendMessage(message: string, conversationId?: string | null) {
  return apiClient.post("/ai/chat", {
    message,
    conversation_id: conversationId ?? null,
  });
}

export async function getConversations() {
  return apiClient.get("/ai/conversations");
}

export async function getConversation(id: string) {
  return apiClient.get(`/ai/conversations/${id}`);
}

export async function createConversation(title?: string) {
  return apiClient.post("/ai/conversations", { title: title ?? null });
}

export interface AIInfoResponse {
  provider: string;
  model: string;
  tools_count: number;
  tool_names: string[];
  is_configured: boolean;
  simulation_mode: boolean;
}

export async function getAIInfo(): Promise<AIInfoResponse> {
  return apiClient.get<AIInfoResponse>("/ai/info");
}
