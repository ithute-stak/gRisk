import { cookies } from "next/headers";
import { type NextRequest, NextResponse } from "next/server";

import { SESSION_COOKIE, apiBaseUrl, sessionCookieSecure } from "@/lib/server-session";

export const dynamic = "force-dynamic";

const SAFE_METHODS = new Set(["GET", "HEAD", "OPTIONS"]);

async function proxy(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  const { path } = await context.params;
  const upstreamPath = path.join("/");
  if (upstreamPath === "api/v1/auth/login") {
    return NextResponse.json({ detail: "Use the secure session endpoint." }, { status: 404 });
  }

  const method = request.method.toUpperCase();
  if (!SAFE_METHODS.has(method) && request.headers.get("x-grisk-request") !== "1") {
    return NextResponse.json({ detail: "Invalid application request." }, { status: 403 });
  }

  const target = new URL(`${apiBaseUrl()}/${upstreamPath}`);
  request.nextUrl.searchParams.forEach((value, key) => target.searchParams.append(key, value));

  const headers = new Headers(request.headers);
  for (const name of [
    "host",
    "content-length",
    "connection",
    "accept-encoding",
    "authorization",
    "cookie",
    "x-grisk-request",
  ]) {
    headers.delete(name);
  }

  const cookieStore = await cookies();
  const token = cookieStore.get(SESSION_COOKIE)?.value;
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const body = method === "GET" || method === "HEAD" ? undefined : await request.arrayBuffer();
  const upstream = await fetch(target, {
    method,
    headers,
    body,
    redirect: "manual",
    cache: "no-store",
  });

  const responseHeaders = new Headers(upstream.headers);
  responseHeaders.delete("content-encoding");
  responseHeaders.delete("content-length");
  responseHeaders.delete("transfer-encoding");
  responseHeaders.set("Cache-Control", "no-store");

  const response = new NextResponse(upstream.body, {
    status: upstream.status,
    statusText: upstream.statusText,
    headers: responseHeaders,
  });
  if (upstream.status === 401) {
    response.cookies.set({
      name: SESSION_COOKIE,
      value: "",
      httpOnly: true,
      secure: sessionCookieSecure(),
      sameSite: "strict",
      path: "/",
      maxAge: 0,
    });
  }
  return response;
}

export const GET = proxy;
export const POST = proxy;
export const PUT = proxy;
export const PATCH = proxy;
export const DELETE = proxy;
export const OPTIONS = proxy;
