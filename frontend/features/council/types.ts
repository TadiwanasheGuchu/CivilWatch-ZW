/** Mirrors backend schemas in app/schemas/councils.py. */
export type CouncilRole =
  | "council_admin"
  | "department_manager"
  | "verification_officer"
  | "maintenance_officer";

export type Permission =
  | "workspace.view"
  | "members.view"
  | "members.manage"
  | "audit.view"
  | "departments.manage"
  | "issues.view"
  | "issues.review"
  | "issues.assign"
  | "issues.work"
  | "issues.close"
  | "analytics.view"
  | "reports.export";

export interface CouncilSummary {
  id: string;
  slug: string;
  name: string;
}

export interface Page<T> {
  items: T[];
  page: number;
  page_size: number;
  total: number;
}

export interface Membership {
  id: string;
  council: CouncilSummary;
  role: CouncilRole;
  created_at: string;
}

export interface Workspace {
  council: CouncilSummary;
  role: CouncilRole | null;
  via_platform_admin: boolean;
  permissions: Permission[];
}

export interface Member {
  membership_id: string;
  user_id: string;
  full_name: string;
  email: string;
  role: CouncilRole;
  department: { id: string; name: string } | null;
  granted_at: string;
}

export interface AuditEntry {
  id: string;
  occurred_at: string;
  actor_user_id: string | null;
  actor_name: string | null;
  action: string;
  target_type: string | null;
  target_id: string | null;
  details: Record<string, unknown>;
  request_id: string | null;
}
