"use client";

import type { ButtonHTMLAttributes, ReactNode } from "react";
import { CheckCircle2, X } from "lucide-react";

export function Button({ variant = "secondary", size = "md", className = "", ...props }: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "secondary" | "danger" | "ghost"; size?: "sm" | "md" }) {
  return <button className={`button button-${variant} button-${size} ${className}`} {...props} />;
}

export function Pill({ children, tone = "neutral" }: { children: ReactNode; tone?: "neutral" | "green" | "amber" | "red" | "blue" | "violet" }) {
  return <span className={`pill pill-${tone}`}>{children}</span>;
}

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <section className={`card ${className}`}>{children}</section>;
}

export function CardHeader({ title, subtitle, action }: { title: string; subtitle?: string; action?: ReactNode }) {
  return <header className="card-header"><div><h3>{title}</h3>{subtitle && <p>{subtitle}</p>}</div>{action}</header>;
}

export function PageIntro({ title, description, actions }: { title: string; description: string; actions?: ReactNode }) {
  return <div className="page-intro"><div><h2>{title}</h2><p>{description}</p></div>{actions && <div className="page-actions">{actions}</div>}</div>;
}

export function Toast({ message, onClose }: { message: string; onClose: () => void }) {
  return <div className="toast"><CheckCircle2 size={17}/><span>{message}</span><button aria-label="Dismiss" onClick={onClose}><X size={14}/></button></div>;
}

export function highlight(text: string, mode: "raw" | "safe", entities: { raw: string; token: string }[]): ReactNode {
  const pairs = mode === "raw" ? entities.map(e => ({ value: e.raw, cls: "raw-entity" })) : entities.map(e => ({ value: e.token, cls: "safe-token" }));
  if (!pairs.length) return text;
  const escaped = pairs.map(p => p.value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
  const regex = new RegExp(`(${escaped.join("|")})`, "g");
  const map = new Map(pairs.map(p => [p.value, p.cls]));
  return text.split(regex).map((part, i) => map.has(part) ? <mark className={map.get(part)} key={`${part}-${i}`}>{part}</mark> : part);
}
