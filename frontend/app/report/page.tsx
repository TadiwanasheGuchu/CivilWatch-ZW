import type { Metadata } from "next";

import { ReportWizard } from "@/features/reporting/wizard/report-wizard";

export const metadata: Metadata = { title: "Report a problem" };

export default function ReportPage() {
  return (
    <main id="main" className="mx-auto w-full max-w-2xl px-4 pt-6 sm:pt-10">
      <ReportWizard />
    </main>
  );
}
