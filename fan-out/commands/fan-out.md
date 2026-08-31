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

If the task above is exactly `?` or `help`, do NOT start the fan-out loop. Instead, read `SKILL.md` and output a concise, user-facing guide on how to use `/fan-out`, explaining what it does, the difference between `partition` and `compete` modes, and the general lifecycle, then stop.

Before spawning anything:

1. Decide `partition` vs `compete`. If the task doesn't clearly imply one, ask — once,
   briefly. It's the one choice that's expensive to get wrong.
2. Propose the slices (or the competing constraints), run `fanout.py plan` to measure the
   coupling between them, and merge what it flags. N is an output of that analysis, not a
   number you pick.
3. Write `brief.md` and `rubric.md` in full, then `seal`. If the work has a visual
   surface, the brief must carry the one render recipe every agent uses and the rubric an
   axis that can only be scored from the render — critics judge the rendered thing, never
   a description of it. If it has none, do not invent one.

Confirm the slicing with the user before spawning if the cut is non-obvious. Then run the
loop and finish with the fold report.

Do not invoke another user-invoked skill from here, and do not let a builder or critic
invoke one either.
