import type { Metadata } from "next";
import { Suspense } from "react";

import { ReportDetailView } from "@/features/reporting/report-detail-view";

export const metadata: Metadata = { title: "Report" };

export default async function ReportPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return (
    <main id="main" className="mx-auto max-w-3xl px-4 pt-6 pb-12 sm:px-6 sm:pt-10">
      <Suspense>
        <ReportDetailView id={id} />
      </Suspense>
    </main>
  );
}
