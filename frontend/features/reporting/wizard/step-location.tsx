"use client";

import { LocateFixed, MapPinOff } from "lucide-react";
import { useState } from "react";

import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { LazyLocationMap } from "@/features/maps/lazy-location-map";

import { useCouncilOptions } from "../hooks";
import type { StepProps } from "./step-props";

const GEO_ERRORS: Record<number, string> = {
  1: "Location permission was refused. Tap the map instead, or allow location for this site.",
  2: "Your location could not be found. Tap the map instead.",
  3: "Finding your location took too long. Try again or tap the map.",
};

export function LocationStep({ draft, update, errors }: StepProps) {
  const councils = useCouncilOptions();
  const [locating, setLocating] = useState(false);
  const [geoError, setGeoError] = useState<string | null>(null);
  const [mapFailed, setMapFailed] = useState(false);
  const hasPin = draft.latitude !== null && draft.longitude !== null;

  function useCurrentLocation() {
    if (!("geolocation" in navigator)) {
      setGeoError("This browser cannot share its location. Tap the map instead.");
      return;
    }
    setLocating(true);
    setGeoError(null);
    navigator.geolocation.getCurrentPosition(
      (position) => {
        setLocating(false);
        update({ latitude: position.coords.latitude, longitude: position.coords.longitude });
      },
      (error) => {
        setLocating(false);
        setGeoError(GEO_ERRORS[error.code] ?? GEO_ERRORS[2]!);
      },
      { enableHighAccuracy: true, timeout: 15_000, maximumAge: 60_000 },
    );
  }

  return (
    <div className="space-y-5">
      <Field
        label="Council"
        hint="The council responsible for where the problem is."
        error={errors.councilId}
      >
        <Select value={draft.councilId ?? ""} onChange={(event) => update({ councilId: event.target.value || null })}>
          <option value="">Choose a council</option>
          {(councils.data ?? []).map((council) => (
            <option key={council.id} value={council.id}>
              {council.name}
            </option>
          ))}
        </Select>
      </Field>

      <div className="space-y-2">
        <p className="text-sm font-medium">Where is the problem?</p>
        <p className="text-sm text-slate">
          Stand near it and use your location, or tap the map. You can drag the pin to adjust it.
        </p>
        <Button variant="secondary" size="lg" className="w-full sm:w-auto" onClick={useCurrentLocation} disabled={locating}>
          <LocateFixed aria-hidden="true" />
          {locating ? "Finding your location…" : "Use my current location"}
        </Button>
        {geoError ? <Alert tone="error">{geoError}</Alert> : null}

        <div className="overflow-hidden rounded-[var(--radius-control)] border border-line">
          {mapFailed ? (
            <div className="flex h-40 flex-col items-center justify-center gap-2 bg-mist px-4 text-center text-sm text-navy-soft">
              <MapPinOff aria-hidden="true" className="size-5" />
              The map is not supported on this device. Use your current location instead.
            </div>
          ) : (
            <LazyLocationMap
              latitude={draft.latitude}
              longitude={draft.longitude}
              onChange={(latitude, longitude) => update({ latitude, longitude })}
              onError={() => setMapFailed(true)}
              label="Map: tap to place the report pin"
            />
          )}
        </div>
        <p role="status" className="text-sm text-slate tabular">
          {hasPin
            ? `Pin set at ${draft.latitude!.toFixed(5)}, ${draft.longitude!.toFixed(5)}`
            : "No location set yet."}
        </p>
        {errors.latitude ? <p className="text-sm font-medium text-red-text">{errors.latitude}</p> : null}
      </div>

      <Field
        label="Landmark or address (optional)"
        hint="For example: opposite the Total garage"
        error={errors.locationDescription}
      >
        <Input
          value={draft.locationDescription}
          maxLength={200}
          onChange={(event) => update({ locationDescription: event.target.value })}
        />
      </Field>
    </div>
  );
}
