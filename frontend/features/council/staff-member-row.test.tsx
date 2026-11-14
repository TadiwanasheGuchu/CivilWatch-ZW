import { fireEvent, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { queueResponses, renderWithClient } from "@/tests/render";

import { StaffMemberRow } from "./staff-member-row";
import type { Member } from "./types";

const member: Member = {
  membership_id: "m1",
  user_id: "u2",
  full_name: "Rumbi Officer",
  email: "rumbi@example.com",
  role: "verification_officer",
  department: null,
  granted_at: "2026-11-14T08:00:00Z",
};

function renderRow(canManage = true) {
  return renderWithClient(
    <ul>
      <StaffMemberRow councilId="c1" member={member} isSelf={false} canManage={canManage} csrfToken="csrf" />
    </ul>,
  );
}

afterEach(() => vi.unstubAllGlobals());

describe("StaffMemberRow", () => {
  it("shows a read-only role badge without manage permission", () => {
    renderRow(false);
    expect(screen.getByText("Verification officer")).toBeInTheDocument();
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  it("asks for confirmation before removing", async () => {
    const fetchMock = queueResponses({ status: 204 });
    renderRow();
    fireEvent.click(screen.getByRole("button", { name: "Remove from staff" }));
    expect(fetchMock).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Remove" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toMatch(/\/councils\/c1\/members\/m1$/);
    expect(init.method).toBe("DELETE");
    expect(init.headers).toMatchObject({ "X-CSRF-Token": "csrf" });
  });

  it("saves a changed role only when asked, and shows API refusals", async () => {
    const fetchMock = queueResponses({
      status: 409,
      body: {
        error: {
          code: "last_council_admin",
          message: "A council must keep at least one administrator. Appoint another first.",
          details: null,
          request_id: "r",
        },
      },
    });
    renderRow();
    fireEvent.change(screen.getByLabelText("Role for Rumbi Officer"), {
      target: { value: "maintenance_officer" },
    });
    expect(fetchMock).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Save changes" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("keep at least one administrator");
    expect(JSON.parse((fetchMock.mock.calls[0] as [string, RequestInit])[1].body as string)).toEqual({
      role: "maintenance_officer",
    });
  });
});
