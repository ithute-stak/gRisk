"use client";

import type { AuthUser } from "@/lib/types";

const STORAGE_KEY = "grisk.access_token";

function decodeBase64Url(value: string): string {
  const normalized = value.replace(/-/g, "+").replace(/_/g, "/");
  const padded = normalized.padEnd(normalized.length + ((4 - (normalized.length % 4)) % 4), "=");
  return atob(padded);
}

export function parseUser(token: string | null): AuthUser | null {
  if (!token) return null;
  try {
    const parts = token.split(".");
    if (parts.length !== 3) return null;
    const payload = JSON.parse(decodeBase64Url(parts[1])) as Record<string, unknown>;
    const sub = typeof payload.sub === "string" ? payload.sub : null;
    if (!sub) return null;
    if (typeof payload.exp === "number" && payload.exp * 1000 <= Date.now()) return null;
    return {
      id: sub,
      email: typeof payload.email === "string" ? payload.email : undefined,
      name: typeof payload.name === "string" ? payload.name : undefined,
      roles: Array.isArray(payload.roles) ? payload.roles.filter((role): role is string => typeof role === "string") : [],
      isSuperuser: payload.is_superuser === true,
    };
  } catch {
    return null;
  }
}

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  const token = sessionStorage.getItem(STORAGE_KEY);
  if (token && !parseUser(token)) {
    sessionStorage.removeItem(STORAGE_KEY);
    return null;
  }
  return token;
}

export function saveToken(token: string): void {
  sessionStorage.setItem(STORAGE_KEY, token);
  window.dispatchEvent(new Event("grisk-session"));
}

export function clearToken(): void {
  sessionStorage.removeItem(STORAGE_KEY);
  window.dispatchEvent(new Event("grisk-session"));
}

export function currentUser(): AuthUser | null {
  return parseUser(getToken());
}
