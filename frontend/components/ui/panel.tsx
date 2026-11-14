import type { HTMLAttributes, ReactNode } from "react";

import { cn } from "@/lib/utils";

interface PanelProps extends HTMLAttributes<HTMLElement> {
  title?: string;
  description?: ReactNode;
  actions?: ReactNode;
}

/** Bordered white surface with an optional heading row. */
export function Panel({ title, description, actions, className, children, ...props }: PanelProps) {
  const headingId = title ? `panel-${title.toLowerCase().replace(/[^a-z0-9]+/g, "-")}` : undefined;
  return (
    <section
      aria-labelledby={headingId}
      className={cn(
        "rounded-[var(--radius-panel)] border border-line bg-surface p-4 sm:p-5",
        className,
      )}
      {...props}
    >
      {title ? (
        <div className="mb-4 flex items-start justify-between gap-3">
          <div>
            <h2 id={headingId} className="text-base font-semibold">
              {title}
            </h2>
            {description ? <p className="mt-0.5 text-sm text-slate">{description}</p> : null}
          </div>
          {actions}
        </div>
      ) : null}
      {children}
    </section>
  );
}
