# Conventions

These conventions exist for one reason: **documentation an agent can navigate by
grep in two reads instead of twenty.** Consistency of IDs and front-matter
matters more than prose quality. Follow these exactly.

## 1. Stable IDs

Every referenceable item has a stable, never-reused ID. IDs are the join keys
that let docs, code, and the index point at each other.

| Item | ID pattern | Example |
|---|---|---|
| Business driver | `B.NN` | `B.03` |
| Functional driver | `F.NN` | `F.01` |
| Quality driver | `Q.NN` | `Q.02` |
| Epic | `EP-NNN` (or the house scheme) | `EP-014` |
| User story | `US-NNN` (or the house scheme, e.g. `PROJ-123`) | `US-014` |
| Enterprise principle | `PR.NN` | `PR.01` |
| RFC (proposal) | `RFC-NNNN` | `RFC-0007` |
| Decision (ADR) | `ADR-NNNN` | `ADR-0007` |
| Software design doc | `SD-<area>` | `SD-rendering` |

Rules:
- **Zero-pad ADR numbers to 4 digits** (`ADR-0007`), so lexical sort = numeric
  sort and `ADR-00` autocompletes usefully.
- **IDs are immutable and never recycled.** If a decision is reversed, write a new
  ADR that supersedes the old one — never edit the old one's meaning or reuse its
  number.
- Driver IDs (`B/F/Q`) live in the PRD and are referenced from HLD/SD/ADR by ID.

## 2. YAML front-matter

Every doc starts with YAML front-matter. This is the structured, greppable layer
— agents filter on it without reading the body.

**ADR front-matter (required fields in bold):**
```yaml
---
id: ADR-0007                 # bold/required
title: Use a file-based event bus between analysis stages   # bold/required
status: accepted             # bold/required — see lifecycle below
level: software              # bold/required — enterprise | solution | software
date: 2025-06-14             # bold/required — ISO 8601, date decided/last-changed
deciders: [team-platform]    # optional
tags: [messaging, ipc, performance]        # optional, lowercase, for discovery
affects: [analysis-runner, results-store]  # components/areas this touches
satisfies: [F.01, Q.02]      # driver IDs this decision serves
complies-with: [PR.03]       # enterprise principle IDs (solution/software decisions)
supersedes: ADR-0003         # optional, if it replaces another
superseded-by: ADR-0011      # optional, set when this one is replaced
---
```

**PRD / HLD / SD front-matter:**
```yaml
---
id: SD-rendering             # for SDs; PRD uses id: PRD, HLD uses id: HLD
title: Rendering pipeline design
status: current              # current | draft | deprecated
updated: 2025-06-14
owners: [team-graphics]      # optional
related-adrs: [ADR-0004, ADR-0007]   # ADRs that shaped this doc
satisfies: [F.02, Q.01]      # PRD driver IDs (HLD/SD)
---
```

Keep field names **exactly** as above — the grep patterns in §6 depend on them.

### Canonical field schema (machine-readable — the linter contract)

Every document carries this front-matter so an agent or CI linter (`automation.md`) can
validate and filter it. Bold = required on every doc; the rest apply where relevant.

| Field | Type / allowed values | Applies to |
|---|---|---|
| **`id`** | stable ID (see §1) | all |
| **`title`** | string | all |
| **`status`** | `draft` \| `in-review` \| `current`/`accepted` \| `proposed` \| `deprecated` \| `superseded` \| `rejected` \| `withdrawn`; user stories also use `ready` \| `in-progress` \| `done` | all |
| **`level`** | `enterprise` \| `solution` \| `software` | all |
| **`updated`** / `date` | ISO 8601 date | all |
| `owner` | string (accountable team/person) | all (recommended) |
| `version` | semver | AD/EA/SAD/HLD |
| `domain` | string | solution/software |
| `conforms-to` | list of standard IDs | all (recommended) |
| `satisfies` | list of `F.xx`/`Q.xx` | HLD/SD/SAD/ADR |
| `complies-with` | list of `PR.xx` | solution/software docs & ADRs |
| `realizes-views` | list of `V-*` | HLD/SD |
| `realizes-capabilities` | list of capability IDs | SAD |
| `security-reviewed` / `cost-reviewed` | boolean | HLD/SAD |
| `privacy-reviewed` | `true` \| `false` \| `n/a` | HLD/SAD |
| `source` | `designed` \| `recovered`/`traced` | AD/HLD/SD/SAD (As-Is vs To-Be) |
| `derivation` | `forward` \| `recovered` | ADR (retroactive vs decided-now) |
| `api-spec` | path to OpenAPI/AsyncAPI/proto/SDL | SD |
| `derived-from-rfc` | `RFC-NNNN` | ADR |
| `resulting-adr` | `ADR-NNNN` | RFC |
| `format` | `house` \| `default` | user stories |
| `epic` | `EP-NNN` or house epic key | user stories |
| `ac-style` | `gherkin` \| `checklist` | user stories |
| `supersedes` / `superseded-by` | `ADR-NNNN` | ADR |

The folder layout these live in, and the README manifest that indexes them, are defined in
`references/repository-structure.md`. For **user stories and acceptance criteria**, detect and
conform to the organisation's house format first (`references/business-analysis.md` §2); the
`US-NNN` scheme and the fields above are only the fallback when no house convention exists.

**House conventions override these defaults.** Companies have their own mandatory sections,
front-matter fields, ID schemes and per-type formats — for *every* document type. Detect them
(`tools/detect_doc_conventions.py` → `house-profile.yaml`), conform to them, and let CI enforce
them (`arch_lint.py --house`). The schema above is the default contract used only where no
house convention exists. See `references/house-style.md`.

## 3. ADR — the Nygård format

One decision per file: `decisions/ADR-NNNN-slug.md`. The body has exactly these
sections, in order. Resist adding ceremony; the power is in the consistency. This
is **MADR 4.0.0-compatible** — the file name (`NNNN-kebab-title`), the `docs/decisions/`
location, the four-state lifecycle, and the immutability rule all match the MADR
community standard, and the optional MADR sections (decision drivers, considered
options, pros/cons, confirmation) can be added when a decision needs them. Keep
`status` to the bare state identifier — no link, no prose (MADR 4.0 rule).

```
# ADR-0007: Use a file-based event bus between analysis stages

## Status
Accepted

## Context
The forces at play — technical, project, organisational — that make a decision
necessary. State the constraints and the drivers (by ID) honestly, including the
ones that push the other way. A reader should understand the problem before
seeing the answer.

## Decision
"We will ..." — active voice, one clear choice. What we are doing, not a menu of
options. If alternatives were seriously weighed, name them in one line each and
say why they lost; keep it tight.

## Consequences
What becomes true after this decision — the new context, good and bad. List the
positive outcomes and, just as plainly, the costs, risks, and follow-on work it
forces. (This is the right home for Cambridge-style trade-off and risk notes if
you want them: "improves X, but reduces Y by ~Z%".)
```

### Status lifecycle
`proposed` → `accepted` → (`deprecated` | `superseded`). Also `rejected` for a
proposal that was considered and declined (keep it — the road not taken is
valuable).

- A new ADR starts `proposed` (or `accepted` if the team already agreed).
- When one ADR replaces another: the new one sets `supersedes: ADR-XXXX` and its
  Status notes "Supersedes ADR-XXXX"; the old one's `status` becomes `superseded`
  with `superseded-by: ADR-YYYY` and a Status line pointing forward. **Update both
  files** — a one-way link is a trap.
- Never delete an ADR. History is the point.

## 4. The decision log (`decisions/README.md`)

A single table indexing every ADR so an agent gets the whole decision landscape
in one read. One row per ADR, newest at the bottom (append-only feel, sorted by
ID). Columns: ID · Title · Status · Date · Summary (one line). Update it on every
ADR add or status change. Template: `assets/templates/decision-log.md`.

## 5. The `ARCH-REF:` code marker

Link enacted decisions back to their record at the code site, in the language's
comment syntax:

```
// ARCH-REF: ADR-0007 (docs/architecture/decisions/ADR-0007-event-bus.md)
# ARCH-REF: ADR-0007 — file-based bus; do not switch to shared memory here
<!-- ARCH-REF: SD-rendering -->
```

- Marker is always the literal token `ARCH-REF:` followed by one ID.
- Place it where a decision is **enacted or could be violated** (a boundary, an
  interface, a deliberately non-obvious mechanism) — not on every line, not as
  decoration. The test: would a future editor be at risk of unknowingly breaking
  the decision here? If yes, mark it.
- One marker can carry a short reminder of the constraint after an `—`.

## 6. Grep patterns these conventions enable

State the convention so the payoff is obvious; an agent can:

```bash
# Every ADR touching a component
grep -rl "affects:.*rendering" docs/architecture/decisions/

# All accepted decisions
grep -rl "^status: accepted" docs/architecture/decisions/

# All enterprise- (or solution-) level decisions
grep -rl "^level: enterprise" docs/architecture/decisions/

# Which decisions satisfy a driver
grep -rl "satisfies:.*Q.02" docs/architecture/

# Everywhere a decision is enacted in code
grep -rn "ARCH-REF: ADR-0007" src/

# The full decision landscape, fast
sed -n '/^|/p' docs/architecture/decisions/README.md
```

If a new field would be useful to filter on, add it to front-matter rather than
burying the fact in prose — prose is for humans, front-matter is for agents.

## 7. Style

- Imperative, concrete, short. A doc nobody updates is a liability.
- Prefer linking by ID over restating. Single source of truth per fact.
- Date everything you change (`date:` / `updated:`).
- Diagrams live inside the doc they explain, not in a separate gallery.
