import type { TextareaHTMLAttributes } from "react";

import { cn } from "@/lib/utils";

export function Textarea({ className, ...props }: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea
      className={cn(
        "block min-h-32 w-full rounded-[var(--radius-control)] border border-line bg-surface px-3 py-2 text-base text-navy",
        "placeholder:text-slate aria-[invalid=true]:border-red-text",
        className,
      )}
      {...props}
    />
  );
}
