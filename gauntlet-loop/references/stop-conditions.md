# Stop conditions

Agreed at intake, written into `gauntlet/config.json`, armed in combination —
first to fire wins. Ask the user which ones to arm rather than assuming: the
choice encodes how much time and money the run may spend, which is not yours to
decide. `gauntlet.py status` computes all of the mechanical ones; your job is to
run it at every wave boundary and act on what it says.

## The four

### `bar-met`
Our output wins the bar comparison in **N consecutive rounds** on a dimension
(config `bar_met_n`, default 2 — a single win is noise). A *lane* retires only
when **every one of its dimensions** has retired via `bar-met` or `clean-streak`;
this is what stops visual wins from retiring a lane whose frame time still loses.

A retired lane can still carry a recorded open gap (a `minor` that never
mattered); the report keeps it. Retirement is a resource decision, not a claim of
perfection.

Best for reachable bars. Against a deliberately unreachable bar it may never
fire — say so at intake so the user knows the run is really governed by budget
and judgment.

### `clean-streak`
**N consecutive bar rounds with GAP SEVERITY `none`** on a dimension (config
`clean_streak_n`, default 2). Distinct from `bar-met`: a dimension can keep
losing the comparison and still have no *closeable* gap left, when the remaining
distance is structural.

The severity field is what makes this condition able to fire at all — a critic is
always asked for the largest gap, and `none` is its way of saying there isn't a
meaningful one. Degenerate streaks are cheap for a lazy critic, which is why a
`none` verdict with empty evidence is rejected and re-run.

### `budget`
Two ceilings, whichever depletes first: **tokens** (config `budget_tokens`) and
**waves** (config `budget_waves`). **Always armed**, even alongside the others —
it is what makes an unattended run safe to agree to.

Tokens are the ceiling that matters, because tokens are what the user pays. A
wave costs whatever its lanes, dimensions and effort tier happen to cost, so a
run budgeted only in waves cannot tell anyone what it spent or when to stop
paying. `status` prints spend, burn rate per wave, and how many waves of budget
remain at that rate; the offer and `extend` price the next block from the run's
own measured calls.

Set both at intake. If only one is set, `init` warns — and the warning is the
honest one: waves are not a unit of money.

When it fires, stop cleanly at a wave boundary after smoothing rather than
mid-lane. A coherent artifact one wave early beats an incoherent one at the
exact limit.

Then offer an extension — see below. The budget running out says the money ran
out, not that the artifact is finished, and the user needs to hear those as two
separate facts.

## Before the stops: shelving and the tier allowance

Two mechanisms fire *during* the run, at wave boundaries, and both exist because
the classic expensive failure is not "the run went past its budget" — it is "the
run spent its whole budget on work that stopped moving at wave 3".

### Shelving a flat dimension

`status` flags any dimension with no movement across its last `flat_rounds_n` bar
rounds (default 3) as `FLAT`, and prints what running it again costs. Flat means
no score gain, no severity easing, no margin narrowing across the whole window —
one lucky round does not un-flatten a stalled dimension, and a dimension that
climbed early but has not moved lately reads as flat, not as improving.

```bash
python3 scripts/gauntlet.py shelve --lane imagery --dimension perf \
    --reason "flat 3 rounds, revert rate 60%; remaining distance is source-asset quality"
```

Shelved is **parked, not retired.** It stops consuming calls from the next wave;
the report keeps its open gap and lists it separately from anything that retired
on `bar-met` or `clean-streak`. `shelve` refuses a dimension the log does not call
flat, so it cannot become a quiet way to abandon work that was climbing.

Shelving is reversible in the only way that matters: an extension can re-cut the
lane around whatever made the dimension structural.

### The tier allowance

Each effort tier may spend its share of the token budget (`cost-model.md`). When
that allowance depletes, `status` says so and the run has exactly two honest
moves: escalate on evidence, or stop. Continuing at the same tier past its
allowance is how the ladder gets quietly deleted.

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
- the recent **revert rate**
- a one-line **read**: `improving`, `mixed`, `at-ceiling`, `unclear`, or
  `nothing-open`
- a suggested wave block, priced in subagent calls over the lanes still open

That read is a reading of the log, not a decision. You present it; the user
decides.

### The offer

Four things, in this order: what stopped, what is still open, whether it is
still moving, what more would cost. Then one question.

```
Budget depleted at wave 8. Stopped after smoothing, report at gauntlet/report.md.
  imagery/visual   still moving — score 5→7, severity major→minor
                   open gap: grain texture reads as compression, not intent
  imagery/perf     flat 3 rounds, revert rate 60% — at its ceiling
Extension: 3 waves on imagery/visual ≈ 12 subagent calls.
My read: worth it on visual, not on perf. Extend 3, re-cut, or stop here?
```

Sizing: **2–4 waves**. Enough to close a named gap, short enough that the next
decision is made on fresh evidence. Wanting another twelve is a signal for a
re-cut or a new run with a new contract, not an extension — and the script warns
when a single grant exceeds the whole original budget.

### When the offer is "stop", not "waves"

Recommend against extending — and say why in one line — when:

- **Nothing is open.** Every dimension retired. Raise the bar (announced) or stop.
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
python3 scripts/gauntlet.py extend --waves 3 --tokens 5000000 \
    --reason "imagery/visual score 5→7, severity major→minor; grain gap still closeable"
```

Grant both units. Waves without tokens means the run stops on tokens before it
runs the waves the user just paid for — the script warns, and prints the measured
projection so you can quote the right number.

The script raises `budget_waves` and `budget_tokens`, appends the grant to
`config.json` with the wave it was granted at and the log read at the time, and
refuses:

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
- The same gap recurring after being closed — a structural ceiling

State the evidence when you stop on judgment. "It seemed done" is not a stop
condition.

## Combining

Typical unattended configuration:

```json
{ "stops": { "bar_met_n": 2, "clean_streak_n": 2,
             "budget_waves": 12, "budget_tokens": 20000000,
             "hard_cap_waves": null, "hard_cap_tokens": null,
             "flat_rounds_n": 3 } }
```

plus judgment armed by agreement. Per-dimension conditions retire dimensions;
lanes retire when all their dimensions do; the run ends when all lanes are
retired or a run-level condition (budget, judgment) fires.

## Always-on stops

Independent of configuration:

- **User interrupt.** Stop at the next safe point and report state.
- **Broken inspection.** Critics cannot reach the real artifact. Stop — the loop
  is no longer measuring anything.
- **Downhill drift.** Champion quality falling wave over wave. Stop, revert to
  the best champion, report.
- **Bar exhausted.** Every round wins decisively on every dimension — the
  comparator no longer discriminates. Raise the bar (announced) or stop; never
  keep running against a bar the artifact has passed.
- **A tier that cannot be escalated out of.** The tier allowance is spent and the
  gates still fail. More money at this tier buys more of the same verdict; more
  money at the next tier buys a bigger version of whatever the failing gate is
  telling you. Stop, or fix the gate.

## Stopping well

Never halt silently. On any stop:

1. Finish the wave and run the smoother, unless the stop is a safety stop
2. Promote the best champion, not necessarily the latest challenger
3. `gauntlet.py report`, then complete the judgement fields yourself
4. State whether the loop was still improving when it stopped
5. On a budget stop, make the extension offer — a priced block of waves, or an
   honest recommendation to stop

That last sentence is what tells the user whether to spend more. It is the most
useful line in the report and the easiest one to fudge — do not.
