"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { fetchMembersAll } from "./members";
import { fetchDepartments, fetchQueue, fetchStaffIssue, fetchSummary, opsKeys } from "./api";
import type { QueueFilters } from "./types";

export function useQueueSummary(councilId: string, enabled = true) {
  return useQuery({ queryKey: opsKeys.summary(councilId), queryFn: ({ signal }) => fetchSummary(councilId, signal), enabled });
}

export function useQueue(councilId: string, filters: QueueFilters, page: number) {
  return useQuery({
    queryKey: opsKeys.queue(councilId, filters, page),
    queryFn: ({ signal }) => fetchQueue(councilId, filters, page, signal),
    placeholderData: keepPreviousData,
  });
}

export function useStaffIssue(councilId: string, issueId: string) {
  return useQuery({
    queryKey: opsKeys.issue(councilId, issueId),
    queryFn: ({ signal }) => fetchStaffIssue(councilId, issueId, signal),
    // Photo URLs expire after five minutes.
    staleTime: 2 * 60_000,
    refetchInterval: 4 * 60_000,
  });
}

export function useDepartments(councilId: string, enabled = true) {
  return useQuery({
    queryKey: opsKeys.departments(councilId),
    queryFn: ({ signal }) => fetchDepartments(councilId, signal),
    enabled,
  });
}

export function useAllMembers(councilId: string, enabled = true) {
  return useQuery({
    queryKey: opsKeys.allMembers(councilId),
    queryFn: ({ signal }) => fetchMembersAll(councilId, signal),
    enabled,
  });
}
