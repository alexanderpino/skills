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
| [`physically-based-rendering`](rendering/) | Graphics / rendering | Expert knowledge of physically based rendering (PBR) and photorealistic image synthesis across offline path tracing and real-time rasterization. |
| [`book-writer`](writing/) | Writing | Write full-length fiction and non-fiction books through a reusable author persona, with the full apparatus of a real book (figures, citations, footnotes, TOC, index) and a research/fact-check workflow. |

More skills will be added over time — each one is independent, so you can
install only the ones you need.

## Installing a skill

The quickest way is the [`skills` CLI](https://www.npmjs.com/package/skills),
which installs a skill straight into the agent that's running:

```bash
# Install a skill by pointing at its directory in this repo
npx skills add github:alexanderpino/skills/game-engine-guru
npx skills add github:alexanderpino/skills/rendering/physically-based-rendering
npx skills add github:alexanderpino/skills/writing/book-writer
```

You can also install from a local checkout:

```bash
git clone https://github.com/alexanderpino/skills.git
npx skills add ./skills/rendering/physically-based-rendering
```

Prefer to do it manually? Point your skill loader — or just your assistant — at
the unpacked skill directory:

- **Claude / Agent Skills:** point a skill loader at the unpacked directory
  (e.g. `rendering/physically-based-rendering/`), which holds the `SKILL.md` and
  its `references/`.
- **Any assistant:** open the skill's `SKILL.md`. It's a router — read it first
  for the core mental model, then open the reference file it points you to.

The unpacked directory is the source of truth. It's plain Markdown, so any coding
assistant — Claude (Sonnet/Opus), Gemini, Codex, etc. — can read the files
directly.

## Repository layout

```
skills/
├── game-engine-guru/                      # unpacked, reviewable skill
│   ├── SKILL.md                           # router + core mental model
│   ├── references/                        # load-on-demand deep dives
│   └── assets/                            # copy-paste scaffolds (C++, C#, Python, HLSL)
├── rendering/
│   └── physically-based-rendering/        # unpacked, reviewable skill
│       ├── SKILL.md                       # router + core mental model
│       └── references/                    # load-on-demand deep dives
└── writing/
    └── book-writer/                       # unpacked, reviewable skill
        ├── SKILL.md                       # router + core mental model
        ├── references/                    # load-on-demand deep dives
        └── templates/                     # scaffolding (LaTeX, scripts)
```

## Maintaining

Edit the files under a skill's unpacked directory and commit them. That directory
is the source of truth and `npx skills add` installs straight from it, so there's
no packaging or build step to keep in sync.
