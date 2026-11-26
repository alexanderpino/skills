---
name: business-rules
description: "Writes or updates a versioned payroll rule catalog with effective dates and sources. Use when a calculation or statutory rule is added or changes."
argument-hint: "<area>"
user-invocable: true
allowed-tools: Read, Glob, Grep, Write, Edit, AskUserQuestion, Agent, Bash(python3 .claude/scripts/resolve_config.py*), Bash(python3 .claude/scripts/artifact_check.py*)
---

# /business-rules

Writes or updates a versioned payroll rule catalog with effective dates and sources. Use when a calculation or statutory rule is added or changes.

**Owner:** `payroll-rules-specialist` — for specialist depth, spawn it with the Agent tool (subagent_type: `payroll-rules-specialist`) and pass the documents it needs by section.

## Before you start

Run `python3 .claude/scripts/resolve_config.py --keys modes.workflow,modes.docs_density,modes.review_mode,stack.name`. Read `production/session-state/active.md` if it exists. A `notes:` line is reported to the user, never ignored.

## Phase 1 — Collect the rule and its legal source

Collect the rule and its legal source.

## Phase 2 — Write formula, inputs and worked examples

Write formula, inputs and worked examples.

## Phase 3 — Compliance review

Run CL-RULE-COMPLIANCE.

## Output

`docs/specs/rules/<area>.md`, from the template `.claude/docs/templates/rule-catalog.md` (sections: Rules; Formulas; Effective Dates; Sources; Worked Examples). Draft one section at a time; at `modes.docs_density: terse` keep each section to its essentials.

## Review

Gates: `CL-RULE-COMPLIANCE`. With `modes.review_mode` `full` run every gate; `lean` only the gates marked `lean: yes` in `.claude/docs/gates.md`; `solo` none — and the report then says `Review: skipped — review_mode=solo`. Spawn each gate's owner (see `.claude/docs/gates.md`) with the gate file and the draft; read the verdict token on the first line of its answer.

## Collaboration

Ask every question in one round, each with a recommended answer. Show the draft before writing. Ask "May I write this to `docs/specs/rules/<area>.md`?" and write only on a yes. Then append one line to `production/session-state/active.md`.

## Return

End with `BUSINESS-RULES: <verdict>` — one of COMPLETE / PARTIAL — or `NOT ASSESSED — <which input was missing or unreadable>`. A step that did not run is named in the report, never left out. Then name the one next step (`/next-step` decides when unsure).
