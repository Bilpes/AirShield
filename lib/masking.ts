import { createHash, randomBytes } from "node:crypto";
import type { DetectedEntity, ProtectionResult } from "./types";

type Rule = { type: string; pattern: RegExp; confidence: number; capture?: number };

const rules: Rule[] = [
  // Context-bearing rules intentionally mask the value, not the label. They
  // cover IDs and phone-like values that are valid application data even when
  // they do not match a country-specific public numbering format.

  // Credit/Debit Card Numbers - various formats (16 digits, 15 digits for Amex, etc.)
  { type: "CARD_NUMBER", pattern: /\b(?:card|card\s+number|cc|credit\s+card|debit\s+card|visa|mastercard|amex|account)\s*(?:is|:|#|-)?\s*([4]\d{3}[\s.-]?\d{4}[\s.-]?\d{4}[\s.-]?\d{4})(?=\s*[,.;]|\s+(?:and|called|phone|mobile|email|from|has|with|shows|balance|cvv|expir|cvc)\b|$)/gi, confidence: 0.99, capture: 1 },
  { type: "CARD_NUMBER", pattern: /\b(?:card|card\s+number|cc|credit\s+card|debit\s+card|account)\s*(?:is|:|#|-)?\s*([5]\d{3}[\s.-]?\d{4}[\s.-]?\d{4}[\s.-]?\d{4})(?=\s*[,.;]|\s+(?:and|called|phone|mobile|email|from|has|with|shows|balance|cvv|expir|cvc)\b|$)/gi, confidence: 0.99, capture: 1 },
  { type: "CARD_NUMBER", pattern: /\b(?:card|card\s+number|cc|credit\s+card|debit\s+card|account)\s*(?:is|:|#|-)?\s*([3][47]\d{2}[\s.-]?\d{6}[\s.-]?\d{5})(?=\s*[,.;]|\s+(?:and|called|phone|mobile|email|from|has|with|shows|balance|cvv|expir|cvc)\b|$)/gi, confidence: 0.99, capture: 1 },
  { type: "CARD_NUMBER", pattern: /\b(?:card|card\s+number|cc|credit\s+card|debit\s+card)\s*(?:is|:|#|-)?\s*(\d{4}[\s.-]?\d{4}[\s.-]?\d{4}[\s.-]?\d{4})(?=\s*[,.;]|\s+(?:and|called|phone|mobile|email|from|has|with|shows|balance|cvv|expir|cvc)\b|$)/gi, confidence: 0.99, capture: 1 },
  { type: "CARD_NUMBER", pattern: /(?<!\d[\s.-])(?:4\d{3}[\s.-]?\d{4}[\s.-]?\d{4}[\s.-]?\d{4}|5[1-5]\d{2}[\s.-]?\d{4}[\s.-]?\d{4}[\s.-]?\d{4}|3[47]\d{2}[\s.-]?\d{6}[\s.-]?\d{5}|6(?:011|5\d{2})[\s.-]?\d{4}[\s.-]?\d{4}[\s.-]?\d{4})(?![.\d])/g, confidence: 0.98 },

  // Financial - Balance, amounts, monetary values
  { type: "BALANCE", pattern: /\b(?:balance|available\s+balance|account\s+balance|current\s+balance|available\s+credit|credit\s+limit)\s*(?:is|:|of)?\s*([\u20b9$\u20ac\u00a3]?\s*[\d,]+\.?\d{0,2})\b/gi, confidence: 0.97, capture: 1 },
  { type: "BALANCE", pattern: /\b(?:balance\s+is|balance\s+of|balance\s+at)\s+([\u20b9$\u20ac\u00a3]?\s*[\d,]+\.?\d{0,2})/gi, confidence: 0.96, capture: 1 },
  { type: "BALANCE", pattern: /\b(?:has|shows|of|with)\s+([\u20b9$\u20ac\u00a3]?\s*[\d,]+\.?\d{0,2})\s*(?:rupees|dollars|euros|rs\.|usd|eur|inr)?\b/gi, confidence: 0.85, capture: 1 },
  { type: "TRANSFER_AMOUNT", pattern: /\b(?:transfer(?:ed|ring)?\s+of|amount\s+(?:of|is)?|debit(?:ed)?\s+of|credit(?:ed)?\s+of)\s*([\u20b9$\u20ac\u00a3]?\s*[\d,]+\.?\d{0,2})/gi, confidence: 0.96, capture: 1 },
  { type: "TRANSFER_AMOUNT", pattern: /\b(?:for|of)\s*([\u20b9$\u20ac\u00a3]?\s*[\d,]+\.?\d{0,2})\s*(?:rupees|dollars|euros|rs\.|usd|eur|inr)?/gi, confidence: 0.80, capture: 1 },
  { type: "MONETARY_VALUE", pattern: /\b([\u20b9$\u20ac\u00a3]\s*[\d,]+\.?\d{0,2})\b/g, confidence: 0.82 },

  // Bank Account Numbers
  { type: "ACCOUNT_NUMBER", pattern: /\b(?:account|acct|a\/c)\s*(?:number|no\.?|id|#|-)?\s*:?\s*([A-Z0-9](?:[A-Z0-9 -]{4,22}[A-Z0-9]))(?=\s*[,.;]|\s+(?:and|called|phone|mobile|email|from|shows|was|has|with|balance)\b|$)/gi, confidence: 0.98, capture: 1 },
  { type: "ACCOUNT_NUMBER", pattern: /\b(?:bank\s+account|bank\s+a\/c|ifsc)\s*(?:number|no\.?|id|#|-)?\s*:?\s*([A-Z0-9]{4,20})(?=\s*[,.;]|\s+|\b|$)/gi, confidence: 0.97, capture: 1 },

  // CVV/CVC/Expiry
  { type: "CVV", pattern: /\b(?:cvv|cvc|security\s+code|card\s+verification)\s*(?:is|:|#|-)?\s*(\d{3,4})(?=\s*[,.;]|\s+|\b|$)/gi, confidence: 0.99, capture: 1 },
  { type: "CARD_EXPIRY", pattern: /\b(?:expir(?:y|ation)|valid\s+thru|valid\s+until)\s*(?:is|:)?\s*(\d{2}[/-]\d{2,4}|\d{4})(?=\s*[,.;]|\s+|\b|$)/gi, confidence: 0.99, capture: 1 },

  // Password/PIN
  { type: "PASSWORD", pattern: /\b(?:password|passcode|passwd|pwd|pin)\s*(?:is|:)?\s*([^\s,;]{4,32})(?=\s*[,.;]|\s+|\b|$)/gi, confidence: 0.95, capture: 1 },

  // SSN/Social Security Numbers
  { type: "SSN", pattern: /\b(?:ssn|social\s+security|social\s+security\s+number)\s*(?:is|:|#|-)?\s*(\d{3}[-\s]?\d{2}[-\s]?\d{4})(?=\s*[,.;]|\s+|\b|$)/gi, confidence: 0.99, capture: 1 },
  { type: "SSN", pattern: /(?<!\d)(?:\d{3}[-\s]?\d{2}[-\s]?\d{4})(?!\d)/g, confidence: 0.75 },

  // OTP/One-time passwords
  { type: "OTP", pattern: /\b(?:otp|one[- ]?time\s+password|verification\s+code)\s*(?:is|:)?\s*(\d{4,8})(?=\s*[,.;]|\s+|\b|$)/gi, confidence: 0.98, capture: 1 },

  // Existing rules
  { type: "PERSON", pattern: /\b(?:patient|customer|member|caller|client)\s+(?:is\s+|named\s+)?([A-Z][A-Za-z'\u2019.-]*(?:\s+[A-Z][A-Za-z'\u2019.-]*){0,2})(?=\s*[,.;:]|\s+(?:with|account|called|phone|mobile|email)\b|$)/gi, confidence: 0.92, capture: 1 },
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
  { type: "PERSON", pattern: /\b(?:Patient\s+|Customer\s+|I\s+am\s+|I['\u2019]m\s+|name is\s+)([A-Z][a-z]+\s+[A-Z][a-z]+)\b/g, confidence: 0.84, capture: 1 },
  { type: "ADDRESS", pattern: /\b\d{1,5}\s+[A-Z][A-Za-z ]+(?:Road|Rd|Street|St|Avenue|Ave|Lane|Ln|Drive|Dr)(?:,\s*[A-Z][A-Za-z]+)?\b/g, confidence: 0.88 },

  // Vehicle registration numbers
  { type: "VEHICLE_REG", pattern: /\b(?:vehicle|car|bike|registration|reg)\s*(?:number|no\.?|id|#|-)?\s*:?\s*([A-Z]{2}\s?[0-9]{1,2}\s?[A-Z]{0,3}\s?[0-9]{4})\b/gi, confidence: 0.96, capture: 1 },
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
