---
name: functional-spec
description: "Section-by-section functional spec for one module. Use when a module needs its requirements written or revised."
argument-hint: "<module>"
user-invocable: true
allowed-tools: Read, Glob, Grep, Write, Edit, AskUserQuestion, Agent, Bash(python3 .claude/scripts/resolve_config.py*), Bash(python3 .claude/scripts/artifact_check.py*)
---

# /functional-spec

Section-by-section functional spec for one module. Use when a module needs its requirements written or revised.

**Owner:** `business-analyst` — for specialist depth, spawn it with the Agent tool (subagent_type: `business-analyst`) and pass the documents it needs by section.

## Before you start

Run `python3 .claude/scripts/resolve_config.py --keys modes.workflow,modes.docs_density,modes.review_mode,stack.name`. Read `production/session-state/active.md` if it exists. A `notes:` line is reported to the user, never ignored.

## Phase 1 — Gather context

Read the product vision and related specs by section.

## Phase 2 — Draft each section with the user

Draft each section with the user.

## Phase 3 — Review

Run PD-SPEC-REVIEW.

## Output

`docs/specs/<module>.md`, from the template `.claude/docs/templates/functional-spec.md` (sections: Overview; Users and Roles; Detailed Rules; Data; Edge Cases; Dependencies; Configurable Parameters; Acceptance Criteria). Draft one section at a time; at `modes.docs_density: terse` keep each section to its essentials.

## Review

Gates: `PD-SPEC-REVIEW`. With `modes.review_mode` `full` run every gate; `lean` only the gates marked `lean: yes` in `.claude/docs/gates.md`; `solo` none — and the report then says `Review: skipped — review_mode=solo`. Spawn each gate's owner (see `.claude/docs/gates.md`) with the gate file and the draft; read the verdict token on the first line of its answer.

## Collaboration

Ask every question in one round, each with a recommended answer. Show the draft before writing. Ask "May I write this to `docs/specs/<module>.md`?" and write only on a yes. Then append one line to `production/session-state/active.md`.

## Return

End with `FUNCTIONAL-SPEC: <verdict>` — one of COMPLETE / PARTIAL — or `NOT ASSESSED — <which input was missing or unreadable>`. A step that did not run is named in the report, never left out. Then name the one next step (`/next-step` decides when unsure).
