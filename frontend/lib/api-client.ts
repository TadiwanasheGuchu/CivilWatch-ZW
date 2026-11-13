import { API_BASE_URL } from "@/lib/config";

/** Error envelope returned by every CivicWatch API error (see docs/04-api-specification.md). */
export interface ApiErrorBody {
  error: {
    code: string;
    message: string;
    details: unknown;
    request_id: string | null;
  };
}

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
    readonly requestId: string | null,
    readonly details: unknown = null,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

function isApiErrorBody(value: unknown): value is ApiErrorBody {
  if (typeof value !== "object" || value === null || !("error" in value)) return false;
  const error = (value as { error: unknown }).error;
  return typeof error === "object" && error !== null && "code" in error && "message" in error;
}

export async function toApiError(response: Response): Promise<ApiError> {
  const body: unknown = await response.json().catch(() => null);
  if (isApiErrorBody(body)) {
    const { code, message, request_id, details } = body.error;
    return new ApiError(response.status, code, message, request_id, details);
  }
  return new ApiError(
    response.status,
    "unexpected_response",
    `The server responded with status ${response.status}.`,
    response.headers.get("X-Request-ID"),
  );
}

export function apiUrl(path: string): string {
  return `${API_BASE_URL}${path.startsWith("/") ? path : `/${path}`}`;
}

/**
 * Low-level request helper. `credentials: "include"` is set now so the
 * cookie-based session planned for authentication works without changes.
 */
export function apiFetch(path: string, init: RequestInit = {}): Promise<Response> {
  return fetch(apiUrl(path), {
    ...init,
    credentials: "include",
    headers: { Accept: "application/json", ...init.headers },
  });
}

export async function apiGet<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await apiFetch(path, { ...init, method: "GET" });
  if (!response.ok) throw await toApiError(response);
  return (await response.json()) as T;
}
