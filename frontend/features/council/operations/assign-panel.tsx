"use client";

import { useId, useMemo, useState } from "react";

import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { errorMessage, fieldErrorsFrom } from "@/lib/api-client";

import { assignIssue } from "./api";
import { useAllMembers, useDepartments } from "./hooks";
import type { StaffIssueDetail } from "./types";
import { useIssueMutation } from "./use-issue-mutation";

const WORKING_ROLES = new Set(["department_manager", "maintenance_officer"]);

export function AssignPanel({ councilId, issue, csrfToken }: { councilId: string; issue: StaffIssueDetail; csrfToken: string }) {
  const departments = useDepartments(councilId);
  const members = useAllMembers(councilId);
  const [departmentId, setDepartmentId] = useState(issue.assignment?.department.id ?? "");
  const [assigneeId, setAssigneeId] = useState(issue.assignment?.assignee?.id ?? "");
  const [note, setNote] = useState("");
  const headingId = useId();
  const mutation = useIssueMutation(councilId, issue.id, () =>
    assignIssue(
      councilId,
      issue.id,
      { department_id: departmentId, assignee_user_id: assigneeId || undefined, note: note.trim() || undefined },
      csrfToken,
    ),
  );
  const fieldErrors = fieldErrorsFrom(mutation.error);
  const people = useMemo(
    () => (members.data ?? []).filter((m) => WORKING_ROLES.has(m.role) && m.department?.id === departmentId),
    [members.data, departmentId],
  );
  const reassigning = Boolean(issue.assignment);

  return (
    <section aria-labelledby={headingId} className="space-y-3 rounded-[var(--radius-panel)] border border-line bg-surface p-4">
      <h2 id={headingId} className="text-base font-semibold">
        {reassigning ? "Reassign" : "Assign"}
      </h2>
      <form
        className="space-y-3"
        onSubmit={(event) => {
          event.preventDefault();
          mutation.mutate(undefined, { onSuccess: () => setNote("") });
        }}
      >
        <Field label="Department" error={fieldErrors.department_id}>
          <Select
            value={departmentId}
            onChange={(e) => {
              setDepartmentId(e.target.value);
              setAssigneeId("");
            }}
            required
          >
            <option value="">Choose a department</option>
            {(departments.data ?? []).filter((d) => d.is_active).map((d) => (
              <option key={d.id} value={d.id}>{d.name}</option>
            ))}
          </Select>
        </Field>
        <Field label="Officer (optional)" hint="Managers and maintenance officers of the chosen department." error={fieldErrors.assignee_user_id}>
          <Select value={assigneeId} onChange={(e) => setAssigneeId(e.target.value)} disabled={!departmentId}>
            <option value="">The whole department</option>
            {people.map((m) => (
              <option key={m.user_id} value={m.user_id}>{m.full_name}</option>
            ))}
          </Select>
        </Field>
        {!reassigning ? (
          <Field label="Message to the reporter (optional)" hint={'If left empty, the reporter is told "Assigned to the … department."'}>
            <Textarea value={note} onChange={(e) => setNote(e.target.value)} maxLength={1000} rows={2} />
          </Field>
        ) : null}
        {mutation.isError && !Object.keys(fieldErrors).length ? <Alert tone="error">{errorMessage(mutation.error)}</Alert> : null}
        {mutation.isSuccess ? <Alert tone="success">Assignment saved.</Alert> : null}
        <Button type="submit" disabled={!departmentId || mutation.isPending}>
          {mutation.isPending ? "Saving…" : reassigning ? "Save assignment" : "Assign"}
        </Button>
      </form>
    </section>
  );
}
