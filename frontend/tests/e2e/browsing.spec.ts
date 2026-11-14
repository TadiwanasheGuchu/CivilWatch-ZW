import { expect, test } from "@playwright/test";

import {
  createCouncil,
  createPlatformAdmin,
  expectNoHorizontalScroll,
  registerViaApi,
  setReportStatus,
  signInViaUi,
  submitReportViaApi,
} from "./support";

test.describe("browsing reports", () => {
  test("explore shows verified public reports only, without naming reporters", async ({ page }) => {
    const platform = await createPlatformAdmin();
    const council = await createCouncil(platform, `E2E Browse Council ${Date.now()}`);
    const reporter = await registerViaApi("Hidden Reporter Name");
    const tag = Date.now().toString(36);
    const verified = await submitReportViaApi(reporter, council.id, { title: `Verified leak ${tag}` });
    await submitReportViaApi(reporter, council.id, { title: `Unverified leak ${tag}` });
    const privateReport = await submitReportViaApi(reporter, council.id, {
      title: `Private leak ${tag}`,
      visibility: "PRIVATE",
    });
    setReportStatus(verified.id, "VERIFIED");
    setReportStatus(privateReport.id, "VERIFIED");

    await page.goto("/explore");
    await page.getByLabel("Council").selectOption(council.id);
    await expect(page.getByRole("link", { name: new RegExp(`Verified leak ${tag}`) })).toBeVisible();
    await expect(page.getByText(`Unverified leak ${tag}`)).toHaveCount(0);
    await expect(page.getByText(`Private leak ${tag}`)).toHaveCount(0);
    await expectNoHorizontalScroll(page);

    await page.getByRole("link", { name: new RegExp(`Verified leak ${tag}`) }).click();
    await expect(page.getByRole("heading", { name: `Verified leak ${tag}` })).toBeVisible();
    await expect(page.getByText("Hidden Reporter Name")).toHaveCount(0);
    await expectNoHorizontalScroll(page);
  });

  test("another resident's private report is not found", async ({ page }) => {
    const platform = await createPlatformAdmin();
    const council = await createCouncil(platform, `E2E Private Council ${Date.now()}`);
    const owner = await registerViaApi("Private Owner");
    const report = await submitReportViaApi(owner, council.id, { visibility: "PRIVATE" });
    const other = await registerViaApi("Curious Neighbour");
    await signInViaUi(page, other.email);
    await page.goto(`/reports/${report.id}`);
    await expect(page.getByText("Report not found")).toBeVisible();
    await expect(page.getByText("Pothole near the clinic")).toHaveCount(0);
  });

  test("navigation reaches every resident page", async ({ page, viewport }) => {
    await page.goto("/");
    const phone = (viewport?.width ?? 1024) < 768;
    const nav = page.getByRole("navigation", { name: "Main" });
    if (phone) {
      for (const label of ["Explore", "Report", "My reports", "Profile", "Home"]) {
        await expect(nav.getByRole("link", { name: label, exact: true })).toBeVisible();
      }
      await nav.getByRole("link", { name: "Explore" }).click();
      await expect(page).toHaveURL(/\/explore$/);
      await expect(nav.getByRole("link", { name: "Explore" })).toHaveAttribute("aria-current", "page");
      await nav.getByRole("link", { name: "Report", exact: true }).click();
      await expect(page).toHaveURL(/\/report$/);
      // The report form has its own action bar instead.
      await expect(page.getByRole("navigation", { name: "Main" })).toHaveCount(0);
    } else {
      await nav.getByRole("link", { name: "Report a problem" }).click();
      await expect(page).toHaveURL(/\/report$/);
      await page.getByRole("navigation", { name: "Main" }).getByRole("link", { name: "Explore" }).click();
      await expect(page).toHaveURL(/\/explore$/);
    }
  });
});
