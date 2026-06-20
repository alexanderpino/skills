---
id: RFC-NNNN            # 4-digit, zero-padded; shares the number space intent of its ADR
title: <short noun phrase>
status: draft           # draft | in-review | accepted | rejected | withdrawn
level: software         # enterprise | solution | software
date: <YYYY-MM-DD>
author: <name>
reviewers: [<who>]      # affected teams / domain experts
board-review: false     # true if it needs Architecture Board / ARB approval
resulting-adr:          # set to ADR-NNNN once approved
affects: [<component/area>]
satisfies: [<F.xx>, <Q.xx>]
complies-with: [<PR.xx>]   # enterprise principles it must honour
---

# RFC-NNNN: <title>

> A proposal open for comment. It **decides nothing yet** — on approval it becomes
> ADR-NNNN (see `references/governance.md`). Keep it readable in one sitting.

## Summary
One paragraph: what is being proposed and why it matters now.

## Problem & context
The forces at play, the drivers (cite `B/F/Q` IDs), constraints, and the enterprise
principles (`PR.xx`) this must respect. State the problem neutrally.

## Proposal
The recommended approach, in enough detail to evaluate. What changes, and where.

## Considered options
Genuine alternatives, each with a one-line trade-off and why it is/isn't preferred.
- **Option A (recommended)** — <why>
- **Option B** — <why not>
- **Option C / do nothing** — <why not>

## Impact
Quality attributes (ISO 25010), security (threat surface), cost (FinOps), affected
systems/teams, migration, and backward compatibility.

## Open questions
What still needs deciding or input from reviewers.

## Decision
> Filled in at the end of review.
- **Outcome:** accepted / rejected — by <Architecture Board / reviewers> on <date>.
- **Resulting ADR:** ADR-NNNN (if accepted).
