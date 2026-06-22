# Standards alignment

This skill is not a bespoke format — every artifact it produces maps onto a
recognised industry standard. Follow these so the output is portable, reviewable,
and familiar to any architect. Cited versions are current as of mid-2026; if a
team already mandates one of these, conform to theirs rather than inventing a
parallel structure.

## Three architecture altitudes (enterprise · solution · software)

A master architect works at three levels. ISO/IEC/IEEE 42010:2022 unifies them: it
describes the architecture of an **entity of interest (EoI)** — which can be an
*enterprise*, a *solution*, or a *system*. The level fixes the EoI, the frameworks,
the notation, and the artifacts; the decision discipline (ADRs) is shared.

| Level | Entity of interest | Primary concerns | Frameworks / notation | Artifacts (templates) |
|---|---|---|---|---|
| **Enterprise** | the organisation / a segment / a capability | strategy↔IT alignment, the whole landscape, capabilities, principles, governance, roadmaps | **TOGAF 10** (ADM, BDAT domains), **ArchiMate 3.2**, Zachman | `enterprise-architecture.md`, principles, capability map, roadmap |
| **Solution** | one solution, often spanning several systems | end-to-end design, integration, technology selection, build-vs-buy, cross-cutting NFRs, fit to the enterprise | TOGAF (Phase E/SBBs), ArchiMate/C4, **EIP** integration patterns | `SAD.md` (Solution Architecture Document) |
| **Software** | a single system / application | components, modules, patterns, interfaces, code structure | **C4**, arc42, UML | `AD.md`, `PRD.md`, `HLD.md`, `SD.md` |

Decisions and traceability cascade **down**, conformance flows **up**: enterprise
*principles* (PR.xx) and *capabilities* constrain *solution* choices, which constrain
*software* designs. ADRs carry a `level:` field; solution/software ADRs carry
`complies-with: [PR.xx]`. Pick the altitude first (the skill's "Three altitudes"
section) — don't apply TOGAF to a code refactor, or stop at C4 for a portfolio choice.

### TOGAF Standard, 10th Edition (enterprise)
The **ADM** is the method: Preliminary → A Vision → B Business → C Information Systems
(Data + Application) → D Technology → E Opportunities & Solutions → F Migration
Planning → G Implementation Governance → H Change Management, with **Requirements
Management** continuous at the centre. Four domains = **BDAT** (Business, Data,
Application, Technology). Outputs live in the **Architecture Content Framework**
(Architecture Vision, Architecture Definition Document, Requirements Specification,
Roadmap) as catalogs/matrices/diagrams, built from **ABBs** (reusable Architecture
Building Blocks) and **SBBs** (implementable Solution Building Blocks), stored in the
**Architecture Repository**. Phase D names *logical* technology blocks — vendor/product
selection is solution/implementation work. The `enterprise-architecture.md` template is
a lean Architecture Definition Document. TOGAF's **Gap Analysis** technique (used across
Phases B–E) is the formal instrument for landscape/capability gaps: a **Gap Analysis Matrix**
(baseline building blocks × target, plus an *Eliminated* column and a *New* row) whose
*eliminated*/*new* cells become roadmap work packages. Method and matrix in `methods.md` §12.

### ArchiMate 3.2 (enterprise/solution modelling language)
The Open Group's modelling language — the EA counterpart to what C4/UML are for
software. Core = 3 layers (**Business · Application · Technology**) × 3 aspects (active
structure / behavior / passive structure); full framework adds **Motivation**,
**Strategy**, **Physical**, **Implementation & Migration** layers. It uses a viewpoints
mechanism and maps cleanly onto TOGAF ADM (Motivation/Strategy → Vision; B/A/T layers →
Phases B–D; Implementation & Migration → Phases E–H). Mermaid has no native ArchiMate
notation — represent ArchiMate views as layered flowcharts (see `mermaid-guide.md`).

### Zachman Framework (enterprise ontology)
A taxonomy, not a method: a 6×6 matrix of interrogatives (What/How/Where/Who/When/Why)
against perspectives (Executive→Operations). Use it as a *completeness check* — have we
addressed each cell that matters? — complementary to TOGAF's process.

## The standards this skill follows

| Concern | Standard | How this skill applies it |
|---|---|---|
| Overall doc structure | **arc42** (Starke & Hruschka), 12 sections | PRD + HLD + SDs together cover the 12 sections (mapping below). arc42's "everything is optional — a cabinet with empty drawers still has value" is exactly our proportional rigour. |
| Architecture description concepts | **ISO/IEC/IEEE 42010:2022** (replaced :2011) | Stakeholders, concerns, viewpoints, views, model kinds, and **correspondence rules** (views must stay consistent — see §"Consistency" below). Unifies all three altitudes via *entity of interest*. |
| Enterprise architecture | **TOGAF 10** + **ArchiMate 3.2** + Zachman | ADM/BDAT structure the `enterprise-architecture.md`; ArchiMate is the notation; Zachman a completeness check. |
| Solution architecture | TOGAF (Phase E, SBBs) + **EIP** | `SAD.md`: end-to-end design, integration patterns, technology selection. |
| Diagram levels (software) | **C4 model** (Simon Brown) | Context / Container / Component / Code, plus supplementary Dynamic, Deployment, System Landscape. See `mermaid-guide.md`. |
| Quality requirements | **SEI Quality Attribute Scenarios + ATAM** (Bass, Clements, Kazman, *Software Architecture in Practice*) | Quality drivers are written as the canonical **6-part scenario** and prioritised with a quality/utility tree. |
| Architecture evaluation | **ATAM** + scenario family (**SAAM**, **CBAM** for cost) + **evolutionary architecture / fitness functions** (Ford, Parsons & Kua) | `architecture-evaluation.md`: risks · non-risks · sensitivity · trade-off points; top scenarios become CI fitness functions. Method in `methods.md` §11. |
| Interface contracts | **OpenAPI 3.1** · **AsyncAPI 3.0** · **gRPC/Protobuf** · **GraphQL SDL** · **Pact** (consumer-driven) | The contract is the source of truth, linked from `SD` via `api-spec:`; breaking changes are ADR-worthy. See `interfaces.md`. |
| Privacy & data protection | **ISO/IEC 29134** (PIA) · **GDPR/UK-GDPR Art. 25/35** · CCPA · HIPAA · PCI-DSS | Mandatory DPIA in HLD/SAD §8 where personal/regulated data is processed; `privacy-reviewed` flag. See `privacy.md`. |
| Decisions (all levels) | **Michael Nygård ADR** (default) + **MADR 4.0.0** (superset) + Y-Statements | One decision per file, immutable, four-state lifecycle, `level:` tagged. Nygård by default; MADR fields when a decision needs them. |
| Requirement wording | **RFC 2119 / RFC 8174** | Normative keywords MUST / SHALL / SHOULD / MAY used precisely in the PRD. |
| Requirements process (optional) | **ISO/IEC/IEEE 29148** | If the team does formal requirements engineering, the PRD slots in as the product/stakeholder requirements view. |
| Software diagrams (mandatory) | **C4 model** levels L1–L4 | Context+Container always; Component where significant; Code rarely/generated. Models-as-code via Structurizr DSL. See `mermaid-guide.md`. |
| Security / threat modelling | **STRIDE** (Microsoft) + **OWASP Top 10:2025** | Mandatory threat-model section in HLD §8 and SAD §8. |
| Cloud cost / FinOps | **FinOps Foundation** framework + **Infracost** | Mandatory cost-estimate matrix in HLD §9 and SAD §9; cost gate in CI (`automation.md`). |
| Legacy reverse engineering | **SAR** (Ducasse & Pollet 2009; Murphy/Notkin/Sullivan reflexion; SEI CMU/SEI-2002-TR-024) | Grounded code-to-architecture strategy in `reverse-engineering.md`. |
| Governance | RFC → ADR + Architecture Board (TOGAF) | `governance.md`; enforced in CI (`automation.md`). |
| Migration & modernization | **7 R's** (AWS/Gartner) · **Strangler Fig** (Fowler) · **Anti-Corruption Layer** (Evans, DDD) · **TOGAF Transition Architecture** (ADM E/F) · As-Is SD recovery (Briand/Labiche/Leduc, IEEE TSE 2006) | Strategy + patterns + As-Is/To-Be in `migration.md`; `transition-architecture.md` template. |
| Gap analysis (all altitudes) | **TOGAF Gap Analysis Matrix** (ADM B–E) · **Fit-Gap** (build-vs-buy/COTS) · **BABOK Strategy Analysis** (current→future→change strategy) | One technique — current→target→delta→closure — with the standard instrument per altitude. Method in `methods.md` §12. |
| Business analysis | **IIBA BABOK® Guide v3** + Agile Extension · **INVEST** (Wake) · **Connextra** story format · **Gherkin** (BDD) | User stories + acceptance criteria in `business-analysis.md`; format-adaptive `user-story.md` — **detect & conform to the org's house style first**. |
| Boundaries & structure (software) | **Strategic DDD** (Evans 2003; Vernon) — codified in **The Open Group O-AA Standard** "DDD strategic patterns" · **Component principles** REP/CCP/CRP + ADP/SDP/SAP and the **Dependency Rule** (Robert C. Martin) · **Hexagonal / Ports & Adapters** (Cockburn) | Finding boundaries (subdomains, bounded contexts, context maps) + choosing a structuring style + the dependency principles, in `structure.md` §§1–2. Style/pattern adoption is ADR-worthy (`significance.md`). |
| Tactics & distributed/cloud patterns | **Architectural tactics** (SEI; Bass, Clements & Kazman, 4th ed.) · **Cloud Design Patterns** (Microsoft Azure Architecture Center) — circuit breaker, bulkhead, retry, CQRS, event sourcing, strangler · **microservices.io** (Richardson) — saga, transactional outbox · **EIP** (Hohpe & Woolf) | Forward catalogue keyed to ISO 25010 qualities — pick a tactic to meet a `Q.xx`, record the trade-off as an ADR. `structure.md` §3. |
| Evolutionary & agile architecture | **Building Evolutionary Architectures / fitness functions** (Thoughtworks — Ford, Parsons & Kua) · **Architectural Runway**, intentional vs emergent (**SAFe**) · Continuous Architecture (Erder, Pureur & Woods) | The "just-enough / last-responsible-moment" stance behind the Triage table; qualities guarded by CI fitness functions. `structure.md` §4, `automation.md`. |

> **ISO/IEC/IEEE 42010:2022 is the baseline of the entire toolkit.** Every artifact at
> every altitude is, ultimately, part of an Architecture Description of some *entity of
> interest*; the `AD.md` root and `conformance-checklist.md` make that conformance explicit,
> and all other standards above slot into its stakeholders / concerns / viewpoints / views /
> decisions structure.


## ISO conformance — the required content

When the documentation must **conform** to ISO (not merely be "inspired by" it), the
governing standard is **ISO/IEC/IEEE 42010:2022**, which specifies the *required
content* of an Architecture Description (AD). Conformance is delivered through two
templates: **`AD.md`** (the conformant container) and **`conformance-checklist.md`**
(the audit). The PRD/HLD/SD/ADR/glossary supply the *content of the views*; `AD.md`
supplies the *required structure* around them.

### 42010:2022 required content (every item must be present)
1. **AD identification & overview** — entity of interest, scope, version, status.
2. **Stakeholders** — identified; each has >= 1 concern.
3. **Concerns** — identified; **each framed by >= 1 viewpoint**.
4. **Architecture viewpoints** — each defines the concerns it frames, its
   stakeholders, and its model kinds/notation.
5. **Architecture views** — one or more; **each governed by exactly one viewpoint**;
   composed of view components (the 2022 term for the former "architecture models").
6. **Correspondences & correspondence rules** — relations that keep views consistent;
   **known inconsistencies recorded openly**.
7. **Architecture decisions & rationale** — key decisions captured (ADRs).

New in 42010:2022 vs :2011 — *entity of interest* (was system of interest),
*stakeholder perspectives* (group concerns), *architecture aspects* (cross-cutting
characteristics reflected in views), and *view component* (was architecture model).
Conformance is verified, not assumed: run the gap analysis in
`conformance-checklist.md`.

### ISO/IEC 25010:2023 — the quality characteristics to name
A quality driver is conformant when it names the specific 25010 characteristic it
targets and gives a measurable response. The **nine** product-quality characteristics
(2023 revision; note the renames) and their sub-characteristics:

| Characteristic | Sub-characteristics |
|---|---|
| Functional suitability | completeness, correctness, appropriateness |
| Performance efficiency | time behaviour, resource utilization, capacity |
| Compatibility | co-existence, interoperability |
| **Interaction capability** *(was Usability)* | appropriateness recognizability, learnability, operability, user-error protection, **user engagement** *(was UI aesthetics)*, **inclusivity** *(new)*, **self-descriptiveness** *(new)* |
| Reliability | **faultlessness** *(was maturity)*, availability, fault tolerance, recoverability |
| Security | confidentiality, integrity, non-repudiation, accountability, authenticity, **resistance** *(new)* |
| Maintainability | modularity, reusability, analysability, modifiability, testability |
| **Flexibility** *(was Portability)* | adaptability, **scalability** *(new)*, installability, replaceability |
| **Safety** *(new top-level)* | operational constraint, risk identification, fail safe, hazard warning, safe integration |

SQuaRE family context: the product-quality model is **ISO/IEC 25010:2023**; the
quality-in-use model moved to **ISO/IEC 25019:2023**; the models overview is
**ISO/IEC 25002**. Measures live in the ISO/IEC 2502n standards.

### ISO/IEC/IEEE 29148:2018 — requirements (PRD)
Requirements should be necessary, singular, unambiguous, feasible, and **verifiable**.
The PRD encodes this with stable IDs, RFC 2119 keywords, and a *means of verification*
per requirement, plus traceability via `satisfies:` / `affects:` front-matter.

## arc42 ↔ this skill's documents

arc42's 12 sections are the reference checklist. They are distributed across our
docs (not a 1:1 file mapping — that's fine, arc42 is tool- and layout-agnostic):

| # | arc42 section | Lives in |
|---|---|---|
| 1 | Introduction & goals (requirements, quality goals, stakeholders) | **PRD** §1–5 |
| 2 | Constraints | **PRD** §6 |
| 3 | Context & scope | **HLD** §2 (C4 Context) |
| 4 | Solution strategy | **HLD** §1 + §7 (overview + key trade-offs) |
| 5 | Building block view *(mandatory)* | **HLD** §3 (C4 Container) → **SD** §2 (C4 Component) |
| 6 | Runtime view | **HLD** §5 / **SD** §3 (sequence diagrams) |
| 7 | Deployment view | **HLD** §"Deployment" (C4 Deployment) |
| 8 | Crosscutting concepts | **HLD** §6 |
| 9 | Architecture decisions | **decisions/** (ADRs) |
| 10 | Quality requirements (tree + scenarios) | **PRD** §5 |
| 11 | Risks & technical debt | HLD/SD "Known issues / debt" |
| 12 | Glossary | **GLOSSARY.md** |

Section 5 (building block view) is the one arc42 marks **mandatory** — never ship
an HLD without at least the container-level structure.

## Quality Attribute Scenario — the 6-part form (SEI/ATAM)

A quality requirement is only useful if it's testable. State each as a scenario
with all six parts; the **response measure** is what turns a wish into a contract:

1. **Source of stimulus** — who/what generates it (user, external system, sensor, developer).
2. **Stimulus** — the condition that arrives (request, event, attack, change request, fault).
3. **Environment** — the circumstances (normal, overload, startup, degraded, development-time).
4. **Artifact** — what is stimulated (whole system, a component, a data store, an interface).
5. **Response** — the required behaviour.
6. **Response measure** — the objective threshold (latency, throughput, % overhead, MTTR, effort).

Prioritise scenarios with a **quality/utility tree**: quality attribute → refinement
→ concrete scenarios, each tagged for business value and architectural difficulty
(ATAM). The PRD template encodes this; don't drop the measure row.

## Decisions — Nygård by default, MADR-compatible

- **Default = Nygård**: *Status · Context · Decision · Consequences*. Lean, proven,
  the origin of the term ADR.
- **MADR 4.0.0** is the broader community standard (`adr.github.io/madr`). It is a
  **superset**: when a decision genuinely needs them, add MADR's optional sections
  — *Decision Drivers*, *Considered Options*, *Pros/Cons per option*, *Confirmation*,
  *More Information*. Our ADR template marks these as optional so you can stay lean
  or go richer without changing format.
- **Current conventions to honour** (from MADR 4.0.0 / adr-tools):
  - Store under `decisions/` (MADR's current recommendation is `docs/decisions/`;
    our root already nests it there).
  - File per decision, `NNNN-kebab-title.md`. We prefix `ADR-` for greppability
    (`ADR-NNNN-slug.md`); both are accepted in practice.
  - **Status holds only the state identifier** (`accepted`), not a link or prose.
  - Four-state lifecycle: `proposed → accepted → (deprecated | superseded)`, plus
    `rejected` for declined proposals. Records are immutable and never deleted.
- ISO/IEC/IEEE 42010:2011 Annex A lists nine information items for a decision; the
  Nygård+MADR fields here cover them (decision, rationale/forces, alternatives,
  consequences, status, relations/supersession, drivers, affected concerns).

## Consistency / correspondence (ISO 42010)

42010 requires **correspondence rules**: the views must agree. Practically: when a
change alters one view, update every view and doc that corresponds to it **in the
same change** — the C4 Context, the affected Container/Component diagram, the SD
prose, the ADR, and the driver it satisfies. A diagram that disagrees with the code
or with another diagram is worse than no diagram. The `satisfies:` / `affects:` /
`related-adrs:` front-matter is the correspondence web; keep it wired.

## Pragmatic stance

arc42, ISO 42010, and ATAM are frameworks, not paperwork mandates. The widely
observed failure mode ("decision documentation theatre") is operational, not
template choice: records that aren't written when the decision is made, aren't
reviewed, and aren't updated when the world moves on. That is exactly why this
skill ties documentation to the moment of planning/changing and keeps it greppable
— so it gets written and stays true, which matters more than which standard's box
it sits in.
