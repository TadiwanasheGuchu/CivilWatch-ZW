import { MapPinned } from "lucide-react";
import Link from "next/link";

import { AccountNav } from "@/features/authentication/account-nav";
import { HeaderNav } from "@/features/navigation/header-nav";
import { NotificationBell } from "@/features/notifications/notification-bell";

export function SiteHeader() {
  return (
    <header className="bg-navy text-white">
      <div className="mx-auto flex h-14 max-w-5xl items-center justify-between gap-3 px-4 sm:px-6">
        <Link
          href="/"
          className="inline-flex min-h-11 items-center gap-2 font-heading text-base font-bold tracking-tight"
        >
          <span className="grid size-8 place-items-center rounded-md bg-teal">
            <MapPinned aria-hidden="true" className="size-4" strokeWidth={2.25} />
          </span>
          CivicWatch <span className="font-medium text-white/70">ZW</span>
        </Link>
        <div className="flex items-center gap-2">
          <HeaderNav />
          <NotificationBell />
          <AccountNav />
        </div>
      </div>
    </header>
  );
}
