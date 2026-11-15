import { expect, test } from "@playwright/test";

test("pages send a content security policy and other hardening headers", async ({ page }) => {
  const violations: string[] = [];
  page.on("console", (message) => {
    if (/Content Security Policy/i.test(message.text())) violations.push(message.text());
  });
  const response = await page.goto("/explore");
  const headers = response!.headers();
  const csp = headers["content-security-policy"];
  expect(csp).toContain("frame-ancestors 'none'");
  expect(csp).toContain("object-src 'none'");
  expect(headers["strict-transport-security"]).toContain("max-age=");
  expect(headers["x-content-type-options"]).toBe("nosniff");
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  // The page (including the map library and its worker) runs within the policy.
  await page.waitForLoadState("networkidle");
  expect(violations).toEqual([]);
});
