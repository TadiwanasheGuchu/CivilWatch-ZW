import type { Page } from "@/features/council/types";
import { apiGet, apiSend, apiUrl, ApiError, toApiError } from "@/lib/api-client";

import type { Category, IssueDetail, IssueStatus, NewReport, OwnIssue, Photo, PublicIssue } from "./types";

export const PAGE_SIZE = 20;

export const reportKeys = {
  categories: ["reporting", "categories"] as const,
  councils: ["reporting", "councils"] as const,
  mine: (page: number) => ["reporting", "mine", page] as const,
  mineRoot: ["reporting", "mine"] as const,
  detail: (id: string) => ["reporting", "detail", id] as const,
  explore: (filters: ExploreFilters, page: number) => ["reporting", "explore", filters, page] as const,
};

export interface ExploreFilters {
  councilId?: string;
  category?: string;
  status?: IssueStatus;
}

export function fetchCategories(signal?: AbortSignal) {
  return apiGet<Category[]>("/categories", { signal });
}

export function fetchCouncilDirectory(signal?: AbortSignal) {
  return apiGet<Page<{ id: string; slug: string; name: string }>>("/councils?page_size=100", { signal });
}

export function submitReport(report: NewReport, csrfToken: string) {
  return apiSend<OwnIssue>("POST", "/issues", { body: report, csrfToken });
}

export function fetchMyReports(page: number, signal?: AbortSignal) {
  return apiGet<Page<OwnIssue>>(`/issues/mine?page=${page}&page_size=${PAGE_SIZE}`, { signal });
}

export function fetchReport(id: string, signal?: AbortSignal) {
  return apiGet<IssueDetail>(`/issues/${encodeURIComponent(id)}`, { signal, cache: "no-store" });
}

export function fetchPublishedReports(filters: ExploreFilters, page: number, signal?: AbortSignal) {
  const params = new URLSearchParams({ page: String(page), page_size: String(PAGE_SIZE) });
  if (filters.councilId) params.set("council_id", filters.councilId);
  if (filters.category) params.set("category", filters.category);
  if (filters.status) params.set("status", filters.status);
  return apiGet<Page<PublicIssue>>(`/issues?${params.toString()}`, { signal });
}

export function removePhoto(issueId: string, photoId: string, csrfToken: string) {
  return apiSend(
    "DELETE",
    `/issues/${encodeURIComponent(issueId)}/photos/${encodeURIComponent(photoId)}`,
    { csrfToken },
  );
}

/**
 * Upload one photo with progress events. Uses XMLHttpRequest because fetch
 * cannot report upload progress, which matters on slow mobile connections.
 */
export function uploadPhoto(
  issueId: string,
  file: Blob,
  csrfToken: string,
  onProgress?: (fraction: number) => void,
): Promise<Photo> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", apiUrl(`/issues/${encodeURIComponent(issueId)}/photos`));
    xhr.withCredentials = true;
    xhr.setRequestHeader("X-CSRF-Token", csrfToken);
    xhr.setRequestHeader("Accept", "application/json");
    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) onProgress?.(event.loaded / event.total);
    };
    xhr.onerror = () => reject(new TypeError("Network request failed"));
    xhr.ontimeout = () => reject(new TypeError("Network request timed out"));
    xhr.onload = () => {
      const response = new Response(xhr.responseText, {
        status: xhr.status,
        headers: { "Content-Type": "application/json" },
      });
      if (xhr.status === 201) {
        response.json().then(resolve, reject);
      } else {
        toApiError(response).then(reject, () =>
          reject(new ApiError(xhr.status, "unexpected_response", "Upload failed.", null)),
        );
      }
    };
    const form = new FormData();
    form.append("file", file, "photo.jpg");
    xhr.send(form);
  });
}
