import { cn } from "@/lib/utils";

import { STATUS_LABELS, STATUS_TONES, type StatusTone } from "./labels";
import type { IssueStatus } from "./types";

const TONE_CLASSES: Record<StatusTone, string> = {
  // A hairline keeps neutral badges visible on the grey page background too.
  neutral: "bg-surface text-navy ring-1 ring-inset ring-line",
  progress: "bg-teal/10 text-teal",
  done: "bg-navy text-white",
  stopped: "bg-red/10 text-red-text",
  attention: "bg-amber/20 text-amber-text",
};

/** Status is always shown as text; colour only reinforces it. */
export function StatusBadge({ status, className }: { status: IssueStatus; className?: string }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold whitespace-nowrap",
        TONE_CLASSES[STATUS_TONES[status]],
        className,
      )}
    >
      {STATUS_LABELS[status]}
    </span>
  );
}
