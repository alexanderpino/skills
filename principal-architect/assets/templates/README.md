<!--
TEMPLATE — architecture index / map. Copy to <root>/README.md and fill in.
This is the "start here" file and the RAG entrypoint. Keep it short; it is a router.
The YAML manifest below is machine-readable — keep it in sync with the tree on every
add/move (see references/repository-structure.md).
-->
---
id: architecture-index
title: Architecture documentation — index
updated: <YYYY-MM-DD>
documents:
  - { id: AD,           path: AD.md,                                  level: software,   status: current }
  - { id: PRD,          path: software/PRD.md,                        level: software,   status: current }
  - { id: HLD,          path: software/HLD.md,                        level: software,   status: current }
  - { id: EA,           path: enterprise/enterprise-architecture.md,  level: enterprise, status: current }
  - { id: cap-map,      path: enterprise/capability-system-map.md,    level: enterprise, status: current }
  - { id: decision-log, path: decisions/README.md,                    level: all,        status: current }
---
# Architecture documentation

**Docs root:** `docs/architecture/`  <!-- record the resolved root here -->

Start here. This index maps the architecture docs so you (human or agent) can
reach the right one in one more read.

## Read before planning or changing code
1. The relevant **PRD** drivers for what you're touching.
2. The **HLD** section for the affected area.
3. The **SD(s)** for the affected component(s).
4. Any **ADR** whose `affects:` overlaps your task — search:
   `grep -rl "affects:.*<component>" decisions/`.
Then check your plan doesn't contradict an `accepted` ADR.

## Documents

| Doc | Purpose | Status |
|-----|---------|--------|
| [AD.md](./AD.md) | **Architecture Description** — ISO/IEC/IEEE 42010 conformant root (stakeholders, concerns, viewpoints, views, correspondences) | current |
| [PRD.md](./PRD.md) | Drivers: business `B.xx`, functional `F.xx`, quality `Q.xx` (ISO 25010 + 6-part scenarios) | current |
| [HLD.md](./HLD.md) | System shape: C4 context + container + deployment, main flows | current |
| [SD-<area>.md](./SD-<area>.md) | Detailed design per component/feature | — |
| [decisions/](./decisions/README.md) | Decision log — all ADRs (Nygård / MADR) | — |
| [GLOSSARY.md](./GLOSSARY.md) | Domain & technical terms | current |
| [conformance-checklist.md](./conformance-checklist.md) | ISO conformance audit (42010 / 25010 / 29148) | current |

<!-- Add an SD row per component. Keep this table truthful; it is the contract
     that makes navigation cheap. -->

## Standards & conformance
These documents conform to **ISO/IEC/IEEE 42010:2022** (architecture description),
**ISO/IEC 25010:2023** (quality model), and **ISO/IEC/IEEE 29148:2018** (requirements),
and follow **arc42** (structure) and **C4** (diagrams). The conformant root is
[AD.md](./AD.md); verify with [conformance-checklist.md](./conformance-checklist.md).
The arc42 12-section checklist is covered across AD + PRD + HLD + SDs + decisions +
glossary. See the skill's `references/standards.md` for the full mapping.

## Higher altitudes (if this work spans them)
This index covers **software-level** (system) docs. For broader scope, link the
relevant higher-altitude docs (often in a central EA repository):
- **Enterprise** — `enterprise-architecture.md` (TOGAF/ArchiMate): capabilities,
  principles, landscape, roadmap. Software here `complies-with:` its principles.
- **Solution** — `SAD.md`: the end-to-end solution this system is part of.

## Conventions (summary)
- IDs are stable and never reused. ADR numbers are 4-digit zero-padded.
- Decisions are ADRs in **Nygård format**, one per file in `decisions/`.
- Code references a decision with a `ARCH-REF: ADR-NNNN` comment at the site it's
  enacted. Find them: `grep -rn "ARCH-REF:" ../../src/`.
- Front-matter is the greppable layer; filter on it before reading bodies.

## How to add things
- New decision → copy `ADR.md` template → `decisions/ADR-NNNN-slug.md`, then add a
  row to `decisions/README.md`.
- New component → copy `SD.md` template → `SD-<area>.md`, then add a row above.
- Changed system shape → update `HLD.md` (and its diagrams) in the same change.
