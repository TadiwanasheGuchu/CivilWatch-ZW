"use client";

import { useEffect, useRef, useState } from "react";

import { DEFAULT_CENTER, DEFAULT_ZOOM, PIN_ZOOM } from "./config";
import { baseStyle, maplibregl } from "./maplibre";

export interface LocationMapProps {
  latitude: number | null;
  longitude: number | null;
  onChange?: (latitude: number, longitude: number) => void;
  /** The map cannot work at all here (no WebGL). */
  onError?: () => void;
  /** Read-only maps (report pages) cannot be tapped or dragged. */
  interactive?: boolean;
  label: string;
}

/**
 * Tap the map (or drag the pin) to choose a location. Loaded lazily: this
 * module pulls in MapLibre, so it is only downloaded when a map is shown.
 */
export default function LocationMap({ latitude, longitude, onChange, onError, interactive = true, label }: LocationMapProps) {
  const container = useRef<HTMLDivElement>(null);
  const map = useRef<maplibregl.Map | null>(null);
  const marker = useRef<maplibregl.Marker | null>(null);
  const callbacks = useRef({ onChange, onError });
  // Tile failures are normal on poor connections: the pin and tapping still
  // work, so the map stays and a short note explains the missing imagery.
  const [tilesUnavailable, setTilesUnavailable] = useState(false);

  useEffect(() => {
    callbacks.current = { onChange, onError };
  });

  useEffect(() => {
    if (!container.current) return;
    const hasPin = latitude !== null && longitude !== null;
    let instance: maplibregl.Map;
    try {
      instance = new maplibregl.Map({
        container: container.current,
        style: baseStyle(),
        center: hasPin ? [longitude, latitude] : DEFAULT_CENTER,
        zoom: hasPin ? PIN_ZOOM : DEFAULT_ZOOM,
        interactive: true,
        dragRotate: false,
        pitchWithRotate: false,
        cooperativeGestures: !interactive,
        attributionControl: { compact: true },
      });
    } catch {
      // No WebGL (old phones): the rest of the form still works.
      callbacks.current.onError?.();
      return;
    }
    instance.touchZoomRotate.disableRotation();
    instance.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
    let tileLoaded = false;
    instance.on("data", (event) => {
      if (event.dataType === "source" && "tile" in event && event.tile) {
        tileLoaded = true;
        setTilesUnavailable(false);
      }
    });
    instance.on("error", () => {
      if (!tileLoaded) setTilesUnavailable(true);
    });
    if (interactive) {
      instance.on("click", (event: maplibregl.MapMouseEvent) => callbacks.current.onChange?.(event.lngLat.lat, event.lngLat.lng));
    }
    map.current = instance;
    return () => {
      instance.remove();
      map.current = null;
      marker.current = null;
    };
    // The map is created once; position updates are handled below.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [interactive]);

  useEffect(() => {
    const instance = map.current;
    if (!instance) return;
    if (latitude === null || longitude === null) {
      marker.current?.remove();
      marker.current = null;
      return;
    }
    if (!marker.current) {
      marker.current = new maplibregl.Marker({ color: "#267C72", draggable: interactive })
        .setLngLat([longitude, latitude])
        .addTo(instance);
      marker.current.on("dragend", () => {
        const position = marker.current?.getLngLat();
        if (position) callbacks.current.onChange?.(position.lat, position.lng);
      });
    } else {
      marker.current.setLngLat([longitude, latitude]);
    }
    instance.easeTo({ center: [longitude, latitude], zoom: Math.max(instance.getZoom(), PIN_ZOOM) });
  }, [latitude, longitude, interactive]);

  return (
    <div className="relative">
      <div ref={container} role="region" aria-label={label} className="h-64 w-full sm:h-80" />
      {tilesUnavailable ? (
        <p className="pointer-events-none absolute top-2 right-12 left-2 rounded bg-surface/95 px-2 py-1 text-xs text-navy-soft">
          Map images could not load on this connection.
          {interactive ? " You can still tap to place the pin or use your location." : ""}
        </p>
      ) : null}
    </div>
  );
}
