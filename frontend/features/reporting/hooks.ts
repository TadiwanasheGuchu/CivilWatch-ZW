"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";

import {
  type ExploreFilters,
  fetchCategories,
  fetchCouncilDirectory,
  fetchMyReports,
  fetchPublishedReports,
  fetchReport,
  reportKeys,
} from "./api";
import { readReference, writeReference } from "./reference-cache";
import type { Category } from "./types";

type CouncilOption = { id: string; slug: string; name: string };

export function useCategories() {
  return useQuery({
    queryKey: reportKeys.categories,
    queryFn: async ({ signal }) => {
      const categories = await fetchCategories(signal);
      writeReference("categories", categories);
      return categories;
    },
    initialData: () => readReference<Category[]>("categories"),
    initialDataUpdatedAt: 0,
    staleTime: 60 * 60_000,
  });
}

export function useCouncilOptions() {
  return useQuery({
    queryKey: reportKeys.councils,
    queryFn: async ({ signal }) => {
      const councils = (await fetchCouncilDirectory(signal)).items;
      writeReference("councils", councils);
      return councils;
    },
    initialData: () => readReference<CouncilOption[]>("councils"),
    initialDataUpdatedAt: 0,
    staleTime: 60 * 60_000,
  });
}

export function useMyReports(page: number) {
  return useQuery({
    queryKey: reportKeys.mine(page),
    queryFn: ({ signal }) => fetchMyReports(page, signal),
    placeholderData: keepPreviousData,
  });
}

export function useReport(id: string) {
  return useQuery({
    queryKey: reportKeys.detail(id),
    queryFn: ({ signal }) => fetchReport(id, signal),
    // Photo URLs expire after five minutes; refresh well before that.
    staleTime: 2 * 60_000,
    refetchInterval: 4 * 60_000,
  });
}

export function usePublishedReports(filters: ExploreFilters, page: number) {
  return useQuery({
    queryKey: reportKeys.explore(filters, page),
    queryFn: ({ signal }) => fetchPublishedReports(filters, page, signal),
    placeholderData: keepPreviousData,
  });
}
