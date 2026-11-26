---
name: architecture-decision
description: "Records one architecture decision as an ADR with options and consequences. Use when a technical decision needs recording."
argument-hint: "<decision>"
user-invocable: true
allowed-tools: Read, Glob, Grep, Write, Edit, AskUserQuestion, Agent, Bash(python3 .claude/scripts/resolve_config.py*), Bash(python3 .claude/scripts/artifact_check.py*)
---

# /architecture-decision

Records one architecture decision as an ADR with options and consequences. Use when a technical decision needs recording.

**Owner:** `lead-engineer` — for specialist depth, spawn it with the Agent tool (subagent_type: `lead-engineer`) and pass the documents it needs by section.

## Before you start

Run `python3 .claude/scripts/resolve_config.py --keys modes.workflow,modes.docs_density,modes.review_mode,stack.name`. Read `production/session-state/active.md` if it exists. A `notes:` line is reported to the user, never ignored.

## Phase 1 — Frame the decision

Frame the decision.

## Phase 2 — Compare options

Compare options.

## Phase 3 — Record the decision

Record the decision.

## Phase 4 — Review

Run TD-ADR-REVIEW.

## Output

`docs/architecture/adr-NNNN-<slug>.md`, from the template `.claude/docs/templates/adr.md` (sections: Status; Context; Options; Decision; Consequences). Draft one section at a time; at `modes.docs_density: terse` keep each section to its essentials.

## Review

Gates: `TD-ADR-REVIEW`. With `modes.review_mode` `full` run every gate; `lean` only the gates marked `lean: yes` in `.claude/docs/gates.md`; `solo` none — and the report then says `Review: skipped — review_mode=solo`. Spawn each gate's owner (see `.claude/docs/gates.md`) with the gate file and the draft; read the verdict token on the first line of its answer.

## Collaboration

Ask every question in one round, each with a recommended answer. Show the draft before writing. Ask "May I write this to `docs/architecture/adr-NNNN-<slug>.md`?" and write only on a yes. Then append one line to `production/session-state/active.md`.

## Return

End with `ARCHITECTURE-DECISION: <verdict>` — one of ACCEPTED / PROPOSED — or `NOT ASSESSED — <which input was missing or unreadable>`. A step that did not run is named in the report, never left out. Then name the one next step (`/next-step` decides when unsure).
