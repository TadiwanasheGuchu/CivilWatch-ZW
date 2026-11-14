import type { IssueStatus } from "./types";

export const STATUS_LABELS: Record<IssueStatus, string> = {
  SUBMITTED: "Submitted",
  UNDER_REVIEW: "Under review",
  NEEDS_INFORMATION: "More information needed",
  VERIFIED: "Verified",
  ASSIGNED: "Assigned",
  IN_PROGRESS: "In progress",
  RESOLVED: "Resolved",
  REJECTED: "Rejected",
  DUPLICATE: "Duplicate",
  CLOSED: "Closed",
};

/** What each status means for the person who reported it. */
export const STATUS_EXPLANATIONS: Record<IssueStatus, string> = {
  SUBMITTED: "Your council has received the report and will review it.",
  UNDER_REVIEW: "A council officer is checking the report.",
  NEEDS_INFORMATION: "The council needs more details before it can continue.",
  VERIFIED: "The council has confirmed the problem.",
  ASSIGNED: "A team has been given the work.",
  IN_PROGRESS: "Work is under way.",
  RESOLVED: "The council says the problem is fixed.",
  REJECTED: "The council will not act on this report.",
  DUPLICATE: "This problem was already reported.",
  CLOSED: "This report is closed.",
};

export type StatusTone = "neutral" | "progress" | "done" | "stopped" | "attention";

export const STATUS_TONES: Record<IssueStatus, StatusTone> = {
  SUBMITTED: "neutral",
  UNDER_REVIEW: "neutral",
  NEEDS_INFORMATION: "attention",
  VERIFIED: "progress",
  ASSIGNED: "progress",
  IN_PROGRESS: "progress",
  RESOLVED: "done",
  REJECTED: "stopped",
  DUPLICATE: "stopped",
  CLOSED: "done",
};

export const PUBLISHED_STATUSES: IssueStatus[] = ["VERIFIED", "ASSIGNED", "IN_PROGRESS", "RESOLVED", "CLOSED"];

const dateFormat = new Intl.DateTimeFormat("en-GB", { dateStyle: "medium" });
const dateTimeFormat = new Intl.DateTimeFormat("en-GB", { dateStyle: "medium", timeStyle: "short" });

export const formatDate = (iso: string) => dateFormat.format(new Date(iso));
export const formatDateTime = (iso: string) => dateTimeFormat.format(new Date(iso));
