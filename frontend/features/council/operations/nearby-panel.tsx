"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";

import { fetchStaffNearby, formatDistance } from "@/features/maps/api";
import { StatusBadge } from "@/features/reporting/status-badge";

/** Other reports within 200 m in this council: candidates when marking duplicates. */
export function NearbyPanel({ councilId, issueId }: { councilId: string; issueId: string }) {
  const { data } = useQuery({
    queryKey: ["council", councilId, "ops", "nearby", issueId],
    queryFn: ({ signal }) => fetchStaffNearby(councilId, issueId, signal),
    staleTime: 60_000,
  });
  if (!data || data.length === 0) return null;
  return (
    <section aria-labelledby="nearby-heading" className="space-y-2 rounded-[var(--radius-panel)] border border-line bg-surface p-4">
      <h2 id="nearby-heading" className="text-base font-semibold">
        Possible duplicates nearby
      </h2>
      <p className="text-sm text-slate">Reports within 200 m. To mark this one as a duplicate, use the original&apos;s reference.</p>
      <ul className="divide-y divide-line">
        {data.map((issue) => (
          <li key={issue.id} className="py-2">
            <Link href={`/council/${councilId}/reports/${issue.id}`} className="block min-h-11 hover:underline">
              <span className="flex flex-wrap items-center gap-2">
                <span className="font-medium tabular">{issue.reference}</span>
                <StatusBadge status={issue.status} />
              </span>
              <span className="block text-sm break-words">{issue.title}</span>
              <span className="block text-xs text-slate">
                {issue.category.name} · {formatDistance(issue.distance_m)}
              </span>
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}
