import { NextRequest, NextResponse } from "next/server";

import {
  SESSION_COOKIE,
  apiBaseUrl,
  sessionCookieSecure,
  toAuthUser,
  tokenMaxAgeSeconds,
  type ApiUser,
} from "@/lib/server-session";

export const dynamic = "force-dynamic";

function loginError(status: number, detail?: string): NextResponse {
  const message = status === 429 && detail ? detail : "The email address or password is incorrect.";
  return NextResponse.json({ detail: message }, { status });
}

export async function POST(request: NextRequest) {
  if (request.headers.get("x-grisk-request") !== "1") {
    return NextResponse.json({ detail: "Invalid application request." }, { status: 403 });
  }

  let payload: { email?: unknown; password?: unknown };
  try {
    payload = (await request.json()) as { email?: unknown; password?: unknown };
  } catch {
    return NextResponse.json({ detail: "Invalid sign-in request." }, { status: 400 });
  }

  const email = typeof payload.email === "string" ? payload.email.trim().toLowerCase() : "";
  const password = typeof payload.password === "string" ? payload.password : "";
  if (!email || !password) {
    return NextResponse.json({ detail: "Email address and password are required." }, { status: 422 });
  }

  const loginBody = new URLSearchParams({ username: email, password });
  const loginResponse = await fetch(`${apiBaseUrl()}/api/v1/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: loginBody,
    cache: "no-store",
  });
  if (!loginResponse.ok) {
    let detail: string | undefined;
    try {
      const errorPayload = (await loginResponse.json()) as { detail?: unknown };
      if (typeof errorPayload.detail === "string") detail = errorPayload.detail;
    } catch {
      // Keep authentication failures generic unless FastAPI supplied a safe rate-limit message.
    }
    return loginError(loginResponse.status, detail);
  }

  const tokenPayload = (await loginResponse.json()) as { access_token?: unknown };
  const token = typeof tokenPayload.access_token === "string" ? tokenPayload.access_token : "";
  if (!token) {
    return NextResponse.json({ detail: "Authentication service returned an invalid response." }, { status: 502 });
  }

  const meResponse = await fetch(`${apiBaseUrl()}/api/v1/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });
  if (!meResponse.ok) {
    return NextResponse.json({ detail: "Unable to establish a secure session." }, { status: 502 });
  }

  const user = toAuthUser((await meResponse.json()) as ApiUser);
  const response = NextResponse.json(user);
  response.headers.set("Cache-Control", "no-store");
  response.cookies.set({
    name: SESSION_COOKIE,
    value: token,
    httpOnly: true,
    secure: sessionCookieSecure(),
    sameSite: "strict",
    path: "/",
    maxAge: tokenMaxAgeSeconds(token),
  });
  return response;
}
