"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { STATUS_LABELS } from "@/features/reporting/labels";
import { apiUrl } from "@/lib/api-client";
import { cn } from "@/lib/utils";

import type { BBox, Cluster, ClustersResponse } from "./api";
import { DEFAULT_CENTER, DEFAULT_ZOOM } from "./config";
import { baseStyle, maplibregl, webglSupported } from "./maplibre";

export interface ClusterMapProps {
  /** Loads clusters for the visible area. Called after every pan or zoom. */
  fetchClusters: (bbox: BBox, zoom: number, signal: AbortSignal) => Promise<ClustersResponse>;
  /** Changing this reloads the data (e.g. when filters change). */
  dataKey: string;
  onSelectIssue: (issueId: string) => void;
  focus?: { latitude: number; longitude: number; zoom: number } | null;
  /** An area to frame, e.g. a council's boundary. */
  fitTo?: BBox | null;
  showBoundaries?: boolean;
  label: string;
}

type Mode = "markers" | "heatmap";
const MOVE_DEBOUNCE_MS = 250;

function clampBounds(map: maplibregl.Map): BBox {
  const b = map.getBounds();
  return [
    Math.max(-180, b.getWest()),
    Math.max(-85, b.getSouth()),
    Math.min(180, b.getEast()),
    Math.min(85, b.getNorth()),
  ];
}

function markerElement(cluster: Cluster): HTMLButtonElement {
  const button = document.createElement("button");
  button.type = "button";
  if (cluster.count === 1) {
    button.className =
      "block size-5 rounded-full border-2 border-white bg-teal shadow focus-visible:outline-3 focus-visible:outline-navy";
    button.setAttribute("aria-label", `Report: ${cluster.status ? STATUS_LABELS[cluster.status] : "open"}`);
  } else {
    const size = cluster.count < 10 ? "size-9" : cluster.count < 100 ? "size-11" : "size-12";
    button.className = `grid ${size} place-items-center rounded-full border-2 border-white bg-navy text-sm font-semibold text-white shadow tabular focus-visible:outline-3 focus-visible:outline-teal`;
    button.textContent = cluster.count > 999 ? "999+" : String(cluster.count);
    button.setAttribute("aria-label", `${cluster.count} reports here. Zoom in`);
  }
  return button;
}

export default function ClusterMap({
  fetchClusters,
  dataKey,
  onSelectIssue,
  focus,
  showBoundaries = true,
  label,
  fitTo,
}: ClusterMapProps) {
  const container = useRef<HTMLDivElement>(null);
  const map = useRef<maplibregl.Map | null>(null);
  const markers = useRef<maplibregl.Marker[]>([]);
  const clusters = useRef<Cluster[]>([]);
  const request = useRef<AbortController | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const callbacks = useRef({ fetchClusters, onSelectIssue });
  const [mode, setMode] = useState<Mode>("markers");
  const modeRef = useRef<Mode>("markers");
  const [total, setTotal] = useState<number | null>(null);
  const [state, setState] = useState<"loading" | "ready" | "error" | "unsupported">(() =>
    webglSupported() ? "loading" : "unsupported",
  );

  useEffect(() => {
    callbacks.current = { fetchClusters, onSelectIssue };
  });

  const renderMarkers = useCallback(() => {
    markers.current.forEach((m) => m.remove());
    markers.current = [];
    const instance = map.current;
    if (!instance || modeRef.current !== "markers") return;
    for (const cluster of clusters.current) {
      const element = markerElement(cluster);
      element.addEventListener("click", (event) => {
        event.stopPropagation();
        if (cluster.count === 1 && cluster.issue_id) {
          callbacks.current.onSelectIssue(cluster.issue_id);
        } else {
          instance.easeTo({ center: [cluster.longitude, cluster.latitude], zoom: Math.min(instance.getZoom() + 2, 19) });
        }
      });
      markers.current.push(new maplibregl.Marker({ element }).setLngLat([cluster.longitude, cluster.latitude]).addTo(instance));
    }
  }, []);

  const load = useCallback(async () => {
    const instance = map.current;
    if (!instance) return;
    request.current?.abort();
    const controller = new AbortController();
    request.current = controller;
    setState("loading");
    try {
      const result = await callbacks.current.fetchClusters(clampBounds(instance), Math.round(instance.getZoom()), controller.signal);
      if (controller.signal.aborted) return;
      clusters.current = result.clusters;
      setTotal(result.total);
      const source = instance.getSource("reports") as maplibregl.GeoJSONSource | undefined;
      source?.setData({
        type: "FeatureCollection",
        features: result.clusters.map((c) => ({
          type: "Feature",
          properties: { count: c.count },
          geometry: { type: "Point", coordinates: [c.longitude, c.latitude] },
        })),
      });
      renderMarkers();
      setState("ready");
    } catch {
      if (!controller.signal.aborted) setState("error");
    }
  }, [renderMarkers]);

  // Create the map once.
  useEffect(() => {
    if (!container.current || state === "unsupported") return;
    let instance: maplibregl.Map;
    try {
      instance = new maplibregl.Map({
        container: container.current,
        style: baseStyle(),
        center: DEFAULT_CENTER,
        zoom: DEFAULT_ZOOM,
        dragRotate: false,
        pitchWithRotate: false,
        attributionControl: { compact: true },
      });
    } catch {
      // Rare: WebGL present but unusable. Report it after this effect.
      queueMicrotask(() => setState("unsupported"));
      return;
    }
    instance.touchZoomRotate.disableRotation();
    instance.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
    map.current = instance;
    instance.on("load", () => {
      if (showBoundaries) {
        instance.addSource("boundaries", { type: "geojson", data: apiUrl("/councils/boundaries") });
        instance.addLayer({ id: "boundary-fill", type: "fill", source: "boundaries", paint: { "fill-color": "#267C72", "fill-opacity": 0.05 } });
        instance.addLayer({
          id: "boundary-official",
          type: "line",
          source: "boundaries",
          filter: ["==", ["get", "is_sample"], false],
          paint: { "line-color": "#172B3A", "line-width": 1.5 },
        });
        instance.addLayer({
          id: "boundary-sample",
          type: "line",
          source: "boundaries",
          filter: ["==", ["get", "is_sample"], true],
          paint: { "line-color": "#172B3A", "line-width": 1.5, "line-dasharray": [3, 2] },
        });
      }
      instance.addSource("reports", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
      instance.addLayer({
        id: "reports-heat",
        type: "heatmap",
        source: "reports",
        layout: { visibility: "none" },
        paint: {
          "heatmap-weight": ["interpolate", ["linear"], ["get", "count"], 1, 0.4, 25, 1],
          "heatmap-radius": ["interpolate", ["linear"], ["zoom"], 5, 12, 15, 40],
          "heatmap-opacity": 0.8,
          "heatmap-color": [
            "interpolate",
            ["linear"],
            ["heatmap-density"],
            0,
            "rgba(38,124,114,0)",
            0.3,
            "#267C72",
            0.6,
            "#E7B45A",
            1,
            "#C65B58",
          ],
        },
      });
      void load();
    });
    instance.on("moveend", () => {
      if (timer.current) clearTimeout(timer.current);
      timer.current = setTimeout(() => void load(), MOVE_DEBOUNCE_MS);
    });
    return () => {
      request.current?.abort();
      if (timer.current) clearTimeout(timer.current);
      markers.current.forEach((m) => m.remove());
      instance.remove();
      map.current = null;
    };
    // The map is created once; data reloads are driven below.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Reload when filters change.
  useEffect(() => {
    if (map.current?.loaded()) void load();
  }, [dataKey, load]);

  useEffect(() => {
    if (focus && map.current) map.current.easeTo({ center: [focus.longitude, focus.latitude], zoom: focus.zoom });
  }, [focus]);

  useEffect(() => {
    if (fitTo && map.current) {
      map.current.fitBounds([[fitTo[0], fitTo[1]], [fitTo[2], fitTo[3]]], { padding: 24, duration: 0 });
    }
  }, [fitTo]);

  function switchMode(next: Mode) {
    setMode(next);
    modeRef.current = next;
    map.current?.setLayoutProperty("reports-heat", "visibility", next === "heatmap" ? "visible" : "none");
    renderMarkers();
  }

  if (state === "unsupported") {
    return (
      <p className="rounded-[var(--radius-control)] border border-line bg-mist p-4 text-sm text-navy-soft">
        The map is not supported on this device. Use the list instead.
      </p>
    );
  }

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm text-slate" aria-live="polite">
          {state === "error"
            ? "Reports for this area could not be loaded."
            : total === null
              ? "Loading reports…"
              : `${total} report${total === 1 ? "" : "s"} in view`}
        </p>
        <div role="group" aria-label="Map display" className="inline-flex rounded-[var(--radius-control)] border border-line bg-surface p-0.5">
          {(["markers", "heatmap"] as const).map((option) => (
            <button
              key={option}
              type="button"
              aria-pressed={mode === option}
              onClick={() => switchMode(option)}
              className={cn(
                "min-h-10 rounded-[calc(var(--radius-control)-2px)] px-3 text-sm font-medium",
                mode === option ? "bg-navy text-white" : "text-navy hover:bg-mist",
              )}
            >
              {option === "markers" ? "Markers" : "Heatmap"}
            </button>
          ))}
        </div>
      </div>
      <div className="overflow-hidden rounded-[var(--radius-control)] border border-line">
        <div ref={container} role="region" aria-label={label} className="h-[60vh] min-h-72 w-full md:h-[32rem]" />
      </div>
      {showBoundaries ? (
        <p className="text-xs text-slate">
          Outlines show council areas. <span className="font-medium">Dashed outlines are sample boundaries</span>, for
          demonstration only, not official council borders.
        </p>
      ) : null}
    </div>
  );
}
