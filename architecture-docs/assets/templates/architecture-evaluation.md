---
id: EVAL
title: <System/solution name> — Architecture Evaluation
status: draft                 # draft | in-review | current
level: software               # enterprise | solution | software
updated: <YYYY-MM-DD>
evaluated-system: <entity of interest>
method: ATAM-lite             # ATAM-lite | ATAM | SAAM | CBAM | informal
source: recovered             # usually evaluating an As-Is architecture
owner: <evaluating architect / team>
satisfies: []                 # quality drivers examined, e.g. [Q.01, Q.03]
---

# Architecture Evaluation — <System/solution name>

> **Assesses whether an architecture is fit for its quality goals** — distinct from
> `conformance-checklist.md` (which audits *document completeness* against ISO 42010). This
> evaluates the *architecture itself*. Grounded in **SEI ATAM** (Bass, Clements & Kazman) and
> the scenario-based family (SAAM, CBAM). Most useful on **existing software**: a health-check
> before investing in it, acquiring it, or planning a migration. Full method: `methods.md` §11.

## 1. Scope & context
What is being evaluated and why now (e.g. pre-migration health-check, due-diligence, recurring
review). The business drivers and the architecture under evaluation (link the HLD/SAD/AD).

## 2. Quality attribute scenarios evaluated
The prioritised scenarios this evaluation tests the architecture against (reuse the PRD `Q.xx`
6-part scenarios / utility tree; add any missing). These are the yardstick.

| ID | Quality attribute (ISO 25010) | Scenario (source·stimulus·response·measure) | Priority (value × difficulty) |
|----|------|------|------|
| Q.01 | <e.g. performance efficiency> | <…> | H × M |

## 3. Architectural approaches
For each scenario, the approach/tactic the architecture actually uses to achieve it (layering,
caching, replication, bulkheads, an event bus, …) — recovered from the design/code.

## 4. Findings
The core ATAM outputs:

- **Risks** — decisions or gaps that endanger a quality goal. *(Each significant risk → an
  ADR proposing the fix, or a debt entry.)*
- **Non-risks** — decisions confirmed sound for the goals (record them; they're reassurance).
- **Sensitivity points** — elements where a quality measure hinges critically on one decision.
- **Trade-off points** — decisions that help one quality and hurt another (the sharpest finds).

| # | Type (risk / non-risk / sensitivity / trade-off) | Scenario(s) | Finding | Impact | Recommendation / ADR |
|---|---|---|---|---|---|
| F1 | risk | Q.01 | <single shared DB is a scaling & blast-radius risk> | High | <split read model — ADR-00NN> |
| F2 | trade-off | Q.01 ↔ Q.03 | <cache improves latency, weakens consistency> | Med | <bounded staleness — ADR-00NN> |

## 5. Risk themes
Cluster the risks into themes (e.g. "no horizontal scaling path", "untested failure modes",
"security debt at the edge"). Themes, not individual risks, drive the roadmap.

## 6. Recommendations & roadmap
Prioritised actions (quick wins vs. structural), each tied to a finding and, where it's a real
decision, an **ADR**. For a system headed for change, this feeds the
`transition-architecture.md`.

## 7. Fitness functions (keep the evaluation alive)
Turn the top scenarios into **automated fitness functions** (evolutionary architecture — Ford,
Parsons & Kua) so the qualities are continuously verified, not assessed once: e.g. a
dependency-cycle test (maintainability), a p99-latency budget test (performance), an
architecture-rule check in CI (`arch_lint` / ArchUnit / dependency-cruiser). List each fitness
function and where it runs.
