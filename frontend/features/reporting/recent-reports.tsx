"use client";

import Link from "next/link";

import { EmptyState, LoadingRows } from "@/components/ui/page-states";

import { usePublishedReports } from "./hooks";
import { ReportListItem } from "./report-list-item";

const NO_FILTERS = {};

/** The latest verified public reports, for the home page. */
export function RecentReports() {
  const { data, isPending, isError } = usePublishedReports(NO_FILTERS, 1);
  return (
    <section aria-labelledby="recent-heading">
      <div className="flex items-end justify-between gap-3">
        <h2 id="recent-heading" className="text-lg font-semibold">
          Recently verified
        </h2>
        <Link href="/explore" className="inline-flex min-h-11 items-center text-sm font-medium text-teal underline underline-offset-2">
          See all
        </Link>
      </div>
      <div className="mt-2">
        {isPending ? (
          <LoadingRows label="Loading recent reports" rows={2} />
        ) : isError || data.items.length === 0 ? (
          <EmptyState title="No verified reports yet">Verified public reports from councils will appear here.</EmptyState>
        ) : (
          <ul className="divide-y divide-line overflow-hidden rounded-[var(--radius-panel)] border border-line bg-surface">
            {data.items.slice(0, 3).map((issue) => (
              <ReportListItem key={issue.id} issue={issue} />
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}
