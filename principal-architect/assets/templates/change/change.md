---
id: {{id}}
title: {{title}}
status: draft
level: {{level}}             # enterprise | solution | software — the altitude (SKILL.md "Three altitudes")
archetype: {{archetype}}     # the Triage row this change falls under (see "Triage" below)
date: {{date}}
base: {{base}}               # branch this change is compared against
affects: []                  # components/areas this change touches, as ADRs name them in affects:
records: []                  # ADR/RFC ids minted for this change (arch.py record adds them)
conflicts: []                # accepted ADR ids this change contradicts; each must be superseded here
---

# Change: {{title}}

<!-- The planning record of one architecture change. Written by the propose workflow,
     read by apply, verify and archive. Keep it short: it exists so the next session
     (or reviewer) knows what was decided and why without re-deriving it. Every
     section must be filled before `arch.py status` reports the change ready. -->

## Intent
<What changes and why, in two or three sentences. Cite the drivers it serves by ID
(B.xx / F.xx / Q.xx), or say plainly that no driver exists yet and record that as a gap.>

## Evidence
<What you read to know this, separated into what you observed and what you infer:
docs by path or ID, code as path:line, tests, configs, git history. Include the
`arch.py consult` result you acted on.>

## Decisions on record
<Every accepted ADR that binds this change, from `arch.py consult`. For each, one line:
honoured as is, or contradicted. A contradicted ADR goes in `conflicts:` and needs a
superseding record in this change (`arch.py record adr --supersedes ADR-NNNN`). If no
decision binds the change, say so and say how you checked.>

## Triage
<The altitude and the archetype, with the row of the SKILL.md Triage table that put it
there. Then the artifacts that row requires and, just as plainly, the ones it does not
require, one line of reason each. This is what keeps the change from over-documenting.>

## Assumptions and gaps
<Everything you could not derive from evidence and did not ask about, each one visible
and owned. Write "None" only when that is true.>
