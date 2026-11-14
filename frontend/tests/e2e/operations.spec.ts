import { expect, type Page, test } from "@playwright/test";

import {
  addMemberViaApi,
  closeExtraContexts,
  createCouncil,
  createDepartmentViaApi,
  createPlatformAdmin,
  expectNoHorizontalScroll,
  pageFor,
  PHOTO_FIXTURE,
  registerViaApi,
  setMemberDepartment,
  submitReportViaApi,
  useViewportFor,
} from "./support";

async function councilWithStaff() {
  const platform = await createPlatformAdmin();
  const council = await createCouncil(platform, `E2E Ops Council ${Date.now()}`);
  const admin = await registerViaApi("Ops Admin");
  await addMemberViaApi(platform, council.id, admin.email, "council_admin");
  const adminSession = { ...admin, csrf: (await (await admin.api.post("auth/login", { data: { email: admin.email, password: "e2e test passphrase" } })).json()).csrf_token };
  const roads = await createDepartmentViaApi(adminSession, council.id, "Roads");
  const verifier = await registerViaApi("Vimbai Verifier");
  const manager = await registerViaApi("Musa Manager");
  const officer = await registerViaApi("Tendai Officer");
  await addMemberViaApi(platform, council.id, verifier.email, "verification_officer");
  await addMemberViaApi(platform, council.id, manager.email, "department_manager");
  await addMemberViaApi(platform, council.id, officer.email, "maintenance_officer");
  await setMemberDepartment(adminSession, council.id, manager.id, roads.id);
  await setMemberDepartment(adminSession, council.id, officer.id, roads.id);
  const resident = await registerViaApi("Rudo Resident");
  const report = await submitReportViaApi(resident, council.id, { title: "Deep pothole on Kaguvi Street" });
  return { platform, council, admin, roads, verifier, manager, officer, resident, report };
}

async function act(page: Page, label: string, note?: string) {
  await page.getByRole("button", { name: label, exact: true }).click();
  if (note) await page.getByLabel(/Message to the reporter/).fill(note);
  await page.getByRole("button", { name: `Confirm: ${label}` }).click();
  await expect(page.getByRole("button", { name: `Confirm: ${label}` })).toHaveCount(0);
}

test.describe("council operations", () => {
  test.beforeEach(({ viewport }) => useViewportFor(viewport));
  test.afterEach(async () => closeExtraContexts());

  test("a report goes from verification to repair, and the reporter follows it", async ({ browser }) => {
    const w = await councilWithStaff();
    const reportUrl = `/council/${w.council.id}/reports/${w.report.id}`;

    // Verification officer: overview → queue → review → verify.
    const verifier = await pageFor(browser, w.verifier.email, `/council/${w.council.id}`);
    await expect(verifier.getByRole("link", { name: "New reports: 1" })).toBeVisible();
    await expectNoHorizontalScroll(verifier);
    await verifier.getByRole("link", { name: "New reports: 1" }).click();
    await expect(verifier).toHaveURL(/reports\?status=SUBMITTED$/);
    await verifier.getByRole("link", { name: /Deep pothole on Kaguvi Street/ }).click();
    await expect(verifier.getByText("Reported by Rudo Resident")).toBeVisible();
    await expectNoHorizontalScroll(verifier);
    await act(verifier, "Start review");
    await act(verifier, "Verify");
    await expect(verifier.getByText("Verified").first()).toBeVisible();
    await expect(verifier.getByRole("heading", { name: "Assign" })).toHaveCount(0);

    // Department manager assigns to the officer.
    const manager = await pageFor(browser, w.manager.email, reportUrl);
    await manager.getByLabel("Department").selectOption(w.roads.id);
    await manager.getByLabel("Officer (optional)").selectOption({ label: "Tendai Officer" });
    await manager.getByRole("button", { name: "Assign", exact: true }).click();
    await expect(manager.getByText("Roads, Tendai Officer")).toBeVisible();

    // Maintenance officer: My work → start → repair photo → resolve.
    const officer = await pageFor(browser, w.officer.email, `/council/${w.council.id}/work`);
    await expect(officer.getByText("Deep pothole on Kaguvi Street")).toBeVisible();
    await expect(officer.getByRole("link", { name: /Directions to CW-/ })).toHaveAttribute("href", /google\.com\/maps\/dir/);
    await expectNoHorizontalScroll(officer);
    await officer.getByRole("link", { name: /Open CW-/ }).click();
    await act(officer, "Start work");
    await officer.getByLabel("Add a repair photo").setInputFiles(PHOTO_FIXTURE);
    await expect(officer.getByRole("img", { name: "Repair photo 1" })).toBeVisible();
    await act(officer, "Mark resolved", "Pothole filled and compacted.");
    await expect(officer.getByText("Resolved").first()).toBeVisible();

    // The reporter sees the outcome, the message and the repair photo.
    const resident = await pageFor(browser, w.resident.email, `/reports/${w.report.id}`);
    await expect(resident.getByText("Pothole filled and compacted.")).toBeVisible();
    await expect(resident.getByRole("img", { name: "Repair photo 1" })).toBeVisible();
    await expect(resident.getByText("Resolved").first()).toBeVisible();
  });

  test("the council asks for information and the reporter answers in the app", async ({ browser }) => {
    const w = await councilWithStaff();
    const reportUrl = `/council/${w.council.id}/reports/${w.report.id}`;
    const verifier = await pageFor(browser, w.verifier.email, reportUrl);
    await act(verifier, "Start review");
    await act(verifier, "Ask the reporter for information", "Which side of the road is it on?");

    const resident = await pageFor(browser, w.resident.email, `/reports/${w.report.id}`);
    await expect(resident.getByText("The council needs more information")).toBeVisible();
    await expect(resident.getByText("Which side of the road is it on?").first()).toBeVisible();
    await resident.getByLabel("Your answer").fill("The northbound side, outside number 14.");
    await resident.getByRole("button", { name: "Send answer" }).click();
    await expect(resident.getByText("The council needs more information")).toHaveCount(0);
    await expectNoHorizontalScroll(resident);

    await verifier.reload();
    await expect(verifier.getByText("The northbound side, outside number 14.")).toBeVisible();
    await expect(verifier.getByRole("button", { name: "Verify", exact: true })).toBeVisible();
  });

  test("required messages are enforced and staff notes stay internal", async ({ browser }) => {
    const w = await councilWithStaff();
    const reportUrl = `/council/${w.council.id}/reports/${w.report.id}`;
    const verifier = await pageFor(browser, w.verifier.email, reportUrl);
    await verifier.getByRole("button", { name: "Reject", exact: true }).click();
    await verifier.getByRole("button", { name: "Confirm: Reject" }).click();
    await expect(verifier.getByText("Write a message for the reporter.")).toBeVisible();
    await verifier.getByRole("button", { name: "Cancel" }).click();

    await verifier.getByLabel("Add a staff note").fill("Same location as last month's complaint.");
    await verifier.getByRole("button", { name: "Add note" }).click();
    await expect(verifier.getByText("Same location as last month's complaint.")).toBeVisible();

    const resident = await pageFor(browser, w.resident.email, `/reports/${w.report.id}`);
    await expect(resident.getByRole("heading", { name: "Deep pothole on Kaguvi Street" })).toBeVisible();
    await expect(resident.getByText("last month's complaint")).toHaveCount(0);
  });

  test("staff who cannot act are told so, and residents cannot open council pages", async ({ browser }) => {
    const w = await councilWithStaff();
    const reportUrl = `/council/${w.council.id}/reports/${w.report.id}`;
    const officer = await pageFor(browser, w.officer.email, reportUrl);
    await expect(officer.getByText("There is nothing for you to do on this report at this stage.")).toBeVisible();
    const resident = await pageFor(browser, w.resident.email, reportUrl);
    await expect(resident.getByRole("alert").filter({ hasText: "No access" })).toBeVisible();
    await expect(resident.getByText("Deep pothole on Kaguvi Street")).toHaveCount(0);
  });

  test("administrators manage departments and staff departments", async ({ browser }) => {
    const w = await councilWithStaff();
    const admin = await pageFor(browser, w.admin.email, `/council/${w.council.id}/departments`);
    await admin.getByLabel("Name", { exact: true }).fill("Water and Sewerage");
    await admin.getByRole("button", { name: "Add department" }).click();
    await expect(admin.getByText("Water and Sewerage")).toBeVisible();
    const waterRow = admin.getByRole("listitem").filter({ hasText: "Water and Sewerage" });
    await waterRow.getByRole("button", { name: "Deactivate" }).click();
    await expect(admin.getByRole("listitem").filter({ hasText: "Water and Sewerage" }).getByText("Inactive")).toBeVisible();
    await expectNoHorizontalScroll(admin);

    await admin.getByRole("navigation", { name: "Council sections" }).getByRole("link", { name: "Staff" }).click();
    const row = admin.getByRole("listitem").filter({ hasText: "Tendai Officer" });
    await expect(row.getByLabel("Department for Tendai Officer")).toHaveValue(w.roads.id);
    await row.getByLabel("Department for Tendai Officer").selectOption("");
    await row.getByRole("button", { name: "Save changes" }).click();
    await expect(row.getByRole("button", { name: "Save changes" })).toHaveCount(0);
    await expect(row.getByLabel("Department for Tendai Officer")).toHaveValue("");
  });
});
