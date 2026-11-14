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

type MutationMethod = "POST" | "PATCH" | "PUT" | "DELETE";

interface SendOptions {
  body?: unknown;
  /** Required by the API for every state-changing request made with a session. */
  csrfToken?: string;
}

/** JSON mutation helper. Resolves to `undefined` for 204 responses. */
export async function apiSend<T = void>(
  method: MutationMethod,
  path: string,
  { body, csrfToken }: SendOptions = {},
): Promise<T> {
  const headers: Record<string, string> = {};
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (csrfToken) headers["X-CSRF-Token"] = csrfToken;
  const response = await apiFetch(path, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!response.ok) throw await toApiError(response);
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

interface ValidationDetail {
  location?: unknown;
  message?: unknown;
}

/**
 * Map a 422 response's details to `{ fieldName: message }` for request-body
 * fields, so server-side validation appears next to the right input.
 */
export function fieldErrorsFrom(error: unknown): Record<string, string> {
  if (!(error instanceof ApiError) || error.code !== "validation_error") return {};
  if (!Array.isArray(error.details)) return {};
  const result: Record<string, string> = {};
  for (const detail of error.details as ValidationDetail[]) {
    if (!Array.isArray(detail.location) || typeof detail.message !== "string") continue;
    const [source, field] = detail.location;
    if (source !== "body" || typeof field !== "string" || field in result) continue;
    result[field] = detail.message.replace(/^Value error, /, "");
  }
  return result;
}

/** A user-facing message for any error thrown by the API helpers. */
export function errorMessage(error: unknown, fallback = "Something went wrong. Please try again."): string {
  if (error instanceof ApiError) {
    if (error.code === "rate_limited") {
      const seconds = (error.details as { retry_after_seconds?: number } | null)?.retry_after_seconds;
      const minutes = seconds ? Math.max(1, Math.ceil(seconds / 60)) : null;
      return minutes
        ? `Too many attempts. Please wait ${minutes} minute${minutes === 1 ? "" : "s"} and try again.`
        : error.message;
    }
    if (error.code === "unexpected_response" || error.status >= 500) return fallback;
    return error.message;
  }
  if (error instanceof TypeError) {
    return "We could not reach CivicWatch. Check your connection and try again.";
  }
  return fallback;
}
