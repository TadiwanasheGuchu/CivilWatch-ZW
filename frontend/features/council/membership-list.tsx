"use client";

import { Building2, ChevronRight } from "lucide-react";
import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { LoadError, LoadingRows } from "@/components/ui/page-states";
import { errorMessage } from "@/lib/api-client";

import { useMyMemberships } from "./hooks";
import { ROLE_LABELS } from "./labels";

/** The councils where the signed-in user works. Renders nothing for residents. */
export function MembershipList() {
  const { data, isPending, isError, error, refetch } = useMyMemberships();
  if (isPending) return <LoadingRows label="Loading your councils" rows={1} />;
  if (isError) return <LoadError message={errorMessage(error)} onRetry={() => void refetch()} />;
  if (data.length === 0) return null;

  return (
    <section aria-labelledby="my-councils-heading">
      <h2 id="my-councils-heading" className="text-lg font-semibold">
        Your councils
      </h2>
      <p className="mt-0.5 text-sm text-navy-soft">Open a council workspace to manage its work.</p>
      <ul className="mt-3 divide-y divide-line overflow-hidden rounded-[var(--radius-panel)] border border-line bg-surface">
        {data.map((membership) => (
          <li key={membership.id}>
            <Link
              href={`/council/${membership.council.id}`}
              className="flex min-h-14 items-center gap-3 px-4 py-3 hover:bg-mist"
            >
              <Building2 aria-hidden="true" className="size-5 shrink-0 text-teal" />
              <span className="min-w-0 flex-1">
                <span className="block truncate font-medium">{membership.council.name}</span>
                <Badge tone="brand" className="mt-1">
                  {ROLE_LABELS[membership.role]}
                </Badge>
              </span>
              <ChevronRight aria-hidden="true" className="size-5 shrink-0 text-slate" />
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}
