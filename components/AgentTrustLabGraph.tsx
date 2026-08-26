"use client";

import type { PGEdge, PGNode } from "@/lib/purpose-graph";
import type { StoreSnapshot } from "@/lib/purpose-graph-sim";

// Fixed, readable layout coordinates (viewBox 0 0 660 470).
const POS: Record<string, { x: number; y: number }> = {
  n_consent: { x: 70, y: 250 },
  n_user: { x: 70, y: 120 },
  n_intent: { x: 205, y: 130 },
  n_agent: { x: 345, y: 120 },
  n_source: { x: 205, y: 300 },
  n_inject: { x: 205, y: 385 },
  n_memwrite: { x: 85, y: 385 },
  n_tool_refund: { x: 345, y: 300 },
  n_tool_transfer: { x: 345, y: 385 },
  n_dest_orig: { x: 520, y: 300 },
  n_dest_external: { x: 520, y: 385 },
  n_approval: { x: 205, y: 220 },
  n_credential: { x: 345, y: 220 },
  n_receipt: { x: 520, y: 120 },
};

const KIND_COLOR: Record<PGNode["kind"], string> = {
  user: "#0bae97",
  intent: "#7757c8",
  agent: "#3974d9",
  assistant: "#3974d9",
  source: "#c98a1b",
  memory: "#34505a",
  tool: "#0b8c9b",
  destination: "#b43b43",
  approval: "#7757c8",
  credential: "#0bae97",
  receipt: "#34505a",
  consent: "#0bae97",
};

const STATUS_COLOR: Record<PGNode["status"], string> = {
  active: "var(--mint-500)",
  pending: "var(--ink-400)",
  quarantined: "var(--amber-500)",
  revoked: "var(--red-500)",
  voided: "var(--red-500)",
  executed: "var(--mint-500)",
  blocked: "var(--red-500)",
  consumed: "var(--ink-400)",
};

const EDGE_COLOR: Record<PGEdge["status"], string> = {
  open: "#b8cbd0",
  revoked: "#df5960",
  quarantined: "#efa821",
  voided: "#df5960",
  confirmed: "#31c5ad",
};

function nodeRadius(kind: PGNode["kind"]): number {
  switch (kind) {
    case "user":
    case "agent":
    case "destination":
    case "intent":
      return 26;
    default:
      return 21;
  }
}

function glyph(kind: PGNode["kind"]): string {
  switch (kind) {
    case "user":
      return "U";
    case "consent":
      return "C";
    case "intent":
      return "I";
    case "agent":
      return "A";
    case "source":
      return "S";
    case "memory":
      return "M";
    case "tool":
      return "T";
    case "destination":
      return "D";
    case "approval":
      return "L";
    case "credential":
      return "K";
    case "receipt":
      return "R";
    default:
      return "?";
  }
}

export function AgentTrustLabGraph({ snapshot }: { snapshot: StoreSnapshot }) {
  const nodes: PGNode[] = snapshot.nodes;
  const nodeById = new Map(nodes.map((node) => [node.id, node]));
  const edges: PGEdge[] = snapshot.edges;

  return (
    <div className="attl-graph-wrap">
      <svg viewBox="0 0 660 470" role="img" aria-label="Live PurposeGraph trust graph" className="attl-graph">
        <defs>
          <marker id="attl-arrow-open" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
            <path d="M 0 0 L 10 5 L 0 10 z" fill="#b8cbd0" />
          </marker>
          <marker id="attl-arrow-revoked" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
            <path d="M 0 0 L 10 5 L 0 10 z" fill="#df5960" />
          </marker>
          <marker id="attl-arrow-confirmed" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
            <path d="M 0 0 L 10 5 L 0 10 z" fill="#31c5ad" />
          </marker>
        </defs>

        {edges.map((edge, index) => {
          const a = POS[edge.from];
          const b = POS[edge.to];
          if (!a || !b) return null;
          const mx = (a.x + b.x) / 2;
          const my = (a.y + b.y) / 2;
          const color = EDGE_COLOR[edge.status];
          const marker =
            edge.status === "revoked" || edge.status === "voided"
              ? "url(#attl-arrow-revoked)"
              : edge.status === "confirmed"
                ? "url(#attl-arrow-confirmed)"
                : "url(#attl-arrow-open)";
          const dash = edge.status === "revoked" || edge.status === "voided" || edge.status === "quarantined" ? "4 4" : "0";
          return (
            <g key={`${edge.from}-${edge.to}-${index}`}>
              <line x1={a.x} y1={a.y} x2={b.x} y2={b.y} stroke={color} strokeWidth={2} markerEnd={marker} strokeDasharray={dash} opacity={0.9} />
              <text x={mx} y={my - 5} textAnchor="middle" fontSize={7.5} fill={edge.status === "open" ? "#6a828a" : color} className="attl-edge-label">
                {edge.label}
              </text>
            </g>
          );
        })}

        {nodes.map((node) => {
          const pos = POS[node.id];
          if (!pos) return null;
          const r = nodeRadius(node.kind);
          const base = KIND_COLOR[node.kind];
          const status = STATUS_COLOR[node.status];
          const isVoided = node.status === "voided" || node.status === "revoked" || node.status === "blocked" || node.status === "quarantined";
          return (
            <g key={node.id} className="attl-node">
              <circle cx={pos.x} cy={pos.y} r={r - 3} fill={isVoided ? "rgba(223,89,96,.1)" : "rgba(255,255,255,.9)"} stroke={status} strokeWidth={2.2} />
              {node.status === "revoked" || node.status === "voided" ? (
                <line x1={pos.x - r * 0.55} y1={pos.y - r * 0.55} x2={pos.x + r * 0.55} y2={pos.y + r * 0.55} stroke="#df5960" strokeWidth={2.2} />
              ) : null}
              {node.status === "blocked" ? (
                <line x1={pos.x - r * 0.55} y1={pos.y - r * 0.55} x2={pos.x + r * 0.55} y2={pos.y + r * 0.55} stroke="#df5960" strokeWidth={2.2} />
              ) : null}
              {node.risk === "high" && node.status !== "blocked" ? (
                <circle cx={pos.x + r - 2} cy={pos.y - r + 2} r={4.5} fill="#df5960" />
              ) : null}
              <text x={pos.x} y={pos.y + 3.5} textAnchor="middle" fontSize={10} fontWeight={800} fill={base}>
                {glyph(node.kind)}
              </text>
              <text x={pos.x} y={pos.y + r + 13} textAnchor="middle" fontSize={8.5} fontWeight={700} fill="#2b3f47" className="attl-node-label">
                {node.label}
              </text>
              {node.status !== "active" && node.status !== "pending" ? (
                <text x={pos.x} y={pos.y + r + 25} textAnchor="middle" fontSize={7} fontWeight={800} fill={status} className="attl-node-status">
                  {node.status.toUpperCase()}
                </text>
              ) : null}
            </g>
          );
        })}
      </svg>
      <div className="attl-legend">
        <span><i className="dot" style={{ background: "#0bae97" }} />Human / consent</span>
        <span><i className="dot" style={{ background: "#3974d9" }} />Agent / tool</span>
        <span><i className="dot" style={{ background: "#c98a1b" }} />Source data</span>
        <span><i className="dot" style={{ background: "#b43b43" }} />Destination boundary</span>
        <span><i className="dot" style={{ background: "#df5960" }} />Revoked / blocked</span>
      </div>
    </div>
  );
}
