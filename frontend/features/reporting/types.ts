/** Mirrors backend schemas in app/schemas/issues.py. */
import type { CouncilSummary } from "@/features/council/types";

export type IssueStatus =
  | "SUBMITTED"
  | "UNDER_REVIEW"
  | "NEEDS_INFORMATION"
  | "VERIFIED"
  | "ASSIGNED"
  | "IN_PROGRESS"
  | "RESOLVED"
  | "REJECTED"
  | "DUPLICATE"
  | "CLOSED";

export type Visibility = "PUBLIC" | "PRIVATE";

export interface Category {
  id: string;
  code: string;
  name: string;
  description: string;
}

export interface Photo {
  id: string;
  url: string;
  thumbnail_url: string;
  width: number;
  height: number;
}

export interface StatusChange {
  from_status: IssueStatus | null;
  to_status: IssueStatus;
  created_at: string;
  /** The council's message to the reporter, or the reporter's answer. Only sent to the reporter. */
  note?: string | null;
}

export interface PublicIssue {
  id: string;
  reference: string;
  council: CouncilSummary;
  category: { code: string; name: string };
  title: string;
  description: string;
  status: IssueStatus;
  latitude: number;
  longitude: number;
  location_description: string | null;
  created_at: string;
  updated_at: string;
  photo_count: number;
  cover_thumbnail_url: string | null;
}

export interface OwnIssue extends PublicIssue {
  visibility: Visibility;
  is_published: boolean;
}

export interface IssueDetail extends PublicIssue {
  history: StatusChange[];
  photos: Photo[];
  /** Repair evidence added by the council. */
  repair_photos: Photo[];
  /** Present only when the viewer is the reporter. */
  visibility?: Visibility;
  is_published?: boolean;
}

export interface NewReport {
  council_id: string;
  category_id: string;
  title: string;
  description: string;
  latitude: number;
  longitude: number;
  location_description: string | null;
  visibility: Visibility;
}
