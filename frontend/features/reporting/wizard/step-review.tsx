"use client";

import { useMutation } from "@tanstack/react-query";
import { CloudOff, Send } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";

import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { signInHref } from "@/features/authentication/redirect";
import { useSession } from "@/features/authentication/use-session";
import { useOnline } from "@/hooks/use-online";
import { ApiError, errorMessage, fieldErrorsFrom } from "@/lib/api-client";

import { submitReport, uploadPhoto } from "../api";
import type { ReportDraft, StepId } from "../draft";
import { useCategories, useCouncilOptions } from "../hooks";
import { type SubmitResult, submitDraft } from "../submit-draft";
import { FIELD_STEPS } from "./validation";

interface ReviewStepProps {
  draft: ReportDraft;
  replace: (draft: ReportDraft) => Promise<void>;
  discard: () => Promise<void>;
  goTo: (step: StepId) => void;
}

function Row({
  label,
  value,
  step,
  goTo,
  locked,
}: {
  label: string;
  value: string;
  step: StepId;
  goTo: (s: StepId) => void;
  locked: boolean;
}) {
  return (
    <div className="flex items-start justify-between gap-3 py-3">
      <div className="min-w-0">
        <dt className="text-sm text-slate">{label}</dt>
        <dd className="mt-0.5 font-medium break-words">{value}</dd>
      </div>
      {/* Once the report exists on the server, editing the draft would change nothing. */}
      {locked ? null : (
        <Button variant="ghost" onClick={() => goTo(step)} aria-label={`Change ${label.toLowerCase()}`}>
          Change
        </Button>
      )}
    </div>
  );
}

export function ReviewStep({ draft, replace, discard, goTo }: ReviewStepProps) {
  const router = useRouter();
  const online = useOnline();
  const { data: session, isPending: sessionPending } = useSession();
  const categories = useCategories();
  const councils = useCouncilOptions();
  const [progress, setProgress] = useState<Record<string, number>>({});
  const [result, setResult] = useState<SubmitResult | null>(null);

  const category = categories.data?.find((c) => c.id === draft.categoryId)?.name ?? "—";
  const council = councils.data?.find((c) => c.id === draft.councilId)?.name ?? "—";
  const photoPosition = useMemo(() => new Map(draft.photos.map((p, i) => [p.id, i + 1])), [draft.photos]);

  async function finish(issueId: string) {
    await discard();
    router.replace(`/reports/${issueId}?submitted=1`);
  }

  const send = useMutation({
    mutationFn: async () => {
      if (!session) throw new Error("Not signed in");
      return submitDraft(draft, {
        submitReport: (report) => submitReport(report, session.csrf_token),
        uploadPhoto: (issueId, blob, onProgress) => uploadPhoto(issueId, blob, session.csrf_token, onProgress),
        saveDraft: replace,
        onPhotoProgress: (id, fraction) => setProgress((current) => ({ ...current, [id]: fraction })),
      });
    },
    onSuccess: async (outcome) => {
      setResult(outcome);
      if (outcome.failedPhotoIds.length === 0) await finish(outcome.issueId);
    },
  });

  const fieldErrors = fieldErrorsFrom(send.error);
  const firstField = Object.keys(fieldErrors)[0];
  const stepToFix = firstField ? FIELD_STEPS[firstField] : undefined;
  const failedCount = result?.failedPhotoIds.length ?? 0;
  const locked = Boolean(draft.submittedIssueId);

  return (
    <div className="space-y-5">
      <dl className="divide-y divide-line rounded-[var(--radius-control)] border border-line bg-surface px-4">
        <Row label="Problem" value={category} step="category" goTo={goTo} locked={locked} />
        <Row label="Title" value={draft.title.trim()} step="details" goTo={goTo} locked={locked} />
        <Row label="Description" value={draft.description.trim()} step="details" goTo={goTo} locked={locked} />
        <Row
          label="Photos"
          value={draft.photos.length ? `${draft.photos.length} photo${draft.photos.length === 1 ? "" : "s"}` : "None"}
          step="photos"
          goTo={goTo}
          locked={locked}
        />
        <Row
          label="Location"
          value={`${council}${draft.locationDescription.trim() ? ` · ${draft.locationDescription.trim()}` : ""}`}
          step="location"
          goTo={goTo}
          locked={locked}
        />
        <Row
          label="Who can see it"
          value={draft.visibility === "PRIVATE" ? "Private: you and council staff" : "Public, after council verification"}
          step="visibility"
          goTo={goTo}
          locked={locked}
        />
      </dl>

      {!online ? (
        <Alert tone="info" title="You are offline">
          <span className="inline-flex items-start gap-2">
            <CloudOff aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
            Your report is saved on this device. Send it when you are back online.
          </span>
        </Alert>
      ) : null}

      {!sessionPending && !session ? (
        <Alert tone="info" title="Sign in to send your report">
          Your report is saved on this device while you sign in.{" "}
          <Link href={signInHref("/report")} className="font-medium text-teal underline underline-offset-2">
            Sign in or create an account
          </Link>
        </Alert>
      ) : null}

      {send.isError ? (
        <Alert tone="error" title="Your report was not sent">
          {stepToFix ? (
            <>
              {fieldErrors[firstField!]}{" "}
              <button type="button" className="font-medium text-teal underline" onClick={() => goTo(stepToFix)}>
                Fix it
              </button>
            </>
          ) : send.error instanceof ApiError || send.error instanceof TypeError ? (
            `${errorMessage(send.error)} Your report is still saved on this device.`
          ) : (
            "Something went wrong. Your report is still saved on this device."
          )}
        </Alert>
      ) : null}

      {send.isPending && draft.photos.length ? (
        <ul aria-label="Photo upload progress" className="space-y-2">
          {draft.photos.map((photo) => {
            const done = Boolean(photo.uploadedPhotoId) || (progress[photo.id] ?? 0) >= 1;
            const percent = Math.round((photo.uploadedPhotoId ? 1 : (progress[photo.id] ?? 0)) * 100);
            return (
              <li key={photo.id} className="text-sm">
                <div className="flex justify-between">
                  <span>Photo {photoPosition.get(photo.id)}</span>
                  <span className="text-slate tabular">{done ? "Uploaded" : `${percent}%`}</span>
                </div>
                <div className="mt-1 h-2 overflow-hidden rounded-full bg-mist" role="progressbar" aria-valuenow={percent} aria-valuemin={0} aria-valuemax={100} aria-label={`Photo ${photoPosition.get(photo.id)} upload`}>
                  <div className="h-full bg-teal transition-[width]" style={{ width: `${percent}%` }} />
                </div>
              </li>
            );
          })}
        </ul>
      ) : null}

      {failedCount > 0 && result && !send.isPending ? (
        <Alert tone="error" title="Some photos did not upload">
          Your report was sent, but {failedCount} photo{failedCount === 1 ? "" : "s"} did not upload.{" "}
          {errorMessage(result.lastError)}
          <span className="mt-3 flex flex-wrap gap-2">
            <Button onClick={() => send.mutate()} disabled={!online}>
              Try again
            </Button>
            <Button variant="secondary" onClick={() => void finish(result.issueId)}>
              Continue without them
            </Button>
          </span>
        </Alert>
      ) : null}

      {failedCount === 0 ? (
        <Button
          size="lg"
          className="w-full"
          onClick={() => send.mutate()}
          disabled={!session || !online || send.isPending}
        >
          <Send aria-hidden="true" />
          {send.isPending ? "Sending…" : draft.submittedIssueId ? "Finish sending" : "Send report"}
        </Button>
      ) : null}
    </div>
  );
}
