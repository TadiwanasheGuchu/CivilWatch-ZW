import { apiGet, apiSend } from "@/lib/api-client";

import type { IssueStatus, PublicIssue } from "@/features/reporting/types";
import type { StaffIssueSummary } from "@/features/council/operations/types";

export type BBox = [west: number, south: number, east: number, north: number];

export interface Cluster {
  latitude: number;
  longitude: number;
  count: number;
  issue_id: string | null;
  status: IssueStatus | null;
}

export interface ClustersResponse {
  zoom: number;
  total: number;
  clusters: Cluster[];
}

export interface MapFilters {
  councilId?: string;
  category?: string;
  statuses?: IssueStatus[];
}

export interface LocatedCouncil {
  id: string;
  slug: string;
  name: string;
  is_sample_boundary: boolean;
}

export type NearbyIssue = PublicIssue & { distance_m: number };
export type NearbyStaffIssue = StaffIssueSummary & { distance_m: number };

function clusterQuery(bbox: BBox, zoom: number, filters: MapFilters): string {
  const params = new URLSearchParams({ bbox: bbox.map((n) => n.toFixed(5)).join(","), zoom: String(zoom) });
  if (filters.councilId) params.set("council_id", filters.councilId);
  if (filters.category) params.set("category", filters.category);
  filters.statuses?.forEach((status) => params.append("status", status));
  return params.toString();
}

export function fetchPublicClusters(bbox: BBox, zoom: number, filters: MapFilters, signal?: AbortSignal) {
  return apiGet<ClustersResponse>(`/map/clusters?${clusterQuery(bbox, zoom, filters)}`, { signal });
}

export function fetchCouncilClusters(
  councilId: string,
  bbox: BBox,
  zoom: number,
  filters: MapFilters,
  signal?: AbortSignal,
) {
  return apiGet<ClustersResponse>(
    `/councils/${encodeURIComponent(councilId)}/map/clusters?${clusterQuery(bbox, zoom, { ...filters, councilId: undefined })}`,
    { signal },
  );
}

export function locateCouncils(latitude: number, longitude: number, signal?: AbortSignal) {
  return apiGet<LocatedCouncil[]>(`/councils/locate?latitude=${latitude}&longitude=${longitude}`, { signal });
}

export function fetchNearby(
  latitude: number,
  longitude: number,
  { radiusM = 1000, category, limit = 20 }: { radiusM?: number; category?: string; limit?: number },
  signal?: AbortSignal,
) {
  const params = new URLSearchParams({
    latitude: String(latitude),
    longitude: String(longitude),
    radius_m: String(radiusM),
    limit: String(limit),
  });
  if (category) params.set("category", category);
  return apiGet<NearbyIssue[]>(`/issues/nearby?${params.toString()}`, { signal });
}

export function fetchStaffNearby(councilId: string, issueId: string, signal?: AbortSignal) {
  return apiGet<NearbyStaffIssue[]>(
    `/councils/${encodeURIComponent(councilId)}/issues/${encodeURIComponent(issueId)}/nearby?radius_m=200`,
    { signal },
  );
}

export interface BoundaryFeature {
  type: "Feature";
  id: string;
  properties: { id: string; slug: string; name: string; is_sample: boolean };
  geometry: { type: "MultiPolygon"; coordinates: number[][][][] };
}

/**
 * Council boundaries. The API lets browsers cache them for five minutes;
 * pass `fresh` where someone has just changed one (the boundary admin page).
 */
export function fetchBoundaries(signal?: AbortSignal, { fresh = false }: { fresh?: boolean } = {}) {
  return apiGet<{ type: "FeatureCollection"; features: BoundaryFeature[] }>("/councils/boundaries", {
    signal,
    cache: fresh ? "no-cache" : "default",
  });
}

export interface BoundaryResult {
  council_id: string;
  source: "official" | "sample";
  area_km2: number;
  vertex_count: number;
  overlaps: string[];
}

export function setBoundary(councilId: string, geometry: unknown, source: "official" | "sample", csrfToken: string) {
  return apiSend<BoundaryResult>("PUT", `/councils/${encodeURIComponent(councilId)}/boundary`, {
    body: { geometry, source },
    csrfToken,
  });
}

export function clearBoundary(councilId: string, csrfToken: string) {
  return apiSend("DELETE", `/councils/${encodeURIComponent(councilId)}/boundary`, { csrfToken });
}

export function formatDistance(metres: number): string {
  return metres < 1000 ? `${Math.round(metres)} m away` : `${(metres / 1000).toFixed(1)} km away`;
}

/** The bounding box of a council's boundary, for framing a map. */
export function boundaryBBox(feature: BoundaryFeature): BBox {
  let west = 180;
  let south = 90;
  let east = -180;
  let north = -90;
  for (const polygon of feature.geometry.coordinates) {
    for (const ring of polygon) {
      for (const [lon, lat] of ring) {
        west = Math.min(west, lon!);
        east = Math.max(east, lon!);
        south = Math.min(south, lat!);
        north = Math.max(north, lat!);
      }
    }
  }
  return [west, south, east, north];
}
