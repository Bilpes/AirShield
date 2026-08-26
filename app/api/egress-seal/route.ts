import {
  createHash,
  generateKeyPairSync,
  KeyObject,
  randomBytes,
  sign,
  verify,
} from "node:crypto";
import { NextResponse } from "next/server";
import {
  destinationProfile,
  evaluateContextFence,
  type ContextEntity,
  type DestinationId,
} from "@/lib/context-fence";
import { productionMode } from "@/lib/server/control-plane";
import { validateDevelopmentReceipt } from "@/lib/server/development-receipts";
import { readJsonBody, RequestBodyError } from "@/lib/server/request";

export const runtime = "nodejs";

interface EgressSealPayload {
  version: "egressseal/v1";
  seal_id: string;
  protected_sha256: string;
  upstream_receipt_id: string;
  policy: string;
  destination_id: DestinationId;
  destination_label: string;
  destination_route: string;
  context_risk: number;
  context_band: string;
  allowed_action: string;
  issued_at: string;
  expires_at: string;
  nonce: string;
  mode: "development-ephemeral-ed25519";
}

interface SignedSeal {
  payload: EgressSealPayload;
  signature: string;
  algorithm: "Ed25519";
  signing_key_id: string;
}

interface DevelopmentKeyPair {
  privateKey: KeyObject;
  publicKey: KeyObject;
  keyId: string;
}

declare global {
  // Development-only process key. Production EgressSeal must use an external KMS/HSM trust anchor.
  var __airshieldEgressSealDevelopmentKey: DevelopmentKeyPair | undefined;
}

const ACTIONS_BY_POLICY: Record<string, { id: string; label: string; connector: string }> = {
  "Healthcare · HIPAA": {
    id: "care.reserve-demo-slot",
    label: "Reserve synthetic virtual-care slot",
    connector: "Demo scheduling connector",
  },
  "Financial services · PCI": {
    id: "finance.open-dispute-review",
    label: "Open synthetic transaction-dispute review",
    connector: "Demo banking case connector",
  },
  "Insurance claims": {
    id: "insurance.create-claim-task",
    label: "Create synthetic claim-review task",
    connector: "Demo claims connector",
  },
  "Contact center privacy": {
    id: "contact-center.create-refund-review",
    label: "Create synthetic refund-review request",
    connector: "Demo CRM connector",
  },
  "Internal copilot DLP": {
    id: "copilot.create-incident-ticket",
    label: "Create synthetic restricted incident ticket",
    connector: "Demo ticketing connector",
  },
};

function developmentKeys(): DevelopmentKeyPair {
  if (globalThis.__airshieldEgressSealDevelopmentKey) {
    return globalThis.__airshieldEgressSealDevelopmentKey;
  }
  const { privateKey, publicKey } = generateKeyPairSync("ed25519");
  const fingerprint = createHash("sha256")
    .update(publicKey.export({ type: "spki", format: "der" }))
    .digest("hex")
    .slice(0, 16);
  const pair = { privateKey, publicKey, keyId: `egressseal-dev-${fingerprint}` };
  globalThis.__airshieldEgressSealDevelopmentKey = pair;
  return pair;
}

function encodedPayload(payload: EgressSealPayload): Buffer {
  return Buffer.from(JSON.stringify(payload), "utf8");
}

function sealSignature(payload: EgressSealPayload): SignedSeal {
  const keys = developmentKeys();
  return {
    payload,
    signature: sign(null, encodedPayload(payload), keys.privateKey).toString("base64url"),
    algorithm: "Ed25519",
    signing_key_id: keys.keyId,
  };
}

function verifySeal(seal: unknown, expectedProtectedText?: string): { valid: boolean; reason: string; seal?: SignedSeal } {
  if (!seal || typeof seal !== "object") return { valid: false, reason: "missing_seal" };
  const candidate = seal as Partial<SignedSeal>;
  if (
    !candidate.payload ||
    typeof candidate.signature !== "string" ||
    candidate.algorithm !== "Ed25519" ||
    typeof candidate.signing_key_id !== "string"
  ) {
    return { valid: false, reason: "invalid_seal_shape" };
  }
  const keys = developmentKeys();
  if (candidate.signing_key_id !== keys.keyId) return { valid: false, reason: "untrusted_development_key" };
  const validSignature = verify(
    null,
    encodedPayload(candidate.payload),
    keys.publicKey,
    Buffer.from(candidate.signature, "base64url"),
  );
  if (!validSignature) return { valid: false, reason: "signature_mismatch" };
  if (Date.parse(candidate.payload.expires_at) <= Date.now()) return { valid: false, reason: "seal_expired" };
  if (expectedProtectedText !== undefined) {
    const hash = createHash("sha256").update(expectedProtectedText, "utf8").digest("hex");
    if (hash !== candidate.payload.protected_sha256) return { valid: false, reason: "content_digest_mismatch" };
  }
  return { valid: true, reason: "signature_content_and_expiry_valid", seal: candidate as SignedSeal };
}

function jsonError(error: unknown) {
  if (error instanceof RequestBodyError) {
    return NextResponse.json({ error: error.message }, { status: error.status });
  }
  return NextResponse.json({ error: "EgressSeal control is unavailable; egress remains denied" }, { status: 503 });
}

export async function POST(request: Request) {
  try {
    const body = await readJsonBody<Record<string, unknown>>(request, 131_072);
    const operation = body.operation;
    if (!operation || !["issue", "verify", "execute"].includes(String(operation))) {
      return NextResponse.json({ error: "operation must be issue, verify, or execute" }, { status: 400 });
    }

    if (productionMode) {
      return NextResponse.json(
        {
          error: "The embedded EgressSeal signer is development-only. Configure an externally trusted KMS/HSM signer and upstream-receipt verifier for production.",
        },
        { status: 503 },
      );
    }

    if (operation === "verify") {
      const protectedText = typeof body.protected_text === "string" ? body.protected_text : undefined;
      const result = verifySeal(body.seal, protectedText);
      return NextResponse.json({ ...result, mode: "development-ephemeral-ed25519" }, { status: result.valid ? 200 : 400 });
    }

    if (operation === "execute") {
      const protectedText = typeof body.protected_text === "string" ? body.protected_text : "";
      const result = verifySeal(body.seal, protectedText);
      if (!result.valid || !result.seal) {
        return NextResponse.json({ error: `SafeAction denied: ${result.reason}` }, { status: 403 });
      }
      const actionId = typeof body.action_id === "string" ? body.action_id : "";
      const action = ACTIONS_BY_POLICY[result.seal.payload.policy];
      if (!action || action.id !== actionId || result.seal.payload.allowed_action !== actionId) {
        return NextResponse.json({ error: "SafeAction denied: action is not allowlisted by the sealed policy" }, { status: 403 });
      }
      if (result.seal.payload.destination_id === "public-general-ai") {
        return NextResponse.json({ error: "SafeAction denied: public destination cannot invoke trusted connectors" }, { status: 403 });
      }
      const tokens = [...new Set(protectedText.match(/\[[A-Z][A-Z0-9_]{1,48}\]/g) ?? [])].slice(0, 6);
      const actionReceiptPayload = {
        version: "safeaction/v1",
        action_receipt_id: `act_${randomBytes(7).toString("hex")}`,
        parent_seal_id: result.seal.payload.seal_id,
        action_id: action.id,
        action_label: action.label,
        connector: action.connector,
        destination_id: result.seal.payload.destination_id,
        token_references: tokens,
        raw_values_visible_to_model: false,
        resolution_mode: "connector-only synthetic demonstration",
        executed_at: new Date().toISOString(),
        outcome: "simulated_success",
      };
      const keys = developmentKeys();
      const actionSignature = sign(
        null,
        Buffer.from(JSON.stringify(actionReceiptPayload), "utf8"),
        keys.privateKey,
      ).toString("base64url");
      return NextResponse.json({
        status: "simulated_success",
        action: actionReceiptPayload,
        signature: actionSignature,
        algorithm: "Ed25519",
        signing_key_id: keys.keyId,
        broker_checks: [
          "EgressSeal signature, expiry, and protected-content digest verified",
          "Destination and action matched the sealed allowlist",
          "Only protected token references entered the broker",
          "Resolution remained connector-only; no raw value returned to the model",
          "Synthetic action receipt signed",
        ],
      });
    }

    const protectedText = typeof body.protected_text === "string" ? body.protected_text : "";
    const policy = typeof body.policy === "string" ? body.policy : "";
    const destinationId = typeof body.destination_id === "string" ? body.destination_id as DestinationId : "public-general-ai";
    const destinationRoute = typeof body.destination_route === "string" ? body.destination_route : "";
    const decision = typeof body.decision === "string" ? body.decision : "review";
    const upstreamReceiptId = typeof body.upstream_receipt_id === "string" ? body.upstream_receipt_id : "";
    const entities = Array.isArray(body.entities)
      ? body.entities.filter((entity): entity is ContextEntity => Boolean(entity && typeof entity === "object"))
      : [];
    const destination = destinationProfile(destinationId);
    const action = ACTIONS_BY_POLICY[policy];
    if (!protectedText || !policy || !destination || !destinationRoute || !action) {
      return NextResponse.json({ error: "protected_text, supported policy, destination_id, and destination_route are required" }, { status: 400 });
    }

    const contextFence = evaluateContextFence(protectedText, entities, destination.id);
    const receiptCheck = validateDevelopmentReceipt({
      receiptId: upstreamReceiptId,
      protectedText,
      decision,
      policy,
      destination: destinationRoute,
    });
    const reasons: string[] = [];
    if (!receiptCheck.valid) reasons.push(receiptCheck.reason);
    if (decision !== "allow") reasons.push(`upstream_decision_${decision}`);
    if (!upstreamReceiptId) reasons.push("missing_upstream_receipt");
    if (destination.status === "blocked") reasons.push("destination_not_approved");
    if (contextFence.disposition !== "allow") reasons.push(`context_fence_${contextFence.disposition}`);

    if (reasons.length) {
      const blockingReason = reasons.some((reason) =>
        reason.startsWith("upstream_receipt_") || reason.includes("blocked") || reason.includes("block"),
      );
      return NextResponse.json({
        issued: false,
        decision: blockingReason ? "block" : "review",
        reasons,
        context_fence: contextFence,
        destination,
        message: "EgressSeal was not issued; protected content remains inside the trust boundary.",
      });
    }

    const now = Date.now();
    const payload: EgressSealPayload = {
      version: "egressseal/v1",
      seal_id: `egs_${randomBytes(8).toString("hex")}`,
      protected_sha256: createHash("sha256").update(protectedText, "utf8").digest("hex"),
      upstream_receipt_id: upstreamReceiptId,
      policy,
      destination_id: destination.id,
      destination_label: destination.label,
      destination_route: destinationRoute,
      context_risk: contextFence.score,
      context_band: contextFence.band,
      allowed_action: action.id,
      issued_at: new Date(now).toISOString(),
      expires_at: new Date(now + 10 * 60_000).toISOString(),
      nonce: randomBytes(12).toString("base64url"),
      mode: "development-ephemeral-ed25519",
    };
    return NextResponse.json({
      issued: true,
      decision: "allow",
      seal: sealSignature(payload),
      context_fence: contextFence,
      destination,
      safe_action: action,
      warning: "Hackathon demonstration: the Ed25519 key is process-local. Production requires a trusted external KMS/HSM key and upstream receipt verification.",
    });
  } catch (error) {
    return jsonError(error);
  }
}
