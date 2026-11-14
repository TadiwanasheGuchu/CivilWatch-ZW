"use client";

import { useId, useState } from "react";

import { EmptyState, LoadError, LoadingRows } from "@/components/ui/page-states";
import { Pagination } from "@/components/ui/pagination";
import { Select } from "@/components/ui/select";
import { errorMessage } from "@/lib/api-client";

import { type ExploreFilters, PAGE_SIZE } from "./api";
import { useCategories, useCouncilOptions, usePublishedReports } from "./hooks";
import { PUBLISHED_STATUSES, STATUS_LABELS } from "./labels";
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

/** Verified public reports, as a list. The map explorer arrives in Milestone 4. */
export function ExploreView() {
  const [filters, setFilters] = useState<ExploreFilters>({});
  const [page, setPage] = useState(1);
  const councils = useCouncilOptions();
  const categories = useCategories();
  const { data, isPending, isError, error, refetch } = usePublishedReports(filters, page);

  const setFilter = (patch: ExploreFilters) => {
    setFilters((current) => ({ ...current, ...patch }));
    setPage(1);
  };

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-bold">Explore reports</h1>
        <p className="mt-1 text-base text-navy-soft">
          Public reports that councils have verified, newest first. Reporters are never named.
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

      {isPending ? (
        <LoadingRows label="Loading reports" rows={4} />
      ) : isError ? (
        <LoadError message={errorMessage(error)} onRetry={() => void refetch()} />
      ) : data.items.length === 0 ? (
        <EmptyState title="No reports match">
          {Object.values(filters).some(Boolean)
            ? "Try removing a filter."
            : "Verified public reports will appear here."}
        </EmptyState>
      ) : (
        <>
          <p className="text-sm text-slate" aria-live="polite">
            {data.total} report{data.total === 1 ? "" : "s"}
          </p>
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
