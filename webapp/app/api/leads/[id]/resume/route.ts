import { NextRequest, NextResponse } from "next/server";

import { serverFetch } from "@/lib/api";

type RouteParams = {
  params: Promise<{ id: string }>;
};

export async function GET(request: NextRequest, { params }: RouteParams) {
  const { id } = await params;
  const upstream = await serverFetch(`/api/v1/leads/${id}/resume`);

  if (upstream.status === 401) {
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("next", `/leads/${id}`);
    return NextResponse.redirect(loginUrl);
  }

  if (!upstream.ok) {
    const contentType = upstream.headers.get("content-type") ?? "";
    if (contentType.includes("application/json")) {
      const body = await upstream.json();
      return NextResponse.json(body, { status: upstream.status });
    }
    return new NextResponse(await upstream.text(), { status: upstream.status });
  }

  const headers = new Headers();
  const contentDisposition = upstream.headers.get("Content-Disposition");
  const contentType = upstream.headers.get("Content-Type");
  if (contentDisposition) {
    headers.set("Content-Disposition", contentDisposition);
  }
  if (contentType) {
    headers.set("Content-Type", contentType);
  }

  return new NextResponse(upstream.body, { status: 200, headers });
}
