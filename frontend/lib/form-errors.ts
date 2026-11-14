import type { FieldValues, Path, UseFormSetError } from "react-hook-form";

import { fieldErrorsFrom } from "@/lib/api-client";

/**
 * Put server-side validation messages on the matching form fields.
 * Returns true if at least one field error was applied.
 */
export function applyServerFieldErrors<T extends FieldValues>(
  error: unknown,
  setError: UseFormSetError<T>,
  fields: ReadonlyArray<Path<T>>,
): boolean {
  const errors = fieldErrorsFrom(error);
  let applied = false;
  for (const field of fields) {
    const message = errors[field];
    if (message) {
      setError(field, { type: "server", message });
      applied = true;
    }
  }
  return applied;
}
