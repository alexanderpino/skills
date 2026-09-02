# Decomposition: profiles, splitting, sizing, ordering

## Contents

1. Story splitting vs subtask decomposition
2. Splitting patterns (story level)
3. Decomposition profiles (subtask level)
4. Sizing rules
5. Ordering and dependencies
6. Mandatory subtasks
7. Naming

---

## 1. Two different operations

Do not confuse them.

**Splitting** produces more *stories*, each independently valuable and
releasable. Trigger it when the story is too big to refine: >7 rules, >3 repos,
>25 files, multiple user outcomes.

**Decomposition** produces *subtasks* inside one story. Subtasks are not
independently valuable; they are units of work and review. Only the parent story
delivers value.

This skill decomposes by default. It *recommends* splitting when blast-radius
thresholds trip, and shows the proposed split, but does not restructure someone's
backlog unasked.

---

## 2. Splitting patterns (story level)

When recommending a split, name the pattern used.

**SPIDR** `[P: Mike Cohn]`:
- **S**pike - carve out the unknown; the spike answers a question, the rest
  builds with the answer
- **P**aths - split by workflow path (happy path first, then alternates)
- **I**nterfaces - split by client/platform/entry point (API first, then UI)
- **D**ata - split by data variety or source (one currency, then all)
- **R**ules - split by business rule (basic rules now, edge rules later)

Additional patterns `[P: Lawrence & Green, "Patterns for Splitting User
Stories"]`: by operation (CRUD), by acceptance criteria, by effort, by
simple-vs-complex, and "defer performance" - build it correct first, then make
it fast as a second story with an explicit number.

Anti-pattern: splitting horizontally into "backend story" and "frontend story".
Neither is releasable; you have created a dependency pair with coordination cost
and no earlier feedback `[F]`.

### Splitting an epic: map it before you cut it

SPIDR tells you *how* to cut one story. For an epic it answers the wrong
question, because the hard part is not the cut, it is knowing which slice is
first. Lay it out as a story map before proposing a split `[P: Patton, User Story
Mapping, 2014]`:

1. **The backbone**, left to right: the steps a user actually goes through, in
   the order they go through them. Not features - activities.
2. **Under each step**, the variations and details, most essential at the top.
3. **Cut a horizontal line** across the whole map. Everything above it is the
   first release: the thinnest path that lets someone complete the whole journey
   badly rather than half the journey well.

That line is the walking skeleton, and it is what makes the first story's value
arguable instead of asserted. A vertical column ("everything about payment") is
usually not a release; a thin horizontal slice through every column usually is.

Two things the map gives you that a split list does not: the steps nobody
mentioned in the ticket become visible as gaps in the backbone, and the argument
about scope moves from "which stories" to "where the line goes", which is a
conversation people can actually have.

Refine one story from above the line properly, and say which one you chose and
why - that is more useful than seven shallow refinements.

---

## 3. Decomposition profiles

Set via `profile:` in config. Profiles change subtask shape, not the rest of the
pipeline.

### `vertical-slice` (default)

Each subtask is a thin end-to-end path that leaves the system working
`[P: Cockburn, walking skeleton]`. Subtask 1 is the narrowest possible version
of the feature that is genuinely usable; later subtasks widen it.

```
S1 [api] Persist and return a fixed 0% tax line on checkout   (AC1)
S2 [api] Compute tax from the rate table for NL orders        (AC1, AC2)
S3 [api] Apply reverse-charge rule for EU B2B                 (AC3)
S4 [web] Render the tax line in the order summary             (AC4)
```

Use when: the team merges to trunk frequently, and partial feature states can be
hidden behind a flag. Best default for AI implementors - each subtask is
independently verifiable end-to-end.

### `layered`

Subtasks follow architectural layer or discipline: schema, backend, API,
frontend, tests, docs. Common in enterprises with separate specialists or
handover-based teams.

```
S1 [api] Add tax_rate table + migration
S2 [api] TaxCalculator domain service + unit tests
S3 [api] Extend POST /orders response with tax breakdown
S4 [web] Order summary tax line
S5 [api] Contract tests for the new response shape
```

Use when: the house convention demands it, or ownership genuinely splits by
layer. Accept the cost - nothing is demonstrable until the last subtask lands,
so put a demonstrable integration point in the plan explicitly.

### `workflow-phase`

Subtasks follow the delivery process: design/spike, implement, test, review,
release/rollout. Common where the process is audited or where a design artefact
must be approved before build.

```
S1 Design note + ADR for tax rounding strategy   (spike, 0.5d)
S2 Implement per the ADR
S3 Test: unit + contract + one e2e path
S4 Rollout: flag on for NL, monitor, flag on globally
```

Use when: governance requires phase evidence. Combine with `vertical-slice`
inside S2 if the implement phase exceeds one day.

### `expand-contract`

For the change vertical slicing cannot express: a wide, mechanical migration -
rename a symbol across forty files, move every call site to a new signature,
swap a library. Forcing that into vertical slices produces slices that are not
demoable and a ≤8-file cap that makes the honest plan impossible to write, so
the profile makes the shape explicit instead `[P: Pocock, to-tickets - wide
refactors follow expand-contract rather than vertical slices]`.

Three phases, and the third is the one teams skip:

```
S1 [api] Add the new signature alongside the old one        (feature, expand)
S2 [api] Move every call site to it                         (migration, mechanical)
S3 [api] Delete the old signature and its tests             (feature, contract)
```

- **Expand** adds the new path without removing the old. Nothing breaks, and it
  is a normal, small, reviewable subtask.
- **Migrate** is the wide one. It is allowed to be wide *because* it is
  mechanical: a codemod or a find-and-replace whose `done_when` is "the codemod
  ran and the suite is green", not a judgement call per site. If it needs
  judgement per call site, it is not mechanical and it is not this profile.
- **Contract** removes the old path. Without it you have shipped two ways of
  doing the same thing and a comment promising to clean up, which is how the
  next refinement in this area finds two conventions and cites the wrong one.
  `SUB016` fails a bundle that expands and migrates without contracting.

The contract step is a subtask in *this* story, not a follow-up, unless
something outside the team still calls the old path - in which case it is a
follow-up with a real trigger and a `blocks` link, per `references/series.md`.

Use when: the change is mechanical and wide. Do not use it to smuggle a
judgement-heavy refactor past the size caps.

### `bugfix`

Bugs refine differently from features and the other profiles handle them badly.
A bug's acceptance criteria are not "the feature works" but "the reported case
produces X, and the class it belongs to produces X too".

```
S1 [api] Reproduce the double-charge in a failing test   (test, covers AC1)
S2 [api] Fix at the root cause identified in D1          (feature, covers AC1, AC2)
S3 [api] Guard the adjacent case surfaced by the repro   (feature, covers AC2)
```

Rules `[L]`:

- **The failing test lands first**, in its own subtask, and is the thing that
  proves the bug exists. If you cannot write it, you have not reproduced the bug
  and the story is not ready - that is a red card, not a detail for the
  implementer.
- **The root cause is a decision**, recorded with its evidence, not a sentence in
  the technical notes. "Why did this happen" and "why here" are challengeable
  claims and belong in `decisions` where someone can disagree.
- **Get to it by asking why until the answers stop being about code** `[F: five
  whys, Toyota]`. "The response was 500" → "the handler raised" → "the file was
  over the limit" → "nothing validates size before the read" → "the limit lives
  in the client and was never enforced server-side". Each step must be evidenced
  like any other claim (`path:line`), or the chain is a story you told yourself.
  Stop at the first cause you can actually fix and own; record the ones past it
  as risks or follow-ups rather than widening this ticket. Two chains from the
  same symptom is a signal that there are two bugs.
- **Fixing the symptom is an explicit choice**, not a default. If the root cause
  is out of reach this sprint, record that as a locked decision with the reason
  and a follow-up ticket. Do not let it look like the root cause was fixed.
- **The regression test is the AC coverage.** A bugfix subtask whose `done_when`
  contains no command that fails before the fix has not been verified.
- Intake needs steps to reproduce, expected behaviour, actual behaviour, and
  which environment and version. Missing any of the four is a blocking question.

Use when: the item is a defect. Do not force a bug into `vertical-slice` - there
is no valuable thin slice of "stop being wrong".

### `research`

The item's deliverable is information. Everything else in this file plans a
build; this profile plans a *finding out*, and its whole job is to stop before
the build.

```
S0 [api] Measure async VAT lookup p95 against the fixture   (spike, covers AC1, AC2)
```

Usually that is the entire decomposition. One question, one probe, one answer.

Rules `[L]`:

- **The criteria are about the answer, not the behaviour.** "A measured p95 is
  written down in ms" and "D9 records which design the measurement supports and
  the number that decided it". If you can write "the user sees X", this is not a
  research item.
- **Every possible answer is named in advance, as examples on the criterion.**
  `under 200ms → build the async design`, `200ms or over → build the pre-computed
  one`. This is the Real Options discipline applied to the probe: an experiment
  whose outcomes you have not priced is one you will rationalise afterwards. It
  is also what makes `AC009` catch the missing value standing exactly on the
  threshold.
- **The spike carries `covers`.** A spike on a delivery story is exempt from
  covering a criterion (`UNCOVERED_OK_KINDS`); here it is the only thing that
  can, so it does.
- **The timebox is the price of an option, not an estimate** `[F: Real Options,
  Maassen & Matts]`. `SPK002` holds the spike to
  `decomposition.spike_timebox_days`. A spike that overruns has stopped buying
  information and started doing the job - and the whole point of buying the
  option was to not do the job yet.
- **No build subtasks.** `SPK004` reports a research item that plans `feature` or
  `migration` work: whatever the answer turns out to be, that subtask was written
  before it. The build belongs to the story this research informs, linked with
  `blocks` so the order survives outside your head (`references/series.md`).
- **Something must be waiting for the answer.** On a research item that is the
  required `decision` intake dimension; on a delivery story it is
  `decisions[].spike`, and `SPK003` reports a spike no decision defers to. A
  spike whose answer changes nothing is reading, and reading is not a ticket.
- **The domain is usually `complex`.** That is the honest reason the item exists,
  and `CYN001` already demands a probe there. If you can classify it
  `complicated`, ask why this is not simply refined.

Use when: `intake.kind` is `spike` - the discovery labels set both (`TRI005` if
the profile disagrees). Do not use it to park a story that is merely vague: the
fix for an unclear story is the intake questions, not a spike.

### `custom`

Supply an ordered list of subtask kinds with conditions in config. The engine
just applies them; all other rules still hold.

---

## 4. Sizing rules

- **≤ 1 day of work per subtask.** The Scrum Guide 2020 describes this as what
  Developers "often" do when decomposing Sprint work `[P]`; treating it as a hard
  cap is this skill's choice `[L]`, because one day is also the size at which a
  single PR stays reviewable. If it does not fit, it is not decomposed yet.
- **≤ 8 files touched** (configurable) `[L]`. Above that, review quality drops
  and agent implementors lose the plot.
- **One repo per subtask** `[L]`. A subtask that spans repos is at least two
  subtasks, because it is at least two PRs, two CI runs and possibly two
  reviewers.
- **One PR per subtask** `[L]`. This is what makes the subtask reviewable and
  makes `done_when` meaningful.
- **≤ 12 subtasks per story** (configurable) `[L]`. More is a split signal.

SMART for tasks `[P: Bill Wake, "INVEST in Good Stories, and SMART Tasks",
2003]`: Specific, Measurable, Achievable, Relevant, Time-boxed. INVEST applies to
the parent story; SMART applies to the subtasks. Do not apply INVEST to subtasks
- "independent" and "valuable" are not properties subtasks are supposed to have.

### The floor, and why one is needed

Every other budget here is a ceiling: at most a day, at most eight files, at most
twelve to read, at most twelve subtasks. A config that only has ceilings leans one
way, and the plan it produces is a drift of slivers - each one defensible, the set
of them exhausting `[N]`.

So there is a floor. **A subtask earns its overhead by being separately
reviewable.** Two pieces of work that will be read together, reviewed together and
merged together are one subtask, however tidy the split looks on the board.

The overhead is not rhetorical. Each subtask costs a ticket, a brief, a review, a
CI run and a handoff - and since the shared context exists, each one costs one
more full load of the dossier: the glossary, the conventions, the ruled-out list.
Three slivers pay for that three times to deliver one pull request's worth of
work. For an agent implementor that is the dominant cost, and it buys nothing.

Two gates hold the floor:

- `SUB017` - under `min_subtask_days` (default 0.25) and touching one file. That
  is a commit inside another subtask, not a subtask.
- `SUB018` - two subtasks in one repo, on the same criterion, in a straight chain
  of two, whose combined size is still inside every cap. Merging removes a
  handoff; the gate says so and leaves the decision to you, because the one good
  reason to keep them apart is that different people review them.

Deliberately exempt, because they are separate for a structural reason rather
than by accident: a `spike` (it holds a deferred decision, `DEC004`), a `rollout`
(it happens days later), and any kind your `decomposition.mandatory` policy asks
for separately.

That last exemption is worth reading twice. **A mandatory-subtask policy is a
clutter generator, and a deliberate one.** `test: always` means a one-line change
gets a second ticket; `docs: public_contract_changed` means a field rename gets a
third. That may be exactly what your house wants - an audit trail, separate
reviewers - but it is a choice about ceremony, made in config, and it is the first
place to look when a plan feels bureaucratic rather than decomposed.

### Estimating in days

`estimate_days` exists for sizing, not for planning or velocity. It answers one
question: is this small enough to be one reviewable unit? Treat anything above
the configured cap as a decomposition failure rather than a large task.

How to arrive at a number `[F]`:

1. **Reference class first.** Find a subtask in the recent history of this repo
   that touched a similar number of files in the same area, and start from what
   that actually took. A remembered comparable beats a felt estimate.
2. **Count the unknowns, not the lines.** Effort concentrates in the parts you
   had to mark `ASSUMPTION` in Phase 2. A five-file change through code you read
   is smaller than a two-file change through code you did not.
3. **Price the seams.** A subtask that crosses a team boundary
   (`needs_coordination: true`) carries waiting time that is not in the coding
   estimate. Note it in the human text rather than inflating the number.
4. **Round to 0.25 / 0.5 / 1.** Finer granularity is false precision at this
   size, and invites the number to be read as a commitment.

If the honest answer is "more than a day", say so and split, rather than writing
`1.0` to satisfy the gate. `validate.py` cannot tell the difference; a reviewer
can, and the subtask will be the one that stalls the sprint.

---

## 5. Ordering and dependencies

`depends_on` holds subtask ids. The graph must be acyclic.

Ordering rules, in precedence order `[L]`:

1. **Contract producers before consumers.** If S2 consumes a contract S1
   produces, S2 depends on S1. `validate.py` enforces this from the
   `produces_contracts` / `consumes_contracts` fields.
2. **Spikes before what they inform.** A deferred decision's spike blocks every
   subtask whose shape that decision determines.
3. **Migrations before code that reads the new shape**, and expand-then-contract
   for anything with a deploy window: add new column → dual-write → backfill →
   read new → drop old. The contract step usually belongs to a later story.
4. **Riskiest slice first** where 1-3 allow it. Front-load the thing most likely
   to invalidate the plan `[F]`.

Record cross-team dependencies explicitly. If a subtask's CODEOWNERS differ from
the story's owning team, mark `needs_coordination: true` and name the team - this
is the most common cause of a story stalling mid-sprint in a multi-repo estate.

### File ownership

Exactly one subtask owns each file `[L]`. `validate.py` fails a bundle where two
subtasks with no dependency between them write the same path (`PAR001`), and
warns where two ordered subtasks do (`PAR002`, a rebase rather than a conflict).

Write the ownership into the briefs, not just the graph: subtask A's `forbidden`
should say "do not edit `openapi.yaml` — S2 owns it". A dependency edge tells a
scheduler; a `forbidden` line tells the implementor, human or agent, who is
otherwise looking at a file that obviously needs changing.

### Waves

`emit.py` derives topological waves from `depends_on`. Everything in one wave is
schedulable in parallel and, by the ownership rule, touches disjoint files.

Read the wave list as a decomposition review: a five-subtask story that comes out
as five waves of one is almost always over-serialised. Ask of each edge whether B
truly cannot start without A's output, or whether A was simply written first.

---

## 6. Mandatory subtasks

Configured under `decomposition.mandatory`. Defaults `[L]`:

| Kind | Condition | Why |
|---|---|---|
| `test` | always | prevents "tests later"; may be folded into slices if the house does TDD - set `when: never` then |
| `docs` | a public contract changed | consumers need the change documented before they hit it |
| `migration` | schema changed | migrations have their own review and rollback path |
| `rollout` | a feature flag is introduced | flags without a removal plan become permanent |

A mandatory subtask that would be empty should be removed, not padded. Record
why in the story's technical notes.

`SUB019` closes the vocabulary. A kind is a switch, not a caption: it selects the
Definition of Done that applies, whether the subtask must cover a criterion,
whether the de-clutter gates leave it alone, and whether it is build work a
research item may not plan. A kind nothing recognises matches none of those, so a
one-letter typo silently exempts the subtask from every gate in the file. Houses
that need another kind add it to `decomposition.extra_subtask_kinds` deliberately.

### `migration` is the kind that cannot be taken back

Everything else here assumes a bad change is a revert away - that is what flags,
rollback notes and wave ordering are for. Data does not work like that: the old
value is gone. So the questions that make a migration safe have to be asked while
there is still someone to ask, and three of them are mechanical:

- **`IRR001`** - say how the data change is reversed, or set
  `rollback.irreversible` with a note saying what is lost and what it would be
  restored from. Both are acceptable answers; only silence is not. Whether to
  accept an irreversible step is the story owner's decision, and they can only
  make it if the refinement said so out loud.
- **`IRR002`** - `done_when` has to count or verify something. A migration that
  ran without error and updated the wrong rows reports success, and the report is
  the only thing anyone reads.
- **`IRR003`** - a dry run belongs in `preflight`. Otherwise the first full-size
  execution is the production one, against data with no second copy.

The related story-level questions - volume, duration, whether it can be re-run
safely, whether it holds a lock - belong in the `data` non-functional entry
(`references/acceptance-criteria.md` §4). Idempotency is worth an acceptance
criterion of its own: "run it twice, the second run changes nothing" is the
cheapest criterion in this document and the one most often assumed.

---

## 7. Naming

Pattern from config, default `"[{repo}] {verb} {object}"` `[L]`.

- Start with an imperative verb: Add, Extend, Replace, Remove, Migrate, Wire,
  Expose, Guard, Backfill, Spike.
- Name the object in domain language, not file names.
- No conjunctions. A title containing "and" is two subtasks.
- ≤ 70 characters, because trackers truncate.

Good: `[api] Add reverse-charge rule to TaxCalculator`
Bad: `[api] Tax stuff` · `Backend work for tax and update the frontend too`
