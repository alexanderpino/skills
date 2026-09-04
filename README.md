# skills

A collection of [Agent Skills](https://docs.claude.com/en/docs/agents-and-tools/agent-skills/overview) —
self-contained, load-on-demand expertise packages that any compatible coding
assistant can use. Each skill lives in its own directory as an unpacked,
reviewable tree of plain Markdown — install it straight from the directory, with
no packaging or build step.

## Available skills

| Skill | Area | What it does |
| --- | --- | --- |
| [`game-engine-guru`](game-engine-guru/) | Game engine architecture | Definitive AAA game-engine-development master skill to 2026 production standards: engine architecture, rendering (Adaptive GBuffer, OpenPBR), ECS, job/fiber systems, memory allocators, physics, animation, audio, networking, asset pipelines, editor tooling, profiling, console, and modern C++23/26. Routes material/BRDF math to `physically-based-rendering`. |
| [`physically-based-rendering`](physically-based-rendering/) | Graphics / rendering | Expert knowledge of physically based rendering (PBR) and photorealistic image synthesis across offline path tracing and real-time rasterization. |
| [`book-writer`](book-writer/) | Book Writing | Write full-length fiction and non-fiction books through a reusable author persona, with the full apparatus of a real book (figures, citations, footnotes, TOC, index) and a research/fact-check workflow. |
| [`principal-architect`](principal-architect/) | Architecture & business analysis | Master enterprise/solution/software architecture skill: consult and maintain living architecture docs (PRD/HLD/SD/SAD/AD, ADRs, user stories) as a gate around planning and code changes. Conforms to ISO/IEC/IEEE 42010, 25010, 29148; uses TOGAF 10, ArchiMate 3.2, C4, arc42, with STRIDE/OWASP threat models, FinOps estimates, and Architecture-as-Code CI. |
| [`mission-control`](mission-control/) | Agent orchestration | Command-and-control orchestrator for autonomous multi-agent development pipelines. Runs a continuous plan→build loop: an Architect decomposes goals into a prioritized backlog, Scouts research, then Implementers execute against a file-ownership ledger, gated by mechanical verifiers and code review. |
| [`gauntlet-loop`](gauntlet-loop/) | Quality iteration | Run a **Smart Gauntlet Loop**: the same result the full-grind gauntlet loop would reach — the same bar met, deciding-grade rigour at every decision — delivered faster and cheaper, with the report proving cost against the intake projection. Mantra: *work smarter, not harder*. The engine is Matt Shumer's and stays recognisable: cut the goal into ranked, independently judgeable lanes; per lane, a builder closes one named gap and a *separate* blind critic in fresh context judges the real artifact against a *reachable* external bar, every round guarded by a champion/challenger revert. Around it, the smart layer spends judgement only where a decision lands: blind promotions by default, screening-tier verdicts for routine rounds with deciding-tier verdicts required at lifecycle turns, hash-cached machine gates harvested from critic findings (the suite compounds into the next run), diff-scoped repeat inspections, gate-verified micro-rounds, a softening tripwire on near-empty diffs, and one blind tournament round before parking a stalled lane. An expert-PM layer keeps it honest: intake contract with stops and kill criteria, a quality-price menu with anchored rungs (what n/10 concretely is and costs — 10 is a wall, not a rung; per-dimension targets so a blanket 10/10 is decomposed with the user), a staged build order behind a generated forward plan (usable everywhere before lovable anywhere), an evidenced refusal for provably impossible targets, a hard no-bar-no-run rule (the run requests missing comparison material via `bar-request` instead of inventing a standard; genuinely novel artifacts get a wayfinder-style spec and answer key — one map, one key — frozen as the bar), WIP-limited waves, frozen scope with a backlog, a budget only the user may extend, and a surplus that returns to the user by default. Stdlib-only state tooling; every rule sourced to project-management, LLM-judge, and real-time-rendering authorities. |
| [`reasoning-matrix`](reasoning-matrix/) | Reasoning & ideation | Generate genuinely non-obvious insights on hard, open-ended questions by crossing a problem's building blocks against a curated set of reasoning lenses, then filtering the results for novelty *and* validity so what survives is both new and true. For lateral thinking, hypothesis generation, and getting past the obvious answer. |
| [`fan-out`](fan-out/) | Parallel agent orchestration | User-invoked only (`/fan-out <task>`): fans one task out to parallel sub-agents against a single sealed brief, has independent critics judge each candidate against a rubric written before the work started, verifies fixes against the delta only so approved work is never re-reviewed, and folds one result with an evidence trail. |
| [`story-refinery`](story-refinery/) | Backlog refinement | Invoked by the user (`/story-refinery <item> [--wishes …]`) or by a calling skill that passes its wishes and gets `handback.json` back: turn a vague backlog item into an implementation-ready package: multi-repo code evidence with `file:line` citations, locked design decisions, testable acceptance criteria, a condensed human-facing description, a machine-readable agent brief, and subtasks decomposed per a configurable house profile. Tracker-agnostic (Jira, GitHub, GitLab, Linear, Azure DevOps, plain markdown) and language-agnostic (the item's language is detected and the refinement, the ticket and the summary come back in it); a `bundle.json` is the single source of truth and every payload is rendered from it, including a one-screen summary to talk a team through the plan. Designed to be layered: a team-tailoring skill loads alongside it, owning the house rules and the config, under a stated precedence and a set of invariants no tailoring may relax. Built for a stream of stories, not one at a time — including several in one run, where the evidence is shared and the judgement never is: a later story inherits the earlier one's dossier and re-verifies it rather than re-deriving it, the follow-ups a refinement creates are tracked with observable triggers, and work that does not exist yet is cited as such — pointing at the item that creates it, with the prerequisite link the tracker needs to hold the order. Reads the ticket's own labels first — a `production-issue` refines differently from a feature, a `sev1` is not refined at all — then carries the field's own techniques as gates rather than advice: example mapping and 3 C's, criterion codes that are assigned once and never renumbered, questions asked as a frontier — the whole round at once, each with a recommendation, and nothing that depends on an answer from that round, partitions and boundary values, decision tables whose completeness is machine-checked, Cynefin (a complex problem gets a probe, not a plan), impact mapping, premortem risks that need a detection signal, Real Options deferral with an expiry, SPIDR and story mapping, INVEST/SMART — a durable dossier so the investigation survives the handoff to an implementer — negative results with re-checkable searches, a glossary, preflight commands that catch a stale anchor, and one shared context every subtask agent reads — and a final adversarial review in which blind critics, handed sealed packets that withhold the author's reasoning, attack the story and its subtasks before anyone implements them. |
| [`gaia`](gaia/) | Terrain & water reference | Citation-grounded authority on terrain and water for engine and authoring-tool builders: 37 documents across generation, simulation, rendering and architecture, every claim carrying a source and a provenance tier. See [`gaia/STATE.md`](gaia/STATE.md) for what has and has not been audited. |

More skills will be added over time — each one is independent, so you can
install only the ones you need.

### Superseded

`terrain-architect` and `terrain-renderer` are **retired** and now live under
[`obsolete/`](obsolete/). Both are superseded by [`gaia`](gaia/), which was distilled from them and
grades every source with a provenance tier. They are kept rather than deleted because
`obsolete/terrain-architect/reference-impl/` is executable and Gaia ships no code, because they
carry longer derivations, and because Gaia's registers cite paths inside them. See
[`obsolete/README.md`](obsolete/README.md).

## Installing a skill

The quickest way is the [`skills` CLI](https://www.npmjs.com/package/skills),
which installs a skill straight into the agent that's running:

```bash
# Install a skill by pointing at its directory in this repo
npx skills add github:alexanderpino/skills/game-engine-guru
npx skills add github:alexanderpino/skills/physically-based-rendering
npx skills add github:alexanderpino/skills/book-writer
npx skills add github:alexanderpino/skills/principal-architect
npx skills add github:alexanderpino/skills/mission-control
npx skills add github:alexanderpino/skills/gauntlet-loop
npx skills add github:alexanderpino/skills/reasoning-matrix
npx skills add github:alexanderpino/skills/fan-out
npx skills add github:alexanderpino/skills/gaia
npx skills add github:alexanderpino/skills/story-refinery
```

You can also install from a local checkout:

```bash
git clone https://github.com/alexanderpino/skills.git
npx skills add ./skills/physically-based-rendering
```

Prefer to do it manually? Point your skill loader — or just your assistant — at
the unpacked skill directory:

- **Claude / Agent Skills:** point a skill loader at the unpacked directory
  (e.g. `physically-based-rendering/`), which holds the `SKILL.md` and
  its `references/`.
- **Any assistant:** open the skill's `SKILL.md`. It's a router — read it first
  for the core mental model, then open the reference file it points you to.

The unpacked directory is the source of truth. It's plain Markdown, so any coding
assistant — Claude (Sonnet/Opus), Gemini, Codex, etc. — can read the files
directly.

## Repository layout

```
skills/
├── game-engine-guru/                  # unpacked, reviewable skill
│   ├── SKILL.md                       # router + core mental model
│   ├── references/                    # load-on-demand deep dives
│   └── assets/                        # copy-paste scaffolds (C++, C#, Python, HLSL)
├── physically-based-rendering/        # unpacked, reviewable skill
│   ├── SKILL.md                       # router + core mental model
│   └── references/                    # load-on-demand deep dives
├── book-writer/                       # unpacked, reviewable skill
│   ├── SKILL.md                       # router + core mental model
│   ├── references/                    # load-on-demand deep dives
│   └── templates/                     # scaffolding (LaTeX, scripts)
├── principal-architect/                 # unpacked, reviewable skill
│   ├── SKILL.md                       # router + core mental model
│   ├── references/                    # load-on-demand deep dives
│   └── assets/                        # templates (PRD/HLD/SD/ADR…) + CI tooling
├── reasoning-matrix/                  # unpacked, reviewable skill
│   ├── SKILL.md                       # router + six-phase method
│   └── references/                    # lens catalog + worked example
├── mission-control/                  # unpacked, reviewable skill
│   ├── SKILL.md                       # router + core mental model
│   ├── references/                    # load-on-demand deep dives
│   └── scripts/                       # pipeline state machine CLI
├── gauntlet-loop/                    # unpacked, reviewable skill
│   ├── SKILL.md                       # router + the loop's phases
│   ├── references/                    # load-on-demand deep dives (intake, bars, cost, stops…)
│   │                                  #   incl. subagent briefs (builder, critic, smoother)
│   └── scripts/                       # run-state CLI (init/log-round/gate/status/park/board/extend/report)
├── fan-out/                          # unpacked, reviewable skill
│   ├── SKILL.md                       # router + the loop (slice → brief → build → critique → fold)
│   ├── references/                    # load-on-demand deep dives (incremental review, prompt caching)
│   ├── scripts/                       # run-state CLI (init/plan/seal/check/snapshot/scope/gate/status)
│   └── commands/                      # optional /fan-out wrapper; the skill provides the command itself
├── story-refinery/                   # unpacked, reviewable skill
│   ├── SKILL.md                       # router + the refinement phases
│   ├── references/                    # load-on-demand deep dives (intake, evidence, AC, example
│   │                                  #   design, risk & options, decomposition, critique…)
│   ├── scripts/                       # bundle tooling (triage/evidence/intake/criteria/validate/review/summary/batch/emit/ingest/progress)
│   ├── assets/                        # bundle schema, skeleton, worked example, ticket templates
│   └── evals/                         # trigger + behaviour evals
├── gaia/                             # unpacked, reviewable skill
│   ├── SKILL.md                       # router + provenance tiers
│   ├── STATE.md                       # what has and has not been audited — not part of the skill
│   ├── references/                    # 37 documents + 6 bibliographies
│   ├── registers/                     # what was measured, what went wrong, which guards hold
│   └── scripts/                       # check.py (the guard), index.py, requote.py
└── obsolete/                         # retired, superseded — kept for provenance
    ├── terrain-architect/             # superseded by gaia/ — keeps the executable reference-impl
    └── terrain-renderer/              # superseded by gaia/
```

## Maintaining

Edit the files under a skill's unpacked directory and commit them. That directory
is the source of truth and `npx skills add` installs straight from it, so there's
no packaging or build step to keep in sync.
