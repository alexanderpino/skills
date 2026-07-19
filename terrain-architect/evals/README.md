# terrain-architect evals

A measurable definition of "authority" for this skill: not "does it sound expert",
but "does it hold the disciplines the skill exists to enforce". Every eval is
objectively checkable, so a regression shows up as a dropped pass, not a vibe.

## The five axes

| Axis | File | What it proves |
|---|---|---|
| **Attribution & tier discipline** | `evals.json` (ids 1–3) | Cites the right source, refuses to fabricate, marks P/F/L/? honestly. This is the skill's founding purpose — a fabricated citation is the one defect it exists to prevent. |
| **Diagnosis** | `evals.json` (ids 4–6) | Turns a symptom into mechanism → minimal fix from the failure catalogue (`09`), one node moved not a rewrite. |
| **Design / ordering** | `evals.json` (ids 7–9) | Picks the erosion backbone by extent, orders the Legal Order, reasons in world units. |
| **Trap-resistance** | `evals.json` (ids 10–12) | Refuses landform-as-algorithm ("the hoodoo algorithm"), catches the `normalize` defect and the effect-vs-process mask confusion. |
| **Triggering** | `trigger-evals.json` | Fires on real terrain-generation prompts and stays quiet on near-misses (DEM plotting, texturing, hiking, geology homework). |

## Passing bar

- **Capability (axes 1–4):** ≥ 0.85 mean `expectations` pass rate with the skill, and a
  **clear positive delta over baseline** on the attribution and trap-resistance axes —
  those are where a strong general model *without* the provenance discipline tends to
  fabricate a plausible citation or invent a "hoodoo algorithm". If the skill doesn't
  move those, it isn't earning its keep.
- **Triggering:** ≥ 0.9 correct fire/no-fire on the held-out split, with the
  should-not-trigger near-misses weighted most (a keyword-matching failure there is the
  expensive kind).

## How to run

Via the **skill-creator** skill's harness (it provides the executor, grader, aggregation
and viewer):

1. **Capability evals** — for each eval in `evals.json`, run one subagent *with* the skill
   and one *baseline* (no skill), save transcripts, then grade each `expectations` list
   with `agents/grader.md`. Aggregate with
   `python -m scripts.aggregate_benchmark <workspace>/iteration-N --skill-name terrain-architect`
   and review with `eval-viewer/generate_review.py` (use `--static` in a headless env).
2. **Triggering evals** — run the description optimiser / trigger check:
   `python -m scripts.run_loop --eval-set evals/trigger-evals.json --skill-path <this skill> --model <session-model>`.

The scenarios are deliberately answer-shaped (this is an advice/reference skill, not a
file transform), so grading reads the answer text against the `expectations` — an
LLM-graded rubric, not a script. Keep the expectations objective enough that two graders
would agree.

## Maintenance

When a new process family is added to the skill, add at least one attribution eval (does
it cite the new work at the right tier?) and, if it introduces a failure mode, one
diagnosis eval. That keeps the "coverage matrix" in the plan honest: every family has a
check that would catch its regression.
