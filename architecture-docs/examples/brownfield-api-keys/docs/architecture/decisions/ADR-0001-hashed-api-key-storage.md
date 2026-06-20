---
id: ADR-0001
title: Store only salted hashes of API keys
status: accepted
level: software
date: 2026-06-20
derivation: recovered
deciders: [team-platform]
tags: [security, auth, storage]
affects: [keysvc, api_keys]
satisfies: [Q.01, F.01]
---

# ADR-0001: Store only salted hashes of API keys

## Status
Accepted

## Context
EP-001 introduces self-service API keys. A leaked database must not expose usable credentials
(`Q.01`, confidentiality). The existing schema stored a `key_value` column in plaintext — a
liability recovered during reverse-engineering of the current service.

## Decision
We will store each API key only as a **salted SHA-256 hash**. The plaintext token is returned
to the integrator exactly once at creation and never persisted. Verification hashes the
presented token and compares.

## Consequences
- **+** A DB leak yields no usable keys (`Q.01` met); aligns with OWASP A02.
- **+** Revocation (`F.02`) is a row flag, independent of the secret.
- **−** A lost key cannot be recovered — the integrator must generate a new one. Accepted;
  mitigated by easy regeneration (US-001).
- Migration: drop the legacy `key_value` column after backfilling hashes.
