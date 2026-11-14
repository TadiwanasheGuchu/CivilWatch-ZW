"use client";

import { CircleAlert, CircleCheck, RefreshCw, ServerCrash } from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

import type { ComponentStatus, Readiness } from "./types";
import { useReadiness } from "./use-readiness";

const COMPONENT_LABELS: Record<keyof Omit<Readiness, "status">, string> = {
  database: "Report database",
  postgis: "Mapping engine",
  cache: "Background jobs queue",
  storage: "Photo storage",
};

function StatusRow({ label, status }: { label: string; status: ComponentStatus }) {
  const ok = status === "ok";
  const Icon = ok ? CircleCheck : CircleAlert;
  return (
    <li className="flex min-h-11 items-center justify-between gap-3 border-t border-line py-2 first:border-t-0">
      <span className="text-sm">{label}</span>
      <span
        className={cn(
          "inline-flex items-center gap-1.5 text-sm font-medium",
          ok ? "text-teal" : "text-red-text",
        )}
      >
        <Icon aria-hidden="true" className="size-4" strokeWidth={2} />
        {ok ? "Operational" : "Unavailable"}
      </span>
    </li>
  );
}

export function SystemStatusPanel() {
  const { data, isPending, isError, isFetching, refetch } = useReadiness();

  return (
    <section
      aria-labelledby="system-status-heading"
      aria-busy={isPending || isFetching}
      className="rounded-[var(--radius-panel)] border border-line bg-surface p-4 sm:p-5"
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 id="system-status-heading" className="text-base font-semibold">
            Platform status
          </h2>
          <p className="mt-0.5 text-sm text-slate">Live check of the CivicWatch services.</p>
        </div>
        <Button
          variant="secondary"
          onClick={() => void refetch()}
          disabled={isFetching}
          aria-label="Check platform status again"
        >
          <RefreshCw aria-hidden="true" className={cn(isFetching && "animate-spin")} />
          <span className="hidden sm:inline">Check again</span>
        </Button>
      </div>

      <div className="mt-4" aria-live="polite">
        {isPending ? (
          <ul aria-label="Loading platform status" className="space-y-2">
            {[0, 1, 2].map((key) => (
              <li key={key} className="h-9 animate-pulse rounded bg-mist" />
            ))}
          </ul>
        ) : isError ? (
          <div role="alert" className="flex items-start gap-3 rounded-[var(--radius-control)] bg-mist p-3">
            <ServerCrash aria-hidden="true" className="mt-0.5 size-5 shrink-0 text-red-text" />
            <div>
              <p className="text-sm font-medium">We could not reach the CivicWatch service.</p>
              <p className="text-sm text-navy-soft">
                Check your connection and try again. If you are on mobile data, the service may
                still be starting.
              </p>
            </div>
          </div>
        ) : (
          <>
            <p className="mb-2 text-sm font-medium">
              {data.status === "ok"
                ? "All services are operational."
                : "Some services are unavailable. Reporting may be affected."}
            </p>
            <ul>
              {(Object.keys(COMPONENT_LABELS) as Array<keyof typeof COMPONENT_LABELS>).map((key) => (
                <StatusRow key={key} label={COMPONENT_LABELS[key]} status={data[key]} />
              ))}
            </ul>
          </>
        )}
      </div>
    </section>
  );
}
