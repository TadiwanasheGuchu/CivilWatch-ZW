"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { EmptyState, LoadError, LoadingRows } from "@/components/ui/page-states";
import { Pagination } from "@/components/ui/pagination";
import { RequireSession } from "@/features/authentication/require-session";
import type { SessionData } from "@/features/authentication/types";
import { formatDateTime } from "@/features/reporting/labels";
import { errorMessage } from "@/lib/api-client";
import { cn } from "@/lib/utils";

import { type AppNotification, fetchNotifications, markAllRead, markRead, notificationKeys, safeAppLink } from "./api";

export function NotificationsView() {
  return <RequireSession>{(session) => <Notifications session={session} />}</RequireSession>;
}

function Notifications({ session }: { session: SessionData }) {
  const [page, setPage] = useState(1);
  const queryClient = useQueryClient();
  const router = useRouter();
  const { data, isPending, isError, error, refetch } = useQuery({
    queryKey: notificationKeys.list(page),
    queryFn: ({ signal }) => fetchNotifications(page, signal),
  });
  const refresh = () => void queryClient.invalidateQueries({ queryKey: notificationKeys.root });
  const readAll = useMutation({ mutationFn: () => markAllRead(session.csrf_token), onSuccess: refresh });
  const open = useMutation({
    mutationFn: (n: AppNotification) => (n.read_at ? Promise.resolve(n) : markRead(n.id, session.csrf_token)),
    onSettled: refresh,
  });

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <h1 className="text-2xl font-bold">Notifications</h1>
        <Button variant="secondary" onClick={() => readAll.mutate()} disabled={readAll.isPending || !data?.items.some((n) => !n.read_at)}>
          Mark all as read
        </Button>
      </div>
      {isPending ? (
        <LoadingRows label="Loading notifications" rows={4} />
      ) : isError ? (
        <LoadError message={errorMessage(error)} onRetry={() => void refetch()} />
      ) : data.items.length === 0 ? (
        <EmptyState title="No notifications yet">Updates about your reports and work will appear here.</EmptyState>
      ) : (
        <>
          <ul className="divide-y divide-line overflow-hidden rounded-[var(--radius-panel)] border border-line bg-surface">
            {data.items.map((n) => (
              <li key={n.id}>
                <Link
                  href={safeAppLink(n.link)}
                  onClick={(event) => {
                    event.preventDefault();
                    open.mutate(n, { onSettled: () => router.push(safeAppLink(n.link)) });
                  }}
                  className={cn("flex gap-3 px-4 py-3 hover:bg-mist sm:px-5", !n.read_at && "bg-teal/5")}
                >
                  <span
                    aria-hidden="true"
                    className={cn("mt-2 size-2 shrink-0 rounded-full", n.read_at ? "bg-transparent" : "bg-teal")}
                  />
                  <span className="min-w-0 flex-1">
                    <span className={cn("block break-words", !n.read_at && "font-semibold")}>
                      {!n.read_at ? <span className="sr-only">Unread: </span> : null}
                      {n.title}
                    </span>
                    {n.body ? <span className="mt-0.5 block text-sm whitespace-pre-line break-words text-navy-soft">{n.body}</span> : null}
                    <span className="mt-0.5 block text-xs text-slate">
                      <time dateTime={n.created_at}>{formatDateTime(n.created_at)}</time>
                    </span>
                  </span>
                </Link>
              </li>
            ))}
          </ul>
          <Pagination page={page} pageSize={20} total={data.total} onPageChange={setPage} label="Notification pages" />
        </>
      )}
    </div>
  );
}
