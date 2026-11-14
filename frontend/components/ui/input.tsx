import type { InputHTMLAttributes } from "react";

import { cn } from "@/lib/utils";

/** Text input. 16px font prevents iOS zoom on focus; 44px min height for touch. */
export function Input({ className, ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={cn(
        "block min-h-11 w-full rounded-[var(--radius-control)] border border-line bg-surface px-3 text-base text-navy",
        "placeholder:text-slate aria-[invalid=true]:border-red-text",
        "disabled:cursor-not-allowed disabled:bg-mist",
        className,
      )}
      {...props}
    />
  );
}
