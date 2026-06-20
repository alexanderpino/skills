---
id: SD-<area>          # e.g. SD-rendering
title: <Component / feature> design
status: current        # draft | in-review | current | deprecated | superseded
level: software
updated: <YYYY-MM-DD>
owner: <accountable person/team>
source: designed       # designed (To-Be) | traced (As-Is, recovered from runtime — migration.md §4)
related-adrs: []       # ADRs shaping this component, e.g. [ADR-0007]
satisfies: []          # PRD driver IDs, e.g. [F.02, Q.02]
realizes-views: [V-COM-<area>, V-RUN-<flow>]   # ISO 42010 views (defined in AD.md §6)
---

# SD — <Component / feature>

> Realizes the component (and relevant runtime) **views** of the Architecture
> Description (governed by VP-FUNC / VP-RUN in [AD.md](./AD.md) §6). The components
> shown here must correspond to those in the HLD container view (rule CR.03).
> Sequence diagrams may be **designed** (To-Be) or **traced** (As-Is, auto-recovered from
> distributed tracing/APM/logs — set `source: traced`; see `references/migration.md` §4).
> An As-Is SD can be conformance-checked against its To-Be counterpart to reveal drift.

Detailed design of one component or feature. Small and focused beats large and
comprehensive — split if it grows past what fits in your head.

## 1. Purpose & scope
What this component is responsible for, and explicitly what it is **not**.

## 2. Component view (C4)
```mermaid
C4Component
  title Components — <Component / feature>
  Component(x, "<Internal part>", "<tech>", "<responsibility>")
  Component(y, "<Internal part>", "<tech>", "<responsibility>")
  Rel(x, y, "<data/contract>", "<mechanism>")
```

## 3. Key interactions
Sequence diagram(s) for non-obvious collaborations — the ones a reader couldn't
guess. Skip if the interaction is trivial.

```mermaid
sequenceDiagram
  participant A as <part>
  participant B as <part>
  A->>B: <call>
  B-->>A: <result>
```

## 4. Interfaces & contracts
The public surface: functions/APIs/messages/file formats others depend on. For
each: name, inputs, outputs, errors. Changes here are architecturally significant
— they need an ADR.

## 5. Data structures & types
The important types and their relationships. A `classDiagram` if composition/
association matters (see mermaid guide).

## 6. Error handling & edge cases
How failures propagate, what's retried, what's fatal, and the boundary conditions
that bite (empty input, oversized data, partial failure of a chain, etc.).

## 7. Decisions & drivers
- Satisfies drivers: <F.xx, Q.xx>
- Shaped by: <ADR-NNNN — one-line why>

## 8. Known issues / debt
Local smells or compromises and the quality attribute they threaten.
