import type { Visibility } from "./types";

export const STEPS = ["category", "details", "photos", "location", "visibility", "review"] as const;
export type StepId = (typeof STEPS)[number];

export const MAX_PHOTOS = 5;

export interface DraftPhoto {
  /** Local id, stable across reloads. */
  id: string;
  blob: Blob;
  /** Set once the photo has reached the server, so retries skip it. */
  uploadedPhotoId: string | null;
}

export interface ReportDraft {
  version: 1;
  step: StepId;
  categoryId: string | null;
  title: string;
  description: string;
  photos: DraftPhoto[];
  councilId: string | null;
  /** True while the council was chosen automatically from the pin, so a moved pin may update it. */
  councilAutoSelected?: boolean;
  latitude: number | null;
  longitude: number | null;
  locationDescription: string;
  visibility: Visibility | null;
  /** Set once the report exists on the server; a retry then only sends missing photos. */
  submittedIssueId: string | null;
  updatedAt: string;
}

export function emptyDraft(): ReportDraft {
  return {
    version: 1,
    step: "category",
    categoryId: null,
    title: "",
    description: "",
    photos: [],
    councilId: null,
    latitude: null,
    longitude: null,
    locationDescription: "",
    visibility: null,
    submittedIssueId: null,
    updatedAt: new Date().toISOString(),
  };
}

/** True when the draft holds anything worth offering to restore. */
export function hasContent(draft: ReportDraft): boolean {
  return Boolean(
    draft.categoryId ||
      draft.title.trim() ||
      draft.description.trim() ||
      draft.photos.length ||
      draft.latitude !== null ||
      draft.submittedIssueId,
  );
}
