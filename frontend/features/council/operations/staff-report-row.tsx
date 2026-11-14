import { ChevronRight, ImageOff, Lock } from "lucide-react";
import Link from "next/link";

import { formatDate } from "@/features/reporting/labels";
import { StatusBadge } from "@/features/reporting/status-badge";

import type { StaffIssueSummary } from "./types";

export function StaffReportRow({ councilId, issue }: { councilId: string; issue: StaffIssueSummary }) {
  return (
    <li>
      <Link href={`/council/${councilId}/reports/${issue.id}`} className="flex gap-3 px-4 py-3 hover:bg-mist sm:px-5">
        <span className="grid size-14 shrink-0 place-items-center overflow-hidden rounded-md bg-mist">
          {issue.cover_thumbnail_url ? (
            // Signed, expiring storage URL.
            // eslint-disable-next-line @next/next/no-img-element
            <img src={issue.cover_thumbnail_url} alt="" loading="lazy" className="size-full object-cover" />
          ) : (
            <ImageOff aria-hidden="true" className="size-5 text-slate" />
          )}
        </span>
        <span className="min-w-0 flex-1">
          <span className="flex flex-wrap items-center gap-2">
            <StatusBadge status={issue.status} />
            {issue.visibility === "PRIVATE" ? (
              <span className="inline-flex items-center gap-1 text-xs text-slate">
                <Lock aria-hidden="true" className="size-3" /> Private
              </span>
            ) : null}
            <span className="text-xs text-slate tabular">{issue.reference}</span>
          </span>
          <span className="mt-1 block font-medium break-words">{issue.title}</span>
          <span className="mt-0.5 block text-sm text-slate">
            {issue.category.name}
            {issue.location_description ? ` · ${issue.location_description}` : ""}
          </span>
          <span className="mt-0.5 block text-xs text-slate">
            Reported {formatDate(issue.created_at)}
            {issue.assignment
              ? ` · ${issue.assignment.department.name}${issue.assignment.assignee ? `, ${issue.assignment.assignee.full_name}` : ""}`
              : ""}
          </span>
        </span>
        <ChevronRight aria-hidden="true" className="mt-5 size-5 shrink-0 text-slate" />
      </Link>
    </li>
  );
}
