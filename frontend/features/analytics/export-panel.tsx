"use client";

import { useMutation } from "@tanstack/react-query";
import { Download } from "lucide-react";
import { useState } from "react";

import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Panel } from "@/components/ui/panel";
import { errorMessage } from "@/lib/api-client";

import { downloadExport } from "./api";

function isoDate(date: Date): string {
  return date.toISOString().slice(0, 10);
}

export function ExportPanel({ councilId }: { councilId: string }) {
  const today = new Date();
  const [from, setFrom] = useState(isoDate(new Date(today.getTime() - 29 * 86_400_000)));
  const [to, setTo] = useState(isoDate(today));
  const invalid = !from || !to || to < from;

  const download = useMutation({
    mutationFn: () => downloadExport(councilId, from, to),
    onSuccess: ({ blob, filename }) => {
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = filename;
      document.body.append(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    },
  });

  return (
    <Panel
      title="Export reports"
      description="A spreadsheet (CSV) of reports received between two dates, at most a year. It has no reporter names or contact details, and each export is recorded in the audit log."
    >
      <form
        noValidate
        className="space-y-4"
        onSubmit={(event) => {
          event.preventDefault();
          if (!invalid) download.mutate();
        }}
      >
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label="From">
            <Input type="date" value={from} max={to || undefined} onChange={(e) => setFrom(e.target.value)} required />
          </Field>
          <Field label="To" error={from && to && to < from ? "The end date must not be before the start date." : undefined}>
            <Input type="date" value={to} min={from || undefined} onChange={(e) => setTo(e.target.value)} required />
          </Field>
        </div>
        {download.isError ? <Alert tone="error">{errorMessage(download.error)}</Alert> : null}
        {download.isSuccess ? <Alert tone="success">Your export has been downloaded.</Alert> : null}
        <Button type="submit" variant="secondary" disabled={invalid || download.isPending}>
          <Download aria-hidden="true" />
          {download.isPending ? "Preparing…" : "Download CSV"}
        </Button>
      </form>
    </Panel>
  );
}
