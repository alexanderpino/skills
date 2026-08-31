---
description: Run a durable, multi-agent mission control loop for large migrations
argument-hint: <task or 'help'>
---

This command is the entry point to the `mission-control` skill. Read its SKILL.md now.

Task:

$ARGUMENTS

If the task above is exactly `?` or `help` (or if no task is provided), do NOT initialize the mission-control loop. Instead, read `SKILL.md` and output a detailed, user-facing guide on how to use `/mission-control`. Explain:
1. What it does (durable state, crash recovery, private sandboxes).
2. When to use it (massive, repository-wide migrations) vs. when not to (small bug fixes).
3. The general lifecycle (Architect -> Scout -> Implementer -> Verification/Gauntlet -> Merge).
4. Basic setup and resume commands (e.g., how it recovers from failure).
Then stop.

Otherwise, proceed with Phase 0 and Phase 1 as described in SKILL.md:
1. Ensure the user has confirmed running a massive task.
2. Initialize the target repository state.
3. Spawn the Architect to decompose the backlog and start the continuous routing loop.