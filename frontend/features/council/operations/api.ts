import type { Page } from "@/features/council/types";
import { apiGet, apiSend, apiUrl, ApiError, toApiError } from "@/lib/api-client";

import type { Photo } from "@/features/reporting/types";

import type { Department, QueueFilters, QueueSummary, StaffIssueDetail, StaffIssueSummary } from "./types";

export const QUEUE_PAGE_SIZE = 20;

const base = (councilId: string) => `/councils/${encodeURIComponent(councilId)}`;

export const opsKeys = {
  all: (councilId: string) => ["council", councilId, "ops"] as const,
  summary: (councilId: string) => ["council", councilId, "ops", "summary"] as const,
  queue: (councilId: string, filters: QueueFilters, page: number) =>
    ["council", councilId, "ops", "queue", filters, page] as const,
  issue: (councilId: string, issueId: string) => ["council", councilId, "ops", "issue", issueId] as const,
  departments: (councilId: string) => ["council", councilId, "departments"] as const,
  allMembers: (councilId: string) => ["council", councilId, "members", "all"] as const,
};

export function fetchSummary(councilId: string, signal?: AbortSignal) {
  return apiGet<QueueSummary>(`${base(councilId)}/issues/summary`, { signal });
}

export function queueQuery(filters: QueueFilters, page: number): string {
  const params = new URLSearchParams({ page: String(page), page_size: String(QUEUE_PAGE_SIZE), sort: filters.sort });
  filters.statuses.forEach((status) => params.append("status", status));
  if (filters.category) params.set("category", filters.category);
  if (filters.departmentId) params.set("department_id", filters.departmentId);
  if (filters.assignedToMe) params.set("assigned_to_me", "true");
  if (filters.q) params.set("q", filters.q);
  return params.toString();
}

export function fetchQueue(councilId: string, filters: QueueFilters, page: number, signal?: AbortSignal) {
  return apiGet<Page<StaffIssueSummary>>(`${base(councilId)}/issues?${queueQuery(filters, page)}`, { signal });
}

export function fetchStaffIssue(councilId: string, issueId: string, signal?: AbortSignal) {
  return apiGet<StaffIssueDetail>(`${base(councilId)}/issues/${encodeURIComponent(issueId)}`, {
    signal,
    cache: "no-store",
  });
}

export function transitionIssue(
  councilId: string,
  issueId: string,
  body: { to_status: string; note?: string; duplicate_of_reference?: string },
  csrfToken: string,
) {
  return apiSend<StaffIssueDetail>("POST", `${base(councilId)}/issues/${encodeURIComponent(issueId)}/transitions`, {
    body,
    csrfToken,
  });
}

export function assignIssue(
  councilId: string,
  issueId: string,
  body: { department_id: string; assignee_user_id?: string; note?: string },
  csrfToken: string,
) {
  return apiSend<StaffIssueDetail>("POST", `${base(councilId)}/issues/${encodeURIComponent(issueId)}/assignment`, {
    body,
    csrfToken,
  });
}

export function addInternalUpdate(councilId: string, issueId: string, body: string, csrfToken: string) {
  return apiSend<StaffIssueDetail>("POST", `${base(councilId)}/issues/${encodeURIComponent(issueId)}/updates`, {
    body: { body },
    csrfToken,
  });
}

export function fetchDepartments(councilId: string, signal?: AbortSignal) {
  return apiGet<Department[]>(`${base(councilId)}/departments`, { signal });
}

export function createDepartment(councilId: string, body: { name: string; description?: string }, csrfToken: string) {
  return apiSend<Department>("POST", `${base(councilId)}/departments`, { body, csrfToken });
}

export function updateDepartment(
  councilId: string,
  departmentId: string,
  body: { name?: string; description?: string | null; is_active?: boolean },
  csrfToken: string,
) {
  return apiSend<Department>("PATCH", `${base(councilId)}/departments/${encodeURIComponent(departmentId)}`, {
    body,
    csrfToken,
  });
}

/** Repair evidence upload with progress (see reporting/api.ts for why XHR). */
export function uploadRepairPhoto(
  councilId: string,
  issueId: string,
  file: Blob,
  csrfToken: string,
  onProgress?: (fraction: number) => void,
): Promise<Photo> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", apiUrl(`${base(councilId)}/issues/${encodeURIComponent(issueId)}/photos`));
    xhr.withCredentials = true;
    xhr.setRequestHeader("X-CSRF-Token", csrfToken);
    xhr.setRequestHeader("Accept", "application/json");
    xhr.upload.onprogress = (event) => event.lengthComputable && onProgress?.(event.loaded / event.total);
    xhr.onerror = () => reject(new TypeError("Network request failed"));
    xhr.onload = () => {
      const response = new Response(xhr.responseText, { status: xhr.status });
      if (xhr.status === 201) response.json().then(resolve, reject);
      else
        toApiError(response).then(reject, () =>
          reject(new ApiError(xhr.status, "unexpected_response", "Upload failed.", null)),
        );
    };
    const form = new FormData();
    form.append("file", file, "repair.jpg");
    xhr.send(form);
  });
}

/** Turn-by-turn directions in the phone's maps app (an external link the officer chooses to open). */
export function directionsUrl(latitude: number, longitude: number): string {
  return `https://www.google.com/maps/dir/?api=1&destination=${latitude},${longitude}`;
}
