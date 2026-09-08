"use client";

import type { AuthUser } from "@/lib/types";

const USER_STORAGE_KEY = "grisk.user";

function isAuthUser(value: unknown): value is AuthUser {
  if (!value || typeof value !== "object") return false;
  const candidate = value as Partial<AuthUser>;
  return (
    typeof candidate.id === "string" &&
    candidate.id.length > 0 &&
    Array.isArray(candidate.roles) &&
    candidate.roles.every((role) => typeof role === "string") &&
    typeof candidate.isSuperuser === "boolean"
  );
}

export function saveUser(user: AuthUser): void {
  if (typeof window === "undefined") return;
  sessionStorage.setItem(USER_STORAGE_KEY, JSON.stringify(user));
  window.dispatchEvent(new Event("grisk-session"));
}

export function clearUser(): void {
  if (typeof window === "undefined") return;
  sessionStorage.removeItem(USER_STORAGE_KEY);
  window.dispatchEvent(new Event("grisk-session"));
}

export function currentUser(): AuthUser | null {
  if (typeof window === "undefined") return null;
  const raw = sessionStorage.getItem(USER_STORAGE_KEY);
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as unknown;
    if (!isAuthUser(parsed)) {
      sessionStorage.removeItem(USER_STORAGE_KEY);
      return null;
    }
    return parsed;
  } catch {
    sessionStorage.removeItem(USER_STORAGE_KEY);
    return null;
  }
}

export async function refreshCurrentUser(): Promise<AuthUser | null> {
  const response = await fetch("/api/session/me", { cache: "no-store" });
  if (response.status === 401) {
    clearUser();
    return null;
  }
  if (!response.ok) {
    throw new Error("Unable to verify the current gRisk session.");
  }
  const user = (await response.json()) as unknown;
  if (!isAuthUser(user)) {
    clearUser();
    throw new Error("Authentication service returned an invalid user session.");
  }
  saveUser(user);
  return user;
}
