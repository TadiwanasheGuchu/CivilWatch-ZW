"use client";

import { MapPin, Navigation } from "lucide-react";
import Link from "next/link";

import { buttonVariants } from "@/components/ui/button";
import { EmptyState, LoadError, LoadingRows } from "@/components/ui/page-states";
import { CouncilShell } from "@/features/council/council-shell";
import { formatDate } from "@/features/reporting/labels";
import { StatusBadge } from "@/features/reporting/status-badge";
import { errorMessage } from "@/lib/api-client";
import { cn } from "@/lib/utils";

import { directionsUrl } from "./api";
import { useQueue } from "./hooks";
import type { QueueFilters } from "./types";

const ACTIVE_WORK: QueueFilters = { statuses: ["ASSIGNED", "IN_PROGRESS"], assignedToMe: true, sort: "oldest" };

/** A phone-first list of the jobs assigned to this officer, oldest first. */
export function MyWorkView({ councilId }: { councilId: string }) {
  return (
    <CouncilShell councilId={councilId} tab="work">
      {() => <MyWork councilId={councilId} />}
    </CouncilShell>
  );
}

function MyWork({ councilId }: { councilId: string }) {
  const { data, isPending, isError, error, refetch } = useQueue(councilId, ACTIVE_WORK, 1);
  if (isPending) return <LoadingRows label="Loading your work" rows={3} />;
  if (isError) return <LoadError message={errorMessage(error)} onRetry={() => void refetch()} />;
  if (data.items.length === 0) {
    return <EmptyState title="Nothing assigned to you">New work assigned to you will appear here.</EmptyState>;
  }
  return (
    <div className="space-y-3">
      <p className="text-sm text-slate">
        <span className="tabular">{data.total}</span> active job{data.total === 1 ? "" : "s"}, oldest first.
      </p>
      <ul className="space-y-3">
        {data.items.map((issue) => (
          <li key={issue.id} className="rounded-[var(--radius-panel)] border border-line bg-surface p-4">
            <div className="flex flex-wrap items-center gap-2">
              <StatusBadge status={issue.status} />
              <span className="text-xs text-slate tabular">{issue.reference}</span>
            </div>
            <p className="mt-2 font-semibold break-words">{issue.title}</p>
            <p className="mt-1 flex items-start gap-1.5 text-sm text-navy-soft">
              <MapPin aria-hidden="true" className="mt-0.5 size-4 shrink-0 text-teal" />
              {issue.location_description ?? `${issue.latitude.toFixed(5)}, ${issue.longitude.toFixed(5)}`}
            </p>
            <p className="mt-1 text-xs text-slate">
              {issue.category.name} · reported {formatDate(issue.created_at)}
            </p>
            <div className="mt-3 grid grid-cols-2 gap-2">
              <a
                href={directionsUrl(issue.latitude, issue.longitude)}
                target="_blank"
                rel="noopener noreferrer"
                className={cn(buttonVariants({ variant: "secondary" }))}
                aria-label={`Directions to ${issue.reference}`}
              >
                <Navigation aria-hidden="true" />
                Directions
              </a>
              <Link href={`/council/${councilId}/reports/${issue.id}`} className={cn(buttonVariants())} aria-label={`Open ${issue.reference}`}>
                Open
              </Link>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
