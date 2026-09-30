---
name: fan-out
description: >-
  User-invoked only — reachable exclusively through the /fan-out slash command. Do NOT load
  or act on this skill because a task looks parallelisable, because the user mentions
  sub-agents, critics, parallel work, multiple approaches, or reviewing agent output, or
  because it would be faster. Those are not invocations. If the user has not typed
  /fan-out or named the fan-out method by name, this skill does not apply — answer the
  request directly instead. When it IS invoked: fans one task out to parallel sub-agents
  against a single sealed brief and allocation plan, each in a lane of its own, has
  independent critics judge each candidate against a rubric written before the work
  started, verifies fixes against the delta only so approved work is never re-reviewed,
  integrates the lanes and judges their seams, and folds one result with an evidence trail.
# The enforced half of "user-invoked only": Claude Code blocks an automatic load and will
# not preload this skill into a sub-agent. The description above is the prompt-level half;
# metadata is free-form data for other tooling, which Claude Code does not act on.
disable-model-invocation: true
argument-hint: <task>
metadata:
  invocation: user
---

# Fan-Out

One brief. N builders. Independent critics. One fold.

## Invocation

This is a **user-invoked** skill. It runs when the user types:

```
/fan-out <task>
```

and at no other time. Never start this loop on your own initiative — spawning N sub-agents
and a critic wave is an expensive, high-latency commitment that belongs to the user, not to
your judgement about what would be thorough. A task that merely *looks* like fan-out work
is a task you should do directly.

Two consequences that follow from being user-invoked:

- **Never nest.** A builder or critic spawned by this skill must not invoke `/fan-out`, or
  any other user-invoked skill. Model-invoked skills are fine and often useful — pass the
  relevant ones through in the shared block so every agent gets the same discipline.
- **`/fan-out` exists as soon as the skill is installed.** Custom commands and skills are
  the same mechanism now, so a skill directory provides its own slash command; the
  `disable-model-invocation: true` in the frontmatter is what makes the restriction real
  rather than a request, and Claude Code blocks an automatic load. `commands/fan-out.md`
  is an optional wrapper: copy it to `.claude/commands/` if you want its pre-flight
  checklist (partition vs compete, allocation and strategies, plan, seal, lanes) in front
  of every run. Both spellings produce `/fan-out`, so install one, not both.

## Orientation

**Governing principle:** the shared context is written once and never mutated. Everything
that differs between agents lives at the *end* of the prompt, never the beginning. That one
rule is what makes prompt caching work and what makes the critics' comparisons valid — if
agents disagree about the ground truth, their outputs are not comparable and the critique
is noise.

**You (the model reading this) are the Orchestrator.** You slice, allocate, spawn, gate,
integrate and fold. You do not build the candidates yourself — not a slice, not a
synthesis, not a seam fix. The moment you write one, you can no longer judge the set
impartially. The only thing you write into the result is mechanical: hotspot entries at
integration.

## Conventions

Everything lives under `.fan-out/<run-id>/`. Each slice gets one **slice id** — lowercase,
hyphenated, fixed for the whole run — and it must be identical in every place it appears,
or the tooling silently fails to correlate them:

```
slices.json (its "id")       candidates/<slice-id>.md     verdicts/<slice-id>.json
revisions/<slice-id>/v<N>/   renders/<slice-id>/r<N>/     lanes/<slice-id>[.patch]
```

A slice is the unit of work; its **lane** is where that work physically happens — a
worktree, a patch file, or the main tree. `integration` is reserved: it names the seam
verdict (`verdicts/integration.json`) and the merged render (`renders/integration/`).

`renders/` holds whatever a critic has to *look at* rather than read — screenshots,
plots, frames, exported pages. **`r<N>` pairs with the snapshot `v<N>`**: the builder's
first render is `r1` alongside the baseline snapshot, and each later fix produces both a
`v<N>` and the `r<N>` taken from it. Keeping the two indices in step is what lets a
verification round put the new render beside the old one instead of taking the builder's
word that the visual finding is fixed. Don't index renders by verification round — round 1
of verification produces `r2`, and a run that conflates the two overwrites its own
baseline.

## The loop

```
TASK
   │
   ├─► SLICE ──────► partition (different parts) or compete (same part, N approaches)
   ├─► ALLOCATE ───► slices.json: who owns what, which isolation, which contracts
   │
   ├─► BRIEF ──────► one immutable file: shared context, identical for everyone
   ├─► RUBRIC ─────► written BEFORE any builder runs, sealed with the brief and plan
   │
   ├─► LANES ──────► one per slice, set up for its strategy
   ├─► PATHFINDER ─► builder #1 alone; its run writes the shared cache prefix
   ├─► FAN-OUT ────► builders #2..N in parallel; they read the prefix from cache
   ├─► TRESPASS ───► mechanical: did any lane write outside what it owns?
   │
   ├─► CRITICS ────► one per candidate, blind to each other, same brief prefix
   ├─► VERIFY ─────► delta and open findings only; never re-review approved scope
   │
   ├─► INTEGRATE ──► land the lanes, run the whole-system oracles, judge the seams
   │
   └─► FOLD ───────► one result + a short evidence trail
```

## Step 1 — Slice and allocate

Pick the mode first, because it changes everything downstream:

| Mode | When | Fold means |
|---|---|---|
| `partition` | The job splits into independent parts (per-module refactor, per-chapter draft, per-file audit) | Merge the parts |
| `compete` | One job, genuinely uncertain approach (algorithm choice, API design, prose voice) | Pick the winner, or synthesize |

If the request is ambiguous, ask once. Guessing wrong is expensive: `partition` work judged
as `compete` produces critics arguing that incomparable things are unequal.

```bash
python scripts/fanout.py init "<task>" --mode partition --n 4
```

Creates `.fan-out/<run-id>/` with skeletons for `brief.md`, `rubric.md` and `slices.json`.

### Cohesion first: N is an output, not an input

Work that sits close together — same files, same symbols, same mental model — belongs in
**one** slice, and the cut goes where the coupling is weakest. Splitting coupled work makes
two agents rebuild the same model, fight over the same files, each drag a critic behind
them, and — worst — makes every verification round cascade, because revising one re-opens
the other's approved regions. `references/incremental-review.md` has that mechanism.

Don't guess at the coupling, measure it. Fill `slices.json` with the proposed slices and
what each would own (next section), then:

```bash
python scripts/fanout.py plan
```

`plan` validates the allocation and reports coupling in four tiers: shared write targets
(`WRITE`) and cross-slice dependencies (`DEP`) are merges; a dependency pinned by a stated
contract (`CONTRACT`) may stay split; shared vocabulary (`VOCAB`) is advisory.

- **Floor** — don't spawn an agent for work smaller than the brief it must read. Three
  one-line fixes in one file are one slice. When `plan` reports `FLOOR` — under a hundred
  existing lines across every slice — stop and do the task directly, unless most of the
  work is new files that count cannot see. This holds inside the loop too: give a builder
  all of a slice's open findings in one pass, not one pass per finding.
- **Ceiling** — stop merging when a slice no longer fits one coherent working set, or stops
  being verifiable in one pass. Between floor and ceiling, N is determined by the work.
- **`compete` is exempt** — there the redundancy is the point, and merging destroys the
  diversity that made the mode worth choosing. It's bounded instead by how many genuinely
  different constraints you can state, which is rarely more than four. `plan` does not
  measure coupling in this mode; it validates the plan and stops.

**`partition` rules.** No two slices own the same file — `seal` refuses the plan if they
do; merge rather than coordinate. Each slice must be verifiable on its own: if B can only
be judged once A lands, it isn't a slice, it's a **phase**. Phases are sequential runs: run
1 goes all the way through integration, and run 2 is a new run whose brief describes what
run 1 delivered. Worktree and patch lanes start from the base commit, so run 1's result
must be committed (the user's call) before run 2's lanes can see it.

**`compete` rules.** Each builder gets a genuinely different constraint, not different
wording. "Optimise for allocation count" vs "optimise for readability" is a real choice;
"do it well" vs "do it nicely" is N copies of one answer and N critics with nothing to say.
State it in one line — the slice's `summary` — because that line is the only per-agent
text that differs in substance.

### The allocation plan

`slices.json` is where the orchestrator says how the work is divided, and it is the
single source of every per-agent block. It is sealed with the brief: a builder's scope
that changes mid-run is the same fault as a brief that changes mid-run.

```json
{
  "hotspots": ["package.json", "src/routes.ts"],
  "slices": [
    {
      "id": "ecs-query",
      "summary": "Rewrite Query iteration over archetype chunks",
      "task": "Iterate chunk by chunk instead of entity by entity.\nKeep Query's public signature; only its internals change.",
      "context": "Query is hot in the render loop; store.h's chunk layout is stable.",
      "strategy": "worktree",
      "strategy_reason": "runs the ECS test suite",
      "owns": ["src/ecs/query.cpp", "src/ecs/query.h"],
      "reads": ["src/ecs/store.h"],
      "out_of_scope": ["caching query results between frames"],
      "must_not": ["change the public Store API"],
      "provides": [{"symbol": "each",
                    "contract": "`Query::each(Fn)` calls Fn once per live entity, chunk order"}],
      "consumes": [],
      "done_when": ["`ctest -R ecs` passes", "no allocation inside `each`"]
    }
  ]
}
```

| Field | What it fixes |
|---|---|
| `summary` | One line: the slice's job, or in `compete` its constraint. It follows `YOUR SLICE:` |
| `task` | The lane's task description: what to do, the approach where it matters, the cases to cover. Text, newlines allowed |
| `context` | What this lane needs to know that the others do not: who calls its code, what is fragile, why it is shaped this way. Text |
| `strategy`, `strategy_reason` | The lane's isolation (next section), and why — decided per lane, so it is recorded |
| `owns` | The lane's scope: the only paths it may write. A trailing `/` owns a directory |
| `reads` | Files the lane should read for context and must not write |
| `out_of_scope` | What this lane must not take on — work, not files ("no caching"). Other lanes' files are added to it automatically |
| `must_not` | Prohibitions for this lane alone. Run-wide ones go in the brief |
| `provides` | Symbols other lanes build against, each with a contract stated as an observation |
| `consumes` | Symbols this lane builds against, naming the providing lane |
| `done_when` | This lane's slice of the definition of done |
| `hotspots` | Files every lane would need to touch — a lockfile, a registry, a route table, a changelog. No lane owns them |

What the fields are for:

- **Everything that differs between agents lives here, never in the brief.** Task,
  context, scope, what is out of scope, prohibitions for one lane: all of it is per-agent
  text, and `fanout.py delta` renders it below the `---` where it cannot touch the cached
  prefix. The brief and the plan split the same things by reach: the brief's *Goal*,
  *Context*, *Out of scope* and *Must not* hold for every agent, the plan's `task`,
  `context`, `owns`, `out_of_scope` and `must_not` for one lane.
- **`task` is where a partition builder learns its job.** `summary` is one line and it is
  enough for a `compete` constraint; a partition lane with nothing more gets a slogan, and
  `plan` warns about it. Write the task as you would brief a colleague on that one part:
  what, the approach where it matters, the cases that must be covered.
- **A contract is what lets a coupled pair stay split.** When `plan` finds `DEP` between
  two slices, merging is the default. The alternative is to pin the edge: the provider
  lists the symbol under `provides` with its contract, the consumer lists it under
  `consumes`, and the provider promises not to move it. `plan` then reports `CONTRACT`
  instead of `DEP`. Write the contract the way a critic writes a `check` — what is
  observably true — because at integration it becomes exactly that.
- **Hotspots belong to integration.** A file every lane appends to is the classic source of
  merge conflicts, and giving it to one lane forces the others to trespass. So nobody owns
  it: each builder lists the entries it needs under *Hotspot entries* in its report, and
  you apply them in Step 6.

### Isolation strategies

Each lane gets one of four strategies, chosen per lane and per run. A strategy fixes four
things at once: where the builder writes, where its critic looks, how the lane is landed,
and how trespass is measured.

| Strategy | Builder writes | Critic looks at | Landed by | Trespass measured on |
|---|---|---|---|---|
| `read-only` | Only its candidate | The candidate | Nothing to land; the fold reads it | Any change to the repository |
| `shared` | The main tree, only its `owns` | The main tree | Already in place | Main-tree changes vs the union of shared lanes' `owns` |
| `patch` | A diff at `lanes/<slice-id>.patch`; the repo stays untouched | The patch, applied in a disposable worktree | `git apply` in the main tree | The paths in the patch |
| `worktree` | Its own git worktree and branch | That worktree | Its diff applied in the main tree | The worktree's diff against the base |

Decide each lane with three questions. Any "yes" means `worktree`:

1. Would it write files another lane also writes? In `partition` that is a slicing error;
   in `compete` it is the mode, and `shared` is therefore never allowed there.
2. Does it run a build, tests, an install, a formatter or a server — anything that writes
   shared state (output directories, caches, lockfiles, ports)?
3. Must it be rejectable on its own, without touching what the others did?

Three times "no": `shared` for writers, `read-only` for lanes that only report. `patch` is
the cheap middle — isolated without a tree of its own to set up — for small changes whose
builder does not need to run anything. When question 2 is a maybe, choose `worktree`: a
wasted worktree costs setup time, a collision costs a round.

What each costs, so the choice is honest:

- **`worktree`** — a fresh checkout lacks everything ignored: dependencies, `.env`, build
  caches, generated files. `fanout.py lane` lists what is missing; install or copy what the
  build and render recipe need before the builder is spawned. It also starts from the base
  commit, so uncommitted work in the main tree is invisible to it.
- **`patch`** — the builder cannot run its own change against a real tree. Critics and
  deciders run on `lane <slice-id> --materialize`, re-made after every new patch.
- **`shared`** — attribution is ownership only. The main tree has several writers, so a
  write inside another shared lane's `owns` cannot be traced to who made it, and a failed
  shared lane cannot be un-landed except by hand.
- **`read-only`** — none; it simply produces nothing to merge.

Mixing is normal: code lanes in `worktree`, a docs lane in `shared`, an audit in
`read-only`. Lanes are created by `fanout.py lane` rather than by a sub-agent harness's own
worktree isolation, because a lane must outlive its builder — the critic, the verifier and
integration all need it at a known path.

## Step 2 — Brief and rubric

**Fill `brief.md` with everything every agent needs and nothing else:** goal, constraints,
what the run as a whole leaves out of scope, the prohibitions that hold for every agent,
relevant paths, acceptance criteria, definition of done, and any excerpt the agents would
otherwise go discover for themselves. Pre-loading this isn't only a caching trick — it
stops N agents from each exploring separately and arriving at N different models of the
problem.

**`brief.md` must not contain** timestamps, run IDs, agent numbers, per-slice file lists,
"you are agent 3 of 7", or anything else that differs between agents.
`references/prompt-caching.md` explains why each of those is fatal. Per-slice scope is not
lost by keeping it out — it lives in `slices.json` and reaches each agent through its delta.

**If the work has a visual surface, the brief carries the recipe for reaching it.** One
command that renders the candidate, plus the exact state to render it in — viewport, seed,
theme, sample input, which page or frame. This belongs in the shared block precisely
because it must not vary: two candidates screenshotted at different widths are two facts
about different things, and the critics' scores stop being comparable. The recipe is
identical for everyone; only the slice id in the output path comes from the delta.

**Run that recipe once yourself before you seal — in a fresh worktree, if any lane is
one** (`git worktree add --detach <tmp> HEAD`), because that bare checkout is what those
builders will get. A recipe that needs a browser this environment doesn't have, a dev server nobody started,
or a dependency a fresh worktree lacks, fails identically in all N builders — and because
the brief is sealed you cannot repair it without starting a new run. One dry run before
`seal` is the cheapest check in the whole loop. If the render genuinely can't be produced
here, say so in the brief and drop the visual axis from the rubric rather than shipping a
recipe you know will fail.

**Fill `rubric.md` before any builder runs.** A rubric written after seeing the candidates
is a rationalisation of the one you already liked. Three to six axes, each with a concrete
failure example, plus the blocking conditions that force `reject` regardless of score. If
there is something to look at, at least one axis must be scoreable **only** from the
render — otherwise the critics quietly score the source that produces the picture, which
is the failure Step 4 exists to prevent.

```bash
python scripts/fanout.py seal
```

`seal` validates the allocation plan and refuses one that does not hold, hashes the brief,
rubric and plan, and records the **base commit** every lane starts from. From here on, an
edit to any of the three is a detected error rather than a silent one — `fanout.py check`
will fail.

## Step 3 — Pathfinder, then fan out

Spawn builder #1 **alone** and wait for it to return, then spawn #2..N **in the same turn**.
The pathfinder does real work on a real slice; it goes first only so its request writes the
shared prefix that the other N-1 read from cache.

Skip it and fire everything at once when the brief is too short to cache at all — the
minimum runs from 512 to 4,096 tokens depending on which model the agents run on, so a
brief over ~4K always caches and one under ~512 never does — or when you want the
wall-clock more than the tokens. Keep the whole wave on one model either way; caches don't
cross models, so critics on a cheaper model than the builders share nothing with them. Read
`references/prompt-caching.md` before deviating further.

**Set up the lanes first**, once the seal is in place:

```bash
python scripts/fanout.py lane            # every lane, per its strategy
python scripts/fanout.py delta <slice-id>   # the block below the '---', per builder
```

`lane` creates each worktree (branch `fanout/<run-id>/<slice-id>`, from the base commit),
prepares the patch location, and lists what a fresh worktree will lack. `delta` renders a
lane's per-agent block from the sealed plan, always in this order: its slice line, task,
context, isolation instructions, scope (what it may write), what it reads, out of scope
(its own entries, then every file another lane owns), the hotspots, its prohibitions, the
contracts it provides and consumes, and its done-when. Empty fields are left out. Paste its output verbatim; do
not hand-write a delta, because a hand-written one drifts from the plan that trespass and
integration will hold the lane to.

**Builder prompt — this exact shape, shared block first:**

```
Read <run-dir>/brief.md in full before doing anything else. It is the complete and
authoritative context for this task. Do not go looking for additional context; if the
brief is insufficient, say so in your report rather than improvising.

Your slice, its isolation and its scope are below the line. Treat that scope as a
boundary, not a suggestion: write only what it lets you write, and where the work
seems to need more, stop and say so in your report. Build against the contracts you
are given, not the code you find — other lanes are changing it right now.

Write your candidate to <run-dir>/candidates/<your slice id>.md: what you did and why,
plus any code, placed as your isolation instructions say. Before you finish, run what
the brief gives you to run — build, tests, lint — against your own change wherever your
isolation allows it, and fix what fails. A candidate that does not compile spends a
critic on a compiler's job.

If the brief names a visual surface, produce it before you finish: run the render
recipe exactly as written, write the output to <run-dir>/renders/<your slice id>/r1/,
and link it from your candidate. Your critic will judge the render rather than your
description of it, so an unrendered candidate is judged on a missing artifact. If the
recipe fails, say so in your report with the error — do not substitute a description.

End the candidate with this report, every heading present, "none" where empty:

## Report
### Files touched
### Hotspot entries
Exactly what you need added to each hotspot file, per file.
### Assumptions
### Scope deviations
Anything you needed outside your scope, and whether you did it or stopped.
### Open questions

---
<output of `fanout.py delta <slice-id>`>
```

Everything above the `---` is byte-identical across every builder — the slice id is
referred to, never written, up there. Everything below is the delta. Keep it that way even
when it feels redundant.

The report headings are fixed because tooling reads them: `integrate` collects *Hotspot
entries*, and `followups` drains *Assumptions*, *Scope deviations* and *Open questions*
into `follow-ups.md`.

**Then check scope, before any critic runs:**

```bash
python scripts/fanout.py trespass
```

Worktree and patch lanes are measured exactly; the shared tree is measured against the
union of its lanes' `owns`. A lane that wrote outside its scope goes back to its builder
with the list — revert those writes, or justify each in the report — and no critic is
spawned for it until it is clean. A trespass that was genuinely necessary is a slicing
error: accept it deliberately, record it for the fold, and cut differently next run. Never
let it reach integration unexamined, where it surfaces as a conflict nobody can attribute.

## Step 4 — Critics

One critic per candidate, all spawned in the same turn, each seeing **exactly one**
candidate. They do not see each other's verdicts and they do not see the other candidates —
a critic that has already read three candidates is anchored, and anchored critics converge
on the first thing they read.

Critics read the same `brief.md` first, so they hit the prefix the builders just paid for —
provided they run on the same model, since caches don't cross models. The 5-minute default
TTL is measured from when a request *starts*, not from when it returns, so the builders'
own generation time is spent out of it: a wave that took six minutes to think has already
expired the entry the critics were meant to read. Spawn them immediately, and treat a long
build as a cold critic wave rather than assuming warmth you no longer have.

**Critic prompt:**

```
Read <run-dir>/brief.md in full. It is the authoritative context.
Then read <run-dir>/rubric.md.

---
Judge exactly one artifact: <run-dir>/candidates/<slice-id>.md
Its files are in <lane root: the worktree, the materialized patch, or the main tree>;
read and run them there, and anchor findings with paths relative to that root. Judge
the lane against its own task, scope and contracts:
<output of `fanout.py delta <slice-id>`, without its leading "---">
If the brief names a visual surface, open <run-dir>/renders/<slice-id>/r1/ and judge
what you see there. Do not read any other candidate.
Write your verdict to <run-dir>/verdicts/<slice-id>.json in this schema:

{
  "candidate": "<slice-id>",
  "round": 1,
  "scores": {"<axis>": 1-5, ...},
  "findings": [
    {
      "id": "F-<slice-id>-01",
      "severity": "blocker" | "major" | "minor" | "nit",
      "anchor": {"file": "<path>", "symbol": "<function or heading>",
                 "quote": "<short verbatim excerpt>", "line_hint": 42},
      "claim": "what is wrong",
      "observed": "the current state, measured — in the same terms as the check",
      "check": "the concrete observation that would prove this fixed",
      "check_cmd": "<optional: a command whose exit 0 means the check now holds>",
      "sites": ["<every other anchor with the same defect>", ...],
      "status": "open"
    }
  ],
  "approved": ["<path or symbol you examined and found sound>", ...],
  "evidence": ["what you actually ran or read", ...],
  "verdict": "accept" | "revise" | "reject"
}

Score against the rubric, not against your taste. Every finding needs an anchor into the
candidate — an unfalsifiable objection is not a finding.

Every field of a finding is something you SAW, not something you concluded:

- `claim` — what is wrong.
- `observed` — what the artifact does NOW, measured, in the units the check uses:
  "renders #808080 at the body panel, r1/hero.png centre". The number you read, the string
  you saw, the timing you took, and where you took it.
- `check` — what would be TRUE once it is right: "the body is #C8102E, as in
  reference.png". Name the value, the range, the reference or the source, and quote the
  brief or rubric where it fixes the target. A check that restates the deviation — off,
  wrong, inconsistent, unclear, too slow — leaves the builder to guess, and it will guess.
- `sites` — every other anchor with the same defect, in full. Not a count, not "and
  others". Empty means you looked and it is local.

Where you cannot name the target because nothing in the brief or rubric fixes it, say that
in `claim` at the honest severity. Never file a check that only you can evaluate.

Where a command settles the check, put it in `check_cmd`, written so exit 0 means the
check holds. Only a command you ran here, against this candidate. Never a fix. If it exits
0 as you file the finding, the check is wrong or there is nothing to file.

Be detailed about what you observed and silent about why you think it matters. No
rationale for a severity: a finding that needs a paragraph to justify it is a preference
filed at the wrong severity.

Where the brief names a visual surface, your evidence must say what you saw in the
render. Check it is current — a render older than the files it renders is stale, and a
stale render is not evidence. If it is missing, stale, empty, or the recipe errored, do
not grade the source in its place: return "revise" with one finding whose check is the
render you need, stated precisely enough for someone to produce it — what to render, at
which state, viewport and seed. Where the brief names none, do not ask for one.

Calibrate severity to consequence, not to how strongly you feel about it. Be blunt about
anything provably wrong — correctness, data loss, security, an unmet acceptance
criterion, a failing check: state it flatly with its anchor, no hedging and no softening.
Be gentle about preference — a defensible call the brief left open, a structure you would
have built differently: one line, "nit" or "minor", and say plainly what you found sound.
Never raise a severity to make a preference get attention.
```

A finding is a **measurement**, and the fields are what a measurement needs to be acted on
by someone who was not there:

- **`anchor` must survive an edit** — symbol name plus a short verbatim quote, line as a
  hint only. Line numbers shift the moment the builder touches the file.
- **`observed` and `check` are the two ends of one line.** Where it is now, where it must
  be, in the same units. Either one alone is half a finding: a target with no measurement
  makes the builder re-derive what you just read, and a measurement with no target is the
  guessing game above.
- **`check` is an observation, not an instruction — and it names the target, not the
  deviation.** "Add a null guard" is a demand; "the null case is handled better" is the
  deviation restated; "`Frame()` returns early when `entity` is invalid" is a check, and a
  later round can confirm it mechanically. Two tests it must pass: could a builder that has
  read only this sentence aim at the right state, and could a second critic decide it the
  same way? What can't be phrased as an observation is taste, and taste is a `nit` at most.
- **`sites` is the pattern**, listed in full or empty. It also settles scope: every site
  named here is inside this finding, so fixing them all is not an out-of-scope edit and
  does not re-open anything the builder was not asked to touch.
- **`check_cmd` is optional and is where the round budget actually goes.** A check phrased
  as an observation is often one a command can decide, and a finding decided by a command
  never reaches an agent at all: `fanout.py deciders <slice-id>` prints them for you to run
  in Step 5. It stays a *decider*, never a fix — "`grep -n 'nullopt' store.cpp`" tells the
  builder nothing about how to get there, which is the point.
- **`approved` is a claim you'll be held to** — whatever is listed there is out of scope for
  every later round unless the code underneath it changes.

Critics that can run something (compile it, execute the tests, diff it) should. A critic
whose `evidence` contains only opinions is a weak gate; treat its `accept` as unproven.

### Detailed about the observation, never about the opinion

"Be more detailed" is good advice pointed in one direction only. Every field above records
something the critic *saw*: a measurement, a location, a list of sites, a command that was
run. None of them records what the critic *thinks* — no rationale for the severity, no
argument for why this matters, no account of what it considered and rejected.

That asymmetry is the whole discipline, and it is worth stating plainly because the two
kinds of detail read alike on the page and behave nothing alike downstream:

- **Observation detail is bounded and reusable.** "#808080 at r1/hero.png centre" is one
  line, it is the same length whoever writes it, the builder can act on it without trusting
  the critic's judgement, and the next round can check whether it moved.
- **Opinion detail is unbounded and load-bearing on nothing.** A paragraph on why the
  colour matters does not tell the builder what colour to use, cannot be verified, and is
  carried by every agent downstream of the verdict — the fold reads all of it.

So: give the number, the location and the list, in one or two lines each. Do not argue.
A finding that needs a paragraph of justification to land is usually a preference filed at
the wrong severity, and the fix is the severity.

The cost is small and lands in the right place. Findings are per-slice delta text sent to
one builder — never the cached shared prefix — so a few extra lines are far cheaper than
the round they save. What must stay short is the *count* of findings, not their precision:
specific still beats comprehensive, and the ratchet guard in Step 5 is what holds that.

### The target is not the route

A finding tells the builder *where* (`anchor`, `sites`), *what is wrong* (`claim`), *where
it stands now* (`observed`) and *what would be true once it is right* (`check`). It
withholds only the route — the specific edit that gets there. Those are separate things,
and the loop fails differently when you drop each:

| Withheld | The builder | Cost |
|---|---|---|
| the route (`how`) | picks its own way to the stated target | none — this is the design |
| the target (`check` names the deviation) | guesses; red, then blue, then green | every round, from round 1 |
| nothing (`check` states the fix) | complies | the check stops testing the artifact |

The middle row is the expensive one, and it is the one that looks fine on inspection: "the
colour is off" is a legitimate observation, it is anchored, it is not an instruction, and
it is unfalsifiable in exactly the way that matters — only the critic can tell when it
stops being true. Naming the target is not prescription. "The car is red" is a fact about
the destination; "respray it with PPG Viper Red" is a route. A critic that will not say
red is not protecting the builder's autonomy, it is running a guessing game.

Withholding the route stays right, and `remedy` (Step 5) is its one licensed exception,
unlocked after a builder has spent a round against a stated target and still missed. That
gate only means anything if the target was stated. A `remedy` handed out to rescue a check
that never named its target is the loop paying an extra round to say what round 1 should
have said in six words.

So the ways to reach a good result faster are not "say more": state the target in the
check, make it decidable without an agent (`check_cmd`, above), and stop the loop early
when the gap is not closeable here.

### Demand the visual when there is a visual to demand

The rule is conditional, and both halves of the condition do work:

- **Something visual exists — or the candidate already ships what produces it — so the
  critic demands it and judges that.** A rendered page, a chart, a UI state, a game frame,
  a diagram, a laid-out document. Never grade the markup, the shader, or the plotting call
  in place of the thing they produce: source that *should* centre the legend and a render
  showing the legend clipped are two different facts, and only one of them is the artifact.
  A verdict on a visual axis whose `evidence` names no render is unproven in exactly the
  way an untested `accept` is unproven.
- **Nothing visual exists** — a pure refactor, an API design, a parser, a prose slice with
  no layout — **so the critic does not ask for one.** A screenshot manufactured to satisfy
  a checklist costs a round and proves nothing, and a critic that pushes a builder to
  invent a visual surface has widened the brief on its own authority.

**Producing it is the builder's job and yours, never the critic's.** The brief carries the
recipe (Step 2) and the builder runs it (Step 3), so in the normal case the render is
already sitting in `renders/<slice-id>/r1/` and the demand never has to be made.

**When the critic demands and finds nothing to look at** — missing, empty, stale, or a
recipe that errored — that is a broken inspection path, not a low score. *Stale* has a
mechanical tell worth stating in the prompt: a render older than the files it renders is
a picture of a candidate that no longer exists, and grading it is worse than grading
nothing, because the verdict looks evidenced. The critic states the demand precisely (what
to render, at which state, viewport, seed) and returns `revise` with a finding whose
`check` is the render's own existence:

```
severity: "blocker"
check: "renders/hero-empty/r1/empty-state.png exists, is newer than the candidate,
        and shows the placeholder copy at 1280px"
```

`blocker`, not `minor` — only `blocker` and `major` hold the gate, so a softer severity
ships a visual axis nobody ever judged, which is the exact hole this section exists to
close. And the critic does not fall back to grading the source: a guess dressed as a
verdict is worse than a stalled round, because the fold cannot tell the two apart.

Then **satisfy the demand rather than waving it away.** Re-run the recipe yourself if it is
mechanical, hand the demand back to the builder if it is not, and re-spawn the critic on
the render. That round is cheap: the demand is delta text and the prefix is still warm.
Where you produced the render yourself the finding still closes honestly — mark it
`verified` once the render exists, with the `reason` saying who made it, since a harness
you had to fix by hand is a fact about the run worth carrying into the fold report.
Only when the render genuinely cannot be produced here — no headless renderer, no harness,
an asset nobody has — do you record the visual axis as **unscored** in the fold report and
say why. Never let a source-only verdict stand in for it silently.

### Soft where it can be, harsh where it must be

Severity is a claim about consequence, not a measure of how strongly the critic felt.
Calibrate both the severity and the tone that carries it to what being wrong would cost:

- **Harsh** where the artifact is wrong and provably so — correctness, data loss, security,
  an unmet acceptance criterion, a failing oracle, a claim the candidate makes that its own
  render or test output contradicts. State it flatly, once, with the anchor: no hedging, no
  praise sandwich, no "you might consider". Softening a real failure is the expensive
  direction; the gate opens and the fold reports as shipped something nobody approved.
- **Soft** where the disagreement is preference — a defensible call the brief left open, a
  structure the critic would have built differently, a style choice with no consequence
  downstream. Say it once as a `nit` or `minor`, phrase it in the builder's own terms, and
  approve the surrounding work explicitly. Do not inflate severity to make a preference get
  attention; that is precisely how `major` stops meaning anything.
- **Soft on the builder, never soft on the check.** Harshness is refusal to grade on a
  curve, not insult, and it is never a licence for contempt. Where the candidate is sound,
  say so plainly — a critic that finds nothing has produced a result, not failed at its
  job, as long as its `evidence` shows it looked.
- **Softness applies to severity, never to `approved`.** Going easy on a preference is
  free; listing a file as approved to be generous is not, because the re-open logic in
  Step 5 treats that list as examined and will not look there again. Approve exactly what
  you inspected, however warm the rest of the verdict is.
- **A defect in the brief is not a defect in the candidate.** When a builder was misled by
  an ambiguous brief, say that in the finding's `claim` and keep the severity honest. The
  brief is the orchestrator's error to fix between runs, not the builder's to absorb.

The tie-breaker when a finding sits between `major` and `nit`: ask what it costs to be
wrong in each direction. Wrong-harsh on a nit costs one builder round. Wrong-soft on a
blocker ships the blocker. Where the two are symmetric, go soft; where they are not, go
harsh.

The loop punishes each failure direction differently. A uniformly harsh critic inflates
severities until the gate can no longer discriminate and the builder spends its two rounds
on taste. A uniformly soft critic returns `accept` with a thin `evidence` array and the
gate becomes theatre. Both leave the same kind of fingerprint on the verdict JSON, so don't
eyeball it — measure it:

```bash
python scripts/fanout.py calibration --strict
```

It reports the severity histogram per critic and flags seven documented failure modes:
`INFLATION` (three quarters of findings blocking), `RUBBER-STAMP` (`accept` on almost no
evidence), `OVER-APPROVED` (an approved list out of proportion to what was examined),
`CHECK-AS-DEMAND` (a `check` that opens with an imperative — the most common quality leak
in the loop), `NO-TARGET` (a `check` that names the deviation and not the target — "the
colour is off", which the builder can only answer by guessing), `NO-DELTA` (a `check` with
no `observed` beside it, so the builder must re-measure what the critic just measured), and
`THIN-ANCHOR` (a blocker anchored only on a line number, which the first edit will lose).

`NO-TARGET` and `NO-DELTA` are the two worth fixing before the builder sees the finding
rather than after. The others cost you a misjudged severity or a weak approval; those two
cost the round itself, and then the next one.

Run it after the critic wave and again before the fold. `--strict` makes any flag exit 1,
so the run stops until each flagged verdict has been read in full and repaired or overruled;
the gate itself never consults calibration, because a heuristic about tone must not hold
real findings. Any calibration you overruled belongs in the fold report.

### Why there is no strictness dial

The obvious next thought is tiered critics: a lenient screening pass to catch gross
failures cheaply, then a strict gate round. Resist it, for three reasons that are specific
to how this loop is built.

Screening is already done, and done better. A missing, empty or truncated candidate never
reaches a critic (see *When an agent fails*), and the cheap oracles in Step 5 — build,
tests, lint, grep, the render — resolve the mechanical failures a lenient critic would
catch, at near-zero cost and with better reliability than an agent reading code.

Strictness is not comparable across critics. In `compete` mode the scores rank candidates,
so a soft critic on one candidate and a harsh one on another produce a ranking that
measures the critics rather than the work. This is the same reason the brief is sealed and
the rubric is written first.

And the axis that genuinely should differ between rounds already does — it just isn't
strictness. Round 1 reviews everything and may raise anything; a verification round reviews
the delta under the ratchet guard. That difference is mechanically computed by
`fanout.py scope` rather than asked for in prose, which is what makes it hold.

## Step 5 — Verification rounds (never re-review what was approved)

A round that re-reads everything is expensive, and worse, it moves the target so the
builder can never converge and the earlier `accept` turns out to have meant nothing. So a
verification round reviews **the delta and the open findings only**. Mechanism and rationale
in `references/incremental-review.md`.

**1. Snapshot before the builder touches anything.**

```bash
python scripts/fanout.py snapshot <slice-id> <path>...
```

Without this there is no delta and the round degenerates into a full re-review. Paths are
relative to the lane root, and `snapshot` resolves them there: a worktree lane's files are
read from its worktree, never from the same path in the main tree, which still holds the
base. A patch lane is snapshotted after `fanout.py lane <slice-id> --materialize` — its
files exist only once applied — and re-materialized after every new patch.

**2. Send the builder only the open findings**, below the `---` as always:

```bash
python scripts/fanout.py delta <slice-id> --findings
```

It prints the lane's usual block followed by its open blocking findings — each with its
anchor, `observed`, `check`, `sites` and any `remedy` — and the fix-only instruction:
fix only these; say so in the report rather than silently changing anything outside
them; a finding's own `sites` are inside it; a `remedy` is one route, not the target. The
lane block rides along because the scope still binds in a fix round, and `trespass` runs
again before the verifier.

**3. Compute the scope mechanically before spawning any critic.**

```bash
python scripts/fanout.py trespass <slice-id>
python scripts/fanout.py snapshot <slice-id> <path>...   # the new revision
python scripts/fanout.py scope <slice-id>
```

Prints three sets: changed hunks (in scope), previously-approved files referencing a symbol
touched by the diff (**re-opened** — this is what keeps delta-review honest), and everything
else (out of scope, do not read).

**4. Run the cheap oracles first, and re-render.** Build, tests, lint, a grep for what the
`check` describes. Every finding a mechanical check resolves is one the critic never sees.
If the slice has a visual surface, re-run the render recipe — same command, same state —
into the `r<N>` that matches the snapshot you just took in step 3 (`v2` → `r2`). A finding
on a visual axis is verified by looking at the new render beside the old one; "fixed the
clipping" is a claim, and a claim is not a check.

```bash
python scripts/fanout.py deciders <slice-id> --run
```

Prints the `check_cmd` each critic attached to its own findings, and lists the ones that
carry none. Without `--run` it only prints; read the commands before you pass `--run`,
because they were written by an agent and `--run` executes them — in the lane's own tree,
where the candidate is. Exit 0 closes that finding: it is set to `verified` with a `reason`
naming the command and its output. Non-zero means the finding still stands, so it goes to
the builder unchanged. This is the largest single
saving in the loop, ahead of the scope narrowing — a slice whose findings are mostly
mechanised can pass a verification round with no agent spawned at all.

Two things it must not swallow. A visual finding is decided by the renders above, never by
a command proving a file exists. And a finding with no `check_cmd` is not thereby weaker:
most judgement calls have none, which is what the verifier is for.

**5. Spawn the verifier** — same shared prefix, tiny delta:

```
Read <run-dir>/brief.md in full. It is the authoritative context.
Then read <run-dir>/rubric.md.

---
VERIFICATION ROUND <N> for <slice-id>.

Open findings to verify: <run-dir>/verdicts/<slice-id>.json (status == "open")

Lane root: <the worktree, the materialized patch, or the main tree>
In scope: <paste the IN SCOPE section of `scope` — the changed hunks, with the
enclosing symbol of each>
Re-opened files: <paste the RE-OPENED section of `scope`>
Out of scope: <paste the OUT OF SCOPE section of `scope`>

Renders: <paste both paths — the new render dir and the previous one> — for any
finding on a visual axis, decide it by comparing the two renders, not by reading the
change that was supposed to produce them.

For each open finding, decide `verified` or `unresolved` against its own `check` — not
against a better fix you would have preferred, and not against any `remedy` on the
finding. Record the observation that decided it in a "reason" field. A fix that satisfies
the check is verified even where you would have written it differently; a check that
still fails is unresolved even where the builder clearly tried. Do not promote a nit to
keep the round busy.

Every finding you mark `unresolved` must also carry a "remedy": one or two sentences
naming a concrete route to the check — the specific change, at the anchor. A builder has
now spent a round on this finding against the check alone and not closed it, so the check
alone has been measured and found insufficient. The remedy is non-binding and it is not
the target: the check stays the contract, and next round you judge the check, not whether
the remedy was followed. If you cannot name a route because the gap needs a decision, an
asset, or a change outside this slice, write that in "remedy" instead and say what is
missing. That sentence ends the loop early, which is worth more than another round.

You may raise a new finding ONLY if it sits inside the in-scope diff or a re-opened file.
Anything outside that is out of bounds — except a genuine blocker (correctness, data
loss, security), which you may raise with "late": true and an explanation of why it was
not visible in round 1. Late minors and nits are logged as follow-ups.

Do not read files listed as out of scope. Do not re-score axes with no in-scope change;
carry the previous score forward.
```

**6. Gate.**

```bash
python scripts/fanout.py gate <slice-id>
```

Exit 0 = done, 1 = another round, 2 = escalate. Default cap is two verification rounds. If
a slice can't converge in three attempts, the brief was wrong or the slice was badly cut —
both your errors, not the builder's. Escalate with what the rounds disagreed about.

To ship a known issue past the gate, set that finding's status to `waived` with a `reason`.
That is an orchestrator decision, it is recorded, and it appears in the fold report. The
`reason` is not optional — `gate` stops on an unreasoned waive, because a waive is the one
path where a blocker leaves the loop by decision rather than by fix, and an unexplained one
is indistinguishable from a mistake.

## Step 6 — Integrate

Every lane has passed its gate on its own. Integration is where they become one result,
and it is a step of its own because it can fail on its own: two lanes that are each
correct can still disagree at the seam, and per-slice critics are blind to that by
construction.

**Choose what lands.**

- `partition` → every lane whose gate passed. Read-only lanes have nothing to land; their
  candidates go straight to the fold.
- `compete` → one lane. Read the **verdicts**, not the candidates: rank by rubric score,
  break ties on unresolved findings weighted by severity, then read the top two candidates
  yourself before choosing. With a visual surface, look at the renders side by side before
  you rank — the verdicts tell you what each critic saw one at a time, and a comparison
  across candidates is the one judgement no critic was allowed to make.

**Synthesis is a lane, not an edit.** Taking the winner's structure and the runner-up's
specific better idea is often right — but writing it yourself makes you a builder, and
you can no longer judge it. Add the synthesis to `synthesis.json` (same schema as
`slices.json`, plus `"from": "<winner>"`, strategy `worktree`); it is decided after the
candidates exist, so it is legitimately outside the sealed plan. `fanout.py lane <id>`
starts its worktree from the winner's change, a builder applies the one named idea, and a
critic judges only what differs from the winner. Then it is the lane that lands.

**Land it.**

```bash
python scripts/fanout.py integrate --check          # partition: every gated lane
python scripts/fanout.py integrate                  # compete: add --winner <slice-id>
```

`integrate` works per strategy, in provider-before-consumer order: shared lanes are
already in place, patch lanes are applied, worktree lanes have their diff against the base
applied. It re-runs `trespass` first and refuses to land a lane that fails it, runs
`git apply --check` for every lane before changing anything, and records what it applied in
`integration/applied.json` so `integrate --revert` can undo it. Nothing is committed and no
branch is merged — the result sits uncommitted in the main tree, and committing it is the
user's call.

**A conflict is never resolved by hand.** Lanes own disjoint files, so a patch that will
not apply means a lane wrote outside its scope or the main tree moved underneath it.
Either way it goes back to the lane. Hand-merging here would ship the one change in the
run that no critic has seen.

**Apply the hotspot entries.** `integrate` prints what each lane asked for under *Hotspot
entries*. Apply them yourself — this is the one place you write, and only because it is
mechanical: entries in a registry or lockfile, never logic. Regenerate what has a
generator (a lockfile, a route index) rather than editing it. An entry that needs judgement
is a slicing error: note it for the fold.

**Run the whole-system oracles.** Full build, the whole test suite, and — where there is a
visual surface — a render of the merged result into `renders/integration/r1/`. Per-lane
tests prove nothing about the seams. A clashing heading scale, a doubled margin, two
different empty states: none of those exist in any single lane's picture, which is exactly
why the per-lane critics all passed.

**Spawn the integration critic** — `partition` runs, and `compete` runs whose synthesis
joined two candidates. Same shared prefix:

```
Read <run-dir>/brief.md in full. It is the authoritative context.
Then read <run-dir>/rubric.md.

---
INTEGRATION REVIEW. The lanes are merged in the main tree.

Judge the seams only — where one lane's work meets another's. Lane internals were
approved by their own critics and are not your business.
Seams to verify, each contract a check: <paste the seams `integrate` printed>
Whole-system oracles: <paste build and test results>
Merged render: <run-dir>/renders/integration/r1/ (if the brief names a visual surface)

Write your verdict to <run-dir>/verdicts/integration.json in the usual schema. Every
finding also carries "owner": the slice id of the lane that must change to fix it —
for a broken contract, the provider. A seam no single lane can fix is a contract
that was wrong: say so in the claim, at its honest severity.
```

**Route seam findings to their lane.** `integrate --revert`, then the owner lane gets a
fix round like any other: `fanout.py delta <owner> --findings` includes the seam findings
it owns. Re-integrate, re-run the oracles, and have a verifier decide the open seam
findings.

```bash
python scripts/fanout.py gate integration
```

The seam gate allows **one** fix round, not two. A seam still open after one fix means the
contract itself was wrong, and no builder can repair a plan: escalate with the contract
and what each side built. Never fix a seam on the integrated tree directly — that fix is
in no lane, has no critic, and is gone on the next `--revert`.

## Step 7 — Fold

Read the **verdicts**, not the candidates. That keeps your context small enough to hold the
whole picture, which is the only place cross-cutting judgement can happen. Pull up a full
candidate only when a verdict is contested, unclear, or flagged by
`fanout.py calibration` — reading verdicts instead of candidates only works while the
verdicts are worth reading. Never edit the brief to fix a slice.

Before writing the report, drain the findings that are leaving unfixed:

```bash
python scripts/fanout.py followups
```

That writes `follow-ups.md` — everything waived with its reason, everything raised late,
every deferred `minor` and `nit`, across all slices and the seam verdict, plus each
builder's reported *Assumptions*, *Scope deviations* and *Open questions*. Every other
finding in this loop has an outlet: it gets fixed, or it holds the gate. These have
neither, and with nowhere to land they stay in files that nobody opens again — which is how
a run reports clean while carrying a dozen things a critic actually flagged.

Finish with a short fold report: what shipped and where it sits (uncommitted in the main
tree), what was rejected and why, any lane landed with `--force` or any trespass you
accepted, any visual axis left unscored because the render could not be produced, a
pointer to `follow-ups.md`, and which of the builders' assumptions a critic actually
checked. That last one is the only judgement the tooling cannot make for you — it can
collect the assumptions, not verify them — and together with the follow-ups it is where
fan-out runs actually go wrong: not in what the critics caught, but in what everyone agreed
to stop looking at.

Then clean up: `fanout.py lane --remove` deletes the worktrees and their branches. Do it
after the fold, never before — `integrate --revert` and any fix round need them.

## When an agent fails

A missing, empty, or truncated candidate is a **failed** slice, not a rejected one. There
is nothing to judge, so don't spawn a critic for it and don't let it enter the fold as a
low score. Re-spawn once with the identical prompt; a second failure points at the slice or
the brief, so escalate rather than trying a third time.

A render recipe that fails is different again: it is sealed and identical for everyone, so
if every builder reports the same error, that is a defect in the brief and re-spawning
will reproduce it exactly. Fix the recipe in a new run, or finish this one with the visual
axis unscored and say so. One builder failing where the others rendered fine is that
builder's problem and re-spawns normally.

The same goes for a verdict that won't parse or arrives with an empty `evidence` array —
that is not a verdict. Re-spawn once, then judge that slice yourself and say so in the fold
report.

A lane that trespasses is neither failed nor rejected: it goes back to its builder with
the `trespass` list before any critic sees it, and a second trespass is a slicing error to
escalate. A lane whose worktree cannot build because a fresh checkout lacks something is a
setup defect — yours, not the builder's; fix the lane and re-spawn with the identical
prompt.

A partial fan-out is still useful. If three of five slices land, integrate and fold those
three and report the other two as unattempted rather than discarding a good round for
being incomplete — as long as none of the three consumes a contract from the missing two.

## Resuming

```bash
python scripts/fanout.py status
```

Reports the newest run: each lane with its strategy and whether its worktree or patch
exists, which lanes are integrated, which candidates exist, which have verdicts, how many
snapshots each slice has. Pick up from there rather than restarting — the brief is sealed, so the
ground truth is intact, and `check` will say so if it isn't.

## Cost discipline

Fan-out multiplies token spend by roughly N. It pays for itself when the slices are truly
independent or the approach is genuinely uncertain, and not on a task one agent could do in
one pass — parallelism buys wall-clock time and diversity, never correctness by itself.
Three agents confidently wrong in the same direction is the normal failure mode, and it is
why the critics are separate agents with a pre-written rubric rather than a self-review
step.

## Reference

- `commands/fan-out.md` — an optional wrapper around the `/fan-out` the skill already
  provides, adding the pre-flight checklist. Copy it to `.claude/commands/` only if you
  want that (see Invocation above); do not install both spellings.
- `references/prompt-caching.md` — what actually caches, what silently doesn't, the
  ordering rules, and why the pathfinder goes first. Read before changing prompt shapes or
  the spawn sequence.
- `references/incremental-review.md` — the finding lifecycle, why re-opening approved scope
  is necessary, mechanical deciders, when a check earns a remedy, cross-slice cascades, the
  ratchet guard, anchor drift. Read before running a verification round or changing the
  verdict schema.
- `scripts/fanout.py` — run dir, plan/seal/check, lane/delta/trespass,
  snapshot/scope/deciders/gate, integrate, calibration, followups, status. Deterministic
  and model-free; the only agent-authored strings it ever executes are the critics'
  `check_cmd`s, and only under `deciders --run`. `plan` and `scope` apply the same coupling
  rule, before and after the fact respectively; `trespass` and `integrate` hold every lane
  to the `owns` it was sealed with. `gate` decides the work; `calibration` lints the
  critique and decides nothing; `followups` drains what the run is choosing not to fix.
