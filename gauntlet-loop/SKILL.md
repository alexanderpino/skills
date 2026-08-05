---
name: gauntlet-loop
description: Run an adversarial build-and-judge quality loop (Gauntlet Loop) to push inspectable artifacts toward a reference-class standard via autonomous rounds. Trigger on "gauntlet", "blind critic", "beat the reference", "keep iterating until it wins", "make it as good as X". Do not trigger for ordinary code review or bug fixing.
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
  safe to agree to, so never offer one.
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
| **Budget** | Hard ceiling on waves / wall clock / tokens. Always armed. |
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
- `references/stop-conditions.md` — the four conditions and their mechanics
- `references/state-and-resume.md` — directory layout, git conventions, resuming a run
- `references/workbench.md` — live progress surface; log schema
- `references/failure-modes.md` — full diagnosis and repair
- `references/example-run.md` — one annotated run

Subagents: `references/builder.md`, `references/critic.md`, `references/smoother.md`.
Tooling: `scripts/gauntlet.py` (init / log-round / status / report).
