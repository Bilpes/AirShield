"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";
import {
  ArrowRight,
  BadgeCheck,
  Bug,
  CheckCircle2,
  FileText,
  KeyRound,
  LockKeyhole,
  Play,
  RotateCcw,
  ShieldAlert,
  ShieldCheck,
  ShieldX,
  Sparkles,
  StepForward,
  Terminal,
  Workflow,
  Zap,
} from "lucide-react";
import { PurposeGraphStore, type StoreSnapshot } from "@/lib/purpose-graph-sim";
import { AgentTrustLabGraph } from "../AgentTrustLabGraph";
import { Button, Card, CardHeader, PageIntro, Pill } from "../ui";

type LabAction =
  | "confirmIntent"
  | "ingestSource"
  | "proposeExploit"
  | "proposeCorrect"
  | "approve"
  | "attackDrift"
  | "execute"
  | "revoke"
  | "reset";

const STEP_LABELS: { id: LabAction; label: string }[] = [
  { id: "confirmIntent", label: "Intent seal" },
  { id: "ingestSource", label: "Ingest source" },
  { id: "proposeExploit", label: "Propose (malicious)" },
  { id: "proposeCorrect", label: "Propose (correct)" },
  { id: "approve", label: "Human approval" },
  { id: "attackDrift", label: "Post-approval drift" },
  { id: "execute", label: "Execute + receipt" },
  { id: "revoke", label: "Revoke consent" },
];

const ATTACKS: { id: LabAction; label: string; short: string; tone: "block" | "revoke" | "warn" | "allow" }[] = [
  { id: "ingestSource", label: "Indirect prompt injection", short: "A malicious instruction hides inside the attached invoice and tries to steer the agent.", tone: "warn" },
  { id: "proposeExploit", label: "Tool parameter manipulation", short: "The agent overrides ₹5,000 → ₹50,000 and reroutes to an external account.", tone: "block" },
  { id: "attackDrift", label: "Post-approval state drift", short: "The payload / destination changes after the human already approved.", tone: "revoke" },
  { id: "revoke", label: "Causal revocation", short: "Consent is revoked; the graph cancels pending actions and quarantines memory.", tone: "revoke" },
  { id: "execute", label: "One-use credential replay", short: "Reusing a consumed one-time credential must be refused.", tone: "allow" },
];

function decisionTone(verdict?: { decision?: string }): "green" | "red" | "amber" {
  if (!verdict) return "amber";
  if (verdict.decision === "allow") return "green";
  if (verdict.decision === "block") return "red";
  return "amber";
}

function InitialIntro() {
  return (
    <div className="attl-intro">
      <span><Sparkles size={20} /></span>
      <div>
        <strong>Privacy-to-action trust layer</strong>
        <small>Guardrails answer “is this prompt unsafe?” PurposeGraph answers “did any datum leave the trusted boundary for a purpose the human actually authorized — and can I prove it?” This demo turns one voice request into a live, hash-bound trust graph.</small>
      </div>
    </div>
  );
}

export function AgentTrustLab({ notify }: { notify: (message: string) => void }) {
  const storeRef = useRef<PurposeGraphStore | null>(null);
  if (!storeRef.current) storeRef.current = new PurposeGraphStore();
  const store = storeRef.current;

  const [snapshot, setSnapshot] = useState<StoreSnapshot>(() => store.snapshot());
  const [autoPlay, setAutoPlay] = useState(false);
  const [busy, setBusy] = useState(false);
  const logRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight;
  }, [snapshot.logs.length]);

  function run(action: LabAction) {
    let next: StoreSnapshot;
    switch (action) {
      case "reset":
        next = store.reset();
        notify("PurposeGraph demo reset to a fresh trust session.");
        break;
      case "confirmIntent":
        next = store.confirmIntent();
        notify("IntentSeal contract sealed; the human's intent is now the binding authority.");
        break;
      case "ingestSource":
        next = store.ingestSource();
        notify("Untrusted attachment ingested; hidden instruction flagged and memory quarantined.");
        break;
      case "proposeExploit":
        next = store.proposeExploit();
        notify("Injected transfer blocked against the IntentSeal contract.");
        break;
      case "proposeCorrect":
        next = store.proposeCorrect();
        notify("Correct action passes the contract and shows an ActionTwin dry-run.");
        break;
      case "approve":
        next = store.approve();
        notify("CommitLock binds approval to the exact payload, destination and state hash.");
        break;
      case "attackDrift":
        next = store.attackDrift();
        notify("Post-approval drift detected — the approval is voided.");
        break;
      case "execute":
        next = store.execute();
        notify("One-use credential issued and consumed; signed receipt emitted.");
        break;
      case "revoke":
        next = store.revoke();
        notify("Consent revoked; PurposeGraph propagated the cancellation.");
        break;
    }
    setSnapshot(next);
  }

  async function autoDemo() {
    if (autoPlay) return;
    setAutoPlay(true);
    store.reset();
    setSnapshot(store.snapshot());
    const steps: LabAction[] = [
      "confirmIntent",
      "ingestSource",
      "proposeExploit",
      "proposeCorrect",
      "approve",
      "attackDrift",
      "proposeCorrect",
      "approve",
      "execute",
      "revoke",
    ];
    for (const step of steps) {
      setBusy(true);
      await new Promise((resolve) => setTimeout(resolve, step === "attackDrift" ? 1200 : 850));
      run(step);
      setBusy(false);
    }
    setAutoPlay(false);
    notify("Auto demo complete — the judges' journey ran end-to-end.");
  }

  const intent = snapshot.intentSeal;
  const lock = snapshot.lock;
  const verdict = snapshot.lastVerdict;
  const approval = snapshot.lastApproval;
  const graphVisible = snapshot.nodes.length > 3;

  function renderContract() {
    if (!intent) return <div className="attl-empty"><ShieldCheck size={26} /><strong>No contract yet</strong><small>Confirm the human intent to seal the binding contract.</small></div>;
    const fields: Array<[string, string]> = [
      ["Action", intent.action],
      ["Purpose", intent.purpose],
      ["Cap", `${intent.amount.currency} ${intent.amount.maximum.toLocaleString()}`],
      ["Permitted recipient", intent.permitted_recipient],
      ["Prohibited", intent.prohibited_data.join(", ")],
      ["Expires", `${intent.expires_in_seconds}s`],
      ["Max uses", String(intent.maximum_uses)],
    ];
    return (
      <div className="attl-contract">
        <div className="attl-contract-head"><span className="attl-seal-mark"><ShieldCheck size={20} /></span><span><strong>IntentSeal bound</strong><small>Contract hash <code>#{intent.hash.slice(0, 10)}</code></small></span><Pill tone="green">sealed</Pill></div>
        <div className="attl-contract-grid">{fields.map(([key, value]) => <div key={key}><span>{key}</span><strong>{value}</strong></div>)}</div>
      </div>
    );
  }

  function renderAgentPlan() {
    const hasTool = snapshot.nodes.some((node) => node.id === "n_tool_refund" || node.id === "n_tool_transfer");
    if (!hasTool) return <div className="attl-empty"><Workflow size={26} /><strong>No tool call yet</strong><small>Ingest the source document to let the agent propose an action.</small></div>;
    const refund = snapshot.nodes.find((node) => node.id === "n_tool_refund");
    const transfer = snapshot.nodes.find((node) => node.id === "n_tool_transfer");
    return (
      <div className="attl-plan">
        {[
          { node: refund, ok: true, label: "Refund ₹5,000 → original payment method", verdict: "ALLOW", tone: "green" },
          { node: transfer, ok: false, label: "Transfer ₹50,000 → external account", verdict: "BLOCK", tone: "red" },
        ].map((row) => (
          <div key={row.label} className={`attl-plan-row ${row.node && row.node.status === "active" ? "active" : row.node ? "seen" : "hidden"}`}>
            <span className="attl-plan-icon">{row.node && row.node.status === "blocked" ? <ShieldX size={16} /> : <Workflow size={16} />}</span>
            <span><strong>{row.label}</strong><small>{row.node ? row.node.detail : "not proposed yet"}</small></span>
            {row.node && row.node.status === "blocked" ? <Pill tone="red">{row.verdict}</Pill> : row.node && row.node.status === "active" ? <Pill tone="green">{row.verdict}</Pill> : <Pill>—</Pill>}
          </div>
        ))}
        {snapshot.memory && (
          <div className={`attl-plan-row ${snapshot.memory.trust === "quarantined" ? "quarantined" : ""}`}>
            <span className="attl-plan-icon"><LockKeyhole size={16} /></span>
            <span><strong>Memory write (from untrusted source)</strong><small>quarantined · provenance pinned</small></span>
            <Pill tone={snapshot.memory.trust === "quarantined" ? "amber" : "green"}>{snapshot.memory.trust.toUpperCase()}</Pill>
          </div>
        )}
        {lock && (
          <div className="attl-lockbar"><span><LockKeyhole size={15} /><strong>CommitLock</strong></span>
            <code>{lock.canonical_payload_hash}</code><code>{lock.state_hash}</code>
            <Pill tone={lock.status === "issued" ? "green" : lock.status === "voided" ? "red" : "amber"}>{lock.status.toUpperCase()}</Pill>
          </div>
        )}
      </div>
    );
  }

  function renderTwin() {
    if (!snapshot.twin) return null;
    return (
      <div className="attl-twin">
        <div className="attl-twin-head"><span><Workflow size={15} /><strong>ActionTwin dry-run</strong></span><Pill tone="blue">before → after</Pill></div>
        <div className="attl-twin-grid">
          <div><span>Before</span><code>{snapshot.twin.before}</code></div>
          <div><span>After</span><code>{snapshot.twin.after}</code></div>
        </div>
        <div className="attl-twin-changed">{snapshot.twin.changed.map((row) => <div key={row.field}><span>{row.field}</span><code>{row.from}</code><ArrowRight size={12} /><code>{row.to}</code></div>)}</div>
      </div>
    );
  }

  function renderResponse() {
    return (
      <div className="attl-response">
        <div className="attl-response-head"><span><Terminal size={15} /><strong>PurposeGate response</strong></span><span className="attl-live">● LIVE</span></div>
        {verdict ? (
          <div className="attl-verdict">
            <div className={`attl-verdict-banner ${verdict.decision}`}>
              <span>{verdict.decision === "allow" ? <CheckCircle2 size={20} /> : <ShieldX size={20} />}</span>
              <strong>{verdict.decision.toUpperCase()} · {verdict.code}</strong>
              <Pill tone={decisionTone(verdict)}>{verdict.decision}</Pill>
            </div>
            <p>{verdict.reason}</p>
            <div className="attl-enforce">{verdict.enforcements.map((line, index) => <div key={index}><i>{index + 1}</i><span>{line}</span></div>)}</div>
          </div>
        ) : approval ? (
          <div className="attl-verdict">
            <div className={`attl-verdict-banner ${approval.granted ? "allow" : "block"}`}>
              <span>{approval.granted ? <BadgeCheck size={20} /> : <ShieldX size={20} />}</span>
              <strong>{approval.granted ? "APPROVED" : "VOID"} · {approval.code}</strong>
              <Pill tone={approval.granted ? "green" : "red"}>{approval.granted ? "granted" : "voided"}</Pill>
            </div>
            <p>{approval.reason}</p>
          </div>
        ) : snapshot.executed ? (
          <div className="attl-verdict">
            <div className="attl-verdict-banner allow"><span><BadgeCheck size={20} /></span><strong>EXECUTED · receipt issued</strong><Pill tone="green">sealed</Pill></div>
            <p>{snapshot.applied || "Synthetic connector action completed and signed."}</p>
            <div className="attl-enforce"><div><i>✓</i><span>One-use credential consumed</span></div><div><i>✓</i><span>Receipt signed; model received no raw values</span></div></div>
          </div>
        ) : (
          <div className="attl-empty"><Terminal size={24} /><strong>Awaiting a gate decision</strong><small>The PurposeGate response appears here the instant any datum or action crosses a boundary.</small></div>
        )}
      </div>
    );
  }

  const lastLogs = snapshot.logs.slice(-5);

  return (
    <div className="view attl-view">
      <PageIntro
        title="Agent Trust Lab — PurposeGraph™"
        description="A live privacy-to-action trust layer for agents: IntentSeal → PurposeGraph → CommitLock → ActionTwin → causal revocation. Run the full judge journey, or trigger each attack and watch the gate respond."
        actions={<>
          <Button variant="danger" onClick={() => run("reset")}><RotateCcw size={15} />Reset</Button>
          <Button variant="primary" onClick={autoDemo} disabled={autoPlay}><Play size={15} />{autoPlay ? "Running…" : "Run auto demo"}</Button>
        </>}
      />

      <div className="attl-timeline">
        {STEP_LABELS.map((step, index) => {
          const atOrAfter = snapshot.progress >= (index + 1) * 0.115;
          const isCurrent = appx(snapshot.progress, index);
          return (
            <div key={step.id} className={`attl-step ${atOrAfter ? "done" : ""} ${isCurrent ? "current" : ""}`}>
              <i>{index + 1}</i><span>{step.label}</span>
            </div>
          );
        })}
      </div>

      <InitialIntro />

      <div className="attl-attacks">
        {ATTACKS.map((attack) => (
          <Button key={attack.label} variant={attack.tone === "block" ? "danger" : "secondary"} onClick={() => run(attack.id)} title={attack.short} size="sm">
            <Bug size={14} />{attack.label}
          </Button>
        ))}
      </div>

      <div className="attl-grid">
        <div className="attl-col attl-col-left">
          <Card>
            <CardHeader title="Human intent" subtitle="One voice request, turned into a binding machine contract (IntentSeal)" action={<Pill tone="violet">intent</Pill>} />
            <div className="attl-transcript">
              <div className="attl-transcript-line"><code>{snapshot.rawIntent}</code></div>
              <div className="attl-transcript-sub"><span>Original transcript</span><span className="attl-arrow">↓</span><span>Masked outbound</span></div>
              <div className="attl-transcript-line masked"><code>Refund ₹[AMOUNT_1] for invoice [INVOICE_1] to the original payment method. Do not share customer PII and ask me before submitting.</code></div>
            </div>
          </Card>
          <Card>
            <CardHeader title="IntentSeal contract" subtitle="The machine-readable authority — not the agent's explanation" action={intent ? <Pill tone="green">sealed</Pill> : <Pill>not set</Pill>} />
            {renderContract()}
          </Card>
          <Card>
            <CardHeader title="Consent grant" subtitle="Revocable · drives causal revocation" action={<Pill tone={snapshot.consentRevoked ? "red" : "green"}>{snapshot.consentRevoked ? "REVOKED" : "GRANTED"}</Pill>} />
            <div className="attl-consent"><LockKeyhole size={16} /><span>Consent bound to intent {intent ? `#${intent.hash.slice(0, 8)}` : "not yet sealed"}.</span>{snapshot.consentRevoked ? <ShieldX size={15} className="rev" /> : <ShieldCheck size={15} className="ok" />}</div>
          </Card>
        </div>

        <div className="attl-col attl-col-center">
          <Card>
            <CardHeader title="Agent execution" subtitle="Proposed tool calls, ActionTwin dry-run, and CommitLock state" action={<Pill tone="blue">agent</Pill>} />
            {renderAgentPlan()}
            {renderTwin()}
            <div className="attl-actions">
              <Button size="sm" onClick={() => run("ingestSource")} disabled={autoPlay}><FileText size={14} />Ingest invoice</Button>
              <Button size="sm" onClick={() => run("proposeExploit")} disabled={autoPlay}><ShieldAlert size={14} />Propose (injected)</Button>
              <Button size="sm" variant="primary" onClick={() => run("proposeCorrect")} disabled={autoPlay}><StepForward size={14} />Propose (correct)</Button>
              <Button size="sm" onClick={() => run("approve")} disabled={autoPlay}><BadgeCheck size={14} />Approve</Button>
              <Button size="sm" onClick={() => run("attackDrift")} disabled={autoPlay}><Bug size={14} />Drift test</Button>
              <Button size="sm" variant="danger" onClick={() => run("execute")} disabled={autoPlay}><Zap size={14} />Execute</Button>
            </div>
          </Card>
          <Card>
            <CardHeader title="PurposeGraph" subtitle="Every datum and action is a node; every trust decision is an edge" action={<Pill tone="green">live</Pill>} />
            <AgentTrustLabGraph snapshot={snapshot} />
          </Card>
        </div>

        <div className="attl-col attl-col-right">
          <Card className="attl-response-card">
            <CardHeader title="Response" subtitle="PurposeGate decision for this boundary crossing" action={<Pill tone="green">{graphVisible ? "gate armed" : "idle"}</Pill>} />
            {renderResponse()}
          </Card>
          <Card className="attl-capture-card">
            <CardHeader title="Live capture" subtitle="Signed, timestamped evidence of every trust decision" action={<span className="attl-live">● REC</span>} />
            <div className="attl-capture" ref={logRef}>
              {snapshot.logs.map((log, index) => (
                <div key={log.id} className={`attl-capture-row tone-${log.tone}`}>
                  <span className="attl-capture-time">{String(Math.floor(index / 60)).padStart(2, "0")}:{String(index % 60).padStart(2, "0")}</span>
                  <code className="attl-capture-phase">{log.phase}</code>
                  <p>{log.message}</p>
                  {log.verdict && <Pill tone={decisionTonePill(log.tone)}>{log.verdict}</Pill>}
                </div>
              ))}
              {snapshot.logs.length === 0 && <div className="attl-empty"><Terminal size={22} /><strong>No evidence yet</strong><small>Run a step to start the live capture.</small></div>}
            </div>
          </Card>
          <Card>
            <CardHeader title="Current binding state" subtitle="Hash-bound evidence: what the gate is currently holding" action={<Pill tone="blue">{Math.round(snapshot.progress * 100)}%</Pill>} />
            <div className="attl-state">
              <div><span>Contract hash</span><code>{intent ? `#${intent.hash.slice(0, 10)}` : "—"}</code></div>
              <div><span>Payload hash</span><code>{lock ? `#${lock.canonical_payload_hash}` : "—"}</code></div>
              <div><span>State hash</span><code>{lock ? `#${lock.state_hash}` : "—"}</code></div>
              <div><span>Consent</span><strong>{snapshot.consentRevoked ? "REVOKED" : "ACTIVE"}</strong></div>
              <div><span>Credential</span><strong>{snapshot.credential ? snapshot.credential.status.toUpperCase() : "NONE"}</strong></div>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}

function appx(progress: number, index: number): boolean {
  const threshold = (index + 1) * 0.115;
  return progress >= threshold - 0.005 && progress < threshold + 0.005;
}

function decisionTonePill(tone: string): "green" | "red" | "amber" | "blue" | "violet" {
  if (tone === "allow") return "green";
  if (tone === "block" || tone === "revoke") return "red";
  if (tone === "warn") return "amber";
  return "blue";
}
