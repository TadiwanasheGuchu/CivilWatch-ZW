"use client";

import { MutationCache, QueryCache, QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";

import { SESSION_QUERY_KEY } from "@/features/authentication/use-session";
import { ApiError } from "@/lib/api-client";

function createQueryClient(): QueryClient {
  // Any 401 or CSRF rejection means the session we hold is no longer valid
  // (expired, revoked or signed out elsewhere): refresh it so the UI updates.
  const onError = (error: unknown) => {
    if (
      error instanceof ApiError &&
      (error.code === "authentication_required" || error.code === "csrf_token_invalid")
    ) {
      void queryClient.invalidateQueries({ queryKey: SESSION_QUERY_KEY });
    }
  };
  const queryClient: QueryClient = new QueryClient({
    queryCache: new QueryCache({ onError }),
    mutationCache: new MutationCache({ onError }),
    defaultOptions: {
      queries: {
        // Slow, metered connections: avoid surprise refetches.
        refetchOnWindowFocus: false,
        staleTime: 60_000,
        // Retry network blips once, but never authorisation or validation errors.
        retry: (failureCount, error) =>
          failureCount < 1 && !(error instanceof ApiError && error.status < 500),
      },
    },
  });
  return queryClient;
}

export function Providers({ children }: { children: ReactNode }) {
  const [queryClient] = useState(createQueryClient);
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
}
