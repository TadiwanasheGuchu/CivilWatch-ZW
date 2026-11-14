"use client";

import { ShieldAlert } from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";

import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { LoadError, LoadingRows } from "@/components/ui/page-states";
import { RequireSession } from "@/features/authentication/require-session";
import type { SessionData } from "@/features/authentication/types";
import { ApiError, errorMessage } from "@/lib/api-client";
import { cn } from "@/lib/utils";

import { useWorkspace } from "./hooks";
import { ROLE_LABELS } from "./labels";
import type { Workspace } from "./types";
import { WorkspaceSwitcher } from "./workspace-switcher";

type Tab = "staff" | "audit";

interface CouncilShellProps {
  councilId: string;
  tab: Tab;
  children: (workspace: Workspace, session: SessionData) => ReactNode;
}

export function CouncilShell(props: CouncilShellProps) {
  return <RequireSession>{(session) => <CouncilWorkspace {...props} session={session} />}</RequireSession>;
}

function CouncilWorkspace({ councilId, tab, children, session }: CouncilShellProps & { session: SessionData }) {
  const { data: workspace, isPending, isError, error, refetch } = useWorkspace(councilId);

  if (isPending) return <LoadingRows label="Loading council workspace" />;
  if (isError) {
    if (error instanceof ApiError && (error.status === 403 || error.status === 404)) {
      return (
        <Alert tone="error" title={error.status === 404 ? "Council not found" : "No access to this council"}>
          {error.status === 404
            ? "This council does not exist or is no longer active."
            : "Your account is not a member of this council's staff. Ask a council administrator if you need access."}{" "}
          <Link href="/account" className="font-medium text-teal underline underline-offset-2">
            Back to your account
          </Link>
        </Alert>
      );
    }
    return <LoadError message={errorMessage(error)} onRetry={() => void refetch()} />;
  }

  const tabs: Array<{ id: Tab; label: string; href: string; visible: boolean }> = [
    { id: "staff", label: "Staff", href: `/council/${councilId}`, visible: workspace.permissions.includes("members.view") },
    { id: "audit", label: "Audit log", href: `/council/${councilId}/audit`, visible: workspace.permissions.includes("audit.view") },
  ];

  return (
    <div className="space-y-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div className="min-w-0">
          <p className="text-sm font-medium text-teal">Council workspace</p>
          <h1 className="mt-1 text-2xl font-bold break-words">{workspace.council.name}</h1>
          <div className="mt-2">
            {workspace.role ? (
              <Badge tone="brand">{ROLE_LABELS[workspace.role]}</Badge>
            ) : workspace.via_platform_admin ? (
              <Badge tone="navy">Platform administrator</Badge>
            ) : null}
          </div>
        </div>
        <WorkspaceSwitcher currentCouncilId={councilId} />
      </div>

      {workspace.via_platform_admin ? (
        <p className="flex gap-2 rounded-[var(--radius-control)] border border-line bg-surface px-4 py-3 text-sm text-navy-soft">
          <ShieldAlert aria-hidden="true" className="mt-0.5 size-4 shrink-0 text-navy" />
          You are acting as a platform administrator. You can manage this council&apos;s staff, and every
          change is recorded in its audit log.
        </p>
      ) : null}

      <nav aria-label="Council sections" className="flex gap-1 border-b border-line">
        {tabs
          .filter((item) => item.visible)
          .map((item) => (
            <Link
              key={item.id}
              href={item.href}
              aria-current={item.id === tab ? "page" : undefined}
              className={cn(
                "inline-flex min-h-11 items-center border-b-2 px-3 text-sm font-medium",
                item.id === tab ? "border-teal text-navy" : "border-transparent text-slate hover:text-navy",
              )}
            >
              {item.label}
            </Link>
          ))}
      </nav>

      {children(workspace, session)}
    </div>
  );
}
