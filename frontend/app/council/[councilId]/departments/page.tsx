import type { Metadata } from "next";

import { DepartmentsView } from "@/features/council/operations/departments-view";

export const metadata: Metadata = { title: "Departments" };

export default async function DepartmentsPage({ params }: { params: Promise<{ councilId: string }> }) {
  const { councilId } = await params;
  return (
    <main id="main" className="mx-auto max-w-5xl px-4 pt-6 pb-12 sm:px-6 sm:pt-10">
      <DepartmentsView councilId={councilId} />
    </main>
  );
}
