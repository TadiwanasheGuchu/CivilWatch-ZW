import type { Metadata } from "next";

import { BoundaryView } from "@/features/council/operations/boundary-view";

export const metadata: Metadata = { title: "Council boundary" };

export default async function BoundaryPage({ params }: { params: Promise<{ councilId: string }> }) {
  const { councilId } = await params;
  return (
    <main id="main" className="mx-auto max-w-5xl px-4 pt-6 pb-12 sm:px-6 sm:pt-10">
      <BoundaryView councilId={councilId} />
    </main>
  );
}
