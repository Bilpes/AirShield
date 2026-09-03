import { randomBytes } from "node:crypto";
import { NextResponse } from "next/server";
import {
  controlPlaneConfigured,
  controlPlaneFetch,
  controlPolicy,
  productionMode,
} from "@/lib/server/control-plane";
import { readJsonBody, RequestBodyError } from "@/lib/server/request";

export const runtime = "nodejs";

export async function POST(request: Request) {
  try {
    const body = await readJsonBody<Record<string, unknown>>(request, 16_384);
    const policy = controlPolicy(body.policy);
    if (!policy) return NextResponse.json({ error: "policy is required" }, { status: 400 });

    if (controlPlaneConfigured()) {
      const upstream = await controlPlaneFetch("/v1/sessions", {
        method: "POST",
        body: JSON.stringify({
          policy,
          language: "en",
          ttl_minutes: typeof body.ttl_minutes === "number" ? body.ttl_minutes : 60,
        }),
      });
      return NextResponse.json(await upstream.json(), { status: upstream.status });
    }
    if (productionMode) {
      return NextResponse.json({ error: "Privacy control plane is not configured" }, { status: 503 });
    }

    return NextResponse.json(
      {
        session_id: `ses_${randomBytes(5).toString("hex")}`,
        language: "en",
        policy,
        stream_url: process.env.NEXT_PUBLIC_EDGE_WS_URL || "/edge/ws/voice (same-origin proxy)",
        expires_at: new Date(Date.now() + 3_600_000).toISOString(),
      },
      { status: 201 },
    );
  } catch (error) {
    if (error instanceof RequestBodyError) {
      return NextResponse.json({ error: error.message }, { status: error.status });
    }
    return NextResponse.json({ error: "Session control unavailable" }, { status: 503 });
  }
}
