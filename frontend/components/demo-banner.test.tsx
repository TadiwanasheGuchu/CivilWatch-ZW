import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

afterEach(() => {
  vi.unstubAllEnvs();
  vi.resetModules();
});

async function renderBanner() {
  const { DemoBanner } = await import("./demo-banner");
  return render(<DemoBanner />);
}

describe("DemoBanner", () => {
  it("is hidden on real deployments", async () => {
    vi.stubEnv("NEXT_PUBLIC_DEMO_MODE", "");
    await renderBanner();
    expect(screen.queryByRole("note")).toBeNull();
  });

  it("labels demonstration sites as sample data", async () => {
    vi.stubEnv("NEXT_PUBLIC_DEMO_MODE", "true");
    await renderBanner();
    expect(screen.getByRole("note", { name: "Demonstration site" })).toHaveTextContent("sample data");
  });
});
