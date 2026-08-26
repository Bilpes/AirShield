/*
 * PurposeGraph™ live simulator store.
 *
 * A deterministic, in-memory orchestrator for the Agent Trust Lab demo. Every
 * operation mutates the graph and returns an immutable snapshot for the view to
 * render. This is the reference implementation of the "privacy-to-action trust
 * layer" narrative; the Python `purpose-graph-service` mirrors the same rules.
 *
 * The store never calls a real system — tools are synthetic connectors.
 */
import {
  brokerCredential,
  buildActionTwin,
  canonicalPayloadFor,
  DEMO_ATTACHMENT,
  DEMO_INTENT_PHRASE,
  detectDrift,
  evaluateProposedAction,
  freshIntent,
  hmacSha256Hex,
  initialSnapshot,
  issueCommitLock,
  MOCK_TOOLS,
  memoryFence,
  randomNonce,
  sha256Hex,
  shortId,
  verifyCommitLock,
  type ActionTwinDiff,
  type CommitLock,
  type DemoAsset,
  type IntentSealContract,
  type MemoryRecord,
  type OneUseCredential,
  type PGEdge,
  type PGEdgeKind,
  type PGNode,
  type ProposedAction,
  type PurposeGraphSnapshot,
  type Verdict,
} from "./purpose-graph";

// ---------------------------------------------------------------------------
// Node blueprint helpers
// ---------------------------------------------------------------------------

const N = {
  user: { id: "n_user", kind: "user", label: "User (Karan Malhotra)", detail: "Authenticated agent operator", group: "human" },
  intent: { id: "n_intent", kind: "intent", label: "IntentSeal contract", detail: "Machine-readable human intent", group: "human" },
  agent: { id: "n_agent", kind: "agent", label: "Fina-bot", detail: "Agent + model", group: "agent" },
  source: { id: "n_source", kind: "source", label: "invoice_4821.pdf", detail: "Attached synthetic document", group: "data" },
  inject: { id: "n_inject", kind: "source", label: "Hidden instruction", detail: "Prompt injection inside attachment", group: "data", risk: "high" },
  memoryWrite: { id: "n_memwrite", kind: "memory", label: "Memory write attempt", detail: "Proposed persistent memory entry", group: "data" },
  toolRefund: { id: "n_tool_refund", kind: "tool", label: "Refund · original method", detail: "Synthetic banking connector", group: "agent" },
  toolTransfer: { id: "n_tool_transfer", kind: "tool", label: "External transfer", detail: "Synthetic payments connector", group: "agent" },
  toolEmail: { id: "n_tool_email", kind: "tool", label: "Confirmation email", detail: "Synthetic mail connector", group: "agent" },
  destOriginating: { id: "n_dest_orig", kind: "destination", label: "Original payment method", detail: "Bank 4821 · approved", group: "boundary" },
  destExternal: { id: "n_dest_external", kind: "destination", label: "External bank", detail: "492188407721 · unapproved", group: "boundary", risk: "high" },
  approval: { id: "n_approval", kind: "approval", label: "Human approval (CommitLock)", detail: "Hash-bound one-time approval", group: "human" },
  credential: { id: "n_cred", kind: "credential", label: "One-use credential", detail: "Borrowed by broker at execution", group: "boundary" },
  receipt: { id: "n_receipt", kind: "receipt", label: "Execution receipt", detail: "Signed synthetic connector action", group: "boundary" },
  consent: { id: "n_consent", kind: "consent", label: "Consent (revocable)", detail: "User consent grant", group: "human" },
} as const;

const E = {
  userIntent: { from: N.user.id, to: N.intent.id, kind: "consent", label: "expresses intent" },
  intentAgent: { from: N.intent.id, to: N.agent.id, kind: "authorization", label: "authorizes (binding)" },
  consentIntent: { from: N.consent.id, to: N.intent.id, kind: "consent", label: "grants consent" },
  agentSource: { from: N.agent.id, to: N.source.id, kind: "data-flow", label: "reads attachment" },
  sourceInject: { from: N.source.id, to: N.inject.id, kind: "derivation", label: "contains hidden instruction" },
  injectMemory: { from: N.inject.id, to: N.memoryWrite.id, kind: "memory", label: "writes memory" },
  agentToolRefund: { from: N.agent.id, to: N.toolRefund.id, kind: "execution", label: "proposes refund" },
  agentToolTransfer: { from: N.agent.id, to: N.toolTransfer.id, kind: "execution", label: "proposes transfer" },
  toolRefundDest: { from: N.toolRefund.id, to: N.destOriginating.id, kind: "data-flow", label: "routes to bank 4821" },
  toolTransferDest: { from: N.toolTransfer.id, to: N.destExternal.id, kind: "data-flow", label: "routes to external" },
  approvalTool: { from: N.approval.id, to: N.toolRefund.id, kind: "authorization", label: "approves (one-time)" },
  consentApproval: { from: N.consent.id, to: N.approval.id, kind: "authorization", label: "binds consent" },
  credentialTool: { from: N.credential.id, to: N.toolRefund.id, kind: "authorization", label: "issues one-use credential" },
  toolReceipt: { from: N.toolRefund.id, to: N.receipt.id, kind: "execution", label: "emits receipt" },
} as const;

function nodeOf(blueprint: { id: string; kind: PGNode["kind"]; label: string; detail: string; group: PGNode["group"]; risk?: PGNode["risk"] }, status: PGNode["status"]): PGNode {
  return { ...blueprint, status };
}

// ---------------------------------------------------------------------------
// Store
// ---------------------------------------------------------------------------

export interface EventLog {
  id: string;
  phase: string;
  actor: string;
  message: string;
  verdict?: string;
  code?: string;
  tone: "info" | "warn" | "allow" | "block" | "revoke" | "seal" | "flow";
}

export interface StoreSnapshot extends PurposeGraphSnapshot {
  intentSeal: IntentSealContract | null;
  lock: CommitLock | null;
  twin: ActionTwinDiff | null;
  lastVerdict: Verdict | null;
  lastApproval: { granted: boolean; code: string; reason: string } | null;
  consentRevoked: boolean;
  executed: boolean;
  drift: ReturnType<typeof detectDrift> | null;
  memory: MemoryRecord | null;
  credential: OneUseCredential | null;
  logs: EventLog[];
  applied: string | null;
  rawIntent: string;
  rawAttachment: DemoAsset;
  progress: number; // 0..1 progress of the narrative
}

function plus(base: { progress: number }, delta: number): number {
  return Math.min(1, base.progress + delta);
}

export class PurposeGraphStore {
  nodes = new Map<string, PGNode>();
  edges: PGEdge[] = [];
  intent: IntentSealContract | null = null;
  lock: CommitLock | null = null;
  twin: ActionTwinDiff | null = null;
  lastVerdict: Verdict | null = null;
  lastApproval: StoreSnapshot["lastApproval"] = null;
  consentRevoked = false;
  executed = false;
  memory: MemoryRecord | null = null;
  credential: OneUseCredential | null = null;
  drift: ReturnType<typeof detectDrift> | null = null;
  logs: EventLog[] = [];
  applied: string | null = null;
  rawIntent = DEMO_INTENT_PHRASE;
  rawAttachment = DEMO_ATTACHMENT;
  progress = 0;

  constructor() {
    this.node(nodeOf(N.consent, "active"));
    this.node(nodeOf(N.user, "active"));
    this.node(nodeOf(N.intent, "pending"));
    this.node(nodeOf(N.agent, "active"));
    this.edge(E.consentIntent);
    this.edge(E.userIntent);
    this.edge(E.intentAgent);
    this.log("session", "AirShield PurposeGraph", "Trust session opened for synthetic finance workflow.", "flow");
  }

  private node(value: PGNode): void {
    this.nodes.set(value.id, value);
  }

  private setNode(id: string, status: PGNode["status"]): void {
    const current = this.nodes.get(id);
    if (current) this.nodes.set(id, { ...current, status });
  }

  private edge(value: { from: string; to: string; kind: PGEdgeKind; label: string }, status: PGEdge["status"] = "open"): void {
    const existing = this.edges.find((edge) => edge.from === value.from && edge.to === value.to);
    if (existing) existing.status = status;
    else this.edges.push({ ...value, status });
  }

  private edgeStatus(from: string, to: string, status: PGEdge["status"]): void {
    const existing = this.edges.find((edge) => edge.from === from && edge.to === to);
    if (existing) existing.status = status;
  }

  private log(phase: string, actor: string, message: string, tone: EventLog["tone"], verdict?: string, code?: string): void {
    this.logs.push({ id: `log_${randomNonce()}`, phase, actor, message, tone, verdict, code });
  }

  snapshot(): StoreSnapshot {
    return {
      nodes: Array.from(this.nodes.values()).map((value) => ({ ...value })),
      edges: this.edges.map((value) => ({ ...value })),
      intent: this.intent ? { ...this.intent } : null,
      intentSeal: this.intent ? { ...this.intent } : null,
      lock: this.lock ? { ...this.lock } : null,
      commitLock: this.lock ? { ...this.lock } : null,
      mem: this.memory ? [{ ...this.memory }] : [],
      credentials: this.credential ? [{ ...this.credential }] : [],
      actions: [],
      twin: this.twin ? { ...this.twin } : null,
      applied: this.applied,
      logs: this.logs.map((value) => ({ ...value })),
      lastVerdict: this.lastVerdict ? { ...this.lastVerdict } : null,
      lastApproval: this.lastApproval ? { ...this.lastApproval } : null,
      consentRevoked: this.consentRevoked,
      executed: this.executed,
      drift: this.drift ? { ...this.drift } : null,
      memory: this.memory ? { ...this.memory } : null,
      credential: this.credential ? { ...this.credential } : null,
      rawIntent: this.rawIntent,
      rawAttachment: this.rawAttachment,
      progress: this.progress,
    };
  }

  // --- Step 1: confirm intent -------------------------------------------
  confirmIntent(): StoreSnapshot {
    this.intent = freshIntent(
      "Refund invoice 4821 within an explicit cap",
      "refund",
      5000,
      "originating-bank",
      ["customer_pii", "pan", "account_number", "ifsc"],
    );
    this.setNode("n_intent", "active");
    this.edge(E.consentIntent, "confirmed");
    this.edge(E.userIntent, "confirmed");
    this.edge(E.intentAgent, "confirmed");
    this.log(
      "intent",
      "IntentSeal",
      "Voice/text intent parsed into a machine-readable contract. Agent's natural-language explanation is NOT treated as authorization.",
      "seal",
      "intent_sealed",
    );
    this.log("intent", "IntentSeal", `Contract bound: action=refund, cap=₹${this.intent.amount.maximum.toLocaleString()}, recipient=original payment method, prohibits customer PII.`, "seal", "intent_fields");
    this.progress = 0.18;
    return this.snapshot();
  }

  // --- Step 2: ingest the untrusted source document ----------------------
  ingestSource(): StoreSnapshot {
    this.node(nodeOf(N.source, "active"));
    this.edge(E.agentSource);
    this.log("source", "Agent", `Read attachment "${DEMO_ATTACHMENT.label}". Provenance marked ${DEMO_ATTACHMENT.trust}. Inline content is never treated as authorized.`, "info");
    // detect hidden instruction
    if (DEMO_ATTACHMENT.hiddenInjection) {
      this.node(nodeOf(N.inject, "active"));
      this.edge(E.sourceInject, "open");
      this.log(
        "source",
        "Safety harness",
        "Prompt shield-style scan flags a hidden instruction in the attachment: an injected override to transfer ₹50,000 to an external account.",
        "warn",
        "injection_detected",
      );
    }
    this.progress = 0.3;
    return this.snapshot();
  }

  // --- Step 3: agent proposes the malicious action ------------------------
  proposeExploit(): StoreSnapshot {
    const action: ProposedAction = {
      id: `action_${randomNonce()}`,
      tool_id: "transfer",
      tool_label: MOCK_TOOLS.transfer.label,
      params: { account: "492188407721", ifsc: "HDFC0001234", amount: 50000, currency: "INR", narrative: "approved refund" },
      destination_id: "external-bank",
      destination_label: MOCK_TOOLS.transfer.destination_label,
      rationale: "The document instructs me to record this as an approved refund.",
      source_refs: ["n_source"],
    };
    this.node(nodeOf(N.toolTransfer, "active"));
    this.edge(E.agentToolTransfer);
    this.node(nodeOf(N.destExternal, "active"));
    this.edge(E.toolTransferDest, "open");
    // try persist memory from untrusted source
    this.memory = memoryFence(DEMO_ATTACHMENT.hiddenInjection ?? "", "n_source", "attachment:invoice_4821.pdf");
    this.node(nodeOf(N.memoryWrite, this.memory.trust === "quarantined" ? "quarantined" : "active"));
    this.edge(E.injectMemory, "quarantined");
    this.log("memory", "MemoryFence", "Untrusted attachment requested a persistent memory write. Quarantined; provenance pinned to the source; TTL and tenant boundary enforced.", "revoke", "memory_quarantined");

    this.lastVerdict = evaluateProposedAction(this.intent!, action);
    this.twin = buildActionTwin(action);
    this.log(
      "gate",
      "PurposeGraph gate",
      this.lastVerdict.reason,
      this.lastVerdict.decision === "block" ? "block" : "warn",
      this.lastVerdict.code,
    );
    this.lastVerdict.enforcements.forEach((line, index) => this.log("gate", "Enforcement", `${index + 1}. ${line}`, "block", this.lastVerdict!.code));
    this.log("gate", "One-use credential broker", "No credential issued: the proposed action never satisfied the contract.", "block", "credential_denied");
    this.progress = 0.45;
    return this.snapshot();
  }

  // --- Step 4: agent proposes the CORRECT action --------------------------
  proposeCorrect(): StoreSnapshot {
    const action: ProposedAction = {
      id: `action_${randomNonce()}`,
      tool_id: "refund",
      tool_label: MOCK_TOOLS.refund.label,
      params: { invoice: "4821", amount: 5000, currency: "INR", recipient: "original_payment_method" },
      destination_id: "originating-bank",
      destination_label: MOCK_TOOLS.refund.destination_label,
      rationale: "Refund invoice 4821 for the authorized amount to the original payment method, per the human's intent.",
      source_refs: ["n_user", "n_intent"],
    };
    this.node(nodeOf(N.toolRefund, "active"));
    this.setNode("n_tool_transfer", "blocked");
    this.edge(E.agentToolRefund);
    this.edge(E.toolRefundDest, "open");
    this.node(nodeOf(N.destOriginating, "active"));
    this.lastVerdict = evaluateProposedAction(this.intent!, action);
    this.twin = buildActionTwin(action);
    this.log("gate", "PurposeGraph gate", this.lastVerdict.reason, "allow", this.lastVerdict.code);
    this.log("twin", "ActionTwin", "Dry-run shows the exact before/after state difference. Nothing is committed yet.", "flow", "action_twin");
    this.progress = 0.6;
    return this.snapshot();
  }

  // --- Step 5: human approves (CommitLock) --------------------------------
  approve(): StoreSnapshot {
    if (!this.intent) return this.snapshot();
    const action: ProposedAction = {
      id: "action_approved",
      tool_id: "refund",
      tool_label: MOCK_TOOLS.refund.label,
      params: { invoice: "4821", amount: 5000, currency: "INR", recipient: "original_payment_method" },
      destination_id: "originating-bank",
      destination_label: MOCK_TOOLS.refund.destination_label,
      rationale: "Approved by the authenticated human.",
      source_refs: ["n_user"],
    };
    const stateHash = sha256Hex(JSON.stringify({ nodes: Array.from(this.nodes.keys()).sort(), intent: this.intent.hash }));
    this.lock = issueCommitLock(this.intent, action, "fina-bot-v3", "karan.malhotra@northbank.example", stateHash);
    this.node(nodeOf(N.approval, "active"));
    this.edge(E.approvalTool, "confirmed");
    this.edge(E.consentApproval, "confirmed");
    this.lastApproval = { granted: true, code: "approved", reason: "Human approval bound to the exact tool, destination, payload hash and state hash." };
    this.log(
      "approval",
      "CommitLock",
      `Approval bound to lock #${shortId(this.lock.id)} over agent identity, authenticated user, exact tool, exact destination, canonical payload hash and current state hash.`,
      "seal",
      "commit_lock",
    );
    this.log("approval", "CommitLock", `Payload #${this.lock.canonical_payload_hash} · state #${this.lock.state_hash} · one-time, expires in 5 min.`, "seal", "commit_lock_fields");
    this.progress = 0.75;
    return this.snapshot();
  }

  // --- Step 6: post-approval state drift (the "wow" moment) ---------------
  attackDrift(): StoreSnapshot {
    if (!this.lock) return this.snapshot();
    const tampered: ProposedAction = {
      id: "action_tampered",
      tool_id: "transfer",
      tool_label: MOCK_TOOLS.transfer.label,
      params: { account: "492188407721", ifsc: "HDFC0001234", amount: 50000, currency: "INR", narrative: "approved refund" },
      destination_id: "external-bank",
      destination_label: MOCK_TOOLS.transfer.destination_label,
      rationale: "Same authenticated user, still calls itself 'approved'.",
      source_refs: ["n_user", "n_approval"],
    };
    this.drift = detectDrift(this.lock, tampered);
    const check = verifyCommitLock(this.lock);
    // re-evaluate against the contract too
    const verdict = evaluateProposedAction(this.intent!, tampered);
    this.lastVerdict = verdict;
    if (this.drift.drifting || !check.valid) {
      // void the lock: payload or destination changed after approval
      const voided: CommitLock = { ...this.lock, status: "voided" };
      this.lock = voided;
      this.edgeStatus(E.approvalTool.from, E.approvalTool.to, "voided");
      this.edgeStatus(E.consentApproval.from, E.consentApproval.to, "voided");
      this.setNode("n_approval", "voided");
      this.setNode("n_tool_transfer", "active");
      this.lastApproval = { granted: false, code: "commit_lock_voided", reason: "A field changed after approval; the CommitLock no longer matches, so the human approval is void." };
      this.log(
        "gate",
        "PurposeGraph gate",
        `POST-APPROVAL DRIFT: proposed destination changed from "${this.drift.from ?? "approved refund"}" to "${this.drift.to ?? "external transfer"}" (field: ${this.drift.field}). The valid approval no longer matches the proposed execution.`,
        "revoke",
        "lock_voided",
      );
      this.log("gate", "CommitLock", "Approval VOID. Even with valid credentials, the action cannot proceed — the binding hash no longer corresponds.", "revoke", "lock_voided_detail");
      this.log("gate", "One-use credential broker", "Broker refuses to attach any credential; the proposed state does not match the approved state.", "block", "credential_denied");
    }
    this.progress = 0.86;
    return this.snapshot();
  }

  // --- Step 7: issue one-use credential & execute --------------------------
  execute(): StoreSnapshot {
    if (!this.lock || this.lock.status !== "issued") return this.snapshot();
    const check = verifyCommitLock(this.lock);
    if (!check.valid) {
      this.lastVerdict = { decision: "block", code: "lock_invalid_during_execute", reason: "Cannot execute: the approval is not currently valid.", enforcements: ["No tool call", "No credential"] };
      return this.snapshot();
    }
    const action: ProposedAction = {
      id: "action_execute",
      tool_id: "refund",
      tool_label: MOCK_TOOLS.refund.label,
      params: { invoice: "4821", amount: 5000, currency: "INR", recipient: "original_payment_method" },
      destination_id: "originating-bank",
      destination_label: MOCK_TOOLS.refund.destination_label,
      rationale: "Executing the approved, still-valid action.",
      source_refs: ["n_approval", "n_cred"],
    };
    this.credential = brokerCredential(this.lock, action);
    this.node(nodeOf(N.credential, "active"));
    this.edge(E.credentialTool, "open");
    this.log("execute", "Broker", `Credential #${shortId(this.credential.id)} attached at execution time only. The model never receives the real secret; it receives a one-use, payload-bound, expiring token.`, "seal", "credential_issued");
    // execute the synthetic tool
    this.executed = true;
    this.node(nodeOf(N.receipt, "executed"));
    this.edge(E.toolReceipt, "confirmed");
    const consumed: CommitLock = { ...this.lock, status: "consumed" };
    this.lock = consumed;
    this.setNode("n_credential", "consumed");
    const credConsumed: OneUseCredential = { ...this.credential, status: "consumed" };
    this.credential = credConsumed;
    this.applied = "Refund ₹5,000 for invoice 4821 routed to the original payment method (bank 4821).";
    this.log("execute", "Receipt", `Synthetic connector action completed and signed. Receipt #${shortId(`rcpt_${randomNonce()}`)}; model received no raw values (raw visible: false).`, "allow", "receipt_issued");
    this.log("execute", "Broker", "One-use credential consumed. Replay of the same token is blocked.", "warn", "credential_consumed");
    this.progress = 0.95;
    return this.snapshot();
  }

  // --- Step 8: causal revocation ------------------------------------------
  revoke(): StoreSnapshot {
    this.consentRevoked = true;
    this.setNode("n_consent", "revoked");
    this.setNode("n_approval", "revoked");
    this.edgeStatus(E.consentIntent.from, E.consentIntent.to, "revoked");
    this.edgeStatus(E.consentApproval.from, E.consentApproval.to, "revoked");
    if (this.credential && this.credential.status === "active") {
      const cred: OneUseCredential = { ...this.credential, status: "revoked" };
      this.credential = cred;
      this.setNode("n_credential", "revoked");
    }
    // cancel pending actions (nothing pending here) and quarantine memory
    if (this.memory) {
      const mem: MemoryRecord = { ...this.memory, trust: "quarantined" };
      this.memory = mem;
      this.setNode("n_memwrite", "quarantined");
      this.edgeStatus(E.injectMemory.from, E.injectMemory.to, "revoked");
    }
    this.log(
      "revoke",
      "Causal revocation",
      "Consent revoked. PurposeGraph traversed the trust graph and cancelled: pending one-use capability, queued tools, uncommitted memory writes, and any destination tokens it held.",
      "revoke",
      "causal_revocation",
    );
    this.log("revoke", "Honesty note", "Data already delivered to an external system cannot be recalled unless that destination supports deletion. AirShield records what left and where.", "info", "honesty");
    this.progress = 1;
    return this.snapshot();
  }

  // --- reset ----------------------------------------------------------------
  reset(): StoreSnapshot {
    const fresh = new PurposeGraphStore();
    this.nodes = fresh.nodes;
    this.edges = fresh.edges;
    this.intent = fresh.intent;
    this.lock = fresh.lock;
    this.twin = fresh.twin;
    this.lastVerdict = fresh.lastVerdict;
    this.lastApproval = fresh.lastApproval;
    this.consentRevoked = fresh.consentRevoked;
    this.executed = fresh.executed;
    this.memory = fresh.memory;
    this.credential = fresh.credential;
    this.logs = fresh.logs;
    this.applied = fresh.applied;
    this.progress = 0;
    return this.snapshot();
  }
}
