import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { SystemStatusPanel } from "./system-status-panel";

function renderWithClient(ui: ReactNode) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

function mockFetch(status: number, body: unknown) {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(new Response(JSON.stringify(body), { status })),
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("SystemStatusPanel", () => {
  it("shows all services operational", async () => {
    mockFetch(200, { status: "ok", database: "ok", postgis: "ok", cache: "ok", storage: "ok" });
    renderWithClient(<SystemStatusPanel />);
    expect(await screen.findByText("All services are operational.")).toBeInTheDocument();
    expect(screen.getAllByText("Operational")).toHaveLength(4);
  });

  it("treats a 503 readiness body as a degraded state, not an error", async () => {
    mockFetch(503, { status: "degraded", database: "ok", postgis: "ok", cache: "unavailable", storage: "ok" });
    renderWithClient(<SystemStatusPanel />);
    expect(await screen.findByText(/Some services are unavailable/)).toBeInTheDocument();
    expect(screen.getByText("Unavailable")).toBeInTheDocument();
  });

  it("shows an actionable error when the API cannot be reached", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
    renderWithClient(<SystemStatusPanel />);
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "We could not reach the CivicWatch service.",
    );
    expect(screen.getByRole("button", { name: "Check platform status again" })).toBeEnabled();
  });
});
