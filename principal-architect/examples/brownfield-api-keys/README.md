# Worked example — architecting from *given* requirements (existing software)

A complete, **lint-clean** demonstration that the `principal-architect` skill can produce the
required architecture documents when you are *handed* functional requirements, an epic, and
user-story acceptance criteria for **existing software** — the common brownfield case.

## The scenario (the inputs you're given)

`LinkShort` is an **existing** Python/Flask URL-shortener REST API. Product hands you a
backlog item to document and extend:

- **Epic (given):** "Self-service API keys" — let external integrators authenticate
  programmatically without manual onboarding.
- **Functional requirements (given):**
  - FR-1: integrators can generate an API key.
  - FR-2: integrators can revoke a key.
  - FR-3: each key is rate-limited independently.
- **User story + acceptance criteria (given, Gherkin):** "As an integrator I want to
  generate an API key so that I can call the API without sharing my password," with
  Given/When/Then acceptance criteria.
- **A quality expectation (given):** keys must never be recoverable if the database leaks.

## What the skill produced from those inputs

Following `references/business-analysis.md` §0 (ingest given requirements — don't re-elicit)
and §3 reverse-engineering for the existing code, mapped onto the skill's structure:

| Given input | Document produced | ID |
|---|---|---|
| Epic | `requirements/EP-001-self-service-api-keys.md` | `EP-001` |
| FR-1…FR-3 | functional drivers in `PRD.md` §4 | `F.01`–`F.03` |
| Quality expectation | quality driver in `PRD.md` §5 (6-part scenario) | `Q.01` |
| Story + acceptance criteria | `requirements/US-001-issue-api-key.md` | `US-001` |
| Recovered design of the existing service | `software/HLD.md`, `software/SD-api-keys.md` | — |
| Recovered decision (hashed-key storage) | `decisions/ADR-0001-hashed-api-key-storage.md` | `ADR-0001` |
| ISO/IEC/IEEE 42010 conformance | `AD.md` + `conformance-checklist.md` | — |

The traceability chain is intact end-to-end:
`EP-001 → F.01 → US-001 → acceptance criteria → test`, and `ADR-0001` is enacted in
`src/keys.py` via an `ARCH-REF:` marker.

## Verify it

```bash
python3 ../../assets/ci/tools/arch_lint.py all \
  --root docs/architecture --src src
```

Exits `0` with no errors — the set is front-matter-valid, 42010-conformant, drift-free, and
its links resolve. This example is also linted automatically by the run skill's driver.
