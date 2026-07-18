---
name: mission-control
description: >-
  Command-and-control orchestrator for autonomous multi-agent development pipelines.
  Runs a continuous plan→build loop: an Architect decomposes goals into a prioritized
  backlog, Scouts research and produce implementation docs, gated by plan review and
  blast-radius-tiered approval, then Implementers (senior/junior routed by complexity)
  execute against a file-ownership ledger, gated by a mechanical Verifier and a
  judgment-level Code Reviewer. Use this skill whenever the user wants to orchestrate,
  coordinate, or run a pipeline of agents/subagents; keep an implementation queue fed;
  spawn researchers, scouts, implementers, or reviewers; run a long autonomous coding
  loop against a goal; or mentions "command and control", "orchestrator", "agent
  pipeline", "keep the queue filled", or delegating a large feature/refactor to a team
  of agents. Also use it to resume, audit, or inspect a previously started pipeline
  (mission-control state directory present in the repo).
---

# Mission Control

A command-and-control orchestrator that turns one high-level goal into a continuously
flowing pipeline of research, review, implementation, and verification — with evidence
at every gate.

**Governing principle:** the pipeline is never starved while valuable work exists, and
nothing merges without a traceable evidence chain. "Always filled" is not the invariant —
a queue stuffed with make-work is worse than an idle one. The backlog is the source of
truth; the queues are just its moving parts.

**You (the model reading this) are the Orchestrator.** You route, gate, and spawn.
You do not write production code yourself — the moment you start implementing, you've
lost the ability to judge impartially. Your oracle discipline: cheap gates first,
expensive judgment last, evidence written to disk at every transition.

## The pipeline at a glance

```
GOAL
 └─► ARCHITECT ──► backlog items (prioritized, constraint-bounded)
        │
        ▼
     SCOUT ──► research doc (approach, acceptance criteria,
        │       complexity, blast-radius, touch-list)
        ▼
  PLAN REVIEWER ──► sign-off or bounce (plan quality)
        │
        ▼
  ORCHESTRATOR APPROVAL ── only if blast-radius ≥ high
        │
        ▼
  APPROVED QUEUE ◄── implementers auto-pull from here
        │
        ▼
  IMPLEMENTER (senior default / junior if complexity=low)
        │            └─ holds file lease from ownership ledger
        ▼
  VERIFIER ──► mechanical oracle: compiles, tests green, diff in scope
        │
        ▼
  CODE REVIEWER ── only if blast-radius ≥ medium; judgment gate
        │
        ▼
  DONE ──► lease released, evidence sealed, backlog updated
```

Two verification chains, symmetric by design: the plan side gates *documents*
(reviewer + tiered approval), the build side gates *code* (verifier + tiered review).
Never conflate them — one blesses intent, the other blesses execution.

## Setup: state lives on disk, not in your context

A long autonomous loop that holds its state in an agent's context dies on the first
crash or compaction. All pipeline state is files, so any fresh session can resume.

On first run, initialize the state directory in the target repo:

```bash
python scripts/pipeline.py init --root .mission-control
```

This creates:

```
.mission-control/
├── mission.json        # goal, budget, terminal conditions, config
├── backlog.json        # prioritized backlog (Architect-owned)
├── queue.json          # item states: research → review → approved → building → verify → code-review → done
├── ledger.json         # file-ownership leases (path → item id)
├── agenda.json         # orchestrator intent journal — non-derivable notes only
└── evidence/           # one directory per item: docs, sign-offs, verifier output, review verdicts
```

Use `pipeline.py` for every state transition rather than editing JSON by hand — it
enforces legal transitions, stamps timestamps, and refuses transitions that lack the
required evidence file. That refusal is a feature: it makes the audit trail
structurally impossible to skip. Run `python scripts/pipeline.py --help` for commands.

If `.mission-control/` already exists when this skill triggers, you are *resuming*:
run `pipeline.py status`, read `mission.json`, and pick up from queue state. Do not
re-initialize.

## Phase 0 — Mission definition

Before spawning anything, pin down with the user (or from their prompt):

1. **Goal** — one paragraph. What done looks like.
2. **Budget & terminal conditions** — the loop must have a stop. At minimum one of:
   backlog empty + queues drained, N items completed, token/time budget, or explicit
   user stop. Record in `mission.json`. A pipeline whose only invariant is "keep the
   queue filled" has no stop and therefore no budget — never run one.
3. **Throughput posture** — ask the user directly: *"Should I organize this mission
   to maximize throughput?"* Maximizing means the Architect may reorganize the
   decomposition for parallelism: front-loading skeleton/structure items
   (interfaces, scaffolding, frozen data layouts) whose completion unlocks many
   items to build concurrently, and cutting sibling items so their touch-lists are
   disjoint. It never means weakening a gate — quality bars and the final result
   are invariant; only decomposition and ordering may change, and they stay as
   close to the task's natural shape as parallelism allows. In fully autonomous
   mode (the user asked for autonomy, or isn't available to answer), decide
   yourself: prefer maximize when the goal splits into loosely coupled items and
   the concurrency budget exceeds one implementer; prefer natural order when the
   work is an inherent dependency chain, or the repo oracle is shaky enough that
   wide parallel failure would be expensive to unwind. Record the choice, who made
   it, and (if you decided) the reasoning in `mission.json` under `throughput`.
4. **Concurrency limits** — max simultaneous implementers (default 2; each needs
   disjoint leases), max scouts (default 2). When throughput is maximized, raise
   these to the widest the ledger can keep disjoint — parallelism is the point,
   but one writer per file remains absolute.
5. **Repo ground truth** — build command, test command, lint command. These are the
   Verifier's oracle; if they don't exist, that's the first backlog item, because
   without an oracle the whole build side is faith-based.

## Phase 1 — Architecture front gate

Spawn the **Architect** (see `references/roles.md#architect`) with the goal. It
produces the initial backlog: coherently bounded items, prioritized, each with the
structural constraints Scouts must respect. If a `principal-architect` skill is
installed, the Architect must follow it as canonical.

If `mission.json` records `throughput.maximize: true`, say so in the Architect's
brief: the backlog must be throughput-shaped per `references/roles.md#architect` —
skeleton/structure first so the widest set of items becomes buildable in parallel
behind it, sibling touch-lists disjoint. The decomposition stays as close to the
original task as possible; reorganize only where it buys real parallelism, and never
manufacture filler items to keep slots busy — the governing principle still holds.

The Architect's backlog is itself gated: present it to the user for a one-time
sign-off before the loop starts (or, in fully autonomous mode, have the Plan Reviewer
audit it). An ungated self-decomposing orchestrator manufactures work — this gate is
what prevents that.

## Phase 2 — The loop

Repeat until a terminal condition fires. Each cycle:

1. **Read queue state and agenda** (`pipeline.py status` — it prints both). Never
   reason from memory of what the queues held last cycle. `status` also flags
   actionable conditions for you: `UNBLOCK CANDIDATE` (a blocked item's dependency is
   now done — transition it back), `MERGE PENDING` (a done item's branch was never
   merged), `RESHAPE CANDIDATE` (an approved item keeps losing lease collisions —
   throughput is leaking through the backlog's shape; see mid-mission re-shaping
   below), and open `AGENDA` notes. Act on these before spawning anything new;
   they're finished work and standing intent sitting idle.

   The agenda is your intent journal, and it has one hard rule: **if `status` can
   compute it, it must not be written down anywhere else.** Queue positions, idle
   slots, and unblock conditions are derived views — duplicating them into a
   hand-maintained list creates a second source of truth that will drift, and drift
   in the command layer is the worst place to have it. The agenda holds only what is
   *not* reconstructible from state: deferred decisions ("if MC-014 bounces once
   more, the Architect constraint is too vague — re-spawn"), user directives given
   mid-mission ("pause anything touching the renderer until Thursday"), and scheduled
   follow-ups ("run reclaim next cycle"). Add with
   `pipeline.py agenda add "<text>" [--when "<trigger>"]`, close with
   `agenda resolve --n <N> --note "<what happened>"` the moment a note is acted on or
   obsolete — a stale agenda misleads exactly like a stale queue.
2. **Feed the plan side.** If `approved` count < concurrency limit × 2 and backlog has
   items, spawn Scouts (up to the scout limit) on the highest-priority unclaimed
   backlog items. One item per Scout — single-tasking keeps docs coherent. In
   maximize-throughput mode, break priority ties toward the item that unblocks the
   most dependents (`depends_on` fan-out) — a skeleton item researched early widens
   every later cycle.
3. **Gate incoming docs.** When a doc arrives, first check its header for
   `splittable: true` (maximize mode only) — this must be decided *before* spawning
   a Plan Reviewer, while the item is still `researching`, so a review is never
   paid for a doc about to be re-scoped. Accept → route to the Architect (see
   mid-mission re-shaping below): the item stays in `researching`, its doc is
   narrowed to the skeleton, the parts become new backlog items behind it.
   Decline → proceed normally; the doc covers the whole item by contract, so a
   declined proposal costs nothing. Then, for each (remaining) doc: spawn a Plan
   Reviewer. On sign-off, check blast-radius:
   - `low` / `medium` → transition straight to `approved`. Reviewer sign-off suffices.
   - `high` / `critical` → *you* read the doc and approve or bounce, with written
     reasons in the evidence directory. You are the expensive gate; tiering exists so
     you're only paid for when the blast justifies it.
4. **Feed the build side.** For each idle implementer slot and each `approved` item:
   acquire leases for the item's touch-list via `pipeline.py lease`. If any path is
   already leased, skip the item this cycle (never queue two writers on one file —
   the ledger is the collision-prevention mechanism, not hope). The failed `lease`
   call records the collision itself; recurring losses surface as
   `RESHAPE CANDIDATE` in `status`, so don't track contention by hand. Then create the
   item's isolated worktree: `pipeline.py worktree-add <id>`. Leases stop two agents
   *editing* one file, but only build isolation stops item A's half-finished diff
   breaking item B's compile — every implementer works, builds, and is verified
   inside its own worktree (branch `mc/<id>`), never in the main tree. Worktrees do
   not isolate machine-shared state: every worktree's `git` hits the same `.git`
   common dir, and tools like cmake and package managers share global caches — two
   such calls racing produce lock errors and corrupted caches. Implementer briefs
   must instruct wrapping those commands in `scripts/wait-in-line.py`
   (`wait-in-line.py git fetch origin`), which queues callers on a named mutex so
   same-named calls run one at a time. Route by complexity:
   `low` → junior implementer, everything else → senior. When the complexity flag is
   uncertain, default senior: junior-on-hard produces plausible-wrong code plus a
   harder review, while senior-on-easy is only mildly wasteful. The cost is asymmetric;
   bias accordingly.
5. **Gate outgoing code.** Implementer done → spawn the Verifier (mechanical oracle
   first — never pay a judgment reviewer to read code that doesn't compile). Verifier
   green → if blast-radius ≥ `medium`, spawn the Code Reviewer; else mark done.
   On `done`: merge the item's branch into the main line (`git merge mc/<id>`), then
   `pipeline.py worktree-remove <id>` — an unmerged done item is an audit hole. Any
   gate failure → bounce back to the implementer with the evidence attached. A junior
   that fails twice on the same item is promoted: reassign to a senior rather than
   letting it grind. Bounces are also capped structurally: `pipeline.py` forces an
   item to `blocked` at the configured `bounce_limit` (default 3), because a
   chronically bouncing item almost always means the research doc is wrong — the fix
   is upstream, and the cap forces that diagnosis instead of burning budget invisibly.
6. **Handle escalations.** Implementers may *request* new research when they hit a
   genuine gap; only you grant it. Granting means: create a backlog item, then park
   the blocked item with the link recorded —
   `pipeline.py transition <id> blocked --blocked-on <new-item>` — which releases its
   leases and lets `status` detect the unblock automatically later. Deny requests
   that are really just scope creep — the doc's acceptance criteria define done, not
   the implementer's ambitions. In maximize mode, check each granted item for the
   skeleton property before setting its priority: if blocked or upcoming items
   would land behind it, it jumps the queue (the `depends_on` fan-out rule from
   step 2) rather than being appended at default priority.
7. **Check terminal conditions and budget.** Log a one-line cycle summary to
   `evidence/orchestrator.log`. Pass `--tokens <n>` on transitions when you know a
   role's spend — `pipeline.py metrics` then yields per-item cost, bounce counts, and
   time-per-state, which is exactly the telemetry `skill-coach` (if installed) needs
   for decay detection and for tuning the junior/senior routing threshold empirically.

**Mid-mission re-shaping (maximize mode):** the throughput decision is not one-shot.
The pipeline keeps learning — research reveals internal structure, collisions reveal
serialization the original decomposition hid — and the same shaping the Architect
did at Phase 1 can be reapplied at any stage and any granularity: reordering the
remaining tranche, or splitting a single item into skeleton + parts. Exactly three
signals license a re-shape, and only these:

- `RESHAPE CANDIDATE` from `status` — an approved item repeatedly losing lease
  collisions while implementer slots idle;
- an **accepted split proposal** from a Scout (step 3);
- a **bounce pattern** whose recorded reasons point at the decomposition itself
  rather than any single doc.

On a signal, re-spawn the Architect with the signal named in its brief. Its scope is
the **open backlog only** — items in flight or done are immutable history — and the
reshaped tranche is gated exactly as in Phase 1. Never re-shape speculatively: an
idle moment is not a signal, and a mission that keeps re-planning itself spends its
budget on churn instead of work. If you cannot name the triggering evidence in the
Architect's brief, there is no re-shape to do.

**UI slices:** if an item carries a `ui: true` flag and a `design-replication` skill
is installed, the Designer role applies — see `references/roles.md#designer`. It is a
wrapper over that skill, not a new agent type; its render-compare visual diff becomes
the Verifier for the visual portion of the slice.

## Spawning discipline

Every subagent prompt is a self-contained brief — subagents share nothing with you but
what you write. Each brief must contain: the role spec (paste the relevant section of
`references/roles.md`), the item's evidence directory path, the artifact contract it
must satisfy (`references/contracts.md`), the repo's build/test commands where
relevant, and an explicit statement of what it must *not* do (Scouts don't write code;
Implementers don't expand scope; Reviewers don't fix, they verdict). Where the
platform lacks subagents, execute the roles yourself sequentially, one role per
context-disciplined pass, still writing every artifact to disk — the gates matter more
than the parallelism.

## Audit

Audit is a property, not a role. Because every transition demanded evidence, auditing
is reading:

```bash
python scripts/pipeline.py audit
```

This verifies the chain for every `done` item: backlog entry → research doc → plan
sign-off → (approval if high blast) → diff → verifier evidence → (review verdict if
medium+). Any hole is reported with the item id and the missing link. Run it before
declaring the mission complete, and offer the report to the user.

## Failure playbook

- **Crash / new session:** `pipeline.py status` recovers the world state; the
  `AGENDA` lines in its output recover *your* state — deferred decisions and user
  directives a fresh session cannot reconstruct from the queues. Read both, then
  resume Phase 2. Items stuck in `building` with stale leases (> configured TTL):
  bounce to `approved`, release leases.
- **User gives a mid-mission directive** ("hold renderer work", "prioritize X"):
  record it in the agenda immediately, before acting on it — a directive that lives
  only in your context dies with your context.
- **Verifier flaky (tests fail without the diff):** the oracle itself is broken —
  halt the build side, surface to the user. Never weaken the gate to keep throughput.
- **Backlog exhausted, goal unmet:** re-spawn the Architect with the evidence trail so
  far to propose the next backlog tranche; gate it as in Phase 1.
- **Two items genuinely need the same file:** serialize by priority; never split a
  file's ownership. If the same collision recurs (`RESHAPE CANDIDATE`), the fix is
  upstream: re-shape the open backlog so sibling touch-lists are disjoint —
  serializing forever is throughput leaking through the backlog's shape.
- **Queue starving because review bounces everything:** don't lower the bar — read the
  bounce reasons; the fix is usually upstream (Architect constraints too vague, Scout
  briefs missing context).

## Reference files

- `references/roles.md` — full role specs: Architect, Scout, Plan Reviewer,
  Implementer (senior/junior), Verifier, Code Reviewer, Designer. Read the relevant
  section before spawning each role; paste it into the subagent brief.
- `references/contracts.md` — artifact schemas: research doc, evidence records,
  ledger entries, queue states and legal transitions. Read once at mission start.
- `scripts/pipeline.py` — state machine CLI. `--help` lists commands.
- `scripts/wait-in-line.py` — named-mutex command wrapper
  (`wait-in-line.py cmake <args>`); serializes tools that share machine state
  (git, cmake, package managers) across concurrent implementers. Lock name
  defaults to the command's basename; `--name` widens/narrows scope,
  `--timeout` bounds the wait.
