import { ChevronRight, ImageOff, Lock } from "lucide-react";
import Link from "next/link";

import { formatDate } from "./labels";
import { StatusBadge } from "./status-badge";
import type { OwnIssue, PublicIssue } from "./types";

/** One report in a list. Thumbnails are signed, short-lived URLs from the API. */
export function ReportListItem({ issue }: { issue: PublicIssue | OwnIssue }) {
  const isPrivate = "visibility" in issue && issue.visibility === "PRIVATE";
  return (
    <li>
      <Link href={`/reports/${issue.id}`} className="flex gap-3 px-4 py-3 hover:bg-mist sm:px-5">
        <span className="grid size-16 shrink-0 place-items-center overflow-hidden rounded-md bg-mist">
          {issue.cover_thumbnail_url ? (
            // Signed, expiring storage URLs: next/image optimisation would cache them.
            // eslint-disable-next-line @next/next/no-img-element
            <img src={issue.cover_thumbnail_url} alt="" loading="lazy" className="size-full object-cover" />
          ) : (
            <ImageOff aria-hidden="true" className="size-5 text-slate" />
          )}
        </span>
        <span className="min-w-0 flex-1">
          <span className="flex flex-wrap items-center gap-2">
            <StatusBadge status={issue.status} />
            {isPrivate ? (
              <span className="inline-flex items-center gap-1 text-xs text-slate">
                <Lock aria-hidden="true" className="size-3" /> Private
              </span>
            ) : null}
          </span>
          <span className="mt-1 block font-medium break-words">{issue.title}</span>
          <span className="mt-0.5 block text-sm text-slate">
            {issue.category.name} · {issue.council.name}
          </span>
          <span className="mt-0.5 block text-xs text-slate tabular">
            {issue.reference} · {formatDate(issue.created_at)}
          </span>
        </span>
        <ChevronRight aria-hidden="true" className="mt-6 size-5 shrink-0 text-slate" />
      </Link>
    </li>
  );
}
