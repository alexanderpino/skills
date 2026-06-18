# skills

A collection of [Agent Skills](https://docs.claude.com/en/docs/agents-and-tools/agent-skills/overview) —
self-contained, load-on-demand expertise packages that any compatible coding
assistant can use. Each skill lives in its own directory as both an installable
`.skill` package and an unpacked, reviewable tree of plain Markdown.

## Available skills

| Skill | Area | What it does |
| --- | --- | --- |
| [`physically-based-rendering`](rendering/) | Graphics / rendering | Expert knowledge of physically based rendering (PBR) and photorealistic image synthesis across offline path tracing and real-time rasterization. |
| [`book-writer`](writing/) | Writing | Write full-length fiction and non-fiction books through a reusable author persona, with the full apparatus of a real book (figures, citations, footnotes, TOC, index) and a research/fact-check workflow. |

More skills will be added over time — each one is independent, so you can
install only the ones you need.

## Installing a skill

The quickest way is the [`skills` CLI](https://www.npmjs.com/package/skills),
which installs a skill straight into the agent that's running:

```bash
# Install a skill by pointing at its directory in this repo
npx skills add github:alexanderpino/skills/rendering/physically-based-rendering
npx skills add github:alexanderpino/skills/writing/book-writer
```

You can also install from a local checkout:

```bash
git clone https://github.com/alexanderpino/skills.git
npx skills add ./skills/rendering/physically-based-rendering
```

Prefer to do it manually? Install the `.skill` package directly (it's just a
zip), or point your skill loader at the unpacked skill directory:

- **Claude / Agent Skills:** install the `*.skill` package (e.g.
  `rendering/physically-based-rendering.skill`), or point a skill loader at the
  unpacked directory (e.g. `rendering/physically-based-rendering/`).
- **Any assistant:** open the skill's `SKILL.md`. It's a router — read it first
  for the core mental model, then open the reference file it points you to.

The unpacked tree is the source of truth and is kept in sync with the `.skill`
package. It's plain Markdown, so any coding assistant — Claude (Sonnet/Opus),
Gemini, Codex, etc. — can read the files directly without unzipping.

## Repository layout

```
skills/
├── rendering/
│   ├── physically-based-rendering.skill   # installable package (zip)
│   └── physically-based-rendering/        # same content, unpacked & reviewable
│       ├── SKILL.md                       # router + core mental model
│       └── references/                    # load-on-demand deep dives
└── writing/
    └── book-writer.skill                  # installable package (zip)
```

## Maintaining

Edit the files under a skill's unpacked directory, then repackage:

```bash
python -m scripts.package_skill /path/to/<area>/<skill-name> ./<area>
# (scripts.package_skill ships with the skill-creator skill)
```
