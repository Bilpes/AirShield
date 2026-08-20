import { randomUUID } from "node:crypto";
import { NextResponse } from "next/server";
import { protectText } from "@/lib/masking";
import {
  controlDestination,
  controlPlaneConfigured,
  controlPlaneFetch,
  controlPolicy,
  createControlSession,
  productionMode,
} from "@/lib/server/control-plane";
import { readJsonBody, RequestBodyError } from "@/lib/server/request";

export const runtime = "nodejs";

export async function POST(request: Request) {
  const started = performance.now();
  try {
    const body = await readJsonBody<Record<string, unknown>>(request, 262_144);
    if (typeof body.text !== "string" || !body.text.trim()) {
      return NextResponse.json({ error: "text must be a non-empty string" }, { status: 400 });
    }
    if (Buffer.byteLength(body.text, "utf8") > 250_000) {
      return NextResponse.json({ error: "text exceeds the 250 KB limit" }, { status: 413 });
    }

    if (controlPlaneConfigured()) {
      const policy = controlPolicy(body.policy);
      if (!policy) return NextResponse.json({ error: "policy is required" }, { status: 400 });
      const sessionId =
        typeof body.session_id === "string" && body.session_id
          ? body.session_id
          : await createControlSession(policy);
      const upstream = await controlPlaneFetch("/v1/protect", {
        method: "POST",
        body: JSON.stringify({
          session_id: sessionId,
          text: body.text,
          policy,
          destination: controlDestination(policy, body.destination),
          speaker_token: typeof body.speaker_token === "string" ? body.speaker_token : undefined,
          idempotency_key:
            typeof body.idempotency_key === "string" ? body.idempotency_key : randomUUID(),
        }),
      });
      const payload = await upstream.json();
      return NextResponse.json(
        { ...payload, session_id: sessionId, latency_ms: Math.max(1, Math.round(performance.now() - started)) },
        { status: upstream.status },
      );
    }

    if (productionMode) {
      return NextResponse.json({ error: "Privacy control plane is not configured; egress denied" }, { status: 503 });
    }

    const result = protectText(body.text);
    return NextResponse.json({
      protected_text: result.protectedText,
      entities: result.entities.map(({ raw: _raw, ...entity }) => entity),
      decision: result.decision,
      policy: typeof body.policy === "string" ? body.policy : "default-v1",
      latency_ms: Math.max(1, Math.round(performance.now() - started)),
      receipt: {
        receipt_id: result.receiptId,
        content_sha256: result.contentHash,
        policy: typeof body.policy === "string" ? body.policy : "default-v1",
        destination: typeof body.destination === "string" ? body.destination : "not-specified",
        entity_counts: result.entities.reduce<Record<string, number>>(
          (counts, entity) => ({ ...counts, [entity.type]: (counts[entity.type] ?? 0) + 1 }),
          {},
        ),
        decision: result.decision,
        created_at: new Date().toISOString(),
        signature: "demo_unsigned",
      },
      warning: "Development-only regex detector; production is configured to fail closed",
    });
  } catch (error) {
    if (error instanceof RequestBodyError) {
      return NextResponse.json({ error: error.message }, { status: error.status });
    }
    return NextResponse.json({ error: "Protection control unavailable; egress denied" }, { status: 503 });
  }
}
