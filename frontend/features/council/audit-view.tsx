"use client";

import { useState } from "react";

import { EmptyState, LoadError, LoadingRows } from "@/components/ui/page-states";
import { Pagination } from "@/components/ui/pagination";
import { Panel } from "@/components/ui/panel";
import { errorMessage } from "@/lib/api-client";

import { PAGE_SIZE } from "./api";
import { CouncilShell } from "./council-shell";
import { useAuditLog } from "./hooks";
import { describeAuditAction } from "./labels";

const timeFormat = new Intl.DateTimeFormat("en-GB", { dateStyle: "medium", timeStyle: "short" });

export function AuditView({ councilId }: { councilId: string }) {
  return (
    <CouncilShell councilId={councilId} tab="audit">
      {(workspace) =>
        workspace.permissions.includes("audit.view") ? (
          <AuditList councilId={councilId} />
        ) : (
          <EmptyState title="Audit log unavailable">Only council administrators can see the audit log.</EmptyState>
        )
      }
    </CouncilShell>
  );
}

function AuditList({ councilId }: { councilId: string }) {
  const [page, setPage] = useState(1);
  const { data, isPending, isError, error, refetch } = useAuditLog(councilId, page, true);

  return (
    <Panel title="Audit log" description="Every staff and administrative change in this council, newest first.">
      {isPending ? (
        <LoadingRows label="Loading audit log" />
      ) : isError ? (
        <LoadError message={errorMessage(error)} onRetry={() => void refetch()} />
      ) : data.items.length === 0 ? (
        <EmptyState title="No activity recorded yet" />
      ) : (
        <>
          <ol className="-mx-4 divide-y divide-line border-t border-line sm:-mx-5">
            {data.items.map((entry) => (
              <li key={entry.id} className="px-4 py-3 sm:px-5">
                <p className="text-sm font-medium">{describeAuditAction(entry.action, entry.details)}</p>
                <p className="mt-0.5 text-sm text-slate">
                  {entry.actor_name ?? "System"}
                  {entry.details.via_platform_admin === true ? " (platform administrator)" : ""} ·{" "}
                  <time dateTime={entry.occurred_at} className="tabular">
                    {timeFormat.format(new Date(entry.occurred_at))}
                  </time>
                </p>
              </li>
            ))}
          </ol>
          <Pagination
            page={page}
            pageSize={PAGE_SIZE}
            total={data.total}
            onPageChange={setPage}
            label="Audit log pages"
          />
        </>
      )}
    </Panel>
  );
}
