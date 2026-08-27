"use client";

import { useEffect, useRef, useState } from "react";
import { Activity, Bot, CircleStop, CircleUserRound, Cpu, LockKeyhole, Mic2, Pause, Play, Radio, RotateCcw, Send, ShieldCheck, Sparkles, UsersRound } from "lucide-react";
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
  const [micConnected, setMicConnected] = useState(false);
  const [captureMode, setCaptureMode] = useState<"none" | "live" | "sample">("none");
  const [voiceState, setVoiceState] = useState<"idle" | "connecting" | "listening" | "paused" | "processing" | "complete" | "error">("idle");
  const [voiceError, setVoiceError] = useState("");
  const [edgeAvailable, setEdgeAvailable] = useState<boolean | null>(null);
  const [input, setInput] = useState("Customer jack, account 123456789, called from +91 123456789 and email jack@example.com.");
  const [protection, setProtection] = useState<ProtectionResult | null>(null);
  const [summary, setSummary] = useState("");
  const [edgeTurns, setEdgeTurns] = useState<TranscriptTurn[]>([]);
  const [busy, setBusy] = useState(false);
  const mediaStream = useRef<MediaStream | null>(null);
  const recorder = useRef<MediaRecorder | null>(null);
  const socket = useRef<WebSocket | null>(null);
  const audioSendQueue = useRef<Promise<void>>(Promise.resolve());
  const closeTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const expectedSocketClose = useRef(false);
  const controlSession = useRef<{ id: string; policy: string } | null>(null);
  const rawPane = useRef<HTMLDivElement>(null);
  const safePane = useRef<HTMLDivElement>(null);
  const demo = DEMOS[industry];
  const turns = captureMode === "live" ? edgeTurns : captureMode === "sample" ? demo.transcript.slice(0, turnCount) : [];
  const entityCount = turns.reduce((total, turn)=>total+turn.entities.length,0);

  useEffect(()=>{ if(!running || paused) return; const id=setInterval(()=>setElapsed(v=>v+1),1000); return ()=>clearInterval(id); },[running,paused]);
  useEffect(()=>{ if(!running || paused || captureMode !== "sample") return; const id=setInterval(()=>setTurnCount(v=>Math.min(v+1,demo.transcript.length)),2500); return ()=>clearInterval(id); },[running,paused,captureMode,demo.transcript.length]);
  useEffect(()=>{ rawPane.current?.scrollTo({top:rawPane.current.scrollHeight,behavior:"smooth"}); safePane.current?.scrollTo({top:safePane.current.scrollHeight,behavior:"smooth"}); },[turnCount,edgeTurns]);
  useEffect(()=>()=>{
    if (closeTimer.current) clearTimeout(closeTimer.current);
    if (recorder.current?.state !== "inactive") recorder.current?.stop();
    mediaStream.current?.getTracks().forEach(t=>t.stop());
    socket.current?.close();
  },[]);

  // Check if edge service is available on mount
  useEffect(()=>{
    if (edgeAvailable !== null) return; // Already checked
    const edgeUrl = configuredEdgeUrl();
    if (!edgeUrl) {
      setEdgeAvailable(false);
      return;
    }
    // Convert WebSocket URL to HTTP for health check
    const healthUrl = edgeUrl.replace(/^ws:/, "http:").replace(/\/ws\/voice$/, "/health");
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 3000);
    fetch(healthUrl, { method: "GET", signal: controller.signal })
      .then(res => {
        clearTimeout(timeout);
        setEdgeAvailable(res.ok);
        if (!res.ok) {
          setVoiceError(`Voice edge service at ${new URL(healthUrl).origin} returned status ${res.status}. Start the edge-service: cd edge-service && python main.py`);
        }
      })
      .catch(() => {
        clearTimeout(timeout);
        setEdgeAvailable(false);
        setVoiceError(`Voice edge service is not running at ${new URL(healthUrl).origin}. Start it with: cd edge-service && python main.py`);
      });
  }, [edgeAvailable]);

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

  function configuredEdgeUrl(): string | null {
    const configured = process.env.NEXT_PUBLIC_EDGE_WS_URL?.trim();
    if (configured) return configured;
    if (typeof window !== "undefined" && window.location.protocol === "http:" && ["localhost", "127.0.0.1"].includes(window.location.hostname)) {
      return `ws://${window.location.hostname}:8001/ws/voice`;
    }
    return null;
  }

  function isEdgeConfigured(): boolean {
    // Check if the edge URL is explicitly configured in environment
    const configured = process.env.NEXT_PUBLIC_EDGE_WS_URL?.trim();
    return Boolean(configured);
  }

  function releaseMicrophone() {
    mediaStream.current?.getTracks().forEach(track=>track.stop());
    mediaStream.current=null;
    setMicConnected(false);
  }

  async function acquireMicrophone(): Promise<MediaStream> {
    const current=mediaStream.current;
    if (current?.getAudioTracks().some(track=>track.readyState === "live")) return current;
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") {
      throw new Error("This browser cannot capture microphone audio. Use current Chrome, Edge, Firefox, or Safari over HTTPS or localhost.");
    }
    const stream=await navigator.mediaDevices.getUserMedia({audio:{channelCount:1,echoCancellation:true,noiseSuppression:true,autoGainControl:true}});
    mediaStream.current=stream;
    setMicConnected(true);
    return stream;
  }

  async function connectMicrophone() {
    setVoiceError("");
    try {
      await acquireMicrophone();
      if (isEdgeConfigured()) {
        notify("Microphone connected. Select Start live capture to transcribe through the self-hosted edge.");
      } else {
        notify("Microphone connected. Note: Live capture requires the edge-service to be running. Use 'Run sample' for demonstration, or start the edge-service with proper configuration to enable live voice capture.");
      }
    } catch (error) {
      const message=error instanceof Error?error.message:"Microphone permission was not granted.";
      setVoiceState("error"); setVoiceError(message); notify(message);
    }
  }

  async function startStream() {
    if (running || voiceState === "connecting" || voiceState === "processing") return;
    const edgeUrl=configuredEdgeUrl();
    if (!edgeUrl) {
      setVoiceState("error"); 
      setVoiceError("NEXT_PUBLIC_EDGE_WS_URL is not configured. Start the self-hosted voice edge service (edge-service) and set the environment variable. Use 'Run sample' for demonstration.");
      notify("Live capture requires the edge-service to be running. Use 'Run sample' instead.");
      return;
    }
    // Check if edge is available (may have been checked on mount, or we check now)
    if (edgeAvailable === false) {
      setVoiceState("error");
      setVoiceError("Voice edge service is not running. Start it with: cd edge-service && python main.py");
      notify("Cannot start live capture: edge-service is not running. Use 'Run sample' for demonstration.");
      return;
    }
    setVoiceState("connecting"); setVoiceError(""); setCaptureMode("live"); setEdgeTurns([]); setTurnCount(0); setElapsed(0); setSummary("");
    expectedSocketClose.current=false;
    try {
      const stream=await acquireMicrophone();
      const ws=new WebSocket(edgeUrl); socket.current=ws;
      ws.onopen=()=>{
        try {
          const supported=["audio/webm;codecs=opus","audio/webm","audio/mp4","audio/ogg;codecs=opus"];
          const mime=supported.find(value=>MediaRecorder.isTypeSupported(value));
          const mr=new MediaRecorder(stream,mime?{mimeType:mime}:undefined); recorder.current=mr;
          audioSendQueue.current=Promise.resolve();
          mr.ondataavailable=event=>{
            if (!event.data.size) return;
            audioSendQueue.current=audioSendQueue.current.then(async()=>{
              const payload=await event.data.arrayBuffer();
              if (ws.readyState===WebSocket.OPEN) ws.send(payload);
            });
          };
          mr.onstop=()=>{
            recorder.current=null;
            void audioSendQueue.current.then(()=>{
              if (ws.readyState===WebSocket.OPEN) ws.send(JSON.stringify({type:"session.end"}));
            });
          };
          ws.send(JSON.stringify({type:"session.start",language:"en",industry,policy:demo.policy,audio_format:mr.mimeType||mime||"audio/webm"}));
          mr.start(750);
          setRunning(true); setPaused(false); setVoiceState("listening");
          notify("Live capture started. Raw and masked transcript pairs will appear side by side.");
        } catch (error) {
          const message=error instanceof Error?error.message:"The browser audio recorder could not start.";
          setVoiceState("error"); setVoiceError(message); releaseMicrophone(); ws.close(); notify(message);
        }
      };
      ws.onmessage=event=>{
        try {
          const message=JSON.parse(String(event.data));
          if (message.type === "session.ready") {
            setVoiceState("listening");
          } else if (message.type === "transcript.pair" && typeof message.raw === "string") {
            const raw=message.raw as string;
            const entities=Array.isArray(message.entities)?message.entities.filter((entity: unknown)=>{
              if (!entity || typeof entity !== "object") return false;
              const item=entity as Record<string,unknown>;
              return typeof item.start === "number" && typeof item.end === "number" && typeof item.token === "string" && typeof item.type === "string";
            }).map((entity: {start:number;end:number;token:string;type:string})=>({raw:raw.slice(entity.start,entity.end),token:entity.token,type:entity.type})):[];
            const turn:TranscriptTurn={
              speaker:typeof message.speaker === "string"?message.speaker:typeof message.speaker_track === "string"?message.speaker_track:"Speaker",
              role:"primary",
              time:formatTime(typeof message.time === "number"?Math.max(0,Math.round(message.time)):0),
              raw,
              safe:typeof message.protected === "string"&&message.protected?message.protected:"[BLOCKED_PENDING_PRIVACY_DECISION]",
              entities,
            };
            setEdgeTurns(previous=>[...previous,turn]);
          } else if (message.type === "policy.decision") {
            const reason=typeof message.reason === "string"?message.reason:"privacy policy denied the stream";
            expectedSocketClose.current=true; setRunning(false);
            if (recorder.current?.state !== "inactive") recorder.current?.stop();
            releaseMicrophone(); setVoiceState("error"); setVoiceError(`Voice protection stopped: ${reason}.`); notify(`Voice protection stopped: ${reason}.`);
          } else if (message.type === "transcript.final") {
            if (closeTimer.current) clearTimeout(closeTimer.current);
            const signature=message.receipt?.signature;
            const signedAllow=message.decision === "allow"&&message.safe_for_egress === true&&typeof signature === "string"&&signature.length>=40&&signature!=="demo_unsigned";
            setVoiceState("complete"); expectedSocketClose.current=true;
            notify(signedAllow?"Live capture completed with a signed protected-egress receipt.":"Live capture completed. The transcript stays provisional and was not released to AI without a signed allow receipt.");
            ws.close();
          }
        } catch {
          expectedSocketClose.current=true; setRunning(false);
          if (recorder.current?.state !== "inactive") recorder.current?.stop();
          releaseMicrophone(); setVoiceState("error"); setVoiceError("The voice edge returned an invalid event; egress remains blocked."); ws.close();
        }
      };
      ws.onerror=()=>{
        setVoiceState("error"); setVoiceError("Could not connect to the self-hosted voice edge. Confirm that it is running and the WebSocket URL and TLS certificate are valid.");
      };
      ws.onclose=event=>{
        socket.current=null;
        if (!expectedSocketClose.current && voiceState !== "complete") {
          const detail=event.reason?` ${event.reason}`:"";
          if (recorder.current?.state !== "inactive") recorder.current?.stop();
          releaseMicrophone(); setRunning(false); setVoiceState("error"); setVoiceError(`Voice connection closed (${event.code}).${detail}`);
        }
      };
    } catch (error) {
      releaseMicrophone(); setRunning(false); setCaptureMode("none"); setVoiceState("error");
      const message=error instanceof Error?error.message:"Live voice capture could not start.";
      setVoiceError(message); notify(message);
    }
  }

  function startSample() {
    if (running) return;
    setCaptureMode("sample"); setEdgeTurns([]); setTurnCount(1); setElapsed(0); setVoiceError(""); setVoiceState("listening"); setRunning(true); setPaused(false);
    notify("Sample playback started. This is labelled sample data and does not use the microphone.");
  }

  function togglePause() {
    const next=!paused;
    if (captureMode === "live" && recorder.current) {
      if (next && recorder.current.state === "recording") recorder.current.pause();
      if (!next && recorder.current.state === "paused") recorder.current.resume();
    }
    setPaused(next); setVoiceState(next?"paused":"listening");
  }

  function stopStream() {
    setRunning(false); setPaused(false);
    if (captureMode === "sample") { setVoiceState("complete"); notify("Sample session ended."); return; }
    setVoiceState("processing");
    const mr=recorder.current;
    if (mr && mr.state !== "inactive") mr.stop();
    else if (socket.current?.readyState === WebSocket.OPEN) socket.current.send(JSON.stringify({type:"session.end"}));
    releaseMicrophone();
    closeTimer.current=setTimeout(()=>{
      if (socket.current && socket.current.readyState <= WebSocket.OPEN) {
        expectedSocketClose.current=true; socket.current.close(); setVoiceState("error"); setVoiceError("Timed out waiting for the final privacy check; egress remains blocked.");
      }
    },120_000);
    notify("Recording stopped. The last audio is being transcribed and rechecked before any egress decision.");
  }

  function reset() {
    expectedSocketClose.current=true;
    if(closeTimer.current) clearTimeout(closeTimer.current);
    if(recorder.current?.state !== "inactive") recorder.current?.stop(); recorder.current=null;
    socket.current?.close(); socket.current=null; releaseMicrophone(); controlSession.current=null;
    setRunning(false); setPaused(false); setElapsed(0); setTurnCount(0); setSummary(""); setEdgeTurns([]); setCaptureMode("none"); setVoiceState("idle"); setVoiceError(""); setProtection(null);
    // Re-check edge availability
    setEdgeAvailable(null);
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
    <PageIntro title="Voice privacy, live and side by side" description="English voice is captured live, transcribed, diarized, and protected on your own infrastructure before any AI model receives it." actions={<><Button onClick={connectMicrophone} disabled={micConnected||running}><Mic2 size={15}/>{micConnected?"Microphone connected":"Connect microphone"}</Button><Button onClick={reset}><RotateCcw size={15}/>Reset</Button></>}/>
    <div className="industry-bar"><div><span>Industry policy</span><div>{INDUSTRIES.map(item=><button key={item} onClick={()=>chooseIndustry(item)} className={industry===item?"active":""}>{item}</button>)}</div></div><div className="source-state"><span className={`status-dot ${voiceState==="error"?"error":voiceState==="listening"?"active":edgeAvailable===false?"error":""}`}/><span><strong>{captureMode==="sample"?"Clearly labelled sample":voiceState==="listening"?"Live microphone capture":micConnected?"Microphone ready":edgeAvailable===false?"Edge service offline":"Voice edge ready when configured"}</strong><small>{edgeAvailable===false?"Start edge-service: cd edge-service && python main.py":"English · self-hosted transcription only"}</small></span></div></div>
    <div className="live-grid"><div className="live-main">
      <Card className="encounter-card"><div className="session-bar"><div className="session-state"><span className={`record-dot ${running?(paused?"paused":"recording"):voiceState==="processing"?"paused":"idle"}`}/><span><strong>{voiceState==="connecting"?"Connecting to private voice edge":voiceState==="processing"?"Transcribing final audio":voiceState==="complete"?"Capture complete":voiceState==="error"?"Capture needs attention":running?(paused?"Live capture paused":captureMode==="sample"?"Running labelled sample":"Listening and protecting"):"Ready for live English voice"}</strong><small>{captureMode==="sample"?"SAMPLE DATA":`SESSION-${industry.toUpperCase().replace(/\W/g,"").slice(0,6)}`} · {industry} · {demo.policy}</small></span></div><div className="session-time"><div className={`wave ${running&&!paused?"active":""}`}>{[8,16,23,11,18,7,15,21,10,17,6,13,20,9,16].map((h,i)=><i key={i} style={{height:h,animationDelay:`${i*.05}s`}}/>)}</div><strong>{formatTime(elapsed)}</strong></div></div>
        {voiceError&&<div className="voice-error" role="alert"><Radio size={15}/><span><strong>Live capture unavailable</strong><small>{voiceError}</small></span></div>}
        <div className="compare-shell">
          <section className="compare-pane raw-pane"><header><span><small>Inside trust boundary</small><strong><Mic2 size={15}/>What people are saying</strong></span><Pill tone="red">Raw · never sent</Pill></header><div className="transcript-pane" ref={rawPane}>{turns.length?turns.map((turn,i)=><article className="turn" key={`${turn.time}-${i}`}><div><span className={`speaker ${turn.role}`}>{turn.speaker}</span><time>{turn.time}</time></div><p>{highlight(turn.raw,"raw",turn.entities)}</p></article>):<EmptyPane state={voiceState}/>}</div></section>
          <div className="shield-divider"><i/><span><ShieldCheck size={15}/></span></div>
          <section className="compare-pane safe-pane"><header><span><small>Outbound AI view</small><strong><ShieldCheck size={15}/>What is being masked</strong></span><Pill tone="amber">Provisional · final check</Pill></header><div className="transcript-pane" ref={safePane}>{turns.length?turns.map((turn,i)=><article className="turn" key={`${turn.time}-${i}`}><div><span className={`speaker ${turn.role}`}>{turn.speaker}</span><time>{turn.time}</time></div><p>{highlight(turn.safe,"safe",turn.entities)}</p></article>):<EmptyPane state={voiceState}/>}</div></section>
        </div>
        <footer className="session-controls"><div><span><Activity size={13}/><strong>{captureMode==="sample"?"Sample":edgeTurns.length?`${edgeTurns.length} live turns`:"Private edge"}</strong></span><span><ShieldCheck size={13}/>{entityCount} masked values</span><span><LockKeyhole size={13}/>No raw AI egress</span></div><div>{!running?<><Button variant="primary" onClick={startStream} disabled={voiceState==="connecting"||voiceState==="processing"}><Mic2 size={15}/>{voiceState==="connecting"?"Connecting…":voiceState==="processing"?"Finalizing…":"Start live capture"}</Button><Button onClick={startSample} disabled={voiceState==="connecting"||voiceState==="processing"}><Play size={15}/>Run sample</Button></>:<><Button onClick={togglePause}>{paused?<Play size={15}/>:<Pause size={15}/>} {paused?"Resume":"Pause"}</Button><Button variant="danger" onClick={stopStream}><CircleStop size={15}/>Stop & protect</Button></>}</div></footer>
      </Card>
      <Card><CardHeader title="Try the protection API" subtitle="Type or paste text. The raw input stays on the left and every detected value is replaced in the protected output." action={<Pill tone="blue">Local Next.js API</Pill>}/><div className="try-grid"><label><span>Raw application text</span><textarea value={input} onChange={e=>{setInput(e.target.value);setProtection(null);}} placeholder="Type text containing a name, account, phone, email, health ID, or payment data…"/></label><div><span>Protected application output</span><div className="protected-output" aria-live="polite">{protection?protection.protectedText:"Select Protect text to run the masking policy."}</div></div></div><div className="try-footer"><div>{protection?.entities.length?protection.entities.map(e=><Pill tone="green" key={`${e.type}-${e.start}`}>{e.type} · {e.token}</Pill>):protection?<Pill tone="amber">No identifiers detected</Pill>:null}</div><div className="try-actions"><Button onClick={resetProtection} disabled={busy}><RotateCcw size={15}/>Reset</Button><Button variant="primary" disabled={busy||!input.trim()} onClick={protectSample}><ShieldCheck size={15}/>{busy?"Protecting…":"Protect text"}</Button></div></div></Card>
      {summary && <Card><CardHeader title="Protected AI summary" subtitle="Generated from the right-side transcript only" action={<Pill tone="green"><Sparkles size={12}/>No raw identifiers</Pill>}/><div className="summary-box">{summary}</div></Card>}
    </div><aside className="live-side">
      <Card><CardHeader title="Speaker ↔ person map" subtitle="Authentication happens outside the LLM" action={<Pill tone="blue">Local vault</Pill>}/><div className="speaker-list">{demo.speakers.map((speaker,i)=><div className="speaker-row" key={speaker.track}><span className={`speaker-avatar ${speaker.color}`}>{speaker.initials}</span><span><strong>{speaker.name}</strong><small>{speaker.track} · {speaker.role}</small></span><em className={speaker.status}>{speaker.assurance}</em></div>)}</div><div className="identity-note"><LockKeyhole size={13}/>The LLM receives random tokens such as [SPEAKER_8A91C2], while unbound tracks stay [UNKNOWN]—never these names.</div></Card>
      <Card><CardHeader title="How identity is established" subtitle="An LLM does not authenticate a human" action={<CircleUserRound size={18}/>}/><div className="identity-steps">{[
        ["Verify session","SSO, OTP, CRM/EHR check-in, IVR or app login"],["Separate voices","Local diarization maintains Speaker A/B/C"],["Bind or stay unknown","Host assertion binds a verified identity"],["Tokenize for AI","Real mapping remains in the local vault"]
      ].map((step,i)=><div key={step[0]}><i>{i+1}</i><span><strong>{step[0]}</strong><small>{step[1]}</small></span></div>)}</div></Card>
      <Card><CardHeader title="Self-hosted model path" subtitle="No per-hour speech API required" action={<Pill tone="green">No metered speech API</Pill>}/><div className="model-stack"><div><Cpu size={16}/><span><strong>faster-whisper</strong><small>English speech-to-text</small></span></div><div><UsersRound size={16}/><span><strong>pyannote.audio</strong><small>Speaker diarization</small></span></div><div><ShieldCheck size={16}/><span><strong>Presidio + rules</strong><small>PII / PHI / PCI / secrets</small></span></div><div><Bot size={16}/><span><strong>Ollama · optional</strong><small>Local summary generation</small></span></div></div></Card>
      <Card><CardHeader title="Downstream route" subtitle="Any application, any approved model" action={<Pill tone="amber">Policy gated</Pill>}/><div className="route-list"><div><span><Bot size={16}/></span><p><strong>{demo.route}</strong><small>Protected transcript only</small></p><em>Protected</em></div><div><span><Send size={16}/></span><p><strong>{demo.destination}</strong><small>Controlled re-association</small></p><em>Receipt required</em></div></div><Button className="full" variant="primary" onClick={summarize} disabled={busy}><Sparkles size={15}/>Send protected stream to local AI</Button></Card>
    </aside></div>
  </div>;
}

function EmptyPane({state}:{state:"idle"|"connecting"|"listening"|"paused"|"processing"|"complete"|"error"}){
  const copy=state==="connecting"?["Connecting securely","Opening the configured self-hosted voice edge."]:state==="listening"?["Listening for speech","Speak naturally; live raw and masked text will appear here."]:state==="processing"?["Finishing transcription","The final audio chunk is being protected."]:state==="error"?["Live capture unavailable","Start the edge-service or use 'Run sample' for demonstration."]:["Waiting for live voice","Select Start live capture after connecting microphone, or use 'Run sample' for demonstration."];
  return <div className="empty-pane"><Radio size={26}/><strong>{copy[0]}</strong><small>{copy[1]}</small></div>;
}
