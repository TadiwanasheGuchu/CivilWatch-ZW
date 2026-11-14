import type { Metadata } from "next";

import { ReviewView } from "@/features/council/operations/review-view";

export const metadata: Metadata = { title: "Review report" };

export default async function CouncilReviewPage({ params }: { params: Promise<{ councilId: string; issueId: string }> }) {
  const { councilId, issueId } = await params;
  return (
    <main id="main" className="mx-auto max-w-6xl px-4 pt-6 pb-12 sm:px-6 sm:pt-10">
      <ReviewView councilId={councilId} issueId={issueId} />
    </main>
  );
}
