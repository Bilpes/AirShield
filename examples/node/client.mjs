// AirShield control-plane client — Node.js 20+
import { randomUUID } from 'node:crypto';

const baseUrl = process.env.AIRSHIELD_URL ?? 'http://127.0.0.1:8080';
const token = process.env.AIRSHIELD_TOKEN ?? 'development-only';

async function post(path, body) {
  const response = await fetch(`${baseUrl}${path}`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!response.ok) throw new Error(`AirShield ${response.status}: ${await response.text()}`);
  return response.json();
}

const session = await post('/v1/sessions', {
  policy: 'saas-copilot-eu-us-v1', language: 'en', ttl_minutes: 60,
});
const result = await post('/v1/protect', {
  session_id: session.session_id,
  text: 'Email mina.hall@orionlabs.com and revoke sk_live_51M3q8x2.',
  policy: 'saas-copilot-eu-us-v1',
  destination: 'enterprise-copilot',
  idempotency_key: randomUUID(),
});
if (result.decision !== 'allow') throw new Error(`Egress denied: ${result.receipt.reason_codes}`);
console.log(result.protected_text, result.receipt.receipt_id);
