import { NextResponse } from "next/server";

import { AUTH_COOKIE, authToken } from "@/lib/auth";

export async function POST(request: Request) {
  const form = await request.formData();
  const password = process.env.APP_PASSWORD;
  if (!password || form.get("password") !== password) {
    return NextResponse.redirect(new URL("/login?error=1", request.url), 303);
  }
  const res = NextResponse.redirect(new URL("/", request.url), 303);
  res.cookies.set(AUTH_COOKIE, await authToken(password), {
    httpOnly: true,
    sameSite: "lax",
    secure: new URL(request.url).protocol === "https:",
    maxAge: 60 * 60 * 24 * 90,
    path: "/",
  });
  return res;
}
