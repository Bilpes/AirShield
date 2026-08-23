"use client";

import { useEffect, useState } from "react";
import type { ViewId } from "@/lib/types";
import { AppShell } from "./AppShell";
import { Toast } from "./ui";
import { Overview } from "./views/Overview";
import { LiveShield } from "./views/LiveShield";
import { PolicyStudio } from "./views/PolicyStudio";
import { TokenVault } from "./views/TokenVault";
import { AuditTrail } from "./views/AuditTrail";
import { Connections } from "./views/Connections";
import { PerformanceLab } from "./views/PerformanceLab";
import { SettingsView } from "./views/SettingsView";
import { DoctorBookingBot } from "./DoctorBookingBot";

export function AirShieldApp() {
  const [view, setView] = useState<ViewId>("overview");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [toast, setToast] = useState("");
  useEffect(()=>{ if(!toast) return; const id=setTimeout(()=>setToast(""),3200); return ()=>clearTimeout(id); },[toast]);
  const props = { navigate: setView, notify: setToast };
  return <>
    <AppShell view={view} setView={setView} sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen}>
      {view === "overview" && <Overview {...props}/>}
      {view === "live" && <LiveShield notify={setToast}/>}
      {view === "policies" && <PolicyStudio notify={setToast}/>}
      {view === "vault" && <TokenVault notify={setToast}/>}
      {view === "audit" && <AuditTrail notify={setToast}/>}
      {view === "connections" && <Connections notify={setToast}/>}
      {view === "lab" && <PerformanceLab notify={setToast}/>}
      {view === "settings" && <SettingsView notify={setToast}/>}
      {toast && <Toast message={toast} onClose={()=>setToast("")}/>}
    </AppShell>
    <DoctorBookingBot notify={setToast}/>
  </>;
}
