# terrain-architect evals

A measurable definition of "authority" for this skill: not "does it sound expert",
but "does it hold the disciplines the skill exists to enforce". Every eval is
objectively checkable, so a regression shows up as a dropped pass, not a vibe.

## The six axes

| Axis | File | What it proves |
|---|---|---|
| **Attribution & tier discipline** | `evals.json` (ids 1–3) | Cites the right source, refuses to fabricate, marks P/F/L/? honestly. This is the skill's founding purpose — a fabricated citation is the one defect it exists to prevent. |
| **Diagnosis** | `evals.json` (ids 4–6, 18) | Turns a symptom into mechanism → minimal fix from the failure catalogue (`09`), including planetary seam failures. |
| **Design / ordering** | `evals.json` (ids 7–9, 13–14, 16–17) | Covers scale-based erosion, Legal Order, named archetypes, runtime substrate, materials, and planetary regimes. |
| **Trap-resistance** | `evals.json` (ids 10–12, 15) | Refuses landform-as-algorithm and proprietary-internal fabrication; catches `normalize` and mask-semantics defects. |
| **Owned implementation** | `evals.json` (ids 19–22) | Converts pre-grounded behavior, field contracts and independent oracles into engine-owned CPU/GPU code; covers the complete generator, grounding decisions, and long-tail regime runtime contracts. |
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

First run the repository-local structural check:

`python evals/validate.py`

It validates schemas, IDs, expectation coverage, trigger balance, historical-result arithmetic,
and the links between recorded results and eval definitions. It does not invoke or grade a model.

Model execution uses the external **skill-creator** harness (it provides the executor, grader,
aggregation and viewer):

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

## Historical validation (iteration 1, non-reproducible)

Ran the 6 most discriminating evals (attribution ids 1–3 + trap-resistance ids 10–12)
with-skill vs a no-skill baseline on the same strong model, grading each `expectations`
list per-expectation (binary):

| Eval | with-skill | baseline | Δ |
|---|---|---|---|
| 1 — droplet-erosion citation | 1.00 | 1.00 | 0 |
| 2 — atoll "algorithm" | 1.00 | 0.75 | +0.25 |
| 3 — stream-power solver cite | 1.00 | 0.67 | +0.33 |
| 10 — hoodoo "algorithm" | 1.00 | 0.75 | +0.25 |
| 11 — normalize defect | 1.00 | 0.67 | +0.33 |
| 12 — effect-vs-process mask | 1.00 | 1.00 | 0 |
| **mean** | **1.00** | **0.81** | **+0.19** |

The machine-readable record is `results/iteration-1.json`. The original model identifier,
transcripts, and grader logs were not retained, so this is **historical evidence, not a
reproducible current benchmark**. Preserve it as a record of the run, but do not use it to claim
that a later model or skill revision still achieves these scores. A current release claim
requires a new run with the model identifier, harness revision, transcripts, and per-expectation
grader output retained together.

The baseline is a strong generalist and already gets the well-known facts right (the
droplet-erosion lineage, the effect-vs-process mask distinction). The skill's measurable
lift is exactly on the disciplines it exists to enforce: **explicit tier framing** ("there
is no atoll/hoodoo *algorithm* — it's an L-tier composition", evals 2 & 10), **citation
completeness** (pairing Braun & Willett 2013 with Cordonnier 2016, eval 3), the
**Peytavie-Arches representation warning** for overhanging hoodoos (eval 10), and the
**precise tiling-seam mechanism** behind the normalize defect (eval 11). Result: `1.00`
with-skill (above the `0.85` bar) with a clear positive delta on the attribution and
trap-resistance axes, as specified. The honest read is that the skill's value here is
*discipline and completeness*, not rescuing a weak model — which is the right thing for a
principal-level reference to do.

## Maintenance

When a new process family is added to the skill, add at least one attribution eval (does
it cite the new work at the right tier?) and, if it introduces a failure mode, one
diagnosis eval. Any new implementation path also needs an owned-implementation expectation
covering provenance and an independent oracle. That keeps the "coverage matrix" in the plan
honest: every family has a check that would catch its regression. Run `python evals/validate.py` and the
`reference-impl` pytest suite before changing any verification claim.
