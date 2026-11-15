/** Human durations for medians given in hours. */
export function formatHours(hours: number | null): string {
  if (hours === null) return "No data yet";
  if (hours < 1) return "Under an hour";
  if (hours < 48) return `${Math.round(hours)} hour${Math.round(hours) === 1 ? "" : "s"}`;
  return formatDays(hours / 24);
}

export function formatDays(days: number | null): string {
  if (days === null) return "No data yet";
  if (days < 1) return "Under a day";
  const rounded = days < 10 ? Math.round(days * 10) / 10 : Math.round(days);
  return `${rounded} day${rounded === 1 ? "" : "s"}`;
}

/** Whole-number share, or null when there is nothing to divide. */
export function percent(part: number, whole: number): number | null {
  return whole > 0 ? Math.round((part / whole) * 100) : null;
}
