import type { Metadata } from "next";

import { TransparencyView } from "@/features/analytics/transparency-view";

export const metadata: Metadata = {
  title: "Council progress",
  description: "How Zimbabwean councils are handling verified public infrastructure reports.",
};

export default function TransparencyPage() {
  return (
    <main id="main" className="mx-auto max-w-5xl px-4 pt-6 pb-12 sm:px-6 sm:pt-10">
      <TransparencyView />
    </main>
  );
}
