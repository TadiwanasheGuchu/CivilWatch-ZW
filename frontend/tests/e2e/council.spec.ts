import { expect, test } from "@playwright/test";

import {
  addMemberViaApi,
  createCouncil,
  createPlatformAdmin,
  expectNoHorizontalScroll,
  registerViaApi,
  signInViaUi,
} from "./support";

test.describe("council workspace", () => {
  test("a council administrator manages staff and sees the audit log", async ({ page }) => {
    const platform = await createPlatformAdmin();
    const council = await createCouncil(platform, "E2E Harare City Council");
    const admin = await registerViaApi("Farai Admin");
    await addMemberViaApi(platform, council.id, admin.email, "council_admin");
    const officer = await registerViaApi("Rumbi Officer");

    await signInViaUi(page, admin.email);
    await page.getByRole("link", { name: /E2E Harare City Council/ }).click();
    await expect(page).toHaveURL(new RegExp(`/council/${council.id}$`));
    await expect(page.getByRole("heading", { name: "E2E Harare City Council" })).toBeVisible();
    await expect(page.getByText("Council administrator").first()).toBeVisible();
    await expectNoHorizontalScroll(page);

    // Add a staff member.
    await page.getByLabel("Email address").fill(officer.email);
    await page.getByLabel("Role", { exact: true }).selectOption("verification_officer");
    await page.getByRole("button", { name: "Add staff member" }).click();
    await expect(page.getByText("Rumbi Officer was added as Verification officer.")).toBeVisible();
    const row = page.getByRole("listitem").filter({ hasText: officer.email });
    await expect(row).toBeVisible();

    // Change their role.
    await row.getByLabel("Role for Rumbi Officer").selectOption("maintenance_officer");
    await row.getByRole("button", { name: "Save role" }).click();
    await expect(row.getByRole("button", { name: "Save role" })).toBeHidden();
    await expect(row.getByLabel("Role for Rumbi Officer")).toHaveValue("maintenance_officer");

    // The last administrator cannot demote themselves.
    const selfRow = page.getByRole("listitem").filter({ hasText: "(you)" });
    await selfRow.getByLabel("Role for Farai Admin").selectOption("maintenance_officer");
    await selfRow.getByRole("button", { name: "Save role" }).click();
    await expect(selfRow.getByRole("alert")).toContainText("keep at least one administrator");
    await selfRow.getByRole("button", { name: "Cancel" }).click();

    // Remove the officer, with confirmation.
    await row.getByRole("button", { name: "Remove from staff" }).click();
    await row.getByRole("button", { name: "Remove", exact: true }).click();
    await expect(page.getByRole("listitem").filter({ hasText: officer.email })).toHaveCount(0);

    // Every change is in the audit log, with who did it.
    await page.getByRole("link", { name: "Audit log" }).click();
    await expect(page).toHaveURL(new RegExp(`/council/${council.id}/audit$`));
    const log = page.getByRole("region", { name: "Audit log" });
    await expect(log.getByText("Removed a staff member (Maintenance officer)")).toBeVisible();
    await expect(
      log.getByText("Changed a staff member's role from Verification officer to Maintenance officer"),
    ).toBeVisible();
    await expect(log.getByText("Added a staff member as Council administrator")).toBeVisible();
    await expect(log.getByText(/E2E Platform Admin \(platform administrator\)/).first()).toBeVisible();
    await expectNoHorizontalScroll(page);
  });

  test("staff without the manage permission see a read-only staff list", async ({ page }) => {
    const platform = await createPlatformAdmin();
    const council = await createCouncil(platform, "E2E Mutare City Council");
    const officer = await registerViaApi("Tafadzwa Officer");
    await addMemberViaApi(platform, council.id, officer.email, "verification_officer");

    await signInViaUi(page, officer.email, `/council/${council.id}`);
    await expect(page.getByRole("region", { name: "Staff" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Add staff member" })).toHaveCount(0);
    await expect(page.getByRole("button", { name: "Remove from staff" })).toHaveCount(0);
    await expect(page.getByRole("link", { name: "Audit log" })).toHaveCount(0);
  });

  test("a resident cannot open a council workspace", async ({ page }) => {
    const platform = await createPlatformAdmin();
    const council = await createCouncil(platform, "E2E Gweru City Council");
    const resident = await registerViaApi("Kuda Resident");

    await signInViaUi(page, resident.email, `/council/${council.id}`);
    await expect(page.getByRole("alert").filter({ hasText: "No access" })).toContainText(
      "No access to this council",
    );
    await expect(page.getByRole("region", { name: "Staff" })).toHaveCount(0);
    await expectNoHorizontalScroll(page);
  });

  test("staff of two councils can switch between them", async ({ page }) => {
    const platform = await createPlatformAdmin();
    const first = await createCouncil(platform, "E2E Kwekwe Town Council");
    const second = await createCouncil(platform, "E2E Masvingo City Council");
    const person = await registerViaApi("Shared Staff");
    await addMemberViaApi(platform, first.id, person.email, "department_manager");
    await addMemberViaApi(platform, second.id, person.email, "maintenance_officer");

    await signInViaUi(page, person.email, `/council/${first.id}`);
    await expect(page.getByText("Department manager").first()).toBeVisible();
    await page.getByLabel("Switch council").selectOption(second.id);
    await expect(page).toHaveURL(new RegExp(`/council/${second.id}$`));
    await expect(page.getByRole("heading", { name: "E2E Masvingo City Council" })).toBeVisible();
    await expect(page.getByText("Maintenance officer").first()).toBeVisible();
  });
});
