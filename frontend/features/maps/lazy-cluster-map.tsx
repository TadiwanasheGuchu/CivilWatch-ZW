"use client";

import dynamic from "next/dynamic";

import type { ClusterMapProps } from "./cluster-map";

/** The report map, downloaded only when shown. */
export const LazyClusterMap = dynamic<ClusterMapProps>(() => import("./cluster-map"), {
  ssr: false,
  loading: () => <div role="status" aria-label="Loading map" className="h-[60vh] min-h-72 w-full animate-pulse rounded bg-mist md:h-[32rem]" />,
});
