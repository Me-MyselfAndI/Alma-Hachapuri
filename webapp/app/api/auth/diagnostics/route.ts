import { NextResponse } from "next/server";

import { serverFetch } from "@/lib/api";

export async function GET() {
  const upstream = await serverFetch("/api/v1/auth/diagnostics");

  const contentType = upstream.headers.get("content-type") ?? "";
  const body = contentType.includes("application/json")
    ? await upstream.json()
    : { detail: await upstream.text() };

  return NextResponse.json(body, {
    status: upstream.status,
    headers: { "Cache-Control": "no-store" },
  });
}
