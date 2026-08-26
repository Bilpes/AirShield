export type DestinationId = "organization-private" | "regional-ria" | "research-sandbox" | "public-general-ai";

export interface DestinationProfile {
  id: DestinationId;
  label: string;
  description: string;
  trust: "private" | "managed" | "restricted" | "external";
  status: "approved" | "conditional" | "blocked";
  baseRisk: number;
  maximumRisk: number;
}

export interface ContextEntity {
  type?: string;
  token?: string;
}

export interface ContextRiskFactor {
  label: string;
  detail: string;
  points: number;
}

export interface ContextFenceResult {
  score: number;
  band: "low" | "guarded" | "high" | "critical";
  disposition: "allow" | "review" | "block";
  factors: ContextRiskFactor[];
  destination: DestinationProfile;
  explanation: string;
}

export const DESTINATION_PROFILES: DestinationProfile[] = [
  {
    id: "organization-private",
    label: "Organization private AI",
    description: "Customer-controlled model and private connector network",
    trust: "private",
    status: "approved",
    baseRisk: 5,
    maximumRisk: 64,
  },
  {
    id: "regional-ria",
    label: "Regional managed RIA",
    description: "Contracted regional service with approved data boundary",
    trust: "managed",
    status: "approved",
    baseRisk: 17,
    maximumRisk: 54,
  },
  {
    id: "research-sandbox",
    label: "Research sandbox",
    description: "Restricted de-identified evaluation environment",
    trust: "restricted",
    status: "conditional",
    baseRisk: 29,
    maximumRisk: 39,
  },
  {
    id: "public-general-ai",
    label: "Public general AI",
    description: "Unapproved external destination with no trusted connector",
    trust: "external",
    status: "blocked",
    baseRisk: 58,
    maximumRisk: 0,
  },
];

export function destinationProfile(id: string): DestinationProfile | undefined {
  return DESTINATION_PROFILES.find((destination) => destination.id === id);
}

export function evaluateContextFence(
  protectedText: string,
  entities: ContextEntity[],
  destinationId: DestinationId,
): ContextFenceResult {
  const destination = destinationProfile(destinationId) ?? DESTINATION_PROFILES[3];
  const factors: ContextRiskFactor[] = [];
  let score = destination.baseRisk;

  factors.push({
    label: "Destination exposure",
    detail: `${destination.label} contributes a ${destination.baseRisk}-point trust-boundary baseline.`,
    points: destination.baseRisk,
  });

  const tokens = protectedText.match(/\[[A-Z][A-Z0-9_]{1,48}\]/g) ?? [];
  if (tokens.length) {
    const points = Math.min(18, tokens.length * 3);
    score += points;
    factors.push({
      label: "Stable token linkage",
      detail: `${tokens.length} protected references could become identifying when combined across turns.`,
      points,
    });
  }

  const types = new Set(entities.map((entity) => entity.type).filter(Boolean));
  if (types.size >= 2) {
    const points = Math.min(16, (types.size - 1) * 4);
    score += points;
    factors.push({
      label: "Entity combination",
      detail: `${types.size} entity classes create cumulative linkage risk even though each value is protected.`,
      points,
    });
  }

  if (/\b(?:diagnos|medication|symptom|claim|account|transaction|incident|employee|patient|beneficiary)\w*\b/i.test(protectedText)) {
    score += 7;
    factors.push({
      label: "Sensitive semantic context",
      detail: "The remaining meaning reveals a regulated or high-impact business context.",
      points: 7,
    });
  }

  if (/\b(?:today|tomorrow|yesterday|\d{1,2}:\d{2}|\d{1,3}(?:\.\d+)?\s?(?:mg|degrees?|years?))\b/i.test(protectedText)) {
    score += 6;
    factors.push({
      label: "Quasi-identifier detail",
      detail: "Timing, age, dose, measurement, or scheduling detail can narrow a person's identity.",
      points: 6,
    });
  }

  if (protectedText.length > 320) {
    const points = protectedText.length > 700 ? 12 : 7;
    score += points;
    factors.push({
      label: "Context accumulation",
      detail: "Longer protected conversations can reveal identity through a mosaic of otherwise safe facts.",
      points,
    });
  }

  if (/\b(?:daughter|son|manager|witness|clinician|supervisor|bystander)\b/i.test(protectedText)) {
    score += 5;
    factors.push({
      label: "Relationship graph",
      detail: "Roles and relationships can reconnect protected participants across records.",
      points: 5,
    });
  }

  score = Math.max(0, Math.min(100, score));
  const band = score >= 80 ? "critical" : score >= 60 ? "high" : score >= 35 ? "guarded" : "low";
  const disposition = destination.status === "blocked" || score >= 80
    ? "block"
    : destination.status === "conditional" || score > destination.maximumRisk
      ? "review"
      : "allow";
  const explanation = disposition === "allow"
    ? "Context is within this destination's cumulative-risk threshold."
    : disposition === "review"
      ? "Individually protected values combine into context that requires a lower-risk destination or human approval."
      : "Destination policy or cumulative context risk prevents egress.";

  return { score, band, disposition, factors, destination, explanation };
}
