import { apiFetch, apiGet, toApiError } from "@/lib/api-client";

import type { PeriodDays, Performance, PublicStats } from "./types";

export const analyticsKeys = {
  performance: (councilId: string, days: PeriodDays) => ["council", councilId, "performance", days] as const,
  public: (councilId: string | null) => ["analytics", "public", councilId ?? "all"] as const,
};

export function fetchPerformance(councilId: string, days: PeriodDays, signal?: AbortSignal) {
  return apiGet<Performance>(`/councils/${councilId}/analytics/performance?days=${days}`, { signal });
}

export function fetchPublicStats(councilId: string | null, signal?: AbortSignal) {
  const query = councilId ? `?council_id=${encodeURIComponent(councilId)}` : "";
  return apiGet<PublicStats>(`/analytics/public${query}`, { signal });
}

/** Downloads the CSV export and returns it with the server's file name. */
export async function downloadExport(councilId: string, from: string, to: string) {
  const params = new URLSearchParams({ from, to });
  const response = await apiFetch(`/councils/${councilId}/reports/export?${params}`, {
    headers: { Accept: "text/csv" },
  });
  if (!response.ok) throw await toApiError(response);
  const disposition = response.headers.get("Content-Disposition") ?? "";
  const filename = /filename="([^"]+)"/.exec(disposition)?.[1] ?? "civicwatch-reports.csv";
  return { blob: await response.blob(), filename };
}
