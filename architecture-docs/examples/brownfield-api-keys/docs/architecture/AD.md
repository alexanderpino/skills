---
id: AD
title: LinkShort — Architecture Description
status: current
version: 1.0.0
level: software
updated: 2026-06-20
entity-of-interest: LinkShort URL-shortener API
conforms-to:
  - ISO/IEC/IEEE 42010:2022
  - ISO/IEC 25010:2023
  - ISO/IEC/IEEE 29148:2018
authors: [team-platform]
---

# Architecture Description — LinkShort

> ISO/IEC/IEEE 42010:2022 conformant container. Detailed content lives in the PRD/HLD/SD/ADRs;
> this AD supplies the required structure. Audited by `conformance-checklist.md`.

## 1. AD identification & overview
| Field | Value |
|---|---|
| Entity of Interest | LinkShort URL-shortener API (existing Flask service) |
| Purpose & scope | Document the service and the self-service API-keys epic (EP-001) |
| Version / date / status | 1.0.0 · 2026-06-20 · current |
| Related documents | [PRD](./PRD.md) · [HLD](./software/HLD.md) · [SD](./software/SD-api-keys.md) · [decisions](./decisions/README.md) |

## 2. Stakeholders
| ID | Stakeholder | Role | Key concerns |
|----|-------------|------|--------------|
| SH.01 | External integrator | Calls the API programmatically | CN.01 |
| SH.02 | Platform team | Operates & secures the API | CN.02, CN.03 |

## 3. Concerns
| ID | Concern | Stakeholders | Framed by viewpoint(s) | Related drivers |
|----|---------|--------------|------------------------|-----------------|
| CN.01 | How do I authenticate to the API? | SH.01 | VP-CTX | F.01 |
| CN.02 | Are keys safe if the DB leaks? | SH.02 | VP-QUAL | Q.01 |
| CN.03 | How is key management structured? | SH.02 | VP-FUNC | F.01, F.02 |

## 5. Viewpoint catalogue
| Viewpoint ID | Name | Concerns framed | Model kinds | Governs view(s) |
|---|---|---|---|---|
| VP-CTX | Context | system scope, external actors | C4 Context | V-CTX |
| VP-FUNC | Functional | structure, responsibilities | C4 Container/Component | V-CON, V-COM-keys |
| VP-QUAL | Quality | quality requirements & trade-offs | ISO 25010 QA scenarios | V-QUAL |
| VP-DEC | Decision | rationale, alternatives | ADR (Nygård/MADR) | V-DEC |

## 6. Views
| View ID | Governing viewpoint | Concerns addressed | Realized in |
|---|---|---|---|
| V-CTX | VP-CTX | CN.01 | HLD §2 |
| V-CON | VP-FUNC | CN.03 | HLD §3 |
| V-COM-keys | VP-FUNC | CN.03 | SD-api-keys §2 |
| V-QUAL | VP-QUAL | CN.02 | PRD §5 |
| V-DEC | VP-DEC | CN.02 | decisions/ |

## 7. Correspondences & consistency
**Correspondence rules:**
- CR.01: Every concern in §3 is framed by ≥ 1 viewpoint in §5.
- CR.02: Every view in §6 is governed by exactly one viewpoint in §5.
- CR.03: A container in the HLD appears in the matching SD component view.

**Known inconsistencies:** none.

## 8. Architecture decisions & rationale
Recorded as ADRs in [`decisions/`](./decisions/README.md). Key decision: `ADR-0001`
(store only salted hashes of API keys).
