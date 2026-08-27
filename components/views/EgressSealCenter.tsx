"use client";

import { useMemo, useRef, useState, type CSSProperties } from "react";
import {
  ArrowRight,
  BadgeCheck,
  CheckCircle2,
  Fingerprint,
  Gauge,
  KeyRound,
  LockKeyhole,
  Play,
  RefreshCw,
  Route,
  ScanLine,
  ShieldAlert,
  ShieldCheck,
  ShieldX,
  Stamp,
  Workflow,
} from "lucide-react";
import { DEMOS, INDUSTRIES } from "@/lib/demo-data";
import {
  DESTINATION_PROFILES,
  evaluateContextFence,
  type ContextFenceResult,
  type DestinationId,
} from "@/lib/context-fence";
import type { Industry } from "@/lib/types";
import { Button, Card, CardHeader, PageIntro, Pill } from "../ui";

interface ProtectedResult {
  protected_text: string;
  entities: Array<{ type?: string; token?: string }>;
  decision: string;
  receipt?: { receipt_id?: string; content_sha256?: string; signature?: string };
  latency_ms?: number;
}

interface SignedSeal {
  payload: {
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
    mode: string;
  };
  signature: string;
  algorithm: string;
  signing_key_id: string;
}

interface SealResponse {
  issued: boolean;
  decision: string;
  message?: string;
  reasons?: string[];
  seal?: SignedSeal;
  context_fence: ContextFenceResult;
  safe_action?: { id: string; label: string; connector: string };
  warning?: string;
}

interface ActionResponse {
  status: string;
  action: {
    action_receipt_id: string;
    action_label: string;
    connector: string;
    token_references: string[];
    raw_values_visible_to_model: boolean;
    resolution_mode: string;
    outcome: string;
  };
  broker_checks: string[];
  signing_key_id: string;
  error?: string;
}

const SYNTHETIC_INPUTS: Record<Industry, string> = {
  Healthcare: "I am Jordan Lee, phone 555-010-8832 and SSN 123-45-6789. My balance in my health account is 2500 rupees. I have had a headache since yesterday and need a virtual appointment tomorrow at 10:00 AM.",
  Finance: "I am Morgan Reed. Card 4111111111111111 shows a balance of 15000 dollars. Account 492188407721 shows a disputed transfer of 45000 to Taylor Chen. Open a review and contact me at morgan@example.com.",
  Insurance: "I am Casey Patel. Policy LC-MTR-884201, vehicle KA03MX4821, and my driving license DL-1234567890 were involved in an accident yesterday near Lake View Avenue.",
  "BPO / Contact center": "I am Sana Chawla. Account 7744001288 was charged twice for 2999 rupees. My card 5555555555554444 shows unusual activity. Create a refund review and send confirmation to sana@example.com.",
  "SaaS / Copilot": "Customer Orion Labs, ID CUS-884201, reported an incident on prod-db-07.internal with IP 192.168.1.100. The affected systems show a balance of 50000 credits. Create a restricted ticket for Mina Hall at mina@orionlabs.com.",
};

const PRIORITIES = [
  { number: 1, label: "EgressSeal™", detail: "Signed release proof", icon: Stamp },
  { number: 2, label: "Destination Switch", detail: "Recalculate before route", icon: Route },
  { number: 3, label: "ContextFence™", detail: "Cumulative risk, not regex only", icon: Gauge },
  { number: 4, label: "SafeAction™", detail: "Tokens act; AI never resolves", icon: Workflow },
];

function routeFor(industry: Industry, destination: DestinationId): string {
  if (destination === "organization-private") return DEMOS[industry].route;
  if (destination === "regional-ria") return `${DEMOS[industry].route} · Regional managed RIA`;
  if (destination === "research-sandbox") return "Restricted research sandbox";
  return "Public general AI";
}

function formatReason(value: string): string {
  return value.replaceAll("_", " ");
}

export function EgressSealCenter({ notify }: { notify: (message: string) => void }) {
  const [industry, setIndustry] = useState<Industry>("Healthcare");
  const [rawText, setRawText] = useState(SYNTHETIC_INPUTS.Healthcare);
  const [destinationId, setDestinationId] = useState<DestinationId>("organization-private");
  const [protectedResult, setProtectedResult] = useState<ProtectedResult | null>(null);
  const [sealResult, setSealResult] = useState<SealResponse | null>(null);
  const [verified, setVerified] = useState(false);
  const [actionResult, setActionResult] = useState<ActionResponse | null>(null);
  const [busy, setBusy] = useState<"protect" | "verify" | "action" | "">("");
  const [error, setError] = useState("");
  const sessions = useRef<Record<string, string>>({});

  const destination = DESTINATION_PROFILES.find((item) => item.id === destinationId) ?? DESTINATION_PROFILES[3];
  const contextFence = useMemo(
    () => sealResult?.context_fence ?? evaluateContextFence(
      protectedResult?.protected_text ?? "",
      protectedResult?.entities ?? [],
      destinationId,
    ),
    [destinationId, protectedResult, sealResult],
  );

  function resetOutcome() {
    setProtectedResult(null);
    setSealResult(null);
    setVerified(false);
    setActionResult(null);
    setError("");
  }

  function chooseIndustry(value: Industry) {
    setIndustry(value);
    setRawText(SYNTHETIC_INPUTS[value]);
    resetOutcome();
  }

  function chooseDestination(value: DestinationId) {
    if (value === destinationId) return;
    setDestinationId(value);
    setSealResult(null);
    setVerified(false);
    setActionResult(null);
    setError("");
    if (protectedResult) notify("Destination changed. The previous EgressSeal cannot authorize the new route; request a new destination-bound seal.");
  }

  async function sessionFor(policy: string): Promise<string> {
    if (sessions.current[policy]) return sessions.current[policy];
    const response = await fetch("/api/sessions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ policy, ttl_minutes: 30 }),
    });
    const data = await response.json();
    if (!response.ok || typeof data.session_id !== "string") {
      throw new Error(data.error || data.detail || "Protected session unavailable");
    }
    sessions.current[policy] = data.session_id;
    return data.session_id;
  }

  async function protectAndSeal() {
    if (!rawText.trim() || busy) return;
    setBusy("protect");
    setError("");
    setSealResult(null);
    setVerified(false);
    setActionResult(null);
    try {
      const policy = DEMOS[industry].policy;
      const destinationRoute = routeFor(industry, destinationId);
      const sessionId = await sessionFor(policy);
      const protectionResponse = await fetch("/api/protect", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionId,
          text: rawText,
          policy,
          destination: destinationRoute,
        }),
      });
      const protection = await protectionResponse.json() as ProtectedResult & { error?: string; detail?: string };
      if (!protectionResponse.ok || !protection.protected_text) {
        throw new Error(protection.error || protection.detail || "Protection denied; no EgressSeal was requested");
      }
      setProtectedResult(protection);

      const sealResponse = await fetch("/api/egress-seal", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          operation: "issue",
          protected_text: protection.protected_text,
          entities: protection.entities,
          decision: protection.decision,
          upstream_receipt_id: protection.receipt?.receipt_id,
          policy,
          destination_id: destinationId,
          destination_route: destinationRoute,
        }),
      });
      const seal = await sealResponse.json() as SealResponse & { error?: string };
      if (!sealResponse.ok) throw new Error(seal.error || "EgressSeal service unavailable");
      setSealResult(seal);
      notify(seal.issued
        ? `EgressSeal issued for ${destination.label}; SafeAction remains locked until verification.`
        : `EgressSeal withheld: ${seal.reasons?.map(formatReason).join(", ") || "policy review"}.`);
    } catch (caught) {
      const message = caught instanceof Error ? caught.message : "EgressSeal request failed; egress remains denied";
      setError(message);
      notify(message);
    } finally {
      setBusy("");
    }
  }

  async function verifyCurrentSeal() {
    if (!sealResult?.seal || !protectedResult) return;
    setBusy("verify");
    setError("");
    try {
      const response = await fetch("/api/egress-seal", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          operation: "verify",
          seal: sealResult.seal,
          protected_text: protectedResult.protected_text,
        }),
      });
      const result = await response.json() as { valid?: boolean; reason?: string; error?: string };
      if (!response.ok || !result.valid) throw new Error(result.error || `Seal verification failed: ${result.reason}`);
      setVerified(true);
      notify("EgressSeal signature, content digest, destination binding, and expiry verified.");
    } catch (caught) {
      const message = caught instanceof Error ? caught.message : "Seal verification failed";
      setVerified(false);
      setError(message);
      notify(message);
    } finally {
      setBusy("");
    }
  }

  async function executeSafeAction() {
    if (!verified || !sealResult?.seal || !sealResult.safe_action || !protectedResult) return;
    setBusy("action");
    setError("");
    try {
      const response = await fetch("/api/egress-seal", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          operation: "execute",
          seal: sealResult.seal,
          protected_text: protectedResult.protected_text,
          action_id: sealResult.safe_action.id,
        }),
      });
      const result = await response.json() as ActionResponse;
      if (!response.ok) throw new Error(result.error || "SafeAction broker denied the request");
      setActionResult(result);
      notify("SafeAction completed as a signed synthetic connector action; the model received no raw values.");
    } catch (caught) {
      const message = caught instanceof Error ? caught.message : "SafeAction failed closed";
      setError(message);
      notify(message);
    } finally {
      setBusy("");
    }
  }

  return <div className="view egress-seal-view">
    <PageIntro
      title="EgressSeal™ control room"
      description="A destination-bound release seal, cumulative context-risk fence, and token-aware action broker—demonstrated as one fail-closed transaction."
      actions={<Button onClick={()=>{ setRawText(SYNTHETIC_INPUTS[industry]); resetOutcome(); }}><RefreshCw size={15}/>Reset demonstration</Button>}
    />

    <div className="innovation-ribbon" aria-label="Four-part innovation flow">
      {PRIORITIES.map((priority, index) => <div key={priority.number}><i>{priority.number}</i><span><strong>{priority.label}</strong><small>{priority.detail}</small></span><priority.icon size={19}/>{index < PRIORITIES.length - 1 && <ArrowRight className="innovation-arrow" size={15}/>}</div>)}
    </div>

    <div className="egress-workbench">
      <div className="egress-left">
        <Card>
          <CardHeader title="Protected transaction" subtitle="Synthetic input is protected before any seal or action can exist" action={<Pill tone="blue">{industry}</Pill>}/>
          <div className="egress-input">
            <label><span>Industry policy</span><select value={industry} onChange={(event)=>chooseIndustry(event.target.value as Industry)}>{INDUSTRIES.map((item)=><option key={item}>{item}</option>)}</select></label>
            <label><span>Raw local input · synthetic only</span><textarea value={rawText} onChange={(event)=>{setRawText(event.target.value);resetOutcome();}} maxLength={4000}/></label>
            <div className="egress-input-footer"><span><LockKeyhole size={13}/>Raw text remains in the local trust-boundary path.</span><Button variant="primary" onClick={protectAndSeal} disabled={Boolean(busy)||!rawText.trim()}><Stamp size={15}/>{busy === "protect" ? "Protecting…" : "Protect & request seal"}</Button></div>
          </div>
        </Card>

        <Card className="destination-switch-card">
          <CardHeader title="Destination Switch" subtitle="Changing destination invalidates the prior seal and recalculates ContextFence" action={<Pill tone={destination.status === "blocked" ? "red" : destination.status === "conditional" ? "amber" : "green"}>{destination.status}</Pill>}/>
          <div className="destination-switch">{DESTINATION_PROFILES.map((item)=><button key={item.id} className={destinationId === item.id ? "active" : ""} onClick={()=>chooseDestination(item.id)}><span><Route size={15}/><strong>{item.label}</strong></span><small>{item.description}</small><em className={item.status}>{item.status} · base risk {item.baseRisk}</em></button>)}</div>
        </Card>

        <Card>
          <CardHeader title="Protected outbound preview" subtitle="This—not the raw input—is bound into EgressSeal" action={protectedResult?<Pill tone={protectedResult.decision === "allow" ? "green" : "amber"}>{protectedResult.decision}</Pill>:<Pill>Waiting</Pill>}/>
          <div className="egress-output">
            {protectedResult ? <>
              <code>{protectedResult.protected_text}</code>
              <div>{protectedResult.entities.map((entity,index)=><Pill tone="green" key={`${entity.token}-${index}`}>{entity.type} · {entity.token}</Pill>)}</div>
              <footer><span>Receipt {protectedResult.receipt?.receipt_id || "unavailable"}</span><span>{protectedResult.latency_ms ?? "—"} ms</span><span>{protectedResult.entities.length} protected entities</span></footer>
            </> : <div className="egress-empty"><ShieldCheck size={25}/><strong>No outbound candidate yet</strong><small>Protect the synthetic input to create a destination-bound candidate.</small></div>}
          </div>
        </Card>
      </div>

      <div className="egress-right">
        <Card className={`context-fence-card risk-${contextFence.disposition === "block" ? "critical" : contextFence.band}`}>
          <CardHeader title="ContextFence™ risk meter" subtitle="Detects mosaic and linkage risk left after field-level masking" action={<Pill tone={contextFence.disposition === "block" || contextFence.band === "high" || contextFence.band === "critical" ? "red" : contextFence.band === "guarded" ? "amber" : "green"}>{contextFence.band} · {contextFence.disposition}</Pill>}/>
          <div className="context-meter">
            <div className="context-score"><span style={{"--risk":`${contextFence.score * 3.6}deg`} as CSSProperties}><i>{contextFence.score}</i></span><div><strong>{contextFence.disposition.toUpperCase()}</strong><small>Destination threshold {destination.maximumRisk || "blocked"}</small></div></div>
            <div className="context-track"><i style={{width:`${contextFence.score}%`}}/></div>
            <p>{contextFence.explanation}</p>
            <div className="context-factors">{contextFence.factors.slice(0,5).map((factor)=><div key={factor.label}><span><strong>{factor.label}</strong><small>{factor.detail}</small></span><b>+{factor.points}</b></div>)}</div>
          </div>
        </Card>

        <Card className={`egress-seal-card ${sealResult?.issued ? "issued" : sealResult ? "denied" : "waiting"}`}>
          <CardHeader title="EgressSeal™" subtitle="Content + policy + destination + risk + expiry, signed as one release proof" action={sealResult?.issued?<Pill tone="green"><BadgeCheck size={12}/>Issued</Pill>:sealResult?<Pill tone="red">Withheld</Pill>:<Pill>Not issued</Pill>}/>
          {!sealResult && <div className="seal-empty"><Stamp size={34}/><strong>No release proof</strong><p>A protected payload is not egress-authorized until a destination-bound seal is issued and verified.</p></div>}
          {sealResult && !sealResult.issued && <div className="seal-denied"><ShieldX size={35}/><strong>Egress remains closed</strong><p>{sealResult.message}</p><div>{sealResult.reasons?.map((reason)=><Pill tone="red" key={reason}>{formatReason(reason)}</Pill>)}</div></div>}
          {sealResult?.issued && sealResult.seal && <div className="seal-issued">
            <div className="seal-mark"><ShieldCheck size={31}/><span>EGRESS</span><strong>SEALED</strong><small>{sealResult.seal.algorithm}</small></div>
            <div className="seal-details"><div><span>Seal ID</span><code>{sealResult.seal.payload.seal_id}</code></div><div><span>Bound destination</span><strong>{sealResult.seal.payload.destination_label}</strong></div><div><span>Signing key</span><code>{sealResult.seal.signing_key_id}</code></div><div><span>Expires</span><strong>{new Date(sealResult.seal.payload.expires_at).toLocaleTimeString([], {hour:"2-digit",minute:"2-digit",second:"2-digit"})}</strong></div></div>
            <Button onClick={verifyCurrentSeal} disabled={Boolean(busy)||verified} variant={verified?"secondary":"primary"}><Fingerprint size={15}/>{verified?"Signature verified":busy === "verify"?"Verifying…":"Verify EgressSeal"}</Button>
            <small><ShieldAlert size={12}/>{sealResult.warning}</small>
          </div>}
        </Card>

        <Card className={`safe-action-card ${verified ? "unlocked" : "locked"}`}>
          <CardHeader title="SafeAction™ demonstration" subtitle="The AI proposes with tokens; a trusted broker resolves only inside the connector" action={<Pill tone={verified?"green":"amber"}>{verified?"Broker unlocked":"Seal required"}</Pill>}/>
          {!actionResult ? <div className="safe-action-ready">
            <span>{verified?<Workflow size={26}/>:<KeyRound size={26}/>}</span>
            <div><strong>{sealResult?.safe_action?.label || "No allowlisted action available"}</strong><p>{verified?"Seal verified. Execute a synthetic connector action without returning raw values to the model.":"Protect, seal, and verify the transaction before SafeAction can run."}</p></div>
            <Button variant="primary" disabled={!verified||Boolean(busy)||!sealResult?.safe_action} onClick={executeSafeAction}><Play size={15}/>{busy === "action"?"Executing…":"Run SafeAction"}</Button>
          </div> : <div className="safe-action-result">
            <header><CheckCircle2 size={23}/><span><strong>Synthetic action completed</strong><small>{actionResult.action.action_receipt_id} · {actionResult.action.connector}</small></span></header>
            <div className="broker-path">{actionResult.broker_checks.map((check,index)=><div key={check}><i>{index+1}</i><span>{check}</span>{index < actionResult.broker_checks.length-1&&<ScanLine size={13}/>}</div>)}</div>
            <footer><span><LockKeyhole size={13}/>Raw values visible to model: <strong>{String(actionResult.action.raw_values_visible_to_model)}</strong></span><span>Signed by <code>{actionResult.signing_key_id}</code></span></footer>
          </div>}
        </Card>

        {error && <div className="egress-error" role="alert"><ShieldX size={16}/><span><strong>Fail-closed result</strong><small>{error}</small></span></div>}
      </div>
    </div>
  </div>;
}
