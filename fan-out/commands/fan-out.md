---
description: Fan one task out to parallel sub-agents judged by independent critics
argument-hint: <task>
---

This command is the only entry point to the `fan-out` skill. Read its SKILL.md now and
follow the loop as written — in particular the shared-block ordering and the
pathfinder-before-parallel spawn sequence, which exist for prompt-caching reasons
documented in `references/prompt-caching.md`.

Task:

$ARGUMENTS

Before spawning anything:

1. Decide `partition` vs `compete`. If the task doesn't clearly imply one, ask — once,
   briefly. It's the one choice that's expensive to get wrong.
2. Propose the slices (or the competing constraints), run `fanout.py plan` to measure the
   coupling between them, and merge what it flags. N is an output of that analysis, not a
   number you pick.
3. Write `brief.md` and `rubric.md` in full, then `seal`.

Confirm the slicing with the user before spawning if the cut is non-obvious. Then run the
loop and finish with the fold report.

Do not invoke another user-invoked skill from here, and do not let a builder or critic
invoke one either.
