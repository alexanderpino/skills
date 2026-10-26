---
description: Route to a principal-architect workflow (consult, propose, apply, verify, archive, bootstrap, handoff) — or 'help'
argument-hint: <consult|propose|apply|verify|archive|bootstrap|handoff> <input> — or 'help'
---

This command is the router for the `principal-architect` skill's change workflow. The
skill also triggers on its own whenever work touches structure, boundaries,
interfaces, data, or quality attributes; this command picks the workflow explicitly.

Arguments:

$ARGUMENTS

If the arguments are exactly `?` or `help`, or empty, do NOT start a workflow. Read
`SKILL.md` and the "Change workflow" section in it, then output a short user-facing
guide: what the skill does (living architecture docs as a gate around engineering
work), the lifecycle consult → propose → apply → verify → archive (plus bootstrap for
a repository without docs, and handoff to OpenSpec or spec-kit once a change is decided),
one line per workflow with its command (`/arch-consult`, `/arch-propose`, `/arch-apply`,
`/arch-verify`, `/arch-archive`, `/arch-bootstrap`, `/arch-handoff`),
the fact that `scripts/arch.py` holds the state so work resumes across sessions, and
the triage rule that most changes need little or no documentation. Then stop.

Otherwise the first word names the workflow and the rest is its input. Read
`references/workflows/<workflow>.md` in the skill's directory and follow it step by
step. If the first word is not a workflow name, treat the whole argument as the input
to `consult`.
