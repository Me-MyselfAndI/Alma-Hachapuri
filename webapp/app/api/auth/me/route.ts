import { NextResponse } from "next/server";

import { serverFetch } from "@/lib/api";
import type { AccountMe } from "@/lib/types";

export async function GET() {
  const upstream = await serverFetch("/api/v1/auth/me");

  if (!upstream.ok) {
    const contentType = upstream.headers.get("content-type") ?? "";
    const body = contentType.includes("application/json")
      ? await upstream.json()
      : { detail: await upstream.text() };
    return NextResponse.json(body, { status: upstream.status });
  }

  const user = (await upstream.json()) as AccountMe;
  return NextResponse.json(user);
}
