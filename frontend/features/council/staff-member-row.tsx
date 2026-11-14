"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useId, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Select } from "@/components/ui/select";
import { errorMessage } from "@/lib/api-client";

import { councilKeys, removeMember, updateMember } from "./api";
import { COUNCIL_ROLES, ROLE_LABELS } from "./labels";
import { opsKeys } from "./operations/api";
import type { Department } from "./operations/types";
import type { CouncilRole, Member } from "./types";

/** Roles that belong to one department. */
const DEPARTMENT_ROLES = new Set<CouncilRole>(["department_manager", "maintenance_officer"]);

interface StaffMemberRowProps {
  councilId: string;
  member: Member;
  isSelf: boolean;
  canManage: boolean;
  csrfToken: string;
  departments?: Department[];
}

export function StaffMemberRow({ councilId, member, isSelf, canManage, csrfToken, departments = [] }: StaffMemberRowProps) {
  const queryClient = useQueryClient();
  const roleId = useId();
  const departmentId = useId();
  const [role, setRole] = useState<CouncilRole>(member.role);
  const [department, setDepartment] = useState<string>(member.department?.id ?? "");
  const [confirmingRemoval, setConfirmingRemoval] = useState(false);
  const usesDepartment = DEPARTMENT_ROLES.has(role);
  const effectiveDepartment = usesDepartment ? department : "";
  const changed = role !== member.role || effectiveDepartment !== (member.department?.id ?? "");

  const refresh = () => {
    void queryClient.invalidateQueries({ queryKey: councilKeys.membersRoot(councilId) });
    void queryClient.invalidateQueries({ queryKey: ["council", councilId, "audit"] });
    void queryClient.invalidateQueries({ queryKey: opsKeys.allMembers(councilId) });
    if (isSelf) {
      void queryClient.invalidateQueries({ queryKey: councilKeys.workspace(councilId) });
      void queryClient.invalidateQueries({ queryKey: councilKeys.memberships });
    }
  };
  const save = useMutation({
    mutationFn: () => {
      const body: { role?: CouncilRole; department_id?: string | null } = {};
      if (role !== member.role) body.role = role;
      // Moving to a role without departments clears it on the server automatically.
      if (usesDepartment && effectiveDepartment !== (member.department?.id ?? "")) {
        body.department_id = effectiveDepartment || null;
      }
      return updateMember(councilId, member.membership_id, body, csrfToken);
    },
    onSuccess: refresh,
  });
  const remove = useMutation({
    mutationFn: () => removeMember(councilId, member.membership_id, csrfToken),
    onSuccess: refresh,
    onSettled: () => setConfirmingRemoval(false),
  });
  const error = save.error ?? remove.error;
  const activeDepartments = departments.filter((d) => d.is_active || d.id === member.department?.id);

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
        {!canManage ? (
          <div className="flex flex-wrap gap-1">
            <Badge tone="brand">{ROLE_LABELS[member.role]}</Badge>
            {member.department ? <Badge>{member.department.name}</Badge> : null}
          </div>
        ) : null}
      </div>

      {canManage ? (
        <div className="space-y-2">
          <div className="grid gap-2 sm:grid-cols-2">
            <div>
              <label htmlFor={roleId} className="sr-only">
                Role for {member.full_name}
              </label>
              <Select id={roleId} value={role} onChange={(e) => setRole(e.target.value as CouncilRole)} disabled={save.isPending || remove.isPending}>
                {COUNCIL_ROLES.map((option) => (
                  <option key={option} value={option}>
                    {ROLE_LABELS[option]}
                  </option>
                ))}
              </Select>
            </div>
            {usesDepartment ? (
              <div>
                <label htmlFor={departmentId} className="sr-only">
                  Department for {member.full_name}
                </label>
                <Select id={departmentId} value={department} onChange={(e) => setDepartment(e.target.value)} disabled={save.isPending}>
                  <option value="">No department</option>
                  {activeDepartments.map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.name}
                    </option>
                  ))}
                </Select>
              </div>
            ) : null}
          </div>
          {changed ? (
            <div className="flex gap-2">
              <Button onClick={() => save.mutate()} disabled={save.isPending}>
                {save.isPending ? "Saving…" : "Save changes"}
              </Button>
              <Button
                variant="ghost"
                onClick={() => {
                  setRole(member.role);
                  setDepartment(member.department?.id ?? "");
                }}
              >
                Cancel
              </Button>
            </div>
          ) : confirmingRemoval ? (
            <div className="flex flex-wrap items-center gap-2" role="group" aria-label={`Confirm removing ${member.full_name}`}>
              <span className="text-sm font-medium">Remove {isSelf ? "yourself" : "this person"}?</span>
              <Button className="bg-red-text text-white hover:bg-red-text/90" onClick={() => remove.mutate()} disabled={remove.isPending}>
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
