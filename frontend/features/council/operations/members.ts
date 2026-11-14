import type { Member } from "@/features/council/types";
import { apiGet } from "@/lib/api-client";

import type { Page } from "@/features/council/types";

/** All active staff (councils have at most a few hundred), for choosing an assignee. */
export async function fetchMembersAll(councilId: string, signal?: AbortSignal): Promise<Member[]> {
  const members: Member[] = [];
  for (let page = 1; page <= 20; page += 1) {
    const result = await apiGet<Page<Member>>(
      `/councils/${encodeURIComponent(councilId)}/members?page=${page}&page_size=100`,
      { signal },
    );
    members.push(...result.items);
    if (members.length >= result.total || result.items.length === 0) break;
  }
  return members;
}
