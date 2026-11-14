"use client";

import { ArrowLeft, ArrowRight } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { LoadingRows } from "@/components/ui/page-states";

import { STEPS, type StepId } from "../draft";
import { CategoryStep } from "./step-category";
import { DetailsStep } from "./step-details";
import { LocationStep } from "./step-location";
import { PhotosStep } from "./step-photos";
import { ReviewStep } from "./step-review";
import { VisibilityStep } from "./step-visibility";
import { useReportDraft } from "./use-report-draft";
import { type StepErrors, validateStep } from "./validation";

const TITLES: Record<StepId, string> = {
  category: "What kind of problem is it?",
  details: "Describe the problem",
  photos: "Add photos",
  location: "Where is it?",
  visibility: "Who can see this report?",
  review: "Check and send",
};

export function ReportWizard() {
  const { draft, restored, persistent, update, replace, discard } = useReportDraft();
  const [errors, setErrors] = useState<StepErrors>({});
  const heading = useRef<HTMLHeadingElement>(null);
  const firstRender = useRef(true);
  const step = draft?.step ?? "category";
  const index = STEPS.indexOf(step);

  // Move focus to the new step's heading so screen readers announce it.
  useEffect(() => {
    if (firstRender.current) {
      firstRender.current = false;
      return;
    }
    heading.current?.focus();
    window.scrollTo({ top: 0 });
  }, [step]);

  if (!draft) return <LoadingRows label="Loading your report" rows={4} />;

  const goTo = (target: StepId) => {
    setErrors({});
    update({ step: target }, { immediate: true });
  };

  function next() {
    const found = validateStep(step, draft!);
    setErrors(found);
    if (Object.keys(found).length) return;
    goTo(STEPS[index + 1]!);
  }

  const lockedAfterSending = Boolean(draft.submittedIssueId);

  return (
    <div className="pb-24">
      {restored && !lockedAfterSending ? (
        <Alert tone="info" className="mb-4" title="We restored your unsent report">
          <button type="button" className="font-medium text-teal underline underline-offset-2" onClick={() => void discard()}>
            Discard it and start again
          </button>
        </Alert>
      ) : null}
      {!persistent ? (
        <Alert tone="info" className="mb-4">
          This browser cannot save drafts, so keep this page open until you send the report.
        </Alert>
      ) : null}

      <p className="text-sm font-medium text-teal">
        Step {index + 1} of {STEPS.length}
      </p>
      <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-line" aria-hidden="true">
        <div className="h-full bg-teal transition-[width]" style={{ width: `${((index + 1) / STEPS.length) * 100}%` }} />
      </div>
      <h1 ref={heading} tabIndex={-1} className="mt-4 text-2xl font-bold outline-none">
        {TITLES[step]}
      </h1>

      <div className="mt-5">
        {step === "category" ? <CategoryStep draft={draft} update={update} errors={errors} /> : null}
        {step === "details" ? <DetailsStep draft={draft} update={update} errors={errors} /> : null}
        {step === "photos" ? <PhotosStep draft={draft} update={update} errors={errors} /> : null}
        {step === "location" ? <LocationStep draft={draft} update={update} errors={errors} /> : null}
        {step === "visibility" ? <VisibilityStep draft={draft} update={update} errors={errors} /> : null}
        {step === "review" ? <ReviewStep draft={draft} replace={replace} discard={discard} goTo={goTo} /> : null}
      </div>

      {step !== "review" ? (
        <div className="fixed inset-x-0 bottom-0 z-20 border-t border-line bg-surface/95 px-4 pt-3 pb-[max(0.75rem,env(safe-area-inset-bottom))] backdrop-blur-sm">
          <div className="mx-auto flex max-w-2xl gap-2">
            {index > 0 ? (
              <Button variant="secondary" size="lg" onClick={() => goTo(STEPS[index - 1]!)}>
                <ArrowLeft aria-hidden="true" />
                Back
              </Button>
            ) : null}
            <Button size="lg" className="flex-1" onClick={next}>
              {step === "visibility" ? "Review" : "Next"}
              <ArrowRight aria-hidden="true" />
            </Button>
          </div>
        </div>
      ) : (
        <Button variant="ghost" className="mt-4" onClick={() => goTo("visibility")} disabled={lockedAfterSending}>
          <ArrowLeft aria-hidden="true" />
          Back
        </Button>
      )}
    </div>
  );
}
