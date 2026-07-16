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
| [`reasoning-matrix`](reasoning-matrix/) | Reasoning & ideation | Generate genuinely non-obvious insights on hard, open-ended questions by crossing a problem's building blocks against a curated set of reasoning lenses, then filtering the results for novelty *and* validity so what survives is both new and true. For lateral thinking, hypothesis generation, and getting past the obvious answer. |
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
npx skills add github:alexanderpino/skills/reasoning-matrix
npx skills add github:alexanderpino/skills/terrain-architect
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
└── terrain-architect/                # unpacked, reviewable skill
    ├── SKILL.md                       # router + core mental model
    └── references/                    # load-on-demand deep dives (noise, erosion, flow, graph runtime, GPU…)
```

## Maintaining

Edit the files under a skill's unpacked directory and commit them. That directory
is the source of truth and `npx skills add` installs straight from it, so there's
no packaging or build step to keep in sync.
