import { fireEvent, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { queueResponses, renderWithClient } from "@/tests/render";

import { SignInForm } from "./sign-in-form";
import { SESSION_QUERY_KEY } from "./use-session";

const replace = vi.fn();
let search = new URLSearchParams();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace, push: vi.fn() }),
  useSearchParams: () => search,
}));

const session = {
  user: { id: "u1", email: "a@example.com", full_name: "A", is_platform_admin: false, email_notifications: true, created_at: "" },
  csrf_token: "csrf",
  expires_at: "",
};

function fill(email: string, password: string) {
  fireEvent.change(screen.getByLabelText("Email address"), { target: { value: email } });
  fireEvent.change(screen.getByLabelText("Password"), { target: { value: password } });
  fireEvent.click(screen.getByRole("button", { name: "Sign in" }));
}

beforeEach(() => {
  replace.mockReset();
  search = new URLSearchParams();
});
afterEach(() => vi.unstubAllGlobals());

describe("SignInForm", () => {
  it("validates before calling the API", async () => {
    const fetchMock = queueResponses();
    renderWithClient(<SignInForm />);
    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));
    expect(await screen.findByText("Enter your email address.")).toBeInTheDocument();
    expect(screen.getByLabelText("Email address")).toHaveAttribute("aria-invalid", "true");
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("stores the session and goes to a safe next page", async () => {
    search = new URLSearchParams({ next: "/council/abc" });
    queueResponses({ status: 200, body: session });
    const { client } = renderWithClient(<SignInForm />);
    fill("a@example.com", "correct horse battery");
    await waitFor(() => expect(replace).toHaveBeenCalledWith("/council/abc"));
    expect(client.getQueryData(SESSION_QUERY_KEY)).toEqual(session);
  });

  it("never redirects off-site", async () => {
    search = new URLSearchParams({ next: "https://evil.example" });
    queueResponses({ status: 200, body: session });
    renderWithClient(<SignInForm />);
    fill("a@example.com", "correct horse battery");
    await waitFor(() => expect(replace).toHaveBeenCalledWith("/account"));
  });

  it("shows the API's message and clears the password on failure", async () => {
    queueResponses({
      status: 401,
      body: { error: { code: "authentication_required", message: "Email or password is incorrect.", details: null, request_id: "r" } },
    });
    renderWithClient(<SignInForm />);
    fill("a@example.com", "wrong password!");
    expect(await screen.findByRole("alert")).toHaveTextContent("Email or password is incorrect.");
    expect(screen.getByLabelText("Password")).toHaveValue("");
    expect(replace).not.toHaveBeenCalled();
  });

  it("explains lockouts", async () => {
    queueResponses({
      status: 429,
      body: { error: { code: "rate_limited", message: "Too many", details: { retry_after_seconds: 600 }, request_id: "r" } },
    });
    renderWithClient(<SignInForm />);
    fill("a@example.com", "whatever pass");
    expect(await screen.findByRole("alert")).toHaveTextContent("Please wait 10 minutes");
  });

  it("toggles password visibility", () => {
    renderWithClient(<SignInForm />);
    const toggle = screen.getByRole("button", { name: "Show password" });
    fireEvent.click(toggle);
    expect(screen.getByLabelText("Password")).toHaveAttribute("type", "text");
    expect(screen.getByRole("button", { name: "Hide password" })).toHaveAttribute("aria-pressed", "true");
  });
});
