---
id: ADR-NNNN            # 4-digit, zero-padded, never reused
title: <short noun phrase, e.g. Use a file-based event bus>
status: proposed        # proposed | accepted | rejected | deprecated | superseded
level: software         # enterprise | solution | software — the altitude of the decision
date: <YYYY-MM-DD>      # decided / last status change
derivation: forward     # forward (decided now) | recovered (retroactive ADR reconstructed from existing code — methods.md §8)
owner: <accountable person/team>
deciders: [<who>]       # optional; the Architecture Board for significant decisions
derived-from-rfc:       # optional: RFC-NNNN this decision came from (governance.md)
tags: [<lowercase>, <topics>]   # optional, for discovery
affects: [<component>, <area>]  # what this decision touches
satisfies: [<F.xx>, <Q.xx>]     # PRD driver IDs this serves
complies-with: [<PR.xx>]        # enterprise principle IDs (for solution/software ADRs)
supersedes:             # optional: ADR-XXXX, if it replaces another
superseded-by:          # optional: set when this one is replaced
---

# ADR-NNNN: <title>

## Status
<Proposed | Accepted | Rejected | Deprecated | Superseded>
<!-- If superseding/superseded, note it here too, e.g.
     "Accepted — supersedes ADR-0003" or "Superseded by ADR-0011". -->

## Context
The forces at play that make a decision necessary: technical constraints, the
drivers involved (cite by ID, e.g. F.01, Q.02), project/organisational pressures,
and the tensions pulling in different directions. State the problem honestly and
neutrally — a reader should grasp the situation before seeing the answer. Don't
describe the solution here.

## Decision
"We will <do X>." One clear choice, in active voice — not a menu. If real
alternatives were weighed, name them briefly and say why each lost:
- <Alternative A> — rejected because <reason>.
- <Alternative B> — rejected because <reason>.

## Consequences
What becomes true once this decision is in effect — the new context, good and bad.

**Positive**
- <benefit / capability unlocked>

**Negative / costs / risks**
- <cost, risk, new obligation, or follow-on work this forces>

**Trade-offs (optional, quantify where possible)**
- <quality A> vs <quality B>: <e.g. "improves throughput ~15%, adds I/O latency on
  small inputs">.

<!-- OPTIONAL — MADR 4.0.0 superset fields. Add any of these only when the decision
     genuinely needs them; omit to stay lean (pure Nygård). See references/standards.md.

## Decision drivers
- <driver / force, e.g. Q.02 overhead budget>

## Considered options
- <Option A>
- <Option B>

## Pros and cons of the options
### <Option A>
- Good, because <…>
- Bad, because <…>

## Confirmation
<How compliance with this decision is checked — test, review, fitness function.>

## More information
<Links, related ADRs, follow-up actions, evidence.>
-->

<!-- Enact this decision in code with a comment at the site:
     // ARCH-REF: ADR-NNNN (docs/architecture/decisions/ADR-NNNN-slug.md)
     Then add a row to decisions/README.md. -->
