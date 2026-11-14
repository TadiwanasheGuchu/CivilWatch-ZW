import { expect, type Page, test } from "@playwright/test";

import {
  createCouncil,
  createPlatformAdmin,
  expectNoHorizontalScroll,
  HARARE,
  PHOTO_FIXTURE,
  registerViaApi,
  signInViaUi,
} from "./support";

test.use({ geolocation: HARARE, permissions: ["geolocation"] });

async function councilFixture() {
  const platform = await createPlatformAdmin();
  return createCouncil(platform, `E2E Council ${Date.now()}`);
}

async function next(page: Page) {
  await page.getByRole("button", { name: /^(Next|Review)$/ }).click();
}

async function fillUpToReview(page: Page, councilName: string, withPhoto = true) {
  await page.goto("/report");
  await expect(page.getByRole("heading", { name: "What kind of problem is it?" })).toBeVisible();
  await expectNoHorizontalScroll(page);
  await page.getByRole("radio", { name: /Roads and potholes/ }).check();
  await next(page);

  await page.getByLabel("Short title").fill("Deep pothole outside the clinic");
  await page.getByLabel("What is the problem?").fill("Wide, deep pothole in the left lane. Cars swerve into traffic.");
  await next(page);

  await expect(page.getByRole("heading", { name: "Add photos" })).toBeVisible();
  if (withPhoto) {
    await page.getByTestId("gallery-input").setInputFiles(PHOTO_FIXTURE);
    await expect(page.getByRole("img", { name: "Photo 1" })).toBeVisible();
  }
  await next(page);

  await page.getByLabel("Council").selectOption({ label: councilName });
  await page.getByRole("button", { name: "Use my current location" }).click();
  await expect(page.getByText(/Pin set at -17\.8292/)).toBeVisible();
  await page.getByLabel("Landmark or address (optional)").fill("Opposite the clinic gate");
  await expectNoHorizontalScroll(page);
  await next(page);

  await page.getByRole("radio", { name: /Public/ }).check();
  await next(page);
  await expect(page.getByRole("heading", { name: "Check and send" })).toBeVisible();
}

test.describe("reporting a problem", () => {
  test("a resident reports a pothole with a photo and follows it", async ({ page }) => {
    const council = await councilFixture();
    const resident = await registerViaApi("Chipo Resident");
    await signInViaUi(page, resident.email);

    await fillUpToReview(page, council.name);
    await expect(page.getByText("Deep pothole outside the clinic")).toBeVisible();
    await expectNoHorizontalScroll(page);
    await page.getByRole("button", { name: "Send report" }).click();

    await expect(page).toHaveURL(/\/reports\/[0-9a-f-]+\?submitted=1$/);
    await expect(page.getByText("Report sent")).toBeVisible();
    await expect(page.getByText(/CW-\d{6}/).first()).toBeVisible();
    await expect(page.getByText("Public after council verification")).toBeVisible();
    await expect(page.getByRole("img", { name: "Photo 1 of the problem" })).toBeVisible();
    await expect(page.getByText("Opposite the clinic gate")).toBeVisible();
    await expectNoHorizontalScroll(page);

    await page.goto("/my-reports");
    await expect(page.getByRole("link", { name: /Deep pothole outside the clinic/ })).toBeVisible();
    await expect(page.getByText("Submitted").first()).toBeVisible();

    // The draft was cleared once everything was sent.
    await page.goto("/report");
    await expect(page.getByText("We restored your unsent report")).toHaveCount(0);
  });

  test("validation stops each step until it is complete", async ({ page }) => {
    await page.goto("/report");
    await next(page);
    await expect(page.getByText("Choose what kind of problem this is.")).toBeVisible();
    await page.getByRole("radio", { name: /Streetlights/ }).check();
    await next(page);
    await page.getByLabel("Short title").fill("Dark");
    await next(page);
    await expect(page.getByText("Give the problem a short title of at least 5 characters.")).toBeVisible();
    await expect(page.getByText("Describe the problem in at least 10 characters.")).toBeVisible();
  });

  test("a draft survives a reload, and signing in keeps it", async ({ page }) => {
    const council = await councilFixture();
    await fillUpToReview(page, council.name);
    // Signed out: the report cannot be sent yet, but nothing is lost.
    await expect(page.getByText("Sign in to send your report")).toBeVisible();
    await expect(page.getByRole("button", { name: "Send report" })).toBeDisabled();

    await page.reload();
    await expect(page.getByText("We restored your unsent report")).toBeVisible();
    await expect(page.getByText("Deep pothole outside the clinic")).toBeVisible();

    const resident = await registerViaApi("Late Signer");
    await page.getByRole("link", { name: "Sign in or create an account" }).click();
    await page.getByLabel("Email address").fill(resident.email);
    await page.getByLabel("Password", { exact: true }).fill("e2e test passphrase");
    await page.getByRole("button", { name: "Sign in" }).click();
    await expect(page).toHaveURL(/\/report$/);
    await expect(page.getByRole("heading", { name: "Check and send" })).toBeVisible();
    await page.getByRole("button", { name: "Send report" }).click();
    await expect(page.getByText("Report sent")).toBeVisible();
  });

  test("offline: the report waits on the device until the connection returns", async ({ page, context }) => {
    const council = await councilFixture();
    const resident = await registerViaApi("Offline Reporter");
    await signInViaUi(page, resident.email);
    await fillUpToReview(page, council.name, false);

    await context.setOffline(true);
    await expect(page.getByText("You are offline")).toBeVisible();
    await expect(page.getByRole("button", { name: "Send report" })).toBeDisabled();
    await context.setOffline(false);
    await expect(page.getByText("You are offline")).toHaveCount(0);
    await page.getByRole("button", { name: "Send report" }).click();
    await expect(page.getByText("Report sent")).toBeVisible();
  });

  test("a failed photo upload can be retried without creating a second report", async ({ page }) => {
    const council = await councilFixture();
    const resident = await registerViaApi("Patchy Signal");
    await signInViaUi(page, resident.email);
    await fillUpToReview(page, council.name);

    let blocked = true;
    await page.route("**/api/v1/issues/*/photos", (route) => (blocked ? route.abort("failed") : route.continue()));
    await page.getByRole("button", { name: "Send report" }).click();
    await expect(page.getByText("Some photos did not upload")).toBeVisible();

    blocked = false;
    await page.getByRole("button", { name: "Try again" }).click();
    await expect(page).toHaveURL(/submitted=1$/);
    await expect(page.getByRole("img", { name: "Photo 1 of the problem" })).toBeVisible();

    await page.goto("/my-reports");
    await expect(page.getByRole("link", { name: /Deep pothole outside the clinic/ })).toHaveCount(1);
  });
});

test("signing out deletes an unsent draft from a shared phone", async ({ page }) => {
  const resident = await registerViaApi("Shared Phone");
  await signInViaUi(page, resident.email);
  await page.goto("/report");
  await page.getByRole("radio", { name: /Roads and potholes/ }).check();
  await page.getByRole("button", { name: "Next" }).click();
  await page.getByLabel("Short title").fill("Something private");
  await page.goto("/account");
  await page.getByRole("button", { name: "Sign out" }).click();
  await expect(page).toHaveURL(/\/$/);
  await page.goto("/report");
  await expect(page.getByRole("heading", { name: "What kind of problem is it?" })).toBeVisible();
  await expect(page.getByText("We restored your unsent report")).toHaveCount(0);
});
