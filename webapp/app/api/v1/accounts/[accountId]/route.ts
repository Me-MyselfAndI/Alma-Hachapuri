import { NextRequest, NextResponse } from "next/server";

import { serverFetch } from "@/lib/api";

type RouteContext = {
  params: Promise<{ accountId: string }>;
};

export async function GET(_request: NextRequest, context: RouteContext) {
  const { accountId } = await context.params;
  const upstream = await serverFetch(`/api/v1/accounts/${accountId}`);

  const contentType = upstream.headers.get("content-type") ?? "";
  const body = contentType.includes("application/json")
    ? await upstream.json()
    : await upstream.text();

  if (contentType.includes("application/json")) {
    return NextResponse.json(body, { status: upstream.status });
  }

  return new NextResponse(body as BodyInit, { status: upstream.status });
}

export async function PATCH(request: NextRequest, context: RouteContext) {
  const { accountId } = await context.params;
  const body = await request.text();
  const upstream = await serverFetch(`/api/v1/accounts/${accountId}`, {
    method: "PATCH",
    body,
  });

  const contentType = upstream.headers.get("content-type") ?? "";
  const responseBody = contentType.includes("application/json")
    ? await upstream.json()
    : await upstream.text();

  if (contentType.includes("application/json")) {
    return NextResponse.json(responseBody, { status: upstream.status });
  }

  return new NextResponse(responseBody as BodyInit, { status: upstream.status });
}
