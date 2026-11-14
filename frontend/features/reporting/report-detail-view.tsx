"use client";

import { ExternalLink, Globe, Lock, MapPin } from "lucide-react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useState } from "react";

import { Alert } from "@/components/ui/alert";
import { LoadError, LoadingRows } from "@/components/ui/page-states";
import { useSession } from "@/features/authentication/use-session";
import { LazyLocationMap } from "@/features/maps/lazy-location-map";
import { ApiError, errorMessage } from "@/lib/api-client";

import { useReport } from "./hooks";
import { formatDateTime, STATUS_EXPLANATIONS, STATUS_LABELS } from "./labels";
import { ReportPhotos } from "./report-photos";
import { StatusBadge } from "./status-badge";

export function ReportDetailView({ id }: { id: string }) {
  const { data: issue, isPending, isError, error, refetch } = useReport(id);
  const { data: session } = useSession();
  const justSubmitted = useSearchParams().get("submitted") === "1";
  const [mapFailed, setMapFailed] = useState(false);

  if (isPending) return <LoadingRows label="Loading report" rows={5} />;
  if (isError) {
    if (error instanceof ApiError && error.status === 404) {
      return (
        <Alert tone="error" title="Report not found">
          It may be private, still awaiting council verification, or the link may be wrong.{" "}
          {!session ? (
            <Link href={`/sign-in?next=${encodeURIComponent(`/reports/${id}`)}`} className="font-medium text-teal underline">
              Sign in if it is your report
            </Link>
          ) : null}
        </Alert>
      );
    }
    return <LoadError message={errorMessage(error)} onRetry={() => void refetch()} />;
  }

  const isOwn = issue.visibility !== undefined;
  const canEditPhotos = isOwn && issue.status === "SUBMITTED" && session ? session : null;

  return (
    <article className="space-y-6">
      {justSubmitted ? (
        <Alert tone="success" title="Report sent">
          Thank you. Your reference is <strong className="tabular">{issue.reference}</strong>. You can follow its
          progress here and under My reports.
        </Alert>
      ) : null}

      <header>
        <p className="text-sm text-slate tabular">
          {issue.reference} · {issue.category.name}
        </p>
        <h1 className="mt-1 text-2xl font-bold break-words">{issue.title}</h1>
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <StatusBadge status={issue.status} />
          {isOwn ? (
            <span className="inline-flex items-center gap-1 text-sm text-slate">
              {issue.visibility === "PRIVATE" ? (
                <>
                  <Lock aria-hidden="true" className="size-4" /> Private
                </>
              ) : (
                <>
                  <Globe aria-hidden="true" className="size-4" />
                  {issue.is_published ? "Public" : "Public after council verification"}
                </>
              )}
            </span>
          ) : null}
        </div>
        <p className="mt-2 text-sm text-navy-soft">{STATUS_EXPLANATIONS[issue.status]}</p>
      </header>

      <ReportPhotos issue={issue} editableBy={canEditPhotos} />

      <section aria-labelledby="details-heading" className="space-y-2">
        <h2 id="details-heading" className="text-lg font-semibold">
          Details
        </h2>
        <p className="whitespace-pre-line break-words">{issue.description}</p>
        <p className="text-sm text-slate">Reported to {issue.council.name}</p>
      </section>

      <section aria-labelledby="location-heading" className="space-y-2">
        <h2 id="location-heading" className="text-lg font-semibold">
          Location
        </h2>
        {issue.location_description ? (
          <p className="flex items-start gap-2">
            <MapPin aria-hidden="true" className="mt-1 size-4 shrink-0 text-teal" />
            {issue.location_description}
          </p>
        ) : null}
        {!mapFailed ? (
          <div className="overflow-hidden rounded-[var(--radius-control)] border border-line">
            <LazyLocationMap
              latitude={issue.latitude}
              longitude={issue.longitude}
              interactive={false}
              onError={() => setMapFailed(true)}
              label="Map showing the report location"
            />
          </div>
        ) : null}
        <a
          href={`https://www.openstreetmap.org/?mlat=${issue.latitude}&mlon=${issue.longitude}#map=18/${issue.latitude}/${issue.longitude}`}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex min-h-11 items-center gap-1.5 text-sm font-medium text-teal underline underline-offset-2"
        >
          Open in OpenStreetMap
          <ExternalLink aria-hidden="true" className="size-4" />
        </a>
      </section>

      <section aria-labelledby="timeline-heading" className="space-y-2">
        <h2 id="timeline-heading" className="text-lg font-semibold">
          Progress
        </h2>
        <ol className="space-y-3 border-l-2 border-line pl-4">
          {issue.history.map((change, index) => (
            <li key={`${change.to_status}-${index}`} className="relative">
              <span aria-hidden="true" className="absolute top-1.5 -left-[1.4rem] size-2.5 rounded-full bg-teal" />
              <p className="font-medium">{STATUS_LABELS[change.to_status]}</p>
              <p className="text-sm text-slate tabular">
                <time dateTime={change.created_at}>{formatDateTime(change.created_at)}</time>
              </p>
            </li>
          ))}
        </ol>
      </section>
    </article>
  );
}
