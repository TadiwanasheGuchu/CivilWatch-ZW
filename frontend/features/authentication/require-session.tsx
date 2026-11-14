"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";

import { LoadError, LoadingRows } from "@/components/ui/page-states";
import { errorMessage } from "@/lib/api-client";

import { signInHref } from "./redirect";
import type { SessionData } from "./types";
import { useSession } from "./use-session";

/**
 * Renders `children` with the signed-in session, or sends the visitor to
 * sign in. This only shapes the UI — the API enforces access on every call.
 */
export function RequireSession({ children }: { children: (session: SessionData) => ReactNode }) {
  const { data: session, isPending, isError, error, refetch } = useSession();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (session === null) router.replace(signInHref(pathname));
  }, [session, router, pathname]);

  if (isPending || session === null) return <LoadingRows label="Loading your account" />;
  if (isError) return <LoadError message={errorMessage(error)} onRetry={() => void refetch()} />;
  return <>{children(session)}</>;
}
