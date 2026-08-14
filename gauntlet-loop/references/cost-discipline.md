# Cost discipline

A gauntlet is a loop that spends money on purpose. The question is never "how do
we run it cheaply" — a cheap loop that closes no gaps is pure waste — but "does
this call buy a gap". Everything here is about killing the calls that do not.

Two numbers govern the run, both printed by `gauntlet.py status`:

- **calls spent** — the running total
- **calls per closed gap** — the only efficiency number that matters

If cost per closed gap climbs wave over wave, the loop is buying less each round.
That is a stop signal, not a reason to try harder.

## Where the tokens actually go

Per lane-round, in rough order of size:

1. The **builder's** context: the artifact it reads, the bar it opens, the files
   it writes.
2. The **critic's** context: two artifacts plus the bar, inspected properly.
3. The **lead agent's** own context: prompts written, verdicts read, state
   narrated.
4. The **smoother**, once a wave, over whatever it is pointed at.

Note what is not on that list: nothing about the *number of waves*. Waves are the
budget unit the user agreed to. The savings live inside the wave, and a saved
call is a call the next wave can spend on a real gap.

## The ten rules

### 1. Machine gates before critics

Any dimension that a command can decide does not need a subagent. Test suites,
benchmarks, frame times, byte sizes, contrast ratios, LCP, word counts, lint
gates — run the command, log the number as evidence (`--mode rubric`).

A critic call to confirm what a benchmark already printed is the single most
common wasted call in this method. Critics are for judgement. Where a dimension
is *entirely* machine-checkable, it never needs a critic at all, and the run's
cost roughly halves on that dimension.

### 2. One critic call per round by default

The expensive part of a critic call is the inspection: opening two artifacts and
the bar, and actually looking. Asking a second critic to re-open the same three
things to answer a second question pays that cost twice.

So the default round is **one call, two questions, two log records**: is the
challenger better than the champion (promotion), and how does it compare to the
bar (bar). The verdict block carries both.

Split it into two calls when:

- the round could **retire** a dimension — retirement is a resource decision and
  deserves an independent second look
- the two answers would **pull against each other** (the challenger beats the
  champion but loses ground on the bar dimension being judged)
- the lane is **expensive to get wrong** — a promotion that lands in a shared
  surface, an irreversible asset change

That is the exception, not the shape of the run.

### 3. Paths, not payloads

Subagents get: the lane goal, the path to `contract.md`, the path to the bar, the
paths they own, and one gap line. They read what they need from disk.

Pasting the artifact, the bar, or the previous verdict into a prompt costs the
tokens once for you and again for them, and it introduces paraphrase drift on
top. Point at paths. This is also the bar-erosion fix, which is why the same
sentence appears in `failure-modes.md`.

### 4. Cap the handoffs

- **Critic:** the verdict block. Nothing before it, nothing after it.
- **Builder:** files touched, one line each, five lines maximum. No rationale, no
  self-assessment — both are forbidden anyway (`builder.md`).
- **Smoother:** the report format in `smoother.md`, nothing else.

Every extra paragraph is read by you, quoted into the next prompt, and carried
for the rest of the run.

### 5. No gap, no builder

A builder needs something named to close. If the last verdict came back clean,
the honest options are: retire the dimension, raise the bar (announced), or park
the lane. Spawning a builder to "keep improving" against no named gap produces a
change nobody asked for and a round nobody can judge.

### 6. Respect the WIP limit

`wip_limit` (default 3) caps the lanes funded in a wave. Below the cap you are
under-using the budget; above it you get one round on each of six lanes, which is
six half-closed gaps and nothing finished.

Depth beats breadth here: three rounds on one lane close a gap, one round on
three lanes usually does not. The ranked lane list decides who gets the slots
(`decomposition.md`).

### 7. Let the script count and publish

`status` computes streaks, trends, stalls, cost and the next-wave plan. `board`
regenerates `workbench.md`. Both are deterministic and free.

Do not recompute state in prose, do not keep a running summary in context, and
never hand-write the workbench. If you find yourself explaining the run's state
to yourself in the transcript, run `status` instead.

### 8. Route the model to the role

A mechanical builder does not need the tier a deciding critic needs, and a
machine-checkable dimension needs no model at all. Routing by role is the largest
saving after the WIP limit — and the one place where economising can destroy the
run's evidence rather than its budget. The cheapest model that can do the job,
never cheaper on the critic whose verdict decides something, and the tier held
fixed within a lane so score trends stay readable.
→ `references/model-routing.md`

### 9. Never pay twice for the same verdict

Two different things get paid for twice, and both need stopping.

**A judgement, re-argued.** A closed gap stays closed and a retired dimension is
not re-opened. `log-round` warns when a record lands on a retired dimension,
because that round is money spent on ground the run already covered
(`failure-modes.md` → Re-litigation).

**A check, re-derived.** This one is subtler and costs more. Anything a command
can decide — paths that exist, flags that match, code that compiles, a number
against a threshold — is a **gate**, declared in `config.json` with the paths it
reads. `gauntlet.py gate` runs it, caches the result against a content hash of
those paths, and on the next round *skips it and says so*:

```
[SKIP] no-dangling-paths — unchanged since wave 2
0 run, 4 skipped (inputs unchanged), 0 failed
```

**A check is invalidated by a change to its inputs, not by the passage of a
round.** That is the whole rule, and it is why the cache is keyed by content
hash rather than by wave number: change a byte in a declared path and the gate
re-runs; change nothing and it does not. Hand the results to the critic
(`critic.md`), which is told explicitly not to re-verify them.

The cost of getting this wrong is not theoretical. In this skill's own self-run,
two consecutive critics each independently re-confirmed that every reference path
existed, every documented flag existed, and no phase number was stale — the same
clean result, twice, inside calls costing roughly 70,000 tokens each. The same
four checks as gates: **0.05 seconds**.

Two failure modes to avoid while doing this:

- **Do not gate a judgement.** "Is this prose clear" is not a command. Gates take
  the mechanical work *off* the critic so its whole budget goes to judgement; they
  do not replace it.
- **Do not let a gate go stale silently.** A gate must declare every path it
  reads. One that reads a file it did not declare will skip when it should run,
  which is worse than not having the gate — you would at least have known you
  were unchecked.

### 10. Read each reference once, at its phase

The reference files are indexed by phase at the bottom of `SKILL.md`. Reading all
of them at intake costs the whole set before the run has decided anything, and
most runs never need `blind-protocol.md`'s rubric section or the resume protocol.

## Cheap moves that are worth their cost

Do not save money on these — each one prevents a much larger loss:

- **First light** (one build, one critic) before the first wave — catches broken
  inspection paths and soft bars.
- **Re-verifying inspection** at each wave boundary — a rotted harness makes
  every later call worthless.
- **The champion snapshot** each wave, taken before the builders spawn — it is a
  commit, not a call, and it is what makes a revert possible.
- **The smoother**, when lanes touched a shared surface — one call that prevents
  a wave of incoherence.

## When the honest answer is "stop spending"

Cost discipline includes saying the loop is not worth more money:

- cost per closed gap is climbing and the open gaps are cosmetic
- every open dimension is parked or stalled
- the remaining gap is a source-asset or architecture problem that lane-level
  rounds cannot reach

Say it plainly, with the numbers from `status`. The cheapest wave in any run is
the one that never ran.
