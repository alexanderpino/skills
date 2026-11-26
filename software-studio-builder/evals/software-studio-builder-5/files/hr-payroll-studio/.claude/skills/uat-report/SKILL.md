---
name: uat-report
description: "Runs and records user acceptance testing for a release candidate. Use when a release candidate is ready for business acceptance."
argument-hint: "[no arguments]"
user-invocable: true
allowed-tools: Read, Glob, Grep, Write, Edit, AskUserQuestion, Agent, Bash(python3 .claude/scripts/resolve_config.py*), Bash(python3 .claude/scripts/artifact_check.py*)
---

# /uat-report

Runs and records user acceptance testing for a release candidate. Use when a release candidate is ready for business acceptance.

**Owner:** `qa-lead` — for specialist depth, spawn it with the Agent tool (subagent_type: `qa-lead`) and pass the documents it needs by section.

## Before you start

Run `python3 .claude/scripts/resolve_config.py --keys modes.workflow,modes.docs_density,modes.review_mode,stack.name`. Read `production/session-state/active.md` if it exists. A `notes:` line is reported to the user, never ignored.

## Phase 1 — Plan scope with business users

Plan scope with business users.

## Phase 2 — Execute UAT scripts

Execute UAT scripts.

## Phase 3 — Record results and defects

Record results and defects.

## Phase 4 — Sign-off

Run QL-UAT-SIGNOFF.

## Output

`production/qa/uat-<date>.md`, from the template `.claude/docs/templates/uat-report.md` (sections: Scope; Participants; Results; Defects; Sign-off). Draft one section at a time; at `modes.docs_density: terse` keep each section to its essentials.

## Review

Gates: `QL-UAT-SIGNOFF`. With `modes.review_mode` `full` run every gate; `lean` only the gates marked `lean: yes` in `.claude/docs/gates.md`; `solo` none — and the report then says `Review: skipped — review_mode=solo`. Spawn each gate's owner (see `.claude/docs/gates.md`) with the gate file and the draft; read the verdict token on the first line of its answer.

## Collaboration

Ask every question in one round, each with a recommended answer. Show the draft before writing. Ask "May I write this to `production/qa/uat-<date>.md`?" and write only on a yes. Then append one line to `production/session-state/active.md`.

## Return

End with `UAT-REPORT: <verdict>` — one of ACCEPTED / CONCERNS / REJECTED — or `NOT ASSESSED — <which input was missing or unreadable>`. A step that did not run is named in the report, never left out. Then name the one next step (`/next-step` decides when unsure).
