import type { Metadata } from "next";

import { OverviewView } from "@/features/council/operations/overview-view";

export const metadata: Metadata = { title: "Council overview" };

export default async function CouncilOverviewPage({ params }: { params: Promise<{ councilId: string }> }) {
  const { councilId } = await params;
  return (
    <main id="main" className="mx-auto max-w-5xl px-4 pt-6 pb-12 sm:px-6 sm:pt-10">
      <OverviewView councilId={councilId} />
    </main>
  );
}
