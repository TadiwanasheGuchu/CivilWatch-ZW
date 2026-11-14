export type ComponentStatus = "ok" | "unavailable";

/** Mirrors backend `ReadinessResponse` (app/schemas/health.py). */
export interface Readiness {
  status: "ok" | "degraded";
  database: ComponentStatus;
  postgis: ComponentStatus;
  cache: ComponentStatus;
  storage: ComponentStatus;
}
