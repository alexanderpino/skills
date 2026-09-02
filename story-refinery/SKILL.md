---
name: story-refinery
description: >-
  User-invoked only - reachable exclusively when the user types /story-refinery or names
  this skill. Do NOT load or act on it because a request looks like refinement, because
  the user mentions a story, ticket, issue, epic, backlog, acceptance criteria, subtasks,
  blast radius or a Definition of Ready, or because a vague request would benefit from
  being refined first. Those are not invocations - answer the request directly instead.
  When it IS invoked: refines a backlog item into an implementation-ready package -
  multi-repo code evidence with file:line citations, locked design decisions, testable
  acceptance criteria, a condensed human-facing description, a machine-readable agent
  brief, and subtasks decomposed per a configurable house profile. Tracker-agnostic -
  works with Jira, GitHub, GitLab, Linear, Azure DevOps, or plain markdown.
metadata:
  invocation: user
---

# Story Refinery

Turns a vague backlog item into an implementation-ready package that serves two
audiences from one set of facts: a **human developer** who shares your context
and needs compression, and an **agent implementor** who shares none of it and
needs explicitness.

The output is a **bundle** (`bundle.json`) plus rendered tracker payloads. The
bundle is the single source of truth. Everything else is a projection of it.

## Quickstart

```bash
python scripts/evidence.py init --config refinery.yaml   # or copy the example by hand
python scripts/evidence.py manifest --config refinery.yaml
python scripts/evidence.py scan --config refinery.yaml -q "<domain noun>" -q "<symbol>"
cp assets/templates/bundle.skeleton.json bundle.json    # author this, phase by phase
python scripts/intake.py assess --bundle bundle.json --write   # enough information? stop if not
python scripts/validate.py bundle.json --config refinery.yaml
python scripts/review.py brief --bundle bundle.json --out reviews/   # blind critics tear it apart
python scripts/review.py digest --bundle bundle.json --stamp        # after you fix what they found
python scripts/emit.py bundle.json --config refinery.yaml --out out/
```

What you author is `bundle.json` and nothing else. Ticket text, agent briefs and
tracker payloads are rendered from it. Never hand-edit one side of a rendered
pair — regenerate both. `assets/examples/example-bundle.json` is a complete
two-repo bundle that validates clean; read it before authoring your first one.

If the session cannot run Python, still author the bundle mentally in the same
order and write the output by hand following `assets/templates/story.md` and
`assets/templates/subtask.md`. You lose the mechanical gates, so say so.

## Provenance markers

Claims in this skill and in the references are tagged so you know what to trust:

| Tag | Meaning |
|-----|---------|
| `[P]` | Primary source, named and checkable |
| `[F]` | Field standard: widely used practitioner consensus, no single canonical source |
| `[L]` | Local convention: this skill's own choice, configurable |
| `[N]` | Novel: invented here, no external backing |
| `[?]` | Unverified: API/tool detail that must be probed at runtime, not assumed |

Carry the same discipline into your output. **Every technical claim in a
refinement either cites `repo/path:line` or is tagged `ASSUMPTION` and becomes
an open question.** There is no third state.

## Core principles

1. **Evidence or assumption.** No unsourced technical assertions. If you did not
   read the file, say so.
2. **Two audiences, one truth.** The human text is short because context is
   shared. The agent brief is long because it is not. They never disagree; the
   agent brief is the human text plus everything a newcomer would have to ask.
3. **Questions are the product.** A refinement that surfaces zero questions did
   not refine anything. Unknowns are the highest-value output.
4. **Decisions are locked, not suggested.** Open technical forks go to an
   explicit gate. An unresolved fork becomes a spike subtask - never
   "the implementer decides."
5. **Decompose by value, order by contract.** Vertical slices by default; where
   repos depend on each other, contract producers are ordered before consumers.
6. **Readiness is mechanical.** `validate.py` decides ready/not-ready. Not vibes,
   not a meeting.
7. **Nothing ships unopposed.** Well-formed is not right. Before handover the
   story and every subtask are read by critics who never saw your reasoning, and
   every finding ends fixed, accepted with a rationale, or rebutted in writing.
   You cannot supply that perspective yourself - you already know what you meant.
8. **Stop at the seam.** Refinement names files, contracts, conventions and
   checks. It does not write the implementation. If you are drafting the diff,
   you have left refinement.

## Workflow

Run phases in order. Do not skip Phase 2 - refinement without code evidence is
just rewording the ticket.

### Phase 0 - Configure

Load `refinery.yaml` from the working repo. If absent, run
`python scripts/evidence.py init --config refinery.yaml` (it writes the annotated
example with the sibling repos it can detect filled in), then confirm the three
settings that change the shape of everything downstream: decomposition `profile`, `tracker.adapter`, and
`tracker.agent_brief.sink`. Do not silently guess a tracker; detect it from the
ticket key format or ask.

### Phase 1 - Intake

Normalize the source item into the bundle's `story` object regardless of origin
(Jira description, GitHub issue body, Slack paste, verbal request). Capture the
original text verbatim in `story.source_text` before rewriting anything - later
phases must be able to check what was actually asked for.

State the story in the 3 C's frame `[P: Jeffries, 2001]`: Card (the intent),
Conversation (what still has to be discussed), Confirmation (how we will know).
Phases 3-5 fill the second and third.

**Sufficiency gate.** Before spending a scan budget, detect whether there is
enough information to refine at all. Read `references/intake.md`.

```bash
python scripts/intake.py assess --bundle bundle.json --write
```

It checks the required dimensions per kind - feature: actor, outcome, trigger;
bug: repro, expected, actual, environment - finds the code anchors a scan
hypothesis needs, and writes `story.intake` plus one open question per missing
dimension. Exit code is the verdict:

| Exit | Verdict | Then |
|---|---|---|
| 0 | `sufficient` | continue to Phase 2 |
| 3 | `scoutable` | run Phase 2 **only** to sharpen the questions, then stop and ask |
| 4 | `insufficient` | stop and ask; there is nothing to scan for |

The detector matches words, not meaning. Read the source text yourself, set
`heuristic: false` on every dimension you confirm, and record what you did
about each gap: `missing` (blocking question), `assumed` (stated assumption plus
a non-blocking question), or `answered` (answer plus who gave it). Replace every
`(best guess: ?)` with your real guess before showing the questions - a question
with a guess attached gets a correction back; a bare question gets an essay.

`validate.py` holds the bundle to this: no subtasks unless the verdict is
`sufficient` (`INT003`), and a dimension is `present` only if its evidence quote
occurs verbatim in `story.source_text` (`INT007`). A mechanism named without an
outcome ("add a Redis cache") is flagged; ask what it is for before scanning for
how to build it.

### Phase 2 - Evidence

Gather multi-repo evidence. Read `references/evidence.md`.

Source resolution order (hybrid, first hit wins per repo):
1. **`provided_index`** - an index another tool already built (e.g. a
   `code-cartographer` output, a repo map, an architecture doc set). Check
   staleness against `git rev-parse HEAD`; a stale index is a warning, not a
   blocker, but every claim drawn from it is downgraded to `[?]`.
2. **`cached_manifest`** - `.refinery/manifests/<repo>@<sha>.json`, invalidated
   by HEAD sha.
3. **`targeted_scan`** - hypothesis-driven `ripgrep` under an explicit file and
   time budget. Never index a whole monorepo to answer one story.

Produce: `evidence.change_surface` (every file you believe will be touched, with
role and line anchor), `evidence.contracts` (OpenAPI/proto/GraphQL/schema/
migration files that cross a repo boundary, with producers and consumers), and
`evidence.conventions` (house patterns observed in real code, each with a
citation - these become instructions for the agent).

```bash
python scripts/evidence.py index --config refinery.yaml      # only if provided_index is configured
python scripts/evidence.py manifest --config refinery.yaml
python scripts/evidence.py scan --config refinery.yaml --query "checkout total" --query "TaxCalculator"
python scripts/evidence.py contracts --config refinery.yaml  # cross-repo edges; direction may be guessed
```

`contracts` is not optional when more than one repo changes: its edges are what
order the subtasks in Phase 5. Where it says the direction is guessed, confirm
which repo owns the file before you rely on it.

### Phase 3 - Example mapping

Run Example Mapping `[P: Wynne, 2015]` over the story: **rules** (blue),
**examples** (green), **questions** (red). Read
`references/acceptance-criteria.md`.

- Each rule becomes one acceptance criterion. Target 3-7 rules; more than 7 is a
  signal the story should be split, not refined `[F]`.
- Each rule needs at least one concrete example. A rule with no example is not
  understood yet.
- Each red question goes into `open_questions` with an owner. Blocking questions
  make the bundle not-ready. This is the correct outcome - report it, do not
  invent an answer to clear the gate.

### Phase 4 - Decision gate

List the genuinely open technical forks that the evidence exposed (storage
choice, sync vs async, where validation lives, migration strategy, feature flag
or not). For each, present 2-4 options with the trade-off stated in one line,
and a recommendation with reasoning.

Present these as a multiple-choice gate and **stop**. Do not proceed to
decomposition with unlocked decisions - the decomposition depends on them.

Each decision resolves to exactly one of:
- `locked` - chosen, with a one-line rationale recorded
- `deferred` - converted into a spike subtask with a timebox and a named
  question it must answer

If `gates.design_decisions: off` in config, record your recommendation as
`locked` with `rationale_source: "assistant-default"` so it is visibly
reviewable later.

### Phase 5 - Decompose

Apply the configured profile. Read `references/decomposition.md`.

Default profile is `vertical-slice` `[L]`: each subtask is a thin end-to-end
slice that leaves the system working `[P: Cockburn, walking skeleton]`.
Alternatives: `layered`, `workflow-phase`, `bugfix`, `custom`. Defects take
`bugfix` - failing test first, root cause as a recorded decision - because there
is no valuable thin slice of "stop being wrong".

Hard rules, enforced by `validate.py`:
- **One subtask = one repo = one PR = one reviewable unit** `[L]`
- **≤ 1 day of work** - the Scrum Guide 2020 describes Developers decomposing
  Sprint work "often to units of one day or less" `[P]`; making it a hard cap is
  this skill's choice `[L]`
- **≤ 8 files touched** (configurable) `[L]`
- SMART `[P: Wake, 2003]`: specific, measurable, achievable, relevant, timeboxed
- Every subtask covers ≥ 1 acceptance criterion, or is explicitly tagged
  `enabling` / `spike`
- Every acceptance criterion is covered by ≥ 1 subtask (coverage matrix)
- Dependency graph is acyclic; contract producers precede consumers
- **Every file has exactly one owning subtask.** Two subtasks writing the same
  file is a merge conflict with humans and two agents fighting over one buffer
  with agent implementors. If a file genuinely needs two passes, add a
  dependency so they are ordered, and say so in both `forbidden` lists.

`emit.py` derives **execution waves** from the dependency graph. Everything in a
wave can run in parallel, which is what a fan-out runner consumes and what makes
the plan legible on a board. Aim for wide waves: a graph that is one long chain
usually contains phantom dependencies recorded only because you wrote the
subtasks in that order.

### Phase 6 - Write for both audiences

Read `references/agent-brief.md`. Both audiences are fields of the bundle you
are authoring (`story.summary_human`, `story.technical_notes_human`,
`subtasks[].human`, `subtasks[].agent_brief`); `assets/templates/bundle.skeleton.json`
shows where each goes.

**Human text** - condensed, decision-dense, assumes shared context. Budgets
(configurable): story summary ≤ 120 words, technical notes ≤ 200 words, subtask
text ≤ 80 words. Write what a senior colleague needs: what changes, why, where,
what is risky, what was decided and why. Delete anything they already know.

**Agent brief** - structured JSON per subtask, no budget, assumes nothing. Its
job is to prevent the four ways agents fail on tickets `[N]`:
- *wandering* → `read_first`, `change_surface`, `context_budget_hint`
- *scope creep* → `forbidden`, `out_of_scope`
- *convention drift* → `conventions` with `path:line` evidence
- *false completion* → `done_when` as runnable commands with expected results

Placement of the agent brief is tracker-dependent and configured via
`tracker.agent_brief.sink` with a fallback chain:
`description_tail` (marker-fenced) | `comment` | `attachment` | `repo_file` |
`custom_field`. See `references/trackers.md`.

### Phase 7 - Validate

```bash
python scripts/validate.py bundle.json --config refinery.yaml
```

Exit 0 = ready. Exit 1 = errors. Exit 2 = the bundle could not be read. Fix or
report. Never hand over a bundle you have not validated.

`validate.py` also lints `refinery.yaml` itself (`CFG001` for keys no script
reads, so a typo cannot masquerade as a setting) and enforces the house
Definition of Done from `validation.definition_of_done` - each rule names the
subtask kinds it applies to and a command pattern their `done_when` must
contain. That is what stops "done" meaning "the code looks right".

If it fails on open questions, that is the finding - present the questions to
the user rather than deleting them.

Then score yourself against `references/rubric.md` and report the weakest
dimension, even when everything passes.

### Phase 8 - Adversarial review

The gates prove the bundle is well-formed. They cannot tell you it is *right* - a
clean bundle can still name the wrong file, carry criteria nobody can test, and
plan a wave that deadlocks. Read `references/critique.md`.

```bash
python scripts/review.py brief --bundle bundle.json --out reviews/
```

That writes one **sealed packet** per critic: their mandate, the finding contract,
and only the slice of the bundle that mandate covers. It withholds your reasoning
mechanically - the conversation, the decision rationales and your self-score are
never put in the packet - because a critic who can see why you chose something
judges the reasoning instead of the artefact.

Hand each packet to a separate sub-agent in **fresh context**. The default panel
`[L]`, each with one question to ask:

| Critic | The one question it exists to ask |
| --- | --- |
| `implementer` | executes the brief literally: where must I guess? |
| `tester` | writes a failing test per criterion: which one is not binary? |
| `archaeologist` | re-opens every citation: which claim is not in the file? |
| `sequencer` | attacks the graph: which subtask cannot start when the plan says? |
| `stakeholder` | source text vs the plan: what is missing, what is uninvited? |

Critics are hostile by assignment. "Looks good" is not a verdict: a critic returns
findings, or records what they tried to break and why it held. Every finding
carries a `locator` that resolves in the bundle and a `failure` naming the
concrete thing that goes wrong downstream - harshness without a locator is vibes,
and the same evidence rule that binds the refinement binds its critics.

**Rubber-ducking** is the solo fallback: no sub-agents available, or a story at or
under `review.rubber_duck_max_subtasks`. Speak as the executor, not the author -
name the first file you would open from each `objective`, narrate each `done_when`
as if running it and predict its output, say of each criterion "passes when ___,
fails when ___", and justify why each subtask is separate. Record it as
`method: "rubber-duck"`; it is lower assurance and the handover should say so.

Then resolve every finding - `fixed`, `accepted` with a written risk, or
`disputed` with a written rebuttal. Silence is not available. If your rebuttal is
correct but rests on something not in the bundle, the critic was still right: the
implementer will see exactly what the critic saw, so put the fact in the bundle.

```bash
python scripts/validate.py bundle.json --config refinery.yaml   # REV gates, after fixes
python scripts/review.py digest --bundle bundle.json --stamp    # stamp what was reviewed
```

A `blocking` finding left open keeps the bundle not-ready (`REV002`), and a stamp
that no longer matches the content means the review was of an earlier draft
(`REV007`). Re-run the critics whose slice you changed rather than re-stamping
over them.

### Phase 9 - Emit and push

```bash
python scripts/emit.py bundle.json --config refinery.yaml --out out/
```

`emit.py` renders payloads and a push plan, converting the markdown into the
target markup (`wiki` for Jira Server, `adf` for Jira Cloud, `html`, or
plaintext) so a description does not arrive full of literal asterisks. ADF
support covers core nodes only and flattens tables - see `scripts/markup.py`.
**It never makes network calls.**
Show the user `out/preview.md` first. Once approved, copy the bundle to
`.refinery/bundles/<KEY>@<YYYY-MM-DD>.json` - that copy is what a later
re-refinement diffs against. Pushing to the tracker happens only after
explicit approval, via whatever adapter is available in the session (MCP
connector, `jira` CLI, `gh` CLI, REST). Confirm the tracker's actual field names
and issue types at runtime - hardcoded field IDs are `[?]` until probed.

### Re-refinement

Stories get refined more than once. The second pass must update the existing
tree, not build a parallel one:

```bash
python scripts/emit.py bundle.json --config refinery.yaml --previous prior-bundle.json
```

The push plan switches to `mode: update` and separates `creates`, `updates` and
`orphans`. Orphaned subtasks are reported, never auto-deleted - work may already
have happened against them. Keep the prior bundle next to the new one
(`.refinery/bundles/<KEY>@<date>.json`) so this is possible at all.

If a brief's embedded hash no longer matches its content, a human edited it in
the tracker. Show the difference and ask; do not silently overwrite.

## When the input is an epic

Do not decompose an epic into subtasks. Run Phases 1-3 to surface the rules and
questions, then propose a **split into stories**, naming the pattern used
(SPIDR, paths, data, rules - see `references/decomposition.md`). Refine one
story properly rather than all of them shallowly, and say which one you chose
and why.

## Anti-goals

This skill does not: write the implementation; estimate in story points (it
estimates in days-of-work for sizing only); replace the conversation with
stakeholders; refine an item it has detected there is not enough information to
refine; hand over a plan that nothing hostile has read; or claim a story is ready
when questions remain open.

## Reference files

| File | Read when |
|------|-----------|
| `references/intake.md` | Phase 1 - is there enough information; verdicts, statuses, asking well |
| `references/evidence.md` | Phase 2 - multi-repo scanning, manifests, contract detection |
| `references/acceptance-criteria.md` | Phase 3 - example mapping, AC forms, testability |
| `references/decomposition.md` | Phase 5 - profiles, splitting patterns, sizing, ordering |
| `references/agent-brief.md` | Phase 6 - agent brief schema, field-by-field guidance |
| `references/critique.md` | Phase 8 - the critic panel, blindness, findings, rubber-ducking |
| `references/trackers.md` | Phase 0/9 - adapter capabilities, sinks, per-tracker notes |
| `references/antipatterns.md` | Any time output feels thin - refinement smells and fixes |
| `references/rubric.md` | Phase 7 - score the refinement before handing it over |

Read one reference per phase, when you reach that phase. Loading them all up
front costs context you will need for the actual code. The exception is
`antipatterns.md`, which is worth a pass before handover.

## Scripts

All stdlib-only Python 3, no dependencies, no network.

- `scripts/intake.py` - sufficiency detection; exit 0 / 3 / 4 for sufficient / scoutable / insufficient
- `scripts/evidence.py` - `init` | `manifest` | `index` | `scan` | `contracts`
- `scripts/validate.py` - the readiness gate
- `scripts/review.py` - `brief` | `digest` | `check`; sealed critic packets and the
  REV gates' stamp
- `scripts/emit.py` - render payloads and a push plan; `--previous` for updates
- `scripts/markup.py` - markdown to wiki / ADF / HTML / plaintext
- `scripts/selftest.py` - six suites: validator gates, config parsing, markup
  conversion, the pipeline end to end, intake detection, and SKILL.md-to-script
  consistency. Run
  it after editing anything in `scripts/` or `SKILL.md`; it prints the assertion
  count rather than this file claiming one.

## Assets

- `assets/refinery.example.yaml` - annotated config; every key marked `[script]`
  (enforced mechanically) or `[claude]` (read while following this skill)
- `assets/schemas/bundle.schema.json` - bundle contract, for editors and other
  tools; `validate.py` is what actually enforces readiness and checks more than
  a schema can express
- `assets/templates/bundle.skeleton.json` - what you author
- `assets/templates/story.md`, `assets/templates/subtask.md` - the rendered view,
  for sessions that cannot run the scripts
- `assets/examples/example-bundle.json` - a complete, validating two-repo example
- `evals/trigger-eval.json` - queries that should and should not trigger this
  skill, in the format skill-creator's description optimiser expects
- `evals/evals.json` - eight behavioural evals with verifiable expectations, for
  skill-creator's run/grade loop
