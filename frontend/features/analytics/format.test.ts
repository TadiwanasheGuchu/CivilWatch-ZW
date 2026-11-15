import { describe, expect, it } from "vitest";

import { formatDays, formatHours, percent } from "./format";

describe("formatHours", () => {
  it("handles missing and small values", () => {
    expect(formatHours(null)).toBe("No data yet");
    expect(formatHours(0.4)).toBe("Under an hour");
    expect(formatHours(1)).toBe("1 hour");
    expect(formatHours(30.4)).toBe("30 hours");
  });
  it("switches to days after two days", () => {
    expect(formatHours(72)).toBe("3 days");
    expect(formatHours(24 * 12.6)).toBe("13 days");
  });
});

describe("formatDays", () => {
  it("keeps one decimal below ten days", () => {
    expect(formatDays(0.5)).toBe("Under a day");
    expect(formatDays(1)).toBe("1 day");
    expect(formatDays(4.04)).toBe("4 days");
    expect(formatDays(4.36)).toBe("4.4 days");
  });
});

describe("percent", () => {
  it("never divides by zero", () => {
    expect(percent(0, 0)).toBeNull();
    expect(percent(2, 3)).toBe(67);
  });
});
