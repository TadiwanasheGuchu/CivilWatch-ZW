import type { NextConfig } from "next";

/** Origin ("scheme://host:port") of a URL or URL template; same-origin paths need none. */
function origin(url: string): string {
  if (url.startsWith("/")) return "";
  return new URL(url.replace(/\{[a-z]\}/g, "a")).origin;
}

const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";
const apiOrigin = origin(apiBase);
// Hosts that put the web app and API on different sites (e.g. Vercel and
// Render) set NEXT_PUBLIC_API_BASE_URL=/api/v1 and API_PROXY_TARGET to the
// API's address: the browser then talks to one origin, so the session
// cookie stays first-party and SameSite protection keeps working.
const apiProxyTarget = process.env.API_PROXY_TARGET?.replace(/\/$/, "");
if (apiBase.startsWith("/") && !apiProxyTarget) {
  throw new Error("A relative NEXT_PUBLIC_API_BASE_URL needs API_PROXY_TARGET.");
}
const tileOrigin = origin(process.env.NEXT_PUBLIC_MAP_TILE_URL ?? "https://tile.openstreetmap.org/{z}/{x}/{y}.png");
// Where photos are served from: the storage service's public endpoint, which
// signs short-lived URLs. Space-separated; set it to your bucket's origin in production.
const mediaOrigins = process.env.NEXT_PUBLIC_MEDIA_ORIGINS ?? "http://localhost:9000 http://127.0.0.1:9000";
const isDev = process.env.NODE_ENV === "development";

// Next.js App Router inlines small scripts for hydration, so script-src needs
// 'unsafe-inline' unless every page is rendered per request with a nonce.
// The policy still blocks scripts from any other origin, plugins, framing
// and form posts elsewhere (docs/06-security-and-privacy.md).
const contentSecurityPolicy = [
  "default-src 'self'",
  `script-src 'self' 'unsafe-inline'${isDev ? " 'unsafe-eval'" : ""}`,
  "style-src 'self' 'unsafe-inline'",
  `img-src 'self' data: blob: ${tileOrigin} ${mediaOrigins}`,
  "font-src 'self'",
  `connect-src 'self' ${apiOrigin} ${tileOrigin}`.replace(/\s+/g, " "),
  "worker-src 'self' blob:",
  "object-src 'none'",
  "base-uri 'self'",
  "form-action 'self'",
  "frame-ancestors 'none'",
].join("; ");

const securityHeaders = [
  { key: "Content-Security-Policy", value: contentSecurityPolicy },
  // Ignored by browsers over plain HTTP, so harmless in local development.
  { key: "Strict-Transport-Security", value: "max-age=63072000; includeSubDomains" },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  // Camera is needed for evidence capture; geolocation for report location.
  { key: "Permissions-Policy", value: "camera=(self), geolocation=(self), microphone=()" },
];

const nextConfig: NextConfig = {
  output: "standalone",
  poweredByHeader: false,
  reactStrictMode: true,
  async headers() {
    return [{ source: "/:path*", headers: securityHeaders }];
  },
  async rewrites() {
    return apiProxyTarget ? [{ source: "/api/:path*", destination: `${apiProxyTarget}/api/:path*` }] : [];
  },
};

export default nextConfig;
