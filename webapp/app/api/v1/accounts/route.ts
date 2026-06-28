import { NextRequest, NextResponse } from "next/server";

import { isNextResponse, requireManageUsersSession } from "@/lib/api-session";
import { serverFetch } from "@/lib/api";

export async function GET(request: NextRequest) {
  const session = await requireManageUsersSession();
  if (isNextResponse(session)) {
    return session;
  }

  const search = request.nextUrl.search;
  const upstream = await serverFetch(`/api/v1/accounts${search}`);

  const contentType = upstream.headers.get("content-type") ?? "";
  const body = contentType.includes("application/json")
    ? await upstream.json()
    : await upstream.text();

  if (contentType.includes("application/json")) {
    return NextResponse.json(body, { status: upstream.status });
  }

  return new NextResponse(body as BodyInit, { status: upstream.status });
}

export async function PATCH(request: NextRequest) {
  const session = await requireManageUsersSession();
  if (isNextResponse(session)) {
    return session;
  }

  const search = request.nextUrl.search;
  const body = await request.text();
  const upstream = await serverFetch(`/api/v1/accounts${search}`, {
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

export async function POST(request: NextRequest) {
  const session = await requireManageUsersSession();
  if (isNextResponse(session)) {
    return session;
  }

  const search = request.nextUrl.search;
  const body = await request.text();
  const upstream = await serverFetch(`/api/v1/accounts${search}`, {
    method: "POST",
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
