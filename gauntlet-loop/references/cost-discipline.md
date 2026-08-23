# Cost discipline

A gauntlet is a loop that spends money on purpose. The question is never "how do
we run it cheaply" — a cheap loop that closes no gaps is pure waste — but "does
this call buy a gap". Everything here is about killing the calls that do not.

## The contract: 80% of the bar for 20% of the cost

That is the whole reason this variant exists, so it is a number the run scores
itself against rather than a claim in a README:

> **≥ 80% of the target bar, for ≤ 20% of the undisciplined cost.**

```bash
python3 scripts/gauntlet.py efficiency
```

Both halves are computed from the log, and the command prints `pass`,
`too-expensive`, `too-cheap`, `missing-both`, or `unmeasured`. `status` prints
the one-line version at every wave boundary and `report` scores it at the end,
so a broken promise surfaces at wave 2 rather than in the post-mortem.

**The denominator is this run without the discipline.** Not a guess at what
someone else's prompt would have cost — that is unmeasurable, and a ratio
against an imagined number is a marketing exercise. The counterfactual is: the
same lanes, the same waves, one round per lane per wave, every round at the
unoptimised price, nothing retired, nothing parked, no dimension decided by a
machine, no verdict at a cheaper tier. That *is* the loop this method descends
from, and every lever below is a line item against it.

**The unoptimised price is measured, once.** First light is that round by
construction: full payloads, deciding tier, cold cache, no gates declared yet.
Record what it cost and the ratio has a real denominator:

```bash
python3 scripts/gauntlet.py efficiency --baseline-round-tokens 130000
```

Without it the command refuses to compute a ratio. A run that cannot score its
own contract has not met it, and the report says so in those words.

**Both halves, or neither.** The cheapest possible run leaves every dimension
unjudged, so quality counts a never-judged dimension as **zero, not as absent** —
that is what the `too-cheap` verdict catches, and it is the verdict this contract
exists to make impossible to hide. Cost discipline that costs quality is not the
deal. Equally, `too-expensive` names the levers that are off, because "spend
less" is not an instruction anyone can act on.

### Where the 5× comes from

A target nobody can derive is a wish. The rules below multiply in two separate
places — **inside the round** and **over the round count** — and the contract
needs both. Modelled from a 130k lane-round (builder ~50k, critic ~70k, lead
~10k); the 70k critic call is measured, from this skill's own self-run, and the
multipliers are estimates until a run measures its own:

| Lever | Where it bites | Round cost |
|---|---|---|
| — | the undisciplined round | 130k |
| Prompt caching (rule 10) | the stable prefix — brief, contract, frozen bar, settled — read at ~0.1× | ~71k |
| Script counts and publishes (rule 7) | the lead narrates nothing `status` can compute | ~64k |
| Screening tier (rule 8) | routine verdicts on a cheaper model | ~52k |
| Machine gates (rule 1) | machine-decided dimensions leave the critic's scope | **~46k (35%)** |

Per-round discipline alone lands at roughly a third — **not** at a fifth. The
rest is the round *count*: the WIP limit funds depth over breadth, retirement
and parking stop funding what is finished or dead, the review cap stops the
fourth look at one gap, and no-gap-no-builder skips the round that has nothing
to close. A run that funds 8 lane-rounds where the undisciplined loop funds 15
is at 53% of the work.

**0.35 × 0.53 ≈ 0.19.** That is the contract, and it says something useful about
which corners cannot be cut: neither half reaches it alone. Cheap rounds without
pruning stop at ~35%; pruning without cheap rounds stops at ~50%. This is also
why `efficiency` lists the levers individually — a missed ceiling is nearly
always two or three of them switched off, not one bad wave.

Two numbers govern the run, both printed by `gauntlet.py status`:

- **calls spent** — the running total
- **calls per closed gap** — the only efficiency number that matters

If cost per closed gap climbs wave over wave, the loop is buying less each round.
That is a stop signal, not a reason to try harder.

**Read that number as predictive, not provisional.** Earned-value practice found
that cost efficiency settles early on large programmes and rarely recovers
(`authorities.md`): the rate you are getting a fifth of the way in is roughly the
rate you will get. So a bad wave 2 is evidence about wave 6, which is why the
kill criteria are checked at wave 2. Waiting for efficiency to improve on its own
is the most expensive optimism available to this loop.

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

## The eleven rules

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
  deserves an independent second look, and that second look runs **hostile**:
  the critic is framed to assume the bar is not met and to find where
  (`blind-protocol.md`, critic rotation). Scrutiny scales with the size of the
  claim, and "done" is the biggest claim a lane ever makes
- the two answers would **pull against each other** (the challenger beats the
  champion but loses ground on the bar dimension being judged)
- the lane is **expensive to get wrong** — a promotion that lands in a shared
  surface, an irreversible asset change

That is the exception, not the shape of the run.

And go *below* one call when the gap allows it. A named gap that decomposes into
gate-checkable pieces — three broken paths, two failing thresholds — does not
need a verdict per piece: the builder takes up to three **micro-rounds**, each
verified by `gate`, and one critic judges the accumulated result. The champion
guard arms at that judgement, which bounds the drift the batching could hide.
More build-iterations per verdict is the cheapest grind the method has.

### 3. Paths, not payloads

Subagents get: the lane goal, the path to `contract.md`, the path to the bar, the
paths they own, and one gap line. They read what they need from disk.

Pasting the artifact, the bar, or the previous verdict into a prompt costs the
tokens once for you and again for them, and it introduces paraphrase drift on
top. Point at paths. This is also the bar-erosion fix, which is why the same
sentence appears in `failure-modes.md`.

After a lane's first round, scope the paths — the dirty-rectangle move. The cold
full read is the largest per-round cost, and most of it re-reads what no builder
touched. A repeat critic gets the bar, the round's diff, and the region it
judges; it demands the full artifact when the slice cannot carry the dimension
(`critic.md`). Buy the full re-read back at every decision round and roughly
every third routine round, as the drift check — scoping that never re-widens is
how a slice quietly becomes the artifact.

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

### 8. Route the model to the decision, not just the role

A mechanical builder does not need the tier a deciding critic needs, and a
machine-checkable dimension needs no model at all. Routing by role is the largest
saving after the WIP limit — and the one place where economising can destroy the
run's evidence rather than its budget. The cheapest model that can do the job,
never cheaper on the critic whose verdict decides something, and the tier held
fixed within a lane so score trends stay readable.
→ `references/model-routing.md`

### 9. Never pay twice for the same verdict

Three different things get paid for twice, and all three need stopping.

**A judgement, re-argued.** A closed gap stays closed and a retired dimension is
not re-opened. `log-round` warns when a record lands on a retired dimension,
because that round is money spent on ground the run already covered
(`failure-modes.md` → Re-litigation). Rules the critic never sees do not hold, so
`board` generates `gauntlet/settled.md` — retired, closed, parked, out of scope —
and every critic prompt hands it over with the bar. It is generated from the log,
so being current costs nothing.

**A gap, re-reviewed.** A round that names a gap the last round already named
buys an opinion, not a closed gap. The loop allows three (`gap_rounds_n`) and
then forces a decision: re-cut, backlog, accept, or escalate. Matching is on
content, not on string equality — a critic rewording yesterday's gap is the
normal case, and exact-match counting was the same as no cap. Blocking gaps
(security, data loss, correctness) are exempt: those get closed, not timed out.
Three rounds at ~40k tokens each is a real bill for one unclosed gap, and it is
paid quietly, wave after wave, by runs that look healthy.

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

**The ratchet: gates are harvested, not just declared.** At every wave boundary,
any gap a critic named that a command could check becomes a new gate. Judgement
is spent once discovering the check; the check then runs free forever. A run
that harvests converts its own history into a regression suite, and its late
waves are cheaper *because* its early waves happened — the same reason an
engine bakes lighting it computed once. The frozen bar gets the same treatment
at Phase 2: measure it once into `gauntlet/bar/measurements.md` and hand critics
the numbers.

The ratchet outlives the run: `init` carries the gate suite across a re-cut and
into the next run on the same artifact. The original loop starts every run from
zero; this one compounds — each gauntlet leaves the next one a larger free
suite and a cheaper wave 1. Prune gates whose subject has left the scope; an
inherited gate nobody understands is inspection rot with a pedigree.

Two failure modes to avoid while doing this:

- **Do not gate a judgement.** "Is this prose clear" is not a command. Gates take
  the mechanical work *off* the critic so its whole budget goes to judgement; they
  do not replace it. (Baking obeys the same line: bake the bar's *measurements*,
  never a paraphrase of its qualities — that is bar erosion.)

  And its blind spot has an owner: **the gates judge what they measure, and
  nothing in fresh context ever reviews the suite itself** — gates are declared
  by whoever runs the loop, often about work that same context produced, and the
  independence machinery (fresh context, blind labels, a separate judge) is
  deliberately not applied to them. So once per run per machine-decided
  dimension — at a re-cut, or before that dimension retires — spend one
  deciding-tier verdict on the question *"what about this dimension do these
  gates not see?"*, judged against the artifact, not against the suite. Field
  evidence for why: a physics suite read 8/7/8 on the same tree that three
  critics in separate contexts independently scored 3/10 visually — the gates
  were right about everything they measured and blind to everything they did
  not. Log the answer as a round; harvest any new check it names.
- **Do not let a gate go stale silently.** A gate must declare every path it
  reads. One that reads a file it did not declare will skip when it should run,
  which is worse than not having the gate — you would at least have known you
  were unchecked.

### 10. Shape the round so the prompt cache can work

A gauntlet is unusually cache-shaped and usually wastes it. Every critic call in
a run opens the same brief, the same contract and the **same frozen bar** — a
prefix that is identical by construction, because freezing it is already the
rule. Only the tail differs: this round's artifact or diff, and one gap line.

Prompt caching is a **prefix match**: the cache key is the exact bytes up to a
breakpoint, and any byte that changes invalidates everything after it. Render
order is `tools` → `system` → `messages`. So the whole technique is an ordering
discipline, and it is free:

- **Stable first, volatile last.** Brief, contract, bar, baked measurements —
  then the diff, the region, the gap. A gap line pasted above the bar makes the
  bar uncacheable for the rest of the run.
- **Byte-identical, not merely equivalent.** A restated bar is different bytes
  every time; the frozen path is the same bytes forever. "Paths, not payloads"
  (rule 3) was already the bar-erosion fix — it is the caching fix too.
- **Nothing volatile in the prefix.** Timestamps, wave numbers, run ids, an
  unsorted JSON dump: each one is a per-call prefix and a guaranteed miss. The
  wave number belongs in the tail with the gap, not in the header.
- **Warm once, then fan out.** A cache entry becomes readable only once the
  first response starts streaming, so N parallel critics with the same prefix
  all pay full price. Fire one lane's call, wait for its first token, then
  release the rest of the wave. That single ordering change is the difference
  between one write and N.
- **Caches are model-scoped.** Switching tiers mid-lane throws the cache away as
  well as confounding the trend (`model-routing.md`) — the LOD ladder pays best
  when each track keeps its model for the lane's life.
- **Mind the TTL against the wave clock.** The default entry lives ~5 minutes; a
  1-hour TTL survives the gap between waves but costs a 2× write instead of
  1.25×, so it needs three reads to pay off rather than two. Reads cost ~0.1×.
  A three-lane wave with several rounds clears that easily; a two-round run does
  not. Where the harness exposes it, `usage.cache_read_input_tokens` says whether
  any of this is actually happening — zero across a wave means something in the
  prefix is moving.

Where a harness builds the calls for you (Claude Code's subagents, for
instance), you do not place the breakpoints — but you still own the prompt's
shape and the order the calls go out in, which is where most of the saving
lives. Verify current mechanics before quoting numbers into a contract: this is
API behaviour, and it moves (`grounding.md`).

### 11. Read each reference once, at its phase

The reference files are indexed by phase at the bottom of `SKILL.md`. Reading all
of them at intake costs the whole set before the run has decided anything, and
most runs never need `blind-protocol.md`'s rubric section or the resume protocol.

## The quality-price menu

Quality has a price curve, and hiding it is how runs end up buying a 9 on a
7 budget or a 7 on a 9 ambition. `quote` prints the curve so the rung is
chosen, not drifted into:

```
$ python3 scripts/gauntlet.py quote --current-score 4
  target  waves  calls  ...
  7       6      ~42    fits
  8       10     ~70    needs +2 wave(s)
  9       18     ~126   needs +10 wave(s)
  10      —      —      not priceable: bar-met cannot fire at 10
```

The model behind the numbers, so it can be argued with: one gap is roughly one
score point up to 7 (the usable rung), and each point above 7 costs about
double the one before. That doubling is not styling — refinement gains taper
across iterations (Madaan et al.) and cost efficiency settles early and rarely
recovers (the CPI finding), both in `authorities.md`. The 10 row is a wall,
not a rung: the script cannot count a bar-met round at 10, so a 10 belongs in
the stretch line as prose.

Two uses, one command. **At intake**, quote from first light's score and put
the menu in the contract next to TARGET and BUDGET (`intake.md`). **At wave
boundaries**, quote again with no flags: it re-prices each open lane from its
last score, and swaps the rounds-per-gap guess for the measured cost per
closed gap once the log has one — the estimate you started with is dead the
moment there are actuals. That re-quote is also what prices an extension
offer in rungs instead of vibes (`stop-conditions.md`).

It is an estimate to choose by, never a promise — the stop conditions, not
the quote, decide when the run ends.

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

## When the budget tightens: degrade detail, never drop the frame

An engine that misses its frame budget lowers resolution; it does not skip the
frame. When token burn runs ahead of progress mid-run, degrade in this order,
each step recorded in the log where the evidence it weakens will be read:

1. Routine critic rounds drop to the screening tier (`--tier screening`).
2. Micro-round batching widens — more gate-verified builds per verdict.
3. Repeat-critic scoping tightens; full re-reads stay at decision rounds.
4. The lowest-ranked funded lane is parked, returning its rounds to the pool.

What never degrades: deciding-tier verdicts at lifecycle turns, the champion
guard, evidence in the log, and the budget stop itself. A dropped frame here is
an unjudged build or a silent self-extension — the two dishonesties the method
cannot survive. If the ladder is exhausted and burn still outruns progress, that
is the stop talking, not a call for a cheaper loop.

## When the honest answer is "stop spending"

Cost discipline includes saying the loop is not worth more money:

- cost per closed gap is climbing and the open gaps are cosmetic
- every open dimension is parked or stalled
- the remaining gap is a source-asset or architecture problem that lane-level
  rounds cannot reach

Say it plainly, with the numbers from `status`. The cheapest wave in any run is
the one that never ran.
