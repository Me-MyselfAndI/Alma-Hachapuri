import { NextResponse } from "next/server";

import { hasPermission } from "@/lib/access";
import { serverFetch } from "@/lib/api";
import type { AccountMe } from "@/lib/types";

export async function getSessionUser(): Promise<AccountMe | null> {
  const upstream = await serverFetch("/api/v1/auth/me");
  if (!upstream.ok) {
    return null;
  }
  return (await upstream.json()) as AccountMe;
}

export async function requirePermissionSession(
  permission: string,
): Promise<AccountMe | NextResponse> {
  const user = await getSessionUser();
  if (!user) {
    return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
  }
  if (!hasPermission(user, permission)) {
    return NextResponse.json(
      { detail: "Insufficient permissions" },
      { status: 403 },
    );
  }
  return user;
}

export async function requireManageUsersSession(): Promise<
  AccountMe | NextResponse
> {
  return requirePermissionSession("manage_users");
}

export function isNextResponse(
  value: AccountMe | NextResponse,
): value is NextResponse {
  return value instanceof NextResponse;
}
