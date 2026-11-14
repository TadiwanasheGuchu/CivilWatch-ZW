import type { Metadata } from "next";

import { StaffView } from "@/features/council/staff-view";

export const metadata: Metadata = { title: "Council staff" };

export default async function CouncilStaffPage({ params }: { params: Promise<{ councilId: string }> }) {
  const { councilId } = await params;
  return (
    <main id="main" className="mx-auto max-w-5xl px-4 pt-6 pb-12 sm:px-6 sm:pt-10">
      <StaffView councilId={councilId} />
    </main>
  );
}
