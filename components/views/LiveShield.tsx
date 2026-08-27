"use client";

import { useEffect, useRef, useState } from "react";
import { Activity, Bot, CircleStop, CircleUserRound, Cpu, LockKeyhole, Mic2, Pause, Play, RotateCcw, ShieldCheck, Sparkles, UsersRound } from "lucide-react";
import { DEMOS, INDUSTRIES } from "@/lib/demo-data";
import type { Industry, ProtectionResult, TranscriptTurn } from "@/lib/types";
import { Button, Card, CardHeader, PageIntro, Pill, highlight } from "../ui";

function formatTime(seconds: number) { return `${String(Math.floor(seconds/60)).padStart(2,"0")}:${String(seconds%60).padStart(2,"0")}`; }

export function LiveShield({ notify }: { notify: (m: string) => void }) {
  const [industry, setIndustry] = useState<Industry>("Healthcare");
  const [running, setRunning] = useState(false);
  const [paused, setPaused] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [turnCount, setTurnCount] = useState(0);
  const [input, setInput] = useState("Customer jack, account 123456789, called from +91 123456789 and email jack@example.com.");
  const [protection, setProtection] = useState<ProtectionResult | null>(null);
  const [summary, setSummary] = useState("");
  const [busy, setBusy] = useState(false);
  const controlSession = useRef<{ id: string; policy: string } | null>(null);
  const rawPane = useRef<HTMLDivElement>(null);
  const safePane = useRef<HTMLDivElement>(null);
  const demo = DEMOS[industry];
  const turns = demo.transcript.slice(0, turnCount);
  const entityCount = turns.reduce((total, turn)=>total+turn.entities.length,0);

  useEffect(()=>{ if(!running || paused) return; const id=setInterval(()=>setElapsed(v=>v+1),1000); return ()=>clearInterval(id); },[running,paused]);
  useEffect(()=>{ if(!running || paused) return; const id=setInterval(()=>setTurnCount(v=>Math.min(v+1,demo.transcript.length)),2500); return ()=>clearInterval(id); },[running,paused,demo.transcript.length]);
  useEffect(()=>{ rawPane.current?.scrollTo({top:rawPane.current.scrollHeight,behavior:"smooth"}); safePane.current?.scrollTo({top:safePane.current.scrollHeight,behavior:"smooth"}); },[turnCount]);

  async function ensureControlSession(): Promise<string> {
    if (controlSession.current?.policy === demo.policy) return controlSession.current.id;
    const response = await fetch("/api/sessions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ policy: demo.policy, ttl_minutes: 60 }),
    });
    const data = await response.json();
    if (!response.ok || typeof data.session_id !== "string") {
      throw new Error(data.error || data.detail || "Protection session is unavailable");
    }
    controlSession.current = { id: data.session_id, policy: demo.policy };
    return data.session_id;
  }

  function startSample() {
    if (running) return;
    setTurnCount(1); setElapsed(0); setSummary("");
    setRunning(true); setPaused(false);
    notify("Sample playback started. This is labelled synthetic data demonstrating the privacy protection flow.");
  }

  function togglePause() {
    setPaused(!paused);
  }

  function stopStream() {
    setRunning(false); setPaused(false);
    notify("Sample session ended.");
  }

  function reset() {
    if(controlSession.current) controlSession.current = null;
    setRunning(false); setPaused(false); setElapsed(0); setTurnCount(0); setSummary(""); setProtection(null);
  }
  function resetProtection() { setInput(""); setProtection(null); }
  function chooseIndustry(value: Industry) { reset(); setIndustry(value); }

  async function protectSample() {
    setBusy(true);
    try {
      const sessionId = await ensureControlSession();
      const response = await fetch("/api/protect", { method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({session_id:sessionId,text:input,policy:demo.policy,destination:demo.route}) });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || data.detail || "Protection denied");
      setProtection({ protectedText:data.protected_text || `Egress ${data.decision}: no content released.`, entities:data.entities, decision:data.decision, receiptId:data.receipt.receipt_id, contentHash:data.receipt.content_sha256, latencyMs:data.latency_ms });
      notify(data.decision === "allow" ? `${data.entities.length} identifiers protected; a policy receipt was created.` : `Egress ${data.decision}; no content was released and a signed receipt was created.`);
    } catch (error) { notify(error instanceof Error ? error.message : "The protection API is unavailable."); } finally { setBusy(false); }
  }

  async function summarize() {
    setBusy(true);
    try {
      const sessionId = await ensureControlSession();
      const protectedTranscript = demo.transcript.map(t=>`[${t.speaker.toUpperCase()}]: ${t.safe}`).join("\n");
      const response=await fetch("/api/summarize",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({session_id:sessionId,text:protectedTranscript,industry,policy:demo.policy,destination:demo.route})});
      const data=await response.json();
      if (!response.ok) throw new Error(data.error || data.detail || "AI egress denied");
      setSummary(data.summary); notify(data.mode==="ollama"?"Summary generated by your self-hosted Ollama model.":"Safe fallback summary generated; connect Ollama for local LLM output.");
    } catch (error) { notify(error instanceof Error ? error.message : "Summary service is unavailable."); } finally {setBusy(false);}
  }

  return <div className="view">
    <PageIntro title="Voice privacy demonstration" description="See how AirShield protects sensitive information in real-time using clearly labelled synthetic sample data." actions={<Button onClick={reset}><RotateCcw size={15}/>Reset</Button>}/>
    <div className="industry-bar"><div><span>Industry policy</span><div>{INDUSTRIES.map(item=><button key={item} onClick={()=>chooseIndustry(item)} className={industry===item?"active":""}>{item}</button>)}</div></div><div className="source-state"><span className={`status-dot ${running?"active":""}`}/><span><strong>{running?"Running labelled sample":"Sample demonstration"}</strong><small>Synthetic data · no microphone required</small></span></div></div>
    <div className="live-grid"><div className="live-main">
      <Card className="encounter-card"><div className="session-bar"><div className="session-state"><span className={`record-dot ${running?(paused?"paused":"recording"):"idle"}`}/><span><strong>{running?(paused?"Sample paused":"Running labelled sample"):"Ready to demonstrate"}</strong><small>{`SESSION-${industry.toUpperCase().replace(/\W/g,"").slice(0,6)}`} · {industry} · {demo.policy}</small></span></div><div className="session-time"><div className={`wave ${running&&!paused?"active":""}`}>{[8,16,23,11,18,7,15,21,10,17,6,13,20,9,16].map((h,i)=><i key={i} style={{height:h,animationDelay:`${i*.05}s`}}/>)}</div><strong>{formatTime(elapsed)}</strong></div></div>
        <div className="compare-shell">
          <section className="compare-pane raw-pane"><header><span><small>Inside trust boundary</small><strong><Mic2 size={15}/>What people are saying</strong></span><Pill tone="red">Raw · synthetic sample</Pill></header><div className="transcript-pane" ref={rawPane}>{turns.length?turns.map((turn,i)=><article className="turn" key={`${turn.time}-${i}`}><div><span className={`speaker ${turn.role}`}>{turn.speaker}</span><time>{turn.time}</time></div><p>{highlight(turn.raw,"raw",turn.entities)}</p></article>):<div className="empty-pane"><ShieldCheck size={26}/><strong>Sample transcript will appear here</strong><small>This is clearly labelled synthetic data demonstrating the privacy protection flow.</small></div>}</div></section>
          <div className="shield-divider"><i/><span><ShieldCheck size={15}/></span></div>
          <section className="compare-pane safe-pane"><header><span><small>Outbound AI view</small><strong><ShieldCheck size={15}/>What is being masked</strong></span><Pill tone="amber">Protected · synthetic sample</Pill></header><div className="transcript-pane" ref={safePane}>{turns.length?turns.map((turn,i)=><article className="turn" key={`${turn.time}-${i}`}><div><span className={`speaker ${turn.role}`}>{turn.speaker}</span><time>{turn.time}</time></div><p>{highlight(turn.safe,"safe",turn.entities)}</p></article>):<div className="empty-pane"><ShieldCheck size={26}/><strong>Protected transcript will appear here</strong><small>Names, phone numbers, and other PII are replaced with tokens.</small></div>}</div></section>
        </div>
        <footer className="session-controls"><div><span><Activity size={13}/><strong>{turns.length?`${turns.length} sample turns`:""}</strong></span><span><ShieldCheck size={13}/>{entityCount} masked values</span><span><LockKeyhole size={13}/>No raw AI egress</span></div><div>{!running?<Button variant="primary" onClick={startSample}><Play size={15}/>Run sample</Button>:<><Button onClick={togglePause}>{paused?<Play size={15}/>:<Pause size={15}/>} {paused?"Resume":"Pause"}</Button><Button variant="danger" onClick={stopStream}><CircleStop size={15}/>Stop</Button></>}</div></footer>
      </Card>
      <Card><CardHeader title="Try the protection API" subtitle="Type or paste text. The raw input stays on the left and every detected value is replaced in the protected output." action={<Pill tone="blue">Local Next.js API</Pill>}/><div className="try-grid"><label><span>Raw application text</span><textarea value={input} onChange={e=>{setInput(e.target.value);setProtection(null);}} placeholder="Type text containing a name, account, phone, email, health ID, or payment data…"/></label><div><span>Protected application output</span><div className="protected-output" aria-live="polite">{protection?protection.protectedText:"Select Protect text to run the masking policy."}</div></div></div><div className="try-footer"><div>{protection?.entities.length?protection.entities.map(e=><Pill tone="green" key={`${e.type}-${e.start}`}>{e.type} · {e.token}</Pill>):protection?<Pill tone="amber">No identifiers detected</Pill>:null}</div><div className="try-actions"><Button onClick={resetProtection} disabled={busy}><RotateCcw size={15}/>Reset</Button><Button variant="primary" disabled={busy||!input.trim()} onClick={protectSample}><ShieldCheck size={15}/>{busy?"Protecting…":"Protect text"}</Button></div></div></Card>
      {summary && <Card><CardHeader title="Protected AI summary" subtitle="Generated from the right-side transcript only" action={<Pill tone="green"><Sparkles size={12}/>No raw identifiers</Pill>}/><div className="summary-box">{summary}</div></Card>}
    </div><aside className="live-side">
      <Card><CardHeader title="Speaker ↔ person map" subtitle="Authentication happens outside the LLM" action={<Pill tone="blue">Local vault</Pill>}/><div className="speaker-list">{demo.speakers.map((speaker,i)=><div className="speaker-row" key={speaker.track}><span className={`speaker-avatar ${speaker.color}`}>{speaker.initials}</span><span><strong>{speaker.name}</strong><small>{speaker.track} · {speaker.role}</small></span><em className={speaker.status}>{speaker.assurance}</em></div>)}</div><div className="identity-note"><LockKeyhole size={13}/>The LLM receives random tokens such as [SPEAKER_8A91C2], while unbound tracks stay [UNKNOWN]—never these names.</div></Card>
      <Card><CardHeader title="How identity is established" subtitle="An LLM does not authenticate a human" action={<CircleUserRound size={18}/>}/><div className="identity-steps">{[
        ["Verify session","SSO, OTP, CRM/EHR check-in, IVR or app login"],["Separate voices","Local diarization maintains Speaker A/B/C"],["Bind or stay unknown","Host assertion binds a verified identity"],["Tokenize for AI","Real mapping remains in the local vault"]
      ].map((step,i)=><div key={step[0]}><i>{i+1}</i><span><strong>{step[0]}</strong><small>{step[1]}</small></span></div>)}</div></Card>
      <Card><CardHeader title="PII detection & masking" subtitle="Automatic identification of sensitive data" action={<Pill tone="green">Local processing</Pill>}/><div className="model-stack"><div><ShieldCheck size={16}/><span><strong>Names & Identifiers</strong><small>Person names, patient IDs, customer IDs</small></span></div><div><ShieldCheck size={16}/><span><strong>Contact Information</strong><small>Phone numbers, email addresses</small></span></div><div><ShieldCheck size={16}/><span><strong>Financial Data</strong><small>Card numbers, account numbers, balances</small></span></div><div><ShieldCheck size={16}/><span><strong>Health Information</strong><small>MRN, diagnoses, medical terms</small></span></div></div></Card>
      <Card><CardHeader title="Downstream route" subtitle="Any application, any approved model" action={<Pill tone="amber">Policy gated</Pill>}/><div className="route-list"><div><span><Bot size={16}/></span><p><strong>{demo.route}</strong><small>Protected transcript only</small></p><em>Protected</em></div><div><span><ShieldCheck size={16}/></span><p><strong>{demo.destination}</strong><small>Controlled re-association</small></p><em>Receipt required</em></div></div><Button className="full" variant="primary" onClick={summarize} disabled={busy}><Sparkles size={15}/>Send protected stream to local AI</Button></Card>
    </aside></div>
  </div>;
}
