"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { EmptyState, LoadError, LoadingRows } from "@/components/ui/page-states";
import { Panel } from "@/components/ui/panel";
import { CouncilShell } from "@/features/council/council-shell";
import { errorMessage, fieldErrorsFrom } from "@/lib/api-client";

import { createDepartment, opsKeys, updateDepartment } from "./api";
import { useDepartments } from "./hooks";
import type { Department } from "./types";

export function DepartmentsView({ councilId }: { councilId: string }) {
  return (
    <CouncilShell councilId={councilId} tab="departments">
      {(workspace, session) => (
        <Departments
          councilId={councilId}
          canManage={workspace.permissions.includes("departments.manage")}
          csrfToken={session.csrf_token}
        />
      )}
    </CouncilShell>
  );
}

function Departments({ councilId, canManage, csrfToken }: { councilId: string; canManage: boolean; csrfToken: string }) {
  const { data, isPending, isError, error, refetch } = useDepartments(councilId);
  return (
    <div className="space-y-6">
      {canManage ? (
        <Panel title="Add a department" description="Reports are assigned to departments, and managers and officers belong to one.">
          <CreateDepartment councilId={councilId} csrfToken={csrfToken} />
        </Panel>
      ) : null}
      <Panel title="Departments">
        {isPending ? (
          <LoadingRows label="Loading departments" />
        ) : isError ? (
          <LoadError message={errorMessage(error)} onRetry={() => void refetch()} />
        ) : data.length === 0 ? (
          <EmptyState title="No departments yet">
            {canManage ? "Add the first one above." : "A council administrator can add departments."}
          </EmptyState>
        ) : (
          <ul className="-mx-4 divide-y divide-line border-t border-line sm:-mx-5">
            {data.map((department) => (
              <DepartmentRow key={`${department.id}-${department.name}-${department.is_active}`} councilId={councilId} department={department} canManage={canManage} csrfToken={csrfToken} />
            ))}
          </ul>
        )}
      </Panel>
    </div>
  );
}

function CreateDepartment({ councilId, csrfToken }: { councilId: string; csrfToken: string }) {
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const create = useMutation({
    mutationFn: () => createDepartment(councilId, { name: name.trim(), description: description.trim() || undefined }, csrfToken),
    onSuccess: () => {
      setName("");
      setDescription("");
      void queryClient.invalidateQueries({ queryKey: opsKeys.departments(councilId) });
    },
  });
  const errors = fieldErrorsFrom(create.error);
  return (
    <form
      className="space-y-3"
      onSubmit={(event) => {
        event.preventDefault();
        create.mutate();
      }}
    >
      <div className="grid gap-3 md:grid-cols-2">
        <Field label="Name" hint="For example: Roads" error={errors.name}>
          <Input value={name} onChange={(e) => setName(e.target.value)} maxLength={80} />
        </Field>
        <Field label="Description (optional)" error={errors.description}>
          <Input value={description} onChange={(e) => setDescription(e.target.value)} maxLength={240} />
        </Field>
      </div>
      {create.isError && !Object.keys(errors).length ? <Alert tone="error">{errorMessage(create.error)}</Alert> : null}
      <Button type="submit" disabled={name.trim().length < 2 || create.isPending}>
        {create.isPending ? "Adding…" : "Add department"}
      </Button>
    </form>
  );
}

function DepartmentRow({ councilId, department, canManage, csrfToken }: { councilId: string; department: Department; canManage: boolean; csrfToken: string }) {
  const queryClient = useQueryClient();
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState(department.name);
  const save = useMutation({
    mutationFn: (body: { name?: string; is_active?: boolean }) => updateDepartment(councilId, department.id, body, csrfToken),
    onSuccess: () => {
      setEditing(false);
      void queryClient.invalidateQueries({ queryKey: opsKeys.departments(councilId) });
    },
  });
  return (
    <li className="space-y-2 px-4 py-3 sm:px-5">
      {editing ? (
        <form
          className="flex flex-col gap-2 sm:flex-row"
          onSubmit={(event) => {
            event.preventDefault();
            save.mutate({ name: name.trim() });
          }}
        >
          <label className="sr-only" htmlFor={`dept-${department.id}`}>Department name</label>
          <Input id={`dept-${department.id}`} value={name} onChange={(e) => setName(e.target.value)} maxLength={80} />
          <div className="flex gap-2">
            <Button type="submit" disabled={save.isPending}>Save</Button>
            <Button type="button" variant="ghost" onClick={() => { setEditing(false); setName(department.name); }}>Cancel</Button>
          </div>
        </form>
      ) : (
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="min-w-0">
            <p className="font-medium break-words">
              {department.name} {!department.is_active ? <Badge className="ml-1">Inactive</Badge> : null}
            </p>
            {department.description ? <p className="text-sm text-slate">{department.description}</p> : null}
          </div>
          {canManage ? (
            <div className="flex gap-1">
              <Button variant="ghost" onClick={() => setEditing(true)} aria-label={`Rename ${department.name}`}>Rename</Button>
              <Button variant="ghost" onClick={() => save.mutate({ is_active: !department.is_active })} disabled={save.isPending}>
                {department.is_active ? "Deactivate" : "Reactivate"}
              </Button>
            </div>
          ) : null}
        </div>
      )}
      {save.isError ? <p role="alert" className="text-sm font-medium text-red-text">{errorMessage(save.error)}</p> : null}
    </li>
  );
}
