# The writer's library — persistent world, character, and theme storage

## What it is

The library is a folder at `~/library/` (configurable via `LIBRARY_ROOT` environment variable) that holds reusable creative material — worlds, characters, themes — outside any single project. Material can be reused across projects and evolves as projects build on it.

This is structurally separate from a project's `notes/` folder. Notes are project-specific. Library items are *canonical* — the writer's record of "this is the world / character / theme as I understand it now."

## Folder structure

```
~/library/
├── worlds/
│   └── <slug>/
│       ├── world.json          # metadata sidecar
│       ├── world.md            # narrative description
│       ├── snapshots/          # historical states
│       └── changelog.md
├── characters/
│   └── <slug>/
│       ├── character.json
│       ├── character.md
│       ├── snapshots/
│       └── changelog.md
└── themes/
    └── <slug>/
        ├── theme.md
        └── used-in.json (optional)
```

Slugs are kebab-case lowercase: `iron-galaxy`, `elara-hrafnir`, `competing-goods`.

## Metadata structure

Each world/character has JSON sidecar:

```json
{
  "id": "iron-galaxy",
  "name": "Iron Galaxy",
  "type": "world",
  "created": "2026-04-25",
  "last_updated": "2026-04-25",
  "current_state_summary": "Brief summary of where this stands now.",
  "snapshots": [
    {"id": "pre-iron-fleet", "date": "2026-04-25",
     "label": "Initial state", "file": "snapshots/2026-04-25_pre-iron-fleet.md"}
  ],
  "used_in": [
    {"project": "iron-fleet", "first_used": "2026-04-25",
     "as_of_snapshot": "pre-iron-fleet"}
  ],
  "tags": ["sci-fi", "space-opera", "star-wars-eu"]
}
```

Themes are simpler — just `theme.md` plus optional `used-in.json` — because they don't accumulate state.

## The library_manager.py script

`templates/library_manager.py` handles all library operations. Intentionally simple — it manages metadata sidecars and snapshot files. Content lives in markdown that Claude or the user edits directly.

```
list <type>                           list all items of a type
show <type> <slug>                    show metadata
create <type> <slug> [name] [summary] create new item
snapshot <type> <slug> <label>        snapshot current state
log <type> <slug>                     show changelog
link <type> <slug> <project> [snap]   record project uses this item
state <type> <slug>                   print current_state_summary
```

Set `LIBRARY_ROOT` to use a non-default location.

## Three modes for project ↔ library interaction

### 1. Reference mode

Project does not copy. `notes/world.md` is a thin pointer:

```
This project uses the canonical library world `iron-galaxy`.
See ~/library/worlds/iron-galaxy/world.md.
```

Best for: tightly bound multi-volume series.
Risk: changes to canonical during writing immediately affect reading.

### 2. Import-with-fork (default)

At project start, library narrative is copied into `notes/world.md`. A `notes/library_link.json` records the source:

```json
{
  "type": "worlds",
  "slug": "iron-galaxy",
  "imported_from_snapshot": "pre-iron-fleet",
  "imported_at": "2026-04-25"
}
```

Project freely modifies its local copy. Canonical unaffected during writing. At project completion, three options:

- **Adopt fully** — project version becomes new canonical, previous state snapshotted
- **Adopt selectively** — walk through diff, choose which changes to incorporate
- **Keep separate** — canonical stays; project version preserved as snapshot named after the project

Best for: most projects.

### 3. Inspiration only

Claude reads library item at start, uses as inspiration. No formal link.

Best for: same world but different time period, same archetype but different character.

## When to create library items

Create when:
- The world will be revisited (series, shared universe, recurring settings)
- A character might appear in another book
- A theme is a long-term preoccupation

Don't create when:
- Genuinely one-off material
- User explicitly wants project-only
- The "world" is so plot-specific that abstraction would damage it

When in doubt, ask the user.

## Snapshots

A snapshot is a frozen-in-time copy of an item's narrative file. Three purposes:

1. **Historical record** — "What did this character look like before book 3?"
2. **Project anchoring** — when a project imports, the snapshot at import is the reference. Later canonical changes don't retroactively change what the project was based on.
3. **Recovery** — rollback points if evolution goes wrong.

Recommended snapshot points:
- Before any major project that imports the item: `pre-<project-slug>`
- At project completion if changes are adopted: `post-<project-slug>`
- After significant standalone revision: short description

## Changelog

Each item has `changelog.md`. Entries added by:
- The script (on creation, on snapshot)
- Claude during project-completion adoption (high-level summary of what changed and why)
- The user manually (canonical edits outside projects)

Format:

```markdown
## 2026-08-15 — adopted changes from project iron-fleet

The clans' political organisation was extended to include the Allthing as
a formal seven-year assembly. This is now canonical. The Yuuzhan Vong
sub-plot is project-specific and was NOT adopted.
```

Changelog entries are *summaries*, not raw diffs. Diffs are recoverable from snapshots.

## What the skill does during Phase 1

First question of intake:

> "Do you already have material for this book? I can begin from:
> - **Existing material** — an outline, notes, fragments, character sketches
> - **Library items** — a world or characters you've worked with before
> - **From scratch** — an idea, a feeling, a sentence"

Based on answer:

- **Existing material** — user uploads or pastes. Claude reads, structures, asks questions to fill gaps. Phase 2 starts with substantial material.
- **Library items** — Claude runs `library_manager.py list worlds` and `list characters`. Presents relevant items. User selects to import. Claude calls `snapshot` and `link`. Phase 2 starts from imported material.
- **From scratch** — normal flow. At end of Phase 2, Claude asks whether any worldbuilding or characters should be promoted to library for future reuse.

## What the skill does at project completion

After Phase 5 (manuscript finishing), before Phase 6 (assembly):

1. Review which library items were imported (from `notes/library_link.json` files)
2. For each, generate a high-level diff: substantive ways project version differs from canonical
3. Ask user: adopt fully, adopt selectively, or keep separate
4. For adopted: copy project version (or selected parts) over canonical, snapshot previous state as `pre-<project>`, add changelog entry
5. For kept-separate: snapshot project version into library as `from-<project>`, add changelog entry noting parallel-rather-than-canonical

Makes evolution explicit and reversible.

## Migration for existing projects

For projects that pre-date the library (like *De IJzeren Vloot*):

1. Identify which `notes/` files are reusable
2. For each, ask user: should this become a library item?
3. For yes: `library_manager.py create ...`, copy narrative into library item, snapshot as initial state, link project to library item
4. Optionally update project's `notes/` to use reference or import-with-fork mode

One-time per pre-existing project.

## What the library is not

- Not a database with queries. If you want "all red-haired characters" you read the markdown.
- Not version control with branches. Linear: snapshots are points in a single timeline per item. To fork, create a new item with a different slug.
- Not a publishing system. The writer's working record.
- Not synchronised across users or machines. Local.

## Why this design rather than something fancier

A more sophisticated system would have database storage, automatic diffing, branching, change-detection. Real features, real complexity. The library is for *one writer over many years*. Markdown + JSON + small script is enough. Writer can read and edit files directly; no tool dependence.

If the library grows to hundreds of items and lookup becomes messy, the system can be replaced *without losing data* — markdown migrates anywhere.
