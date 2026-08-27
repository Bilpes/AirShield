"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import {
  AlertTriangle,
  Bot,
  CalendarCheck2,
  CircleStop,
  Mic,
  Minimize2,
  RotateCcw,
  Send,
  ShieldCheck,
  Stethoscope,
  Video,
  X,
} from "lucide-react";

type ChatItem =
  | { id: string; kind: "assistant" | "user"; text: string }
  | {
      id: string;
      kind: "protected";
      text: string;
      count: number;
      receipt: string;
      decision: string;
      routed: boolean;
    }
  | { id: string; kind: "booking"; text: string };

type ProtectionPayload = {
  protected_text?: string;
  entities?: Array<{ type: string; token: string }>;
  decision?: string;
  receipt?: { receipt_id?: string; signature?: string } | null;
  error?: string;
  detail?: string;
};

const INITIAL_MESSAGES: ChatItem[] = [
  {
    id: "welcome",
    kind: "assistant",
    text: "I can guide a virtual symptom check and book a doctor. This demonstration is not medical diagnosis or emergency care.",
  },
];

const QUICK_COMMANDS = [
  "I have a fever and need a virtual doctor today",
  "Book a video visit tomorrow at 10 AM",
  "Find a general physician for a virtual checkup",
];

function id(prefix: string): string {
  return `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function looksUrgent(text: string): boolean {
  return /\b(severe chest pain|difficulty breathing|can(?:not|'t) breathe|faint(?:ed|ing)?|unconscious|stroke|heavy bleeding|suicid(?:e|al))\b/i.test(text);
}

export function DoctorBookingBot({ notify }: { notify: (message: string) => void }) {
  const [open, setOpen] = useState(true);
  const [messages, setMessages] = useState<ChatItem[]>(INITIAL_MESSAGES);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [stage, setStage] = useState<1 | 2 | 3>(1);
  const [showSlots, setShowSlots] = useState(false);
  const [recording, setRecording] = useState(false);
  const [voiceDraft, setVoiceDraft] = useState("");
  const [voiceError, setVoiceError] = useState("");
  const [voiceAvailable, setVoiceAvailable] = useState<boolean | null>(null);
  const session = useRef<string | null>(null);
  const list = useRef<HTMLDivElement>(null);
  const stream = useRef<MediaStream | null>(null);
  const recorder = useRef<MediaRecorder | null>(null);
  const socket = useRef<WebSocket | null>(null);
  const audioQueue = useRef<Promise<void>>(Promise.resolve());
  const voiceTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const voiceRaw = useRef<string[]>([]);
  const voiceProtected = useRef<string[]>([]);
  const voiceEntities = useRef(0);

  useEffect(() => {
    list.current?.scrollTo({ top: list.current.scrollHeight, behavior: "smooth" });
  }, [messages, showSlots, voiceDraft, voiceError]);

  useEffect(
    () => () => {
      if (voiceTimer.current) clearTimeout(voiceTimer.current);
      if (recorder.current?.state !== "inactive") recorder.current?.stop();
      stream.current?.getTracks().forEach((track) => track.stop());
      socket.current?.close();
    },
    [],
  );

  // Check if edge service is available for voice
  useEffect(() => {
    if (voiceAvailable !== null) return;
    const url = edgeUrl();
    if (!url) {
      setVoiceAvailable(false);
      return;
    }
    // ws://localhost:8001/ws/voice -> http://localhost:8001/v1/health
    const healthUrl = url.replace(/^ws:/, "http:").replace(/\/ws\/voice$/, "/v1/health");
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 3000);
    fetch(healthUrl, { method: "GET", signal: controller.signal })
      .then(res => {
        clearTimeout(timeout);
        setVoiceAvailable(res.ok);
      })
      .catch(() => {
        clearTimeout(timeout);
        setVoiceAvailable(false);
      });
  }, [voiceAvailable]);

  async function ensureSession(): Promise<string> {
    if (session.current) return session.current;
    const response = await fetch("/api/sessions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ policy: "Healthcare · HIPAA", ttl_minutes: 30 }),
    });
    const data = (await response.json()) as { session_id?: string; error?: string; detail?: string };
    if (!response.ok || !data.session_id) {
      throw new Error(data.error || data.detail || "A protected healthcare session could not be created.");
    }
    session.current = data.session_id;
    return data.session_id;
  }

  function addProtectedConversation(
    raw: string,
    protectedText: string,
    count: number,
    receipt: string,
    decision = "allow",
  ) {
    setMessages((current) => [
      ...current,
      { id: id("user"), kind: "user", text: raw },
      {
        id: id("protected"),
        kind: "protected",
        text: protectedText,
        count,
        receipt,
        decision,
        routed: true,
      },
      {
        id: id("safety"),
        kind: "assistant",
        text: "Before booking: if you have severe chest pain, fainting, new confusion, or difficulty breathing, contact local emergency services now. Otherwise, continue with the demo appointment flow.",
      },
    ]);
    setStage(2);
    setShowSlots(true);
  }

  function addHeldConversation(
    raw: string,
    protectedText: string,
    count: number,
    receipt: string,
    decision: string,
  ) {
    setMessages((current) => [
      ...current,
      { id: id("user"), kind: "user", text: raw },
      {
        id: id("protected"),
        kind: "protected",
        text: protectedText || "[NO CONTENT RELEASED]",
        count,
        receipt,
        decision,
        routed: false,
      },
      {
        id: id("held"),
        kind: "assistant",
        text: `AirShield returned ${decision}. The protected turn was held inside the trust boundary, so no RIA or booking step was opened.`,
      },
    ]);
    setStage(1);
    setShowSlots(false);
  }

  async function protectAndSend(raw: string) {
    setBusy(true);
    setVoiceError("");
    try {
      if (looksUrgent(raw)) {
        setMessages((current) => [
          ...current,
          { id: id("user"), kind: "user", text: raw },
          {
            id: id("urgent"),
            kind: "assistant",
            text: "This may describe an emergency. Contact local emergency services now. No RIA or appointment action was performed.",
          },
        ]);
        setStage(1);
        setShowSlots(false);
        notify("Possible emergency warning signs detected. Contact local emergency services now.");
        return;
      }
      const sessionId = await ensureSession();
      const response = await fetch("/api/protect", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionId,
          text: raw,
          policy: "Healthcare · HIPAA",
          destination: "Clinical note AI",
        }),
      });
      const data = (await response.json()) as ProtectionPayload;
      if (!response.ok) throw new Error(data.error || data.detail || "Protection was denied.");
      const protectedText = data.protected_text || "";
      const entities = Array.isArray(data.entities) ? data.entities : [];
      const decision = data.decision || "review";
      const receipt = data.receipt?.receipt_id || "no egress receipt";
      if (decision !== "allow") {
        addHeldConversation(raw, protectedText, entities.length, receipt, decision);
        notify(`Doctor bot request held by healthcare policy: ${decision}.`);
        return;
      }
      if (!protectedText) throw new Error("The protection service returned an incomplete allow response.");
      addProtectedConversation(raw, protectedText, entities.length, receipt, decision);
      notify("Only the protected request entered the doctor-booking demonstration flow.");
    } catch (error) {
      const message = error instanceof Error ? error.message : "The protected doctor bot is unavailable.";
      setVoiceError(message);
      notify(message);
    } finally {
      setBusy(false);
    }
  }

  async function submit(event?: FormEvent) {
    event?.preventDefault();
    const value = input.trim();
    if (!value || busy || recording) return;
    setInput("");
    await protectAndSend(value);
  }

  function edgeUrl(): string | null {
    const configured = process.env.NEXT_PUBLIC_EDGE_WS_URL?.trim();
    if (configured) return configured;
    if (
      typeof window !== "undefined" &&
      window.location.protocol === "http:" &&
      ["localhost", "127.0.0.1"].includes(window.location.hostname)
    ) {
      return `ws://${window.location.hostname}:8001/ws/voice`;
    }
    return null;
  }

  function releaseVoice() {
    stream.current?.getTracks().forEach((track) => track.stop());
    stream.current = null;
    recorder.current = null;
    setRecording(false);
  }

  async function startVoice() {
    const url = edgeUrl();
    if (!url) {
      const message = "Configure NEXT_PUBLIC_EDGE_WS_URL to use voice booking demo, or use text input.";
      setVoiceError(message);
      notify(message);
      return;
    }
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") {
      const message = "Microphone recording is unavailable in this browser. Use HTTPS or localhost.";
      setVoiceError(message);
      notify(message);
      return;
    }
    setVoiceError("");
    setVoiceDraft("Connecting to the private voice edge…");
    voiceRaw.current = [];
    voiceProtected.current = [];
    voiceEntities.current = 0;
    try {
      const media = await navigator.mediaDevices.getUserMedia({
        audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true },
      });
      stream.current = media;
      const ws = new WebSocket(url);
      socket.current = ws;
      ws.onopen = () => {
        try {
          const formats = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4", "audio/ogg;codecs=opus"];
          const mimeType = formats.find((format) => MediaRecorder.isTypeSupported(format));
          const mediaRecorder = new MediaRecorder(media, mimeType ? { mimeType } : undefined);
          recorder.current = mediaRecorder;
          audioQueue.current = Promise.resolve();
          mediaRecorder.ondataavailable = (chunk) => {
            if (!chunk.data.size) return;
            audioQueue.current = audioQueue.current.then(async () => {
              const bytes = await chunk.data.arrayBuffer();
              if (ws.readyState === WebSocket.OPEN) ws.send(bytes);
            });
          };
          mediaRecorder.onstop = () => {
            void audioQueue.current.then(() => {
              if (ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ type: "session.end" }));
            });
          };
          ws.send(
            JSON.stringify({
              type: "session.start",
              language: "en",
              policy: "Healthcare · HIPAA",
              audio_format: mediaRecorder.mimeType || mimeType || "audio/webm",
            }),
          );
          mediaRecorder.start(750);
          setRecording(true);
          setVoiceDraft("Listening privately… Select the stop button when your command is complete.");
        } catch {
          releaseVoice();
          ws.close();
          setVoiceError("The browser recorder could not start.");
        }
      };
      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(String(event.data));
          if (message.type === "transcript.pair" && typeof message.raw === "string") {
            voiceRaw.current.push(message.raw);
            if (typeof message.protected === "string") voiceProtected.current.push(message.protected);
            if (Array.isArray(message.entities)) voiceEntities.current += message.entities.length;
            setVoiceDraft(`Heard locally: ${voiceRaw.current.join(" ")} · protected preview is provisional`);
          } else if (message.type === "policy.decision" && message.decision !== "allow") {
            if (voiceTimer.current) clearTimeout(voiceTimer.current);
            const reason = typeof message.reason === "string" ? message.reason : "voice policy denied the request";
            setVoiceError(`Voice command blocked: ${reason}. No RIA request was released.`);
            releaseVoice();
            ws.close();
          } else if (message.type === "transcript.final") {
            if (voiceTimer.current) clearTimeout(voiceTimer.current);
            const raw = voiceRaw.current.join(" ").trim();
            const protectedText =
              typeof message.protected === "string" && message.protected
                ? message.protected
                : voiceProtected.current.join(" ").trim();
            const decision = typeof message.decision === "string" ? message.decision : "review";
            const receipt = message.receipt && typeof message.receipt === "object" ? message.receipt : null;
            const signature = typeof receipt?.signature === "string" ? receipt.signature : "";
            const signedAllow =
              decision === "allow" &&
              message.safe_for_egress === true &&
              signature.length >= 40 &&
              signature !== "demo_unsigned";
            const count = Array.isArray(message.entities) ? message.entities.length : voiceEntities.current;
            const receiptId = typeof receipt?.receipt_id === "string" ? receipt.receipt_id : "no signed voice receipt";
            if (raw && protectedText && signedAllow) {
              addProtectedConversation(raw, protectedText, count, receiptId, decision);
              notify("Voice completed with a signed allow receipt; only protected text entered the booking demo.");
            } else if (raw) {
              addHeldConversation(raw, protectedText, count, receiptId, decision);
              notify("Voice remained inside the trust boundary because no signed final allow receipt was available.");
            } else {
              setVoiceError("No protected English speech was available; nothing was sent to the bot.");
            }
            setVoiceDraft("");
            releaseVoice();
            ws.close();
          }
        } catch {
          if (voiceTimer.current) clearTimeout(voiceTimer.current);
          setVoiceError("The voice edge returned an invalid response; no bot request was released.");
          releaseVoice();
          ws.close();
        }
      };
      ws.onerror = () => {
        if (voiceTimer.current) clearTimeout(voiceTimer.current);
        setVoiceError("Could not connect to the self-hosted voice edge. Configure NEXT_PUBLIC_EDGE_WS_URL.");
        setVoiceDraft("");
        releaseVoice();
      };
      ws.onclose = () => {
        socket.current = null;
      };
    } catch {
      releaseVoice();
      setVoiceDraft("");
      const message = "Microphone permission was denied or the device is unavailable.";
      setVoiceError(message);
      notify(message);
    }
  }

  function stopVoice() {
    if (recorder.current?.state === "recording" || recorder.current?.state === "paused") {
      recorder.current.stop();
      setVoiceDraft("Final audio is being transcribed and protected…");
      setRecording(false);
      stream.current?.getTracks().forEach((track) => track.stop());
      if (voiceTimer.current) clearTimeout(voiceTimer.current);
      voiceTimer.current = setTimeout(() => {
        setVoiceDraft("");
        setVoiceError("Timed out waiting for the final privacy check; no RIA request was released.");
        socket.current?.close();
        releaseVoice();
      }, 120_000);
    }
  }

  function reserveSlot() {
    setStage(3);
    setShowSlots(false);
    setMessages((current) => [
      ...current,
      {
        id: id("booking"),
        kind: "booking",
        text: "Demo slot reserved: Virtual General Physician, tomorrow at 10:00 AM. No real appointment or clinical record was created.",
      },
    ]);
    notify("Demo appointment reserved through the trusted booking-connector pattern.");
  }

  function urgentGuidance() {
    setShowSlots(false);
    setMessages((current) => [
      ...current,
      {
        id: id("urgent"),
        kind: "assistant",
        text: "This booking demonstration cannot assess an emergency. Contact local emergency services or an approved urgent-care channel now. No appointment action was performed.",
      },
    ]);
  }

  function reset() {
    session.current = null;
    if (voiceTimer.current) clearTimeout(voiceTimer.current);
    voiceTimer.current = null;
    socket.current?.close();
    releaseVoice();
    setMessages(INITIAL_MESSAGES);
    setInput("");
    setStage(1);
    setShowSlots(false);
    setVoiceDraft("");
    setVoiceError("");
  }

  if (!open) {
    return (
      <button className="doctor-bot-launcher" onClick={() => setOpen(true)} aria-label="Open protected doctor booking assistant">
        <span><Stethoscope size={21}/></span>
        <span><strong>CareShield Assistant</strong><small>Protected doctor booking</small></span>
        <i/>
      </button>
    );
  }

  return (
    <aside className="doctor-bot-panel" aria-label="Protected virtual doctor and appointment booking demonstration">
      <header className="doctor-bot-header">
        <span className="doctor-bot-logo"><ShieldCheck size={24}/></span>
        <span><strong>CareShield Assistant</strong><small>Virtual checkup & doctor booking</small><em><i/>Online · RIA demo path</em></span>
        <button onClick={reset} aria-label="Reset doctor bot"><RotateCcw size={15}/></button>
        <button onClick={() => setOpen(false)} aria-label="Minimize doctor bot"><Minimize2 size={16}/></button>
        <button onClick={() => setOpen(false)} aria-label="Close doctor bot"><X size={17}/></button>
      </header>

      <div className="doctor-bot-protected"><ShieldCheck size={15}/><strong>AirShield protected</strong><span>Raw details stay inside your trust boundary</span></div>

      <div className="doctor-bot-steps">
        {["Symptoms", "Doctor", "Book"].map((label, index) => {
          const number = (index + 1) as 1 | 2 | 3;
          return <div className={stage >= number ? "active" : ""} key={label}><i>{number}</i><span>{label}</span></div>;
        })}
      </div>

      <div className="doctor-bot-chat" ref={list} aria-live="polite">
        {messages.length === 1 && <div className="doctor-bot-command-intro"><span>Try a text or voice command</span><div>{QUICK_COMMANDS.map((command, index)=><button key={command} onClick={()=>setInput(command)}>{index===0?"Describe symptoms":index===1?"Book video visit":"Find a specialist"}</button>)}</div></div>}
        {messages.map((message) => {
          if (message.kind === "protected") {
            return <article className={`doctor-bot-protection ${message.routed ? "routed" : "held"}`} key={message.id}><header><ShieldCheck size={13}/><strong>{message.routed ? "Sent to RIA demo — protected text" : "Held by AirShield — not routed"}</strong></header><p>{message.text}</p><footer><span>{message.count} identifiers tokenized</span><span>{message.decision}</span><span>Receipt {message.receipt.slice(0,18)}</span></footer></article>;
          }
          if (message.kind === "booking") {
            return <article className="doctor-bot-booked" key={message.id}><CalendarCheck2 size={18}/><span><strong>Demo booking complete</strong><p>{message.text}</p></span></article>;
          }
          return <article className={`doctor-bot-message ${message.kind}`} key={message.id}><small>{message.kind === "user" ? "You · raw local view" : "Care assistant"}</small><p>{message.text}</p></article>;
        })}

        {showSlots && <>
          <div className="doctor-bot-safety"><AlertTriangle size={14}/><button onClick={urgentGuidance}>I may have emergency signs</button><button onClick={()=>setShowSlots(true)}>No emergency signs</button></div>
          <article className="doctor-bot-slot"><span><Stethoscope size={18}/></span><div><strong>Virtual General Physician</strong><small><Video size={12}/>Tomorrow · 10:00 AM · 20 min</small></div><button onClick={reserveSlot}>Reserve slot</button></article>
        </>}
        {voiceDraft && <div className="doctor-bot-voice-state"><span className="voice-bars">{[5,11,17,8,14,19,7,13].map((height,index)=><i key={index} style={{height}}/>)}</span><span>{voiceDraft}</span></div>}
        {voiceError && <div className="doctor-bot-error" role="alert"><AlertTriangle size={13}/><span>{voiceError}</span></div>}
        {voiceAvailable === false && !voiceDraft && !voiceError && <div className="doctor-bot-error" role="alert"><AlertTriangle size={13}/><span>Voice requires Docker. Run: docker compose up. Use text input instead.</span></div>}
      </div>

      <form className="doctor-bot-compose" onSubmit={submit}>
        <label><span className="sr-only">Doctor booking command</span><input value={input} onChange={(event)=>setInput(event.target.value)} placeholder="Type symptoms or booking request…" maxLength={4000}/></label>
        <button type="button" className={recording?"recording":""} onClick={recording?stopVoice:startVoice} disabled={voiceAvailable === false && !recording} title={voiceAvailable === false ? "Voice requires Docker. Use text input." : "Protected voice command"} aria-label={recording?"Stop voice command":"Start protected voice command"}>{recording?<CircleStop size={18}/>:<Mic size={18}/>}</button>
        <button type="submit" disabled={busy||recording||!input.trim()} aria-label="Protect and send booking command"><Send size={18}/></button>
        <small><ShieldCheck size={11}/>Only protected text enters the RIA and trusted booking demonstration path.</small>
      </form>
    </aside>
  );
}
