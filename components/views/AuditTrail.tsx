"use client";

import { useMemo, useState } from "react";
import { CheckCircle2, Download, Search, ShieldCheck, SlidersHorizontal, XCircle } from "lucide-react";
import { Button, Card, CardHeader, PageIntro, Pill } from "../ui";

const events=[
  ["Policy applied","Finance · PCI v12","Edge gateway","ses_8F2A","Today 12:44","Allowed","9fd3…a21c"],
  ["Protected AI request","Safe payload · Local Ollama","Service account","req_81C9","Today 12:44","Attested","bb42…19f0"],
  ["Re-identification denied","Purpose field incomplete","Jordan Lee","tok_6B90","Today 11:28","Blocked","187b…c42d"],
  ["Policy updated","Account threshold 0.92 → 0.95","Maya Patel","policy_v12","Today 10:16","Approved","67cc…a922"],
  ["Destination write-back","CRM case created","CRM connector","case_2D71","Yesterday 17:03","Success","af51…771e"],
];
export function AuditTrail({notify}:{notify:(m:string)=>void}){
  const [query,setQuery]=useState(""); const visible=useMemo(()=>events.filter(e=>e.join(" ").toLowerCase().includes(query.toLowerCase())),[query]);
  function exportCsv(){const csv=["Event,Detail,Actor,Target,Time,Result,Hash",...events.map(e=>e.map(v=>`\"${v}\"`).join(","))].join("\n");const a=document.createElement("a");a.href=URL.createObjectURL(new Blob([csv],{type:"text/csv"}));a.download="airshield-audit.csv";a.click();notify("Audit CSV exported.")}
  return <div className="view"><PageIntro title="Evidence, not promises" description="Every policy decision, identity binding, AI route, and privileged action in a tamper-evident record." actions={<><Button onClick={()=>notify("Hash chain verified: no breaks found.")}><ShieldCheck size={15}/>Verify chain</Button><Button variant="primary" onClick={exportCsv}><Download size={15}/>Export CSV</Button></>}/><Card className="table-card"><CardHeader title="Audit events" subtitle="Last demo hash-chain verification · 2 minutes ago" action={<Pill tone="green"><span className="status-dot"/>Chain intact</Pill>}/><div className="filter-bar"><label><Search size={14}/><input value={query} onChange={e=>setQuery(e.target.value)} placeholder="Search event, actor, or target"/></label><select><option>All results</option><option>Allowed</option><option>Blocked</option></select><select><option>Last 24 hours</option><option>Last 7 days</option></select></div><div className="table-scroll"><table><thead><tr><th>Event</th><th>Actor</th><th>Target</th><th>Time</th><th>Result</th><th>Event hash</th></tr></thead><tbody>{visible.map((e,i)=><tr key={e[0]}><td><span className="audit-event"><i className={e[5]==="Blocked"?"danger":e[5]==="Approved"?"warning":"success"}>{e[5]==="Blocked"?<XCircle size={14}/>:e[5]==="Approved"?<SlidersHorizontal size={14}/>:<CheckCircle2 size={14}/>}</i><span><strong>{e[0]}</strong><small>{e[1]}</small></span></span></td><td>{e[2]}</td><td><code>{e[3]}</code></td><td className="muted">{e[4]}</td><td><Pill tone={e[5]==="Blocked"?"red":e[5]==="Approved"?"amber":"green"}>{e[5]}</Pill></td><td className="hash">{e[6]}</td></tr>)}</tbody></table></div></Card></div>
}
