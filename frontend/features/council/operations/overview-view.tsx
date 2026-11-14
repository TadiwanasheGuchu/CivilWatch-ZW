"use client";

import { ArrowRight, Wrench } from "lucide-react";
import Link from "next/link";

import { EmptyState, LoadError, LoadingRows } from "@/components/ui/page-states";
import { CouncilShell } from "@/features/council/council-shell";
import { errorMessage } from "@/lib/api-client";

import { useQueueSummary } from "./hooks";
import { STATUS_GROUPS } from "./status-groups";

export function OverviewView({ councilId }: { councilId: string }) {
  return (
    <CouncilShell councilId={councilId} tab="overview">
      {(workspace) =>
        workspace.permissions.includes("issues.view") ? (
          <Overview councilId={councilId} canWork={workspace.permissions.includes("issues.work")} />
        ) : (
          <EmptyState title="Reports are for council staff">
            As a platform administrator you can manage this council&apos;s{" "}
            <Link href={`/council/${councilId}/staff`} className="font-medium text-teal underline">
              staff
            </Link>
            .
          </EmptyState>
        )
      }
    </CouncilShell>
  );
}

function Overview({ councilId, canWork }: { councilId: string; canWork: boolean }) {
  const { data, isPending, isError, error, refetch } = useQueueSummary(councilId);
  if (isPending) return <LoadingRows label="Loading report counts" rows={4} />;
  if (isError) return <LoadError message={errorMessage(error)} onRetry={() => void refetch()} />;

  const counts = new Map(data.counts.map((row) => [row.status, row.count]));
  const total = data.counts.reduce((sum, row) => sum + row.count, 0);

  return (
    <div className="space-y-5">
      {canWork ? (
        <Link
          href={`/council/${councilId}/work`}
          className="flex items-center gap-3 rounded-[var(--radius-panel)] border border-line bg-surface p-4 hover:bg-mist"
        >
          <Wrench aria-hidden="true" className="size-5 text-teal" />
          <span className="flex-1">
            <span className="block font-semibold">My work</span>
            <span className="text-sm text-slate">
              <span className="tabular">{data.assigned_to_me}</span> active report
              {data.assigned_to_me === 1 ? "" : "s"} assigned to you
            </span>
          </span>
          <ArrowRight aria-hidden="true" className="size-5 text-slate" />
        </Link>
      ) : null}

      <section aria-labelledby="queue-heading">
        <div className="flex items-end justify-between gap-3">
          <h2 id="queue-heading" className="text-lg font-semibold">
            Reports by stage
          </h2>
          <Link href={`/council/${councilId}/reports`} className="inline-flex min-h-11 items-center text-sm font-medium text-teal underline">
            All <span className="tabular mx-1">{total}</span> reports
          </Link>
        </div>
        <ul className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-3">
          {STATUS_GROUPS.map((group) => {
            const count = group.statuses.reduce((sum, status) => sum + (counts.get(status) ?? 0), 0);
            return (
              <li key={group.id}>
                <Link
                  href={`/council/${councilId}/reports?status=${group.statuses.join(",")}`}
                  className="block h-full rounded-[var(--radius-control)] border border-line bg-surface p-3 hover:border-teal"
                  aria-label={`${group.label}: ${count}`}
                >
                  <span className="block font-heading text-2xl font-bold tabular">{count}</span>
                  <span className="block text-sm font-medium">{group.label}</span>
                  <span className="block text-xs text-slate">{group.hint}</span>
                </Link>
              </li>
            );
          })}
        </ul>
      </section>
    </div>
  );
}
