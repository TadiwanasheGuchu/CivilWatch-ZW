"use client";

import { useState } from "react";

export type NearMeState =
  | { kind: "idle" }
  | { kind: "locating" }
  | { kind: "found"; latitude: number; longitude: number }
  | { kind: "error"; message: string };

const MESSAGES: Record<number, string> = {
  1: "Location permission was refused. Allow location for this site to see reports near you.",
  2: "Your location could not be found.",
  3: "Finding your location took too long. Try again.",
};

/** Ask the browser for the person's location, once, when they tap "Near me". */
export function useNearMe() {
  const [state, setState] = useState<NearMeState>({ kind: "idle" });
  function locate() {
    if (!("geolocation" in navigator)) {
      setState({ kind: "error", message: "This browser cannot share its location." });
      return;
    }
    setState({ kind: "locating" });
    navigator.geolocation.getCurrentPosition(
      (position) => setState({ kind: "found", latitude: position.coords.latitude, longitude: position.coords.longitude }),
      (error) => setState({ kind: "error", message: MESSAGES[error.code] ?? MESSAGES[2]! }),
      { enableHighAccuracy: false, timeout: 15_000, maximumAge: 120_000 },
    );
  }
  return { state, locate, reset: () => setState({ kind: "idle" }) };
}
