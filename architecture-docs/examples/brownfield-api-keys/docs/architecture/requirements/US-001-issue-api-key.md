---
id: US-001
title: Generate an API key
status: ready
level: software
updated: 2026-06-20
owner: team-platform
format: default
epic: EP-001
satisfies: [F.01]
realizes-capabilities: [CAP-developer-platform]
ac-style: gherkin
estimate: 3
priority: must
---

# US-001 — Generate an API key

> Ingested from the given user story; acceptance criteria copied verbatim from the backlog
> (they were already testable, so kept as-is per `business-analysis.md` §0).

## Story
**As an** external integrator
**I want** to generate an API key for my account
**so that** I can call the LinkShort API without sharing my password.

## Context / notes
Delivers `F.01` under epic `EP-001`. The key value is shown once and never stored in plaintext
(see `Q.01` and `ADR-0001`). Solutioning lives in `SD-api-keys`, not here.

## Acceptance criteria

```gherkin
Scenario: Integrator generates a key
  Given I am an authenticated integrator with no API key
  When  I POST /api/keys
  Then  I receive a 201 with a key value shown exactly once
  And   the key works as a bearer credential on a subsequent request

Scenario: Generated key is never stored in plaintext
  Given I have generated an API key
  When  the platform team inspects the keys table
  Then  only a salted hash of the key is present, never the key value

Scenario: Reuse of the one-time reveal is impossible
  Given I have generated an API key
  When  I request the key value again
  Then  the API does not return it (I must generate a new key)
```

## INVEST self-check
Independent · Negotiable · Valuable · Estimable · Small · Testable — passes.

## Definition of Done
AC met & demoed · tests automated & green · `SD-api-keys`/`ADR-0001` updated if design changed ·
reviewed · merged · deployed to production.
