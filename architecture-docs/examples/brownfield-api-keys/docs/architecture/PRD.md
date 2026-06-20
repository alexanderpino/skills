---
id: PRD
title: LinkShort — Product Requirements
status: current
level: software
updated: 2026-06-20
owners: [team-platform]
---

# PRD — LinkShort

The *why* and *what* for the **self-service API keys** epic on the existing LinkShort API.
Functional drivers `F.xx` were **ingested from the given functional requirements** (not
re-elicited); the quality driver was promoted from a given non-functional expectation.

## 1. Stakeholders
- **External integrator** — builds against the LinkShort API; needs programmatic auth.
- **Platform team** — operates the API; owns security and rate limits.

## 2. Goals & motivation
Let integrators self-serve credentials (generate/revoke keys) so onboarding needs no manual
steps, while protecting the platform from abuse and credential leakage.

## 3. Business drivers
- **B.01:** Reduce integrator onboarding from days (manual) to minutes (self-service).

## 4. Functional drivers
> Ingested from given requirements FR-1…FR-3. RFC 2119 keywords make obligation exact.

- **F.01:** The system **MUST** let an authenticated integrator generate an API key, returning the key value exactly once.
- **F.02:** The system **MUST** let an integrator revoke one of their API keys, after which it is rejected.
- **F.03:** The system **MUST** rate-limit requests **per API key** independently of other keys.

> Detailed behaviour is specified as user stories (`US-NNN`) under epic **EP-001**, each
> linked to its `F.xx`. See [requirements/](./requirements/).

## 5. Quality drivers — quality attribute scenarios

### Q.01 — API keys unrecoverable from a database leak
| Part | Value |
|---|---|
| **Quality characteristic (ISO 25010)** | security → confidentiality |
| **Source of stimulus** | an attacker with a dump of the keys table |
| **Stimulus** | attempts to recover usable API keys from stored data |
| **Environment** | data-at-rest compromise (leaked backup) |
| **Artifact** | the API-key data store |
| **Response** | stored material cannot be reversed into a usable key |
| **Response measure** | keys stored only as salted SHA-256 hashes; 0 plaintext keys recoverable |
| **Means of verification** | code review + test asserting the store contains no plaintext key |

### Quality / utility tree (prioritisation)
| 25010 characteristic | Refinement | Scenario | Value | Difficulty |
|---|---|---|---|---|
| Security | Confidentiality | Q.01 | H | L |

## 6. Constraints
- **C.01:** Must run within the existing Flask service and PostgreSQL store (no new datastore).

## 7. Driver → decision traceability
Decisions serving these drivers carry `satisfies:` front-matter — e.g. `ADR-0001` satisfies
`Q.01`. To list them: `grep -rl "satisfies:.*Q.01" .`
