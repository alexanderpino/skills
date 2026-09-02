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
| [`terrain-renderer`](terrain-renderer/) | Terrain rendering | Principal terrain-rendering authority to 2026 AAA production standards — every major paradigm end to end: heightfield LOD (clipmaps, CDLOD, CBT), cluster/meshlet virtualized geometry (the Nanite family), UE Landscape/Nanite Landscape, blocky chunked voxel worlds (greedy/binary meshing, voxel AO), smooth voxel isosurfaces (marching cubes, Transvoxel, dual contouring), tiled streaming, terrain materials & virtual texturing, GPU-driven culling, planetary rendering & float-precision doctrine, terrain lighting/shadows, plus the full dynamic surface — water (Gerstner/FFT, flow-mapped rivers, fullscreen-triangle pass, engine-native water systems), snow/wetness/weather state & deformation, auxiliary-map consumption, vegetation/grass & scatter, roads/decals/runtime modification, physics handoff, tool-viewport previews — and the artifact catalogue (cracks, popping, swimming, shimmer). Consumes `terrain-architect`'s generated fields; routes BRDF math to `physically-based-rendering`. |
| [`fan-out`](fan-out/) | Parallel agent orchestration | User-invoked only (`/fan-out <task>`): fans one task out to parallel sub-agents against a single sealed brief, has independent critics judge each candidate against a rubric written before the work started, verifies fixes against the delta only so approved work is never re-reviewed, and folds one result with an evidence trail. |
| [`story-refinery`](story-refinery/) | Backlog refinement | User-invoked only (`/story-refinery`): turn a vague backlog item into an implementation-ready package: multi-repo code evidence with `file:line` citations, locked design decisions, testable acceptance criteria, a condensed human-facing description, a machine-readable agent brief, and subtasks decomposed per a configurable house profile. Tracker-agnostic (Jira, GitHub, GitLab, Linear, Azure DevOps, plain markdown); a `bundle.json` is the single source of truth and every payload is rendered from it. Carries the field's own techniques as gates rather than advice: example mapping and 3 C's, partitions and boundary values, decision tables whose completeness is machine-checked, Cynefin (a complex problem gets a probe, not a plan), impact mapping, premortem risks that need a detection signal, Real Options deferral with an expiry, SPIDR and story mapping, INVEST/SMART — and a final adversarial review in which blind critics, handed sealed packets that withhold the author's reasoning, attack the story and its subtasks before anyone implements them. |
| [`terrain-architect`](terrain-architect/) | Terrain generation | Principal-level terrain generation expertise — the algorithms with verified citations (noise/FBM, tectonic uplift, hydraulic/thermal/glacial/coastal/marine/aeolian erosion, mass wasting, rivers incl. meanders & waterfalls, lakes, karst, desert, periglacial, volcanoes, impact craters, climate & multi-biome worlds, ecosystems, scatter, surface materials, splatmap/albedo/normal/AO synthesis & compositing) and the substrate for building terrain tools (Gaea/World Machine-class, or realtime): typed fields, graph runtimes, caching, preview pyramids, GPU patterns. Also diagnoses wrong terrain (seams, terracing, stalled rivers). |

More skills will be added over time — each one is independent, so you can
install only the ones you need.

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
npx skills add github:alexanderpino/skills/story-refinery
npx skills add github:alexanderpino/skills/terrain-architect
npx skills add github:alexanderpino/skills/terrain-renderer
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
│   └── commands/                      # /fan-out slash command — copy to .claude/commands/
├── story-refinery/                   # unpacked, reviewable skill
│   ├── SKILL.md                       # router + the refinement phases
│   ├── references/                    # load-on-demand deep dives (intake, evidence, AC, example
│   │                                  #   design, risk & options, decomposition, critique…)
│   ├── scripts/                       # bundle tooling (evidence/intake/validate/review/emit/selftest)
│   ├── assets/                        # bundle schema, skeleton, worked example, ticket templates
│   └── evals/                         # trigger + behaviour evals
├── terrain-architect/                # unpacked, reviewable skill
│   ├── SKILL.md                       # router + core mental model
│   └── references/                    # load-on-demand deep dives (noise, erosion, flow, graph runtime, GPU…)
└── terrain-renderer/                 # unpacked, reviewable skill
    ├── SKILL.md                       # router + doctrine (paradigm choice, error budgets, contracts)
    └── references/                    # load-on-demand deep dives (LOD, Nanite-family, voxels, VT, planetary…)
```

## Maintaining

Edit the files under a skill's unpacked directory and commit them. That directory
is the source of truth and `npx skills add` installs straight from it, so there's
no packaging or build step to keep in sync.
