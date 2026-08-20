"use client";

import { useState } from "react";
import { ArrowRight, Check, Copy, KeyRound, Plus, Radio, Webhook } from "lucide-react";
import { Button, Card, CardHeader, PageIntro, Pill } from "../ui";

const integrations=[
  ["FW","faster-whisper","Local English transcription","Ready","green","No API fee"],
  ["PY","pyannote.audio","Local speaker diarization","Ready","green","No API fee"],
  ["PR","Presidio","PII/PHI/PCI detection","Ready","green","No API fee"],
  ["OL","Ollama","Optional local LLM summaries","Configure","blue","Self-hosted"],
  ["EH","EHR / FHIR","Healthcare destination","Configure","blue","Not connected"],
  ["CR","CRM / Contact center","BPO and finance destination","Configure","blue","Not connected"],
];
const samples={
  curl:`curl -X POST http://localhost:4174/api/protect \\\n  -H "Content-Type: application/json" \\\n  -d '{"text":"Customer text", "policy":"Financial services · PCI", "destination":"Banking support AI"}'`,
  dotnet:`var result = await client.PostAsJsonAsync("/api/protect",\n  new { text, policy = "Financial services · PCI", destination = "Banking support AI" });`,
  java:`HttpRequest request = HttpRequest.newBuilder()\n  .uri(URI.create(baseUrl + "/api/protect"))\n  .POST(BodyPublishers.ofString(payload)).build();`,
  python:`result = requests.post(f"{base_url}/api/protect",\n  json={"text": text, "policy": "Financial services · PCI", "destination": "Banking support AI"})`,
  node:`const result = await fetch("/api/protect", {\n  method: "POST", body: JSON.stringify({ text, policy })\n});`,
  go:`req, _ := http.NewRequest("POST", baseURL+"/api/protect",\n  bytes.NewReader(payload))`,
};
type Tab=keyof typeof samples;
export function Connections({notify}:{notify:(m:string)=>void}){
  const [tab,setTab]=useState<Tab>("curl");
  return <div className="view"><PageIntro title="Connect once. Protect every application." description="REST, WebSocket, reverse-proxy, sidecar, and SDK integration for any language or host application." actions={<Button variant="primary" onClick={()=>notify("Connection wizard opened in demo mode.")}><Plus size={15}/>Add connection</Button>}/><div className="connection-grid">{integrations.map(item=><Card className="connection-card" key={item[1]}><div><span>{item[0]}</span><Pill tone={item[4] as "green"|"blue"}>{item[3]}</Pill></div><h3>{item[1]}</h3><p>{item[2]}</p><footer><span>{item[5]}</span><button onClick={()=>notify(`${item[1]} configuration selected.`)}>{item[3]==="Ready"?"Manage":"Open"}<ArrowRight size={13}/></button></footer></Card>)}</div><div className="section-intro"><span><h3>Universal developer access</h3><p>Java, .NET, Python, Node.js, Go, mobile, telephony, and any HTTP/WebSocket client.</p></span><Button size="sm" onClick={()=>notify("Sandbox key created in demo mode.")}><KeyRound size={14}/>Create API key</Button></div><div className="api-grid"><Card><CardHeader title="API endpoints" subtitle="Language-neutral contracts"/><div className="endpoint-list"><div><i><Webhook size={15}/></i><span><strong>POST /api/protect</strong><small>Text, prompt, log, ticket, transcript</small></span><Pill tone="green">REST</Pill></div><div><i><Radio size={15}/></i><span><strong>WS /ws/voice</strong><small>PCM, Opus, or G.711 audio</small></span><Pill tone="blue">Stream</Pill></div><div><i><Check size={15}/></i><span><strong>GET /api/health</strong><small>Local model readiness</small></span><Pill tone="green">Ready</Pill></div></div></Card><Card className="code-card"><div className="code-tabs">{(Object.keys(samples) as Tab[]).map(t=><button key={t} className={tab===t?"active":""} onClick={()=>setTab(t)}>{t==="dotnet"?".NET":t==="node"?"Node.js":t}</button>)}<button className="copy" onClick={async()=>{await navigator.clipboard.writeText(samples[tab]);notify("Code sample copied.")}}><Copy size={13}/>Copy</button></div><pre>{samples[tab]}</pre></Card></div></div>
}
