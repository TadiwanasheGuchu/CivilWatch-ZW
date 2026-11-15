"use client";

import { X } from "lucide-react";
import Link from "next/link";

import { buttonVariants } from "@/components/ui/button";
import { LoadingRows } from "@/components/ui/page-states";
import { errorMessage } from "@/lib/api-client";
import { cn } from "@/lib/utils";

import { useReport } from "./hooks";
import { formatDate } from "./labels";
import { StatusBadge } from "./status-badge";

/** A short summary of the report chosen on the map. */
export function MapPreview({ issueId, onClose }: { issueId: string; onClose: () => void }) {
  const { data: issue, isPending, isError, error } = useReport(issueId);
  return (
    <section aria-label="Selected report" className="relative rounded-[var(--radius-panel)] border border-line bg-surface p-4">
      <button type="button" onClick={onClose} aria-label="Close preview" className="absolute top-2 right-2 grid size-11 place-items-center text-slate hover:text-navy">
        <X aria-hidden="true" className="size-5" />
      </button>
      {isPending ? (
        <LoadingRows label="Loading report" rows={2} />
      ) : isError ? (
        <p className="text-sm text-red-text">{errorMessage(error)}</p>
      ) : (
        <div className="flex gap-3 pr-10">
          {issue.photos[0] ? (
            // Signed, expiring storage URL.
            // eslint-disable-next-line @next/next/no-img-element
            <img src={issue.photos[0].thumbnail_url} alt="" className="size-20 shrink-0 rounded-md object-cover" />
          ) : null}
          <div className="min-w-0 space-y-1">
            <StatusBadge status={issue.status} />
            <h2 className="font-semibold break-words">{issue.title}</h2>
            <p className="text-sm text-slate">
              {issue.category.name} · {issue.council.name} · {formatDate(issue.created_at)}
            </p>
            <Link href={`/reports/${issue.id}`} className={cn(buttonVariants({ variant: "secondary" }), "mt-1")}>
              View report
            </Link>
          </div>
        </div>
      )}
    </section>
  );
}
