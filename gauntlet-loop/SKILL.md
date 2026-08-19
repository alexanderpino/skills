---
name: gauntlet-loop
description: Run an adversarial build-and-judge quality loop (Smart Gauntlet Loop) to push inspectable artifacts to a reachable target bar via autonomous rounds, spending judgement only where a decision lands and parking lanes that stop paying for themselves. The user needs no method vocabulary and no prepared prompt — a one-line wish plus an artifact is complete input; the skill composes the contract, bar, lanes and budget itself. Trigger on the INTENT — iterate an inspectable artifact (page, docs, README, copy, design, render, code quality) toward high or comparable quality — in any language and any wording, not on these example phrases: "gauntlet", "make it as good as X / like [product]", "keep iterating / keep going until it's genuinely great", "don't stop after one pass", "professional / production / best-in-class quality", "10/10", "hold up against this reference or example", Dutch "maak dit zo goed als X / blijf verbeteren tot het echt goed is", or when the user supplies reference material to match. Do not trigger for ordinary code review, bug fixing against failing tests, or small bounded edits.
---

# Gauntlet Loop

> **Work smarter, not harder.**

That is the whole skill, and it is a decision rule rather than a slogan. A
gauntlet loop's natural drift is to work *harder* — more rounds, more re-checking,
more coverage — all of which feel like rigour and are only cost. So when you are
choosing between two moves here, take the one that closes the gap with less work,
and when you are tempted to add a step, ask the test every rule in this file has
to pass: **does it make the loop smarter, or only busier?**

This is the **smart gauntlet loop**: Shumer's engine run the way a real-time
engine runs a frame. A game engine does not render a *better* scene than the
naive renderer — it renders the **same scene**, indistinguishable to the
player, at a fraction of the cost, by never spending where the eye is not
looking: detail scaled to distance, unchanged regions reused, the cheapest test
rejecting first, static light baked once. Every cost rule below is one of those
moves with the names changed (`references/authorities.md`). The promise is the
same: **the result the full-grind loop would have reached — the same bar met,
deciding-grade rigour at every decision — faster and cheaper**, and the report
proves it against the intake projection rather than asserting it.

The method is Matt Shumer's, published 27 July 2026 as the technique behind the
"Claude of Duty" run (`https://somethingbig.ai/gauntlet-loop`, prompt at
`https://github.com/mshumer/Claude-of-Duty`). This skill adds an intake contract,
a champion/challenger regression guard, deterministic state tooling,
per-dimension bars, a WIP limit, a park rule for stalled lanes, and named failure
modes. Credit Shumer for the pattern; be honest about which parts are additions.

## The loop, and the guardrails around it

**The engine is Shumer's and stays recognisable.** Cut the goal into
independently judgeable lanes. Per lane: a builder closes one named gap, then a
*different* critic in fresh context judges the real artifact against a real
external bar, blind where the artifact allows. Bar wins → the critic names the
single largest remaining gap and it goes back. Repeat.

Everything else in this file is one of two things: a **guardrail** against a
known weakness of that loop, or the **project management** deciding what gets
funded. Both serve the loop. A rule that stops the loop from running is a wrong
rule, and a guardrail that adds work without removing more work elsewhere fails
the mantra even when the weakness it names is real.

The weaknesses, their signals, and the guardrail each one buys, in one table:
→ `references/failure-modes.md`
Provenance for each rule: → `references/authorities.md`

## What the user must supply: almost nothing

There is no "gauntlet prompt" to write, and never send a user away to write
one. A one-line wish plus an artifact — "make this landing page genuinely
good", "get these docs to the level of X" — is complete input. Composing the
gauntlet is this skill's own Phase 0–2 work: first light produces something
to look at, the bar is found and proposed (`references/bar-selection.md`:
never ask the user to define "good"), the lanes are cut, the menu is priced,
and the whole thing comes back as **one contract block to confirm, not a
form to fill in**. The only three things genuinely theirs to decide — stops,
kill criteria, budget — arrive as proposals with numbers attached. A user
who does know the method can pre-specify any of it; a user who has never
heard of it gives up nothing.

## When not to use this

- **Correctness work with a pass/fail oracle** — that is a debug loop. Fix it
  first, then gauntlet the quality.
- **Artifacts nobody can inspect.** Fix the inspection path first, or you have
  only an opinion exchange.
- **Small bounded edits.** A gauntlet on a 20-line change is theatre.
- **Subjective taste with no comparator**, unless the user supplies one.

If the work is mostly correctness-and-coordination, suggest a plan/execute
orchestrator instead. The two compose: orchestrate to *done*, gauntlet to *good*.

## Requirements and blast radius

- **Version control is required** — the champion/challenger guard is built on it.
  Refuse to start **wave 1** on a dirty tree, so the first champion is a known
  state and a full abort is one command. No VCS? `git init` with consent, also
  before wave 1. Phase 0 is exempt: it runs on any tree.
- **Writes are confined** to the workspace and `gauntlet/`; builders write only
  files they own this wave. **Under Mission Control**, initialise inside the
  assigned worktree (`mc/<id>`), never the repo root, and cut lanes that respect
  the Implementer's semantic leases.
- **The budget stop is always armed.** Never offer an unattended loop without a
  ceiling; when it depletes the run *stops*.
- **Subagents make critics honest.** Without them the method degrades — see
  "Degraded mode".

## Cost discipline

A wave spends real money, and most of it is spendable on things that buy nothing.
Rationale and exceptions: → `references/cost-discipline.md`

1. **Machine gates before critics.** A dimension a command can decide is decided
   by that command, logged `--mode rubric` with the number as evidence.
2. **One critic call per round — or fewer.** One inspection answers both
   comparisons and writes two records. When the named gap splits into
   gate-checkable pieces, batch up to three gate-verified micro-builds into one
   judgement. Split into two calls only when the round could retire a dimension.
3. **Paths, not payloads — and scoped paths after round one.** Subagents get
   paths, owned files and one gap line; a repeat critic gets the bar, the diff
   and the judged region, with a full re-read at decision rounds.
4. **Cap the handoffs.** Critic: the verdict block. Builder: five lines.
5. **No gap, no builder.** Nothing to close means retire, raise the bar, or park.
6. **Respect the WIP limit** (default 3). Depth closes gaps; breadth half-closes.
7. **Let the script count and publish.** `status`, `board`, `quote` and `plan`
   are free — never narrate state into chat or hand-write the workbench.
8. **Route the model to the decision, not just the role.** Screening-tier
   verdicts steer routine rounds; a deciding-tier verdict is bought where a
   lifecycle turns — retire, park, promote into a shared surface. Logged
   `--tier`; the script refuses to retire on screening evidence.
   → `references/model-routing.md`
9. **Never pay twice for the same verdict.** Settled work is not re-judged, a
   check whose inputs have not changed is not re-run (`gate` caches on a content
   hash), and the frozen bar is measured **once** — bake its machine numbers at
   the freeze, never re-derive them per round.
10. **Read each reference once, at its phase.**

## State: one directory, one script

`scripts/gauntlet.py` (stdlib-only) owns all run state under `gauntlet/`. The
model judges; the script counts.

`gauntlet/` holds `config.json` (lanes, dimensions, stops, WIP, parks,
extensions, **gates**), `contract.md`, the frozen `bar/`, `ownership.md`,
`backlog.md`, `rounds.jsonl` (the log — script-written only), and the generated
`workbench.md` and `report.md`. Layout and git conventions:
`references/state-and-resume.md`.

**Declare gates before wave 1**, one `config.json` entry per mechanical check:
`{"name": ..., "cmd": "<shell; fails on non-zero exit or any stdout>", "paths":
["<every file the check reads>"]}`. `paths` is what the cache hashes, so an
undeclared input makes the gate skip when it should run (`cost-discipline.md`).
Both `cmd` and `paths` resolve from the directory the script is invoked in —
always run it from the workspace root (under Mission Control, the worktree
root), or every path silently resolves to nothing; `gate` warns when a gate's
paths match no file, and never caches such a gate. An answer key is a gate
farm: every mechanically checkable item in it becomes a gate here at init,
checked free every wave, leaving the critics only the judgement items
(`references/bar-selection.md`).

```bash
python3 scripts/gauntlet.py init --lanes a,b --dimensions visual,perf \
    --bar-kind reference --budget-waves 8 --target-score 7 --wip-limit 3 \
    --budget-tokens 1500000
python3 scripts/gauntlet.py log-round --wave 2 --lane a --dimension visual --round 3 \
    --mode blind --winner other --margin clear --score 7 --severity major \
    --gap "..." --evidence shots/w2r3.png --tokens 74000 --critic-model sonnet
python3 scripts/gauntlet.py gate     # mechanical checks; skips those whose inputs are unchanged
python3 scripts/gauntlet.py status   # state, next-wave plan, park list, fired stops
python3 scripts/gauntlet.py quote --current-score 4   # the quality-price menu: what 7, 8, 9 cost; 10 is not a price
python3 scripts/gauntlet.py plan --current-score 4    # draft plan.md: build stages in order, priced — the forward scaffold
python3 scripts/gauntlet.py park --lane a --dimension visual --reason "..."
python3 scripts/gauntlet.py board    # regenerate workbench.md from the log
python3 scripts/gauntlet.py extend --waves 3 --reason "..."   # only on a user grant
python3 scripts/gauntlet.py report   # draft the end-of-run report
```

Log every comparison through the script — the validation is the point. Waves are
the unit the user agreed to; **tokens are the unit that actually burns**, so pass
`--tokens` on each round and `status` will print cost per closed gap in the unit
the bill arrives in. Without it, `status` says `tokens: not measured`, which is
the honest reading and a poor one.

## Phase 0 — First light

**Before the contract, not after it.** Get one real artifact and one working
inspection path in front of the user in a single step. It needs no permission:
one reversible build in the workspace.

1. **Build the thinnest end-to-end thing** — a walking skeleton, not one polished
   part. If the artifact already exists, skip the build and capture it.
2. **Verify inspection on it**: take the screenshot, run the benchmark, render
   the page. The failure that otherwise wastes hours, caught in minutes.
3. **Judge it once** — one critic, one verdict, in the block `references/critic.md`
   defines. Read that brief now; this is the one place the loop needs it before
   Phase 4. Put the candidate bar in `gauntlet/bar-candidate/` and give the critic
   *that* path — `gauntlet/bar/` does not exist yet. A candidate bar is the user's
   named comparator, or one you propose in a line: an external artifact you can
   open, not a checklist you wrote. Score against a **provisional target of 7**;
   Phase 2 sets the real one.
4. **Show the user** the artifact and the verdict.

Then the arithmetic, out loud, on **provisional** numbers: the *lanes* you expect
to cut (independently judgeable parts of the artifact — Phase 3) and the default
*WIP limit* of 3 (lanes funded per wave), both re-checked at Phase 3:

> rounds you estimate per gap × lanes ÷ WIP limit ≈ waves needed

Estimate the numerator from first light's own `GAP SEVERITY`, and say which
reading you took so it can be argued with: a `minor` gap with a named fix is
usually one round, a `major` gap two or three, and a gap the critic calls
structural is not closeable at lane level at all — a rescope, not a number.

Act on what the step returns, and say which branch you took.

- A **vague verdict** means fix the bar, not run the wave.
- A **verdict already at or above the provisional 7** — common when the artifact
  already existed — means there is no gap to fund, so do not open wave 1. Raise
  the bar to something the artifact demonstrably misses and re-judge, or tell the
  user it is already there and stop. A run opened against no named gap buys
  nothing.
- A **projection that misses the budget** means rescope before wave 1 — drop the
  lowest-ranked lane, lower the target (the old one becomes the stretch), or ask
  for more budget.
- A **target the first measurement already disproves** — a 2× speedup asked of a
  loop the profile shows at its hardware floor — is refused before wave 1, with
  the number. Say what the measured ceiling is, under which constraints it holds,
  what would have to change to move it (a different algorithm, a different
  scope: a different contract), and the nearest target that *is* reachable.
  Running waves toward a proven impossibility spends the budget re-proving the
  first measurement. → `references/bar-selection.md`

Two exemptions, because first light runs before `init` exists: its verdict is the
one comparison not logged — record it in `contract.md` instead — and it runs
**regardless of tree state**. **Commit its output before the clean-tree check**:
that commit is the wave-1 baseline the champion guard arms against, and it is
what makes the tree clean. With no repo the order is: consent → `git init` →
commit first light → clean-tree check.

## Phase 1 — The contract

Never loop unattended without this settled. Read `references/intake.md`, put a
compact contract in front of the user, get confirmation. Infer or propose
everything you can; only **stops**, **kill criteria** and **budget** genuinely
require the user, because they encode how much time and money the run may spend.

**Size the contract to the run.** Under ~3 waves or 2 lanes, four lines is the
whole contract — goal, target bar, budget, stops — confirmed in one exchange.
The full table below is for long unattended runs, where the fields you skip are
the ones nobody can add later.

**Price the target as a menu, and anchor its rungs.** `quote` turns first
light's score into the quality-price menu — what 7, 8 and 9 cost, and that 10
is not a price (bar-met cannot fire there). A rung must also *mean* something:
three questions per ambitious dimension — what must n/10 concretely do; where
is "I would ship this"; what is explicitly *not* needed — become one anchor
line per rung in `contract.md`, so the offer reads anchor + price and TARGET
and BUDGET are chosen together (`references/intake.md`). Anchors are for
choosing, never for judging — the critic still scores against the frozen bar.
Autonomous with no rung named? Default to 7 and record the menu, so the
unmade choice stays visible.

**Then hang the run on the scaffold.** `plan` drafts `gauntlet/plan.md` — the
build stages in order (bootstrap → everything to usable → the ambitious rungs
→ stretch on a grant), each priced; you add the anchors and the serialised
pairs. Regenerate at wave boundaries, where prices move from the intake guess
to measured actuals. The workbench looks backward; the plan looks forward.

Fields, each explained in `intake.md`: **goal** (destination, not route) ·
**target bar** per dimension · optional **stretch** · **inspection** (and which
dimensions have machine gates) · ranked **lanes** + WIP limit · armed **stops** ·
**kill** criteria · **budget** with projected call count and optional hard cap ·
**autonomy**.

Stops (`references/stop-conditions.md`): `bar-met`, `clean-streak`,
`no-progress` (parks a lane), `budget`, `judgment` — armed in combination, first
to fire wins.

**Cold start is normal.** With no artifact yet, wave 1 is a bootstrap wave: first
versions, no champion comparison, first bar comparison as soon as there is output
to inspect. Do not invent a fake baseline.

## Phase 2 — Set a reachable bar

The highest-leverage decision in the run. → `references/bar-selection.md`

- **External and inspectable**, and **reachable inside the budget**. A target
  nobody can hit is not ambition: every round fails, every lane looks stalled,
  and the log stops carrying information.
- **Set `--target-score` where the target sits** (default 7). The script counts
  a bar-met round only at or above it, so a target of 10 means bar-met never
  fires; the script warns you.
- **No bar, no run.** The loop's output is "A or B is better"; a B the agent
  invented while building A measures nothing. If there is no comparison
  material, run `bar-request` — it writes `gauntlet/bar-request.md` naming what
  would settle each dimension, for the user or a scout agent to fetch — and
  stop until it arrives. `log-round` refuses bar-mode records while
  `gauntlet/bar/` is empty. For genuinely novel artifacts the bar is a
  research-backed **spec and answer key**, authored before wave 1 and frozen
  like any bar. Matt Pocock's `wayfinder` produces exactly this — run with one
  modification: *one map and one answer key, not a ticket each* (the answer
  key is the bar, and a bar is one frozen file, not fourteen tickets). An
  answer key bars function well and taste badly, so aesthetic dimensions still
  need a reference artifact of their own. And mid-run, a question whose answer
  is a *choice* is escaped fog: back to the map or the user, never decided ad
  hoc by a builder. → `references/bar-selection.md`
- **Targets are per dimension when the ambitions differ** —
  `--dimension-targets "gameplay=8,graphics=6"`, and retirement on each
  dimension is judged against its own number. A blanket "10/10 like the
  reference" is not a target, it is an unpriced wish: decompose it with the
  user — ask what n/10 each dimension must reach — because the same 10 that is
  merely expensive on gameplay rules is unreachable-by-iteration on animation
  and shader craft against a AAA bar. Price the reachable rungs (`quote`),
  refuse the disproved ones with evidence, and never let one dimension's wall
  sink the rungs the others can reach.
- **Ambition above it is a *stretch***, recorded in `contract.md` as a heading
  rather than a promise. Retirement is judged against the target only; the report
  states the distance to the stretch — and the stretch is what a surplus buys
  (Phase 7), so write it as a real bar, not a mood.
- **Freeze the bar** under `gauntlet/bar/`, and **declare each dimension**
  (visual + frame time; clarity + completeness) in `config.json`, judged
  separately. One collapsed score is how a loop trades away the dimension nobody
  is watching.
- **Bake the bar's numbers at the freeze.** Run every machine measurement the
  bar allows — frame times, sizes, counts, scores — once, into
  `gauntlet/bar/measurements.md`. Critics get the numbers; nobody re-derives a
  frozen artifact's metrics per round. Judgement is never baked, only
  measurement — paraphrasing the bar is erosion (`failure-modes.md`).
- **Place it on the ladder:** *testable* is the precondition Phase 0 produces,
  *usable* is where the target belongs, *lovable* is where a stretch belongs. A
  gauntlet does not generate POC → MVP → MLP; it moves one artifact up. If the
  user actually needs to decide **whether to build at all**, that is discovery
  work — say so rather than polish an unvalidated idea.

## Phase 3 — Cut and rank the lanes

Split the goal into **lanes**: the smallest units that can be improved and judged
independently. You cut them, not the user. → `references/decomposition.md`

- **The lane test:** can a fresh critic look at this one thing and say which of
  two versions is better, without needing the rest?
- **Rank them**, because a wave funds `wip_limit` lanes and not all of them:
  value to the goal × how closeable the gap looks at lane level ÷ cost per round.
  Starving every lane equally is the commonest way a budget produces nothing
  finishable.
- **One file, one owner, per wave**, in `gauntlet/ownership.md`. This is also
  what lets the wave run concurrently.
- **The lane set is frozen at the contract.** Between waves it can be merged,
  split, re-ranked or replaced; it does not *grow* because the run noticed more
  work — a new lane needs a slot freed by a retirement or a park. Everything else
  anyone notices goes to `gauntlet/backlog.md`, one line, and returns in the
  report as work the user can choose to buy. Never as scope this run added.

## Phase 4 — Run the waves

A wave is one pass over the **funded** lanes — the top `wip_limit` of the ranked
list, as printed by `status` — at **one round per lane per wave**. Phases 4–6
cycle until a stop fires. `status` also names the **build stage**: dimensions
below their usable line are funded before any dimension buys a rung above it —
whole-and-crude beats one-part-excellent, enforced in the ranking.

**Wave setup, once, before any lane starts:** take the champion commit. That one
ref is every lane's `--champion-ref` for the wave. Concurrent per-round commits
contend on the git index and capture each other's half-built trees — disjoint
*file* ownership does not make the index disjoint (`state-and-resume.md`).

Then, per lane, per round:

1. **Build.** Builder gets the lane goal, the bar path, the current artifact and
   the last named gap — not the previous builder's reasoning.
   → `references/builder.md`
   When the gap splits into gate-checkable pieces, the builder may take up to
   three **micro-rounds** — build, run `gate`, build again — before one critic
   judges the accumulated result. The champion guard still arms at that
   judgement; log `--diff-lines` so the tripwire can read the round.
2. **Gate, then judge.** Run `gate` first — a dimension failing its own benchmark
   needs no critic — and hand its output to the critic. `gate` is lane-agnostic
   and safe to run concurrently: its cache is locked, and a suite whose inputs
   another lane just moved simply re-runs. Machine checks cost seconds; making
   them a wave barrier to save those seconds would cost a wave. Then one critic
   call covering both comparisons
   (→ `references/critic.md`, `references/blind-protocol.md`):
   - **Promotion:** challenger vs champion, **blind by default** — both sides
     are ours, so this comparison is always blindable even when the bar is not:
     export both under randomised labels, no history, and log `--blind`
     (`references/blind-protocol.md`). Wins → promote; loses → revert. The
     regression guard; skipped only on a lane's first round.
   - **Bar:** ours vs the target bar, per dimension — produced on every round,
     including a reverted one, where it judges the surviving champion. Gives the
     winner, margin, gap and severity that drive the streaks. Routine rounds may
     run at `--tier screening`; a deciding-tier verdict is required wherever a
     lifecycle turns, and the script enforces it.
3. **Log both** through `log-round` (`--mode champion`, then `--mode
   blind`/`rubric`). Every record names its `--dimension`; the script rejects
   undeclared ones, because a lane cannot retire on dimensions nobody judged.
   Under a blind protocol the critic returns `WINNER: A | B` — you hold the label
   mapping and log `ours`/`other`; never ask the critic which side was ours.
4. A bar verdict with severity `major`/`minor` and no specific gap is invalid and
   rejected. A `none` verdict must still cite what it inspected.

**Run independent lanes concurrently.** Spawn the wave's builders in a *single
message*, and spawn each lane's critic the moment **that lane's** builder returns
— not when the slowest one does. A critic reads paths and owned files, never
another lane's output, so waiting buys nothing: identical cost, roughly a third
of the wall-clock at WIP 3.

**Promotion and revert commits are yours, issued serially as verdicts land** —
never by a builder, never in parallel. Path-scoped to that lane's owned files,
which is what keeps one wave snapshot sufficient. They serialise against each
other and block no lane.

**Serialise a pair instead when one lane's result changes what "good" means for
the other** — lighting before materials, structure before paragraph polish
(`references/decomposition.md`). The mechanics, so two agents resolve it the same
way: the pair occupies both its slots in the same wave, the dependent builder
spawns when the upstream *verdict* lands, and the other lanes are unaffected.

**Exactly two in-wave barriers:** the smoother, and the wave-boundary review.
Gates, logging and the champion snapshot are not barriers. Never block on the
user mid-wave; check-ins belong at boundaries, if autonomy asked for them.

## Phase 5 — Smooth

At each wave's end, one fresh agent over the parts that changed, resolving seams
between independently-improved lanes. Mandate: coherence, not redesign.
→ `references/smoother.md`

Skip only when the funded lanes touched genuinely disjoint files — check the
diff, do not assume. Never skip on a shared visual surface, a single document, or
one rendering pipeline.

## Phase 6 — The wave-boundary review

The cheapest phase in the loop and the one that decides whether the budget buys
anything. Run `status`, then act:

- **Retire** what met the target or ran out of closeable gaps; its budget returns
  to the pool.
- **Park** what `status` flags as stalled: `park --lane <l> --dimension <d>
  --reason "<log read>"`. It is not a verdict on the artifact — it is the decision
  to stop paying for rounds that stopped buying anything, and the open gap goes to
  the user in the report. Resume only on *new evidence*: a re-cut, a fixed
  inspection path, a new source asset, a revised bar. "It might work this time" is
  sunk cost with extra steps.
  **One tournament round before the park** when the stall is a ceiling within
  reach of the target: two builders, *differently framed* approaches to the same
  gap, judged blind three-way against the champion. The log has proven repetition
  dead on this lane; diversity is the one move not yet tried, it costs one extra
  builder call, and either it breaks the ceiling or it hardens the park report.
  Once per lane per run — a second tournament is grinding with extra steps.
- **Re-cut** when the smoother reports the same seam twice, or two lanes' critics
  keep citing each other's territory. Between waves, never mid-wave; the protocol
  is in `references/decomposition.md`.
- **Reallocate** — a retired or parked lane promotes the next one in. Re-check
  the feasibility arithmetic if the budget now looks tight.
- **Harvest gates.** Any gap a critic named this wave that a command could check
  becomes a gate in `config.json`. Gates accumulate; each one moves work
  permanently from a critic call to a free check, so late waves are cheaper
  *because* early waves happened. The run is meant to learn.
- **Re-verify inspection** — open one evidence artifact this wave cited and
  confirm it is real and current. A harness that broke silently makes every later
  critic call worthless.
- **Review the gates' blind spot** — once per run per machine-decided dimension
  (at a re-cut, or before that dimension retires): one deciding-tier verdict on
  "what about this dimension do these gates not see?", judged against the
  artifact. Gates are declared inside the run and nothing else ever reviews the
  suite (`references/cost-discipline.md`).
- **Check the kill criteria** from intake. They fire early on purpose.
- **Publish** with `board`. Free, and it keeps the user out of your context.

## Phase 7 — Stop and hand off

When a stop fires, finish the wave and the smoother (unless it is a safety stop),
promote the best champion — not necessarily the latest challenger — then **smoke
test the deliverable in its final state**: open, run or render the promoted
artifact once, end to end, *after* the smoother's edits. The promoted-and-
smoothed state is otherwise the one state of the artifact nobody ever inspected
as a whole — the smoother was the last writer and no critic judged its output.
Handing that over unopened is the failure every tester recognises. Then `board`
and `report`. `report` drafts every section from the log; you fill in the smoke
test (what you opened, what you saw), the one thing it cannot know — whether the
bar was raised mid-run — and your honest read.

**The surplus is the deliverable.** The promise of this variant is the same
result at lower cost, so when every lane retires with budget unspent, the
surplus **returns to the user by default** — stop, report, and state the
savings against the intake projection (`report` prints both numbers). A stretch
block — the contract's stretch re-armed as an announced target, same guards,
judged rounds — exists as an option the user may *buy* with the surplus; offer
it in one line, never roll into it, and never polish past a retired bar
unasked. Spending the savings without a grant is how "cheaper" quietly becomes
"the same price with extra steps".

Do not soften the open-gaps section. A report that reads as a victory lap is
worth less than one that says exactly where the artifact is still weak.

**Budget stop:** a budget stop means the money ran out, not that the artifact is
done. Run `status` — it prints the offer material, the honest read and the priced
block — and put that in front of the user. `extend` enforces the rest.
→ `references/stop-conditions.md`

## Non-negotiables

Four the script cannot check, so they are on you:

- **No builder grades its own homework.** Separate agent, fresh context. (They do
  *inspect* their output before handoff — a smoke test, not grading.)
- **Critics inspect the artifact, never a summary of it** — and blind where
  blindable, with the mode labelled honestly where not.
- **Losers get reverted.** What stops a long run wandering downhill one
  plausible-sounding round at a time. `log-round` checks the *record* says so;
  only you can make the working tree match it.
- **The target bar never moves down.** Raising it mid-run is allowed, announced.

The rest are enforced in `gauntlet.py` and it will say so at the point of use: a
round with no named gap is rejected, a record on a retired dimension warns, a
stalled lane must be parked before an extension can be priced, and an extension
needs a reason drawn from the log. Restating them here would be a second copy to
keep in sync — read the error message instead.

**Visible text is Simplified Technical English (ASD-STE100):** active voice, one
statement per sentence, 20–25 words, no marketing language. It binds what the run
*produces* — goals, gaps, verdicts, reports, the board — because that text is read
by agents and users who did not write it. This file is method prose, not run
output, and is not bound by the sentence ceiling.

## Degraded mode (no subagents)

Isolation weakens but the method survives: run critics as separate explicit
passes receiving only the artifact and the bar, never carry builder rationale
across, keep logging through the script. Say plainly that critic independence is
weaker than a real context boundary. With no file access at all, offer the method
as a manual protocol rather than claiming to run it.

## Scale expectations

A round is a builder call plus a critic call; a wave is that times the funded
lanes, plus a smoother. `init` prints the projection (3 lanes × 8 waves ≈ 56
calls); concurrency cuts a wave's wall-clock, not its cost. Say so before
starting when the projection looks disproportionate to the artifact.

## Reference files

Each phase above cites the reference it needs — read it there, not upfront.
Three are not cited inline:

- `references/example-run.md` — one annotated run end to end. Read once before
  your first gauntlet; point users at it when they ask what they are agreeing to.
- `references/workbench.md` — the generated progress surface and the log schema.
- `references/authorities.md` — where these rules come from and what each forces.

Subagent briefs: `builder.md`, `critic.md`, `smoother.md`.
Tooling: `scripts/gauntlet.py` (init / log-round / gate / status / quote / plan / park / board / extend / report).
