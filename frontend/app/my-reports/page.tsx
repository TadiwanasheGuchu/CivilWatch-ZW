import type { Metadata } from "next";

import { MyReportsView } from "@/features/reporting/my-reports-view";

export const metadata: Metadata = { title: "My reports" };

export default function MyReportsPage() {
  return (
    <main id="main" className="mx-auto max-w-3xl px-4 pt-6 pb-12 sm:px-6 sm:pt-10">
      <MyReportsView />
    </main>
  );
}
