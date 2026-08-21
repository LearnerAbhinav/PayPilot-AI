function getBaseUrl(): string {
  const envUrl = import.meta.env.VITE_API_URL;
  if (!envUrl) return "/api";
  const trimmed = envUrl.trim().replace(/\/+$/, "");
  return trimmed.endsWith("/api") ? trimmed : `${trimmed}/api`;
}

const BASE_URL = getBaseUrl();

function getToken(): string | null {
  return localStorage.getItem("paypilot_token");
}

interface RequestOptions extends Omit<RequestInit, "method" | "body"> {
  params?: Record<string, string | number | boolean | undefined | null>;
}

async function request<T>(
  method: string,
  path: string,
  body?: unknown,
  options: RequestOptions = {},
): Promise<T> {
  const { params, ...fetchOptions } = options;

  const cleanPath = path.startsWith("/") ? path : `/${path}`;
  let urlStr = `${BASE_URL}${cleanPath}`;
  if (params) {
    const sp = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value != null) {
        sp.set(key, String(value));
      }
    });
    const qs = sp.toString();
    if (qs) urlStr += `?${qs}`;
  }

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(fetchOptions.headers as Record<string, string>),
  };

  const token = getToken();
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(urlStr, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
    ...fetchOptions,
  });

  if (!response.ok) {
    if (response.status === 401) {
      localStorage.removeItem("paypilot_token");
      if (window.location.pathname !== "/login") {
        window.location.href = "/login";
      }
    }
    const errorBody = await response.json().catch(() => null);
    const message = errorBody?.detail || `Request failed: ${response.status}`;
    throw new Error(message);
  }

  return response.json();
}

const apiClient = {
  get: <T>(path: string, options?: RequestOptions) =>
    request<T>("GET", path, undefined, options),
  post: <T>(path: string, body?: unknown, options?: RequestOptions) =>
    request<T>("POST", path, body, options),
  put: <T>(path: string, body?: unknown, options?: RequestOptions) =>
    request<T>("PUT", path, body, options),
  delete: <T>(path: string, options?: RequestOptions) =>
    request<T>("DELETE", path, undefined, options),
};

export { apiClient };
