"use client";

import Link from "next/link";
import { useState } from "react";

import { buttonVariants } from "@/components/ui/button";
import { EmptyState, LoadError, LoadingRows } from "@/components/ui/page-states";
import { Pagination } from "@/components/ui/pagination";
import { RequireSession } from "@/features/authentication/require-session";
import { errorMessage } from "@/lib/api-client";

import { PAGE_SIZE } from "./api";
import { useMyReports } from "./hooks";
import { ReportListItem } from "./report-list-item";

export function MyReportsView() {
  return <RequireSession>{() => <MyReportsList />}</RequireSession>;
}

function MyReportsList() {
  const [page, setPage] = useState(1);
  const { data, isPending, isError, error, refetch } = useMyReports(page);

  return (
    <div className="space-y-4">
      <div className="flex items-end justify-between gap-3">
        <h1 className="text-2xl font-bold">My reports</h1>
        <Link href="/report" className={buttonVariants({ size: "md" })}>
          New report
        </Link>
      </div>
      {isPending ? (
        <LoadingRows label="Loading your reports" rows={4} />
      ) : isError ? (
        <LoadError message={errorMessage(error)} onRetry={() => void refetch()} />
      ) : data.items.length === 0 ? (
        <EmptyState title="You have not reported anything yet">
          When you report a problem, you can follow it here until it is fixed.
        </EmptyState>
      ) : (
        <>
          <ul className="divide-y divide-line overflow-hidden rounded-[var(--radius-panel)] border border-line bg-surface">
            {data.items.map((issue) => (
              <ReportListItem key={issue.id} issue={issue} />
            ))}
          </ul>
          <Pagination page={page} pageSize={PAGE_SIZE} total={data.total} onPageChange={setPage} label="Report pages" />
        </>
      )}
    </div>
  );
}
