/** API paths that must work without staff login (L1a/L1b intake + A1 token). */

export type PublicApiRoute = {
  /** Omit to allow any HTTP method on `path`. */
  method?: string;
  path: string;
};

export const PUBLIC_API_ROUTES: readonly PublicApiRoute[] = [
  { method: "POST", path: "/api/v1/leads/verification-requests" },
  { path: "/api/v1/leads/verify" },
  { method: "POST", path: "/api/v1/auth/token" },
] as const;

export function isPublicApiRoute(pathname: string, method: string): boolean {
  return PUBLIC_API_ROUTES.some((route) => {
    if (route.method && route.method !== method) {
      return false;
    }
    return pathname === route.path;
  });
}
