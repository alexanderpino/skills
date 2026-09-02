<!-- FALLBACK RENDERING. bundle.json is the source of truth; emit.py produces this
     view automatically. Use this template only when you cannot run the scripts. -->

# {KEY} — {Title}

## Why / What
<!-- ≤ 120 words. The outcome and who it is for. Assume the reader knows the
     product. No implementation. -->

## Acceptance criteria
<!-- 2–7 rules. Each rule gets ≥1 concrete example, including the boundary. -->

**AC1 — {rule}**
- {example → expected outcome}
- {boundary example → expected outcome}

**AC2 — {rule}**
- {example → expected outcome}

## Non-goals
- {explicitly out of scope, with follow-up ticket if one exists}

## Technical notes
<!-- ≤ 200 words. What changes, where, what was decided and why, what is risky.
     Every path cited. Delete anything a colleague already knows. -->

Change surface: `repo/path:line (symbol)`, …
Contracts: `repo/openapi.yaml` — additive only; consumed by `web@1.4`.

**Decisions**
- D1 {question} → **{choice}**. {one-line rationale}.

**Risks**
- R1 {risk} → {mitigation}

## Open questions
- Q1 {question} — owner: {name} — blocking: yes/no

## Subtasks
| # | Title | Repo | Covers | Depends on | Est |
|---|-------|------|--------|------------|-----|
| S1 | {title} | {repo} | AC1 | — | 0.5d |

## Non-functional
<!-- Give a number or write "unchanged". Do not leave blank. -->
Performance: · Concurrency: · Failure: · Data: · Security: · Observability: ·
Accessibility: · i18n: · Compatibility:
