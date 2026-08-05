# Example run, annotated

One compact run, end to end. The artifact is deliberately small — a landing-page
hero section — so the machinery is visible. A real run has more lanes and more
waves; the shape is identical.

## The request

> "Make the hero section of my site actually good. Here are three sites I think
> are exceptional: [links]. Don't stop after one pass — keep going."

"Keep going" with a supplied comparator: a gauntlet. Correctness is not the
problem (the page renders); the ceiling is.

## Contract (proposed in one block, confirmed by the user)

```
GOAL     Hero section holds up in a blind comparison against the three references
BAR      visual: screenshots of the three references at 1440×900 → gauntlet/bar/
         perf: LCP < 1.5s, CLS < 0.1 (Lighthouse, throttled) → gauntlet/bar/perf.md
INSPECT  Playwright screenshot harness at 1440×900 + Lighthouse CI, both verified
LANES    typography, layout-and-spacing, imagery  (proposed; may re-cut)
STOP     bar-met N=2, clean-streak N=2, budget 8 waves, judgment armed
BUDGET   8 waves ≈ 3 lanes × ~2 rounds × 3 calls ≈ 40–60 subagent invocations
AUTONOMY Unattended; workbench.html updated per round
BENCH    gauntlet/workbench.html
```

```bash
python3 scripts/gauntlet.py init --lanes typography,layout,imagery \
    --dimensions visual,perf --budget-waves 8
```

Working tree was dirty → asked the user to commit first. Bar screenshots frozen
into `gauntlet/bar/`.

## Round zero

One build round on `typography` only, then one critic. The critic verdict came
back *"B's type hierarchy is stronger"* with no measurable specifics — too soft.
Diagnosis: the bar screenshots included whole pages, so the critic judged
everything at once. Fix: cropped bar shots to the hero region only. Second
round-zero verdict: *"A (ref): headline tracking is optically compensated at
display size; B renders default tracking — visibly looser at 96px."* Actionable.
Wave 1 may start.

## Wave 1 (bootstrap — no champions exist yet)

Three builders in parallel, disjoint file ownership. No promotion comparisons
(first round of each lane); one bar comparison per lane per dimension.

```bash
python3 scripts/gauntlet.py log-round --wave 1 --lane typography --dimension visual \
  --round 1 --mode blind --winner other --margin decisive --severity major \
  --gap "no optical tracking compensation at display sizes" \
  --evidence gauntlet/shots/w1-typo-ab.png --critic-framing default
```

Similar records for `layout` (major: "reference uses a 12-col grid with content
capped at 7 cols; ours spans full width") and `imagery`. Perf dimension logged
via rubric mode (a Lighthouse number cannot be blinded):

```bash
python3 scripts/gauntlet.py log-round --wave 1 --lane imagery --dimension perf \
  --round 1 --mode rubric --winner other --margin clear --severity major \
  --gap "hero image 1.8MB uncompressed; LCP 3.4s vs 1.5s budget" \
  --evidence gauntlet/bench/w1.json
```

Smoother pass: found one seam (typography's new type scale collided with
layout's spacing tokens), fixed, logged.

## Wave 2 — a revert

`layout`'s builder closed the grid gap but the challenger *lost* the promotion
comparison: the critic (blind, challenger vs champion) found the new grid
introduced horizontal overflow at 1280px. Reverted to the champion ref; the
critic's reasoning — not the builder's — went into round 3.

```bash
python3 scripts/gauntlet.py log-round --wave 2 --lane layout --dimension visual \
  --round 2 --mode champion --winner other --margin clear --action reverted \
  --champion-ref 4f2a91c --evidence gauntlet/shots/w2-layout-champ.png
```

A losing round is data: the next builder got "close the grid gap *without*
breaking 1280px" and succeeded in round 3.

## Wave 3 — a re-cut

The smoother reported the same seam twice running: typography and layout kept
fighting over vertical rhythm. Per `decomposition.md`, a recurring seam means the
cut is wrong. Merged the two lanes into `type-and-layout` between waves; noted in
the workbench that streak counters for both reset deliberately.

## Waves 4–6

`type-and-layout` visual: won blind rounds in waves 5 and 6 → bar-met streak 2 →
dimension retired. Perf: LCP down to 1.4s → severity `none` twice → clean-streak
retired. Lane retired. `imagery` visual kept losing on margin `thin` with gaps
getting cosmetic ("grain texture in ref reads intentional; ours reads like
compression").

## The stop

`status` at the wave-6 boundary: one lane fully retired; `imagery` showing
margins thin for three rounds and one revert — the judgment signal. Stopped on
judgment with evidence, two waves under budget, rather than spending them on a
lane at its ceiling.

```
STOP CONDITIONS FIRED / SIGNALLED:
  - judgment signal: revert rate over 50% in recent rounds — likely at the ceiling
```

## The report (abridged)

- Bar: three reference heroes (visual) + LCP/CLS budgets (perf); never moved
- `type-and-layout`: retired, 9 bar rounds, 1 revert, 1 re-cut
- `imagery`: open — largest remaining gap: image texture quality vs references
- Evidence: 14 blind rounds, 6 rubric rounds
- **Still improving at stop?** Visual: no — margins thin and flat for three
  rounds. Perf: retired. Recommendation: the imagery gap is an asset problem,
  not an iteration problem; commission or generate better source imagery, then
  a 2-wave follow-up gauntlet on `imagery` alone would likely retire it.

That recommendation is the report doing its job: telling the user where more
compute would and would not help.
