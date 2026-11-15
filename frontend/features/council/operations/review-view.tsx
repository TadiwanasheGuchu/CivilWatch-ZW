"use client";

import { ArrowLeft, Lock, Navigation } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { Alert } from "@/components/ui/alert";
import { LoadError, LoadingRows } from "@/components/ui/page-states";
import { CouncilShell } from "@/features/council/council-shell";
import { LazyLocationMap } from "@/features/maps/lazy-location-map";
import { formatDateTime, STATUS_LABELS } from "@/features/reporting/labels";
import { StatusBadge } from "@/features/reporting/status-badge";
import { ApiError, errorMessage } from "@/lib/api-client";

import { directionsUrl } from "./api";
import { AssignPanel } from "./assign-panel";
import { useStaffIssue } from "./hooks";
import { InternalNotes } from "./internal-notes";
import { NearbyPanel } from "./nearby-panel";
import { PhotoGrid, RepairPhotoUpload } from "./repair-photos";
import { ReviewActions } from "./review-actions";
import type { StaffIssueDetail } from "./types";

export function ReviewView({ councilId, issueId }: { councilId: string; issueId: string }) {
  return (
    <CouncilShell councilId={councilId} tab="reports">
      {(_, session) => <Review councilId={councilId} issueId={issueId} csrfToken={session.csrf_token} />}
    </CouncilShell>
  );
}

function Review({ councilId, issueId, csrfToken }: { councilId: string; issueId: string; csrfToken: string }) {
  const { data: issue, isPending, isError, error, refetch } = useStaffIssue(councilId, issueId);
  if (isPending) return <LoadingRows label="Loading report" rows={6} />;
  if (isError) {
    if (error instanceof ApiError && error.status === 404) {
      return <Alert tone="error" title="Report not found">It does not belong to this council.</Alert>;
    }
    return <LoadError message={errorMessage(error)} onRetry={() => void refetch()} />;
  }
  return (
    <div className="space-y-6">
      <Link href={`/council/${councilId}/reports`} className="inline-flex min-h-11 items-center gap-1 text-sm font-medium text-teal">
        <ArrowLeft aria-hidden="true" className="size-4" /> All reports
      </Link>
      {/* Phones: summary, then actions, then details. Desktop: actions in a sidebar. */}
      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_22rem]">
        <div className="lg:col-start-1 lg:row-start-1">
          <ReportSummary issue={issue} />
        </div>
        <div className="space-y-4 lg:sticky lg:top-4 lg:col-start-2 lg:row-span-2 lg:row-start-1 lg:self-start">
          <ReviewActions key={issue.status} councilId={councilId} issue={issue} csrfToken={csrfToken} />
          {issue.can_assign ? (
            <AssignPanel key={issue.assignment?.assigned_at ?? "none"} councilId={councilId} issue={issue} csrfToken={csrfToken} />
          ) : null}
          {["SUBMITTED", "UNDER_REVIEW", "NEEDS_INFORMATION"].includes(issue.status) ? (
            <NearbyPanel councilId={councilId} issueId={issue.id} />
          ) : null}
          {issue.available_transitions.length === 0 && !issue.can_assign ? (
            <p className="rounded-[var(--radius-panel)] border border-line bg-surface p-4 text-sm text-slate">
              There is nothing for you to do on this report at this stage.
            </p>
          ) : null}
        </div>
        <div className="space-y-6 lg:col-start-1 lg:row-start-2">
          <ReportBody issue={issue} councilId={councilId} csrfToken={csrfToken} />
          <InternalNotes councilId={councilId} issue={issue} csrfToken={csrfToken} />
        </div>
      </div>
    </div>
  );
}

function ReportSummary({ issue }: { issue: StaffIssueDetail }) {
  return (
    <header className="space-y-2">
      <p className="text-sm text-slate tabular">
        {issue.reference} · {issue.category.name}
      </p>
      <h1 className="text-2xl font-bold break-words">{issue.title}</h1>
      <div className="flex flex-wrap items-center gap-2">
        <StatusBadge status={issue.status} />
        {issue.visibility === "PRIVATE" ? (
          <span className="inline-flex items-center gap-1 text-sm text-slate">
            <Lock aria-hidden="true" className="size-4" /> Private report
          </span>
        ) : (
          <span className="text-sm text-slate">Public report</span>
        )}
      </div>
      <dl className="grid gap-x-6 gap-y-1 text-sm sm:grid-cols-2">
        <div>
          <dt className="inline text-slate">Reported by </dt>
          <dd className="inline font-medium">{issue.reporter_name}</dd>
        </div>
        <div>
          <dt className="inline text-slate">Received </dt>
          <dd className="inline">{formatDateTime(issue.created_at)}</dd>
        </div>
        {issue.assignment ? (
          <div className="sm:col-span-2">
            <dt className="inline text-slate">Assigned to </dt>
            <dd className="inline font-medium">
              {issue.assignment.department.name}
              {issue.assignment.assignee ? `, ${issue.assignment.assignee.full_name}` : " (whole department)"}
            </dd>
          </div>
        ) : null}
        {issue.duplicate_of ? (
          <div className="sm:col-span-2">
            <dt className="inline text-slate">Duplicate of </dt>
            <dd className="inline font-medium tabular">{issue.duplicate_of.reference}</dd>
          </div>
        ) : null}
      </dl>
    </header>
  );
}

function ReportBody({ issue, councilId, csrfToken }: { issue: StaffIssueDetail; councilId: string; csrfToken: string }) {
  const [mapFailed, setMapFailed] = useState(false);
  return (
    <>
      {issue.feedback ? (
        <section
          aria-labelledby="feedback-heading"
          className={
            issue.feedback.fixed
              ? "space-y-1 rounded-[var(--radius-panel)] border-l-4 border-teal bg-surface p-4"
              : "space-y-1 rounded-[var(--radius-panel)] border-l-4 border-red bg-surface p-4"
          }
        >
          <h2 id="feedback-heading" className="text-base font-semibold">
            {issue.feedback.fixed ? "The reporter says it is fixed" : "The reporter says it is not fixed"}
          </h2>
          {issue.feedback.comment ? <p className="whitespace-pre-line break-words">{issue.feedback.comment}</p> : null}
          <p className="text-xs text-slate">{formatDateTime(issue.feedback.created_at)}</p>
        </section>
      ) : null}

      <section aria-labelledby="description-heading" className="space-y-2">
        <h2 id="description-heading" className="text-lg font-semibold">Description</h2>
        <p className="whitespace-pre-line break-words">{issue.description}</p>
      </section>

      {issue.photos.length ? (
        <section aria-labelledby="photos-heading" className="space-y-2">
          <h2 id="photos-heading" className="text-lg font-semibold">Reporter&apos;s photos</h2>
          <PhotoGrid photos={issue.photos} label="Reporter photo" />
        </section>
      ) : null}

      {issue.repair_photos.length || issue.can_add_repair_photos ? (
        <section aria-labelledby="repair-heading" className="space-y-2">
          <h2 id="repair-heading" className="text-lg font-semibold">Repair photos</h2>
          {issue.repair_photos.length ? <PhotoGrid photos={issue.repair_photos} label="Repair photo" /> : null}
          {issue.can_add_repair_photos ? <RepairPhotoUpload councilId={councilId} issueId={issue.id} csrfToken={csrfToken} /> : null}
        </section>
      ) : null}

      <section aria-labelledby="location-heading" className="space-y-2">
        <h2 id="location-heading" className="text-lg font-semibold">Location</h2>
        {issue.location_description ? <p>{issue.location_description}</p> : null}
        {!mapFailed ? (
          <div className="overflow-hidden rounded-[var(--radius-control)] border border-line">
            <LazyLocationMap latitude={issue.latitude} longitude={issue.longitude} interactive={false} onError={() => setMapFailed(true)} label="Map showing the report location" />
          </div>
        ) : null}
        <a href={directionsUrl(issue.latitude, issue.longitude)} target="_blank" rel="noopener noreferrer" className="inline-flex min-h-11 items-center gap-1.5 text-sm font-medium text-teal underline underline-offset-2">
          <Navigation aria-hidden="true" className="size-4" /> Get directions
        </a>
      </section>

      <section aria-labelledby="history-heading" className="space-y-2">
        <h2 id="history-heading" className="text-lg font-semibold">History</h2>
        <ol className="space-y-3 border-l-2 border-line pl-4">
          {issue.history.map((change, index) => (
            <li key={`${change.created_at}-${index}`} className="relative">
              <span aria-hidden="true" className="absolute top-1.5 -left-[1.4rem] size-2.5 rounded-full bg-teal" />
              <p className="font-medium">{STATUS_LABELS[change.to_status]}</p>
              <p className="text-xs text-slate">
                {change.changed_by ?? "Former staff"} · <time dateTime={change.created_at}>{formatDateTime(change.created_at)}</time>
              </p>
              {change.note ? (
                <p className="mt-1 rounded bg-mist px-2 py-1 text-sm whitespace-pre-line break-words">
                  <span className="sr-only">Message to the reporter: </span>
                  {change.note}
                </p>
              ) : null}
            </li>
          ))}
        </ol>
      </section>
    </>
  );
}
