export type Industry = "Healthcare" | "Finance" | "Insurance" | "BPO / Contact center" | "SaaS / Copilot";
export type ViewId = "overview" | "live" | "policies" | "vault" | "audit" | "connections" | "lab" | "settings";
export type SpeakerRole = "primary" | "secondary" | "unknown";

export interface Speaker {
  initials: string;
  name: string;
  role: string;
  track: string;
  assurance: string;
  status: "verified" | "claimed" | "unknown";
  color: SpeakerRole;
}

export interface EntityPair {
  raw: string;
  token: string;
  type: string;
}

export interface TranscriptTurn {
  speaker: string;
  role: SpeakerRole;
  time: string;
  raw: string;
  safe: string;
  entities: EntityPair[];
}

export interface IndustryDemo {
  industry: Industry;
  policy: string;
  route: string;
  destination: string;
  speakers: Speaker[];
  transcript: TranscriptTurn[];
}

export interface DetectedEntity {
  type: string;
  raw?: string;
  token: string;
  start: number;
  end: number;
  confidence: number;
}

export interface ProtectionResult {
  protectedText: string;
  entities: DetectedEntity[];
  decision: "allow" | "block" | "review";
  receiptId: string;
  contentHash?: string;
  latencyMs: number;
}
