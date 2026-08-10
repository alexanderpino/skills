# Aim — rounds are experiments, not attempts

The failure this file exists to prevent: a builder gets "the gap", tries
something, a critic looks at what it became. That loop measures everything
*after* the fact and states nothing *before* it — so a round can never be
wrong, only unlucky, and a run of it is indistinguishable from doing things
and hoping for the best. Verdicts tell you where the artifact is; they do not
tell you whether anyone understood why.

The fix is the ordinary shape of an experiment, enforced mechanically:

> **Hypothesis → intervention → measurement → conclusion.**

The loop already had the middle two. `aim` adds the first, and scoring aims
against verdicts adds the last.

## The aim record

Before a round's builder runs, state the bet:

```bash
python3 scripts/gauntlet.py aim --wave 5 --lane layout --dimension visual --round 5 \
    --hypothesis "the CTA reads tight because its padding ignores the 8pt grid;
                  snapping to the grid should close the last minor" \
    --approach "8pt grid padding on hero CTA" \
    --expect-severity none
```

Three parts, each doing distinct work:

- **Hypothesis** — why the gap exists and why this change should close it. If
  you cannot state it, the round is a guess you are about to pay for — which is
  worth knowing *before* the builder runs, not after.
- **Approach** — the intervention, named. This is the retry-prevention key: a
  missed approach goes into a ledger, and no later round quietly tries it again.
- **Expectation** — what the verdict must show if the hypothesis is right:
  `--expect-severity minor|none` and/or `--expect-score N`. This is what makes
  the round falsifiable.

The builder receives the hypothesis and approach as part of its brief — a
builder that knows *why* the change should work builds it better than one that
only knows *what* to change.

## The honesty constraints

Two rules keep the metric from being gamed, both enforced by the script:

1. **The expectation must improve on the last verdict.** An aim the artifact
   has already met is not a bet; allowing it would let a run buy a flattering
   hit rate by aiming at the floor. `aim` reads the log and refuses.
2. **Aim before build.** An expectation written after the verdict is astrology.
   The ordering is the doctrine; `log-round` backs it with a warning on any bar
   round (tier 1 up) that has no aim on record, and `status`, the board and the
   report count unaimed rounds — a round that could not miss, and so could not
   teach.

## Scoring — hit, miss, pending

Every aim is scored against what actually happened:

| Outcome | Meaning |
|---|---|
| **hit** | The verdict met every stated expectation |
| **miss — reverted** | The challenger lost the promotion comparison |
| **miss — fell short** | Promoted, but the verdict did not reach the expectation |
| **pending** | No verdict yet |

`status` prints the hit rate; the board carries it as a tile and per lane card;
the report gets a section titled *"Did the rounds know what they were aiming
at?"* — which is this file's question in one line.

## What the hit rate is for

It is the run's measure of **whether it understands the artifact** — a
different thing from whether the artifact is improving, and the thing whose
absence feels like "doen maar wat".

- **High hit rate, gaps closing** — the run understands the lane. Rounds are
  experiments confirming a working model. Carry on.
- **Low hit rate** (under half, three or more scored aims) — the mental model
  is wrong. More build rounds are more guesses at the same wrong model.
  `status` and `plan` say it directly: **DIAGNOSE FIRST**.
- **High hit rate, gaps *not* closing** — expectations are being met but the
  bar is not getting nearer: the aims are too small, or the remaining distance
  is structural. Aim bigger, or re-cut.

## The diagnosis round

When aims keep missing, the cheap move is a round that changes nothing: one
read-only investigation whose product is a *cause*, not an edit. Give a
fresh-context agent the artifact, the bar, the failed hypotheses from the
ledger, and one question — *why is this dimension not converging?* Its answer
becomes the next aim's hypothesis. Log its cost with
`spend --role diagnostician`.

A diagnosis at the cheap tier costs a fraction of a build round and replaces
the two or three misses that were coming. This is the difference between an
experiment program and trial-and-error: trial-and-error responds to failure
with another trial; an experiment program responds with a better hypothesis.

A cause is also what re-opens parked work: `unshelve` asks for exactly this
kind of new information, and a diagnosis that names why a shelved dimension
stalled is the strongest grounds there are for reinvesting budget in it
(`cost-model.md` §6).

## The failed-approaches ledger

Every missed aim records its approach and how it missed. `plan` prints them
under the lane they belong to:

```
  [layout / visual]  severity minor
      gutter rhythm fixed; hero CTA spacing still tighter than the reference
      tried and missed: "rem-based spacing" (fell short)
      tried and missed: "tighten grid gutters" (reverted)
```

The rule that goes with it: **never re-use a missed approach without a new
reason to believe it.** Retrying a failed approach with no new information is
the purest form of hoping for the best, and it is now visible when it happens.

## Tier 0 aims at the loop, not the artifact

The probe's hypothesis is not about the artifact — it is *"the inspection path
works and the bar is sharp enough for a critic to cut with."* That is why
unaimed-round accounting starts at tier 1: round zero is the experiment that
validates the apparatus, and its expectations live in the escalation gates
(`cost-model.md` §1) rather than in an aim record.

## What this costs

Nothing but the sentence you were owed anyway. An aim is one command per
round, no model calls. What it buys: misses become information, failed
approaches stop being retried, incomprehension gets named while the budget can
still respond to it — and the report can answer the question a spend of this
size deserves: not only *did it get better*, but *did we know what we were
doing*.
