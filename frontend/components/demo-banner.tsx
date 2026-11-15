import { FlaskConical } from "lucide-react";

import { DEMO_MODE } from "@/lib/config";

/** Shown on every page of a demonstration deployment so sample data is never mistaken for real reports. */
export function DemoBanner() {
  if (!DEMO_MODE) return null;
  return (
    <div role="note" aria-label="Demonstration site" className="border-b border-amber/40 bg-amber/15 text-navy">
      <p className="mx-auto flex max-w-5xl items-start gap-2 px-4 py-2 text-sm sm:px-6">
        <FlaskConical aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
        <span>
          <strong className="font-semibold">Demonstration site.</strong> Councils, boundaries, accounts and reports
          here are sample data, not real infrastructure problems.
        </span>
      </p>
    </div>
  );
}
