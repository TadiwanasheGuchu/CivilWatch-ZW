import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError, apiSend, errorMessage, fieldErrorsFrom } from "./api-client";

afterEach(() => vi.unstubAllGlobals());

describe("apiSend", () => {
  it("sends JSON with the CSRF header and credentials", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ ok: true }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    await apiSend("PATCH", "/users/me", { body: { full_name: "A" }, csrfToken: "tok" });
    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(init.method).toBe("PATCH");
    expect(init.credentials).toBe("include");
    expect(init.headers).toMatchObject({ "X-CSRF-Token": "tok", "Content-Type": "application/json" });
    expect(init.body).toBe('{"full_name":"A"}');
  });

  it("resolves to undefined on 204", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 204 })));
    await expect(apiSend("POST", "/auth/logout", { csrfToken: "t" })).resolves.toBeUndefined();
  });
});

describe("fieldErrorsFrom", () => {
  it("maps body validation errors to fields and strips the pydantic prefix", () => {
    const error = new ApiError(422, "validation_error", "invalid", "r", [
      { location: ["body", "password"], message: "Value error, Password must be at least 10 characters." },
      { location: ["body"], message: "Value error, whole-body problem" },
      { location: ["query", "page"], message: "bad" },
    ]);
    expect(fieldErrorsFrom(error)).toEqual({ password: "Password must be at least 10 characters." });
  });

  it("ignores non-validation errors", () => {
    expect(fieldErrorsFrom(new ApiError(409, "conflict", "x", null))).toEqual({});
  });
});

describe("errorMessage", () => {
  it("explains rate limits in minutes", () => {
    const error = new ApiError(429, "rate_limited", "Too many", null, { retry_after_seconds: 90 });
    expect(errorMessage(error)).toBe("Too many attempts. Please wait 2 minutes and try again.");
  });

  it("hides server internals", () => {
    expect(errorMessage(new ApiError(500, "internal_error", "Traceback…", null))).toMatch(/Something went wrong/);
  });

  it("explains network failures", () => {
    expect(errorMessage(new TypeError("Failed to fetch"))).toMatch(/could not reach CivicWatch/);
  });
});
