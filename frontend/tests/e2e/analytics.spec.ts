import { readFile } from "node:fs/promises";

import { expect, type Page, test } from "@playwright/test";

import {
  addMemberViaApi,
  type ApiUser,
  closeExtraContexts,
  createCouncil,
  createDepartmentViaApi,
  createPlatformAdmin,
  expectNoHorizontalScroll,
  pageFor,
  registerViaApi,
  setMemberDepartment,
  submitReportViaApi,
  useViewportFor,
} from "./support";

async function act(user: ApiUser, path: string, data: object) {
  const response = await user.api.post(path, { data, headers: { "X-CSRF-Token": user.csrf } });
  expect(response.status(), await response.text()).toBeLessThan(300);
}

/** One public report fixed, one private report waiting for review. */
async function scenario() {
  const platform = await createPlatformAdmin();
  const council = await createCouncil(platform, `E2E Progress ${Date.now()} ${Math.floor(Math.random() * 1e6)}`);
  const admin = await registerViaApi("Progress Admin");
  await addMemberViaApi(platform, council.id, admin.email, "council_admin");
  const roads = await createDepartmentViaApi(admin, council.id, "Roads");
  const officer = await registerViaApi("Progress Officer");
  await addMemberViaApi(platform, council.id, officer.email, "maintenance_officer");
  await setMemberDepartment(admin, council.id, officer.id, roads.id);
  const verifier = await registerViaApi("Progress Verifier");
  await addMemberViaApi(platform, council.id, verifier.email, "verification_officer");
  const resident = await registerViaApi("Progress Resident");

  const fixed = await submitReportViaApi(resident, council.id, { title: "Broken streetlight by the school" });
  const base = `councils/${council.id}/issues/${fixed.id}`;
  await act(admin, `${base}/transitions`, { to_status: "UNDER_REVIEW" });
  await act(admin, `${base}/transitions`, { to_status: "VERIFIED" });
  await act(admin, `${base}/assignment`, { department_id: roads.id, assignee_user_id: officer.id });
  await act(officer, `${base}/transitions`, { to_status: "IN_PROGRESS" });
  await act(officer, `${base}/transitions`, { to_status: "RESOLVED", note: "New lamp fitted." });
  const hidden = await submitReportViaApi(resident, council.id, {
    title: "Private report about a leaking pipe",
    visibility: "PRIVATE",
  });
  return { council, admin, verifier, resident, fixed, hidden };
}

/** A headline figure (the first group of figures on the page). */
function tile(page: Page, label: string) {
  return page
    .locator("dl")
    .first()
    .locator("> div").filter({ has: page.locator("dt", { hasText: new RegExp(`^${label}$`) }) });
}

test.describe("performance, exports and public progress", () => {
  test.beforeEach(({ viewport }) => useViewportFor(viewport));
  test.afterEach(async () => closeExtraContexts());

  test("staff see their council's performance and managers export it", async ({ browser }) => {
    const s = await scenario();
    const page = await pageFor(browser, s.admin.email, `/council/${s.council.id}`);
    await page.getByRole("navigation", { name: "Council sections" }).getByRole("link", { name: "Performance" }).click();
    await expect(page).toHaveURL(new RegExp(`/council/${s.council.id}/performance$`));
    await expect(tile(page, "Received")).toContainText("2");
    await expect(tile(page, "Fixed")).toContainText("1");
    await expect(tile(page, "Waiting for review")).toContainText("1");
    await expect(page.getByRole("region", { name: "Performance" }).getByText("Roads", { exact: true })).toBeVisible();
    await page.getByRole("combobox", { name: "Period" }).selectOption("30");
    await expect(tile(page, "Received")).toContainText("2");
    await expectNoHorizontalScroll(page);

    const download = page.waitForEvent("download");
    await page.getByRole("button", { name: "Download CSV" }).click();
    const file = await download;
    expect(file.suggestedFilename()).toMatch(/^civicwatch-.*\.csv$/);
    const csv = await readFile((await file.path())!, "utf-8");
    expect(csv).toContain(s.fixed.reference);
    expect(csv).toContain(s.hidden.reference);
    expect(csv).not.toContain(s.resident.email);
    expect(csv).not.toContain("Progress Resident");
    await expect(page.getByText("Your export has been downloaded.")).toBeVisible();
  });

  test("verification officers see figures but cannot export", async ({ browser }) => {
    const s = await scenario();
    const page = await pageFor(browser, s.verifier.email, `/council/${s.council.id}/performance`);
    await expect(tile(page, "Received")).toContainText("2");
    await expect(page.getByRole("button", { name: "Download CSV" })).toHaveCount(0);
  });

  test("the public progress page counts only verified public reports", async ({ page }) => {
    const s = await scenario();
    await page.goto("/");
    await page.getByRole("link", { name: "See how councils are doing" }).click();
    await expect(page.getByRole("heading", { name: "Council progress" })).toBeVisible();
    await page.getByRole("combobox", { name: "Council" }).selectOption({ label: s.council.name });
    // Two reports exist, but the private one is never counted.
    await expect(tile(page, "Verified reports")).toContainText("1");
    await expect(tile(page, "Fixed")).toContainText("1");
    await expect(tile(page, "Being worked on")).toContainText("0");
    await expect(page.getByText("Private report about a leaking pipe")).toHaveCount(0);
    await expectNoHorizontalScroll(page);
  });
});
