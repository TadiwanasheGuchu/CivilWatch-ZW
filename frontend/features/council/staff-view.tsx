"use client";

import { useState } from "react";

import { EmptyState, LoadError, LoadingRows } from "@/components/ui/page-states";
import { Pagination } from "@/components/ui/pagination";
import { Panel } from "@/components/ui/panel";
import { errorMessage } from "@/lib/api-client";

import { AddStaffForm } from "./add-staff-form";
import { PAGE_SIZE } from "./api";
import { CouncilShell } from "./council-shell";
import { useMembers } from "./hooks";
import { StaffMemberRow } from "./staff-member-row";

export function StaffView({ councilId }: { councilId: string }) {
  return (
    <CouncilShell councilId={councilId} tab="staff">
      {(workspace, session) => {
        if (!workspace.permissions.includes("members.view")) {
          return <EmptyState title="Nothing to show yet">Your role has no staff tools in this council.</EmptyState>;
        }
        const canManage = workspace.permissions.includes("members.manage");
        return (
          <div className="space-y-6">
            {canManage ? (
              <Panel title="Add staff" description="Give a registered CivicWatch user a role in this council.">
                <AddStaffForm councilId={councilId} csrfToken={session.csrf_token} />
              </Panel>
            ) : null}
            <StaffList
              councilId={councilId}
              canManage={canManage}
              currentUserId={session.user.id}
              csrfToken={session.csrf_token}
            />
          </div>
        );
      }}
    </CouncilShell>
  );
}

function StaffList({
  councilId,
  canManage,
  currentUserId,
  csrfToken,
}: {
  councilId: string;
  canManage: boolean;
  currentUserId: string;
  csrfToken: string;
}) {
  const [page, setPage] = useState(1);
  const { data, isPending, isError, error, refetch } = useMembers(councilId, page, true);

  return (
    <Panel title="Staff" description={data ? `${data.total} ${data.total === 1 ? "person" : "people"}` : undefined}>
      {isPending ? (
        <LoadingRows label="Loading staff" />
      ) : isError ? (
        <LoadError message={errorMessage(error)} onRetry={() => void refetch()} />
      ) : data.items.length === 0 ? (
        <EmptyState title="No staff yet" />
      ) : (
        <>
          <ul className="-mx-4 divide-y divide-line border-t border-line sm:-mx-5">
            {data.items.map((member) => (
              <StaffMemberRow
                key={`${member.membership_id}-${member.role}`}
                councilId={councilId}
                member={member}
                isSelf={member.user_id === currentUserId}
                canManage={canManage}
                csrfToken={csrfToken}
              />
            ))}
          </ul>
          <Pagination
            page={page}
            pageSize={PAGE_SIZE}
            total={data.total}
            onPageChange={setPage}
            label="Staff pages"
          />
        </>
      )}
    </Panel>
  );
}
