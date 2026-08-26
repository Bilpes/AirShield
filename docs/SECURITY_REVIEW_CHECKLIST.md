# Security and privacy release checklist

A production gate is **failed** until every applicable item has linked evidence and an accountable approver.

- [ ] Threat model reviewed after final data-flow and deployment changes
- [ ] DPIA/ROPA, lawful basis, notices, contracts/BAA/DPA, transfer and national-sector analysis approved
- [ ] Entra claims or exact portable subject bindings tested; conflicting tenant, wildcard subject, excessive scope, stale JWKS, and dev-auth cases denied
- [ ] Host cookie/bearer authentication, exact Origin/tenant, signed track claim, protocol state, direct-edge denial, secret rotation, and aggregate gateway limits tested
- [ ] Tenant A/B adversarial suite, object-ID enumeration, and database-isolation review passed
- [ ] Azure Key Vault/OpenBao permissions least-privilege; wrap/sign keys separate; rotations and outages tested
- [ ] No raw audio/text/identity/token appears in logs, metrics, traces, receipts, crash dumps, support tooling, or analytics
- [ ] Model files and manifest hash verified at startup; registry signatures/provenance and representative red-team slice gates passed
- [ ] `block`/`review`/dependency failure cannot reach an AI destination
- [ ] Destination allowlists and private egress verified at app, gateway, and network layers
- [ ] Reidentification requester/approver separation, PAM, ticket validation, one-time access, expiry, and alerting tested
- [ ] Retention, deletion, backup expiry, legal hold, key-version retirement, and restore behavior approved
- [ ] Evidence export is immutable, independently verified, monitored, and protected by separate administration
- [ ] Images are digest pinned, signed, scanned; admission controls reject placeholders/unsigned artifacts
- [ ] Kubernetes restricted policy, read-only roots, non-root IDs, quotas, PDB/HPA, NetworkPolicy and secret CSI tested
- [ ] End-to-end web/gateway/edge/control TLS/private CAs and PostgreSQL `verify-full` are tested, including certificate rollover and expiry
- [ ] Azure private DNS/endpoints, separated vault/managed identities, PostgreSQL HA/PITR and diagnostic export tested
- [ ] Dependency/model/image SBOM and licenses reviewed; critical vulnerabilities resolved or explicitly accepted
- [ ] SAST, DAST, API fuzzing, penetration testing, load/soak, chaos/failover, and incident exercises complete
- [ ] Independent legal, privacy, security, model, penetration, and applicable PCI/sector assessor conclusions recorded

Do not label AirShield or a customer deployment “certified” solely because this checklist or repository exists.
