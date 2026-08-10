# Pace — where the wall-clock goes, and how to get it back

Cost and speed are different problems. The cost model (`cost-model.md`) makes
calls cheaper or removes them; this file is about finishing sooner. The framing
that keeps the two honest:

> **Speed = quality gained per round × rounds per hour.**

Almost everything that matters lives in the first factor. The canonical run's
own finding — sequential single-owner passes beat parallel fan-out decisively —
is a *speed* finding as much as a quality one: three rounds of six parallel
agents netted half a point with a regression in the middle, so the wall-clock
to reach quality X was *longer* via fan-out, despite more agents running at
once. Working harder ran slower. Everything below is the other kind of gain.

## Measure before tuning

Every ledger record carries a timestamp, so the run can read its own pace with
nothing extra logged. `status` prints it:

```
pace: avg wave 38 min, 1.6 waves/hour · elapsed 4.2 h (active 3.1 h)
  ~3 more wave(s) ≈ 1.9 h at this pace
  stages: build 22 min · judge 11 min · smooth 5 min
```

- A wave's span is first record to last record within that wave. It includes
  the lead agent's own orchestration time between calls — honestly, because
  that time is part of the run. It cannot see the first call's duration, so
  treat these as steering figures, not billing figures.
- **Elapsed vs active** is the first diagnostic: a large gap between them is
  idle time — waiting on a human, on an external system, or on the lead agent —
  and no amount of model tuning recovers it.
- Pass `--seconds` on `log-round` and `spend` when you have real durations, and
  the wave splits into **build / judge / smooth**. That split decides which
  lever below applies: a build-dominated wave and a judge-dominated wave call
  for different fixes.

## 1. Converge in fewer rounds — the lever that dominates

A round costs its calls *and* its latency, so the fastest run is the one that
needs the fewest rounds. Three practices, all already in the doctrine, read
here as speed mechanisms:

- **A sharp bar produces a sharp gap produces a converging round.** Round
  zero's real product is a bar the critic can cut with; a vague verdict at
  round zero predicts slow convergence for the whole run. Fixing the bar is the
  highest-leverage speed work available (`bar-selection.md`).
- **Batch the minors.** One named gap per round keeps gaps attributable, and
  that discipline earns its cost while gaps are `major`. Once a dimension is
  down to `minor` cosmetics, one round per cosmetic is convergence tax: fold
  the critic's second-order NOTES into a single batch brief and close three
  gaps in one round. Attribution matters less there because the champion guard
  catches any regression — that guard is precisely what makes batching safe.
  `plan` suggests this when a dimension sits on a minor.
- **Measure every round, judge on plateau.** An oracle dimension read every
  round costs nothing and shows the plateau the moment it happens — a model is
  then called once, to name why, instead of narrating each measurement
  (`cost-model.md` §5).

## 2. Pipeline, don't fan out

The sequential-beats-parallel finding is about **coupled edits**, not about the
clock. Single ownership serialises *writes*; it does not require the run to sit
idle between stages:

- While lane A's critics judge round N, lane B's builder runs. Builders write
  disjoint paths; critics only read. Nothing about the regression guard or
  critic independence is touched.
- Within one lane the chain is genuinely serial — the next builder needs the
  named gap — so a single-lane wave's floor is build + judge latency. That
  floor is exactly why batching minors (fewer rounds) beats any amount of
  within-lane cleverness.
- The smoother needs the whole artifact, so builders wait on it — but planning,
  oracle measurements and the no-change checks are read-only and run alongside
  it for free.

The distinction to keep: **pipelining overlaps stages of independent work;
fan-out parallelises coupled work.** The first is free speed; the second is the
thing the canonical run showed to be slower and worse.

## 3. Judging strategy — let the revert rate decide

From tier 2 a round runs two critic calls: promotion, then bar-if-promoted.
That conditional is only load-bearing when reverts actually happen. `status`
and `plan` read the recent revert rate and recommend:

| Recent revert rate | Strategy | Why |
|---|---|---|
| ≤ ~15% | **Speculate** — run promotion and bar critics concurrently | The rare wasted bar verdict costs one cheap call; serializing costs every round a critic's full latency |
| mid-range | Keep the serial default | Neither cost dominates |
| ≥ ~35% | **Serialize** — and read the rate itself | Speculative bar verdicts would mostly be discarded, and a rate that high is a ceiling signal (`failure-modes.md`) |

Tiers 0–1 already collapse both questions into one screening call, which is the
fastest shape of all and the reason the probe is quick.

## 4. The cheap path is the fast path

The cost routing in `cost-model.md` §2 is also the latency routing, which is why
"cheaper" and "faster" are mostly the same work:

- The `cheap` tier's verdicts return several times faster than the `high`
  tier's, on top of costing a fifth as much.
- An oracle round has no model latency at all.
- Small prompts are fast prompts: the read-budget and paths-not-contents rules
  (§3) cut time-to-first-token every single call.
- A stable, byte-identical prompt prefix caches — and cache reads are not just
  ~10× cheaper, they stream sooner.
- Screening critics at low effort return faster than deliberating ones; effort
  above `low` on a which-of-two-is-better question buys latency, not accuracy.

## 5. Cut the orchestration idle

On long runs the biggest sink is often nobody's model: it is the time between
calls. `plan`'s output is deliberately a dispatch list — brief builders with
pointer paths and the gap verbatim rather than re-writing each brief as prose,
and dispatch a wave's independent calls in one batch rather than one at a time.
When `status` shows elapsed far above active, this is where it went.

## 6. The paid lever — fast mode, priced

When a deadline genuinely outranks cost, `claude-opus-5` supports
`speed: "fast"` (research preview, Claude API only): roughly 2.5× output speed
at $10/$50 per Mtok — double the standard Opus rate, 10× the cheap tier. Two
rules if a run uses it: re-quote the budget at intake, because every projection
in this skill assumes standard pricing; and buy it for the builder chain on the
critical path, not for critics a cheaper-and-faster tier already serves. This is
the one lever in this file that is "harder" rather than "smarter" — reach for it
last.

## What not to trade away

Speed bought by weakening the guards is negative speed:

- **Nothing is slower than a wave that goes backwards.** The champion guard
  exists because plausible-looking rounds regress; a revert caught costs one
  round, a regression merged costs the waves that built on it. The guard is a
  speed feature.
- Skipping round zero to "get going" trades one cheap round for a run that
  converges slowly against a bar nobody sharpened.
- Collapsing critic calls is a tier/evidence decision (§3), not a default —
  and the blind protocol is never the thing to cut: an unblinded critic drifts
  agreeable, verdicts soften, and the loop runs *longer*.
