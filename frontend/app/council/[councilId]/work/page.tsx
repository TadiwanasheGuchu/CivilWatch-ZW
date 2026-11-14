import type { Metadata } from "next";

import { MyWorkView } from "@/features/council/operations/my-work-view";

export const metadata: Metadata = { title: "My work" };

export default async function MyWorkPage({ params }: { params: Promise<{ councilId: string }> }) {
  const { councilId } = await params;
  return (
    <main id="main" className="mx-auto max-w-3xl px-4 pt-6 pb-12 sm:px-6 sm:pt-10">
      <MyWorkView councilId={councilId} />
    </main>
  );
}
