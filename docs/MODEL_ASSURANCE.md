# Model assurance and release gates

## Production model stack

The intended customer-controlled stack is faster-whisper (English ASR), pyannote.audio or an evaluated alternative (speaker diarization), Presidio orchestration, a pinned spaCy/context model, domain recognizers, and optionally a local Ollama-compatible LLM. A model name in the UI is not an assurance claim. Every artifact must have a version, hash, provenance, license review, vulnerability scan, evaluation record, and rollback target.

## Measurement plan

| Layer | Required slices | Primary measures |
|---|---|---|
| ASR | Nordic-accented and US English; headset/phone/meeting codecs; noise; clinical/financial jargon; numbers; names | WER, entity-weighted WER, numeral error rate, real-time factor, p95/p99 latency |
| Diarization | 1–8 speakers; overlap; interruption; phone/meeting audio; gender/age/accent slices where lawful | DER, JER, speaker-count error, track-switch rate |
| Sensitive-entity detection | Healthcare, Finance, Insurance, BPO, SaaS; Nordic/EU/US identifier formats; ASR errors; Unicode/adversarial forms | Exact/overlap precision and recall by entity, critical false negatives, calibration, abstention rate |
| End-to-end egress | Chunked and final transcripts; each policy/destination; outages | Raw-value egress rate, block/review rate, p95 latency, receipt completeness |

Release-blocking defaults are in `control-plane/evaluation/quality-gates.yaml`: micro recall 0.995, critical-entity recall 0.999, precision 0.95, and zero critical false negatives in the approved release set. Customers may require stricter gates. Tiny synthetic fixtures prove only deterministic regression behavior and explicitly report `production_gate_satisfied: false`.

## Evaluation protocol

1. Define intended use, excluded use, countries, sectors, codecs, environments, and language (English only).
2. Create legally sourced, minimized, access-controlled, representative datasets. Separate train/tune/test and protect the test set from developers.
3. Label with written guidelines and dual adjudication for critical entities. Record inter-annotator agreement.
4. Evaluate raw ASR output—not cleaned reference text—then end-to-end stream chunks.
5. Report aggregate and slice results with confidence intervals; a passing aggregate cannot hide a failed critical slice.
6. Red-team obfuscation, homoglyphs, digit grouping, misspellings, overlapping speech, low volume, background names, and prompt injection.
7. Promote only through signed model/policy manifests. Canary on metadata-only rates; never capture raw production samples by default.
8. Trigger reevaluation on model, recognizer, threshold, policy, audio frontend, runtime, or material population change.

## Artifact manifest and distribution

Preload models onto the read-only `airshield-models` volume; production pods never fetch from a public model hub. Generate `/models/manifest.json` as canonical JSON with `{"format":1,"files":{"relative/path":"lowercase-sha256"}}`, covering every regular file below the configured ASR and, when enabled, diarization directories. Supply the manifest's own SHA-256 through `MODEL_MANIFEST_SHA256`. Edge startup rejects missing files, symlinks, path traversal, an unpinned manifest, incomplete model coverage, or any digest mismatch before loading inference. Store the signed manifest, evaluation report, license/provenance record, malware/vulnerability scan, and promotion approval together in the release registry; the runtime hash check complements rather than replaces signature/admission verification.

## Fail-closed semantics

- Missing/unhealthy contextual detector blocks readiness when configured fail-closed.
- Unsupported policy actions, unapproved destinations, model/KMS errors, and production control-plane absence deny egress.
- Confidence below a critical threshold is `block`; noncritical low-confidence content may be `review` only when policy explicitly permits it.
- `review` is not equivalent to safe. A human decision must occur within the customer trust boundary before reprocessing.

## Drift and incident response

Monitor entity rates, confidence distributions, ASR quality probes, abstentions, latency, and manually adjudicated privacy incidents without raw identifiers in metric labels. Establish thresholds per customer and slice. A confirmed false-negative escape freezes the affected route, preserves metadata evidence, initiates privacy/security response, expands regression fixtures using lawful synthetic or de-identified examples, and requires a new signed evaluation report.
