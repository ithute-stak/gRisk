import { NextRequest, NextResponse } from "next/server";

import { SESSION_COOKIE, sessionCookieSecure } from "@/lib/server-session";

export async function POST(request: NextRequest) {
  if (request.headers.get("x-grisk-request") !== "1") {
    return NextResponse.json({ detail: "Invalid application request." }, { status: 403 });
  }
  const response = NextResponse.json({ ok: true });
  response.headers.set("Cache-Control", "no-store");
  response.cookies.set({
    name: SESSION_COOKIE,
    value: "",
    httpOnly: true,
    secure: sessionCookieSecure(),
    sameSite: "strict",
    path: "/",
    maxAge: 0,
  });
  return response;
}
