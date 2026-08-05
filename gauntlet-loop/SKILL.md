---
name: gauntlet-loop
description: Run an adversarial build-and-judge quality loop (Gauntlet Loop) to push inspectable artifacts toward a reference-class standard via autonomous rounds. Trigger on "gauntlet", "blind critic", "beat the reference", "keep iterating until it wins", "make it as good as X". Also authors portable gauntlet prompts for running the method elsewhere — trigger on "write me a gauntlet prompt", "a gauntlet prompt for X", "gauntlet prompt I can paste". Do not trigger for ordinary code review or bug fixing.
---

# Gauntlet Loop

> **Set the bar. Cut the lanes. Build. Judge blind. Run it again.**

## Provenance

The method is Matt Shumer's, published 27 July 2026 as the technique behind the
"Claude of Duty" run (`https://somethingbig.ai/gauntlet-loop`, prompt at
`https://github.com/mshumer/Claude-of-Duty`). This skill is an operational
expansion: it adds an intake contract, a champion/challenger regression guard,
deterministic state tooling, per-dimension bars, and named failure modes. When
citing the method, credit Shumer for the pattern and be honest about which parts
are this skill's additions.

## What a Gauntlet Loop actually is

A quality-*maximising* loop, not a correctness loop.

The lead agent decomposes a goal into the smallest parts that can be improved and
judged **separately**. Each part gets a builder and a *different* critic running
in fresh context. The critic inspects the real artifact — rendered pixels, running
binary, actual prose, actual measurements — and compares it against a concrete
external bar, blind wherever the artifact allows. If the bar wins, the critic
names the single largest remaining gap and the work goes back. Then another round.

Three properties make it a gauntlet rather than a review:

1. **The bar is external and inspectable.** Not "make it production-ready". A real
   reference the agent cannot argue its way around.
2. **The builder never grades itself.** A builder has seen every decision it made
   and is therefore excellent at justifying them. Justification is the enemy here.
3. **The round count is not scheduled.** Rounds are earned by gaps, not planned.

## Two modes

**Run mode** is the default and the rest of this file: you perform the loop here,
with the state directory and the script.

**Author mode** produces a *prompt* that will run a gauntlet somewhere this skill
is not installed — another agent, another machine, a teammate, a scheduled job.
Phase 0 is identical (a prompt built on an unconfirmed contract ships a soft bar
and no inspection path); you then stop, render the contract into a prompt, and
skip the waves. → `references/prompt-authoring.md`

Choose author mode when the user asks for a prompt, or when the loop will
demonstrably run elsewhere. If it is going to run *here*, run it — an emitted
prompt loses the deterministic counting and the verdict validation, and offering
one in place of a run you could have performed is a downgrade.

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
- **The budget stop is always armed.** An unattended loop without a ceiling is not
  safe to agree to, so never offer one. When the budget depletes the run *stops* —
  then you may **offer an extension in waves**. You may never take one.
- **Subagents are what make critics honest.** Each critic needs its own clean
  context. Without subagents the method degrades — see "Degraded mode" below.

## State: one directory, one script

All run state lives under `gauntlet/` in the project root, managed by
`scripts/gauntlet.py` (stdlib-only Python). The model judges; the script counts.
Streaks, stop conditions, revert rates and budget consumption are computed
deterministically so they cannot drift over a long context.

```
gauntlet/
├── config.json      # lanes, dimensions, armed stop thresholds
├── contract.md      # the confirmed intake contract
├── bar/             # frozen bar artifacts — never edited after intake
├── ownership.md     # file-ownership ledger, refreshed each wave
├── rounds.jsonl     # one validated record per comparison (script-written)
├── workbench.html   # live Kanban board (updated via #gauntlet-state JSON)
└── report.md        # drafted by the script at the end, completed by you
```

```bash
python3 scripts/gauntlet.py init --lanes a,b --dimensions visual,perf --bar-kind reference --budget-waves 12
python3 scripts/gauntlet.py log-round --wave 2 --lane a --dimension visual --round 3 \
    --mode blind --winner other --margin clear --score 7 --severity major --gap "..." \
    --evidence shots/w2r3.png
python3 scripts/gauntlet.py status    # streaks, revert rate, fired stop conditions
python3 scripts/gauntlet.py extend --waves 3 --reason "..."   # only after the user grants it
python3 scripts/gauntlet.py report    # draft the end-of-run report from the log
```

Log every comparison through the script, never by hand-editing the file — the
validation is the point. Full layout, git conventions and the resume protocol:
`references/state-and-resume.md`.

## Phase 0 — The contract

Never start looping without this settled. Read `references/intake.md`, then put a
compact contract in front of the user and get confirmation. 
First, you must set up the **Live Kanban Workbench** by copying the HTML template to `gauntlet/workbench.html` and opening it in the user's browser.
Infer or propose everything you can; only **stop conditions** and **budget** genuinely require the
user, because they encode how much time and money the run may spend.

| Field | What it fixes |
|---|---|
| **Goal** | The destination, not the route. Do not accept an implementation plan as a goal. |
| **Bar** | The concrete external comparator, per dimension. |
| **Inspection** | How a critic will actually reach the output each round. |
| **Stop** | Which conditions are armed, with thresholds → `config.json`. |
| **Budget** | Ceiling on waves / wall clock / tokens. Always armed. Say that it is a checkpoint: when it runs out the run stops and you come back with an extension offer. Optionally agree a **hard cap** no extension may cross. |
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

Assign file ownership per lane in `gauntlet/ownership.md`. One file, one owner,
per wave. Sizing, parallel-vs-serial, and re-cutting: `references/decomposition.md`.

## Round zero — before any wave

Run one build and one critic verdict on a single lane before scaling up. It costs
almost nothing and surfaces the two failures that would otherwise waste hours: a
broken inspection path, and a bar too soft for the critic to compare against. A
vague round-zero verdict means fix the bar, not run the wave.

## Phase 3 — Run the waves

A wave is one pass over the active lanes. Phases 3 and 4 cycle until a stop
condition fires — this is the loop, not a sequence.

Per lane, per round:

1. **Build.** Spawn a builder with the lane goal, the bar path, the current
   artifact, and the last named gap. Not the previous builder's reasoning.
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

Two critic calls per round is the default. On cheap, fast-moving lanes you may
collapse them into one call that answers both questions — but log two records,
and prefer the full split whenever a round's outcome will trigger retirement.

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
- **The budget is extended by the user or not at all.** Stop first, offer second,
  resume only on a grant — and log the grant with its reason.
- **No emitted prompt carries an uncapped loop.** "Loop until it's perfect" is
  the shape users copy and the one thing this skill never offers. Every prompt
  written in author mode ships a wave ceiling and an instruction to stop there
  and ask — it will spend someone else's money unattended.
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

## Degraded mode (no subagents)

Without subagents the isolation weakens but the method survives: run critics as
separate explicit passes that receive only the artifact and the bar, never carry
builder rationale across, and keep logging through the script. Tell the user
plainly that critic independence is weaker than a real context boundary — do not
pretend otherwise. In a plain chat with no file access at all, offer the method
as a manual protocol rather than claiming to run it.

## Scale expectations

Set these at intake so the budget means something: each round is one builder call
plus up to two critic calls; a wave multiplies that by active lanes; smoothing
adds one call per wave. A 3-lane, 10-wave run is therefore roughly 100 subagent
invocations. Parallel lanes raise the burn *rate*, not the total. When the
projected total looks disproportionate to the artifact, say so before starting.

Price an extension the same way, over the lanes still open — a 3-wave extension
on one surviving lane is ~12 calls, not another hundred. That arithmetic is what
makes "3 more waves?" a question the user can actually answer.

## Worked example

`references/example-run.md` walks one compact run end to end — contract, round
zero, a revert, a re-cut, a judgment stop — with real log lines. Read it once
before your first run; point users at it when they ask what they are agreeing to.

## Reference files

Read at the relevant phase, not upfront:

- `references/intake.md` — the contract; cold start; cost expectations
- `references/bar-selection.md` — bar taxonomies; dimensions; finding a bar
- `references/decomposition.md` — lane sizing, ownership, parallel vs serial
- `references/blind-protocol.md` — honest blind comparison; champion mode; rubric fallback
- `references/stop-conditions.md` — the four conditions, their mechanics, and the budget-extension protocol
- `references/state-and-resume.md` — directory layout, git conventions, resuming a run
- `references/workbench.md` — live progress surface; log schema
- `references/failure-modes.md` — full diagnosis and repair
- `references/example-run.md` — one annotated run
- `references/prompt-authoring.md` — author mode: emitting a portable gauntlet prompt

Subagents: `references/builder.md`, `references/critic.md`, `references/smoother.md`.
Tooling: `scripts/gauntlet.py` (init / log-round / status / report).
Templates: `assets/prompt-template.md` (author mode, standalone tier).
