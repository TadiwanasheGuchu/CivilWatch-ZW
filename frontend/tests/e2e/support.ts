import { execFileSync } from "node:child_process";
import path from "node:path";

import { expect, request, type APIRequestContext, type Page } from "@playwright/test";

export const API_URL = process.env.E2E_API_URL ?? "http://localhost:8000/api/v1";
export const PASSWORD = "e2e test passphrase";

const BACKEND_DIR = path.resolve(__dirname, "../../../backend");
const BACKEND_PYTHON = process.env.E2E_BACKEND_PYTHON ?? path.join(BACKEND_DIR, ".venv/bin/python");

export function uniqueEmail(prefix: string): string {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}@example.com`;
}

/** A signed-in API client with its own cookie jar (a separate "browser"). */
export interface ApiUser {
  api: APIRequestContext;
  csrf: string;
  email: string;
  id: string;
}

export async function registerViaApi(fullName: string, email = uniqueEmail("user")): Promise<ApiUser> {
  const api = await request.newContext({ baseURL: `${API_URL}/` });
  const response = await api.post("auth/register", {
    data: { email, password: PASSWORD, full_name: fullName },
  });
  expect(response.status(), await response.text()).toBe(201);
  const body = await response.json();
  return { api, csrf: body.csrf_token, email, id: body.user.id };
}

/** Platform admins can only be appointed from the server's command line. */
export async function createPlatformAdmin(): Promise<ApiUser> {
  const user = await registerViaApi("E2E Platform Admin", uniqueEmail("platform"));
  execFileSync(BACKEND_PYTHON, ["-m", "app.cli", "grant-platform-admin", user.email], {
    cwd: BACKEND_DIR,
    stdio: "pipe",
  });
  const login = await user.api.post("auth/login", { data: { email: user.email, password: PASSWORD } });
  expect(login.status()).toBe(200);
  return { ...user, csrf: (await login.json()).csrf_token };
}

export async function createCouncil(admin: ApiUser, name: string): Promise<{ id: string; name: string }> {
  const slug = `e2e-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
  const response = await admin.api.post("councils", {
    data: { slug, name },
    headers: { "X-CSRF-Token": admin.csrf },
  });
  expect(response.status(), await response.text()).toBe(201);
  return response.json();
}

export async function addMemberViaApi(admin: ApiUser, councilId: string, email: string, role: string) {
  const response = await admin.api.post(`councils/${councilId}/members`, {
    data: { email, role },
    headers: { "X-CSRF-Token": admin.csrf },
  });
  expect(response.status(), await response.text()).toBe(201);
}

export async function signInViaUi(page: Page, email: string, next = "/account") {
  await page.goto(`/sign-in?next=${encodeURIComponent(next)}`);
  await page.getByLabel("Email address").fill(email);
  await page.getByLabel("Password", { exact: true }).fill(PASSWORD);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(new RegExp(`${next.replace(/[/?]/g, "\\$&")}$`));
}

export async function expectNoHorizontalScroll(page: Page) {
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  );
  expect(overflow).toBeLessThanOrEqual(0);
}
