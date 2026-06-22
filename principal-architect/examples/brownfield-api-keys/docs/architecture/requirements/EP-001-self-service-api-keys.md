---
id: EP-001
title: Self-service API keys
status: in-progress
level: software
updated: 2026-06-20
owner: team-platform
format: default
realizes-capabilities: [CAP-developer-platform]
satisfies: [F.01, F.02, F.03]
priority: must
---

# EP-001 — Self-service API keys

> Ingested from the given backlog epic. Default format (no house epic style detected in this
> example repo).

## Outcome
**So that** external integrators can authenticate programmatically and start calling the
LinkShort API in minutes, without the platform team manually provisioning credentials.

## Scope
- **In scope:** generating keys, revoking keys, per-key rate limiting.
- **Out of scope:** OAuth flows, per-endpoint scopes, billing.

## Traceability
| Up — capability | Functional drivers (features) | Down — stories |
|---|---|---|
| CAP-developer-platform | F.01, F.02, F.03 (PRD §4) | US-001 (more to follow: revoke, rate-limit) |

Quality expectations reference `Q.01` (key confidentiality) — not re-specified here.

## Epic-level acceptance (definition of done for the epic)
- [ ] An integrator can generate, use, and revoke a key end-to-end with no manual step.
- [ ] `Q.01` passes its means of verification (no recoverable plaintext keys).

## Notes / open questions
- Assumption: existing integrator accounts already authenticate via session/password; key
  issuance reuses that identity. (Confirm with product — recorded as a visible assumption.)
