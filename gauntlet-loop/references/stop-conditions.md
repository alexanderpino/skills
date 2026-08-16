# Stop conditions

Agreed at intake, written into `gauntlet/config.json`, armed in combination —
first to fire wins. Ask the user which ones to arm rather than assuming: the
choice encodes how much time and money the run may spend, which is not yours to
decide. `gauntlet.py status` computes all of the mechanical ones; your job is to
run it at every wave boundary and act on what it says.

Two of them end spending on *one lane* (`bar-met`, `clean-streak` retire it;
`no-progress` parks it). Two end the *run* (`budget`, `judgment`). Kill criteria,
agreed at intake, end the run early on evidence the user named in advance.

## The lane-level conditions

### `bar-met`
Our output wins the bar comparison in **N consecutive rounds** on a dimension
(config `bar_met_n`, default 2 — a single win is noise). A *lane* retires only
when **every one of its dimensions** has retired via `bar-met` or `clean-streak`;
this is what stops visual wins from retiring a lane whose frame time still loses.

A retired lane can still carry a recorded open gap (a `minor` that never
mattered); the report keeps it. Retirement is a resource decision, not a claim of
perfection.

This is the condition that does the work in a well-set run, which is why the
target bar has to be reachable. Against a target nobody can hit it never fires,
every lane looks stalled, and the run is really governed by the budget alone.

### `clean-streak`
**N consecutive bar rounds with GAP SEVERITY `none`** on a dimension (config
`clean_streak_n`, default 2). Distinct from `bar-met`: a dimension can keep
losing the comparison and still have no *closeable* gap left, when the remaining
distance is structural.

The severity field is what makes this condition able to fire at all — a critic is
always asked for the largest gap, and `none` is its way of saying there isn't a
meaningful one. Degenerate streaks are cheap for a lazy critic, which is why a
`none` verdict with empty evidence is rejected and re-run.

### `no-progress` — the prune

The only condition that ends a lane **without** it having succeeded. It fires
when a dimension stops paying for its rounds, computed by `status` from the log:

- **no movement in N rounds** (config `no_progress_n`, default 3): no score gain,
  no severity easing, no margin narrowing across the last N bar rounds
- **reverts outpacing promotions** — over 50% of the recent champion rounds ended
  in a revert, so builders are making it worse more often than better
- **the same gap named three rounds running** — the distance is structural, and
  no amount of lane-level work reaches it

`status` prints `PARK RECOMMENDED` with the reason and the exact command:

```bash
python3 scripts/gauntlet.py park --lane imagery --dimension visual \
    --reason "flat 3 rounds, score 5→5; grain gap is a source-asset problem"
```

**Parking is not a verdict on the artifact.** It is the decision to stop paying
for rounds that stopped buying anything, and it is the single most valuable thing
a long run does with its budget. The freed slots go to the next lanes on the
ranked list; the open gap goes into the report where the user can act on it.

The script defends the decision in both directions: it refuses to park a
dimension the log still reads as moving (use `--force` for a scope or priority
call from outside the log), and it warns if you log a round against a parked one.

**Resuming.** `park --resume --reason "<what changed>"` funds it again — on *new
evidence only*: a re-cut that includes the structural element, a fixed inspection
path, a new source asset, a revised bar. "It might work this time" is sunk cost
with extra steps. The resume reason lands in the run history either way.

## The run-level conditions

### `budget`
Ceiling on waves (config `budget_waves`), optionally also wall clock or tokens
tracked outside the script. **Always armed**, even alongside the others — it is
what makes an unattended run safe to agree to.

When it fires, stop cleanly at a wave boundary after smoothing rather than
mid-lane. A coherent artifact one wave early beats an incoherent one at the
exact limit.

Then offer an extension — see below. The budget running out says the money ran
out, not that the artifact is finished, and the user needs to hear those as two
separate facts.

## Extending the budget

The one stop condition with a "would you like more?" attached. A gauntlet is
worth running long, and the commonest way a good run ends badly is a hard stop at
wave 8 with a lane that was still climbing, and nobody told the user.

**Stop first. Offer second. Resume only on a grant.** Never leave the loop
running while you ask, and never extend on your own authority — an extension is
the user spending money they have not yet agreed to spend.

### What `status` gives you

When the budget fires, `gauntlet.py status` prints the offer material from the
log alone:

- every **open** dimension, with whether it is still moving — score trend across
  its last rounds, severity easing (major → minor → none), margin narrowing
- every **parked** dimension, listed but deliberately not priced in
- the recent **revert rate**, and the cost so far in calls per closed gap
- a one-line **read**: `improving`, `mixed`, `at-ceiling`, `unclear`, or
  `nothing-open`
- a suggested wave block, priced in subagent calls over the lanes still funded

**Park before you price.** `extend` refuses a grant while a dimension is flagged
for parking, because an extension priced over stalled lanes buys exactly the
rounds the log says are worthless.

That read is a reading of the log, not a decision. You present it; the user
decides.

### The offer

Four things, in this order: what stopped, what is still open, whether it is
still moving, what more would cost. Then one question.

```
Budget depleted at wave 8. Stopped after smoothing, report at gauntlet/report.md.
~54 calls, 6 gaps closed (~9 each).
  imagery/visual   still moving — score 5→7, severity major→minor
                   open gap: grain texture reads as compression, not intent
  imagery/perf     parked at wave 6 — flat 3 rounds, revert rate 60%
Extension: 3 waves on imagery/visual ≈ 9 subagent calls.
My read: worth it on visual. Extend 3, re-cut, or stop here?
```

Sizing: **2–4 waves**. Enough to close a named gap, short enough that the next
decision is made on fresh evidence. Wanting another twelve is a signal for a
re-cut or a new run with a new contract, not an extension — and the script warns
when a single grant exceeds the whole original budget.

### When the offer is "stop", not "waves"

Recommend against extending — and say why in one line — when:

- **Nothing is open.** Every dimension retired or parked. Raise the bar
  (announced) or stop.
- **The log reads `at-ceiling`.** No open dimension still moving, or reverts
  outpacing promotions. More waves buy reverts. `extend` refuses this read
  without `--force`; use `--force` only when the user has seen the read and chose
  to fund it anyway, and let the report record that.
- **Inspection is broken.** Fix the path first; a loop that cannot see the
  artifact should not be bought more time.
- **Downhill drift.** Promote the best champion and stop.
- **The bar is exhausted.** Every round wins decisively — the comparator no
  longer discriminates. Raise the bar, then talk about waves.

### Recording the grant

```bash
python3 scripts/gauntlet.py extend --waves 3 \
    --reason "imagery/visual score 5→7, severity major→minor; grain gap still closeable"
```

The script raises `budget_waves`, appends the grant to `config.json` with the
wave it was granted at and the log read at the time, and refuses:

- a grant before the budget is actually depleted (evidence-free by construction)
- a reason too thin to be evidence
- anything past an agreed `hard_cap_waves`

Both `status` and `report` then show the run as e.g. `initial 8, extended 2×:
+3, +2`. Also note the grant in `contract.md` and on the workbench — the contract
is the agreement, and this changed it.

### Hard cap

If the user wants unattended running past the first budget, offer a hard cap at
intake instead of a bigger budget:

```bash
python3 scripts/gauntlet.py init ... --budget-waves 8 --hard-cap-waves 20
```

The budget stays the checkpoint where you come back and report; the cap is the
number no extension may cross. It keeps "the budget stop is always armed" true
through any number of extensions.

### `judgment`
You call diminishing returns — with **evidence from the log**, not a feeling:

- Margins narrowing across rounds (decisive → clear → thin) in `status` output
- Named gaps getting smaller and more cosmetic
- Revert rate climbing past the promotion rate (`status` flags >50% in the
  recent window as a judgment signal)
- Cost per closed gap climbing wave over wave — the loop is buying less each time
- The same gap recurring after being closed — a structural ceiling

State the evidence when you stop on judgment. "It seemed done" is not a stop
condition.

### `kill` criteria

The stage gate: evidence, named by the user at intake, that ends the run early
without any further discussion. Agreeing them costs one line at intake and saves
the argument that otherwise happens at wave 9, when everyone is invested.

Good kill criteria are specific and checkable at a wave boundary:

```
KILL  visual not at target by wave 4 → stop and report; the approach is wrong
KILL  frame time still over 16ms after the renderer lane retires → stop
KILL  more than half the lanes parked → stop; the decomposition is wrong
```

Check them in the wave-boundary review, alongside `status`. When one fires, stop
and report like any other stop — the user pre-authorised this exact decision, so
do not re-litigate it, and do not offer an extension against a criterion they
named specifically to prevent one.

## Combining

Typical unattended configuration:

```json
{
  "stops": {
    "bar_met_n": 2, "clean_streak_n": 2, "no_progress_n": 3,
    "target_score": 7, "budget_waves": 8, "hard_cap_waves": null
  },
  "wip_limit": 3
}
```

plus judgment armed by agreement and any kill criteria in `contract.md`.
Per-dimension conditions retire or park dimensions; lanes retire when all their
dimensions retire, and close when each is retired or parked; the run ends when
nothing is left to fund or a run-level condition fires.

## Always-on stops

Independent of configuration:

- **User interrupt.** Stop at the next safe point and report state.
- **Nothing left to fund.** Every dimension retired or parked. The run is over
  whatever the budget says; the open gaps go to the user.
- **Broken inspection.** Critics cannot reach the real artifact. Stop — the loop
  is no longer measuring anything.
- **Downhill drift.** Champion quality falling wave over wave. Stop, revert to
  the best champion, report.
- **Bar exhausted.** Every round wins decisively on every dimension — the
  comparator no longer discriminates. Raise the bar (announced) or stop; never
  keep running against a bar the artifact has passed.

## Stopping well

Never halt silently. On any stop:

1. Finish the wave and run the smoother, unless the stop is a safety stop
2. Promote the best champion, not necessarily the latest challenger
3. `gauntlet.py board`, then `gauntlet.py report`, then complete the judgement
   fields yourself — including what each parked lane would need to be worth
   restarting
4. State whether the loop was still improving when it stopped
5. On a budget stop, make the extension offer — a priced block of waves, or an
   honest recommendation to stop

That last sentence is what tells the user whether to spend more. It is the most
useful line in the report and the easiest one to fudge — do not.
