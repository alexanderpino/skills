---
name: dev-story
description: "Implements one story test-first and reports the evidence. Use when a story is ready to build."
argument-hint: "<story id>"
user-invocable: true
allowed-tools: Read, Glob, Grep, Write, Edit, AskUserQuestion, Agent, Bash(python3 .claude/scripts/resolve_config.py*), Bash(python3 .claude/scripts/artifact_check.py*)
---

# /dev-story

Implements one story test-first and reports the evidence. Use when a story is ready to build.

**Owner:** `backend-engineer` — for specialist depth, spawn it with the Agent tool (subagent_type: `backend-engineer`) and pass the documents it needs by section.

## Before you start

Run `python3 .claude/scripts/resolve_config.py --keys modes.workflow,modes.docs_density,modes.review_mode,stack.name`. Read `production/session-state/active.md` if it exists. A `notes:` line is reported to the user, never ignored.

## Phase 1 — Read the story and its spec sections

Read the story and its spec sections.

## Phase 2 — Write failing tests

Write failing tests.

## Phase 3 — Implement

Implement.

## Phase 4 — Run the tests and record evidence

Run the tests and record evidence.

## Collaboration

Ask every question in one round, each with a recommended answer. Show the draft before writing. Ask "May I write this to `<path>`?" and write only on a yes. Then append one line to `production/session-state/active.md`.

## Return

End with `DEV-STORY: <verdict>` — one of DONE / BLOCKED — or `NOT ASSESSED — <which input was missing or unreadable>`. A step that did not run is named in the report, never left out. Then name the one next step (`/next-step` decides when unsure).
