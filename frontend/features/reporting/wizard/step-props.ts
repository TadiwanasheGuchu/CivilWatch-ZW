import type { ReportDraft } from "../draft";
import type { StepErrors } from "./validation";

export interface StepProps {
  draft: ReportDraft;
  update: (patch: Partial<ReportDraft>) => void;
  errors: StepErrors;
}
