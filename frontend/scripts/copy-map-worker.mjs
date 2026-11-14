// MapLibre runs a Web Worker that it locates relative to its own module.
// Bundling moves that module, so we serve the worker from a fixed public path
// (see features/maps/location-map.tsx). Copied from the installed package on
// every build, so it always matches the library version.
import { copyFileSync, mkdirSync } from "node:fs";
import { createRequire } from "node:module";
import path from "node:path";

const require = createRequire(import.meta.url);
const source = path.join(path.dirname(require.resolve("maplibre-gl/package.json")), "dist", "maplibre-gl-worker.mjs");
const targetDir = path.join(process.cwd(), "public", "maplibre");
mkdirSync(targetDir, { recursive: true });
copyFileSync(source, path.join(targetDir, "maplibre-gl-worker.mjs"));
console.log("Copied MapLibre worker to public/maplibre/");
