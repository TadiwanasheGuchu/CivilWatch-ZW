"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ThumbsDown, ThumbsUp } from "lucide-react";
import { useId, useState } from "react";

import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { errorMessage } from "@/lib/api-client";

import { giveFeedback, reportKeys } from "./api";
import type { IssueDetail } from "./types";

/** "Was the problem fixed?" — asked once the council resolves a report. */
export function FixFeedback({ issue, csrfToken }: { issue: IssueDetail; csrfToken: string }) {
  const queryClient = useQueryClient();
  const [fixed, setFixed] = useState<boolean | null>(null);
  const [comment, setComment] = useState("");
  const headingId = useId();
  const commentId = useId();
  const send = useMutation({
    mutationFn: () => giveFeedback(issue.id, { fixed: fixed!, comment: comment.trim() || undefined }, csrfToken),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: reportKeys.detail(issue.id) }),
  });

  if (issue.feedback) {
    return (
      <Alert tone={issue.feedback.fixed ? "success" : "info"} title="Thank you for your feedback">
        You told the council the problem {issue.feedback.fixed ? "was fixed" : "was not fixed"}.
        {issue.feedback.comment ? <span className="mt-1 block whitespace-pre-line">“{issue.feedback.comment}”</span> : null}
      </Alert>
    );
  }

  return (
    <section aria-labelledby={headingId} className="space-y-3 rounded-[var(--radius-panel)] border-l-4 border-teal bg-surface p-4">
      <h2 id={headingId} className="text-base font-semibold">
        Was the problem fixed?
      </h2>
      <p className="text-sm text-navy-soft">Your answer goes to the council. It is not shown publicly.</p>
      <div role="group" aria-label="Was the problem fixed?" className="grid grid-cols-2 gap-2 sm:max-w-sm">
        <Button variant={fixed === true ? "primary" : "secondary"} aria-pressed={fixed === true} onClick={() => setFixed(true)}>
          <ThumbsUp aria-hidden="true" /> Yes, fixed
        </Button>
        <Button variant={fixed === false ? "primary" : "secondary"} aria-pressed={fixed === false} onClick={() => setFixed(false)}>
          <ThumbsDown aria-hidden="true" /> No
        </Button>
      </div>
      {fixed !== null ? (
        <form
          className="space-y-2"
          onSubmit={(event) => {
            event.preventDefault();
            send.mutate();
          }}
        >
          <label htmlFor={commentId} className="block text-sm font-medium">
            {fixed ? "Anything to add? (optional)" : "What is still wrong? (optional)"}
          </label>
          <Textarea id={commentId} value={comment} onChange={(e) => setComment(e.target.value)} maxLength={1000} rows={3} />
          {send.isError ? <Alert tone="error">{errorMessage(send.error)}</Alert> : null}
          <Button type="submit" disabled={send.isPending}>
            {send.isPending ? "Sending…" : "Send to the council"}
          </Button>
        </form>
      ) : null}
    </section>
  );
}
