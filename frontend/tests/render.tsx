import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import type { ReactNode } from "react";
import { vi } from "vitest";

export function renderWithClient(ui: ReactNode) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return { client, ...render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>) };
}

/** Stub fetch with a queue of JSON responses, returned in order. */
export function queueResponses(...responses: Array<{ status: number; body?: unknown }>) {
  const mock = vi.fn();
  for (const { status, body } of responses) {
    mock.mockResolvedValueOnce(
      new Response(body === undefined ? null : JSON.stringify(body), { status }),
    );
  }
  vi.stubGlobal("fetch", mock);
  return mock;
}
