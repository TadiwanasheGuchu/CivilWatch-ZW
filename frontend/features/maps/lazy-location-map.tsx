"use client";

import dynamic from "next/dynamic";

import type { LocationMapProps } from "./location-map";

/** The map, loaded only when rendered and never on the server. */
export const LazyLocationMap = dynamic<LocationMapProps>(() => import("./location-map"), {
  ssr: false,
  loading: () => (
    <div role="status" aria-label="Loading map" className="h-64 w-full animate-pulse bg-mist sm:h-80" />
  ),
});
