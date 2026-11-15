import { describe, expect, it } from "vitest";

import { safeAppLink } from "./api";

describe("safeAppLink", () => {
  it("keeps in-app links", () => {
    expect(safeAppLink("/reports/abc")).toBe("/reports/abc");
  });

  it.each(["https://evil.example", "//evil.example", "/\\evil.example", "javascript:alert(1)"])("refuses %s", (link) => {
    expect(safeAppLink(link)).toBe("/");
  });
});
