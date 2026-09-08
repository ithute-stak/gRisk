import { NextResponse } from "next/server";

import { SESSION_COOKIE, sessionCookieSecure } from "@/lib/server-session";

export async function POST() {
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
