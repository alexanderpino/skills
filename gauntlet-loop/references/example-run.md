# Example run, annotated

One compact run, end to end. The artifact is deliberately small — a landing-page
hero section — so the machinery is visible. A real run has more lanes and more
waves; the shape is identical.

## The request

> "Make the hero section of my site actually good. Here are three sites I think
> are exceptional: [links]. Don't stop after one pass — keep going."

"Keep going" with a supplied comparator: a gauntlet. Correctness is not the
problem (the page renders); the ceiling is.

## First light — before any of the paperwork

No contract yet, no `gauntlet/` directory, no permission asked. One build of the
thinnest hero that renders end to end — headline, image, CTA, all crude — then
the Playwright harness pointed at it and a screenshot taken, then one critic
against a *candidate* bar (the three reference heroes, not yet frozen).

The first verdict came back *"B's type hierarchy is stronger"* with no measurable
specifics — too soft to build against. Diagnosis: the candidate bar shots were
whole pages, so the critic judged everything at once. Cropped them to the hero
region and re-ran: *"A (ref): headline tracking is optically compensated at
display size; B renders default tracking — visibly looser at 96px."* Actionable.

That screenshot and that sentence went to the user **before** the contract
below — about four minutes in. Two failures were already dead (a whole-page bar
that could not discriminate; an unverified screenshot harness), and the
conversation that follows is about something visible rather than an adjective.

The verdict is not logged — `init` does not exist yet — so it goes into
`contract.md` as the run's starting evidence.

Then the arithmetic:

> `major` gap with a named fix ≈ 2 rounds per lane × 3 lanes ÷ WIP 2 ≈ 3 waves
> for one pass, ~6 for two. Fits inside 8. No rescope needed.

Had it come to 14 waves, the honest move was to drop `layout` or lower the target
*then* — not to start and discover it at wave 8.

## Contract (proposed in one block, confirmed by the user)

```
GOAL     Hero section holds up in a blind comparison against the three references
BAR KIND hybrid
TARGET   visual: the three reference heroes at 1440×900 → gauntlet/bar/, score 7/10
         perf:   LCP < 1.5s, CLS < 0.1 (Lighthouse, throttled) → gauntlet/bar/perf.md
STRETCH  visual indistinguishable from reference 2 at full resolution — direction
         only; not what retirement is judged against
INSPECT  Playwright screenshots at 1440×900 (verified) + Lighthouse CI.
         perf is a machine gate: no critic call, the number decides
LANES    1 imagery  2 typography  3 layout-and-spacing   WIP limit 2
STOP     bar-met 2, clean-streak 2, no-progress 3, budget 8 waves, judgment armed
KILL     visual not at target by wave 5 → stop; the references are a different craft
BUDGET   8 waves × (2 lanes × 2 calls + 1 smoother) ≈ 40 subagent invocations
AUTONOMY Unattended; workbench regenerated each wave boundary
BENCH    gauntlet/workbench.md
```

```bash
python3 scripts/gauntlet.py init --lanes imagery,typography,layout \
    --dimensions visual,perf --bar-kind hybrid \
    --target-score 7 --wip-limit 2 --no-progress-n 3 --budget-waves 8
```

The tree was dirty — first light did not care, but wave 1 does, so the user
committed here. The cropped candidate shots were frozen into `gauntlet/bar/`,
which is where they stop being candidates. Three lanes cut, two funded per wave:
`layout` waits.

## Wave 1 (bootstrap — no champions exist yet)

Two builders in parallel (`imagery`, `typography`), disjoint file ownership. No
promotion comparisons (first round of each lane); one critic call per lane
covering the visual dimension. `perf` needs no critic — Lighthouse decides it.

```bash
python3 scripts/gauntlet.py log-round --wave 1 --lane typography --dimension visual \
  --round 1 --mode blind --winner other --margin decisive --score 4 --severity major \
  --gap "no optical tracking compensation at display sizes" \
  --evidence gauntlet/shots/w1-typo-ab.png --critic-framing default

python3 scripts/gauntlet.py log-round --wave 1 --lane imagery --dimension perf \
  --round 1 --mode rubric --winner other --margin clear --score 4 --severity major \
  --gap "hero image 1.8MB uncompressed; LCP 3.4s against a 1.5s budget" \
  --evidence gauntlet/bench/w1.json
```

That second record cost a Lighthouse run and no subagent at all. Smoother pass:
one seam (typography's new type scale collided with imagery's caption spacing),
fixed. `board` regenerated.

## Wave 2 — a revert

`typography`'s builder closed the tracking gap but the challenger *lost* the
promotion comparison: the same critic call found the new type scale introduced
horizontal overflow at 1280px. Reverted to the champion ref; the critic's
reasoning — not the builder's — went into round 3.

```bash
python3 scripts/gauntlet.py log-round --wave 2 --lane typography --dimension visual \
  --round 2 --mode champion --winner other --margin clear --score 5 --action reverted \
  --champion-ref 4f2a91c --evidence gauntlet/shots/w2-typo-champ.png
```

A losing round is data: the next builder got "close the tracking gap *without*
breaking 1280px" and succeeded in round 3.

## Wave 4 — a park

`imagery/visual` had run four rounds. `status` at the boundary:

```
[imagery / visual] STALLED
  bar 4  promoted 1  reverted 2  streaks bar-met 0 clean 0  rubric 0.0
  score 5/7 target  margins clear → clear → clear  trend: score 5→5, flat
  PARK RECOMMENDED: no movement in 3 rounds (score 5→5, flat)
  open gap: grain texture in the reference reads as intentional; ours reads as compression
```

The builder's last handoff had already said it: the gap needs different source
imagery, not different code. Parked, with the reason, and `layout` took the freed
slot from the queue:

```bash
python3 scripts/gauntlet.py park --lane imagery --dimension visual \
  --reason "flat 3 rounds at score 5, 2 reverts; grain gap is a source-asset problem"
```

The lane's open gap goes to the user in the report, where they can act on it —
commission or generate better source images — in a way no further round could.
`imagery/perf` kept running: it was still moving, and dimensions park separately.

## Waves 5–7

`typography/visual` won blind rounds in waves 6 and 7 → bar-met streak 2 →
dimension retired at score 8 against a target of 7. `imagery/perf`: LCP down to
1.4s → severity `none` twice → clean-streak retired. `layout/visual` closed two
gaps and was still moving at wave 7.

## The stop

`status` at the wave-7 boundary: two dimensions retired, one parked, `layout`
still climbing, one wave of budget left. The kill criterion did not fire — visual
reached target at wave 6. Ran wave 8, smoothed, and stopped on budget.

```
wave 8 of 8 budgeted | ~38 calls spent | 6 gap(s) closed (~6 calls each) | WIP limit 2

STOP CONDITIONS FIRED / SIGNALLED:
  - budget (wave 8 >= 8)

BUDGET DEPLETED — stop cleanly, report, then OFFER AN EXTENSION.

Evidence for the offer:
  [layout / visual] still moving (score 5→7, severity easing) — open gap: vertical
                    rhythm breaks below the fold
  [imagery / visual] parked — not priced into an extension
  recent revert rate: 17%

  read: every open dimension is still moving — an extension is likely to buy real gains

Suggested next wave block: 2–4 waves (~6–12 subagent calls over 1 open lane(s), WIP limit 2).
```

Put to the user in four lines — what stopped, what is open, whether it is still
moving, what more costs — and answered with "yes, two":

```bash
python3 scripts/gauntlet.py extend --waves 2 \
    --reason "layout/visual score 5→7, severity major→minor, 1 revert in 6; rhythm gap still closeable"
```

Note the price: ~6–12 calls, not another forty. The parked lane is not in that
number, and `extend` would have refused the grant if it had still been unparked.

## The report (abridged)

- Target: three reference heroes at 7/10 (visual) + LCP/CLS budgets (perf); never
  moved. Stretch (indistinguishable at full resolution): not reached, and not
  reachable by iteration — it is a photography problem.
- Cost: ~38 calls, 6 gaps closed, ~6 calls per gap
- `typography`: retired at wave 7, 7 bar rounds, 1 revert
- `imagery/perf`: retired. `imagery/visual`: **parked** at wave 4 — open gap:
  source image grain. Worth restarting only with new source assets; more waves
  would not have moved it.
- `layout`: open, still moving at the stop, extended 2 waves
- Evidence: 11 blind rounds, 5 rubric rounds (perf was machine-gated throughout)
- **Still improving at stop?** Yes on layout; no on the rest. Recommendation:
  commission the hero imagery, then a 2-wave follow-up gauntlet on `imagery`
  alone would likely retire it.

That recommendation is the report doing its job: telling the user where more
compute would and would not help — and the park is what made the answer honest
instead of a guess.
