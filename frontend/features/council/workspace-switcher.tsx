"use client";

import { useRouter } from "next/navigation";
import { useId } from "react";

import { Select } from "@/components/ui/select";

import { useMyMemberships } from "./hooks";

/** Lets staff of several councils switch workspace. Lists only their own memberships. */
export function WorkspaceSwitcher({ currentCouncilId }: { currentCouncilId: string }) {
  const { data } = useMyMemberships();
  const router = useRouter();
  const id = useId();
  if (!data || data.length < 2) return null;
  return (
    <div className="w-full sm:w-64">
      <label htmlFor={id} className="mb-1.5 block text-sm font-medium text-navy">
        Switch council
      </label>
      <Select
        id={id}
        value={currentCouncilId}
        onChange={(event) => router.push(`/council/${event.target.value}`)}
      >
        {data.map((membership) => (
          <option key={membership.id} value={membership.council.id}>
            {membership.council.name}
          </option>
        ))}
      </Select>
    </div>
  );
}
