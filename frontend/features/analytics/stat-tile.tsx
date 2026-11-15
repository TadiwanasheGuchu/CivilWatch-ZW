import type { ReactNode } from "react";

/** One headline figure. The number is real data; `hint` explains what it counts. */
export function StatTile({ label, value, hint }: { label: string; value: ReactNode; hint?: string }) {
  return (
    <div className="rounded-[var(--radius-control)] border border-line bg-surface p-3">
      <dt className="text-sm font-medium text-navy-soft">{label}</dt>
      <dd className="mt-1 font-heading text-2xl font-bold tabular">{value}</dd>
      {hint ? <dd className="mt-0.5 text-xs text-slate">{hint}</dd> : null}
    </div>
  );
}

/** A labelled count with a proportional bar; the bar is decoration, the number is the content. */
export function CountBar({ label, value, max, detail }: { label: string; value: number; max: number; detail?: string }) {
  const width = max > 0 ? Math.max(2, Math.round((value / max) * 100)) : 0;
  return (
    <li className="space-y-1 py-2">
      <div className="flex items-baseline justify-between gap-3 text-sm">
        <span className="min-w-0 font-medium break-words">{label}</span>
        <span className="shrink-0 tabular text-navy-soft">
          {value}
          {detail ? <span className="text-slate"> · {detail}</span> : null}
        </span>
      </div>
      <div aria-hidden="true" className="h-1.5 rounded-full bg-mist">
        <div className="h-full rounded-full bg-teal" style={{ width: `${width}%` }} />
      </div>
    </li>
  );
}
