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

/** Harare city centre. */
export const HARARE = { latitude: -17.8292, longitude: 31.0522 };
export const PHOTO_FIXTURE = path.resolve(__dirname, "fixtures/pothole.jpg");

/**
 * Test setup only: council workflow endpoints arrive in Milestone 3, so
 * reports are marked verified directly in the database as the schema owner.
 */
export function setReportStatus(issueId: string, status: string) {
  const script = [
    "import os, sys",
    "from sqlalchemy import create_engine, text",
    "engine = create_engine(os.environ['CIVICWATCH_MIGRATION_DATABASE_URL'])",
    "with engine.begin() as c:",
    "    c.execute(text('UPDATE issues SET status = :s WHERE id = :i'), {'s': sys.argv[2], 'i': sys.argv[1]})",
  ].join("\n");
  execFileSync(BACKEND_PYTHON, ["-c", script, issueId, status], { cwd: BACKEND_DIR, stdio: "pipe" });
}

export async function submitReportViaApi(
  user: ApiUser,
  councilId: string,
  overrides: Record<string, unknown> = {},
): Promise<{ id: string; reference: string }> {
  const categories = await (await user.api.get("categories")).json();
  const response = await user.api.post("issues", {
    headers: { "X-CSRF-Token": user.csrf },
    data: {
      council_id: councilId,
      category_id: categories[0].id,
      title: "Pothole near the clinic",
      description: "Deep pothole that fills with water after rain.",
      latitude: HARARE.latitude,
      longitude: HARARE.longitude,
      visibility: "PUBLIC",
      ...overrides,
    },
  });
  expect(response.status(), await response.text()).toBe(201);
  return response.json();
}

export async function createDepartmentViaApi(admin: ApiUser, councilId: string, name: string): Promise<{ id: string }> {
  const response = await admin.api.post(`councils/${councilId}/departments`, {
    data: { name },
    headers: { "X-CSRF-Token": admin.csrf },
  });
  expect(response.status(), await response.text()).toBe(201);
  return response.json();
}

export async function setMemberDepartment(admin: ApiUser, councilId: string, userId: string, departmentId: string) {
  const members = await (await admin.api.get(`councils/${councilId}/members?page_size=100`)).json();
  const member = members.items.find((m: { user_id: string }) => m.user_id === userId);
  const response = await admin.api.patch(`councils/${councilId}/members/${member.membership_id}`, {
    data: { department_id: departmentId },
    headers: { "X-CSRF-Token": admin.csrf },
  });
  expect(response.status(), await response.text()).toBe(200);
}

/** Sign in as another person in a fresh browser context (separate cookies). */
export async function pageFor(browser: import("@playwright/test").Browser, email: string, next: string) {
  const context = await browser.newContext({ viewport: browserViewport });
  extraContexts.push(context);
  const page = await context.newPage();
  await signInViaUi(page, email, next);
  return page;
}

let browserViewport: { width: number; height: number } | null = null;
const extraContexts: import("@playwright/test").BrowserContext[] = [];

export async function closeExtraContexts() {
  await Promise.all(extraContexts.splice(0).map((context) => context.close()));
}
export function useViewportFor(viewport: { width: number; height: number } | null) {
  browserViewport = viewport;
}

/** Load the bundled SAMPLE boundaries (operator command), creating the sample councils. */
export function loadSampleBoundaries() {
  execFileSync(BACKEND_PYTHON, ["-m", "app.cli", "load-sample-boundaries", "--create-missing"], {
    cwd: BACKEND_DIR,
    stdio: "pipe",
  });
}

export function squareBoundary(lat: number, lon: number, half: number) {
  return {
    type: "Polygon",
    coordinates: [[[lon - half, lat - half], [lon + half, lat - half], [lon + half, lat + half], [lon - half, lat + half], [lon - half, lat - half]]],
  };
}
