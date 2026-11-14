import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

const TONES = {
  neutral: "bg-mist text-navy",
  brand: "bg-teal/10 text-teal",
  navy: "bg-navy text-white",
} as const;

export function Badge({
  tone = "neutral",
  children,
  className,
}: {
  tone?: keyof typeof TONES;
  children: ReactNode;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium whitespace-nowrap",
        TONES[tone],
        className,
      )}
    >
      {children}
    </span>
  );
}
