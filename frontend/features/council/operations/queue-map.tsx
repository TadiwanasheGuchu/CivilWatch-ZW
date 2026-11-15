"use client";

import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useCallback, useMemo } from "react";

import { type BBox, boundaryBBox, fetchBoundaries, fetchCouncilClusters } from "@/features/maps/api";
import { LazyClusterMap } from "@/features/maps/lazy-cluster-map";

import type { QueueFilters } from "./types";

/** The council's reports on a map (all visibilities), framed to its boundary. */
export function QueueMap({ councilId, filters }: { councilId: string; filters: QueueFilters }) {
  const router = useRouter();
  const boundaries = useQuery({ queryKey: ["maps", "boundaries"], queryFn: ({ signal }) => fetchBoundaries(signal), staleTime: 5 * 60_000 });
  const fitTo = useMemo<BBox | null>(() => {
    const feature = boundaries.data?.features.find((f) => f.properties.id === councilId);
    return feature ? boundaryBBox(feature) : null;
  }, [boundaries.data, councilId]);
  const fetchClusters = useCallback(
    (bbox: BBox, zoom: number, signal: AbortSignal) =>
      fetchCouncilClusters(councilId, bbox, zoom, { category: filters.category, statuses: filters.statuses }, signal),
    [councilId, filters.category, filters.statuses],
  );
  return (
    <LazyClusterMap
      fetchClusters={fetchClusters}
      dataKey={JSON.stringify([filters.category, filters.statuses])}
      onSelectIssue={(id) => router.push(`/council/${councilId}/reports/${id}`)}
      fitTo={fitTo}
      label="Map of this council's reports"
    />
  );
}
