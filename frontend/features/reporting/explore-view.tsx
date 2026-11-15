"use client";

import { List, LocateFixed, Map as MapIcon } from "lucide-react";
import { useCallback, useId, useMemo, useState } from "react";

import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { EmptyState, LoadError, LoadingRows } from "@/components/ui/page-states";
import { Pagination } from "@/components/ui/pagination";
import { Select } from "@/components/ui/select";
import {
  type BBox,
  boundaryBBox,
  fetchBoundaries,
  fetchNearby,
  fetchPublicClusters,
  formatDistance,
} from "@/features/maps/api";
import { LazyClusterMap } from "@/features/maps/lazy-cluster-map";
import { errorMessage } from "@/lib/api-client";
import { cn } from "@/lib/utils";
import { useQuery } from "@tanstack/react-query";

import { type ExploreFilters, PAGE_SIZE } from "./api";
import { useCategories, useCouncilOptions, usePublishedReports } from "./hooks";
import { PUBLISHED_STATUSES, STATUS_LABELS } from "./labels";
import { MapPreview } from "./map-preview";
import { useNearMe } from "./near-me";
import { ReportListItem } from "./report-list-item";
import type { IssueStatus } from "./types";

function FilterSelect({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: Array<{ value: string; label: string }>;
}) {
  const id = useId();
  return (
    <div>
      <label htmlFor={id} className="mb-1.5 block text-sm font-medium">
        {label}
      </label>
      <Select id={id} value={value} onChange={(event) => onChange(event.target.value)}>
        <option value="">All</option>
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </Select>
    </div>
  );
}

type View = "list" | "map";

/** Verified public reports, as a list or a map, with "near me". */
export function ExploreView() {
  const [filters, setFilters] = useState<ExploreFilters>({});
  const [page, setPage] = useState(1);
  const [view, setView] = useState<View>("list");
  const [selected, setSelected] = useState<string | null>(null);
  const nearMe = useNearMe();
  const councils = useCouncilOptions();
  const categories = useCategories();

  const setFilter = (patch: ExploreFilters) => {
    setFilters((current) => ({ ...current, ...patch }));
    setPage(1);
  };
  const here = nearMe.state.kind === "found" ? nearMe.state : null;

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-bold">Explore reports</h1>
        <p className="mt-1 text-base text-navy-soft">
          Public reports that councils have verified. Reporters are never named.
        </p>
      </div>
      <div className="grid gap-3 sm:grid-cols-3">
        <FilterSelect
          label="Council"
          value={filters.councilId ?? ""}
          onChange={(value) => setFilter({ councilId: value || undefined })}
          options={(councils.data ?? []).map((c) => ({ value: c.id, label: c.name }))}
        />
        <FilterSelect
          label="Problem"
          value={filters.category ?? ""}
          onChange={(value) => setFilter({ category: value || undefined })}
          options={(categories.data ?? []).map((c) => ({ value: c.code, label: c.name }))}
        />
        <FilterSelect
          label="Status"
          value={filters.status ?? ""}
          onChange={(value) => setFilter({ status: (value || undefined) as IssueStatus | undefined })}
          options={PUBLISHED_STATUSES.map((s) => ({ value: s, label: STATUS_LABELS[s] }))}
        />
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <div role="group" aria-label="Show reports as" className="inline-flex rounded-[var(--radius-control)] border border-line bg-surface p-0.5">
          {(
            [
              ["list", "List", List],
              ["map", "Map", MapIcon],
            ] as const
          ).map(([id, text, Icon]) => (
            <button
              key={id}
              type="button"
              aria-pressed={view === id}
              onClick={() => setView(id)}
              className={cn(
                "inline-flex min-h-10 items-center gap-1.5 rounded-[calc(var(--radius-control)-2px)] px-3 text-sm font-medium",
                view === id ? "bg-navy text-white" : "text-navy hover:bg-mist",
              )}
            >
              <Icon aria-hidden="true" className="size-4" />
              {text}
            </button>
          ))}
        </div>
        <Button variant="secondary" onClick={nearMe.locate} disabled={nearMe.state.kind === "locating"}>
          <LocateFixed aria-hidden="true" />
          {nearMe.state.kind === "locating" ? "Finding you…" : "Near me"}
        </Button>
        {here ? (
          <Button variant="ghost" onClick={nearMe.reset}>
            Show all
          </Button>
        ) : null}
      </div>
      {nearMe.state.kind === "error" ? <Alert tone="error">{nearMe.state.message}</Alert> : null}

      {view === "map" ? (
        <MapView filters={filters} here={here} selected={selected} onSelect={setSelected} />
      ) : here ? (
        <NearbyList latitude={here.latitude} longitude={here.longitude} category={filters.category} />
      ) : (
        <ReportList filters={filters} page={page} onPageChange={setPage} />
      )}
    </div>
  );
}

function MapView({
  filters,
  here,
  selected,
  onSelect,
}: {
  filters: ExploreFilters;
  here: { latitude: number; longitude: number } | null;
  selected: string | null;
  onSelect: (id: string | null) => void;
}) {
  const fetchClusters = useCallback(
    (bbox: BBox, zoom: number, signal: AbortSignal) =>
      fetchPublicClusters(
        bbox,
        zoom,
        { councilId: filters.councilId, category: filters.category, statuses: filters.status ? [filters.status] : undefined },
        signal,
      ),
    [filters],
  );
  const focus = useMemo(() => (here ? { latitude: here.latitude, longitude: here.longitude, zoom: 15 } : null), [here]);
  // Frame the chosen council's area, when it has a boundary.
  const boundaries = useQuery({ queryKey: ["maps", "boundaries"], queryFn: ({ signal }) => fetchBoundaries(signal), staleTime: 5 * 60_000 });
  const fitTo = useMemo<BBox | null>(() => {
    const feature = boundaries.data?.features.find((f) => f.properties.id === filters.councilId);
    return feature ? boundaryBBox(feature) : null;
  }, [boundaries.data, filters.councilId]);
  return (
    <div className="space-y-3">
      <LazyClusterMap
        fetchClusters={fetchClusters}
        dataKey={JSON.stringify(filters)}
        onSelectIssue={onSelect}
        focus={focus}
        fitTo={fitTo}
        label="Map of verified public reports"
      />
      {selected ? <MapPreview issueId={selected} onClose={() => onSelect(null)} /> : null}
    </div>
  );
}

function NearbyList({ latitude, longitude, category }: { latitude: number; longitude: number; category?: string }) {
  const { data, isPending, isError, error, refetch } = useQuery({
    queryKey: ["reporting", "nearby", latitude.toFixed(4), longitude.toFixed(4), category],
    queryFn: ({ signal }) => fetchNearby(latitude, longitude, { radiusM: 2000, category }, signal),
  });
  if (isPending) return <LoadingRows label="Finding reports near you" rows={3} />;
  if (isError) return <LoadError message={errorMessage(error)} onRetry={() => void refetch()} />;
  if (data.length === 0) {
    return <EmptyState title="No verified reports within 2 km">Try the map to look further away.</EmptyState>;
  }
  return (
    <div className="space-y-2">
      <p className="text-sm text-slate">Verified reports within 2 km of you, closest first.</p>
      <ul className="divide-y divide-line overflow-hidden rounded-[var(--radius-panel)] border border-line bg-surface">
        {data.map((issue) => (
          <ReportListItem key={issue.id} issue={issue} detail={formatDistance(issue.distance_m)} />
        ))}
      </ul>
    </div>
  );
}

function ReportList({ filters, page, onPageChange }: { filters: ExploreFilters; page: number; onPageChange: (page: number) => void }) {
  const { data, isPending, isError, error, refetch } = usePublishedReports(filters, page);
  if (isPending) return <LoadingRows label="Loading reports" rows={4} />;
  if (isError) return <LoadError message={errorMessage(error)} onRetry={() => void refetch()} />;
  if (data.items.length === 0) {
    return (
      <EmptyState title="No reports match">
        {Object.values(filters).some(Boolean) ? "Try removing a filter." : "Verified public reports will appear here."}
      </EmptyState>
    );
  }
  return (
    <>
      <p className="text-sm text-slate" aria-live="polite">
        {data.total} report{data.total === 1 ? "" : "s"}
      </p>
      <ul className="divide-y divide-line overflow-hidden rounded-[var(--radius-panel)] border border-line bg-surface">
        {data.items.map((issue) => (
          <ReportListItem key={issue.id} issue={issue} />
        ))}
      </ul>
      <Pagination page={page} pageSize={PAGE_SIZE} total={data.total} onPageChange={onPageChange} label="Report pages" />
    </>
  );
}
