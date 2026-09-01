---
description: Run an adversarial build-and-judge quality loop to push an artifact to a reference-class standard
argument-hint: <task or 'help'>
---

This command is the entry point to the `gauntlet-loop` skill. Read its SKILL.md now.

Task:

$ARGUMENTS

If the task above is exactly `?` or `help` (or if no task is provided), do NOT initialize the gauntlet loop. Instead, read `SKILL.md` and output a detailed, user-facing guide on how to use `/gauntlet-loop`. Explain:
1. What it does (a quality-maximizing loop, not a correctness loop).
2. The core mechanics (Champion/Challenger regression guard, external Bar, Blind Critics).
3. The economic guardrails (WIP limits, Lane Parking for stalled progress, Mechanical Gates).
4. The setup phase (First Light -> The Contract -> Setting the Bar).
Then stop.

Otherwise, proceed with Phase 0 (First Light) and Phase 1 (The Contract) as described in SKILL.md:
1. Verify version control is clean.
2. Build the thinnest end-to-end artifact (or capture it if it exists).
3. Verify the inspection path.
4. Judge it once to establish the baseline and present the contract.