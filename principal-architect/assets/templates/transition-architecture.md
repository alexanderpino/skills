---
id: transition-architecture
title: <Transformation name> — Transition Architecture
status: draft                 # draft | in-review | current | deprecated | superseded
version: 0.1.0
level: solution               # solution | enterprise (migrations usually span systems)
domain: <business domain>
owner: <accountable architect / team>
updated: <YYYY-MM-DD>
conforms-to: [ISO/IEC/IEEE 42010:2022]
frameworks: [TOGAF ADM Phase E/F]
migration-strategy: []        # 7 R's per system, e.g. [rehost, replatform, refactor]
complies-with: []             # enterprise principle IDs
realizes-capabilities: []
---

# Transition Architecture — <Transformation name>

> The roadmap from the current state to the target, **through documented interim states**.
> Never jump As-Is → To-Be in one undocumented leap. Each interim state must be a viable,
> testable, *reversible* configuration. Method and patterns: `references/migration.md`.

## 1. Drivers & scope
Why transform now, the goals/outcomes, scope (systems in/out), constraints, and the
enterprise principles (`PR.xx`) and capabilities this serves. Scenario type
(local-to-global / on-prem→cloud / monolith→distributed/SaaS — `migration.md` §2).

## 2. Baseline architecture (As-Is)
The current state, captured from evidence — including **As-Is sequence diagrams**
recovered from runtime (tracing/APM/logs, `source: traced`; see `migration.md` §4).

```mermaid
flowchart LR
  a[Legacy system]:::old --> b[(Shared DB)]:::old
  classDef old fill:#f4cccc,stroke:#333
```
Known constraints, coupling, and debt that shape the path.

## 3. Target architecture (To-Be)
The desired end state and why it meets the drivers. Link the HLD/SAD that define it.

```mermaid
flowchart LR
  s1[Service A]:::new --> e[(Event bus)]:::mid
  s2[Service B]:::new --> e
  classDef new fill:#d9ead3,stroke:#333
  classDef mid fill:#fff2cc,stroke:#333
```

## 4. Migration strategy (per system — 7 R's)
| System | 7 R's strategy | Rationale | Target |
|---|---|---|---|
| <System A> | refactor | <high value, cloud-native> | <To-Be> |
| <System B> | rehost → replatform | <speed first, optimise later> | <To-Be> |

## 5. Transition states (the heart of this document)
One subsection per interim state. Each must stand on its own and be reversible.

### T1 — <name of interim state>
- **Scope / what changes:** <which slice moves; what runs in parallel>
- **Patterns used:** <Strangler Fig router / ACL at boundary / event-driven intermediary>
- **Data & protocol mapping:** <CDC running? old↔new schema/protocol adapters; SoT per entity>
- **Risks:** <risk → likelihood/impact → mitigation>
- **Rollback strategy:** <exact steps to revert to the previous state; data reconciliation;
  feature-flag/route flip; what makes rollback safe and how long it stays possible>
- **Validation / exit criteria:** <objective checks that must pass before T2: traffic %,
  error budget, reconciliation counts, conformance of As-Is vs To-Be SD>

### T2 — <name of interim state>
<repeat the structure>

```mermaid
flowchart LR
  AsIs[Baseline] --> T1[T1] --> T2[T2] --> ToBe[Target]
```

## 6. Cutover & decommission
The final cutover plan, the decommissioning of retired systems (7 R's: retire), and the
point of no return (after which rollback is no longer the strategy — forward-fix only).

## 7. Risks, dependencies & decisions
- Cross-cutting risks and mitigations; sequencing dependencies between states.
- Each significant choice (strategy, pattern, mapping/CDC, cutover) is an ADR
  (`level: solution`/`enterprise`), linked here.
- Threat model and FinOps for each interim state live in the relevant HLD/SAD; summarise
  residual risk here.
