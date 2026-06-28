import { NextResponse } from "next/server";

import {
  AUTH_COOKIE_NAME,
  clearAuthCookieOptions,
} from "@/lib/auth-cookie";

export async function POST() {
  const response = new NextResponse(null, { status: 204 });
  response.cookies.set(AUTH_COOKIE_NAME, "", clearAuthCookieOptions());
  return response;
}
