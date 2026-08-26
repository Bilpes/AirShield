# AirShield hackathon brief

## Pitch

AirShield is a self-hosted, real-time privacy firewall for voice and text AI. It transcribes English speech locally, separates speakers, binds authenticated application identities, masks sensitive values, and sends only protected meaning to any downstream AI.

## Five-minute demo

1. Select Healthcare, Finance, Insurance, BPO/Contact center, or SaaS/Copilot.
2. Start the English voice stream.
3. Show raw speech on the left and protected AI input on the right.
4. Point out Speaker A/B/C and their SSO/OTP/unknown status.
5. Send the right-side transcript to local Ollama and generate a useful summary.
6. Show that names, account numbers, MRNs, phones, secrets, and addresses do not appear in the LLM input.
7. Open the audit receipt and integration screen.

## Why local models

Managed speech APIs charge by audio duration and receive raw audio before AirShield can mask it. The hackathon path uses faster-whisper locally, Presidio locally, and optional pyannote locally. There is no per-hour transcription bill. An optional Ollama model produces summaries without token charges.

## Honest prototype statement

The interface, Next.js APIs, deterministic text protection, microphone capture path, and local-model edge code are implemented. The preview uses synthetic English turns unless the separately installed edge model is configured. Demo accuracy and latency are illustrative; they are not compliance or clinical claims.

## Technology stack

- Next.js 16, React 19, TypeScript
- Responsive CSS, Lucide React
- Next.js Route Handlers
- Python FastAPI WebSocket edge
- faster-whisper `small.en`
- Presidio, spaCy, and custom recognizers
- Optional pyannote.audio
- Optional Ollama
- Docker Compose
- REST, JSON, WebSocket

## Cost message

The software path has no mandatory paid API. Running locally on an existing laptop has approximately zero incremental service cost. A pilot pays for compute, security hardening, model validation, monitoring, storage, and engineering—not speech minutes or LLM tokens if all models remain local.
