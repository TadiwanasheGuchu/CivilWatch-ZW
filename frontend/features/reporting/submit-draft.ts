import type { ReportDraft } from "./draft";
import type { NewReport, OwnIssue, Photo } from "./types";

export interface SubmitDependencies {
  submitReport: (report: NewReport) => Promise<OwnIssue>;
  uploadPhoto: (issueId: string, blob: Blob, onProgress: (fraction: number) => void) => Promise<Photo>;
  /** Persist progress after each step, so a reload or crash never repeats work. */
  saveDraft: (draft: ReportDraft) => Promise<void>;
  onPhotoProgress?: (photoId: string, fraction: number) => void;
}

export interface SubmitResult {
  issueId: string;
  draft: ReportDraft;
  /** Local ids of photos that still need uploading. */
  failedPhotoIds: string[];
  lastError: unknown;
}

export function toNewReport(draft: ReportDraft): NewReport {
  if (
    !draft.categoryId ||
    !draft.councilId ||
    draft.latitude === null ||
    draft.longitude === null ||
    !draft.visibility
  ) {
    throw new Error("The report is not complete.");
  }
  return {
    council_id: draft.councilId,
    category_id: draft.categoryId,
    title: draft.title.trim(),
    description: draft.description.trim(),
    latitude: draft.latitude,
    longitude: draft.longitude,
    location_description: draft.locationDescription.trim() || null,
    visibility: draft.visibility,
  };
}

/**
 * Send a draft. Safe to call again after any failure:
 * - the report is created at most once (its id is saved in the draft);
 * - photos already uploaded are skipped; the rest are retried.
 * Creating the report throws on failure, leaving the draft untouched.
 */
export async function submitDraft(initial: ReportDraft, deps: SubmitDependencies): Promise<SubmitResult> {
  let draft = initial;
  if (!draft.submittedIssueId) {
    const issue = await deps.submitReport(toNewReport(draft));
    draft = { ...draft, submittedIssueId: issue.id, updatedAt: new Date().toISOString() };
    await deps.saveDraft(draft);
  }
  const issueId = draft.submittedIssueId as string;

  const failedPhotoIds: string[] = [];
  let lastError: unknown = null;
  for (const photo of draft.photos) {
    if (photo.uploadedPhotoId) continue;
    try {
      const uploaded = await deps.uploadPhoto(issueId, photo.blob, (fraction) =>
        deps.onPhotoProgress?.(photo.id, fraction),
      );
      draft = {
        ...draft,
        photos: draft.photos.map((p) => (p.id === photo.id ? { ...p, uploadedPhotoId: uploaded.id } : p)),
        updatedAt: new Date().toISOString(),
      };
      await deps.saveDraft(draft);
    } catch (error) {
      failedPhotoIds.push(photo.id);
      lastError = error;
    }
  }
  return { issueId, draft, failedPhotoIds, lastError };
}
