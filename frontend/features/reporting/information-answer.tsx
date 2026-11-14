"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { MessageCircleQuestion } from "lucide-react";
import { useId, useState } from "react";

import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { errorMessage } from "@/lib/api-client";

import { provideInformation, reportKeys } from "./api";
import type { IssueDetail } from "./types";

/** Shown to the reporter when the council has asked them a question. */
export function InformationAnswer({ issue, csrfToken }: { issue: IssueDetail; csrfToken: string }) {
  const queryClient = useQueryClient();
  const [answer, setAnswer] = useState("");
  const headingId = useId();
  const inputId = useId();
  const question = [...issue.history].reverse().find((h) => h.to_status === "NEEDS_INFORMATION")?.note;
  const send = useMutation({
    mutationFn: () => provideInformation(issue.id, answer.trim(), csrfToken),
    onSuccess: (detail) => {
      queryClient.setQueryData(reportKeys.detail(issue.id), detail);
      void queryClient.invalidateQueries({ queryKey: reportKeys.mineRoot });
    },
  });

  return (
    <section aria-labelledby={headingId} className="space-y-3 rounded-[var(--radius-panel)] border-l-4 border-amber bg-surface p-4">
      <h2 id={headingId} className="flex items-center gap-2 text-base font-semibold">
        <MessageCircleQuestion aria-hidden="true" className="size-5 text-amber-text" />
        The council needs more information
      </h2>
      {question ? <p className="rounded bg-mist px-3 py-2 whitespace-pre-line break-words">{question}</p> : null}
      <form
        className="space-y-2"
        onSubmit={(event) => {
          event.preventDefault();
          send.mutate();
        }}
      >
        <label htmlFor={inputId} className="block text-sm font-medium">
          Your answer
        </label>
        <Textarea id={inputId} value={answer} onChange={(e) => setAnswer(e.target.value)} maxLength={1000} rows={3} />
        <p className="text-sm text-slate">You can also add photos below before sending.</p>
        {send.isError ? <Alert tone="error">{errorMessage(send.error)}</Alert> : null}
        <Button type="submit" disabled={!answer.trim() || send.isPending}>
          {send.isPending ? "Sending…" : "Send answer"}
        </Button>
      </form>
    </section>
  );
}
