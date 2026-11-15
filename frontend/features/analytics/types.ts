/** Mirrors backend app/schemas/analytics.py. */
export interface CategoryCount {
  code: string;
  name: string;
  received: number;
  fixed: number;
}

export interface DepartmentLoad {
  id: string;
  name: string;
  assigned: number;
  in_progress: number;
  oldest_open_days: number | null;
}

export type PeriodDays = 30 | 90 | 365;

export interface Performance {
  period_days: PeriodDays;
  since: string;
  received: number;
  open_now: number;
  awaiting_review: number;
  awaiting_assignment: number;
  fixed_in_period: number;
  median_hours_to_first_response: number | null;
  median_hours_to_verify: number | null;
  median_hours_to_fix: number | null;
  categories: CategoryCount[];
  departments: DepartmentLoad[];
  feedback_responses: number;
  feedback_fixed: number;
}

export interface PublicCouncilStats {
  id: string;
  slug: string;
  name: string;
  published: number;
  open: number;
  fixed: number;
  median_days_to_fix: number | null;
}

export interface PublicStats {
  published: number;
  open: number;
  fixed: number;
  median_days_to_fix: number | null;
  categories: CategoryCount[];
  councils: PublicCouncilStats[];
}
