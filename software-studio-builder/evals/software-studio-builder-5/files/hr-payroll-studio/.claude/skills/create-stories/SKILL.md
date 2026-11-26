---
name: create-stories
description: "Breaks an approved functional spec into stories with acceptance criteria. Use when a spec is approved and work must be planned."
argument-hint: "<spec path>"
user-invocable: true
allowed-tools: Read, Glob, Grep, Write, Edit, AskUserQuestion, Agent, Bash(python3 .claude/scripts/resolve_config.py*), Bash(python3 .claude/scripts/artifact_check.py*)
---

# /create-stories

Breaks an approved functional spec into stories with acceptance criteria. Use when a spec is approved and work must be planned.

**Owner:** `business-analysis-lead` — for specialist depth, spawn it with the Agent tool (subagent_type: `business-analysis-lead`) and pass the documents it needs by section.

## Before you start

Run `python3 .claude/scripts/resolve_config.py --keys modes.workflow,modes.docs_density,modes.review_mode,stack.name`. Read `production/session-state/active.md` if it exists. A `notes:` line is reported to the user, never ignored.

## Phase 1 — Read the spec

Read the spec.

## Phase 2 — Slice into stories

Slice into stories.

## Phase 3 — Write acceptance criteria

Write acceptance criteria.

## Output

`production/stories/<id>.md`, from the template `.claude/docs/templates/story.md` (sections: Story; Acceptance Criteria; Spec References; Test Evidence). Draft one section at a time; at `modes.docs_density: terse` keep each section to its essentials.

## Collaboration

Ask every question in one round, each with a recommended answer. Show the draft before writing. Ask "May I write this to `production/stories/<id>.md`?" and write only on a yes. Then append one line to `production/session-state/active.md`.

## Return

End with `CREATE-STORIES: <verdict>` — one of COMPLETE / PARTIAL — or `NOT ASSESSED — <which input was missing or unreadable>`. A step that did not run is named in the report, never left out. Then name the one next step (`/next-step` decides when unsure).
