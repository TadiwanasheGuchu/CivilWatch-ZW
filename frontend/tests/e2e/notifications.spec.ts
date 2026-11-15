import { expect, test } from "@playwright/test";

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

async function scenario() {
  const platform = await createPlatformAdmin();
  const council = await createCouncil(platform, `E2E Notify ${Date.now()}`);
  const admin = await registerViaApi("Notify Admin");
  await addMemberViaApi(platform, council.id, admin.email, "council_admin");
  const roads = await createDepartmentViaApi(admin, council.id, "Roads");
  const officer = await registerViaApi("Notified Officer");
  await addMemberViaApi(platform, council.id, officer.email, "maintenance_officer");
  await setMemberDepartment(admin, council.id, officer.id, roads.id);
  const resident = await registerViaApi("Notified Resident");
  const report = await submitReportViaApi(resident, council.id, { title: "Collapsed drain cover" });
  const base = `councils/${council.id}/issues/${report.id}`;
  return { council, admin, roads, officer, resident, report, base };
}

test.describe("notifications and feedback", () => {
  test.beforeEach(({ viewport }) => useViewportFor(viewport));
  test.afterEach(async () => closeExtraContexts());

  test("the reporter is notified and the bell counts unread updates", async ({ browser }) => {
    const s = await scenario();
    await act(s.admin, `${s.base}/transitions`, { to_status: "UNDER_REVIEW" });
    await act(s.admin, `${s.base}/transitions`, { to_status: "NEEDS_INFORMATION", note: "Is the cover missing or broken?" });

    const page = await pageFor(browser, s.resident.email, "/");
    const bell = page.getByRole("link", { name: "Notifications, 2 unread" });
    await expect(bell).toBeVisible();
    await bell.click();
    await expect(page.getByRole("heading", { name: "Notifications" })).toBeVisible();
    await expect(page.getByText(`The council needs more information about ${s.report.reference}`)).toBeVisible();
    await expect(page.getByText("Is the cover missing or broken?")).toBeVisible();
    await expectNoHorizontalScroll(page);

    await page.getByRole("link", { name: new RegExp(`more information about ${s.report.reference}`) }).click();
    await expect(page).toHaveURL(new RegExp(`/reports/${s.report.id}$`));
    await expect(page.getByText("The council needs more information").first()).toBeVisible();
    await expect(page.getByRole("link", { name: "Notifications, 1 unread" })).toBeVisible();

    await page.goto("/notifications");
    await page.getByRole("button", { name: "Mark all as read" }).click();
    await expect(page.getByRole("link", { name: "Notifications", exact: true })).toBeVisible();
  });

  test("officers are told about new work, and about fixes the reporter disputes", async ({ browser }) => {
    const s = await scenario();
    await act(s.admin, `${s.base}/transitions`, { to_status: "UNDER_REVIEW" });
    await act(s.admin, `${s.base}/transitions`, { to_status: "VERIFIED" });
    await act(s.admin, `${s.base}/assignment`, { department_id: s.roads.id, assignee_user_id: s.officer.id });

    const officer = await pageFor(browser, s.officer.email, "/notifications");
    const work = officer.getByRole("link", { name: new RegExp(`New work assigned to you: ${s.report.reference}`) });
    await expect(work).toBeVisible();
    await work.click();
    await expect(officer).toHaveURL(new RegExp(`/council/${s.council.id}/reports/${s.report.id}$`));

    await act(s.officer, `${s.base}/transitions`, { to_status: "IN_PROGRESS" });
    await act(s.officer, `${s.base}/transitions`, { to_status: "RESOLVED", note: "Cover replaced." });

    // The reporter disagrees.
    const resident = await pageFor(browser, s.resident.email, `/reports/${s.report.id}`);
    await expect(resident.getByRole("heading", { name: "Was the problem fixed?" })).toBeVisible();
    await resident.getByRole("button", { name: "No" }).click();
    await resident.getByLabel("What is still wrong? (optional)").fill("The new cover is already cracked.");
    await resident.getByRole("button", { name: "Send to the council" }).click();
    await expect(resident.getByText("You told the council the problem was not fixed.")).toBeVisible();
    await expectNoHorizontalScroll(resident);

    await officer.goto("/notifications");
    await expect(officer.getByText(`The reporter says ${s.report.reference} is not fixed`)).toBeVisible();
    await officer.goto(`/council/${s.council.id}/reports/${s.report.id}`);
    await expect(officer.getByRole("heading", { name: "The reporter says it is not fixed" })).toBeVisible();
    await expect(officer.getByText("The new cover is already cracked.")).toBeVisible();
  });
});
