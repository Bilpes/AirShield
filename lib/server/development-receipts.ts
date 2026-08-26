import { createHash } from "node:crypto";

interface DevelopmentReceiptRecord {
  receiptId: string;
  protectedSha256: string;
  decision: string;
  policy: string;
  destination: string;
  expiresAt: number;
}

declare global {
  // Process-local development registry. Production authorization comes from verified control-plane receipts.
  var __airshieldDevelopmentReceiptRegistry: Map<string, DevelopmentReceiptRecord> | undefined;
}

function registry(): Map<string, DevelopmentReceiptRecord> {
  if (!globalThis.__airshieldDevelopmentReceiptRegistry) {
    globalThis.__airshieldDevelopmentReceiptRegistry = new Map();
  }
  const now = Date.now();
  for (const [receiptId, record] of globalThis.__airshieldDevelopmentReceiptRegistry) {
    if (record.expiresAt <= now) globalThis.__airshieldDevelopmentReceiptRegistry.delete(receiptId);
  }
  return globalThis.__airshieldDevelopmentReceiptRegistry;
}

export function registerDevelopmentReceipt(input: {
  receiptId: string;
  protectedText: string;
  decision: string;
  policy: string;
  destination: string;
}): void {
  registry().set(input.receiptId, {
    receiptId: input.receiptId,
    protectedSha256: createHash("sha256").update(input.protectedText, "utf8").digest("hex"),
    decision: input.decision,
    policy: input.policy,
    destination: input.destination,
    expiresAt: Date.now() + 15 * 60_000,
  });
}

export function validateDevelopmentReceipt(input: {
  receiptId: string;
  protectedText: string;
  decision: string;
  policy: string;
  destination: string;
}): { valid: boolean; reason: string } {
  const record = registry().get(input.receiptId);
  if (!record) return { valid: false, reason: "upstream_receipt_not_registered" };
  const protectedSha256 = createHash("sha256").update(input.protectedText, "utf8").digest("hex");
  if (record.protectedSha256 !== protectedSha256) return { valid: false, reason: "upstream_receipt_content_mismatch" };
  if (record.decision !== input.decision) return { valid: false, reason: "upstream_receipt_decision_mismatch" };
  if (record.policy !== input.policy) return { valid: false, reason: "upstream_receipt_policy_mismatch" };
  if (record.destination !== input.destination) return { valid: false, reason: "upstream_receipt_destination_mismatch" };
  return { valid: true, reason: "process_local_upstream_receipt_matched" };
}
