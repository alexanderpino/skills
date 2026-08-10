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
STOP     bar-met N=2, clean-streak N=2, budget 8 waves / 20M tokens, judgment armed
BUDGET   20M tokens ≈ €180 at €9/Mtok, and 8 waves. Whichever depletes first stops
         the run. At tier 3 a wave is 3 lanes × (1 + 2×2) + 1 ≈ 16 calls
LADDER   Start tier 0 (probe). Tiers 0–1 ≈ €36 of the €180 — if this is not
         working, that is what finding out costs
MODELS   cheap=claude-haiku-4-5, mid=claude-sonnet-5, high=claude-opus-5
         (1× / 3× / 5× on output). Builders buy the top tier from wave 2;
         critics screen cheap and escalate only thin verdicts
AUTONOMY Unattended; workbench regenerated per wave
BENCH    gauntlet/workbench.html (renders gauntlet/state.json)
```

```bash
python3 scripts/gauntlet.py init --lanes typography,layout,imagery \
    --dimensions visual,perf --budget-waves 8 --budget-tokens 20000000 \
    --cost-per-mtok 9.0
```

Working tree was dirty → asked the user to commit first. Bar screenshots frozen
into `gauntlet/bar/`. Three lanes were cut, but tier 0 runs only one — the other
two cost nothing until they run, and can still be re-cut for free.

## Round zero — tier 0, the probe

One build round on `typography` only, one collapsed critic call on a cheap
model. `typography` was chosen by risk, not comfort: it is the lane the other
two build on (a type scale change moves every spacing decision in `layout`),
and its bar is the hardest inspection in the cut — if the harness cannot show a
critic optical tracking differences at 96px, it cannot show it anything
subtler. A pass here de-risks the most; a kill here is cheapest.

The verdict came back *"B's type hierarchy is stronger"* with no measurable
specifics — too soft.

```bash
python3 scripts/gauntlet.py tier
#   [x] rounds at this tier — 1 bar round logged at tier 0
#   [ ] the bar discriminates — verdicts are vague — sharpen the bar, do not escalate
```

The gate did its job: the fix was cheap because nothing had scaled yet. Diagnosis:
the bar screenshots included whole pages, so the critic judged everything at once.
Fix: cropped bar shots to the hero region only. Second round-zero verdict:
*"A (ref): headline tracking is optically compensated at display size; B renders
default tracking — visibly looser at 96px."* Actionable.

Then the calibration that matters:

```bash
python3 scripts/gauntlet.py spend --tokens 300000 --role builder --note "probe builder, typography"
python3 scripts/gauntlet.py status
#   spend 420k tok ≈ €3.78 of 20.00M tok ≈ €180.00 (2%)
```

Put to the user before wave 1: *"Round zero cost ≈ €3.80 including the false
start. Eight waves at three lanes lands around €150–190. Still eight?"* — they
said yes, and now that yes is informed.

```bash
python3 scripts/gauntlet.py escalate --reason "probe verdict names optical tracking at 96px; inspection path verified after bar re-crop"
#   escalated: tier 0 → 1 (pilot)
```

## Wave 1 — tier 1, the pilot

Two lanes, not three: `typography` and `layout`. Mid-tier builders, cheap
screening critics, one collapsed call each. No promotion comparisons (first round
of each lane); one bar record per lane per dimension all the same.

From tier 1 up, every round states its bet before the builder runs — the probe
aimed at the loop itself, but from here the aims are about the artifact:

```bash
python3 scripts/gauntlet.py aim --wave 1 --lane typography --dimension visual --round 1 \
  --hypothesis "headline tracking is default at 96px; the refs compensate optically, which is most of the perceived gap" \
  --approach "size-stepped letter-spacing on display sizes" \
  --expect-severity minor
```

The builder gets the hypothesis and approach in its brief; the round is now
falsifiable. The verdict:

```bash
python3 scripts/gauntlet.py log-round --wave 1 --lane typography --dimension visual \
  --round 1 --mode blind --winner other --margin decisive --score 4 --severity major \
  --gap "no optical tracking compensation at display sizes" \
  --evidence gauntlet/shots/w1-typo-ab.png --critic-framing default --tokens 95000
```

At the wave boundary, both lanes had moved and the pilot allowance was 60% spent:

```bash
python3 scripts/gauntlet.py escalate --reason "typography 4→6 severity major→minor, layout 3→6; both closing named gaps at pilot cost"
#   escalated: tier 1 → 2 (campaign)
#   ~5 calls per lane per round (was 3)
```

Before the escalation was spent, `imagery` — never judged — got its price. Not a
build round: a **survey**, one cheap bar comparison of the hero as it stood
against the references, and one Lighthouse measurement for perf. Two verdicts
(`visual` major: "stock photo reads generic against the references' shot-to-
brief imagery"; `perf` major: LCP 3.4s) for one cheap critic call plus a free
measurement — so the campaign's first `plan` ranked three *measured* lanes, not
two measured and one guess. `plan` would have put `imagery` at the top unpriced
anyway: a never-judged pair outranks every known major until someone prices it.

`imagery`'s first build round then came at wave 2, and none of the budget went
to building it while the method was still unproven.

Similar records for `layout` (major: "reference uses a 12-col grid with content
capped at 7 cols; ours spans full width"). Perf dimension logged via rubric mode
(a Lighthouse number cannot be blinded):

```bash
python3 scripts/gauntlet.py log-round --wave 2 --lane imagery --dimension perf \
  --round 1 --mode oracle --winner other --margin clear --score 3 --severity major \
  --gap "hero image 1.8MB uncompressed; LCP 3.4s vs 1.5s budget" \
  --evidence gauntlet/bench/w1.json
```

Note the mode: LCP is a **number**, so no model was asked. `oracle` rounds cost
no critic tokens and feed the streaks like any bar round. Over the run this
removed roughly half the critic calls — `perf` was measured every time and only
brought to a model once, at wave 5, to name why the number had stopped moving.

Smoother pass: found one seam (typography's new type scale collided with
layout's spacing tokens), fixed, logged.

## Wave 2 — a revert

`layout`'s builder closed the grid gap but the challenger *lost* the promotion
comparison: the critic (blind, challenger vs champion) found the new grid
introduced horizontal overflow at 1280px. Reverted to the champion ref; the
critic's reasoning — not the builder's — went into round 3.

```bash
python3 scripts/gauntlet.py log-round --wave 2 --lane layout --dimension visual \
  --round 2 --mode champion --winner other --margin clear --score 5 --action reverted \
  --champion-ref 4f2a91c --evidence gauntlet/shots/w2-layout-champ.png --tokens 85000
```

A losing round is data twice over. The round's aim ("switch the hero to the
reference's 12-col grid", expect minor) scored **miss — reverted**, and the
approach went into the failed ledger; the next round's aim had to say what would
be different ("same grid, with explicit overflow containment at 1280px") rather
than quietly trying the same thing again. That builder got "close the grid gap
*without* breaking 1280px" and succeeded in round 3.

## Wave 3 — planning the wave instead of running it

`plan` at the wave boundary ranked what was open and priced the alternative:

```
RUN (largest gap first):
  [layout / visual]       severity major
  [typography / visual]   severity minor
HOLD:
  [imagery / perf]        oracle unchanged since wave 2

Proposed wave: 2 lane(s), ~11 calls
  ~€14.20 — against ~€21.30 to run all 3 lane(s) regardless of evidence (~€7.10 saved)
```

`imagery` was held (`skip --reason-code oracle-unchanged`) — the measurement had
not moved, so there was nothing for a builder to react to. Wave 3 ran two lanes.

Wave 4's `layout` builder came back having escalated instead of editing: the fix
needed a file it did not own. `git diff --quiet` on its owned paths confirmed
nothing had changed, so no critic ran at all:

```bash
python3 scripts/gauntlet.py skip --wave 4 --lane layout --dimension visual \
  --reason-code no-change --note "builder escalated for a file it does not own"
```

Ownership was transferred and the round re-briefed. Judging that unchanged
artifact would have cost two calls to reproduce the wave-3 verdict word for word.

## Wave 3b — a re-cut

The smoother reported the same seam twice running: typography and layout kept
fighting over vertical rhythm. Per `decomposition.md`, a recurring seam means the
cut is wrong. Merged the two lanes into `type-and-layout` between waves; noted in
the workbench that streak counters for both reset deliberately.

## Waves 4–6 — a shelving

`type-and-layout` visual: won blind rounds in waves 5 and 6 → bar-met streak 2 →
dimension retired. Perf: LCP down to 1.4s → severity `none` twice → clean-streak
retired. Lane retired.

`imagery` perf went flat: LCP stuck at 2.1s across three rounds, margins thin,
two reverts. `status` at the wave-5 boundary said so and priced it:

```
[imagery / perf]
  recent margins: thin → thin → thin
  open gap: LCP 2.1s vs 1.5s; remaining cost is the source asset, not the pipeline
  FLAT for 3 bar rounds — shelve it or re-cut it; running it again costs ~5 calls per round for no movement
```

```bash
python3 scripts/gauntlet.py shelve --lane imagery --dimension perf \
  --reason "flat 3 rounds at thin margin; remaining LCP distance is source asset quality, not pipeline"
```

That is roughly €25 of wave-6 and wave-7 calls that never happened. Under the old
shape the same evidence sat unread in the log until the budget ran out.

`imagery` visual kept losing on margin `thin` with gaps getting cosmetic ("grain
texture in ref reads intentional; ours reads like compression") — and its aims
kept missing: 1 hit in 4 scored. `status` said what that means: *this dimension
is not understood — diagnose before building again.* One read-only round on the
cheap tier (`spend --role diagnostician`), given the artifact, the bar and the
three failed hypotheses from the ledger, came back with the cause: the gap was
never in the processing pipeline — the references shoot on film, and no filter
makes a compressed stock photo read as intentional grain. Every prior aim had
been a guess at the same wrong model. That cause became the report's
recommendation instead of three more missed rounds.

## The stop

`status` at the wave-6 boundary: one lane fully retired, one dimension shelved,
`imagery` visual showing margins thin for three rounds and one revert — the
judgment signal. Stopped on judgment with evidence, two waves under budget and
€60 under the token budget, rather than spending them on a lane at its ceiling.

```
STOP CONDITIONS FIRED / SIGNALLED:
  - judgment signal: revert rate over 50% in recent rounds — likely at the ceiling
```

## Variant: the same run stopping on budget

Had `imagery` still been closing gaps at wave 8, the budget would have fired
first. Then the run stops, smooths, reports — and comes back with an offer rather
than a farewell. `status` at the boundary:

```
wave 8 of 8 budgeted

BUDGET DEPLETED — stop cleanly, report, then OFFER AN EXTENSION.

Evidence for the offer:
  [imagery / visual] still moving (score 5→7, severity easing) — open gap: grain
                     texture reads as compression, not intent
  recent revert rate: 17%

  read: every open dimension is still moving — an extension is likely to buy real gains

Suggested next wave block: 2–4 waves (~12–24 subagent calls over 1 open lane(s)).
  measured from this run: ~2.30M tok ≈ €20.70 – 4.60M tok ≈ €41.40
```

Put to the user in four lines — what stopped, what is open, whether it is still
moving, what more costs — with the cost measured from this run rather than
estimated. Answered with "yes, three":

```bash
python3 scripts/gauntlet.py extend --waves 3 --tokens 4000000 \
    --reason "imagery/visual score 5→7, severity major→minor, 1 revert in 6; grain gap still closeable"
```

Both units granted. Waves alone would have stopped on tokens partway through
wave 10, having spent the money and delivered two of the three waves — the script
warns when you try.

Waves 9–11 then run on `imagery` alone; the report shows `initial 8, extended 1×:
+3` and says whether those three waves earned their keep. Had the read come back
`at-ceiling` instead, the offer would have been "stop, or re-cut `imagery` around
the source assets" — and `extend` would have refused the grant without `--force`.

## The report (abridged)

- Bar: three reference heroes (visual) + LCP/CLS budgets (perf); never moved
- Spend: 13.4M tokens ≈ €121 of €180 budgeted (67%); ended at tier 2 of 3
- Models: haiku-4-5 ran 14 critic calls for €4; sonnet-5 ran the smoother and the
  split critics for €18; opus-5 ran the builders for €99. **Six thin verdicts
  were escalated to opus-5 and it agreed with all six** — €8 that bought
  confirmation, not information. Next run: escalate only when a thin verdict
  would retire a lane, or raise the bar so the comparison is harder
- Ladder: tier 0 → 1 at €3.78 spent, tier 1 → 2 at €31. Both escalations paid for
  themselves; the false start in round zero cost €1.20 and saved a wave
- `type-and-layout`: retired, 9 bar rounds, 1 revert, 1 re-cut
- `imagery / perf`: **shelved** at wave 5, not retired — LCP 2.1s vs 1.5s target
- `imagery / visual`: open — largest remaining gap: image texture quality vs references
- Evidence: 14 blind, 1 rubric, 7 oracle rounds — `perf` was measured, not judged
- Aims: 11 scored, 8 hit (73%) — `type-and-layout` hit 7 of 8 (the run understood
  that lane); `imagery/visual` hit 1 of 4, and the diagnosis round found why:
  the gap was the source asset, not the pipeline. Every miss's approach is in
  the ledger; none was retried
- Management: 5 rounds not run (2 no-change, 2 oracle-unchanged, 1 gap-too-small)
  ≈ €11 of critic calls never spent; lanes ran serially from wave 3 after the
  smoother reported the same seam twice
- **Still improving at stop?** Visual: no — margins thin and flat for three
  rounds. Perf: retired. Recommendation: the imagery gap is an asset problem,
  not an iteration problem; commission or generate better source imagery, then
  a 2-wave follow-up gauntlet on `imagery` alone would likely retire it.

That recommendation is the report doing its job: telling the user where more
compute would and would not help.
