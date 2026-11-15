"use client";

import { useMutation } from "@tanstack/react-query";
import { useId, useState } from "react";

import { errorMessage } from "@/lib/api-client";

import { updateProfile } from "./api";
import type { SessionData } from "./types";
import { useSetSession } from "./use-session";

/** Whether notifications are also sent by email. Saves as soon as it is changed. */
export function EmailPreference({ session }: { session: SessionData }) {
  const setSession = useSetSession();
  const id = useId();
  // Shown immediately; put back if saving fails.
  const [checked, setChecked] = useState(session.user.email_notifications);
  const mutation = useMutation({
    mutationFn: (enabled: boolean) => updateProfile({ email_notifications: enabled }, session.csrf_token),
    onSuccess: (user) => setSession({ ...session, user }),
    onError: () => setChecked(session.user.email_notifications),
  });

  return (
    <div className="space-y-2">
      <div className="flex items-start gap-3">
        <input
          id={id}
          type="checkbox"
          className="mt-0.5 size-6 shrink-0 accent-teal"
          checked={checked}
          disabled={mutation.isPending}
          onChange={(event) => {
            setChecked(event.target.checked);
            mutation.mutate(event.target.checked);
          }}
          aria-describedby={`${id}-hint`}
        />
        <div>
          <label htmlFor={id} className="font-medium">
            Email me about my reports and assigned work
          </label>
          <p id={`${id}-hint`} className="text-sm text-slate">
            Sent to {session.user.email}.
          </p>
        </div>
      </div>
      <p role="status" className="text-sm text-slate">
        {mutation.isPending ? "Saving…" : mutation.isSuccess ? (checked ? "Emails turned on." : "Emails turned off.") : ""}
      </p>
      {mutation.isError ? (
        <p role="alert" className="text-sm font-medium text-red-text">
          {errorMessage(mutation.error)}
        </p>
      ) : null}
    </div>
  );
}
