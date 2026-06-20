---
id: AD
title: <Entity of Interest> — Architecture Description
status: current               # current | draft | deprecated
version: 0.1.0                # semver of the AD itself
updated: <YYYY-MM-DD>
entity-of-interest: <system / product / service name>
level: software              # enterprise | solution | software — altitude of this AD's EoI
conforms-to:
  - ISO/IEC/IEEE 42010:2022   # architecture description (required content)
  - ISO/IEC 25010:2023        # product quality model (quality characteristics)
  - ISO/IEC/IEEE 29148:2018   # requirements engineering (PRD)
authors: [<name/team>]
---

# Architecture Description — <Entity of Interest>

> **Conformant container per ISO/IEC/IEEE 42010:2022.** This document provides the
> *required content* of an Architecture Description (AD) and ties together the PRD,
> HLD, SD(s), decisions and glossary, which hold the detailed content of the views.
> Each numbered clause below corresponds to a 42010 required-content item; address
> every one (briefly is fine — empty is not, that breaks conformance). Audit with
> `conformance-checklist.md`.

## 1. AD identification & overview  *(42010: AD information)*
| Field | Value |
|---|---|
| Entity of Interest (EoI) | <what is being described> |
| Purpose & scope | <why this AD exists; what's in/out of scope> |
| Version / date / status | <from front-matter> |
| Architecture rationale (overview) | <one paragraph: the central idea and why> |
| Related documents | [PRD](./PRD.md) · [HLD](./HLD.md) · SD-*.md · [decisions](./decisions/README.md) · [GLOSSARY](./GLOSSARY.md) |
| Standards conformed to | ISO/IEC/IEEE 42010:2022; ISO/IEC 25010:2023; ISO/IEC/IEEE 29148:2018 |

## 2. Stakeholders  *(42010: identify stakeholders)*
Everyone who develops, operates, uses, or is affected by the EoI. Every stakeholder
must have at least one concern in §3.

| ID | Stakeholder | Role / relationship | Key concerns |
|----|-------------|---------------------|--------------|
| SH.01 | <e.g. application engineer> | <uses the system> | CN.01, CN.03 |

## 3. Concerns  *(42010: identify concerns; each MUST be framed by a viewpoint)*
A concern is an interest in the EoI (a need, goal, risk, or quality). Group by
stakeholder perspective if helpful. **Every concern must be framed by ≥ 1 viewpoint
in §5** — that is the conformance rule.

| ID | Concern | Stakeholders | Framed by viewpoint(s) | Related drivers |
|----|---------|--------------|------------------------|-----------------|
| CN.01 | <e.g. How do I integrate the system?> | SH.01 | VP-CTX | F.01 |
| CN.02 | <e.g. Will it meet performance targets?> | SH.02 | VP-QUAL | Q.01 |

## 4. Architecture aspects *(42010:2022, optional)*
Cross-cutting characteristics reflected across multiple views (e.g. concurrency,
security, data flow). List them so views can be checked for consistent treatment.
- <aspect> — appears in: <views>

## 5. Viewpoint catalogue  *(42010: required content of an AD; each viewpoint frames concerns)*
A viewpoint is the convention for constructing a kind of view. Define each before
using it. The starter set below maps the C4 / arc42 views this skill produces onto
42010 viewpoints — keep, drop, or add to suit the EoI.

| Viewpoint ID | Name | Concerns framed | Stakeholders | Model kinds / notation | Governs view(s) |
|---|---|---|---|---|---|
| VP-CTX | Context | system scope, external interfaces, dependencies | all | C4 Context (mermaid) | V-CTX |
| VP-FUNC | Functional / building-block | functional structure, responsibilities, interfaces | architects, developers | C4 Container + Component (mermaid) | V-CON, V-COM-* |
| VP-RUN | Runtime | behaviour, collaboration, ordering | architects, developers | UML/mermaid sequence, C4 Dynamic | V-RUN-* |
| VP-DEP | Deployment | infrastructure, distribution | ops, architects | C4 Deployment (mermaid) | V-DEP |
| VP-QUAL | Quality | quality requirements & trade-offs | all | QA scenarios (SEI/ATAM), ISO 25010 | V-QUAL |
| VP-DEC | Decision | rationale, alternatives, traceability | architects, developers | ADR (Nygård/MADR) | V-DEC |

<!-- For each viewpoint you can add a fuller spec: source/reference, intended
     consumer expertise, scope of concerns, and level of detail (the Cambridge
     view-definition shape works well here). -->

## 6. Views  *(42010: AD contains one or more views, each governed by exactly one viewpoint)*
Each view realizes a viewpoint and lives in a content doc. A view is governed by
**exactly one** viewpoint.

| View ID | Governing viewpoint | Concerns addressed | Realized in |
|---|---|---|---|
| V-CTX | VP-CTX | CN.01 | HLD §2 (System context) |
| V-CON | VP-FUNC | CN.01, CN.03 | HLD §3 (Containers) |
| V-COM-<area> | VP-FUNC | CN.03 | SD-<area> §2 (Components) |
| V-RUN-<flow> | VP-RUN | CN.03 | HLD §5 / SD-<area> §3 |
| V-DEP | VP-DEP | CN.04 | HLD §6 (Deployment) |
| V-QUAL | VP-QUAL | CN.02 | PRD §5 (Quality scenarios) |
| V-DEC | VP-DEC | <as relevant> | decisions/ (ADRs) |

## 7. Correspondences & consistency  *(42010: correspondences, correspondence rules, known inconsistencies)*
Relations between AD elements and the rules that keep views consistent.

**Correspondence rules** (must always hold):
- CR.01: Every concern in §3 is framed by ≥ 1 viewpoint in §5.
- CR.02: Every view in §6 is governed by exactly one viewpoint in §5.
- CR.03: A component in a Container view appears in the matching Component SD.
- CR.04: An element named in a diagram matches the term in the GLOSSARY.
- CR.05: A change to one view updates corresponding views/SDs/ADRs in the same change.

**Known inconsistencies** (record openly — hiding them breaks conformance):
- <none yet> / <describe + tracking issue>

## 8. Architecture decisions & rationale  *(42010: capture key decisions + rationale)*
Architecturally significant decisions are recorded as ADRs in
[`decisions/`](./decisions/README.md) (Nygård/MADR). This clause is satisfied by the
decision log; the overall rationale is summarised in §1.

## 9. Conformance
Audited against the required content of the standards above — see
[`conformance-checklist.md`](./conformance-checklist.md). Re-check on any change
that adds a stakeholder, concern, view, or significant decision.
