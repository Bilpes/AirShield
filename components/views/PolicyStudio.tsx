"use client";

import { useState } from "react";
import type { LucideIcon } from "lucide-react";
import { Beaker, Building2, CreditCard, FileBadge, Headphones, Mail, MapPin, Phone, Save, ShieldCheck, SlidersHorizontal, UserRound, CalendarDays, Hash } from "lucide-react";
import { Button, Card, CardHeader, PageIntro, Pill } from "../ui";

const templates = [
  ["Healthcare · HIPAA","Clinical PHI & identifiers",Building2],["Financial services · PCI","Accounts, cards & identity",CreditCard],["Insurance claims","Policyholder & claim data",FileBadge],["Contact center privacy","Customer PII & payment",Headphones],["Internal copilot DLP","Secrets and company data",SlidersHorizontal]
] as const;
const initialRules: [string, string, string, number, LucideIcon][] = [
  ["Names & people","Patients, customers, employees","Tokenize",82,UserRound],["Dates of birth","Exact and contextual dates","Date shift",90,CalendarDays],["Account / record IDs","MRN, policy, account, customer IDs","Tokenize",95,Hash],["Phone numbers","Local and international formats","Mask",90,Phone],["Addresses & locations","Street and precise geography","Generalize",86,MapPin],["Email addresses","Personal and business email","Mask",94,Mail]
];

export function PolicyStudio({notify}:{notify:(m:string)=>void}){
  const [template,setTemplate]=useState("Healthcare · HIPAA");
  const [version,setVersion]=useState(12);
  const [rules,setRules]=useState(initialRules.map(r=>({name:r[0],detail:r[1],action:r[2],confidence:r[3],icon:r[4],enabled:true})));
  const publish=()=>{setVersion(v=>v+1);notify(`Policy version ${version+1} published.`)};
  return <div className="view"><PageIntro title="Define what may leave your boundary" description="Versioned industry policies control detection, treatment, confidence, vaulting, and downstream routes." actions={<><Button onClick={()=>notify("Policy test passed on the synthetic English corpus.")}><Beaker size={15}/>Test policy</Button><Button variant="primary" onClick={publish}><Save size={15}/>Publish changes</Button></>}/>
    <div className="policy-layout"><Card><CardHeader title="Industry templates" subtitle="One engine, different policy packs"/><div className="template-list">{templates.map(([name,detail,Icon])=><button key={name} className={template===name?"active":""} onClick={()=>setTemplate(name)}><i><Icon size={16}/></i><span><strong>{name}</strong><small>{detail}</small></span>{template===name&&<span className="status-dot"/>}</button>)}</div></Card>
    <Card className="policy-main"><div className="policy-summary"><span><h3>{template}</h3><p>Applies to English voice, transcripts, prompts, logs, chat, and destination write-back.</p></span><span><strong>94%</strong><small>demo coverage</small><Pill tone="amber">Pilot target</Pill></span></div><div className="section-heading"><h3>Protected entity rules</h3><p>Validate thresholds against a representative industry corpus before production.</p></div><div className="rule-list">{rules.map((rule,index)=><div className="rule-row" key={rule.name}><span className="rule-name"><i><rule.icon size={15}/></i><span><strong>{rule.name}</strong><small>{rule.detail}</small></span></span><select value={rule.action} onChange={e=>setRules(v=>v.map((r,i)=>i===index?{...r,action:e.target.value}:r))}>{["Tokenize","Mask","Redact","Date shift","Generalize","Allow"].map(a=><option key={a}>{a}</option>)}</select><label className="range"><input type="range" min="50" max="99" value={rule.confidence} onChange={e=>setRules(v=>v.map((r,i)=>i===index?{...r,confidence:+e.target.value}:r))}/><output>{rule.confidence}%</output></label><label className="switch"><input type="checkbox" checked={rule.enabled} onChange={e=>setRules(v=>v.map((r,i)=>i===index?{...r,enabled:e.target.checked}:r))}/><span/></label></div>)}</div><div className="section-heading"><h3>Enforcement</h3><p>Controls applied whenever this policy is active.</p></div><div className="setting-rows"><Setting title="Fail closed" detail="Block AI egress when detection or policy evaluation is unavailable."/><Setting title="Require egress receipt" detail="Hash protected content and record policy, route, and entity counts."/><Setting title="English only" detail="Reject or route non-English sessions for manual review."/></div><footer className="policy-footer"><span>Published version {version} · demo workspace</span><Button size="sm" variant="primary" onClick={publish}><ShieldCheck size={14}/>Publish v{version+1}</Button></footer></Card></div>
  </div>
}
function Setting({title,detail}:{title:string;detail:string}){return <div><span><strong>{title}</strong><small>{detail}</small></span><label className="switch"><input type="checkbox" defaultChecked/><span/></label></div>}
