"use client";

import type { ReactNode } from "react";
import type { LucideIcon } from "lucide-react";
import { Activity, Bell, Beaker, Blocks, ChevronDown, FileClock, GitBranch, Grid2X2, KeyRound, Menu, Mic2, PlugZap, Search, Settings, ShieldCheck, SlidersHorizontal, Stamp, X } from "lucide-react";
import type { ViewId } from "@/lib/types";
import { NAV_META } from "@/lib/demo-data";

const nav: { id: ViewId; label: string; icon: LucideIcon; section?: string }[] = [
  { id: "overview", label: "Overview", icon: Grid2X2, section: "Workspace" },
  { id: "live", label: "Live Shield", icon: Mic2 },
  { id: "egress", label: "EgressSeal™", icon: Stamp },
  { id: "trustlab", label: "Agent Trust Lab", icon: GitBranch, section: "Agent trust" },
  { id: "lab", label: "Performance Lab", icon: Beaker },
  { id: "policies", label: "Policy Studio", icon: SlidersHorizontal },
  { id: "vault", label: "Token Vault", icon: KeyRound },
  { id: "audit", label: "Audit Trail", icon: FileClock },
  { id: "connections", label: "Connections", icon: PlugZap, section: "Platform" },
  { id: "settings", label: "Settings", icon: Settings },
];

export function AppShell({ view, setView, sidebarOpen, setSidebarOpen, children }: { view: ViewId; setView: (v: ViewId) => void; sidebarOpen: boolean; setSidebarOpen: (v: boolean) => void; children: ReactNode }) {
  const [eyebrow, title] = NAV_META[view];
  const navigate = (id: ViewId) => { setView(id); setSidebarOpen(false); };
  return <div className="app-shell">
    <aside className={`sidebar ${sidebarOpen ? "open" : ""}`} aria-label="Primary navigation">
      <div className="brand"><span className="brand-mark"><ShieldCheck size={28}/></span><span><strong>AirShield</strong><small>Control plane</small></span><button className="sidebar-close" onClick={()=>setSidebarOpen(false)} aria-label="Close navigation"><X size={18}/></button></div>
      <nav className="sidebar-nav">
        {nav.map((item, index) => <div key={item.id}>{item.section && <p className={`nav-label ${index ? "spaced" : ""}`}>{item.section}</p>}<button className={`nav-item ${view === item.id ? "active" : ""}`} onClick={()=>navigate(item.id)}><item.icon size={17}/><span>{item.label}</span>{item.id === "live" && <i className="live-dot"/>}</button></div>)}
      </nav>
      <div className="sidebar-bottom">
        <div className="edge-card"><div><span className="status-dot"/><strong>Local models ready</strong><small>English only</small></div><div className="edge-meter"><i/></div><span>Whisper · pyannote · Presidio</span></div>
        <button className="profile" onClick={()=>navigate("settings")}><span className="avatar">MP</span><span><strong>Maya Patel</strong><small>Security admin</small></span><ChevronDown size={14}/></button>
      </div>
    </aside>
    {sidebarOpen && <button className="sidebar-scrim" aria-label="Close navigation" onClick={()=>setSidebarOpen(false)}/>}
    <section className="main-column">
      <header className="topbar"><div className="topbar-left"><button className="icon-button menu-button" onClick={()=>setSidebarOpen(true)} aria-label="Open navigation"><Menu size={18}/></button><div className="page-heading"><span>{eyebrow}</span><h1>{title}</h1></div></div><div className="topbar-actions"><span className="edge-chip"><span className="status-dot"/><span>Self-hosted edge</span><ChevronDown size={13}/></span><button className="search-button"><Search size={15}/><span>Find anything</span><kbd>⌘K</kbd></button><button className="icon-button notification" aria-label="Notifications"><Bell size={17}/><i/></button></div></header>
      <main>{children}</main>
      <nav className="mobile-nav" aria-label="Mobile navigation">{[
        {id:"overview" as ViewId,label:"Home",icon:Grid2X2},{id:"live" as ViewId,label:"Shield",icon:Mic2},{id:"egress" as ViewId,label:"Seal",icon:Stamp},{id:"audit" as ViewId,label:"Audit",icon:FileClock}
      ].map(item=><button key={item.id} className={view===item.id?"active":""} onClick={()=>navigate(item.id)}><item.icon size={19}/><small>{item.label}</small></button>)}<button onClick={()=>setSidebarOpen(true)}><Blocks size={19}/><small>More</small></button></nav>
    </section>
  </div>;
}
