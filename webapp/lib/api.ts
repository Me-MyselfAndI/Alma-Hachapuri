import { cookies } from "next/headers";

import { AUTH_COOKIE_NAME } from "@/lib/auth-cookie";

const API_URL = process.env.API_URL ?? "http://localhost:8000";

export { API_URL };

type ServerFetchOptions = {
  method?: string;
  json?: unknown;
  body?: BodyInit;
  /** Override cookie token (e.g. immediately after login). */
  token?: string;
};

export async function serverFetch(
  path: string,
  options: ServerFetchOptions = {},
): Promise<Response> {
  const { method = "GET", json, body, token: tokenOverride } = options;

  const cookieStore = await cookies();
  const token = tokenOverride ?? cookieStore.get(AUTH_COOKIE_NAME)?.value;

  const headers: HeadersInit = {};
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  if (json !== undefined) {
    headers["Content-Type"] = "application/json";
  } else if (body !== undefined && typeof body === "string") {
    headers["Content-Type"] = "application/json";
  }

  const url = path.startsWith("http") ? path : `${API_URL}${path}`;

  return fetch(url, {
    method,
    headers,
    body: json !== undefined ? JSON.stringify(json) : body,
    cache: "no-store",
  });
}

export async function fetchHealth(): Promise<{ status: string }> {
  const res = await fetch(`${API_URL}/health`, { cache: "no-store" });
  if (!res.ok) throw new Error(`API health check failed: ${res.status}`);
  return res.json();
}
