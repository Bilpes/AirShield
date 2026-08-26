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
const developmentSockets = production ? "" : " ws: wss:";
const contentSecurityPolicy = [
  "default-src 'self'",
  `script-src 'self' 'unsafe-inline'${production ? "" : " 'unsafe-eval'"}`,
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data: blob:",
  "font-src 'self' data:",
  `connect-src 'self'${edgeConnectSource ? ` ${edgeConnectSource}` : ""}${developmentSockets}`,
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
