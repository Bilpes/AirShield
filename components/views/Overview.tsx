"use client";

import { Activity, ArrowRight, CloudCog, Download, LockKeyhole, Mic2, ShieldCheck, Sparkles, UsersRound } from "lucide-react";
import type { ViewId } from "@/lib/types";
import { Button, Card, CardHeader, PageIntro, Pill } from "../ui";

const stats = [
  { label: "Protected voice sessions", value: "1,284", trend: "+12.6%", icon: ShieldCheck },
  { label: "Sensitive entities blocked", value: "8,642", trend: "+18.2%", icon: LockKeyhole },
  { label: "Safe AI requests", value: "12.8K", trend: "100% attested", icon: CloudCog },
  { label: "Added edge latency", value: "74 ms", trend: "demo p95", icon: Activity },
];
const recent = [
  ["Person name", "[CUSTOMER_1]", "Finance voice", "12:44:11", "Tokenized"],
  ["Medical record no.", "[MRN_1]", "Healthcare voice", "12:41:12", "Tokenized"],
  ["Phone number", "•••• ••• 3210", "Contact center", "12:38:06", "Masked"],
  ["API secret", "[SECRET_1]", "Internal copilot", "12:21:54", "Blocked"],
];

export function Overview({ navigate, notify }: { navigate: (v: ViewId) => void; notify: (m: string) => void }) {
  return <div className="view">
    <PageIntro title="Voice and text privacy at a glance" description="One self-hosted control plane for healthcare, finance, insurance, contact centers, and enterprise copilots." actions={<><Button onClick={()=>notify("Demo posture report prepared.")}><Download size={15}/>Export report</Button><Button variant="primary" onClick={()=>navigate("live")}><Mic2 size={15}/>Open Live Shield</Button></>}/>
    <Card className="hero-card"><div><span className="hero-eyebrow"><span className="status-dot"/>All local protection services operational</span><h2>Your AI boundary is protected</h2><p>Raw voice, identity, regulated data, and secrets remain on your infrastructure. Only protected context reaches the downstream AI.</p></div><div className="posture"><div className="posture-ring"><strong>96</strong><small>posture</small></div><span><small>Controls passing</small><strong>24 of 25</strong><small>Evidence sync · 2m ago</small></span></div></Card>
    <div className="stats-grid">{stats.map((stat)=><Card className="stat-card" key={stat.label}><div className="stat-top"><span>{stat.label}</span><i><stat.icon size={15}/></i></div><div><strong>{stat.value}</strong><small>{stat.trend}</small></div><svg viewBox="0 0 80 28" preserveAspectRatio="none" aria-hidden="true"><path d="M0 24 C9 21 13 25 21 18 S35 20 42 12 S54 16 62 8 S72 12 80 3"/></svg></Card>)}</div>
    <div className="overview-grid">
      <Card><CardHeader title="Protection path" subtitle="Raw input stays local; protected meaning moves forward" action={<Pill tone="green"><span className="status-dot"/>Live</Pill>}/><div className="flow"><div><span><Mic2/></span><strong>Capture</strong><small>Voice or text</small></div><i/><div><span><UsersRound/></span><strong>Identify</strong><small>Voice tracks</small></div><i/><div><span><ShieldCheck/></span><strong>Protect</strong><small>Local models</small></div><i/><div><span className="safe"><CloudCog/></span><strong>Safe egress</strong><small>Any AI</small></div></div><div className="flow-note"><LockKeyhole size={14}/>PII, PHI, PCI and secrets remain inside the trust boundary <strong>English model pack</strong></div></Card>
      <Card><CardHeader title="Protected traffic" subtitle="Safe outbound AI calls" action={<Pill tone="green">No leakage</Pill>}/><div className="traffic"><strong>12,804</strong><small>+14.2% from prior period</small><div className="bar-chart">{[55,72,61,83,70,91,78].map((h,i)=><div key={i}><i className={i===6?"today":""} style={{height:`${h}%`}}/><span>{["M","T","W","T","F","S","S"][i]}</span></div>)}</div></div></Card>
    </div>
    <Card className="table-card"><CardHeader title="Recently protected" subtitle="Latest sensitive entities intercepted before AI egress" action={<button className="text-link" onClick={()=>navigate("audit")}>View audit trail <ArrowRight size={14}/></button>}/><div className="table-scroll"><table><thead><tr><th>Entity</th><th>Protected value</th><th>Workflow</th><th>Time</th><th>Action</th></tr></thead><tbody>{recent.map((row,i)=><tr key={row[0]}><td><span className="entity-cell"><i>{["PN","MR","PH","SK"][i]}</i><span><strong>{row[0]}</strong><small>Confidence {99-i}.1%</small></span></span></td><td><code>{row[1]}</code></td><td>{row[2]}</td><td className="muted">{row[3]}</td><td><Pill tone={row[4]==="Blocked"?"red":"green"}>{row[4]}</Pill></td></tr>)}</tbody></table></div></Card>
  </div>;
}
