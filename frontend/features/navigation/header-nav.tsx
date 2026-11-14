"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/utils";

import { isActive, NAV_ITEMS } from "./nav-items";

/** Tablet and desktop: the same destinations as the bottom bar, in the header. */
export function HeaderNav() {
  const pathname = usePathname();
  return (
    <nav aria-label="Main" className="hidden md:block">
      <ul className="flex items-center gap-1">
        {NAV_ITEMS.filter((item) => item.href !== "/" && item.href !== "/account").map(({ href, label, primary }) => (
          <li key={href}>
            <Link
              href={href}
              aria-current={isActive(pathname, href) ? "page" : undefined}
              className={cn(
                "inline-flex min-h-11 items-center rounded-[var(--radius-control)] px-3 text-sm font-medium",
                primary ? "bg-teal text-white hover:bg-teal-hover" : "text-white/80 hover:bg-navy-soft hover:text-white",
                "aria-[current=page]:text-white aria-[current=page]:underline aria-[current=page]:underline-offset-8",
              )}
            >
              {primary ? "Report a problem" : label}
            </Link>
          </li>
        ))}
      </ul>
    </nav>
  );
}
