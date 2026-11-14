import { Camera, ClipboardCheck, ListChecks, Plus } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import Link from "next/link";

import { buttonVariants } from "@/components/ui/button";
import { RecentReports } from "@/features/reporting/recent-reports";
import { SystemStatusPanel } from "@/features/system-status/system-status-panel";
import { cn } from "@/lib/utils";

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
    body: "See each status change until the work is resolved.",
  },
];

export default function HomePage() {
  return (
    <main id="main" className="mx-auto max-w-5xl px-4 pt-6 pb-12 sm:px-6 sm:pt-10">
      <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_22rem] lg:gap-12">
        <div className="space-y-8">
          <div>
            <p className="text-sm font-medium text-teal">Infrastructure reporting for Zimbabwe</p>
            <h1 className="mt-2 text-2xl leading-tight font-bold sm:text-3xl">
              See a problem on your street? Tell the council that can fix it.
            </h1>
            <p className="mt-3 max-w-prose text-base text-navy-soft">
              Report potholes, broken streetlights, blocked drains, water leaks and uncollected waste —
              and follow every report in the open.
            </p>
            <div className="mt-5 flex flex-col gap-2 sm:flex-row">
              <Link href="/report" className={cn(buttonVariants({ size: "lg" }))}>
                <Plus aria-hidden="true" />
                Report a problem
              </Link>
              <Link href="/explore" className={cn(buttonVariants({ variant: "secondary", size: "lg" }))}>
                Explore reports
              </Link>
            </div>
          </div>

          <RecentReports />

          <section aria-labelledby="how-heading">
            <h2 id="how-heading" className="text-lg font-semibold">
              How it works
            </h2>
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
          </section>
        </div>

        <aside>
          <SystemStatusPanel />
        </aside>
      </div>
    </main>
  );
}
