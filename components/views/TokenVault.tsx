"use client";

import { useMemo, useState } from "react";
import { AlertTriangle, Eye, KeyRound, LockKeyhole, Search, Settings, X } from "lucide-react";
import { Button, Card, CardHeader, PageIntro, Pill } from "../ui";

const tokens=[
  ["[CUSTOMER_1]","Person","FIN-8F2A","12:44:09","22h 41m","OTP verified"],
  ["[ACCOUNT_1]","Bank account","FIN-8F2A","12:44:11","22h 41m","No access"],
  ["[MRN_1]","Medical record no.","HC-44B1","11:52:33","21h 50m","EHR service"],
  ["[PHONE_1]","Phone","BPO-44B1","11:52:37","21h 50m","No access"],
  ["[POLICY_ID_1]","Policy number","INS-119C","09:16:24","19h 14m","Claims reviewer"],
  ["[SECRET_1]","API credential","SAS-311A","08:02:17","Revoked","Security team"],
];
export function TokenVault({notify}:{notify:(m:string)=>void}){
  const [query,setQuery]=useState(""); const [selected,setSelected]=useState<string|null>(null); const [purpose,setPurpose]=useState("");
  const visible=useMemo(()=>tokens.filter(t=>t.join(" ").toLowerCase().includes(query.toLowerCase())),[query]);
  return <div className="view"><PageIntro title="Encrypted token mappings" description="The LLM sees stable tokens. Actual identity mappings stay in a separately permissioned local trust plane." actions={<Button onClick={()=>notify("Vault configuration is available under Settings.")}><Settings size={15}/>Vault settings</Button>}/><div className="warning-banner"><AlertTriangle size={18}/><span><strong>Privileged trust-plane workspace</strong><small>Re-identification requires an approved purpose, expires automatically, and creates an audit event.</small></span></div><Card className="table-card"><CardHeader title="Active mappings" subtitle="6 tokens across 5 protected sessions" action={<Pill tone="green"><span className="status-dot"/>Encrypted at rest</Pill>}/><div className="filter-bar"><label><Search size={14}/><input placeholder="Search token, type, or session" value={query} onChange={e=>setQuery(e.target.value)}/></label><Button size="sm" onClick={()=>notify("Vault synchronized.")}>Refresh</Button></div><div className="table-scroll"><table><thead><tr><th>Token</th><th>Entity type</th><th>Session</th><th>Created</th><th>Expires</th><th>Last access</th><th/></tr></thead><tbody>{visible.map((t,i)=><tr key={t[0]}><td><code>{t[0]}</code></td><td>{t[1]}</td><td>{t[2]}</td><td className="muted">{t[3]}</td><td><Pill tone={t[4]==="Revoked"?"red":i>2?"amber":"green"}>{t[4]}</Pill></td><td>{t[5]}</td><td><Button size="sm" onClick={()=>setSelected(t[0])}><Eye size={13}/>Request</Button></td></tr>)}</tbody></table></div></Card>
    {selected&&<div className="modal-backdrop" onMouseDown={e=>{if(e.target===e.currentTarget)setSelected(null)}}><section className="modal"><header><span><h2>Request access to {selected}</h2><p>Privileged re-identification · local token vault</p></span><button onClick={()=>setSelected(null)}><X size={18}/></button></header><div className="modal-body"><div className="modal-warning"><LockKeyhole size={16}/>Resolved values are never sent to the AI model. Access expires after five minutes.</div><label><span>Approved purpose</span><select value={purpose} onChange={e=>setPurpose(e.target.value)}><option value="">Select a purpose…</option><option>Customer record correction</option><option>Clinical note finalization</option><option>Privacy investigation</option></select></label><label><span>Ticket or session reference</span><input placeholder="e.g. INC-1042"/></label></div><footer><Button onClick={()=>setSelected(null)}>Cancel</Button><Button variant="primary" onClick={()=>{if(!purpose){notify("Select an approved purpose.");return}setSelected(null);notify("Access approved for five minutes and written to the audit trail.")}}><KeyRound size={14}/>Submit request</Button></footer></section></div>}
  </div>
}
