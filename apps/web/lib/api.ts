"use client";

import { clearUser } from "@/lib/auth";
import type { AuthUser } from "@/lib/types";

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
    if (Array.isArray(payload.detail)) {
      return payload.detail.map((item) => item.msg).filter(Boolean).join("; ") || text;
    }
  } catch {
    // Preserve the upstream response when it is not JSON.
  }
  return text;
}

async function handleUnauthorized(response: Response): Promise<void> {
  if (response.status !== 401) return;
  clearUser();
  if (typeof window !== "undefined") window.location.assign("/login");
}

export async function apiRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  const method = (init.method ?? "GET").toUpperCase();
  if (!["GET", "HEAD", "OPTIONS"].includes(method)) {
    headers.set("X-gRisk-Request", "1");
  }
  if (init.body && !(init.body instanceof FormData) && !(init.body instanceof URLSearchParams)) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(proxyUrl(path), {
    ...init,
    method,
    headers,
    cache: "no-store",
  });
  if (!response.ok) {
    const message = await readError(response);
    await handleUnauthorized(response);
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

export function apiUpload<T>(path: string, form: FormData): Promise<T> {
  return apiRequest<T>(path, { method: "POST", body: form });
}

export async function apiDownload(path: string): Promise<{ blob: Blob; filename: string | null }> {
  const response = await fetch(proxyUrl(path), { method: "GET", cache: "no-store" });
  if (!response.ok) {
    const message = await readError(response);
    await handleUnauthorized(response);
    throw new ApiError(message, response.status);
  }
  const disposition = response.headers.get("content-disposition");
  const filenameMatch = disposition?.match(/filename\*?=(?:UTF-8''|\")?([^\";]+)/i);
  const filename = filenameMatch ? decodeURIComponent(filenameMatch[1].replace(/^\"|\"$/g, "")) : null;
  return { blob: await response.blob(), filename };
}

export async function login(email: string, password: string): Promise<AuthUser> {
  const response = await fetch("/api/session/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email: email.trim(), password }),
    cache: "no-store",
  });
  if (!response.ok) {
    throw new ApiError(await readError(response), response.status);
  }
  return (await response.json()) as AuthUser;
}

export async function logout(): Promise<void> {
  try {
    await fetch("/api/session/logout", { method: "POST", cache: "no-store" });
  } finally {
    clearUser();
  }
}
