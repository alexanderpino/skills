# Measuring whether this skill triggers

Trigger accuracy is worth measuring, but the stock `skill-creator` loop
(`scripts/run_loop.py` → `run_eval.py`) measures something narrower than
"does the skill trigger", and the difference is large enough to invert the
conclusion. Read this before trusting a trigger score.

## What the stock harness measures

Two properties of `run_single_query`, both visible in its source:

1. **Only the first tool call counts.** If the model's first action is
   anything other than `Skill`/`Read`, the run returns `False` immediately.
   Realistic eval queries name real file paths — the eval-writing guidance
   asks for exactly that — so a sensible agent lists or greps first and is
   scored as "did not trigger" even when it invokes the skill one call later.
2. **The candidate is registered as a slash command** in `.claude/commands/`,
   not as a skill in `.claude/skills/<name>/SKILL.md`. That is a different
   list reaching the model in a different way.

A third problem is the eval author's, not the harness's: if the queries
reference files that do not exist in the scratch project, the model spends
its turn establishing that instead of doing the task.

## What that did to this skill's numbers

Same description, same 20-query eval set (10 should-trigger, 10 near-miss
negatives; both sets half Dutch):

| Harness | precision | recall | accuracy |
|---|---|---|---|
| stock `run_loop` | 100% | 6–11% | 53–56% |
| fixed (skill registration, files present, Skill within first 5 calls) | 100% | 40%* | 70%* |

\* n=1 per query; see the noise warning below.

Four materially different descriptions — including two the loop generated
specifically to be more assertive — all scored within noise of each other on
the stock harness. That is the signature of a measurement ceiling, not of a
description that cannot be improved. Do not let such a loop rewrite the
description: it is fitting to the harness.

## The noise warning

At one run per query the measurement is a coin flip on borderline cases. The
clearest example: `run a gauntlet on docs/getting-started.md ...` — the most
explicit trigger phrase in the set — scored 0.00 at n=1, and a traced re-run
invoked the skill as tool call **#1**. Use at least 3 runs per query, and
treat any single-run result as a hypothesis.

## The fixed measurement script

`gauntlet-loop-workspace/trigger-eval/measure_trigger.py` (not shipped with
the skill; it lives in the eval workspace) registers a real skill, creates
the files the queries mention, counts a trigger when the `Skill` call appears
within the first 5 tool calls, and reports precision/recall/accuracy with a
per-query trigger rate.

```bash
python3 measure_trigger.py eval_set.json description.txt claude-fable-5 3 /tmp/scratch
```

## Variance makes description A/B testing expensive — budget it first

A candidate description written specifically against the observed misses
(naming page/docs artifact classes outright, plus "use this BEFORE editing
anything yourself") measured *worse*: 30% recall against the baseline's 40%,
precision 100% in both. But the interesting part is not the number — it is
that the hit set almost completely swapped. Baseline hit emails, CLI text,
deck narrative, game replays; the candidate hit pricing page, emails,
portfolio, and missed the four the baseline caught. Only one query was stable
across both.

That is variance, not a description effect: at three runs per query the noise
is larger than any difference these candidates produce. Distinguishing two
descriptions reliably would need roughly 10+ runs per query — 200+ `claude -p`
invocations per candidate. **That is a real budget item; agree it before
starting.** This exploration consumed a significant share of a session's
tokens and returned a methodological finding rather than a better description.

Practical guidance:

- Do not change a working description on a difference of one or two queries.
- Measure the *current* description first and keep the number; only chase a
  candidate if you have budget for enough runs to beat the noise.
- Precision is the property worth protecting. Across every configuration
  measured here it stayed at 100% — including all ten hard negatives, four of
  them Dutch. Recall around 40% is the honest current figure.

## What the eval set should contain

- **Positives** across artifact classes (page, docs, copy, emails, deck, CLI
  text, render/visuals), in more than one language, with the two real
  signals: reference material supplied, and an iterate-until-good intent.
- **Negatives that are genuinely hard**: same vocabulary, different intent —
  translation asked to "sound professional", a comparison the user wants as
  analysis only, failing tests dressed up as "make it best-in-class", a quick
  cosmetic tweak. Easy negatives ("write a fibonacci function") measure
  nothing.

Precision has never been the problem for this skill; recall is. When tuning,
watch that the negatives stay at zero — an assertive description that starts
firing on the translation or the analysis-only query has traded away the
thing that was working.
