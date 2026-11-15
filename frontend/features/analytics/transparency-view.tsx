"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useId, useState } from "react";

import { Panel } from "@/components/ui/panel";
import { EmptyState, LoadError, LoadingRows } from "@/components/ui/page-states";
import { Select } from "@/components/ui/select";
import { errorMessage } from "@/lib/api-client";

import { analyticsKeys, fetchPublicStats } from "./api";
import { formatDays } from "./format";
import { CountBar, StatTile } from "./stat-tile";
import type { PublicStats } from "./types";

export function TransparencyView() {
  const councilSelectId = useId();
  const [councilId, setCouncilId] = useState<string | null>(null);
  // The all-councils figures also supply the list of councils to choose from.
  const all = useQuery({
    queryKey: analyticsKeys.public(null),
    queryFn: ({ signal }) => fetchPublicStats(null, signal),
  });
  const selected = useQuery({
    queryKey: analyticsKeys.public(councilId),
    queryFn: ({ signal }) => fetchPublicStats(councilId, signal),
    enabled: councilId !== null,
    placeholderData: keepPreviousData,
  });
  const query = councilId ? selected : all;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Council progress</h1>
        <p className="mt-1 max-w-prose text-base text-navy-soft">
          How councils are handling reports made in public. These figures count only public reports a council
          has verified — the same reports anyone can <Link href="/explore" className="font-medium text-teal underline underline-offset-2">explore</Link>. Private reports are never included.
        </p>
      </div>

      {all.data && all.data.councils.length > 0 ? (
        <div className="sm:w-80">
          <label htmlFor={councilSelectId} className="block text-sm font-medium text-navy">
            Council
          </label>
          <Select
            id={councilSelectId}
            className="mt-1.5"
            value={councilId ?? ""}
            onChange={(e) => setCouncilId(e.target.value || null)}
          >
            <option value="">All councils</option>
            {all.data.councils.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </Select>
        </div>
      ) : null}

      {query.isPending ? (
        <LoadingRows label="Loading council progress" rows={4} />
      ) : query.isError ? (
        <LoadError message={errorMessage(query.error)} onRetry={() => void query.refetch()} />
      ) : query.data.published === 0 ? (
        <EmptyState title="No verified public reports yet">
          Figures appear here once councils verify reports that residents made public.
        </EmptyState>
      ) : (
        <Figures data={query.data} showCouncils={councilId === null} />
      )}
    </div>
  );
}

function Figures({ data, showCouncils }: { data: PublicStats; showCouncils: boolean }) {
  const maxCategory = Math.max(0, ...data.categories.map((c) => c.received));
  return (
    <div className="space-y-5">
      <dl className="grid grid-cols-2 gap-2 lg:grid-cols-4">
        <StatTile label="Verified reports" value={data.published} />
        <StatTile label="Being worked on" value={data.open} hint="verified, not yet fixed" />
        <StatTile label="Fixed" value={data.fixed} />
        <StatTile label="Typical time to fix" value={formatDays(data.median_days_to_fix)} hint="median, from verification" />
      </dl>

      <div className="grid gap-5 lg:grid-cols-2">
        {showCouncils ? (
          <Panel title="By council">
            <ul className="divide-y divide-line">
              {data.councils.map((c) => (
                <li key={c.id} className="py-3">
                  <p className="font-medium break-words">{c.name}</p>
                  <dl className="mt-1 grid grid-cols-2 gap-x-4 gap-y-0.5 text-sm sm:grid-cols-4">
                    {[
                      ["Verified", c.published],
                      ["Open", c.open],
                      ["Fixed", c.fixed],
                      ["Time to fix", formatDays(c.median_days_to_fix)],
                    ].map(([label, value]) => (
                      <div key={label as string} className="flex gap-1">
                        <dt className="text-slate">{label}:</dt>
                        <dd className="tabular">{value}</dd>
                      </div>
                    ))}
                  </dl>
                </li>
              ))}
            </ul>
          </Panel>
        ) : null}
        <Panel title="By category" description="Verified reports, and how many are fixed.">
          <ul>
            {data.categories.map((c) => (
              <CountBar key={c.code} label={c.name} value={c.received} max={maxCategory} detail={`${c.fixed} fixed`} />
            ))}
          </ul>
        </Panel>
      </div>
    </div>
  );
}
