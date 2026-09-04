---
# --- okf v0.2, written by tools/okf_apply.py -----------------------
type: Evals
title: terrain-architect evals
description: How the capability and trigger evals are structured and what each axis is meant to probe.
tags: [terrain, evals]
status: stable
generated: { by: process:claude-code, at: 2026-07-29T13:19:50+02:00 }
# --- end okf v0.2 ----------------------------------------------------
---
# terrain-architect evals

A measurable definition of "authority" for this skill: not "does it sound expert",
but "does it hold the disciplines the skill exists to enforce". Every eval is
objectively checkable, so a regression shows up as a dropped pass, not a vibe.

## The seven axes

| Axis | File | What it proves |
|---|---|---|
| **Attribution & tier discipline** | `evals.json` (ids 1–3, 38–39) | Cites the right source, refuses to fabricate, marks P/F/L/? honestly. This is the skill's founding purpose — a fabricated citation is the one defect it exists to prevent. ⚠️ Ids 38–39 close a hole the Maintenance rule below had already forbidden: `12`'s glacial half and `28` shipped carrying only ids 36–37, on another axis, so nothing checked the citation split that each of those chapters' own provenance sections spends its length on. |
| **Diagnosis** | `evals.json` (ids 4–6, 18, 23, 28, 32, 34) | Turns a symptom into mechanism → minimal fix from the failure catalogue (`09`), including planetary seams, aeolian no-ops, and relief-representation failures. |
| **Design / ordering** | `evals.json` (ids 7–9, 13–14, 16–17, 26–27, 29, 36–37) | Covers scale-based erosion, Legal Order, named archetypes, runtime substrate, materials, planetary regimes, viewing envelopes, and layer-aware scatter. |
| **Trap-resistance** | `evals.json` (ids 10–12, 15, 25, 33, 35) | Refuses landform-as-algorithm and proprietary-internal fabrication; catches `normalize`, mask-semantics, and branded-node attribution defects. |
| **Owned implementation** | `evals.json` (ids 19–22, 24) | Converts pre-grounded behavior, field contracts and independent oracles into engine-owned CPU/GPU code; covers the complete generator, grounding decisions, wind-field implementation, and long-tail regime runtime contracts. |
| **Review** | `evals.json` (ids 30–31) | Hands the skill someone else's design and asks what is wrong with it — a different act from diagnosing a symptom you were handed. ⚠️ This axis existed in `evals.json` before it existed here: the validator checked only that every *required* axis was used, never that a declared axis was in the vocabulary, so `review` went undeclared and a typo would have passed too. Both halves are now checked. |
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

⚠️ **This rule was stated here and then not followed, twice.** `12`'s glacial half and `28` both
arrived with a design eval and no attribution eval — the axis the rule names first, and the axis
those two chapters most need, since each spends a long provenance section splitting a graphics
citation from the physics under it (`12`: Argudo 2020 vs Glen 1955 vs Halfar's exact solution) or
declaring that no single paper covers the mechanism at all (`28`: glacial-flour turquoise). Ids 38
and 39 close it. Nothing enforces the rule itself — `validate.py` checks the *vocabulary* and the
coverage floor, and `test_audit_drift.py::test_the_eval_readme_axis_table_matches_evals_json`
checks that the table above still lists every id — so a new chapter with no attribution eval is
still caught only by a reader. When you add one, put its id in the table row in the same commit.
