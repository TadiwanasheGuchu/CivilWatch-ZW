"use client";

import { useQuery } from "@tanstack/react-query";
import { Bell } from "lucide-react";
import Link from "next/link";

import { useSession } from "@/features/authentication/use-session";

import { fetchUnreadCount, notificationKeys } from "./api";

/** Header bell with the unread count, refreshed every minute while the page is open. */
export function NotificationBell() {
  const { data: session } = useSession();
  const { data } = useQuery({
    queryKey: notificationKeys.unread,
    queryFn: ({ signal }) => fetchUnreadCount(signal),
    enabled: Boolean(session),
    refetchInterval: 60_000,
    // Only poll while the tab is visible, to save data.
    refetchIntervalInBackground: false,
    refetchOnWindowFocus: true,
  });
  if (!session) return null;
  const count = data?.unread ?? 0;
  return (
    <Link
      href="/notifications"
      aria-label={count ? `Notifications, ${count} unread` : "Notifications"}
      className="relative inline-grid size-11 place-items-center rounded-[var(--radius-control)] text-white hover:bg-navy-soft"
    >
      <Bell aria-hidden="true" className="size-5" />
      {count ? (
        <span
          aria-hidden="true"
          className="absolute top-1.5 right-1 min-w-5 rounded-full bg-amber px-1 text-center text-xs leading-5 font-bold text-navy tabular"
        >
          {count > 99 ? "99+" : count}
        </span>
      ) : null}
    </Link>
  );
}
