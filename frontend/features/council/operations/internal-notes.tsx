"use client";

import { ShieldCheck } from "lucide-react";
import { useId, useState } from "react";

import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { formatDateTime } from "@/features/reporting/labels";
import { errorMessage } from "@/lib/api-client";

import { addInternalUpdate } from "./api";
import type { StaffIssueDetail } from "./types";
import { useIssueMutation } from "./use-issue-mutation";

export function InternalNotes({ councilId, issue, csrfToken }: { councilId: string; issue: StaffIssueDetail; csrfToken: string }) {
  const [body, setBody] = useState("");
  const headingId = useId();
  const inputId = useId();
  const mutation = useIssueMutation(councilId, issue.id, () => addInternalUpdate(councilId, issue.id, body.trim(), csrfToken));

  return (
    <section aria-labelledby={headingId} className="space-y-3">
      <h2 id={headingId} className="flex items-center gap-2 text-lg font-semibold">
        <ShieldCheck aria-hidden="true" className="size-5 text-navy" />
        Staff notes
      </h2>
      <p className="text-sm text-slate">Only council staff can see these. They cannot be edited or deleted.</p>
      {issue.updates.length ? (
        <ol className="space-y-2">
          {issue.updates.map((update) => (
            <li key={update.id} className="rounded-[var(--radius-control)] border border-line bg-surface p-3">
              <p className="whitespace-pre-line break-words">{update.body}</p>
              <p className="mt-1 text-xs text-slate">
                {update.author ?? "Former staff"} · <time dateTime={update.created_at}>{formatDateTime(update.created_at)}</time>
              </p>
            </li>
          ))}
        </ol>
      ) : null}
      <form
        className="space-y-2"
        onSubmit={(event) => {
          event.preventDefault();
          mutation.mutate(undefined, { onSuccess: () => setBody("") });
        }}
      >
        <label htmlFor={inputId} className="block text-sm font-medium">
          Add a staff note
        </label>
        <Textarea id={inputId} value={body} onChange={(e) => setBody(e.target.value)} maxLength={2000} rows={3} />
        {mutation.isError ? <Alert tone="error">{errorMessage(mutation.error)}</Alert> : null}
        <Button type="submit" variant="secondary" disabled={!body.trim() || mutation.isPending}>
          {mutation.isPending ? "Saving…" : "Add note"}
        </Button>
      </form>
    </section>
  );
}
