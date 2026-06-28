/** Cross-tab signal when login/logout replaces the session cookie. */

export const AUTH_SESSION_CHANGED_KEY = "alma_auth_session_changed";

export function notifyAuthSessionChanged(): void {
  if (typeof window === "undefined") {
    return;
  }
  localStorage.setItem(AUTH_SESSION_CHANGED_KEY, String(Date.now()));
}

/** Full navigation so no in-memory React state survives an account switch. */
export function redirectAfterAuthChange(path: string): void {
  notifyAuthSessionChanged();
  window.location.assign(path);
}
