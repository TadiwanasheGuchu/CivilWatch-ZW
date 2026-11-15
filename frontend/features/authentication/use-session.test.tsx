import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it } from "vitest";

import type { SessionData } from "./types";
import { SESSION_QUERY_KEY, useSetSession } from "./use-session";

const sessionFor = (id: string): SessionData => ({
  user: { id, email: `${id}@example.com`, full_name: id, is_platform_admin: false, email_notifications: true, created_at: "" },
  csrf_token: "t",
  expires_at: "",
});

function setup() {
  const client = new QueryClient();
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  );
  const { result } = renderHook(() => useSetSession(), { wrapper });
  return { client, setSession: result.current };
}

describe("useSetSession", () => {
  it("drops cached data when a different user signs in", () => {
    const { client, setSession } = setup();
    client.setQueryData(SESSION_QUERY_KEY, sessionFor("alice"));
    client.setQueryData(["council", "memberships"], ["alice's councils"]);
    setSession(sessionFor("bob"));
    expect(client.getQueryData(["council", "memberships"])).toBeUndefined();
    expect(client.getQueryData(SESSION_QUERY_KEY)).toEqual(sessionFor("bob"));
  });

  it("keeps cached data when the same user's profile changes", () => {
    const { client, setSession } = setup();
    client.setQueryData(SESSION_QUERY_KEY, sessionFor("alice"));
    client.setQueryData(["council", "memberships"], ["alice's councils"]);
    setSession({ ...sessionFor("alice"), user: { ...sessionFor("alice").user, full_name: "Alice B" } });
    expect(client.getQueryData(["council", "memberships"])).toEqual(["alice's councils"]);
  });
});
