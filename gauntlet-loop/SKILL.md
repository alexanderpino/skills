---
name: gauntlet-loop
description: Run an adversarial build-and-judge quality loop (Gauntlet Loop) to push inspectable artifacts to a reachable target bar via autonomous rounds, parking lanes that stop paying for themselves. Trigger on "gauntlet", "blind critic", "beat the reference", "keep iterating until it wins", "make it as good as X". Do not trigger for ordinary code review or bug fixing.
---

# Gauntlet Loop

> **Set a reachable bar. Cut the lanes. Build. Judge blind. Park what stalls.**

The method is Matt Shumer's, published 27 July 2026 as the technique behind the
"Claude of Duty" run (`https://somethingbig.ai/gauntlet-loop`, prompt at
`https://github.com/mshumer/Claude-of-Duty`). This skill adds an intake contract,
a champion/challenger regression guard, deterministic state tooling,
per-dimension bars, a WIP limit, a park rule for stalled lanes, and named failure
modes. Credit Shumer for the pattern; be honest about which parts are additions.

A quality-*maximising* loop, not a correctness loop, run under a fixed budget: a
builder closes one named gap, a *different* critic in fresh context judges the
real artifact against a real bar, and the lanes that stop paying stop getting
funded. What separates it from a review, and where each rule comes from:
→ `references/authorities.md`

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
  ceiling. When it depletes the run *stops*; then you may **offer** an extension.
  You may never take one.
- **Subagents make critics honest.** Without them the method degrades — see
  "Degraded mode".

## Cost discipline

A wave spends real money, and most of it is spendable on things that buy nothing.
Rationale and exceptions: → `references/cost-discipline.md`

1. **Machine gates before critics.** A dimension a command can decide is decided
   by that command, logged `--mode rubric` with the number as evidence.
2. **One critic call per round.** One inspection answers both comparisons and
   writes two records. Split only when the round could retire a dimension.
3. **Paths, not payloads.** Subagents get paths, owned files and one gap line.
4. **Cap the handoffs.** Critic: the verdict block. Builder: five lines.
5. **No gap, no builder.** Nothing to close means retire, raise the bar, or park.
6. **Respect the WIP limit** (default 3). Depth closes gaps; breadth half-closes.
7. **Let the script count and publish.** `status` and `board` are free — never
   narrate state into chat or hand-write the workbench.
8. **Route the model to the role:** cheapest that can do the job, never cheaper
   on a deciding critic, tier fixed within a lane. → `references/model-routing.md`
9. **Never pay twice for the same verdict.** Settled work is not re-judged.
10. **Read each reference once, at its phase.**

## State: one directory, one script

`scripts/gauntlet.py` (stdlib-only) owns all run state under `gauntlet/`. The
model judges; the script counts.

`gauntlet/` holds `config.json` (lanes, dimensions, stops, WIP, parks,
extensions), `contract.md`, the frozen `bar/`, `ownership.md`, `backlog.md`,
`rounds.jsonl` (the log — script-written only), and the generated `workbench.md`
and `report.md`. Layout and git conventions: `references/state-and-resume.md`.

```bash
python3 scripts/gauntlet.py init --lanes a,b --dimensions visual,perf \
    --bar-kind reference --budget-waves 8 --target-score 7 --wip-limit 3
python3 scripts/gauntlet.py log-round --wave 2 --lane a --dimension visual --round 3 \
    --mode blind --winner other --margin clear --score 7 --severity major \
    --gap "..." --evidence shots/w2r3.png
python3 scripts/gauntlet.py status   # state, next-wave plan, park list, fired stops
python3 scripts/gauntlet.py park --lane a --dimension visual --reason "..."
python3 scripts/gauntlet.py board    # regenerate workbench.md from the log
python3 scripts/gauntlet.py extend --waves 3 --reason "..."   # only on a user grant
python3 scripts/gauntlet.py report   # draft the end-of-run report
```

Log every comparison through the script — the validation is the point.

## Phase 0 — First light

**Before the contract, not after it.** Get one real artifact and one working
inspection path in front of the user in a single step. Nothing here needs
permission — it is one build in the workspace, it is reversible, and it is what
makes every later decision concrete.

1. **Build the thinnest end-to-end thing** — a walking skeleton, not one polished
   part. If the artifact already exists, skip the build and capture it.
2. **Verify inspection on it**: take the screenshot, run the benchmark, render
   the page. The failure that otherwise wastes hours, caught in minutes.
3. **Judge it once** against a candidate bar — one critic, one verdict, in the
   block from `references/critic.md`: `SCORE` (0–10), `WINNER`, `MARGIN`,
   `GAP SEVERITY` (major / minor / none), `LARGEST GAP`, `EVIDENCE`. Score it
   against a **provisional target of 7**; Phase 2 sets the real one. Read that
   brief now — this is the one place the loop needs it before Phase 4.
4. **Show the user** the artifact and the verdict.

Then the arithmetic, out loud, on **provisional** numbers — the lanes you expect
to cut and the default WIP limit of 3, both re-checked at Phase 3:

> rounds you estimate per gap × lanes ÷ WIP limit ≈ waves needed

Estimate the numerator from first light's own `GAP SEVERITY`, and say which
reading you took so it can be argued with: a `minor` gap with a named fix is
usually one round, a `major` gap two or three, and a gap the critic calls
structural is not closeable at lane level at all — a rescope, not a number.

Three answers fall out of this one step, each cheaper here than anywhere later:
whether inspection works, whether the bar is sharp enough to discriminate (a
vague verdict means fix the bar, not run the wave), and whether the projection
fits a budget. If it does not fit, **rescope before wave 1** — drop the
lowest-ranked lane, lower the target (the old one becomes the stretch), or ask
for more budget. Say which you chose.

Two exemptions, because first light runs before `init` exists:

- **Its comparison is the one that does not go through the log.** Record the
  verdict in `contract.md` when you write it; every later comparison is logged.
- **Its bar is a *candidate*** — a reference you propose, not yet frozen.
  Freezing under `gauntlet/bar/` happens at Phase 2, once the contract names it.

It also runs **regardless of tree state**. The dirty-tree refusal and any
`git init` consent belong to the contract, before the first funded wave — not in
front of the user's first look at anything. **Commit first light's output before
that check runs**: it is the wave-1 baseline the champion guard arms against, and
committing it is what makes the tree clean for wave 1.

## Phase 1 — The contract

Never loop unattended without this settled. Read `references/intake.md`, put a
compact contract in front of the user, get confirmation. Infer or propose
everything you can; only **stops**, **kill criteria** and **budget** genuinely
require the user, because they encode how much time and money the run may spend.

**Size the contract to the run.** Under ~3 waves or 2 lanes, four lines is the
whole contract — goal, target bar, budget, stops — confirmed in one exchange.
The full table below is for long unattended runs, where the fields you skip are
the ones nobody can add later.

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
- **Set `--target-score` where the target sits** (default 7). A target of 10
  means no lane can ever retire; the script warns you.
- **Ambition above it is a *stretch***, recorded in `contract.md` as a heading
  rather than a promise. Retirement is judged against the target only; the report
  states the distance to the stretch.
- **Freeze the bar** under `gauntlet/bar/`, and **declare each dimension**
  (visual + frame time; clarity + completeness) in `config.json`, judged
  separately. One collapsed score is how a loop trades away the dimension nobody
  is watching.
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
list, as printed by `status`. Phases 4–6 cycle until a stop fires.

**Wave setup, once, before any lane starts:** take the champion commit. That one
ref is every lane's `--champion-ref` for the wave. Concurrent per-round commits
contend on the git index and capture each other's half-built trees — disjoint
*file* ownership does not make the index disjoint (`state-and-resume.md`).

Then, per lane, per round:

1. **Build.** Builder gets the lane goal, the bar path, the current artifact and
   the last named gap — not the previous builder's reasoning.
   → `references/builder.md`
2. **Gate, then judge.** Run any machine gate first — a dimension failing its own
   benchmark needs no critic. Then one critic call covering both comparisons
   (→ `references/critic.md`, `references/blind-protocol.md`):
   - **Promotion:** challenger vs champion. Wins → promote; loses → revert. The
     regression guard; skipped only on a lane's first round.
   - **Bar:** ours vs the target bar, per dimension — produced on every round,
     including a reverted one, where it judges the surviving champion. Gives the
     winner, margin, gap and severity that drive the streaks.
3. **Log both** through `log-round` (`--mode champion`, then `--mode
   blind`/`rubric`). Every record names its `--dimension`; the script rejects
   undeclared ones, because a lane cannot retire on dimensions nobody judged.
   Under a blind protocol the critic returns `WINNER: A | B` — you hold the label
   mapping and log `ours`/`other`; never ask the critic which side was ours.
4. A bar verdict with severity `major`/`minor` and no specific gap is invalid and
   rejected. A `none` verdict must still cite what it inspected.

**Promotion and revert commits are issued by you, serially, as verdicts land** —
never by builders and never in parallel. They are path-scoped to the lane's owned
files, which is what keeps one wave snapshot sufficient.

**Run independent lanes concurrently.** Spawn the wave's builders in a *single
message*, and spawn each lane's critic the moment **that lane's** builder returns
— not when the slowest one does. A critic reads paths and owned files, never
another lane's output, so waiting buys nothing. A wave's wall-clock is then the
slowest *lane* rather than the sum of all of them: at a WIP limit of 3, roughly a
third of the elapsed time for identical cost.

**Serialise a pair instead when one lane's result changes what "good" means for
the other** — lighting before materials, information architecture before
paragraph polish (`references/decomposition.md`). Concurrency is the default for
independent lanes, not a rule that overrides dependency. The mechanics, so two
agents resolve it the same way: a serialised pair **occupies both its slots in
the same wave**, the dependent lane's builder spawns when the upstream lane's
*verdict* lands (not when its builder returns), and the wave's other lanes are
unaffected and still run concurrently.

**Two in-wave barriers, and they earn it:** the smoother at the end of a wave and
the wave-boundary review. The champion snapshot is wave *setup*, before any lane
starts, so it is not a third. Machine gates and logging run inline. Never block on
the user mid-wave; check-ins belong at boundaries, if autonomy asked for them.

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
- **Park** what `status` flags as stalled — no movement in `no_progress_n`
  rounds, reverts outpacing promotions, or the same gap three rounds running:
  `park --lane <l> --dimension <d> --reason "<log read>"`. Parking is not failure
  and not a verdict on the artifact; it is the decision to stop paying for rounds
  that stopped buying anything, and the open gap goes to the user in the report.
  Resume only on *new evidence* — a re-cut, a fixed inspection path, a new source
  asset, a revised bar. "It might work this time" is sunk cost with extra steps.
- **Re-cut** when the smoother reports the same seam twice, or two lanes' critics
  keep citing each other's territory. Between waves, never mid-wave; the protocol
  — evidence, `init --force`, the deliberate streak reset — is in
  `references/decomposition.md`.
- **Reallocate** — a retired or parked lane promotes the next one in. Re-check
  the feasibility arithmetic if the budget now looks tight.
- **Check the kill criteria** from intake. They fire early on purpose.
- **Publish** with `board`. Free, and it keeps the user out of your context.

## Phase 7 — Stop and hand off

When a stop fires, finish the wave and the smoother (unless it is a safety stop),
promote the best champion — not necessarily the latest challenger — then `board`,
`report`, and complete it:

- Target bar used, whether it was raised mid-run, distance left to any stretch
- Lanes: rounds each, and how each ended — retired, parked, still open
- Gaps closed, and — the part the user actually needs — **gaps still open**
- Cost: calls spent, and calls per closed gap
- Blind vs rubric round counts (not equivalent evidence)
- Your honest read on whether the loop was still improving at the stop

Do not soften the open-gaps section. A report that reads as a victory lap is
worth less than one that says exactly where the artifact is still weak.

### When the budget depletes, offer an extension

A budget stop means the money ran out, not that the artifact is done. Stop,
report, then put **one priced block of waves** in front of the user. `status`
prints the material as soon as the budget fires:

```
Budget depleted at wave 8. Stopped, smoothed, report written. ~54 calls, 6 gaps closed.
  imagery/visual   still moving — score 5→7, severity major→minor; open gap: <gap>
  imagery/perf     parked at wave 6 — flat 3 rounds; open gap stays in the report
Extension of 3 waves ≈ 21 subagent calls on imagery/visual alone.
My read: worth it for visual. Extend 3, re-cut, or stop here?
```

- **The user grants it. You never self-extend**, and never keep looping while you
  ask. A budget that extends itself is not a budget.
- **Park before you price**, over funded lanes only, in intake's units. `extend`
  refuses otherwise — pricing over stalled lanes funds exactly the rounds the log
  calls worthless.
- **A block, not a tap:** two to four waves. Wanting another twelve is a re-cut.
- **Lead with the honest read, and recommend stopping when it says stop.**
  Selling an extension you do not believe in is the most expensive thing you can
  do in this skill.
- **Record it** in `config.json`, the report and `contract.md`.

A hard cap agreed at intake is the real ceiling and the script will not cross it.
Full protocol, including when the offer is "stop": `references/stop-conditions.md`.

## Non-negotiables

- **No builder grades its own homework.** Separate agent, fresh context. (They do
  *inspect* their output before handoff — a smoke test, not grading.)
- **Critics inspect the artifact, never a summary of it.**
- **Blind where blindable; label the mode honestly where not.**
- **Name the gap or the round didn't happen.** Enforced by the script.
- **The target bar never moves down.** Raising it mid-run is allowed, announced.
- **Losers get reverted** — what stops a long run wandering downhill one
  plausible-sounding round at a time.
- **A stalled lane gets parked, not one more push.**
- **Settled work is not re-judged.** Closed gaps stay closed, retired dimensions
  stay retired; regressions are caught by the champion comparison and the machine
  gates, and reported with evidence — never re-argued.
- **Scope is frozen at the contract.** Re-cuts redistribute; they never expand.
- **Every comparison goes through the log** (first light excepted — it predates
  `init`). State the model remembers is state the run will lose.
- **The budget is extended by the user or not at all.**
- **Visible text is Simplified Technical English (ASD-STE100):** active voice, one
  statement per sentence, 20–25 words max, no marketing language.

## Failure modes

Read `references/failure-modes.md` before long unattended runs. The short list:

| Mode | Signal |
|---|---|
| Critic sycophancy | Everything passes; gaps get vaguer |
| Rubric gaming | Builder matches the critic's wording, not the bar |
| Bar erosion | Comparisons quietly get easier |
| Unreachable bar | Every round fails; scores never move |
| Progress theatre | Rounds logged, artifact unchanged |
| Zombie lane | Same gap, round after round, still funded |
| Ceiling denial | The same gap recurs; reverts climb |
| Lane collision | Two lanes fight over one file |
| Downhill drift | Late output worse than mid-run |
| Context bleed | Critic echoes the builder's justifications |
| Gold plating | Rounds spent past the target on a retired dimension |
| Re-litigation | Closed gaps re-argued; retired dimensions re-judged |
| Scope snowball | More lanes at wave 6 than wave 1; projection doubled |
| Token burn | Cost per closed gap climbing wave over wave |
| Budget creep | Extensions granted repeatedly, each "nearly there" |
| Inspection rot | Stale or missing evidence |

## Degraded mode (no subagents)

Isolation weakens but the method survives: run critics as separate explicit
passes receiving only the artifact and the bar, never carry builder rationale
across, keep logging through the script. Say plainly that critic independence is
weaker than a real context boundary. With no file access at all, offer the method
as a manual protocol rather than claiming to run it.

## Scale expectations

A round is a builder call plus a critic call; a wave is that times the funded
lanes, plus a smoother — `init` prints the projection (3 lanes × 8 waves ≈ 56
calls) and `extend` prices the block. Concurrency cuts a wave's *wall-clock*, not
its cost. Say so before starting when the projection looks disproportionate to
the artifact, and watch cost per closed gap: when it climbs wave over wave, the
honest offer is a stop.

## Reference files

Each phase above cites the reference it needs — read it there, not upfront.
Three are not cited inline:

- `references/example-run.md` — one annotated run end to end. Read once before
  your first gauntlet; point users at it when they ask what they are agreeing to.
- `references/workbench.md` — the generated progress surface and the log schema.
- `references/authorities.md` — where these rules come from and what each forces.

Subagent briefs: `builder.md`, `critic.md`, `smoother.md`.
Tooling: `scripts/gauntlet.py` (init / log-round / status / park / board / extend / report).
