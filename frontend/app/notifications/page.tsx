import type { Metadata } from "next";

import { NotificationsView } from "@/features/notifications/notifications-view";

export const metadata: Metadata = { title: "Notifications" };

export default function NotificationsPage() {
  return (
    <main id="main" className="mx-auto max-w-3xl px-4 pt-6 pb-12 sm:px-6 sm:pt-10">
      <NotificationsView />
    </main>
  );
}
