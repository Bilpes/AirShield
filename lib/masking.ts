import { createHash, randomBytes } from "node:crypto";
import type { DetectedEntity, ProtectionResult } from "./types";

type Rule = { type: string; pattern: RegExp; confidence: number; capture?: number };

const rules: Rule[] = [
  // Context-bearing rules intentionally mask the value, not the label. They
  // cover IDs and phone-like values that are valid application data even when
  // they do not match a country-specific public numbering format.
  { type: "PERSON", pattern: /\b(?:patient|customer|member|caller|client)\s+(?:is\s+|named\s+)?([A-Z][A-Za-z'’.-]*(?:\s+[A-Z][A-Za-z'’.-]*){0,2})(?=\s*[,.;:]|\s+(?:with|account|called|phone|mobile|email)\b|$)/gi, confidence: 0.92, capture: 1 },
  { type: "CARD_OR_ACCOUNT", pattern: /\b(?:account(?:\s+(?:number|no\.?|id))?|acct(?:\s+(?:number|no\.?|id))?|customer\s+id)\s*(?:is|:|#|-)?\s*([A-Z0-9](?:[A-Z0-9 -]{4,22}[A-Z0-9]))(?=\s*[,.;]|\s+(?:and|called|phone|mobile|email|from)\b|$)/gi, confidence: 0.98, capture: 1 },
  { type: "PHONE", pattern: /\b(?:called\s+from|phone|mobile|telephone|tel)\s*(?:is|:|#|-)?\s*(\+?\d(?:[\s().-]*\d){6,14})(?=\s*[,.;]|\s+(?:and|email|account|from)\b|$)/gi, confidence: 0.98, capture: 1 },
  { type: "EMAIL", pattern: /\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b/gi, confidence: 0.99 },
  { type: "SECRET", pattern: /\b(?:sk|pk|api)[_-](?:live|test)?[_-]?[A-Za-z0-9]{8,}\b/gi, confidence: 0.99 },
  { type: "PHONE", pattern: /(?<!\d)(?:\+?91[\s-]?)?[6-9]\d{4}[\s-]?\d{5}(?!\d)|(?<!\d)(?:\+?1[\s-]?)?\(?\d{3}\)?[\s-]\d{3}[\s-]\d{4}(?!\d)/g, confidence: 0.98 },
  { type: "PAN", pattern: /\b[A-Z]{5}\d{4}[A-Z]\b/g, confidence: 0.99 },
  { type: "MRN", pattern: /\b(?:MRN\s*(?:is|:|#)?\s*)?[A-Z]{2,5}-\d{5,10}\b/gi, confidence: 0.97 },
  { type: "POLICY_ID", pattern: /\b[A-Z]{2,5}-(?:[A-Z]{2,5}-)?\d{5,10}\b/g, confidence: 0.94 },
  { type: "DATE_OF_BIRTH", pattern: /\b(?:DOB\s*(?:is|:)?\s*)?(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{1,2}\s+(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{4})\b/gi, confidence: 0.96 },
  { type: "IP_ADDRESS", pattern: /\b(?:\d{1,3}\.){3}\d{1,3}\b/g, confidence: 0.97 },
  { type: "CARD_OR_ACCOUNT", pattern: /(?<!\d)\d{10,19}(?!\d)/g, confidence: 0.9 },
  { type: "PERSON", pattern: /\b(?:Patient\s+|Customer\s+|I\s+am\s+|I['’]m\s+|name is\s+)([A-Z][a-z]+\s+[A-Z][a-z]+)\b/g, confidence: 0.84, capture: 1 },
  { type: "ADDRESS", pattern: /\b\d{1,5}\s+[A-Z][A-Za-z ]+(?:Road|Rd|Street|St|Avenue|Ave|Lane|Ln|Drive|Dr)(?:,\s*[A-Z][A-Za-z]+)?\b/g, confidence: 0.88 },
];

export function protectText(text: string): ProtectionResult {
  const candidates: Omit<DetectedEntity, "token">[] = [];
  for (const rule of rules) {
    const expression = new RegExp(rule.pattern.source, rule.pattern.flags);
    for (const match of text.matchAll(expression)) {
      if (match.index === undefined) continue;
      const raw = rule.capture && match[rule.capture] ? match[rule.capture] : match[0];
      const offset = rule.capture ? match[0].lastIndexOf(raw) : 0;
      const start = match.index + offset;
      candidates.push({ type: rule.type, raw, start, end: start + raw.length, confidence: rule.confidence });
    }
  }
  candidates.sort((a, b) => a.start - b.start || b.end - a.end);
  const entities: DetectedEntity[] = [];
  const counters: Record<string, number> = {};
  let occupiedUntil = -1;
  for (const entity of candidates) {
    if (entity.start < occupiedUntil) continue;
    counters[entity.type] = (counters[entity.type] ?? 0) + 1;
    entities.push({ ...entity, token: `[${entity.type}_${counters[entity.type]}]` });
    occupiedUntil = entity.end;
  }
  let cursor = 0;
  let protectedText = "";
  for (const entity of entities) {
    protectedText += text.slice(cursor, entity.start) + entity.token;
    cursor = entity.end;
  }
  protectedText += text.slice(cursor);
  return {
    protectedText,
    entities,
    decision: "allow",
    receiptId: `rcp_${randomBytes(5).toString("hex")}`,
    contentHash: createHash("sha256").update(protectedText).digest("hex"),
    latencyMs: 1,
  };
}
