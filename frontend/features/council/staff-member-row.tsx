"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useId, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Select } from "@/components/ui/select";
import { errorMessage } from "@/lib/api-client";

import { changeMemberRole, councilKeys, removeMember } from "./api";
import { COUNCIL_ROLES, ROLE_LABELS } from "./labels";
import type { CouncilRole, Member } from "./types";

interface StaffMemberRowProps {
  councilId: string;
  member: Member;
  isSelf: boolean;
  canManage: boolean;
  csrfToken: string;
}

export function StaffMemberRow({ councilId, member, isSelf, canManage, csrfToken }: StaffMemberRowProps) {
  const queryClient = useQueryClient();
  const selectId = useId();
  const [role, setRole] = useState<CouncilRole>(member.role);
  const [confirmingRemoval, setConfirmingRemoval] = useState(false);

  const refresh = () => {
    void queryClient.invalidateQueries({ queryKey: councilKeys.membersRoot(councilId) });
    void queryClient.invalidateQueries({ queryKey: ["council", councilId, "audit"] });
    if (isSelf) {
      void queryClient.invalidateQueries({ queryKey: councilKeys.workspace(councilId) });
      void queryClient.invalidateQueries({ queryKey: councilKeys.memberships });
    }
  };
  const changeRole = useMutation({
    mutationFn: () => changeMemberRole(councilId, member.membership_id, role, csrfToken),
    onSuccess: refresh,
  });
  const remove = useMutation({
    mutationFn: () => removeMember(councilId, member.membership_id, csrfToken),
    onSuccess: refresh,
    onSettled: () => setConfirmingRemoval(false),
  });
  const error = changeRole.error ?? remove.error;

  return (
    <li className="space-y-3 px-4 py-4 sm:px-5">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="font-medium break-words">
            {member.full_name}
            {isSelf ? <span className="font-normal text-slate"> (you)</span> : null}
          </p>
          <p className="text-sm break-all text-slate">{member.email}</p>
        </div>
        {!canManage ? <Badge tone="brand">{ROLE_LABELS[member.role]}</Badge> : null}
      </div>

      {canManage ? (
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
          <label htmlFor={selectId} className="sr-only">
            Role for {member.full_name}
          </label>
          <div className="sm:w-64">
            <Select
              id={selectId}
              value={role}
              onChange={(event) => setRole(event.target.value as CouncilRole)}
              disabled={changeRole.isPending || remove.isPending}
            >
              {COUNCIL_ROLES.map((option) => (
                <option key={option} value={option}>
                  {ROLE_LABELS[option]}
                </option>
              ))}
            </Select>
          </div>
          {role !== member.role ? (
            <div className="flex gap-2">
              <Button onClick={() => changeRole.mutate()} disabled={changeRole.isPending}>
                {changeRole.isPending ? "Saving…" : "Save role"}
              </Button>
              <Button variant="ghost" onClick={() => setRole(member.role)}>
                Cancel
              </Button>
            </div>
          ) : confirmingRemoval ? (
            <div className="flex flex-wrap items-center gap-2" role="group" aria-label={`Confirm removing ${member.full_name}`}>
              <span className="text-sm font-medium">Remove {isSelf ? "yourself" : "this person"}?</span>
              <Button
                className="bg-red-text text-white hover:bg-red-text/90"
                onClick={() => remove.mutate()}
                disabled={remove.isPending}
              >
                {remove.isPending ? "Removing…" : "Remove"}
              </Button>
              <Button variant="ghost" onClick={() => setConfirmingRemoval(false)}>
                Keep
              </Button>
            </div>
          ) : (
            <Button variant="ghost" className="text-red-text" onClick={() => setConfirmingRemoval(true)}>
              Remove from staff
            </Button>
          )}
        </div>
      ) : null}

      {error ? (
        <p role="alert" className="text-sm font-medium text-red-text">
          {errorMessage(error)}
        </p>
      ) : null}
    </li>
  );
}
