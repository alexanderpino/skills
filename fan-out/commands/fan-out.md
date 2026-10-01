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

If the task above is exactly `?` or `help`, do NOT start the fan-out loop. Instead, read `SKILL.md` and output a concise, user-facing guide on how to use `/fan-out`, explaining what it does, the difference between `partition` and `compete` modes, the four isolation strategies, and the general lifecycle, then stop.

Before spawning anything:

1. Decide `partition` vs `compete`. If the task doesn't clearly imply one, ask — once,
   briefly. It's the one choice that's expensive to get wrong.
2. Write the allocation plan in `slices.json`: per slice its task and context, what it
   owns (scope), reads, leaves out of scope and must not do, the contracts it provides and
   consumes, its done-when, and an isolation strategy
   (`worktree`, `patch`, `shared`, `read-only`) with one line of reason — decided per lane,
   for this run. Files every lane would touch go under `hotspots`, owned by nobody;
   files nobody may ever write go under `protected`.
3. Run `fanout.py plan` to validate the plan and measure coupling, and merge what it
   flags — or pin a `DEP` edge with a contract the provider can keep. N is an output of
   that analysis, not a number you pick.
4. Write `brief.md` and `rubric.md` in full, then `seal`. Run-wide scope and prohibitions
   go in the brief; everything per lane stays in the plan. If the work has a visual
   surface, the brief must carry the one render recipe every agent uses and the rubric an
   axis that can only be scored from the render — critics judge the rendered thing, never
   a description of it. If it has none, do not invent one.
5. `fanout.py lane` to set up the lanes; every builder's per-agent block comes from
   `fanout.py delta <slice-id>`, never written by hand.

Confirm the slicing and the strategies with the user before spawning if the cut is
non-obvious. Then run the loop — trespass before critics, integration before the fold —
and finish with the fold report.

Do not invoke another user-invoked skill from here, and do not let a builder or critic
invoke one either.
