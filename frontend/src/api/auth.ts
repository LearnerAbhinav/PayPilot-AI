import { apiClient } from "./client";
import type { AuthResponse, UserProfile } from "../types/api";

export async function login(email: string, password: string): Promise<AuthResponse> {
  return apiClient.post<AuthResponse>("/auth/login", { email, password });
}

export async function register(
  fullName: string,
  email: string,
  password: string,
): Promise<AuthResponse> {
  return apiClient.post<AuthResponse>("/auth/register", {
    full_name: fullName,
    email,
    password,
    business_name: `${fullName}'s Business`,
  });
}

export async function getProfile(): Promise<UserProfile> {
  return apiClient.get<UserProfile>("/auth/me");
}
