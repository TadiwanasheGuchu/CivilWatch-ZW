import { apiFetch, toApiError } from "@/lib/api-client";

import type { Readiness } from "./types";

/**
 * The readiness probe answers 503 with a normal readiness body when a
 * dependency is down, so both 200 and 503 are treated as data.
 */
export async function fetchReadiness(signal?: AbortSignal): Promise<Readiness> {
  const response = await apiFetch("/health/ready", { signal, cache: "no-store" });
  if (response.status === 200 || response.status === 503) {
    return (await response.json()) as Readiness;
  }
  throw await toApiError(response);
}
