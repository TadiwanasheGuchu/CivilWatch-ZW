"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { ApiError } from "@/lib/api-client";

import { opsKeys } from "./api";
import type { StaffIssueDetail } from "./types";

/** Run a change that returns the updated report, then refresh counts and lists. */
export function useIssueMutation<TInput>(
  councilId: string,
  issueId: string,
  mutate: (input: TInput) => Promise<StaffIssueDetail>,
) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: mutate,
    onSuccess: (detail) => {
      queryClient.setQueryData(opsKeys.issue(councilId, issueId), detail);
      void queryClient.invalidateQueries({
        predicate: (query) =>
          query.queryKey[0] === "council" &&
          query.queryKey[1] === councilId &&
          query.queryKey[2] === "ops" &&
          query.queryKey[3] !== "issue",
      });
    },
    onError: (error) => {
      // Someone else changed the report first: show its current state.
      if (error instanceof ApiError && error.status === 409) {
        void queryClient.invalidateQueries({ queryKey: opsKeys.issue(councilId, issueId) });
      }
    },
  });
}
