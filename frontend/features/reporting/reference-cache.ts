/**
 * Categories and the council list rarely change. Keeping the last copy on
 * the device lets someone start a report with no connection at all.
 */
const PREFIX = "civicwatch:reference:";

export function readReference<T>(name: string): T | undefined {
  try {
    const raw = window.localStorage.getItem(PREFIX + name);
    return raw ? (JSON.parse(raw) as T) : undefined;
  } catch {
    return undefined;
  }
}

export function writeReference(name: string, value: unknown): void {
  try {
    window.localStorage.setItem(PREFIX + name, JSON.stringify(value));
  } catch {
    // Storage full or blocked: the app still works online.
  }
}
