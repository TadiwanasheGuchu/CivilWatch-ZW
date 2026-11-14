/**
 * Accept only same-site relative paths as post-sign-in destinations, so a
 * crafted `?next=` link cannot send someone to another website.
 */
export function safeNextPath(next: string | null | undefined, fallback = "/account"): string {
  if (!next || !next.startsWith("/") || next.startsWith("//") || next.startsWith("/\\")) {
    return fallback;
  }
  return next;
}

export function signInHref(next: string): string {
  return `/sign-in?next=${encodeURIComponent(next)}`;
}
