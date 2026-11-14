import type { Metadata } from "next";
import { Suspense } from "react";

import { QueueView } from "@/features/council/operations/queue-view";

export const metadata: Metadata = { title: "Council reports" };

export default async function CouncilReportsPage({ params }: { params: Promise<{ councilId: string }> }) {
  const { councilId } = await params;
  return (
    <main id="main" className="mx-auto max-w-5xl px-4 pt-6 pb-12 sm:px-6 sm:pt-10">
      <Suspense>
        <QueueView councilId={councilId} />
      </Suspense>
    </main>
  );
}
