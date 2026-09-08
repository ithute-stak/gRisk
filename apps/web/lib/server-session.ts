import type { AuthUser } from "@/lib/types";

export const SESSION_COOKIE = "grisk_session";

export type ApiUser = {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  is_superuser: boolean;
  roles: string[];
};

export function apiBaseUrl(): string {
  return (process.env.API_BASE_URL ?? "http://api:8000").replace(/\/$/, "");
}

export function toAuthUser(user: ApiUser): AuthUser {
  return {
    id: user.id,
    email: user.email,
    name: user.full_name,
    roles: user.roles,
    isSuperuser: user.is_superuser,
  };
}

export function sessionCookieSecure(): boolean {
  return process.env.GRISK_COOKIE_SECURE === "true";
}

export function tokenMaxAgeSeconds(token: string): number {
  try {
    const payloadPart = token.split(".")[1];
    if (!payloadPart) return 3600;
    const payload = JSON.parse(Buffer.from(payloadPart, "base64url").toString("utf8")) as {
      exp?: number;
    };
    if (typeof payload.exp !== "number") return 3600;
    return Math.max(1, Math.min(86400, payload.exp - Math.floor(Date.now() / 1000)));
  } catch {
    return 3600;
  }
}
