"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";

import { fetchSession } from "./api";
import type { SessionData } from "./types";

export const SESSION_QUERY_KEY = ["auth", "session"] as const;

export function useSession() {
  return useQuery({
    queryKey: SESSION_QUERY_KEY,
    queryFn: ({ signal }) => fetchSession(signal),
    staleTime: 5 * 60_000,
  });
}

/** Replace the cached session after sign-in or a profile change. */
export function useSetSession() {
  const queryClient = useQueryClient();
  return (session: SessionData | null) => {
    const previous = queryClient.getQueryData<SessionData | null>(SESSION_QUERY_KEY);
    if (previous?.user.id !== session?.user.id) {
      // A different person (or nobody) is now signed in: never show them
      // responses cached for the previous user.
      queryClient.removeQueries({ predicate: (query) => query.queryKey[0] !== "auth" });
    }
    queryClient.setQueryData(SESSION_QUERY_KEY, session);
  };
}
