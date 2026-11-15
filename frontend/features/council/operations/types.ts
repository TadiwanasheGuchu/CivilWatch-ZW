/** Mirrors backend app/schemas/operations.py. Staff-only data. */
import type { IssueStatus, Photo, Visibility } from "@/features/reporting/types";

export interface Department {
  id: string;
  name: string;
  description: string | null;
  is_active: boolean;
}

export interface Assignment {
  department: { id: string; name: string };
  assignee: { id: string; full_name: string } | null;
  assigned_at: string;
}

export interface StaffIssueSummary {
  id: string;
  reference: string;
  title: string;
  category: { code: string; name: string };
  status: IssueStatus;
  visibility: Visibility;
  location_description: string | null;
  latitude: number;
  longitude: number;
  created_at: string;
  updated_at: string;
  photo_count: number;
  cover_thumbnail_url: string | null;
  assignment: Assignment | null;
}

export interface StaffStatusChange {
  from_status: IssueStatus | null;
  to_status: IssueStatus;
  note: string | null;
  changed_by: string | null;
  created_at: string;
}

export interface InternalUpdate {
  id: string;
  body: string;
  author: string | null;
  created_at: string;
}

export interface AvailableTransition {
  to_status: IssueStatus;
  label: string;
  note_required: boolean;
  needs_duplicate_of: boolean;
}

export interface StaffIssueDetail extends StaffIssueSummary {
  description: string;
  reporter_name: string;
  duplicate_of: { id: string; reference: string } | null;
  photos: Photo[];
  repair_photos: Photo[];
  history: StaffStatusChange[];
  updates: InternalUpdate[];
  available_transitions: AvailableTransition[];
  can_assign: boolean;
  can_add_repair_photos: boolean;
  feedback: { fixed: boolean; comment: string | null; created_at: string } | null;
}

export interface QueueSummary {
  counts: Array<{ status: IssueStatus; count: number }>;
  assigned_to_me: number;
}

export interface QueueFilters {
  statuses: IssueStatus[];
  category?: string;
  departmentId?: string;
  assignedToMe?: boolean;
  q?: string;
  sort: "newest" | "oldest";
}
