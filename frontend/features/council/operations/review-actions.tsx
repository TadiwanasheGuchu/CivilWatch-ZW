"use client";

import { useId, useState } from "react";

import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { ApiError, errorMessage, fieldErrorsFrom } from "@/lib/api-client";

import { transitionIssue } from "./api";
import type { AvailableTransition, StaffIssueDetail } from "./types";
import { useIssueMutation } from "./use-issue-mutation";

const DESTRUCTIVE = new Set(["REJECTED", "DUPLICATE"]);

/** The status changes this person may make now — exactly as offered by the API. */
export function ReviewActions({ councilId, issue, csrfToken }: { councilId: string; issue: StaffIssueDetail; csrfToken: string }) {
  const [chosen, setChosen] = useState<AvailableTransition | null>(null);
  const [note, setNote] = useState("");
  const [duplicateOf, setDuplicateOf] = useState("");
  const headingId = useId();
  const mutation = useIssueMutation(councilId, issue.id, () =>
    transitionIssue(
      councilId,
      issue.id,
      {
        to_status: chosen!.to_status,
        note: note.trim() || undefined,
        duplicate_of_reference: chosen!.needs_duplicate_of ? duplicateOf.trim().toUpperCase() : undefined,
      },
      csrfToken,
    ),
  );
  const fieldErrors = fieldErrorsFrom(mutation.error);

  if (issue.available_transitions.length === 0) return null;

  function reset() {
    setChosen(null);
    setNote("");
    setDuplicateOf("");
    mutation.reset();
  }

  return (
    <section aria-labelledby={headingId} className="space-y-3 rounded-[var(--radius-panel)] border border-line bg-surface p-4">
      <h2 id={headingId} className="text-base font-semibold">
        Next step
      </h2>
      {!chosen ? (
        <div className="flex flex-wrap gap-2">
          {issue.available_transitions.map((transition) => (
            <Button
              key={transition.to_status}
              variant={DESTRUCTIVE.has(transition.to_status) ? "secondary" : "primary"}
              onClick={() => {
                mutation.reset();
                setChosen(transition);
              }}
            >
              {transition.label}
            </Button>
          ))}
        </div>
      ) : (
        <form
          className="space-y-3"
          onSubmit={(event) => {
            event.preventDefault();
            mutation.mutate(undefined, { onSuccess: reset });
          }}
        >
          <p className="font-medium">{chosen.label}</p>
          {chosen.needs_duplicate_of ? (
            <Field label="Reference of the original report" hint="For example CW-000123" error={fieldErrors.duplicate_of_reference}>
              <Input value={duplicateOf} onChange={(e) => setDuplicateOf(e.target.value)} autoCapitalize="characters" />
            </Field>
          ) : null}
          <Field
            label={chosen.note_required ? "Message to the reporter" : "Message to the reporter (optional)"}
            hint="The reporter sees this message. The public does not."
            error={fieldErrors.note}
          >
            <Textarea value={note} onChange={(e) => setNote(e.target.value)} maxLength={1000} rows={3} />
          </Field>
          {mutation.isError && !Object.keys(fieldErrors).length ? (
            <Alert tone="error">
              {mutation.error instanceof ApiError && mutation.error.code === "invalid_transition"
                ? "Someone else changed this report just now. It has been refreshed; check its status."
                : errorMessage(mutation.error)}
            </Alert>
          ) : null}
          <div className="flex flex-wrap gap-2">
            <Button type="submit" disabled={mutation.isPending}>
              {mutation.isPending ? "Saving…" : `Confirm: ${chosen.label}`}
            </Button>
            <Button type="button" variant="ghost" onClick={reset}>
              Cancel
            </Button>
          </div>
        </form>
      )}
    </section>
  );
}
