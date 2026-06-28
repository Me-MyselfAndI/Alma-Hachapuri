import { NextResponse } from "next/server";

import { API_URL } from "@/lib/api";
import {
  AUTH_COOKIE_NAME,
  authCookieOptions,
} from "@/lib/auth-cookie";
import type { TokenResponse } from "@/lib/types";

type LoginBody = {
  email?: string;
  password?: string;
};

export async function POST(request: Request) {
  let body: LoginBody;
  try {
    body = (await request.json()) as LoginBody;
  } catch {
    return NextResponse.json({ detail: "Invalid JSON body" }, { status: 400 });
  }

  const email = body.email?.trim();
  const password = body.password;

  if (!email || !password) {
    return NextResponse.json(
      { detail: "Email and password are required" },
      { status: 422 },
    );
  }

  const form = new URLSearchParams();
  form.set("username", email);
  form.set("password", password);

  const upstream = await fetch(`${API_URL}/api/v1/auth/token`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: form.toString(),
    cache: "no-store",
  });

  const contentType = upstream.headers.get("content-type") ?? "";
  const parsed = contentType.includes("application/json")
    ? await upstream.json()
    : { detail: await upstream.text() };

  if (!upstream.ok) {
    return NextResponse.json(parsed, { status: upstream.status });
  }

  const { access_token } = parsed as TokenResponse;
  const response = NextResponse.json({ ok: true });
  response.cookies.set(AUTH_COOKIE_NAME, access_token, authCookieOptions());
  return response;
}
