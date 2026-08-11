---
name: gauntlet-loop
description: Run an adversarial build-and-judge quality loop (Gauntlet Loop) to push inspectable artifacts toward a reference-class standard via autonomous rounds. Trigger on "gauntlet", "blind critic", "beat the reference", "keep iterating until it wins", "make it as good as X". Do not trigger for ordinary code review or bug fixing.
---

# Gauntlet Loop

> **Set the bar. Probe it cheap. Cut the lanes. Build. Judge blind. Run it again —
> and buy more effort only where the log says it is buying something.**

## Provenance

The method is Matt Shumer's, published 27 July 2026 as the technique behind the
"Claude of Duty" run (`https://somethingbig.ai/gauntlet-loop`, prompt at
`https://github.com/mshumer/Claude-of-Duty`). This skill is an operational
expansion: it adds an intake contract, a champion/challenger regression guard,
deterministic state tooling, per-dimension bars, named failure modes, and a cost
model — an escalating effort ladder, spend measured in tokens rather than waves,
model routing by role, wave scheduling by evidence, and mid-run shelving of work
that stopped moving. When citing the method, credit Shumer for the pattern and be
honest about which parts are this skill's additions.

**The published method is deliberately unbounded.** Shumer's instruction is *"Do
not tell it to do three rounds and stop. Tell it to keep looping,"* alongside a
recommendation to raise effort because "it costs much more, but the extra effort
usually produces better work." A separate public implementation says the
consequence outright: *"The loop will not finish on its own. You are the brake."*
Everything this skill adds about budget, tiers and scheduling **is** that brake.
A run that spent its whole budget was the method behaving exactly as published —
say so plainly rather than treating it as a fault.

One finding from the canonical run is worth carrying: **sequential single-owner
passes beat parallel fan-out decisively** (its own scores went 3.59 → 4.14 →
4.05 → 5.05 — three rounds of six parallel agents netted about half a point and
regressed once; the jump came from one sequential pass). Fan-out is the method's
most visible feature and its most over-used one. → `references/decomposition.md`

## What a Gauntlet Loop actually is

A quality-*maximising* loop, not a correctness loop.

The lead agent decomposes a goal into the smallest parts that can be improved and
judged **separately**. Each part gets a builder and a *different* critic running
in fresh context. The critic inspects the real artifact — rendered pixels, running
binary, actual prose, actual measurements — and compares it against a concrete
external bar, blind wherever the artifact allows. If the bar wins, the critic
names the single largest remaining gap and the work goes back. Then another round.

Four properties make it a gauntlet rather than a review:

1. **The bar is external and inspectable.** Not "make it production-ready". A real
   reference the agent cannot argue its way around.
2. **The builder never grades itself.** A builder has seen every decision it made
   and is therefore excellent at justifying them. Justification is the enemy here.
3. **The round count is not scheduled.** Rounds are earned by gaps, not planned.
4. **The effort is not scheduled either.** The loop starts at the cheapest tier
   that can produce a verdict and buys its way up with evidence. An idea that
   will not work dies as a probe, not as a campaign.

## When not to use this

- **Correctness work with a pass/fail oracle** (failing test, crash, wrong output).
  That is a debug loop; a gauntlet wastes compute on it. Fix it first, then
  gauntlet the quality.
- **Artifacts nobody can inspect.** No inspection path means no loop — only
  opinion exchange. Fix the path first (screenshot harness, benchmark, render).
- **Small bounded edits.** A gauntlet on a 20-line change is theatre.
- **Genuinely subjective taste with no comparator** — unless the user supplies
  the comparator, in which case it works fine.

If the work is mostly correctness-and-coordination rather than quality-ceiling,
say so and suggest a plan/execute orchestrator instead. The two compose:
orchestrate to *done*, gauntlet to *good*.

## Requirements and blast radius

Settle these before anything else:

- **Version control is required.** The champion/challenger guard is built on it.
  Refuse to start on a dirty working tree — have the user commit or stash first,
  so the run's first champion is a known state and a full abort is one command.
  If the project has no VCS, `git init` it (with the user's consent) before wave 1.
- **Writes are confined** to the project workspace and the `gauntlet/` state
  directory. Builders write only files they own this wave (`references/decomposition.md`). **Mission Control Integration:** If running under Mission Control, the Gauntlet Loop MUST initialize inside the assigned private worktree (`mc/<id>`), never at the repository root. All lanes cut must strictly respect the Implementer's Mission Control semantic leases.
- **The budget stop is always armed, and it is denominated in tokens.** An
  unattended loop without a ceiling is not safe to agree to, so never offer one.
  Waves are not a unit of money — a wave costs whatever its lanes and dimensions
  happen to cost — so set `--budget-tokens` alongside `--budget-waves` and let
  whichever depletes first stop the run. Then you may **offer an extension**.
  You may never take one.
- **Effort is bought in tiers, not assumed.** Start at tier 0 and escalate only
  on evidence (`references/cost-model.md`). Opening every lane at full effort
  before anything has been judged is the single most expensive mistake available
  in this skill.
- **Subagents are what make critics honest.** Each critic needs its own clean
  context. Without subagents the method degrades — see "Degraded mode" below.

## State: one directory, one script

All run state lives under `gauntlet/` in the project root, managed by
`scripts/gauntlet.py` (stdlib-only Python). The model judges; the script counts.
Streaks, stop conditions, revert rates and budget consumption are computed
deterministically so they cannot drift over a long context.

```
gauntlet/
├── config.json      # lanes, dimensions, stop thresholds, effort tier, spend budget
├── contract.md      # the confirmed intake contract
├── bar/             # frozen bar artifacts — never edited after intake
├── shots/           # per-round evidence: screenshots, renders, benchmark dumps
├── ownership.md     # file-ownership ledger, refreshed each wave
├── rounds.jsonl     # one validated record per comparison (script-written)
├── aims.jsonl       # each round's hypothesis and expected outcome, stated before it ran
├── skips.jsonl      # rounds deliberately not run, and what each saved
├── spend.jsonl      # token spend that produced no round: builders, smoother
├── state.json       # the workbench spec (script-written); state.js beside it for file://
├── workbench.html   # copied from assets/ once — generic renderer, never hand-edited
└── report.md        # drafted by the script at the end, completed by you
```

```bash
python3 scripts/gauntlet.py init --lanes a,b --dimensions visual,perf --bar-kind reference \
    --budget-waves 12 --budget-tokens 20000000 --cost-per-mtok 9.0 \
    --models cheap=claude-haiku-4-5,mid=claude-sonnet-5,high=claude-opus-5
python3 scripts/gauntlet.py log-round --wave 2 --lane a --dimension visual --round 3 \
    --mode blind --winner other --margin clear --score 7 --severity major --gap "..." \
    --evidence shots/w2r3.png --tokens 120000 --model cheap
python3 scripts/gauntlet.py log-round ... --model high --escalated-from cheap  # re-judged a thin verdict
python3 scripts/gauntlet.py log-round ... --mode oracle --evidence "lighthouse: LCP 1.42s"  # measured, no critic
python3 scripts/gauntlet.py spend --tokens 300000 --role builder --model high --note "lane a builder"
python3 scripts/gauntlet.py plan --max-lanes 2   # which lanes earn a round, priced against running all
python3 scripts/gauntlet.py aim --wave 4 --lane a --dimension visual --round 5 \
    --hypothesis "..." --approach "..." --expect-severity none   # the bet, before the builder runs
python3 scripts/gauntlet.py skip --wave 4 --lane a --dimension visual --reason-code no-change
python3 scripts/gauntlet.py tier      # current effort tier; is the next one earned?
python3 scripts/gauntlet.py escalate --reason "..."   # buy the next tier, on evidence
python3 scripts/gauntlet.py status    # streaks, spend, burn rate, flat dimensions, stops
python3 scripts/gauntlet.py shelve --lane a --dimension perf --reason "..."   # park a stalled dimension
python3 scripts/gauntlet.py unshelve --lane a --dimension perf --reason "..." # reinvest — new information only
python3 scripts/gauntlet.py board     # regenerate state.json for the workbench
python3 scripts/gauntlet.py extend --waves 3 --tokens 5000000 --reason "..."  # only on a grant
python3 scripts/gauntlet.py report    # draft the end-of-run report from the log
```

Pass `--tokens` on every round and every builder call. Without them the run
cannot price itself, `status` cannot print a burn rate, and every extension offer
degrades from "≈ €30" to "≈ 12 subagent calls" — a unit no user can evaluate.

Log every comparison through the script, never by hand-editing the file — the
validation is the point. Full layout, git conventions and the resume protocol:
`references/state-and-resume.md`.

## Phase 0 — The contract

Never start looping without this settled. Read `references/intake.md`, then put a
compact contract in front of the user and get confirmation. Set up the **Live
Kanban Workbench** by copying `assets/workbench.html` to `gauntlet/workbench.html`
and opening it in the user's browser.

The board is a generic renderer over one spec document, the way Swagger UI is a
generic renderer over an OpenAPI document: `gauntlet.py board` writes
`gauntlet/state.json`, and the page draws it. **Never edit the HTML, never ask a
subagent to, and never hand-write the spec while the script owns it.**
→ `references/workbench.md`

Infer or propose everything you can; only **stop conditions** and **budget**
genuinely require the user, because they encode how much time and money the run
may spend.

| Field | What it fixes |
|---|---|
| **Goal** | The destination, not the route. Do not accept an implementation plan as a goal. |
| **Bar** | The concrete external comparator, per dimension. |
| **Inspection** | How a critic will actually reach the output each round. |
| **Stop** | Which conditions are armed, with thresholds → `config.json`. |
| **Budget** | Tokens first, waves second — priced in the user's currency. Always armed. Say that it is a checkpoint: when it runs out the run stops and you come back with an extension offer. Optionally agree a **hard cap** no extension may cross. |
| **Ladder** | Where the run starts on the effort ladder and what each escalation will cost. Default: tier 0. |
| **Autonomy** | Unattended until a stop fires, or check in at wave boundaries. |
| **Workbench** | Where progress is visible without interrupting the run. |

Stop conditions (`references/stop-conditions.md`): `bar-met`, `clean-streak`,
`budget`, `judgment` — armed in combination, first to fire wins.

A bar that is not realistically reachable is fine and often correct — it supplies
direction and prevents stopping at "pretty good for an AI". Say this out loud when
proposing an ambitious bar so the user reads it as a heading, not a promise.

**Cold start is normal.** When the artifact does not exist yet, wave 1 is a
bootstrap wave: builders produce first versions, no champion comparison exists,
and the first bar comparison runs as soon as there is output to inspect. Do not
invent a fake baseline.

## Phase 1 — Set the bar

The highest-leverage decision in the run. Read `references/bar-selection.md` for
taxonomies per artifact class and for finding a bar when the user has none.

Freeze bar artifacts under `gauntlet/bar/` at intake. Most real artifacts need
more than one **dimension** (visual + frame time; clarity + completeness); declare
them in `config.json` and judge each in its own comparison — collapsing them into
one score is how a loop trades away the dimension nobody is watching.

## Phase 2 — Cut the lanes

Split the goal into **lanes**: the smallest units that can be improved and judged
independently. You cut them, not the user — you can see the artifact and they
cannot see it the way you do.

The lane test: *can a fresh critic look at this one thing and say which of two
versions is better, without needing the rest?*

Then **order the lanes by risk, not by comfort**: the lane whose failure would
invalidate the most work runs first — structure before cosmetics, foundations
before finish. The probe targets the top of that ranking, and the serial passes
descend it. Easiest-first ordering finds the structural problem at tier-3
prices, under work that assumed it away.

Assign file ownership per lane in `gauntlet/ownership.md`. One file, one owner,
per wave. Sizing, risk ordering, breadth-vs-depth, parallel-vs-serial, and
re-cutting: `references/decomposition.md`.

## Phase 2b — The effort ladder

Effort is bought, not assumed. The run starts at tier 0 and each escalation costs
a piece of evidence from the tier below it. Full model, gates and rationale:
`references/cost-model.md`.

| Tier | Name | Scope | Builder | Critic | Share of budget |
|---|---|---|---|---|---|
| 0 | probe | 1 lane, 1 dimension, 1 round | mid | cheap, 1 collapsed call | 5% |
| 1 | pilot | ≤2 lanes, 1 wave | mid | cheap, 1 screening call | 15% |
| 2 | campaign | all lanes, full waves | high | mid, split; escalate on `thin` | 40% |
| 3 | polish | only lanes still moving | high | high, full split | 40% |

`cheap`/`mid`/`high` are labels, not models. They resolve through `config.json`
— by default `claude-haiku-4-5` / `claude-sonnet-5` / `claude-opus-5`, whose
output tokens cost 1× / 3× / 5× respectively. Set them at intake with
`--models cheap=…,mid=…,high=…` and put the roster in the contract.

`gauntlet.py tier` prints whether the next tier is earned; `escalate --reason`
buys it. The four gates — a round ran at this tier, the bar discriminates,
inspection is live, the artifact is moving — are all computed from the log, and
`escalate` refuses when one fails. That refusal is the mechanism working: it says
more money would buy a bigger version of the problem you already have.

Before buying the campaign tier, run a **survey**: one bar comparison per
never-judged lane/dimension — the artifact as it stands, a cheap critic or an
oracle measurement, **no builders**. It prices the whole landscape at one cheap
call per pair, so the campaign's first `plan` ranks measured gaps instead of
guessed ones. Breadth is bought with critics; depth with builders; breadth with
builders is fan-out — the proven-worse shape. → `references/decomposition.md`

The point of the shape: **an unpromising run dies having spent a fifth of the
budget instead of all of it.** Say that at intake, because it is what makes an
ambitious budget safe to agree to.

## Round zero — before any wave

Tier 0 *is* round zero: one build and one critic verdict on a single lane. It
surfaces the two failures that would otherwise waste hours — a broken inspection
path, and a bar too soft for the critic to compare against. A vague round-zero
verdict means fix the bar, not run the wave.

**Aim it at the biggest risk.** The probe lane is the one whose failure would
invalidate the most — the hardest inspection, the most novel work, the
foundational choice the other lanes assume. A probe that proves the easy part
proves nothing; the point of paying 5% to learn something is to learn the
expensive thing while everything can still be re-cut for free.

It is also the run's **price calibration**. Log what it cost
(`log-round --tokens`, `spend --tokens`), then extrapolate to the proposed budget
and put the projected total in front of the user *in their currency* before
wave 1. One round of real measurement beats any estimate, and it costs one round.
If the projection is disproportionate to the artifact, say so before wave 1 —
that is the cheapest moment in the whole run to say it.

## Phase 3 — Run the waves

A wave is one pass over the active lanes. Phases 3 and 4 cycle until a stop
condition fires — this is the loop, not a sequence.

**Plan the wave before running it. The loop's default — every active lane, every
wave — is almost never right.**

```bash
python3 scripts/gauntlet.py plan [--max-lanes N]
```

`plan` ranks what is open by gap severity, holds what is flat, shelved or
retired, and prices the proposed wave against running everything regardless of
evidence. Then apply three gates before spending a single critic call
(→ `references/cost-model.md` §5):

1. **No change, no judgement.** Confirm the builder actually changed its owned
   paths. If it did not, `skip --reason-code no-change` and re-brief it — judging
   an unchanged artifact costs two calls to reproduce the last verdict.
2. **A number does not need a model.** When a dimension has a numeric bar, take
   the measurement and log `--mode oracle`. It costs no critic tokens, feeds the
   streaks like any bar round, and is stronger evidence than a model verdict.
   Call a model on that dimension only to name the gap when the number plateaus.
3. **Serial unless genuinely independent.** → `references/decomposition.md`

Record what you held: `skip --lane X --dimension Y --reason-code gap-too-small`.
Restraint that is not logged is invisible, and the report should be able to show
what the run chose not to spend.

Per lane, per round:

0. **Aim.** Before the builder runs, state the round's bet through
   `gauntlet.py aim`: the **hypothesis** (why the gap exists and why this change
   should close it), the **approach** (named, so a missed one is never quietly
   retried), and the **expected verdict** (`--expect-severity` / `--expect-score`
   — and it must improve on the last verdict, or the script refuses). A round
   without an aim cannot miss, and a round that cannot miss teaches nothing.
   The script scores every aim against what actually happened and prints the hit
   rate — under 50% means the model of the artifact is wrong: **diagnose before
   building again**. → `references/aim.md`
1. **Build.** Spawn a builder with the lane goal, the bar path, the current
   artifact, the last named gap — and the round's aim, so it knows *why* the
   change should work. Not the previous builder's reasoning.
   → `references/builder.md`
2. **Snapshot.** Commit the pre-round champion (git; conventions in
   `references/state-and-resume.md`). Nothing is merged yet.
3. **Judge — two comparisons, both blind where possible** (→ `references/critic.md`,
   `references/blind-protocol.md`):
   - **Promotion:** challenger vs champion. Challenger wins → promote. Loses →
     revert. This is the regression guard; skip it only on the very first round
     of a lane, when no champion exists.
   - **Bar:** (if promoted) ours vs the bar, per dimension. Produces the winner,
     the margin, the gap and its severity. This drives the streaks.
4. **Log both** through `gauntlet.py log-round` (`--mode champion` and
   `--mode blind`/`--mode rubric` respectively). Every record names the
   `--dimension` it was judged on, and the script rejects any dimension not
   declared in `config.json` — a lane cannot retire on dimensions nobody judged.
5. A bar verdict with severity `major`/`minor` and no named gap is invalid — the
   script rejects it. A verdict of severity `none` must still cite what it
   inspected, or it is a lazy critic, not a clean round.

**How many critic calls is a tier decision, not a taste decision.** At tiers 0–1
one collapsed screening call answers both questions; log two records regardless.
From tier 2 the split is the default. In both cases, escalate a *specific* verdict
to a stronger critic when it comes back `thin` and will decide a retirement — a
`decisive` verdict does not get better on a bigger model. → `references/cost-model.md`

**Whether the two comparisons run serially or concurrently is a pace decision,
and the log makes it**: at a low revert rate `status` recommends running them
concurrently (the rare wasted bar verdict costs one call; serializing costs every
round a critic's latency), at a high one it recommends staying serial. Pipeline
across lanes too — dispatch the next lane's builder while this lane's critics
run; ownership serialises writes, not the clock. → `references/pace.md`

## Phase 3b — Stop paying for stalled work

At every wave boundary, `status` flags any dimension that has not moved in
`flat_rounds_n` bar rounds (default 3) as `FLAT`, with the cost of running it
again printed next to it. Shelve it:

```bash
python3 scripts/gauntlet.py shelve --lane imagery --dimension perf --reason "<log evidence>"
```

Shelved is **parked, not retired**: it stops consuming calls from the next wave,
and the report keeps its open gap. `shelve` refuses a dimension the log does not
call flat, so this cannot quietly become a way to abandon work that was climbing.

A lane that stalls at wave 3 should cost three waves of calls, not twelve. The
evidence is in the log from wave 3 — this is what puts it on the screen there.

Parked is not forgotten, and the calls the shelf frees are a **transfer, not a
cut** — they belong to the dimensions still moving. The moment there is *new
information* — a diagnosis round names the cause, a new source asset lands, a
re-cut changes what the lane is — bring the dimension back:

```bash
python3 scripts/gauntlet.py unshelve --lane imagery --dimension perf \
    --reason "diagnosis: LCP floor was the source asset; new 400KB master replaces it"
```

`unshelve` demands that new information in `--reason`, prints the dimension's
failed-approaches ledger on the way back in, and the first aim after it must
carry the new reason in its hypothesis. Budget left over is not, on its own, a
reason — that would be re-buying the stall.

## Phase 4 — Smooth

At the end of each wave, spawn one fresh agent over the *whole* artifact to
resolve seams between independently-improved parts. Mandate: coherence, not
redesign. → `references/smoother.md`

Skip it when lanes are genuinely independent. Never skip it on a shared visual
surface, a single document, or a single rendering pipeline. Then check
`gauntlet.py status` and start the next wave, re-cut lanes, or stop.

## Phase 5 — Stop and hand off

When a stop fires, finish the wave and the smoother (unless it is a safety stop),
promote the best champion — not necessarily the latest challenger — then run
`gauntlet.py report` and complete it:

- Bar used, and whether it was raised mid-run
- Lanes, rounds each, how each retired
- Gaps closed, and — the part the user actually needs — **gaps still open**
- Blind vs rubric round counts (not equivalent evidence)
- Your honest read on whether the loop was still improving at the stop

Do not soften the open-gaps section. A report that reads as a victory lap is
worth less than one that says exactly where the artifact is still weak.

## Phase 5b — when the budget depletes, offer an extension

A budget stop means the money ran out, not that the artifact is done. Those are
different facts and the user is owed both. So: stop the run, report, and then put
one extension offer in front of them — **a next block of waves**, priced.

`gauntlet.py status` prints the offer material as soon as the budget fires: the
open dimensions, whether each is still moving (score trend, severity easing,
margin narrowing), the recent revert rate, and its read of the log. Present that,
not a vibe:

```
Budget depleted at wave 8. Stopped, smoothed, report written.
  imagery/visual   still moving — score 5→7, severity major→minor; open gap: <gap>
  imagery/perf     flat for 3 rounds; revert rate 60%
Extension of 3 waves ≈ 30 subagent calls. My read: worth it for visual, not perf.
Extend 3 waves on imagery/visual only, re-cut, or stop here?
```

Rules for the offer:

- **The user grants it. You never self-extend**, and you never keep the loop
  running while you ask. A budget that extends itself is not a budget.
- **Offer a block, not an open tap.** Two to four waves, sized so the next
  decision is made on fresh evidence. If it looks like it needs another twelve,
  that is a re-cut or a new run, not an extension.
- **Price it in the same units as intake** — waves and projected subagent calls
  for the lanes still open, not the retired ones.
- **Lead with the honest read.** Say "still improving", "flat", or "too few
  rounds to tell" and back it from the log. Selling an extension you do not
  believe in is the most expensive thing you can do in this skill.
- **Recommend stopping when the evidence says stop.** At a ceiling, with every
  dimension retired, with a broken inspection path, or on downhill drift, the
  correct offer is "stop" or "re-cut" — `extend` refuses that log read without
  `--force`, and a bar the artifact has passed calls for raising the bar instead.
- **Record it.** `gauntlet.py extend --waves N --reason "<evidence>"` writes the
  grant into `config.json` and the report; then note it in `contract.md` and on
  the workbench. Extensions are run history, and an unrecorded one is how a
  4-wave run quietly becomes a 30-wave one.

If the user pre-agreed a hard cap at intake, it is the real ceiling — extensions
stop there and the script refuses to cross it. Full protocol:
`references/stop-conditions.md`.

## The brake steers, it does not shrink

Everything this skill adds to the published method — tiers, token budgets,
plans, skips, shelving, aims — exists to *redirect* spend toward what buys
quality, never to lower the ceiling. The result is the point; cost discipline is
how an ambitious result stays affordable. Two rules keep that true:

**The guards that buy quality are never traded for cost or speed.**
Fresh-context critics, the blind protocol, the champion guard, the frozen bar,
real-artifact inspection, per-dimension judging: these *are* the method's power,
and every cost and pace decision routes around them, never through them
(`references/pace.md`, "What not to trade away"). A cheaper critic is fine; a
critic that saw the builder's reasoning is not cheaper — it is broken.

**Savings are reinvested, not pocketed.** The budget is the user's ceiling, not
a target to undershoot. Tokens freed by a skip, an oracle round, or a shelving
flow to the dimensions still moving, to tier-3 polish (which exists precisely to
spend 40% of the budget once the evidence supports it), to raising the bar once
everything retires, or back into a shelved dimension the moment a diagnosis
produces a new hypothesis (`unshelve`). Stopping early because the evidence says
ceiling is management; stopping early while the log still says *moving*, with
budget left, is the mirror image of budget creep — and the report should treat
it as a finding, not a saving.

## Non-negotiables

- **No builder grades its own homework.** Separate agent, fresh context, always.
  (Builders *inspect* their output before handoff — checking it runs and renders
  is not grading; it prevents burning a round on a broken artifact.)
- **Critics inspect the artifact, never a summary of it.**
- **Blind where blindable; label the mode honestly where not.**
- **Name the gap or the round didn't happen.** Enforced by the script.
- **The bar never moves down.** Frozen at intake; raising it mid-run is allowed
  and announced.
- **Losers get reverted.** Champion/challenger is what stops a long run from
  wandering downhill one plausible-sounding round at a time.
- **Every comparison goes through the log.** State the model remembers is state
  the run will lose.
- **Every call reports what it cost.** A run that cannot price itself cannot tell
  the user when to stop paying, and "≈ 12 subagent calls" is not a price.
- **Effort goes up on evidence, never on optimism.** The gates are in the log;
  `escalate` enforces them.
- **The most expensive model is not the default.** Roles get the model their job
  needs — generation is where quality is bought, classification usually is not.
  Record which model did what, escalate specific verdicts rather than whole runs,
  and let the log say whether the expensive tier earned its multiplier.
  → `references/cost-model.md`
- **A flat dimension gets shelved, not re-run.** The wave boundary is where that
  decision belongs — not the moment the budget runs out.
- **Never judge an artifact that did not change.** The gate is free; the two
  critic calls it replaces are not.
- **Every round states its expectation before it runs — and is scored against
  it.** A hypothesis, an approach, an expected verdict, through `aim`, before the
  builder. Misses become information; a low hit rate calls for a diagnosis round,
  not another build; a missed approach is never retried without a new reason.
- **A numeric bar is measured, not judged.** Log it `--mode oracle` and spend the
  model only on naming the gap when the number stops moving.
- **The budget is extended by the user or not at all.** Stop first, offer second,
  resume only on a grant — and log the grant with its reason.
- **Language Rules (ASD-STE100).** All visible text on the Kanban board (goals, gaps, next fixes) and reports must use Simplified Technical English: max 20-25 words per sentence, active voice, one instruction per sentence, no AI marketing language.

## Failure modes

Read `references/failure-modes.md` before long unattended runs. The short list:

| Mode | Signal | Response |
|---|---|---|
| Critic sycophancy | Everything passes, gaps get vaguer | Force a choice; severity field; require evidence |
| Rubric gaming | Builder optimises the critic's wording, not the bar | Rotate critic framing; re-randomise labels |
| Bar erosion | Comparisons quietly get easier | Re-read frozen bar files each wave |
| Progress theatre | Rounds logged, artifact unchanged | Per-round artifact evidence; diff champions |
| Lane collision | Two lanes fight over one file | One file, one owner per wave |
| Downhill drift | Late output worse than mid-run | Champion commits; revert losers; per-dimension bars |
| Context bleed | Critic echoes builder's justifications | Critic gets artifact + bar only |
| Ceiling denial | Same gap recurs; reverts climb | Re-cut or stop; `status` surfaces the signal |
| Budget creep | Extensions granted repeatedly, each "nearly there" | Block-sized extensions, evidence per grant, hard cap |
| Inspection rot | Stale or missing evidence | Re-verify the path at every wave boundary |
| Premature scale-up | Every lane opened at full effort before any verdict | Start at tier 0; `escalate` on gates |
| Unsatisfiable critic | No verdict ever reaches `none`; only the budget can end the run | Calibrated scale; `none` is a valid verdict |
| Cost blindness | Run priced in waves and calls; nobody knows what it spent | `--budget-tokens`, `--tokens` on every call |
| Top-tier default | Every role on the strongest model; spend-by-model is one bar | Route by role; escalate verdicts, not runs; check it with `--escalated-from` |
| Unmanaged fan-out | Every lane run every wave; parallel by default on coupled work | `plan` before the wave; serial unless genuinely independent |
| Judging nothing | Verdicts repeat because the artifact never changed | No-change gate; `skip --reason-code no-change` and re-brief |
| Model reads a number | A critic call spent restating a measurement | `--mode oracle`; call a model only to name a plateau |
| Convoy | Wave time ≈ sum of every stage; critics idle while builders run and vice versa | Pipeline independent stages; judging strategy from the revert rate (`pace.md`) |
| Convergence tax | One round per cosmetic gap once a dimension is down to minors | Batch the critic's NOTES into one brief; the champion guard makes it safe |
| Build-and-hope | Rounds run with no stated expectation; misses look like bad luck | `aim` before every build; diagnose when the hit rate drops below half |
| Comfort-first probe | POC proves the easy lane; the structural risk surfaces at tier 3 | Probe the riskiest lane; survey the rest before the campaign |

## Degraded mode (no subagents)

Without subagents the isolation weakens but the method survives: run critics as
separate explicit passes that receive only the artifact and the bar, never carry
builder rationale across, and keep logging through the script. Tell the user
plainly that critic independence is weaker than a real context boundary — do not
pretend otherwise. In a plain chat with no file access at all, offer the method
as a manual protocol rather than claiming to run it.

## Scale expectations

Calls per lane per round = **1 builder + (critic calls × dimensions)**. At tier 3
with two dimensions that is 5, not 3 — the dimension multiplier is the term that
gets forgotten, and forgetting it is how a budget the user agreed to becomes one
they did not. A wave is `lanes × that + 1` for the smoother. `gauntlet.py`
computes it from the current tier and the declared dimensions rather than from a
constant.

So a 3-lane, 2-dimension run at tier 3 is ~16 calls per wave, and ten of those
waves is ~160 subagent invocations. Parallel lanes raise the burn *rate*, not the
total. The ladder is what keeps that number from being what an *unpromising* run
costs: tiers 0 and 1 together are a fifth of the budget.

Then stop estimating and start measuring. After round zero the run knows its own
per-call cost; `status` prints the burn rate and the waves of budget remaining at
that rate, and both the extension offer and `extend` price the next block from
this run's own calls. Quote money, not calls — "≈ €30 for three more waves on the
one lane still moving" is a question a user can answer.

## Worked example

`references/example-run.md` walks one compact run end to end — contract, round
zero, a revert, a re-cut, a judgment stop — with real log lines. Read it once
before your first run; point users at it when they ask what they are agreeing to.

## Reference files

Read at the relevant phase, not upfront:

- `references/intake.md` — the contract; cold start; cost expectations
- `references/cost-model.md` — the effort ladder, model tiering, context discipline, honest pricing
- `references/pace.md` — wall-clock: convergence per round, pipelining vs fan-out, judging strategy by revert rate
- `references/aim.md` — rounds as experiments: hypothesis, expectation, hit rate, the diagnosis round
- `references/bar-selection.md` — bar taxonomies; dimensions; finding a bar
- `references/decomposition.md` — lane sizing, ownership, parallel vs serial
- `references/blind-protocol.md` — honest blind comparison; champion mode; rubric fallback
- `references/stop-conditions.md` — the four conditions, their mechanics, and the budget-extension protocol
- `references/state-and-resume.md` — directory layout, git conventions, resuming a run
- `references/workbench.md` — live progress surface; log schema
- `references/failure-modes.md` — full diagnosis and repair
- `references/example-run.md` — one annotated run

Subagents: `references/builder.md`, `references/critic.md`, `references/smoother.md`.
Tooling: `scripts/gauntlet.py` (init / log-round / status / report).
