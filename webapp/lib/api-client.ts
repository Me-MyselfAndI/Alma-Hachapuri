type FastApiValidationError = {
  msg: string;
  loc?: (string | number)[];
};

type FastApiErrorBody = {
  detail?: string | FastApiValidationError[];
};

export type PublicFetchResult<T> =
  | { ok: true; data: T; status: number }
  | { ok: false; status: number; body: unknown };

export async function publicFetch<T>(
  path: string,
  options: {
    method?: string;
    formData?: FormData;
    json?: unknown;
  } = {},
): Promise<PublicFetchResult<T>> {
  const { method = "GET", formData, json } = options;

  const headers: HeadersInit = {};
  let body: BodyInit | undefined;

  if (json !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(json);
  } else if (formData) {
    body = formData;
  }

  const res = await fetch(path, { method, headers, body });
  const contentType = res.headers.get("content-type") ?? "";
  const parsed = contentType.includes("application/json")
    ? await res.json()
    : await res.text();

  if (res.ok) {
    return { ok: true, data: parsed as T, status: res.status };
  }

  return { ok: false, status: res.status, body: parsed };
}

export function formatApiError(status: number, body: unknown): string {
  if (status === 502 || status === 503) {
    return "We couldn't send the verification email. Please try again later.";
  }

  if (typeof body === "object" && body !== null && "detail" in body) {
    const detail = (body as FastApiErrorBody).detail;
    if (typeof detail === "string") {
      return detail;
    }
    if (Array.isArray(detail)) {
      return detail.map((item) => item.msg).join("; ");
    }
  }

  if (status === 400) {
    return "Please check your input and try again.";
  }

  if (status === 422) {
    return "Some fields are invalid. Please review the form.";
  }

  return "Something went wrong. Please try again.";
}

/** Friendly verify-page copy when API detail is absent. */
export function formatVerifyError(status: number, body: unknown): string {
  if (typeof body === "object" && body !== null && "detail" in body) {
    const detail = (body as FastApiErrorBody).detail;
    if (typeof detail === "string" && detail.trim()) {
      return detail;
    }
  }

  switch (status) {
    case 400:
      return "Verification link is missing or invalid.";
    case 404:
      return "This verification link is not valid.";
    case 409:
      return "This link has already been used.";
    case 410:
      return "This verification link has expired. Please submit the form again.";
    default:
      return formatApiError(status, body);
  }
}
