import { CircleAlert, CircleCheck, Info } from "lucide-react";
import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

const TONES = {
  error: { icon: CircleAlert, border: "border-red", iconClass: "text-red-text" },
  success: { icon: CircleCheck, border: "border-teal", iconClass: "text-teal" },
  info: { icon: Info, border: "border-line", iconClass: "text-slate" },
} as const;

interface AlertProps {
  tone: keyof typeof TONES;
  title?: string;
  children?: ReactNode;
  className?: string;
}

/** Inline status message. Errors are announced immediately (role="alert"). */
export function Alert({ tone, title, children, className }: AlertProps) {
  const { icon: Icon, border, iconClass } = TONES[tone];
  return (
    <div
      role={tone === "error" ? "alert" : "status"}
      className={cn(
        "flex gap-3 rounded-[var(--radius-control)] border-l-4 bg-surface px-4 py-3 text-sm",
        border,
        className,
      )}
    >
      <Icon aria-hidden="true" className={cn("mt-0.5 size-4 shrink-0", iconClass)} />
      <div className="space-y-0.5">
        {title ? <p className="font-semibold">{title}</p> : null}
        {children ? <div className="text-navy-soft">{children}</div> : null}
      </div>
    </div>
  );
}
