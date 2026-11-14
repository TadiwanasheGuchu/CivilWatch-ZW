import { describe, expect, it } from "vitest";

import { describeAuditAction } from "./labels";

describe("describeAuditAction", () => {
  it("describes known actions in plain language", () => {
    expect(describeAuditAction("membership.role_changed", { from: "council_admin", to: "maintenance_officer" })).toBe(
      "Changed a staff member's role from Council administrator to Maintenance officer",
    );
  });

  it("does not trust unexpected detail values", () => {
    expect(describeAuditAction("membership.granted", { role: "<script>" })).toBe(
      "Added a staff member as Unknown role",
    );
  });

  it("falls back to the action code", () => {
    expect(describeAuditAction("something.new", {})).toBe("something.new");
  });
});
