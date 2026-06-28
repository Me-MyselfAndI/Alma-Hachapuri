import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

import { tokenHasPermission } from "@/lib/access";
import { AUTH_COOKIE_NAME } from "@/lib/auth-cookie";
import { isPublicApiRoute } from "@/lib/public-api-routes";

export function middleware(request: NextRequest) {
  const { pathname, search } = request.nextUrl;
  const token = request.cookies.get(AUTH_COOKIE_NAME)?.value;

  if ((pathname.startsWith("/leads") || pathname.startsWith("/admin")) && !token) {
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("next", pathname + search);
    return NextResponse.redirect(loginUrl);
  }

  if (
    pathname.startsWith("/admin") &&
    token &&
    !tokenHasPermission(token, "manage_users")
  ) {
    return NextResponse.redirect(new URL("/leads", request.url));
  }

  if (pathname.startsWith("/api/v1/")) {
    if (!token && isPublicApiRoute(pathname, request.method)) {
      return NextResponse.next();
    }
    if (!token) {
      return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
    }
    const requestHeaders = new Headers(request.headers);
    requestHeaders.set("Authorization", `Bearer ${token}`);
    return NextResponse.next({ request: { headers: requestHeaders } });
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/leads/:path*", "/admin/:path*", "/login", "/api/v1/:path*"],
};
