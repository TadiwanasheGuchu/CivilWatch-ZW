import type { Page } from "@/features/council/types";
import { apiGet, apiSend } from "@/lib/api-client";

export type NotificationKind =
  | "status_changed"
  | "information_requested"
  | "information_provided"
  | "work_assigned"
  | "feedback_not_fixed";

export interface AppNotification {
  id: string;
  kind: NotificationKind;
  title: string;
  body: string | null;
  link: string;
  created_at: string;
  read_at: string | null;
}

export const notificationKeys = {
  root: ["notifications"] as const,
  unread: ["notifications", "unread"] as const,
  list: (page: number) => ["notifications", "list", page] as const,
};

export function fetchUnreadCount(signal?: AbortSignal) {
  return apiGet<{ unread: number }>("/notifications/unread-count", { signal, cache: "no-store" });
}

export function fetchNotifications(page: number, signal?: AbortSignal) {
  return apiGet<Page<AppNotification>>(`/notifications?page=${page}&page_size=20`, { signal, cache: "no-store" });
}

export function markRead(id: string, csrfToken: string) {
  return apiSend<AppNotification>("POST", `/notifications/${encodeURIComponent(id)}/read`, { csrfToken });
}

export function markAllRead(csrfToken: string) {
  return apiSend<{ unread: number }>("POST", "/notifications/read-all", { csrfToken });
}

/** Only follow links inside the app (the API only ever stores relative links). */
export function safeAppLink(link: string): string {
  return link.startsWith("/") && !link.startsWith("//") && !link.startsWith("/\\") ? link : "/";
}
