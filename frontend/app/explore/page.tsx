import type { Metadata } from "next";

import { ExploreView } from "@/features/reporting/explore-view";

export const metadata: Metadata = { title: "Explore reports" };

export default function ExplorePage() {
  return (
    <main id="main" className="mx-auto max-w-3xl px-4 pt-6 pb-12 sm:px-6 sm:pt-10">
      <ExploreView />
    </main>
  );
}
