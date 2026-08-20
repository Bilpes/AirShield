import { randomUUID } from "node:crypto";
import { NextResponse } from "next/server";
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

const fallback: Record<string, string> = {
  Healthcare: "The patient reported a dry cough and mild fever for three days, with no chest pain. Current medication includes metformin 500 mg twice daily. The clinician asked about respiratory symptoms and exposure. All direct identifiers were removed before summary generation.",
  Finance: "The customer reported a pending ₹45,000 transfer. The agent confirmed that the transaction was pending rather than lost and created a support case. Customer, account, tax and contact identifiers were tokenized before AI processing.",
  Insurance: "The policyholder reported a motor accident and provided incident details. A witness statement was recorded and a claim reference was opened. Policy, vehicle, location and contact identifiers were protected before AI processing.",
  "BPO / Contact center": "The customer reported a duplicate ₹1,499 charge. The agent confirmed the issue, created a refund request, and advised a three-business-day resolution. Customer identity, contact and account details were protected.",
  "SaaS / Copilot": "The incident affected one customer tenant and involved an expired certificate. An exposed API credential must be revoked. Customer, infrastructure and secret values were removed before the incident summary was generated.",
};

const industryPolicies: Record<string, string> = {
  Healthcare: "healthcare-us-eu-v1",
  Finance: "finance-eu-us-v1",
  Insurance: "insurance-eu-us-v1",
  "BPO / Contact center": "contact-center-eu-us-v1",
  "SaaS / Copilot": "saas-copilot-eu-us-v1",
};

export async function POST(request: Request) {
  try {
    const body = await readJsonBody<Record<string, unknown>>(request, 262_144);
    if (typeof body.text !== "string" || !body.text.trim()) {
      return NextResponse.json({ error: "text is required" }, { status: 400 });
    }
    if (Buffer.byteLength(body.text, "utf8") > 250_000) {
      return NextResponse.json({ error: "text exceeds the 250 KB limit" }, { status: 413 });
    }

    let protectedText = body.text;
    let receipt: unknown;
    if (controlPlaneConfigured()) {
      const policy = controlPolicy(body.policy ?? industryPolicies[String(body.industry)]);
      if (!policy) return NextResponse.json({ error: "A recognized policy or industry is required" }, { status: 400 });
      const sessionId =
        typeof body.session_id === "string" && body.session_id
          ? body.session_id
          : await createControlSession(policy);
      const protection = await controlPlaneFetch("/v1/protect", {
        method: "POST",
        body: JSON.stringify({
          session_id: sessionId,
          text: body.text,
          policy,
          destination: controlDestination(policy, body.destination),
          idempotency_key: typeof body.idempotency_key === "string" ? body.idempotency_key : randomUUID(),
        }),
      });
      if (!protection.ok) {
        return NextResponse.json({ error: "Privacy policy did not authorize AI egress" }, { status: 503 });
      }
      const result = (await protection.json()) as {
        protected_text?: string;
        decision?: "allow" | "block" | "review";
        receipt?: unknown;
      };
      if (!result.protected_text || result.decision !== "allow") {
        return NextResponse.json(
          { error: `AI egress denied by privacy policy (${result.decision ?? "unknown"})` },
          { status: 422 },
        );
      }
      protectedText = result.protected_text;
      receipt = result.receipt;
    } else if (productionMode) {
      return NextResponse.json({ error: "Privacy control plane is not configured; AI egress denied" }, { status: 503 });
    }

    const base = process.env.OLLAMA_BASE_URL;
    const model = process.env.OLLAMA_MODEL || "llama3.2:3b";
    if (base) {
      try {
        const response = await fetch(`${base.replace(/\/$/, "")}/api/generate`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            model,
            stream: false,
            prompt: `You are a concise business summarizer. Use only the protected English transcript below. Do not infer or recreate masked identifiers. Keep all [TOKENS] exactly as written.\n\n${protectedText}`,
          }),
          signal: AbortSignal.timeout(20_000),
        });
        if (response.ok) {
          const data = (await response.json()) as { response?: string };
          if (data.response) {
            return NextResponse.json({ summary: data.response, mode: "ollama", model, receipt });
          }
        }
      } catch {
        // Production fails closed below. Development may use a deterministic safe fallback.
      }
    }

    if (productionMode) {
      return NextResponse.json({ error: "Approved local AI destination is unavailable; egress denied" }, { status: 503 });
    }
    return NextResponse.json({
      summary: fallback[String(body.industry)] || "The protected conversation was processed successfully. Sensitive identifiers were tokenized before summary generation.",
      mode: "safe-fallback",
      model: null,
      receipt,
    });
  } catch (error) {
    if (error instanceof RequestBodyError) {
      return NextResponse.json({ error: error.message }, { status: error.status });
    }
    return NextResponse.json({ error: "Protected summary service unavailable" }, { status: 503 });
  }
}
