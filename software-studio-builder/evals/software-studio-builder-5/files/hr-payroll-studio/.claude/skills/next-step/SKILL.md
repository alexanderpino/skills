---
name: next-step
description: "Names the one next step for this HR Payroll Studio project from the workflow catalog and the artifacts on disk. Use when the user asks what to do next or is stuck."
argument-hint: "[no arguments]"
user-invocable: true
allowed-tools: Read, Glob, Grep, Bash(python3 .claude/scripts/resolve_config.py*), Bash(python3 .claude/scripts/artifact_check.py*)
---

# /next-step

1. Run `python3 .claude/scripts/resolve_config.py --keys project.stage,modes.workflow,modes.rigor`.
2. Run `python3 .claude/scripts/artifact_check.py --phase <project.stage>` (all phases if
   the stage is unset).
3. Read `production/session-state/active.md` if it exists — work in progress beats a new step.

Decide from the rows (the helper observes, you judge):

- The first row with `expected=yes status=MISSING` in the current phase is the next step:
  name its `/command`, its owner and the artifact it produces.
- Every `expected=yes` row PRESENT: suggest `/gate-check <next phase>`.
- Rows with `status=NOT_ASSESSED` are named as such — never read as done.
- `expected=later` rows are mentioned once: "not asked for at modes.workflow=<level>".

## Return

Answer in at most six lines. End with `NEXT: /<command> — <why>` or
`NEXT: NOT ASSESSED — <why the state could not be read>`.
