/**
 * Raster tiles. The default is OpenStreetMap's public tile server, which is
 * fine for development and light use; its usage policy rules out heavy
 * production traffic, so set NEXT_PUBLIC_MAP_TILE_URL to a tile provider
 * before launch (see docs/09-deployment-guide.md).
 */
export const TILE_URL = process.env.NEXT_PUBLIC_MAP_TILE_URL ?? "https://tile.openstreetmap.org/{z}/{x}/{y}.png";
export const TILE_ATTRIBUTION =
  process.env.NEXT_PUBLIC_MAP_ATTRIBUTION ??
  '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors';

/** Roughly the centre of Zimbabwe, for an empty map. */
export const DEFAULT_CENTER: [number, number] = [29.8, -19.0];
export const DEFAULT_ZOOM = 5.5;
export const PIN_ZOOM = 16;
