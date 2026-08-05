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
Ceiling on waves (config `budget_waves`), optionally also wall clock or tokens
tracked outside the script. **Always armed**, even alongside the others — it is
what makes an unattended run safe to agree to.

When it fires, stop cleanly at a wave boundary after smoothing rather than
mid-lane. A coherent artifact one wave early beats an incoherent one at the
exact limit.

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
{ "stops": { "bar_met_n": 2, "clean_streak_n": 2, "budget_waves": 12 } }
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

## Stopping well

Never halt silently. On any stop:

1. Finish the wave and run the smoother, unless the stop is a safety stop
2. Promote the best champion, not necessarily the latest challenger
3. `gauntlet.py report`, then complete the judgement fields yourself
4. State whether the loop was still improving when it stopped

That last sentence is what tells the user whether to spend more. It is the most
useful line in the report and the easiest one to fudge — do not.
