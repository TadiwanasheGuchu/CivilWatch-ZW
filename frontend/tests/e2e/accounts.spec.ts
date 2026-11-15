import { expect, test } from "@playwright/test";

import { expectNoHorizontalScroll, PASSWORD, registerViaApi, signInViaUi, uniqueEmail } from "./support";

test.describe("accounts", () => {
  test("register, see the account page, sign out and sign back in", async ({ page }) => {
    const email = uniqueEmail("resident");
    await page.goto("/register");
    await expectNoHorizontalScroll(page);
    await page.getByLabel("Full name").fill("Chipo Resident");
    await page.getByLabel("Email address").fill(email);
    await page.getByLabel("Password", { exact: true }).fill(PASSWORD);
    await page.getByRole("button", { name: "Create account" }).click();

    await expect(page).toHaveURL(/\/account$/);
    await expect(page.getByRole("heading", { name: "Your account" })).toBeVisible();
    await expect(page.getByText(`Signed in as ${email}`)).toBeVisible();
    await expect(page.getByRole("link", { name: /Your account \(Chipo Resident\)/ })).toBeVisible();
    await expectNoHorizontalScroll(page);

    await page.getByRole("button", { name: "Sign out" }).click();
    await expect(page).toHaveURL(/\/$/);
    await expect(page.getByRole("banner").getByRole("link", { name: "Sign in" })).toBeVisible();

    await signInViaUi(page, email);
    await expect(page.getByText(`Signed in as ${email}`)).toBeVisible();
  });

  test("protected pages send signed-out visitors to sign in, then back", async ({ page }) => {
    const user = await registerViaApi("Tendai Moyo");
    await page.goto("/account");
    await expect(page).toHaveURL(/\/sign-in\?next=%2Faccount$/);
    await expectNoHorizontalScroll(page);
    await page.getByLabel("Email address").fill(user.email);
    await page.getByLabel("Password", { exact: true }).fill(PASSWORD);
    await page.getByRole("button", { name: "Sign in" }).click();
    await expect(page).toHaveURL(/\/account$/);
  });

  test("validation errors are shown next to the fields", async ({ page }) => {
    await page.goto("/register");
    await page.getByRole("button", { name: "Create account" }).click();
    await expect(page.getByText("Enter your full name.")).toBeVisible();
    await expect(page.getByLabel("Email address")).toHaveAttribute("aria-invalid", "true");

    const taken = await registerViaApi("Existing Person");
    await page.getByLabel("Full name").fill("Someone Else");
    await page.getByLabel("Email address").fill(taken.email);
    await page.getByLabel("Password", { exact: true }).fill(PASSWORD);
    await page.getByRole("button", { name: "Create account" }).click();
    await expect(page.getByText("An account with this email address already exists.")).toBeVisible();
  });

  test("wrong password is reported without revealing which part was wrong", async ({ page }) => {
    const user = await registerViaApi("Rudo Dube");
    await page.goto("/sign-in");
    await page.getByLabel("Email address").fill(user.email);
    await page.getByLabel("Password", { exact: true }).fill("not the password");
    await page.getByRole("button", { name: "Sign in" }).click();
    await expect(page.getByRole("alert").filter({ hasText: "incorrect" })).toHaveText(
      "Email or password is incorrect.",
    );
  });

  test("update name and change password", async ({ page }) => {
    const user = await registerViaApi("Nyasha Old");
    await signInViaUi(page, user.email);
    const name = page.getByLabel("Full name");
    await name.fill("Nyasha New");
    await page.getByRole("button", { name: "Save name" }).click();
    await expect(page.getByText("Your name has been updated.")).toBeVisible();
    await expect(page.getByRole("link", { name: /Your account \(Nyasha New\)/ })).toBeVisible();

    await page.getByLabel("Current password").fill(PASSWORD);
    await page.getByLabel("New password").fill("a different passphrase");
    await page.getByRole("button", { name: "Change password" }).click();
    await expect(page.getByText("You have been signed out on every other device.")).toBeVisible();
    // The API client registered the user in another "browser": that session has ended.
    const other = await user.api.get("users/me");
    expect(other.status()).toBe(401);
  });

  test("turn notification emails off and on again", async ({ page }) => {
    const user = await registerViaApi("Tendai Email");
    await signInViaUi(page, user.email);
    const toggle = page.getByLabel("Email me about my reports and assigned work");
    await expect(toggle).toBeChecked();
    await toggle.uncheck();
    await expect(page.getByText("Emails turned off.")).toBeVisible();
    await page.reload();
    await expect(toggle).not.toBeChecked();
    await toggle.check();
    await expect(page.getByText("Emails turned on.")).toBeVisible();
  });
});
