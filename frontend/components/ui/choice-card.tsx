import type { InputHTMLAttributes, ReactNode } from "react";

import { cn } from "@/lib/utils";

interface ChoiceCardProps extends Omit<InputHTMLAttributes<HTMLInputElement>, "type"> {
  title: string;
  description?: ReactNode;
  icon?: ReactNode;
}

/**
 * A native radio button presented as a large tappable card. Being a real
 * radio input, it works with keyboards, screen readers and form semantics.
 */
export function ChoiceCard({ title, description, icon, className, ...props }: ChoiceCardProps) {
  return (
    <label
      className={cn(
        "flex min-h-14 cursor-pointer items-start gap-3 rounded-[var(--radius-control)] border border-line bg-surface p-3",
        "has-[:checked]:border-teal has-[:checked]:bg-teal/5 has-[:focus-visible]:outline-3 has-[:focus-visible]:outline-offset-2 has-[:focus-visible]:outline-teal",
        className,
      )}
    >
      <input type="radio" className="mt-1 size-4 shrink-0 accent-teal" {...props} />
      {icon ? <span className="mt-0.5 shrink-0 text-teal">{icon}</span> : null}
      <span className="min-w-0">
        <span className="block font-medium">{title}</span>
        {description ? <span className="mt-0.5 block text-sm text-slate">{description}</span> : null}
      </span>
    </label>
  );
}
