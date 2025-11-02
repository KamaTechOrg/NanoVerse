// src/utils/api.ts
import {
  RegisterRequest,
  LoginRequest,
  AuthResponse,
  RegisterResponse,
  User,
} from "../types/auth";

// Determine API base URL based on current location
function getApiBaseUrl(): string {
  // Use VITE_API_BASE if set in environment
  const envUrl = import.meta.env.VITE_API_BASE;
  if (envUrl) return envUrl;

  // Otherwise use current origin (same protocol, host, port)
  // This ensures it works on desktop, mobile, and any domain
  return window.location.origin;
}

const API_BASE_URL = getApiBaseUrl();

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

async function apiRequest<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  console.log(`[apiRequest] START ${options.method ?? "GET"} ${url}`);

  const controller = new AbortController();
  const timeoutMs = 20000; // 20s during dev
  const timeoutId = setTimeout(() => {
    controller.abort();
  }, timeoutMs);

  const finalOptions: RequestInit = {
    ...options,
    signal: controller.signal,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers ?? {}),
    },
  };

  let res: Response;
  try {
    console.log("trying to fetch the url in the api.ts file", url);

    res = await fetch(url, finalOptions);
    console.log("succeed to fetch the url !!!");
    
  } catch (err: any) {
    clearTimeout(timeoutId);
    console.error(`[apiRequest] FETCH FAILED ${url}:`, err && (err.name || err.message) ? err : err);
    if (err && err.name === "AbortError") {
      throw new ApiError(0, "timeout");
    }
    throw new ApiError(0, err?.message ?? String(err));
  } finally {
    clearTimeout(timeoutId);
  }

  console.log(`[apiRequest] FIN ${res.status} ${url}`);

  if (!res.ok) {
    let msg = `HTTP ${res.status}`;
    try {
      const j = await res.json();
      msg = j?.detail || j?.error || JSON.stringify(j);
    } catch { /* ignore */ }
    throw new ApiError(res.status, msg);
  }

  // Try to parse JSON — in case of empty response return empty object
  try {
    const text = await res.text();
    if (!text) return {} as T;
    return JSON.parse(text) as T;
  } catch (e) {
    console.error("[apiRequest] json parse error:", e);
    throw new ApiError(0, "invalid_json");
  }
}


export const authApi = {
  register(data: RegisterRequest): Promise<RegisterResponse> {
    return apiRequest<RegisterResponse>("/auth/register", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  login(data: LoginRequest): Promise<AuthResponse> {
    console.log('[api.ts] try do the login');

    return apiRequest<AuthResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  health(): Promise<{ ok: boolean; service: string }> {
    return apiRequest<{ ok: boolean; service: string }>("/health");
  },
};

// ---------- Helpers ----------
export const authHeader = (token?: string | null): Record<string, string> =>
  token ? { Authorization: `Bearer ${token}` } : {};


export type { User };
export default { authApi, apiRequest, authHeader };