import { describe, expect, it } from "vitest";

import { safeNextPath } from "./redirect";

describe("safeNextPath", () => {
  it.each([
    ["/account", "/account"],
    ["/council/abc?x=1", "/council/abc?x=1"],
  ])("keeps same-site path %s", (input, expected) => {
    expect(safeNextPath(input)).toBe(expected);
  });

  it.each([null, "", "https://evil.example", "//evil.example", "/\\evil.example", "javascript:alert(1)"])(
    "rejects %s",
    (input) => {
      expect(safeNextPath(input)).toBe("/account");
    },
  );
});
