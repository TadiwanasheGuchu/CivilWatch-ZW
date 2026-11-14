import { describe, expect, it } from "vitest";

import { changePasswordSchema, registerSchema } from "./schemas";

describe("registerSchema", () => {
  const valid = { full_name: "Tendai Moyo", email: "tendai@example.com", password: "long enough pass" };

  it("accepts valid input and trims", () => {
    const result = registerSchema.parse({ ...valid, full_name: "  Tendai Moyo ", email: " tendai@example.com " });
    expect(result.full_name).toBe("Tendai Moyo");
    expect(result.email).toBe("tendai@example.com");
  });

  it.each([
    [{ password: "short" }, "password"],
    [{ password: " ".repeat(12) }, "password"],
    [{ password: "tendai@example.com" }, "password"],
    [{ email: "not-an-email" }, "email"],
    [{ full_name: "   " }, "full_name"],
  ])("rejects %o", (override, field) => {
    const result = registerSchema.safeParse({ ...valid, ...override });
    expect(result.success).toBe(false);
    expect(result.error?.issues[0]?.path).toEqual([field]);
  });
});

describe("changePasswordSchema", () => {
  it("rejects reusing the current password", () => {
    const result = changePasswordSchema.safeParse({
      current_password: "same password here",
      new_password: "same password here",
    });
    expect(result.success).toBe(false);
  });
});
