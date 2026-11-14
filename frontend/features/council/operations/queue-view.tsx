"use client";

import { Search } from "lucide-react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useId, useMemo, useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { EmptyState, LoadError, LoadingRows } from "@/components/ui/page-states";
import { Pagination } from "@/components/ui/pagination";
import { Select } from "@/components/ui/select";
import { CouncilShell } from "@/features/council/council-shell";
import { useCategories } from "@/features/reporting/hooks";
import type { IssueStatus } from "@/features/reporting/types";
import { errorMessage } from "@/lib/api-client";

import { QUEUE_PAGE_SIZE } from "./api";
import { useDepartments, useQueue } from "./hooks";
import { StaffReportRow } from "./staff-report-row";
import { groupForStatuses, OPEN_STATUSES, STATUS_GROUPS } from "./status-groups";
import type { QueueFilters } from "./types";

const VALID = new Set<string>(STATUS_GROUPS.flatMap((g) => g.statuses));

function filtersFrom(params: URLSearchParams): QueueFilters & { page: number } {
  const statuses = (params.get("status") ?? "")
    .split(",")
    .filter((s): s is IssueStatus => VALID.has(s));
  return {
    statuses,
    category: params.get("category") ?? undefined,
    departmentId: params.get("department") ?? undefined,
    q: params.get("q") ?? undefined,
    sort: params.get("sort") === "oldest" ? "oldest" : "newest",
    page: Math.max(1, Number(params.get("page")) || 1),
  };
}

export function QueueView({ councilId }: { councilId: string }) {
  return (
    <CouncilShell councilId={councilId} tab="reports">
      {() => <Queue councilId={councilId} />}
    </CouncilShell>
  );
}

function Queue({ councilId }: { councilId: string }) {
  const params = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const { page, ...filters } = useMemo(() => filtersFrom(new URLSearchParams(params.toString())), [params]);
  const [search, setSearch] = useState(filters.q ?? "");
  const ids = { status: useId(), category: useId(), department: useId(), sort: useId(), search: useId() };
  const categories = useCategories();
  const departments = useDepartments(councilId);
  const { data, isPending, isError, error, refetch } = useQueue(councilId, filters, page);

  function update(patch: Record<string, string | undefined>) {
    const next = new URLSearchParams(params.toString());
    for (const [key, value] of Object.entries(patch)) {
      if (value) next.set(key, value);
      else next.delete(key);
    }
    if (!("page" in patch)) next.delete("page");
    router.replace(`${pathname}?${next.toString()}`, { scroll: false });
  }

  const groupValue =
    filters.statuses.length === 0
      ? ""
      : filters.statuses.join(",") === OPEN_STATUSES.join(",")
        ? "open"
        : (groupForStatuses(filters.statuses)?.statuses.join(",") ?? filters.statuses.join(","));

  return (
    <div className="space-y-4">
      <form
        role="search"
        onSubmit={(event: FormEvent) => {
          event.preventDefault();
          update({ q: search.trim() || undefined });
        }}
        className="flex gap-2"
      >
        <label htmlFor={ids.search} className="sr-only">
          Search reports by title or reference
        </label>
        <Input
          id={ids.search}
          type="search"
          placeholder="Title or reference"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
        />
        <Button type="submit" variant="secondary" aria-label="Search">
          <Search aria-hidden="true" />
        </Button>
      </form>

      <div className="grid grid-cols-2 gap-2 lg:grid-cols-4">
        <div>
          <label htmlFor={ids.status} className="mb-1 block text-sm font-medium">Stage</label>
          <Select
            id={ids.status}
            value={groupValue}
            onChange={(event) =>
              update({ status: event.target.value === "open" ? OPEN_STATUSES.join(",") : event.target.value || undefined })
            }
          >
            <option value="">All stages</option>
            <option value="open">All open</option>
            {STATUS_GROUPS.map((group) => (
              <option key={group.id} value={group.statuses.join(",")}>
                {group.label}
              </option>
            ))}
          </Select>
        </div>
        <div>
          <label htmlFor={ids.category} className="mb-1 block text-sm font-medium">Problem</label>
          <Select id={ids.category} value={filters.category ?? ""} onChange={(e) => update({ category: e.target.value || undefined })}>
            <option value="">All</option>
            {(categories.data ?? []).map((c) => (
              <option key={c.code} value={c.code}>{c.name}</option>
            ))}
          </Select>
        </div>
        <div>
          <label htmlFor={ids.department} className="mb-1 block text-sm font-medium">Department</label>
          <Select id={ids.department} value={filters.departmentId ?? ""} onChange={(e) => update({ department: e.target.value || undefined })}>
            <option value="">All</option>
            {(departments.data ?? []).map((d) => (
              <option key={d.id} value={d.id}>{d.name}</option>
            ))}
          </Select>
        </div>
        <div>
          <label htmlFor={ids.sort} className="mb-1 block text-sm font-medium">Order</label>
          <Select id={ids.sort} value={filters.sort} onChange={(e) => update({ sort: e.target.value === "oldest" ? "oldest" : undefined })}>
            <option value="newest">Newest</option>
            <option value="oldest">Oldest</option>
          </Select>
        </div>
      </div>

      {isPending ? (
        <LoadingRows label="Loading reports" rows={5} />
      ) : isError ? (
        <LoadError message={errorMessage(error)} onRetry={() => void refetch()} />
      ) : data.items.length === 0 ? (
        <EmptyState title="No reports match">Try another stage or clear the search.</EmptyState>
      ) : (
        <>
          <p className="text-sm text-slate" aria-live="polite">
            <span className="tabular">{data.total}</span> report{data.total === 1 ? "" : "s"}
          </p>
          <ul className="divide-y divide-line overflow-hidden rounded-[var(--radius-panel)] border border-line bg-surface">
            {data.items.map((issue) => (
              <StaffReportRow key={issue.id} councilId={councilId} issue={issue} />
            ))}
          </ul>
          <Pagination
            page={page}
            pageSize={QUEUE_PAGE_SIZE}
            total={data.total}
            onPageChange={(next) => update({ page: String(next) })}
            label="Report pages"
          />
        </>
      )}
    </div>
  );
}
