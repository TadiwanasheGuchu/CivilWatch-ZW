import { expect, test } from "@playwright/test";

test.describe("home page", () => {
  test("renders without horizontal scrolling", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
    );
    expect(overflow).toBeLessThanOrEqual(0);
  });

  test("reports live platform status from the API", async ({ page }) => {
    await page.goto("/");
    const panel = page.getByRole("region", { name: "Platform status" });
    await expect(panel.getByText("All services are operational.")).toBeVisible();
  });

  test("status refresh control meets the 44px touch target", async ({ page }) => {
    await page.goto("/");
    const button = page.getByRole("button", { name: "Check platform status again" });
    const box = await button.boundingBox();
    expect(box?.height ?? 0).toBeGreaterThanOrEqual(44);
    expect(box?.width ?? 0).toBeGreaterThanOrEqual(44);
  });
});
