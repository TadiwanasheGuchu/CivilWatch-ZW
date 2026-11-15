"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useId, useState } from "react";

import { Panel } from "@/components/ui/panel";
import { EmptyState, LoadError, LoadingRows } from "@/components/ui/page-states";
import { Select } from "@/components/ui/select";
import { CouncilShell } from "@/features/council/council-shell";
import { errorMessage } from "@/lib/api-client";

import { analyticsKeys, fetchPerformance } from "./api";
import { ExportPanel } from "./export-panel";
import { formatHours, percent } from "./format";
import { CountBar, StatTile } from "./stat-tile";
import type { PeriodDays, Performance } from "./types";

const PERIODS: Array<{ days: PeriodDays; label: string }> = [
  { days: 30, label: "Last 30 days" },
  { days: 90, label: "Last 90 days" },
  { days: 365, label: "Last 12 months" },
];

export function PerformanceView({ councilId }: { councilId: string }) {
  return (
    <CouncilShell councilId={councilId} tab="performance">
      {(workspace) =>
        workspace.permissions.includes("analytics.view") ? (
          <div className="space-y-6">
            <Figures councilId={councilId} />
            {workspace.permissions.includes("reports.export") ? <ExportPanel councilId={councilId} /> : null}
          </div>
        ) : (
          <EmptyState title="Performance figures are for council staff">
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

function Figures({ councilId }: { councilId: string }) {
  const periodId = useId();
  const [days, setDays] = useState<PeriodDays>(90);
  const { data, isPending, isError, error, refetch, isFetching } = useQuery({
    queryKey: analyticsKeys.performance(councilId, days),
    queryFn: ({ signal }) => fetchPerformance(councilId, days, signal),
    placeholderData: keepPreviousData,
  });

  return (
    <section aria-labelledby="performance-heading" className="space-y-4" aria-busy={isFetching}>
      <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h2 id="performance-heading" className="text-lg font-semibold">
            Performance
          </h2>
          <p className="text-sm text-slate">Reports received in the period, and the work open today.</p>
        </div>
        <div className="sm:w-48">
          <label htmlFor={periodId} className="sr-only">
            Period
          </label>
          <Select id={periodId} value={days} onChange={(e) => setDays(Number(e.target.value) as PeriodDays)}>
            {PERIODS.map((p) => (
              <option key={p.days} value={p.days}>
                {p.label}
              </option>
            ))}
          </Select>
        </div>
      </div>
      {isPending ? (
        <LoadingRows label="Loading performance figures" rows={4} />
      ) : isError ? (
        <LoadError message={errorMessage(error)} onRetry={() => void refetch()} />
      ) : (
        <Details data={data} councilId={councilId} />
      )}
    </section>
  );
}

function Details({ data, councilId }: { data: Performance; councilId: string }) {
  const maxCategory = Math.max(0, ...data.categories.map((c) => c.received));
  const maxDepartment = Math.max(0, ...data.departments.map((d) => d.assigned + d.in_progress));
  const fixedShare = percent(data.feedback_fixed, data.feedback_responses);

  return (
    <div className="space-y-5">
      <dl className="grid grid-cols-2 gap-2 lg:grid-cols-5">
        <StatTile label="Received" value={data.received} hint="in the period" />
        <StatTile label="Fixed" value={data.fixed_in_period} hint="resolved in the period" />
        <StatTile label="Open now" value={data.open_now} hint="not yet resolved" />
        <StatTile label="Waiting for review" value={data.awaiting_review} />
        <StatTile label="Waiting for a team" value={data.awaiting_assignment} hint="verified, not assigned" />
      </dl>

      <div className="grid gap-5 lg:grid-cols-2">
        <Panel title="Typical times" description="Median from the report being received, for reports received in the period.">
          <dl className="divide-y divide-line">
            {[
              ["First response", data.median_hours_to_first_response],
              ["Verified", data.median_hours_to_verify],
              ["Fixed", data.median_hours_to_fix],
            ].map(([label, hours]) => (
              <div key={label as string} className="flex items-baseline justify-between gap-3 py-2 text-sm">
                <dt className="font-medium">{label}</dt>
                <dd className="tabular text-navy-soft">{formatHours(hours as number | null)}</dd>
              </div>
            ))}
          </dl>
        </Panel>

        <Panel title="Residents' answers" description='"Was it fixed?" answers given in the period.'>
          {data.feedback_responses === 0 ? (
            <p className="text-sm text-slate">No answers yet.</p>
          ) : (
            <p className="text-sm">
              <span className="font-heading text-2xl font-bold tabular">{fixedShare}%</span>{" "}
              <span className="text-navy-soft">
                said it was fixed (<span className="tabular">{data.feedback_fixed}</span> of{" "}
                <span className="tabular">{data.feedback_responses}</span>).
              </span>
            </p>
          )}
        </Panel>

        <Panel title="By category" description="Reports received in the period, and how many are fixed.">
          {data.categories.length === 0 ? (
            <p className="text-sm text-slate">No reports in this period.</p>
          ) : (
            <ul>
              {data.categories.map((c) => (
                <CountBar key={c.code} label={c.name} value={c.received} max={maxCategory} detail={`${c.fixed} fixed`} />
              ))}
            </ul>
          )}
        </Panel>

        <Panel title="Department workload" description="Work assigned to each department today.">
          {data.departments.length === 0 ? (
            <p className="text-sm text-slate">
              No departments yet.{" "}
              <Link href={`/council/${councilId}/departments`} className="font-medium text-teal underline">
                Set them up
              </Link>
              .
            </p>
          ) : (
            <ul>
              {data.departments.map((d) => (
                <CountBar
                  key={d.id}
                  label={d.name}
                  value={d.assigned + d.in_progress}
                  max={maxDepartment}
                  detail={
                    d.oldest_open_days === null
                      ? "nothing open"
                      : `${d.in_progress} started · oldest ${d.oldest_open_days} day${d.oldest_open_days === 1 ? "" : "s"}`
                  }
                />
              ))}
            </ul>
          )}
        </Panel>
      </div>
    </div>
  );
}
