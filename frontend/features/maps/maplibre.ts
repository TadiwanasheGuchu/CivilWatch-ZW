/**
 * Shared MapLibre setup. Import maplibregl from here, never directly, so
 * every map uses the same worker location and base style.
 */
import "maplibre-gl/dist/maplibre-gl.css";

import * as maplibregl from "maplibre-gl";

import { TILE_ATTRIBUTION, TILE_URL } from "./config";

// Served from public/ (copied by scripts/copy-map-worker.mjs), because the
// bundler moves MapLibre away from the worker file it expects beside it.
maplibregl.setWorkerUrl("/maplibre/maplibre-gl-worker.mjs");

export function baseStyle(): maplibregl.StyleSpecification {
  return {
    version: 8,
    sources: {
      base: { type: "raster", tiles: [TILE_URL], tileSize: 256, maxzoom: 19, attribution: TILE_ATTRIBUTION },
    },
    layers: [{ id: "base", type: "raster", source: "base" }],
  };
}

export { maplibregl };

/** Whether this browser can run MapLibre (it needs WebGL). */
export function webglSupported(): boolean {
  try {
    const canvas = document.createElement("canvas");
    return Boolean(canvas.getContext("webgl2") ?? canvas.getContext("webgl"));
  } catch {
    return false;
  }
}
