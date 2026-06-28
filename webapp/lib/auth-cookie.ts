/** HttpOnly staff session cookie (Q-W1 B). */

export const AUTH_COOKIE_NAME = "alma_access_token";

/** Matches API default `jwt_expire_minutes` (24h). */
export const AUTH_COOKIE_MAX_AGE = 60 * 60 * 24;

export function authCookieOptions(maxAge = AUTH_COOKIE_MAX_AGE) {
  return {
    httpOnly: true,
    sameSite: "lax" as const,
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge,
  };
}

export function clearAuthCookieOptions() {
  return {
    httpOnly: true,
    sameSite: "lax" as const,
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: 0,
  };
}
