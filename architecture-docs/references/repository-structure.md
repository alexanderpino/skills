# Repository structure — the universal architecture layout

This is the canonical folder layout the skill creates and maintains. It is designed
to be **machine-readable and agent-navigable** (RAG-optimised): a strict semantic
hierarchy, one concept per file, stable IDs, and YAML front-matter on every document so
an LLM can filter and retrieve without reading bodies. Use it verbatim unless the repo
already defines its own location (Step 0 of `SKILL.md`).

## The layout

```text
docs/architecture/
├── README.md                     # 🧭 INDEX / MAP — RAG entrypoint; machine-readable manifest in front-matter
├── AD.md                         # ISO/IEC/IEEE 42010 conformant root (stakeholders, concerns, viewpoints, views)
├── GLOSSARY.md                   # ubiquitous language (arc42 §12)
├── conformance-checklist.md      # ISO 42010 / 25010 / 29148 audit
├── house-profile.yaml            # detected house conventions per doc type (detect_doc_conventions.py); enforced in CI
│
├── enterprise/                   # 🏛  ENTERPRISE altitude (often a central EA repo; link if external)
│   ├── enterprise-architecture.md   # TOGAF ADD: vision, principles, BDAT landscape, roadmap
│   └── capability-system-map.md     # bridge: Business Capability Map ⇄ systems/solutions
│
├── solution/                     # 🧩 SOLUTION altitude (one per solution)
│   └── SAD-<solution>.md            # Solution Architecture Document (end-to-end, integration, NFR, threat, cost)
│
├── migration/                    # 🔄 MIGRATION & modernization (As-Is → To-Be)
│   └── transition-<name>.md         # Transition Architecture: baseline → interim states → target
│
├── software/                     # ⚙️  SOFTWARE altitude (one folder per system if monorepo)
│   ├── PRD.md                       # product requirements / drivers (B/F/Q)
│   ├── HLD.md                       # C4 L1–L2 (+L3 index), runtime, deployment, threat model, FinOps
│   └── SD-<area>.md                 # C4 L3 component (+L4 code where useful), interfaces, data
│
├── requirements/                 # 📝 BUSINESS ANALYSIS — epics, user stories & acceptance criteria
│   ├── user-story-template.md       # the org's HOUSE format (detected, or created if none exists)
│   ├── EP-NNN-<slug>.md             # epics (large outcomes; parent of features/stories)
│   └── US-NNN-<slug>.md             # stories (or kept in the tracker; mirror the house format)
│
├── decisions/                    # 🧠 DECISIONS — single source of truth, all altitudes
│   ├── README.md                    # decision log (index table of every ADR)
│   ├── rfc/                         # proposals under discussion
│   │   └── RFC-NNNN-<slug>.md        # Request for Comments (pre-decision)
│   └── ADR-NNNN-<slug>.md           # accepted decisions (Nygård/MADR), level-tagged
│
└── diagrams/                     # 🖼  models-as-code (optional but recommended)
    ├── workspace.dsl                # Structurizr DSL — single C4 model, many views
    └── exports/                     # generated SVG/PNG (CI artifact, never hand-edited)
```

Notes:
- In a **single-system** repo you may flatten `software/` to the root (`HLD.md`, `SD-*.md`)
  — keep `decisions/`, `enterprise/` (or a link), and `solution/` as needed.
- Enterprise docs frequently live in a **central EA repository**; from a system repo, put
  a one-line pointer + `complies-with:` links rather than copying them.
- `diagrams/workspace.dsl` is the optional **architecture-as-code** source of truth for C4
  (Structurizr DSL); mermaid snippets embedded in the docs are the lightweight default.

## Why this is RAG / agent-optimised

1. **One concept per file, stable IDs.** Each ADR, SD, and driver is independently
   retrievable and citable (`ADR-0007`, `Q.02`, `SD-rendering`). Chunkers don't have to
   split a monolith; retrieval returns the smallest correct unit.
2. **YAML front-matter on every doc** = a structured metadata layer an agent filters on
   before reading prose (`grep "^status: accepted"`, or vector-DB metadata filters). See
   the schema in `conventions.md`.
3. **The README is a manifest.** `README.md` front-matter carries a machine-readable
   `documents:` catalog (id, path, level, status) so an agent loads one file to learn the
   whole map — the ideal RAG entrypoint.
4. **Semantic folder names mirror the three altitudes** (`enterprise/ solution/ software/`),
   so the path itself encodes altitude — usable as a retrieval facet.
5. **Consistent Markdown tagging.** Fixed heading order per template, fenced ```mermaid```
   blocks, and the `ARCH-REF:` code marker give deterministic anchors for extraction.
6. **Append-only decisions.** ADRs are immutable and never deleted, so a vector index never
   goes stale on rationale; supersession is a link, not an edit.

## Machine-readable index (README front-matter manifest)

```yaml
---
id: architecture-index
title: Architecture documentation — index
updated: <YYYY-MM-DD>
documents:
  - { id: AD,            path: AD.md,                              level: software,   status: current }
  - { id: PRD,           path: software/PRD.md,                    level: software,   status: current }
  - { id: HLD,           path: software/HLD.md,                    level: software,   status: current }
  - { id: EA,            path: enterprise/enterprise-architecture.md, level: enterprise, status: current }
  - { id: cap-map,       path: enterprise/capability-system-map.md,   level: enterprise, status: current }
  - { id: decision-log,  path: decisions/README.md,                level: all,        status: current }
---
```

Keep the manifest in sync with the tree on every add/move — it is the contract that lets
an agent navigate in one read.
