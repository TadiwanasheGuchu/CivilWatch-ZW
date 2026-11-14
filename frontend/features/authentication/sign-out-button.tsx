"use client";

import { useMutation } from "@tanstack/react-query";
import { LogOut } from "lucide-react";

import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { ApiError, errorMessage } from "@/lib/api-client";

import { openDraftStore } from "@/features/reporting/draft-store";

import { signOut } from "./api";
import type { SessionData } from "./types";

/**
 * After signing out we load the home page afresh rather than navigating in
 * the app: it discards every cached response from the old session, and
 * avoids protected pages reacting to the sign-out mid-navigation.
 *
 * Phones are often shared, so an unsent report draft (and its photos) is
 * deleted from the device too.
 */
async function leaveSignedOut() {
  try {
    await (await openDraftStore()).clear();
  } finally {
    window.location.replace("/");
  }
}

export function SignOutButton({ session }: { session: SessionData }) {
  const mutation = useMutation({
    mutationFn: () => signOut(session.csrf_token),
    onSuccess: () => void leaveSignedOut(),
    onError: (error) => {
      // Already signed out on the server (expired or revoked): treat as done.
      if (error instanceof ApiError && error.status === 401) void leaveSignedOut();
    },
  });
  const showError = mutation.isError && !(mutation.error instanceof ApiError && mutation.error.status === 401);

  return (
    <div className="space-y-3">
      {showError ? <Alert tone="error">{errorMessage(mutation.error)}</Alert> : null}
      <Button variant="secondary" onClick={() => mutation.mutate()} disabled={mutation.isPending || mutation.isSuccess}>
        <LogOut aria-hidden="true" />
        {mutation.isPending || mutation.isSuccess ? "Signing out…" : "Sign out"}
      </Button>
    </div>
  );
}
