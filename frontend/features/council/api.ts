import { apiGet, apiSend } from "@/lib/api-client";

import type { AuditEntry, CouncilRole, Member, Membership, Page, Workspace } from "./types";

export const PAGE_SIZE = 20;

export const councilKeys = {
  memberships: ["council", "memberships"] as const,
  workspace: (councilId: string) => ["council", councilId, "workspace"] as const,
  members: (councilId: string, page: number) => ["council", councilId, "members", page] as const,
  membersRoot: (councilId: string) => ["council", councilId, "members"] as const,
  audit: (councilId: string, page: number) => ["council", councilId, "audit", page] as const,
};

const base = (councilId: string) => `/councils/${encodeURIComponent(councilId)}`;

export function fetchMyMemberships(signal?: AbortSignal) {
  return apiGet<Membership[]>("/users/me/memberships", { signal });
}

export function fetchWorkspace(councilId: string, signal?: AbortSignal) {
  return apiGet<Workspace>(`${base(councilId)}/workspace`, { signal });
}

export function fetchMembers(councilId: string, page: number, signal?: AbortSignal) {
  return apiGet<Page<Member>>(`${base(councilId)}/members?page=${page}&page_size=${PAGE_SIZE}`, {
    signal,
  });
}

export function addMember(
  councilId: string,
  input: { email: string; role: CouncilRole },
  csrfToken: string,
) {
  return apiSend<Member>("POST", `${base(councilId)}/members`, { body: input, csrfToken });
}

/** Change a staff member's role and/or department (`null` removes the department). */
export function updateMember(
  councilId: string,
  membershipId: string,
  body: { role?: CouncilRole; department_id?: string | null },
  csrfToken: string,
) {
  return apiSend<Member>("PATCH", `${base(councilId)}/members/${encodeURIComponent(membershipId)}`, {
    body,
    csrfToken,
  });
}

export function removeMember(councilId: string, membershipId: string, csrfToken: string) {
  return apiSend("DELETE", `${base(councilId)}/members/${encodeURIComponent(membershipId)}`, {
    csrfToken,
  });
}

export function fetchAuditLog(councilId: string, page: number, signal?: AbortSignal) {
  return apiGet<Page<AuditEntry>>(
    `${base(councilId)}/audit-logs?page=${page}&page_size=${PAGE_SIZE}`,
    { signal },
  );
}
