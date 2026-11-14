import { ChevronDown } from "lucide-react";
import type { SelectHTMLAttributes } from "react";

import { cn } from "@/lib/utils";

/**
 * Native select, styled. Deliberately not a custom listbox: the native
 * control gives budget Android phones their own picker, works with screen
 * readers and keyboards out of the box, and ships no extra JavaScript.
 */
export function Select({ className, children, ...props }: SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <div className="relative">
      <select
        className={cn(
          "block min-h-11 w-full appearance-none rounded-[var(--radius-control)] border border-line bg-surface py-2 pr-10 pl-3 text-base text-navy",
          "aria-[invalid=true]:border-red-text disabled:cursor-not-allowed disabled:bg-mist",
          className,
        )}
        {...props}
      >
        {children}
      </select>
      <ChevronDown
        aria-hidden="true"
        className="pointer-events-none absolute top-1/2 right-3 size-4 -translate-y-1/2 text-slate"
      />
    </div>
  );
}
