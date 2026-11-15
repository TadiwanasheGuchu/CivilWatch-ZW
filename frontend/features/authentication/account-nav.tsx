"use client";

import { CircleUserRound, LogIn } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { signInHref } from "./redirect";
import { useSession } from "./use-session";

/** Header link: "Sign in" when signed out, the account page when signed in. */
export function AccountNav() {
  const { data: session, isPending } = useSession();
  const pathname = usePathname();
  const linkClass =
    "inline-flex min-h-11 items-center gap-2 rounded-[var(--radius-control)] px-3 text-sm font-medium text-white hover:bg-navy-soft";

  if (isPending) return <span aria-hidden="true" className="h-8 w-20 animate-pulse rounded bg-navy-soft" />;
  if (!session) {
    if (pathname === "/sign-in" || pathname === "/register") return null;
    return (
      <Link href={signInHref(pathname)} className={linkClass}>
        <LogIn aria-hidden="true" className="size-4" />
        Sign in
      </Link>
    );
  }
  const firstName = session.user.full_name.split(" ")[0] ?? session.user.full_name;
  return (
    <Link href="/account" className={linkClass} aria-label={`Your account (${session.user.full_name})`}>
      <CircleUserRound aria-hidden="true" className="size-5" />
      {/* Icon only on the narrowest phones, where the header has no room; the link is still named. */}
      <span className="hidden max-w-28 truncate min-[400px]:inline">{firstName}</span>
    </Link>
  );
}
