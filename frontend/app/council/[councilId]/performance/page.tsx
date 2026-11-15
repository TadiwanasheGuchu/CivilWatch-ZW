import type { Metadata } from "next";

import { PerformanceView } from "@/features/analytics/performance-view";

export const metadata: Metadata = { title: "Council performance" };

export default async function CouncilPerformancePage({ params }: { params: Promise<{ councilId: string }> }) {
  const { councilId } = await params;
  return (
    <main id="main" className="mx-auto max-w-5xl px-4 pt-6 pb-12 sm:px-6 sm:pt-10">
      <PerformanceView councilId={councilId} />
    </main>
  );
}
