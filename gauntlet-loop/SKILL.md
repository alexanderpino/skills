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

## What it is

A quality-*maximising* loop, not a correctness loop — run under a fixed budget.

Decompose a goal into the smallest parts that can be improved and judged
**separately**. Each gets a builder and a *different* critic in fresh context.
The critic inspects the real artifact — rendered pixels, running binary, actual
prose, actual measurements — against a concrete external bar, blind wherever the
artifact allows. If the bar wins, the critic names the single largest remaining
gap and the work goes back. Then another round, on the lanes still moving.

Four properties make it a gauntlet rather than a review:

1. **The bar is external and inspectable.** Not "make it production-ready".
2. **The bar is reachable.** The target is where done actually is; ambition above
   it is a *stretch*, and a stretch never defines done.
3. **The builder never grades itself.** Justification is the enemy here.
4. **Rounds are earned, not scheduled** — and withdrawn when a lane stops paying.

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
  Refuse to start on a dirty tree, so the first champion is a known state and a
  full abort is one command. No VCS? `git init` with consent, before wave 1.
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
These decide whether the budget reaches a result. → `references/cost-discipline.md`

1. **Machine gates before critics.** A dimension a command can decide — test,
   benchmark, byte size, contrast ratio, LCP — is decided by that command and
   logged as `--mode rubric` with the number as evidence. Critics judge; they do
   not measure.
2. **One critic call per round by default.** The inspection is the expensive
   part; one call answers both comparisons and produces two log records. Split
   into two only when the round could retire a dimension, when the two verdicts
   pull opposite ways, or when a wrong promotion is expensive.
3. **Paths, not payloads.** Subagents get paths, owned files and one gap line —
   never pasted artifacts, bars or prior verdicts.
4. **Cap the handoffs.** Critic: the verdict block only. Builder: files touched,
   one line each, five maximum.
5. **No gap, no builder.** Nothing named to close means retire, raise the bar, or
   park — not another round.
6. **Respect the WIP limit** (default 3 lanes per wave). Depth closes gaps;
   breadth buys half-closed ones.
7. **Let the script count and publish.** `status` and `board` are deterministic
   and free. Never narrate run state into chat; never hand-write the workbench.
8. **Route the model to the role.** The cheapest model that can do that role's
   job — mechanical builders drop a tier, machine gates need none — and never
   cheaper on the critic whose verdict decides something. Hold the tier fixed
   within a lane so score trends stay readable.
   → `references/model-routing.md`
9. **Never pay twice for the same verdict.** Settled work is not re-judged; see
   the non-negotiables.
10. **Read each reference once, at its phase.**

## State: one directory, one script

`scripts/gauntlet.py` (stdlib-only) owns all run state under `gauntlet/`. The
model judges; the script counts.

```
gauntlet/
├── config.json      # lanes, dimensions, armed stops, WIP limit, parks, extensions
├── contract.md      # the confirmed intake contract
├── bar/             # frozen bar artifacts — never edited after intake
├── ownership.md     # file-ownership ledger, refreshed each wave
├── backlog.md       # noticed but deliberately unfunded; carried into the report
├── rounds.jsonl     # one validated record per comparison (script-written)
├── workbench.md     # progress board — regenerated by `board`, never hand-edited
└── report.md        # drafted by the script at the end, completed by you
```

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

Log every comparison through the script — the validation is the point. Layout,
git conventions and the resume protocol: `references/state-and-resume.md`.

## Phase 0 — The contract

Never loop without this settled. Read `references/intake.md`, put a compact
contract in front of the user, get confirmation. Infer or propose everything you
can; only **stops**, **kill criteria** and **budget** genuinely require the user,
because they encode how much time and money the run may spend.

| Field | What it fixes |
|---|---|
| **Goal** | The destination, not the route. An implementation plan is not a goal. |
| **Target bar** | The concrete external comparator per dimension, set where "done" is — reachable from here, inside the budget. |
| **Stretch** | Optional. Direction only; never a stop condition, never blocks retirement. |
| **Inspection** | How a critic reaches the output each round, and which dimensions have machine gates. |
| **Lanes** | The proposed split, ranked, with the WIP limit for a wave. |
| **Stop** | Which conditions are armed, with thresholds → `config.json`. |
| **Kill** | Named evidence that ends the whole run early, agreed now rather than argued later. |
| **Budget** | Waves / wall clock / tokens, always armed, with the projected call count. Optional hard cap no extension may cross. |
| **Autonomy** | Unattended until a stop fires, or check in at wave boundaries. |

Stops (`references/stop-conditions.md`): `bar-met`, `clean-streak`,
`no-progress` (parks a lane), `budget`, `judgment` — armed in combination, first
to fire wins.

**Cold start is normal.** With no artifact yet, wave 1 is a bootstrap wave: first
versions, no champion comparison, first bar comparison as soon as there is output
to inspect. Do not invent a fake baseline.

## Phase 1 — Set a reachable bar

The highest-leverage decision in the run. → `references/bar-selection.md`

Two things must be true of the target: **external and inspectable**, and
**reachable from the current artifact inside the budget**. A target nobody can
hit is not ambition — every round fails, every lane looks stalled, and the log
stops carrying information. Set `--target-score` where the target sits (default
7); a target of 10 means no lane can ever retire, and the script warns you.

Ambition above the target is legitimate: record it as a **stretch** in
`contract.md`, say plainly it is a heading and not a promise, and report the
distance to it at the end. Retirement is judged against the target only.

Freeze bar artifacts under `gauntlet/bar/`. Most artifacts need more than one
**dimension** (visual + frame time; clarity + completeness) — declare them in
`config.json` and judge each in its own comparison. Collapsing them into one
score is how a loop trades away the dimension nobody is watching.

**Where the target sits on the ladder.** A gauntlet does not generate a POC, then
an MVP, then an MLP — it runs *after* something inspectable exists and moves one
artifact up a quality ladder. But use the ladder to place the bar: *testable* is
the precondition (and what a bootstrap wave produces), *usable* is where the
target belongs, *lovable* is where a stretch belongs. Two consequences: a
bootstrap wave builds a thin end-to-end slice rather than one perfect part, and
if the user actually needs to decide **whether to build at all**, that is
discovery work — say so instead of polishing an unvalidated idea.
→ `references/bar-selection.md`, `references/authorities.md`

## Phase 2 — Cut and rank the lanes

Split the goal into **lanes**: the smallest units that can be improved and judged
independently. You cut them, not the user.

The lane test: *can a fresh critic look at this one thing and say which of two
versions is better, without needing the rest?*

Then **rank** them, because a wave funds `wip_limit` lanes and not all of them:
value to the goal × how closeable the gap looks at lane level ÷ cost per round.
Starving every lane equally is the commonest way a budget produces nothing
finishable.

Assign file ownership per lane in `gauntlet/ownership.md` — one file, one owner,
per wave. Sizing, ranking, parallel-vs-serial, re-cutting, and what a park says
about the cut: `references/decomposition.md`.

**The lane set is frozen at the contract.** Between waves it can be merged,
split, re-ranked or replaced; it does not *grow* because the run noticed more
work. A new lane needs a slot freed by a retirement or a park. Everything else
anyone notices goes to `gauntlet/backlog.md`, one line, and comes back in the
report as work the user can choose to buy in a future run — never as scope this
run quietly added.

## Round zero — and the feasibility gate

Run one build and one critic verdict on a single lane before scaling up. It costs
almost nothing and surfaces the two failures that waste hours: a broken
inspection path, and a bar too soft to compare against. A vague round-zero
verdict means fix the bar, not run the wave.

Then do the arithmetic once, out loud, before wave 1:

> rounds to close the first gap × lanes ÷ WIP limit ≈ waves needed

If it does not fit the budget, **rescope now** — drop the lowest-ranked lane,
lower the target to where the budget reaches (old target becomes the stretch), or
ask for more budget. Say which you chose. The cheapest wave to cancel is the one
that has not run.

## Phase 3 — Run the waves

A wave is one pass over the **funded** lanes — the top `wip_limit` of the ranked
list, as printed by `status`. Phases 3–5 cycle until a stop fires.

Per lane, per round:

1. **Build.** Builder gets the lane goal, the bar path, the current artifact and
   the last named gap — not the previous builder's reasoning.
   → `references/builder.md`
2. **Snapshot.** Commit the pre-round champion (`references/state-and-resume.md`).
   Nothing is merged yet.
3. **Gate, then judge.** Run any machine gate first — a dimension failing its own
   benchmark needs no critic. Then one critic call covering both comparisons
   (→ `references/critic.md`, `references/blind-protocol.md`):
   - **Promotion:** challenger vs champion. Wins → promote; loses → revert. The
     regression guard; skipped only on a lane's first round.
   - **Bar:** (if promoted) ours vs the target bar, per dimension. Produces the
     winner, margin, gap and severity, which drive the streaks.
4. **Log both** through `log-round` (`--mode champion`, then `--mode
   blind`/`rubric`). Every record names its `--dimension`; the script rejects
   undeclared ones, because a lane cannot retire on dimensions nobody judged.
5. A bar verdict with severity `major`/`minor` and no specific gap is invalid and
   rejected. A `none` verdict must still cite what it inspected.

## Phase 4 — Smooth

At each wave's end, one fresh agent over the parts that changed, resolving seams
between independently-improved lanes. Mandate: coherence, not redesign.
→ `references/smoother.md`

Skip only when the funded lanes touched genuinely disjoint files — check the
diff, do not assume. Never skip on a shared visual surface, a single document, or
one rendering pipeline.

## Phase 5 — The wave-boundary review

The cheapest phase in the loop and the one that decides whether the budget buys
anything. Run `status`, then act:

- **Retire** what met the target or ran out of closeable gaps; its budget returns
  to the pool.
- **Park** what `status` flags as stalled — no movement in `no_progress_n`
  rounds, reverts outpacing promotions, or the same gap three rounds running:
  `park --lane <l> --dimension <d> --reason "<log read>"`. Parking is not failure
  and not a verdict on the artifact; it is the decision to stop paying for rounds
  that stopped buying anything. The open gap goes into the report, where the user
  can act on it.
- **Re-cut** when the smoother reports the same seam twice, or two lanes' critics
  keep citing each other's territory. Between waves, never mid-wave.
- **Reallocate** — a retired or parked lane promotes the next one in. Re-check
  the feasibility arithmetic if the budget now looks tight.
- **Check the kill criteria** from intake. They fire early on purpose.
- **Publish** with `board`. It costs nothing and keeps the user out of your
  context.

Resume a parked lane only on *new evidence* — a re-cut, a fixed inspection path,
a new source asset, a revised bar. "It might work this time" is sunk cost with
extra steps; `park --resume` records the reason either way.

## Phase 6 — Stop and hand off

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
- **Park before you price**, in intake's units, over funded lanes only. `extend`
  refuses while a lane is flagged for parking — pricing over stalled lanes funds
  exactly the rounds the log calls worthless.
- **A block, not a tap:** two to four waves, so the next decision is made on
  fresh evidence. Wanting another twelve is a re-cut or a new run.
- **Lead with the honest read** from the log, and **recommend stopping when it
  says stop** — at a ceiling, everything retired or parked, inspection broken, or
  downhill drift. `extend` refuses that read without `--force`; a bar the
  artifact has passed calls for raising it instead. Selling an extension you do
  not believe in is the most expensive thing you can do in this skill.
- **Record it** in `config.json`, the report and `contract.md`. An unrecorded
  extension is how a 4-wave run becomes a 30-wave one.

A hard cap agreed at intake is the real ceiling and the script will not cross it.
Full protocol: `references/stop-conditions.md`.

## Non-negotiables

- **No builder grades its own homework.** Separate agent, fresh context. (They do
  *inspect* their output before handoff — that is a smoke test, not grading.)
- **Critics inspect the artifact, never a summary of it.**
- **Blind where blindable; label the mode honestly where not.**
- **Name the gap or the round didn't happen.** Enforced by the script.
- **The target bar never moves down.** Raising it mid-run is allowed, announced.
- **Losers get reverted.** This is what stops a long run wandering downhill one
  plausible-sounding round at a time.
- **A stalled lane gets parked, not one more push.**
- **Settled work is not re-judged.** A closed gap stays closed and a retired
  dimension is not re-opened. Regressions are caught mechanically — by the
  champion comparison within a dimension, by machine gates across them — not by
  review passes. A critic that thinks something previously closed has broken
  reports a *regression* with evidence; it does not re-argue the verdict.
- **Scope is frozen at the contract.** Re-cuts redistribute; they never expand.
  Noticed work goes to the backlog and the report, not into the wave.
- **Every comparison goes through the log.** State the model remembers is state
  the run will lose.
- **The budget is extended by the user or not at all** — stop, offer, resume only
  on a grant, log the grant with its reason.
- **Visible text is Simplified Technical English (ASD-STE100):** active voice, one
  statement per sentence, 20–25 words max, no marketing language.

## Failure modes

Read `references/failure-modes.md` before long unattended runs. The short list:

| Mode | Signal | Response |
|---|---|---|
| Critic sycophancy | Everything passes, gaps get vaguer | Force a choice; severity field; require evidence |
| Rubric gaming | Builder optimises the critic's wording, not the bar | Rotate critic framing; re-randomise labels |
| Bar erosion | Comparisons quietly get easier | Re-read frozen bar files each wave |
| Unreachable bar | Every round fails; scores never move | Target where done is; ambition goes in the stretch |
| Progress theatre | Rounds logged, artifact unchanged | Per-round artifact evidence; diff champions |
| Zombie lane | Same gap, round after round, still funded | `status` flags it; park it |
| Lane collision | Two lanes fight over one file | One file, one owner per wave |
| Downhill drift | Late output worse than mid-run | Champion commits; revert losers; per-dimension bars |
| Context bleed | Critic echoes builder's justifications | Critic gets artifact + bar only |
| Gold plating | Rounds spent past the target on a retired dimension | Retirement is a stop, not a suggestion |
| Re-litigation | Closed gaps re-argued; retired dimensions re-judged | Settled is settled; regressions caught mechanically |
| Scope snowball | More lanes at wave 6 than wave 1; projection quietly doubled | Frozen scope; new lanes need a freed slot; backlog |
| Token burn | Cost per closed gap climbing wave over wave | Machine gates, one critic call, WIP limit, model routing |
| Budget creep | Extensions granted repeatedly, each "nearly there" | Block-sized extensions, evidence per grant, hard cap |
| Inspection rot | Stale or missing evidence | Re-verify the path at every wave boundary |

## Degraded mode (no subagents)

Isolation weakens but the method survives: run critics as separate explicit
passes receiving only the artifact and the bar, never carry builder rationale
across, keep logging through the script. Say plainly that critic independence is
weaker than a real context boundary. In a plain chat with no file access, offer
the method as a manual protocol rather than claiming to run it.

## Scale expectations

A round is a builder call plus a critic call; a wave is that times the funded
lanes, plus a smoother — `init` prints the projection (a 3-lane, 8-wave run is
roughly 56 calls) and `extend` prices the block. Parallel lanes raise the burn
*rate*, not the total. Say so before starting when the projection looks
disproportionate to the artifact, and watch cost per closed gap: when it climbs
wave over wave, the honest offer is a stop.

## Reference files

Read at the relevant phase, not upfront:

- `references/intake.md` — the contract; cold start; cost expectations
- `references/bar-selection.md` — bar taxonomies; target vs stretch; dimensions
- `references/decomposition.md` — lane sizing, ranking, WIP, ownership, re-cutting
- `references/cost-discipline.md` — where the tokens go and how not to spend them
- `references/model-routing.md` — which model and effort per subagent role, and prices
- `references/blind-protocol.md` — blind comparison; champion mode; machine gates; rubric fallback
- `references/stop-conditions.md` — the conditions, parking, kill criteria, the extension protocol
- `references/state-and-resume.md` — layout, git conventions, resuming a run
- `references/workbench.md` — the generated progress surface; log schema
- `references/failure-modes.md` — full diagnosis and repair
- `references/example-run.md` — one annotated run, end to end
- `references/authorities.md` — where these rules come from, and what each forces

Subagents: `references/builder.md`, `references/critic.md`, `references/smoother.md`.
Tooling: `scripts/gauntlet.py` (init / log-round / status / park / board / extend / report).
