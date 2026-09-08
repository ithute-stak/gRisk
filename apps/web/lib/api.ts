"use client";

import { clearToken, getToken } from "@/lib/auth";

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
  }
}

function proxyUrl(path: string): string {
  const normalized = path.startsWith("/") ? path : `/${path}`;
  return `/api/proxy${normalized}`;
}

async function readError(response: Response): Promise<string> {
  const text = await response.text();
  if (!text) return `gRisk API request failed (${response.status}).`;
  try {
    const payload = JSON.parse(text) as { detail?: string | Array<{ msg?: string }> };
    if (typeof payload.detail === "string") return payload.detail;
    if (Array.isArray(payload.detail)) return payload.detail.map((item) => item.msg).filter(Boolean).join("; ") || text;
  } catch {
    // Preserve the upstream response when it is not JSON.
  }
  return text;
}

export async function apiRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (init.body && !(init.body instanceof FormData) && !(init.body instanceof URLSearchParams)) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(proxyUrl(path), { ...init, headers, cache: "no-store" });
  if (!response.ok) {
    const message = await readError(response);
    if (response.status === 401) {
      clearToken();
      if (typeof window !== "undefined") window.location.assign("/login");
    }
    throw new ApiError(message, response.status);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export function apiGet<T>(path: string): Promise<T> {
  return apiRequest<T>(path);
}

export function apiPost<T>(path: string, payload: unknown): Promise<T> {
  return apiRequest<T>(path, { method: "POST", body: JSON.stringify(payload) });
}

export function apiPatch<T>(path: string, payload: unknown): Promise<T> {
  return apiRequest<T>(path, { method: "PATCH", body: JSON.stringify(payload) });
}

export async function login(email: string, password: string): Promise<{ access_token: string }> {
  const body = new URLSearchParams({ username: email.trim(), password });
  const response = await fetch(proxyUrl("/api/v1/auth/login"), {
    method: "POST",
    body,
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    cache: "no-store",
  });
  if (!response.ok) throw new ApiError("The email address or password is incorrect.", response.status);
  return (await response.json()) as { access_token: string };
}
