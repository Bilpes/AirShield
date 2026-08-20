# DPIA and control-mapping starter

This is an engineering starter, not legal advice or a completed DPIA. The customer/controller must document its roles, purposes, lawful bases, national Nordic implementation rules, data-subject expectations, transfers, retention, and residual risk. Applicability depends on country, sector, deployment, and customer role.

## Processing inventory

| Data | Location and purpose | Default persistence |
|---|---|---|
| Raw audio | Private edge memory for ASR/diarization | None by AirShield; customer-configured diagnostic capture must be separately approved |
| Raw transcript | Local authorized UI/bounded edge memory | None in control-plane database/evidence |
| Protected transcript | Local UI and approved AI route | Caller/destination controlled; receipt stores only SHA-256 digest |
| Token mapping | Tenant-scoped PostgreSQL | AES-GCM ciphertext + wrapped per-record DEK until policy expiry/deletion |
| Identity binding | Tenant-scoped PostgreSQL | Keyed subject digest, track, assurance/source, optional consent reference |
| Evidence | Tenant chain + immutable export | Metadata only; default engineering setting seven years, subject to schedule review |
| Workload identity | In-memory verified JWT claims | Not persisted as raw token; actor represented by keyed digest in evidence |

## Regulation/control map

| Requirement area | Engineering control/evidence | Customer actions / gaps |
|---|---|---|
| GDPR Arts. 5, 6, 9 | Data minimization; protected egress; sector policies; no default raw persistence | Determine purpose/lawful basis and Art. 9 condition; notices; necessity/proportionality; processor terms |
| GDPR Arts. 25, 32 | Fail-closed design, tenant isolation, encryption, workload identity, private deployment, tests | Risk assessment, TOM approval, access review, vulnerability/penetration tests, incident process |
| GDPR Arts. 30, 35 | Data-flow inventory, policy/evidence metadata, DPIA starter | Complete ROPA/DPIA with DPO and local counsel; consult authority if high residual risk remains |
| GDPR Arts. 15–22, 17 | Searchable host references, retention and session-data deletion endpoint | Validate identity and legal exceptions; coordinate copies in AI destinations, logs, exports, and backups |
| GDPR Chapter V | Azure/private or customer Kubernetes placement; destination allowlist | SCC/adequacy/transfer assessment and subprocessors where data crosses regions |
| Nordic national rules | Country/sector tags can be added to versioned policy | Counsel must map Denmark, Finland, Iceland, Norway, Sweden and sector-specific implementation; do not treat “Nordic” as one law |
| HIPAA Privacy/Security/Breach Rules | PHI policy, minimum egress, access control, encryption, audit evidence | Confirm covered-entity/business-associate role, BAA, risk analysis, policies, contingency plan, breach assessment |
| PCI DSS 4.0.1 | PAN/account detection, tokenization, destination controls, dual control, logging restrictions | Acquirer/QSA determines scope and validation. Never store sensitive authentication data after authorization; segmentation and assessor testing remain required |
| NIS2 | Private architecture, incident/evidence readiness, supply-chain and resilience controls | Determine entity classification and national transposition; governance and reporting are organizational |
| DORA | ICT risk/evidence, private deployment, resilience and supplier controls | Financial entity must integrate testing, incident reporting, register of information, and third-party oversight |
| EHDS | Health-data minimization, access/control evidence, private EU architecture | Determine phased applicability, EHR-system role, interoperability/conformity, access and secondary-use requirements |
| EU AI Act | Model inventory, intended use, quality gates, human review and logs | Classify provider/deployer role and use case; complete required risk, transparency, oversight, monitoring and conformity work where applicable |

## DPIA questions that must be answered before production

- Which speakers expect processing, and how is notice/consent handled where required?
- Can the objective be achieved with fewer identifiers, no reidentification, or shorter mapping lifetime?
- Who can view the raw pane, bind identity, approve reidentification, delete data, alter policy, or export evidence?
- What happens to protected text at each AI destination, and can a model infer an identity from context?
- What are the tested false-negative rates for every material population and acoustic condition?
- How are backup expiry, legal holds, immutable evidence, key versions, and deletion requests reconciled?
- Which subprocessors, regions, remote support paths, and transfer mechanisms exist?
- What residual risks remain to patients, callers, employees, customers, and bystanders?

## Important limitation

Neither this code, a cloud service feature, nor an AI-generated document makes a deployment GDPR-, HIPAA-, PCI-, NIS2-, DORA-, EHDS-, or AI-Act compliant or certified. Independent legal, privacy, security, model, penetration, and applicable assessor review remains required.
