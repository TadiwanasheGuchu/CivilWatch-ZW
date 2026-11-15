import { ApiError, apiGet, apiSend } from "@/lib/api-client";

import type { CurrentUser, SessionData } from "./types";

/** The current session, or `null` when signed out. */
export async function fetchSession(signal?: AbortSignal): Promise<SessionData | null> {
  try {
    return await apiGet<SessionData>("/auth/session", { signal, cache: "no-store" });
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) return null;
    throw error;
  }
}

export function signIn(input: { email: string; password: string }) {
  return apiSend<SessionData>("POST", "/auth/login", { body: input });
}

export function register(input: { email: string; password: string; full_name: string }) {
  return apiSend<SessionData>("POST", "/auth/register", { body: input });
}

export function signOut(csrfToken: string) {
  return apiSend("POST", "/auth/logout", { csrfToken });
}

export function updateProfile(
  input: { full_name?: string; email_notifications?: boolean },
  csrfToken: string,
) {
  return apiSend<CurrentUser>("PATCH", "/users/me", { body: input, csrfToken });
}

export function changePassword(
  input: { current_password: string; new_password: string },
  csrfToken: string,
) {
  return apiSend("POST", "/users/me/password", { body: input, csrfToken });
}
