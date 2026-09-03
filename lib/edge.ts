// Browser-side helpers for reaching the self-hosted voice edge.
//
// Default path (same-origin proxy): the browser opens its WebSocket against
// the SAME ORIGIN as the web app — `/edge/ws/voice` — and the Next.js server
// proxies it to the voice edge (see the rewrite in next.config.ts, upstream
// configurable via EDGE_UPSTREAM). This keeps live voice working on
// localhost, LAN IPs and HTTPS hosts (e.g. cloud preview URLs) without
// cross-origin WebSockets, mixed-content failures, or CSP exceptions for a
// second origin.
//
// Explicit override: set NEXT_PUBLIC_EDGE_WS_URL to an absolute ws:// or
// wss:// URL to point browsers straight at the edge, or at an authenticated
// gateway in production deployments.

export const EDGE_WS_PATH = "/edge/ws/voice";

/** WebSocket URL for live voice capture, or null when rendered server-side. */
export function edgeWebSocketUrl(): string | null {
  const configured = process.env.NEXT_PUBLIC_EDGE_WS_URL?.trim();
  if (configured) return configured;
  if (typeof window === "undefined") return null;
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${window.location.host}${EDGE_WS_PATH}`;
}

/** Health endpoint for the same edge: ws(s)://host/ws/voice -> http(s)://host/v1/health */
export function edgeHealthUrl(edgeUrl: string): string {
  return edgeUrl.replace(/^ws/, "http").replace(/\/ws\/voice$/, "/v1/health");
}
