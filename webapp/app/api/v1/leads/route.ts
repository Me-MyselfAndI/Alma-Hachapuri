import { NextRequest, NextResponse } from "next/server";

import { serverFetch } from "@/lib/api";

export async function GET(request: NextRequest) {
  const search = request.nextUrl.search;
  const upstream = await serverFetch(`/api/v1/leads${search}`);

  const contentType = upstream.headers.get("content-type") ?? "";
  const body = contentType.includes("application/json")
    ? await upstream.json()
    : await upstream.text();

  if (contentType.includes("application/json")) {
    return NextResponse.json(body, { status: upstream.status });
  }

  return new NextResponse(body as BodyInit, { status: upstream.status });
}
