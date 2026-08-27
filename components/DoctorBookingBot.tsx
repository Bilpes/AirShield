"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import {
  AlertTriangle,
  Bot,
  CalendarCheck2,
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
  const session = useRef<string | null>(null);
  const list = useRef<HTMLDivElement>(null);

  useEffect(() => {
    list.current?.scrollTo({ top: list.current.scrollHeight, behavior: "smooth" });
  }, [messages, showSlots]);

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
      notify(message);
    } finally {
      setBusy(false);
    }
  }

  async function submit(event?: FormEvent) {
    event?.preventDefault();
    const value = input.trim();
    if (!value || busy) return;
    setInput("");
    await protectAndSend(value);
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
    setMessages(INITIAL_MESSAGES);
    setInput("");
    setStage(1);
    setShowSlots(false);
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
        {messages.length === 1 && <div className="doctor-bot-command-intro"><span>Try a text command</span><div>{QUICK_COMMANDS.map((command, index)=><button key={command} onClick={()=>setInput(command)}>{index===0?"Describe symptoms":index===1?"Book video visit":"Find a specialist"}</button>)}</div></div>}
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
      </div>

      <form className="doctor-bot-compose" onSubmit={submit}>
        <label><span className="sr-only">Doctor booking command</span><input value={input} onChange={(event)=>setInput(event.target.value)} placeholder="Type symptoms or booking request…" maxLength={4000}/></label>
        <button type="submit" disabled={busy||!input.trim()} aria-label="Protect and send booking command"><Send size={18}/></button>
        <small><ShieldCheck size={11}/>Only protected text enters the RIA and trusted booking demonstration path.</small>
      </form>
    </aside>
  );
}
