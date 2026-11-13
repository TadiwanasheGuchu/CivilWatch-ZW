"use client";

import { useQuery } from "@tanstack/react-query";

import { fetchReadiness } from "./api";

export function useReadiness() {
  return useQuery({
    queryKey: ["system", "readiness"],
    queryFn: ({ signal }) => fetchReadiness(signal),
    staleTime: 30_000,
  });
}
