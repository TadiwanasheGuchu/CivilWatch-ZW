import type { IssueStatus } from "@/features/reporting/types";

/** How staff think about the queue. Used by the overview tiles and the queue filter. */
export interface StatusGroup {
  id: string;
  label: string;
  hint: string;
  statuses: IssueStatus[];
}

export const STATUS_GROUPS: StatusGroup[] = [
  { id: "new", label: "New reports", hint: "Waiting for review to start", statuses: ["SUBMITTED"] },
  { id: "review", label: "Under review", hint: "Being checked", statuses: ["UNDER_REVIEW"] },
  { id: "waiting", label: "Waiting for reporter", hint: "More information requested", statuses: ["NEEDS_INFORMATION"] },
  { id: "verified", label: "Ready to assign", hint: "Verified, not yet assigned", statuses: ["VERIFIED"] },
  { id: "assigned", label: "Assigned", hint: "Work not started", statuses: ["ASSIGNED"] },
  { id: "progress", label: "In progress", hint: "Work under way", statuses: ["IN_PROGRESS"] },
  { id: "resolved", label: "Resolved", hint: "Awaiting closure", statuses: ["RESOLVED"] },
  { id: "closed", label: "Closed", hint: "Finished", statuses: ["CLOSED"] },
  { id: "declined", label: "Rejected or duplicate", hint: "No action taken", statuses: ["REJECTED", "DUPLICATE"] },
];

export const OPEN_STATUSES: IssueStatus[] = [
  "SUBMITTED",
  "UNDER_REVIEW",
  "NEEDS_INFORMATION",
  "VERIFIED",
  "ASSIGNED",
  "IN_PROGRESS",
  "RESOLVED",
];

export function groupForStatuses(statuses: IssueStatus[]): StatusGroup | undefined {
  const key = [...statuses].sort().join(",");
  return STATUS_GROUPS.find((group) => [...group.statuses].sort().join(",") === key);
}
