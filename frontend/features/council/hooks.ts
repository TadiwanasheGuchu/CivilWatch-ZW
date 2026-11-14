"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { councilKeys, fetchAuditLog, fetchMembers, fetchMyMemberships, fetchWorkspace } from "./api";

export function useMyMemberships(enabled = true) {
  return useQuery({
    queryKey: councilKeys.memberships,
    queryFn: ({ signal }) => fetchMyMemberships(signal),
    enabled,
  });
}

export function useWorkspace(councilId: string) {
  return useQuery({
    queryKey: councilKeys.workspace(councilId),
    queryFn: ({ signal }) => fetchWorkspace(councilId, signal),
  });
}

export function useMembers(councilId: string, page: number, enabled: boolean) {
  return useQuery({
    queryKey: councilKeys.members(councilId, page),
    queryFn: ({ signal }) => fetchMembers(councilId, page, signal),
    placeholderData: keepPreviousData,
    enabled,
  });
}

export function useAuditLog(councilId: string, page: number, enabled: boolean) {
  return useQuery({
    queryKey: councilKeys.audit(councilId, page),
    queryFn: ({ signal }) => fetchAuditLog(councilId, page, signal),
    placeholderData: keepPreviousData,
    enabled,
  });
}
