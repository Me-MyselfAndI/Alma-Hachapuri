type StaffFetchOptions = {
  method?: string;
  json?: unknown;
};

export type StaffFetchResult<T> =
  | { ok: true; data: T; status: number }
  | { ok: false; status: number; body: unknown };

export async function staffFetch<T>(
  path: string,
  options: StaffFetchOptions = {},
): Promise<StaffFetchResult<T>> {
  const { method = "GET", json } = options;

  const headers: HeadersInit = {};
  if (json !== undefined) {
    headers["Content-Type"] = "application/json";
  }

  const res = await fetch(path, {
    method,
    headers,
    body: json !== undefined ? JSON.stringify(json) : undefined,
    credentials: "include",
  });

  const contentType = res.headers.get("content-type") ?? "";
  const parsed = contentType.includes("application/json")
    ? await res.json()
    : await res.text();

  if (res.ok) {
    return { ok: true, data: parsed as T, status: res.status };
  }

  return { ok: false, status: res.status, body: parsed };
}

type FastApiValidationError = {
  msg: string;
  loc?: (string | number)[];
};

type FastApiErrorBody = {
  detail?: string | FastApiValidationError[];
};

export function formatStaffApiError(status: number, body: unknown): string {
  if (typeof body === "object" && body !== null && "detail" in body) {
    const detail = (body as FastApiErrorBody).detail;
    if (typeof detail === "string" && detail.trim()) {
      return detail;
    }
    if (Array.isArray(detail)) {
      return detail.map((item) => item.msg).join("; ");
    }
  }

  if (status === 502 || status === 503) {
    return "The server is temporarily unavailable. Please try again later.";
  }

  if (status === 400) {
    return "Please check your input and try again.";
  }

  if (status === 422) {
    return "Some fields are invalid. Please review the form.";
  }

  return "Something went wrong. Please try again.";
}
