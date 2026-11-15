import { expect, test } from "@playwright/test";

import {
  addMemberViaApi,
  closeExtraContexts,
  createCouncil,
  createPlatformAdmin,
  expectNoHorizontalScroll,
  HARARE,
  loadSampleBoundaries,
  pageFor,
  registerViaApi,
  setReportStatus,
  signInViaUi,
  squareBoundary,
  submitReportViaApi,
  useViewportFor,
} from "./support";

test.use({ geolocation: HARARE, permissions: ["geolocation"] });

test.describe("maps", () => {
  test.beforeEach(({ viewport }) => useViewportFor(viewport));
  test.afterEach(async () => closeExtraContexts());

  test("explore map: markers, filter, preview and near me", async ({ page }) => {
    const platform = await createPlatformAdmin();
    const council = await createCouncil(platform, `E2E Map Council ${Date.now()}`);
    const reporter = await registerViaApi("Map Reporter");
    const tag = Date.now().toString(36);
    // A spot of its own, so "near me" is not crowded by other test runs' reports.
    const spot = { latitude: HARARE.latitude + (Math.random() - 0.5) * 0.08, longitude: HARARE.longitude + (Math.random() - 0.5) * 0.08 };
    await page.context().setGeolocation(spot);
    const report = await submitReportViaApi(reporter, council.id, { title: `Mapped pothole ${tag}`, ...spot });
    setReportStatus(report.id, "VERIFIED");

    await page.goto("/explore");
    await page.getByLabel("Council").selectOption(council.id);
    await page.getByRole("button", { name: "Map" }).click();
    const marker = page.getByRole("button", { name: "Report: Verified" });
    await expect(marker).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText("1 report in view")).toBeVisible();
    await expectNoHorizontalScroll(page);
    await marker.click();
    const preview = page.getByRole("region", { name: "Selected report" });
    await expect(preview.getByRole("heading", { name: `Mapped pothole ${tag}` })).toBeVisible();
    await expect(preview.getByRole("link", { name: "View report" })).toHaveAttribute("href", `/reports/${report.id}`);

    await page.getByRole("button", { name: "Heatmap" }).click();
    await expect(page.getByRole("button", { name: "Report: Verified" })).toHaveCount(0);
    await expect(page.getByRole("button", { name: "Heatmap" })).toHaveAttribute("aria-pressed", "true");

    await page.getByRole("button", { name: "List" }).click();
    await page.getByRole("button", { name: "Near me" }).click();
    const nearby = page.getByRole("link", { name: new RegExp(`Mapped pothole ${tag}`) });
    await expect(nearby).toBeVisible();
    await expect(nearby).toContainText(/m away/);
  });

  test("the report form chooses the council from the pin and points out similar reports", async ({ page }) => {
    loadSampleBoundaries();
    const resident = await registerViaApi("Pin Reporter");
    // Find the sample council the way the app does: from the location.
    const located = await (await resident.api.get(`councils/locate?latitude=${HARARE.latitude}&longitude=${HARARE.longitude}`)).json();
    const harare = located.find((c: { slug: string }) => c.slug === "harare");
    expect(harare, "sample Harare boundary should cover the city centre").toBeTruthy();
    const knownTitle = `Known pothole ${Date.now()}`;
    // Its own spot inside the sample boundary, so other test runs' reports don't crowd the list.
    const spot = { latitude: HARARE.latitude + (Math.random() - 0.5) * 0.08, longitude: HARARE.longitude + (Math.random() - 0.5) * 0.08 };
    await page.context().setGeolocation(spot);
    const existing = await submitReportViaApi(resident, harare.id, { title: knownTitle, ...spot });
    setReportStatus(existing.id, "VERIFIED");

    await signInViaUi(page, resident.email, "/report");
    await page.getByRole("radio", { name: /Roads and potholes/ }).check();
    await page.getByRole("button", { name: "Next" }).click();
    await page.getByLabel("Short title").fill("Pothole by the clinic gate");
    await page.getByLabel("What is the problem?").fill("Large pothole that fills with water.");
    await page.getByRole("button", { name: "Next" }).click();
    await page.getByRole("button", { name: "Next" }).click();
    await page.getByRole("button", { name: "Use my current location" }).click();

    await expect(page.getByText(/Council chosen from your pin: Harare City Council/)).toBeVisible();
    await expect(page.getByText(/based on a sample boundary/)).toBeVisible();
    await expect(page.getByLabel("Council")).toHaveValue(harare.id);
    await expect(page.getByText("Already reported nearby?")).toBeVisible();
    await expect(page.getByRole("link", { name: new RegExp(knownTitle) })).toBeVisible();
    await expectNoHorizontalScroll(page);
  });

  test("staff see their council's reports on a map and nearby possible duplicates", async ({ browser }) => {
    const platform = await createPlatformAdmin();
    const council = await createCouncil(platform, `E2E Staff Map ${Date.now()}`);
    const verifier = await registerViaApi("Map Verifier");
    await addMemberViaApi(platform, council.id, verifier.email, "verification_officer");
    const resident = await registerViaApi("Twin Reporter");
    const first = await submitReportViaApi(resident, council.id, { title: "Blocked drain A", visibility: "PRIVATE" });
    const second = await submitReportViaApi(resident, council.id, { title: "Blocked drain B" });

    const staff = await pageFor(browser, verifier.email, `/council/${council.id}/reports?view=map`);
    await expect(staff.getByRole("button", { name: "2 reports here. Zoom in" })).toBeVisible({ timeout: 15_000 });
    await expectNoHorizontalScroll(staff);

    await staff.goto(`/council/${council.id}/reports/${first.id}`);
    const panel = staff.getByRole("region", { name: "Possible duplicates nearby" });
    await expect(panel.getByText(second.reference)).toBeVisible();
    await expect(panel.getByText(/m away/)).toBeVisible();
  });

  test("platform administrators upload, check and remove boundaries", async ({ browser }) => {
    const platform = await createPlatformAdmin();
    const council = await createCouncil(platform, `E2E Boundary ${Date.now()}`);
    const admin = await pageFor(browser, platform.email, `/council/${council.id}/boundary`);
    await expect(admin.getByText(/has no boundary/)).toBeVisible();

    const file = (geometry: object) => ({
      name: "boundary.geojson",
      mimeType: "application/geo+json",
      buffer: Buffer.from(JSON.stringify(geometry)),
    });
    // Swapped coordinates are explained, not saved.
    await admin.getByLabel("GeoJSON file").setInputFiles(file(squareBoundary(HARARE.longitude, HARARE.latitude, 0.01)));
    await admin.getByRole("button", { name: "Save boundary" }).click();
    await expect(admin.getByText(/longitude, latitude/).last()).toBeVisible();

    await admin.getByLabel("GeoJSON file").setInputFiles(file(squareBoundary(-19.2, 29.0, 0.01)));
    await admin.getByRole("button", { name: "Save boundary" }).click();
    await expect(admin.getByText("Boundary saved")).toBeVisible();
    await expect(admin.getByText(/km²/)).toBeVisible();
    await expect(admin.getByText(/has an official boundary/)).toBeVisible();
    await expectNoHorizontalScroll(admin);

    await admin.getByRole("button", { name: "Remove boundary" }).click();
    await admin.getByRole("button", { name: "Remove", exact: true }).click();
    await expect(admin.getByText(/has no boundary/)).toBeVisible();
  });

  test("the boundary tab is only for platform administrators", async ({ browser }) => {
    const platform = await createPlatformAdmin();
    const council = await createCouncil(platform, `E2E No Boundary Tab ${Date.now()}`);
    const admin = await registerViaApi("Council Admin Only");
    await addMemberViaApi(platform, council.id, admin.email, "council_admin");
    const page = await pageFor(browser, admin.email, `/council/${council.id}`);
    const tabs = page.getByRole("navigation", { name: "Council sections" });
    await expect(tabs.getByRole("link", { name: "Staff" })).toBeVisible();
    await expect(tabs.getByRole("link", { name: "Boundary" })).toHaveCount(0);
  });
});
