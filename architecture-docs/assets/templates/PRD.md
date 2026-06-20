---
id: PRD
title: <Product / system name> — Product Requirements
status: current        # current | draft | deprecated
updated: <YYYY-MM-DD>
owners: [<team>]
---

# PRD — <Product / system name>

The *why* and *what*. Each driver has a stable ID and is referenced (by ID) from
the HLD, SDs, and ADRs. Keep statements crisp and testable.

## 1. Stakeholders
- **<Stakeholder>** — who they are and how they relate to the system.
<!-- e.g. system engineers, external integrators, end users -->

## 2. Goals & motivation
What each stakeholder wants, and what they should be able to do with the system.

## 3. Business drivers
> Stable IDs `B.NN`. The commercial / organisational reasons the system exists.

- **B.01:** <driver statement>
- **B.02:** <driver statement>

## 4. Functional drivers
> Stable IDs `F.NN`. What the system must *do*. Use RFC 2119 / 8174 keywords
> (MUST / SHALL / SHOULD / MAY) precisely so obligation level is unambiguous.

- **F.01:** The system <MUST/SHOULD> <capability>, taking <inputs> and producing <outputs>.

> **Detailed functional behaviour** is expressed as **user stories with acceptance criteria**
> (`US-NNN`), each linked back to the `F.xx` it serves (`satisfies: [F.01]`). Write them in the
> organisation's **house format** — detect and conform to it first; only fall back to the
> default template when none exists. See `references/business-analysis.md` and the
> `user-story.md` template. The chain is `capability → F.xx → US-NNN → acceptance criteria → test`.

## 5. Quality drivers — quality attribute scenarios
> Stable IDs `Q.NN`. Each quality goal targets a specific **ISO/IEC 25010:2023**
> characteristic and is written as the SEI/ATAM **6-part quality attribute scenario**,
> so it is testable rather than aspirational. The **response measure** plus a **means
> of verification** make it conformant with ISO/IEC/IEEE 29148 (every requirement
> must be verifiable). See `references/standards.md`.

> **ISO/IEC 25010:2023 characteristics** (pick the one each driver targets):
> functional suitability · performance efficiency · compatibility · interaction
> capability · reliability · security · maintainability · flexibility · safety.

### Q.01 — <short name>
| Part | Value |
|---|---|
| **Quality characteristic (ISO 25010)** | <e.g. performance efficiency → time behaviour> |
| **Source of stimulus** | <who/what generates it: user, external system, developer, sensor> |
| **Stimulus** | <the condition that arrives: request, event, change request, fault, attack> |
| **Environment** | <circumstances: normal operation, overload, startup, degraded, development-time> |
| **Artifact** | <what is stimulated: whole system, a component, a data store, an interface> |
| **Response** | <the required behaviour> |
| **Response measure** | <the objective threshold, e.g. "≥ 5 chains configurable without code change; overhead ≤ 10%; p99 latency < 200 ms"> |
| **Means of verification** | <how pass/fail is checked: benchmark, test, review, fitness function> |

<!-- Repeat the Q-block per quality driver. -->

### Quality / utility tree (prioritisation)
Prioritise the scenarios above so design effort goes where it matters (ATAM):
ISO 25010 characteristic → refinement → scenario, each rated for **business value**
and **architectural difficulty** (e.g. High/Medium/Low).

| 25010 characteristic | Refinement | Scenario | Value | Difficulty |
|---|---|---|---|---|
| <e.g. Performance efficiency> | <e.g. Time behaviour> | Q.01 | H | M |

## 6. Constraints
> Hard limits the design must respect (legal, licensing, platform, org).

- **C.01:** <constraint>

## 7. Driver → decision traceability
Decisions that serve these drivers carry `satisfies: [<IDs>]` in their
front-matter. To see which decisions address a driver:
`grep -rl "satisfies:.*Q.01" .`
