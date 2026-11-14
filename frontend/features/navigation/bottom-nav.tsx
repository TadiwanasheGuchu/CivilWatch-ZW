"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/utils";

import { isActive, NAV_ITEMS } from "./nav-items";

/** Phone navigation. Hidden on the report form, which has its own action bar. */
export function BottomNav() {
  const pathname = usePathname();
  if (pathname === "/report") return null;
  return (
    <nav
      aria-label="Main"
      className="fixed inset-x-0 bottom-0 z-30 border-t border-line bg-surface pb-[env(safe-area-inset-bottom)] md:hidden"
    >
      <ul className="mx-auto grid max-w-md grid-cols-5">
        {NAV_ITEMS.map(({ href, label, icon: Icon, primary }) => {
          const active = isActive(pathname, href);
          return (
            <li key={href}>
              <Link
                href={href}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "flex min-h-14 flex-col items-center justify-center gap-0.5 text-[11px] font-medium",
                  active ? "text-teal" : "text-slate",
                )}
              >
                {primary ? (
                  <span className="grid size-10 place-items-center rounded-full bg-teal text-white shadow-sm">
                    <Icon aria-hidden="true" className="size-5" strokeWidth={2.5} />
                  </span>
                ) : (
                  <Icon aria-hidden="true" className="size-5" />
                )}
                <span>{label}</span>
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
