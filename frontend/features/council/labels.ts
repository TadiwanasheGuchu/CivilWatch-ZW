import type { CouncilRole } from "./types";

export const ROLE_LABELS: Record<CouncilRole, string> = {
  council_admin: "Council administrator",
  department_manager: "Department manager",
  verification_officer: "Verification officer",
  maintenance_officer: "Maintenance officer",
};

export const ROLE_DESCRIPTIONS: Record<CouncilRole, string> = {
  council_admin: "Manages staff and council settings, and can see the audit log.",
  department_manager: "Oversees a department's work and assigns reports.",
  verification_officer: "Reviews incoming reports and verifies them.",
  maintenance_officer: "Works on assigned reports in the field.",
};

export const COUNCIL_ROLES = [
  "council_admin",
  "department_manager",
  "verification_officer",
  "maintenance_officer",
] as const satisfies readonly CouncilRole[];

export function roleLabel(role: unknown): string {
  return typeof role === "string" && role in ROLE_LABELS
    ? ROLE_LABELS[role as CouncilRole]
    : "Unknown role";
}

/** Plain-language description of an audit entry. Unknown actions fall back to their code. */
export function describeAuditAction(action: string, details: Record<string, unknown>): string {
  switch (action) {
    case "council.created":
      return "Created the council";
    case "membership.granted":
      return `Added a staff member as ${roleLabel(details.role)}`;
    case "membership.role_changed":
      return `Changed a staff member's role from ${roleLabel(details.from)} to ${roleLabel(details.to)}`;
    case "membership.revoked":
      return `Removed a staff member (${roleLabel(details.role)})`;
    default:
      return action;
  }
}
