/*
 * Agent Trust Lab — PurposeGraph™ capture + response API.
 *
 * Runs the same deterministic engine as the browser demo, server-side, so the
 * "response" the lab renders is a real computation (not a hard-coded verdict).
 * In production the identical rules run in the `purpose-graph-service` Python
 * service behind a KMS/HSM trust anchor; this route is the overlay that keeps
 * the live demo and the production decision path aligned.
 */
import { NextResponse } from "next/server";
import { readJsonBody, RequestBodyError } from "@/lib/server/request";
import { PurposeGraphStore, type StoreSnapshot } from "@/lib/purpose-graph-sim";
import { shortId } from "@/lib/purpose-graph";

export const runtime = "nodejs";

declare global {
  var __agentTrustLabStore: PurposeGraphStore | undefined;
}

const ACTIONS = [
  "reset",
  "confirmIntent",
  "ingestSource",
  "proposeExploit",
  "proposeCorrect",
  "approve",
  "attackDrift",
  "execute",
  "revoke",
  "auto",
] as const;

type ActionName = (typeof ACTIONS)[number];

function store(): PurposeGraphStore {
  if (!globalThis.__agentTrustLabStore) {
    globalThis.__agentTrustLabStore = new PurposeGraphStore();
  }
  return globalThis.__agentTrustLabStore;
}

/** A structured, machine-readable "response" for the current step. */
function buildResponse(store: PurposeGraphStore, action: ActionName, snapshot: StoreSnapshot): Record<string, unknown> {
  const verdict = snapshot.lastVerdict;
  const approval = snapshot.lastApproval;
  const intent = snapshot.intentSeal;
  const lock = snapshot.lock;
  return {
    request: { action, engine: "airshield-purposegraph-v1", mode: "demo" },
    state: {
      binding_hash: lock
        ? {
            payload: lock.canonical_payload_hash,
            state: lock.state_hash,
            lock_id: shortId(lock.id),
            status: lock.status,
          }
        : null,
      contract_hash: intent ? shortId(intent.hash) : null,
      consent_revoked: snapshot.consentRevoked,
      executed: snapshot.executed,
      memory: snapshot.memory?.trust ?? null,
    },
    decision: verdict
      ? {
          verdict: verdict.decision,
          code: verdict.code,
          reason: verdict.reason,
          enforcements: verdict.enforcements,
        }
      : null,
    approval: approval
      ? { granted: approval.granted, code: approval.code, reason: approval.reason }
      : null,
    drift: snapshot.drift
      ? { field: snapshot.drift.field, from: snapshot.drift.from, to: snapshot.drift.to, drifting: snapshot.drift.drifting }
      : null,
    trace_progress: snapshot.progress,
    log_lines: snapshot.logs.length,
  };
}

export async function POST(request: Request) {
  try {
    const body = await readJsonBody<{ action?: string }>(request, 16_384);
    const action = (body.action ?? "auto") as ActionName;
    if (!ACTIONS.includes(action)) {
      return NextResponse.json({ error: `action must be one of ${ACTIONS.join(", ")}` }, { status: 400 });
    }

    // Production path: proxy to the self-hosted Python PurposeGraph service.
    const upstream = process.env.PURPOSEGRAPH_URL;
    if (upstream) {
      const target = `${upstream.replace(/\/$/, "")}/v1/trust-graph/run`;
      const proxied = await fetch(target, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action }),
        cache: "no-store",
      });
      const payload = await proxied.json();
      return NextResponse.json(payload, { status: proxied.status });
    }

    const lab = store();
    if (action === "reset") lab.reset();
    else if (action === "confirmIntent") lab.confirmIntent();
    else if (action === "ingestSource") lab.ingestSource();
    else if (action === "proposeExploit") lab.proposeExploit();
    else if (action === "proposeCorrect") lab.proposeCorrect();
    else if (action === "approve") lab.approve();
    else if (action === "attackDrift") lab.attackDrift();
    else if (action === "execute") lab.execute();
    else if (action === "revoke") lab.revoke();
    const snapshot = lab.snapshot();
    return NextResponse.json(
      { ...buildResponse(lab, action, snapshot), snapshot, rendered_response: buildResponse(lab, action, snapshot) },
      { status: 200 },
    );
  } catch (error) {
    if (error instanceof RequestBodyError) {
      return NextResponse.json({ error: error.message }, { status: error.status });
    }
    return NextResponse.json({ error: "Agent Trust Lab control unavailable" }, { status: 503 });
  }
}
