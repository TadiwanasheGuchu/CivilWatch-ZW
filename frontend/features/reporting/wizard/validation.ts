import { z } from "zod";

import type { ReportDraft, StepId } from "../draft";

/** Per-step checks, mirroring the API's rules (app/schemas/issues.py). The API re-validates. */
const stepSchemas: Partial<Record<StepId, z.ZodType>> = {
  category: z.object({ categoryId: z.string({ message: "Choose what kind of problem this is." }) }),
  details: z.object({
    title: z
      .string()
      .transform((value) => value.trim().replace(/\s+/g, " "))
      .pipe(
        z
          .string()
          .min(5, "Give the problem a short title of at least 5 characters.")
          .max(120, "Keep the title under 120 characters."),
      ),
    description: z
      .string()
      .transform((value) => value.trim())
      .pipe(
        z
          .string()
          .min(10, "Describe the problem in at least 10 characters.")
          .max(2000, "Keep the description under 2000 characters."),
      ),
  }),
  location: z.object({
    councilId: z.string({ message: "Choose the council responsible for this area." }),
    latitude: z.number({ message: "Set the location: tap the map or use your current location." }),
    longitude: z.number({ message: "Set the location: tap the map or use your current location." }),
    locationDescription: z.string().max(200, "Keep this under 200 characters."),
  }),
  visibility: z.object({
    visibility: z.enum(["PUBLIC", "PRIVATE"], { message: "Choose who can see this report." }),
  }),
};

export type StepErrors = Record<string, string>;

export function validateStep(step: StepId, draft: ReportDraft): StepErrors {
  const schema = stepSchemas[step];
  if (!schema) return {};
  const result = schema.safeParse(draft);
  if (result.success) return {};
  const errors: StepErrors = {};
  for (const issue of result.error.issues) {
    const field = String(issue.path[0] ?? "form");
    errors[field] ??= issue.message;
  }
  // One message is enough for a missing pin.
  if (errors.latitude && errors.longitude) delete errors.longitude;
  return errors;
}

/** Which step holds an API field, so a server error can send the person back to it. */
export const FIELD_STEPS: Record<string, StepId> = {
  category_id: "category",
  title: "details",
  description: "details",
  council_id: "location",
  latitude: "location",
  longitude: "location",
  location_description: "location",
  visibility: "visibility",
};
