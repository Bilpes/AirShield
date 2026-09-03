import type { NextConfig } from "next";

const production = process.env.NODE_ENV === "production";
let edgeConnectSource = "";
try {
  const configured = process.env.NEXT_PUBLIC_EDGE_WS_URL;
  if (configured) {
    const parsed = new URL(configured);
    const localInsecureEdge = process.env.AIRSHIELD_ALLOW_INSECURE_LOCAL_EDGE === "true";
    if (
      !["ws:", "wss:"].includes(parsed.protocol) ||
      (production && parsed.protocol !== "wss:" && !localInsecureEdge)
    ) {
      throw new Error("NEXT_PUBLIC_EDGE_WS_URL must use WSS in production");
    }
    edgeConnectSource = parsed.origin;
  }
} catch (error) {
  if (error instanceof Error && error.message.includes("must use WSS")) throw error;
  throw new Error("NEXT_PUBLIC_EDGE_WS_URL must be an absolute ws:// or wss:// URL");
}
// Same-origin voice-edge proxy. Browsers connect to `/edge/ws/voice` on the
// web app's own origin and Next.js forwards it to the voice edge, so live
// voice works from localhost, LAN IPs and HTTPS hosts (cloud previews) with
// no cross-origin WebSocket, mixed-content failure, or extra CSP origin.
// The upstream is resolved at build time (rewrites are baked into the build),
// so Docker builds pass EDGE_UPSTREAM explicitly (docker-compose sets
// http://edge:8001); local dev defaults to the edge started by run_local.sh.
const edgeUpstream = process.env.EDGE_UPSTREAM?.trim() || "http://127.0.0.1:8001";

const developmentSockets = production ? "" : " ws: wss:";
// In same-origin proxy mode the browser opens a wss:// WebSocket against this
// same host. CSP3 says 'self' covers the ws/wss upgrade of the same origin,
// but several browsers (notably Safari) still require the scheme explicitly,
// and the public host is not known at build time (previews vary), so allow
// wss: only when the proxy default is in use.
const proxySockets = process.env.NEXT_PUBLIC_EDGE_WS_URL?.trim() ? "" : " wss:";
const contentSecurityPolicy = [
  "default-src 'self'",
  `script-src 'self' 'unsafe-inline'${production ? "" : " 'unsafe-eval'"}`,
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data: blob:",
  "font-src 'self' data:",
  `connect-src 'self'${edgeConnectSource ? ` ${edgeConnectSource}` : ""}${developmentSockets}${proxySockets}`,
  "media-src 'self' blob:",
  "object-src 'none'",
  "base-uri 'self'",
  "form-action 'self'",
  "frame-ancestors 'none'",
].join("; ");

const nextConfig: NextConfig = {
  reactStrictMode: true,
  output: "standalone",
  poweredByHeader: false,
  allowedDevOrigins: ["127.0.0.1", "localhost", "*.e2b.app"],
  async rewrites() {
    return [{ source: "/edge/:path*", destination: `${edgeUpstream}/:path*` }];
  },
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          { key: "Content-Security-Policy", value: contentSecurityPolicy },
          { key: "Referrer-Policy", value: "no-referrer" },
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "X-Frame-Options", value: "DENY" },
          { key: "Permissions-Policy", value: "camera=(), microphone=(self), geolocation=()" },
          ...(production
            ? [{ key: "Strict-Transport-Security", value: "max-age=31536000; includeSubDomains" }]
            : []),
        ],
      },
    ];
  },
};

export default nextConfig;
