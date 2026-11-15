/** Public runtime configuration. Only NEXT_PUBLIC_ values belong here — never secrets. */
export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

/** True on demonstration deployments, whose councils, accounts and reports are sample data. */
export const DEMO_MODE = process.env.NEXT_PUBLIC_DEMO_MODE === "true";
