import { Camera, ClipboardCheck, ListChecks } from "lucide-react";
import type { LucideIcon } from "lucide-react";

import { SystemStatusPanel } from "@/features/system-status/system-status-panel";

const STEPS: Array<{ icon: LucideIcon; title: string; body: string }> = [
  {
    icon: Camera,
    title: "Report it",
    body: "Choose the problem, add a photo and confirm the location on a map.",
  },
  {
    icon: ClipboardCheck,
    title: "Council verifies and assigns",
    body: "Your council checks the report and sends it to the team responsible.",
  },
  {
    icon: ListChecks,
    title: "Follow progress",
    body: "See each status change until the work is resolved, and say whether it was fixed.",
  },
];

export default function HomePage() {
  return (
    <main id="main" className="mx-auto max-w-5xl px-4 pt-6 pb-12 sm:px-6 sm:pt-10">
      <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_22rem] lg:gap-12">
        <div>
          <p className="text-sm font-medium text-teal">Infrastructure reporting for Zimbabwe</p>
          <h1 className="mt-2 text-2xl leading-tight font-bold sm:text-3xl">
            See a problem on your street? Tell the council that can fix it.
          </h1>
          <p className="mt-3 max-w-prose text-base text-navy-soft">
            CivicWatch connects residents with their local authority to report potholes, broken
            streetlights, blocked drains, water leaks and uncollected waste — and to track every
            report in the open.
          </p>

          <h2 className="mt-8 text-lg font-semibold">How it works</h2>
          <ol className="mt-3 divide-y divide-line rounded-[var(--radius-panel)] border border-line bg-surface">
            {STEPS.map(({ icon: Icon, title, body }, index) => (
              <li key={title} className="flex gap-3 p-4">
                <span className="grid size-9 shrink-0 place-items-center rounded-md bg-mist text-teal">
                  <Icon aria-hidden="true" className="size-5" strokeWidth={2} />
                </span>
                <div>
                  <h3 className="text-sm font-semibold">
                    <span className="sr-only">Step {index + 1}: </span>
                    {title}
                  </h3>
                  <p className="mt-0.5 text-sm text-slate">{body}</p>
                </div>
              </li>
            ))}
          </ol>

          <p className="mt-6 rounded-[var(--radius-control)] border-l-4 border-amber bg-surface px-4 py-3 text-sm">
            <span className="font-semibold text-amber-text">In development.</span> Resident
            accounts and report submission are being built and are not open yet.
          </p>
        </div>

        <aside>
          <SystemStatusPanel />
        </aside>
      </div>
    </main>
  );
}
