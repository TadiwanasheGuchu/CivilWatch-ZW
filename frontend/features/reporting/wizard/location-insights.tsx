"use client";

import { useQuery } from "@tanstack/react-query";
import { ExternalLink } from "lucide-react";
import { useEffect } from "react";

import { Alert } from "@/components/ui/alert";
import { fetchNearby, formatDistance, locateCouncils } from "@/features/maps/api";
import { useOnline } from "@/hooks/use-online";

import type { ReportDraft } from "../draft";
import { useCategories, useCouncilOptions } from "../hooks";

const SIMILAR_RADIUS_M = 150;

/**
 * Uses the pin to (1) choose the council whose boundary covers it and
 * (2) show verified reports of the same kind close by, so people can check
 * before reporting something twice. Both are optional helpers: offline,
 * or without boundaries, the person simply chooses the council themselves.
 */
export function LocationInsights({
  draft,
  update,
}: {
  draft: ReportDraft;
  update: (patch: Partial<ReportDraft>) => void;
}) {
  const online = useOnline();
  const councils = useCouncilOptions();
  const categories = useCategories();
  const hasPin = draft.latitude !== null && draft.longitude !== null;
  const lat = draft.latitude ?? 0;
  const lon = draft.longitude ?? 0;
  const categoryCode = categories.data?.find((c) => c.id === draft.categoryId)?.code;

  const located = useQuery({
    queryKey: ["maps", "locate", lat.toFixed(5), lon.toFixed(5)],
    queryFn: ({ signal }) => locateCouncils(lat, lon, signal),
    enabled: hasPin && online,
    staleTime: 10 * 60_000,
  });
  const similar = useQuery({
    queryKey: ["maps", "similar", lat.toFixed(4), lon.toFixed(4), categoryCode],
    queryFn: ({ signal }) => fetchNearby(lat, lon, { radiusM: SIMILAR_RADIUS_M, category: categoryCode, limit: 3 }, signal),
    enabled: hasPin && online && Boolean(categoryCode),
    staleTime: 5 * 60_000,
  });

  const best = located.data?.[0];
  // Choose the council from the pin unless the person picked one themselves.
  useEffect(() => {
    if (!best) return;
    const mayAutoSelect = draft.councilId === null || draft.councilAutoSelected;
    if (mayAutoSelect && draft.councilId !== best.id) {
      update({ councilId: best.id, councilAutoSelected: true });
    }
  }, [best, draft.councilId, draft.councilAutoSelected, update]);

  if (!hasPin || !online) return null;
  const chosenName = councils.data?.find((c) => c.id === draft.councilId)?.name;

  return (
    <div className="space-y-3">
      {located.isSuccess && best && draft.councilId === best.id ? (
        <p role="status" className="text-sm text-navy-soft">
          Council chosen from your pin: <span className="font-medium">{best.name}</span>
          {best.is_sample_boundary ? " (based on a sample boundary; check it is right)" : ""}.
        </p>
      ) : null}
      {located.isSuccess && best && draft.councilId && draft.councilId !== best.id ? (
        <Alert tone="info">
          Your pin is inside {best.name}&apos;s area{best.is_sample_boundary ? " (sample boundary)" : ""}, but you chose{" "}
          {chosenName ?? "another council"}. If that council has a boundary, the report may be refused.
        </Alert>
      ) : null}
      {located.isSuccess && located.data.length === 0 ? (
        <p role="status" className="text-sm text-slate">
          No council boundary covers this spot yet. Choose the council responsible above.
        </p>
      ) : null}

      {similar.data && similar.data.length > 0 ? (
        <Alert tone="info" title="Already reported nearby?">
          <p>
            Verified reports of the same kind within {SIMILAR_RADIUS_M} m. If yours is the same problem, you can follow
            that report instead. You can still send yours.
          </p>
          <ul className="mt-2 space-y-1">
            {similar.data.map((issue) => (
              <li key={issue.id}>
                <a
                  href={`/reports/${issue.id}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex min-h-11 flex-col justify-center py-1"
                >
                  <span className="inline-flex items-center gap-1 font-medium break-words text-teal underline underline-offset-2">
                    {issue.title}
                    <ExternalLink aria-hidden="true" className="size-3.5 shrink-0" />
                  </span>
                  <span className="text-xs text-slate">{formatDistance(issue.distance_m)}</span>
                  <span className="sr-only">(opens in a new tab)</span>
                </a>
              </li>
            ))}
          </ul>
        </Alert>
      ) : null}
    </div>
  );
}
