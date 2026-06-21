# Slice methodology — finishing coherent units before moving on

## What it is

A *slice* is a coherent, self-contained unit of deliverable work that, once complete, is independently useful. The slice methodology is the discipline of completing one slice fully before starting the next, rather than working all components of a project in parallel and finishing them all at the end.

The methodology has a single rule: **at any point during the project, the work completed should be useful on its own.**

## Why it matters

The default failure mode of multi-deliverable projects is the all-fronts-half-finished trap. The user starts a book, decides on a theme, drafts the first chapter, then notices the world-building needs more work, then starts a second chapter, then realises the persona needs adjustment, then drafts a third chapter with the adjusted persona but old world-building... after a long session, every component is partially advanced and nothing is finished. The work feels productive while it happens and unsatisfying when reviewed.

The slice methodology prevents this by enforcing a different ordering: one coherent unit at a time, fully finished before the next starts. The cost is that some components stay completely unwritten while others are complete; the gain is that the completed work is genuinely usable.

## When it applies

Slice methodology applies to any project that produces multiple deliverables which can be sequenced into coherent groupings. Common examples:

- **Technical documentation projects** — a slice is one tutorial plus the how-tos and reference pages it touches plus the explanations it invokes. (See `technical-documentation.md` for the technical-doc-specific application.)
- **Multi-volume narrative works** — a trilogy or series, where each volume is its own slice.
- **Multi-language projects** — when content is being prepared in multiple languages, one language at a time, fully finished, before moving to the next.
- **Reference works with an apparatus** — a textbook with body chapters plus a glossary plus an index plus a bibliography. Each appendix can be its own slice rather than parallel-progressing.
- **Book series with a shared world** — write one book completely, then the next, rather than drafting all books in parallel.

It does **not** apply to:

- **Single-volume narrative works** — a novel is one slice. Working on it linearly chapter-by-chapter is the natural order, but that's not slicing; that's just sequential drafting within one slice.
- **Projects with strong cross-dependencies that prevent finishing any unit in isolation** — though these are rarer than they appear. Often what looks like a cross-dependency is solvable by sequencing the slices appropriately.

## How to identify slices

A slice has three properties:

1. **It is coherent** — the work within the slice belongs together. A reader who consumes only this slice gets a complete experience of something, not a partial experience of everything.
2. **It is self-contained** — the slice can be completed without depending on work that belongs to a future slice. (It may depend on work in earlier slices; that is what completed earlier slices are for.)
3. **It is independently useful** — once finished, the slice has value on its own. It does not require the rest of the project to complete before it earns its keep.

Sometimes the natural slices are obvious: the volumes of a multi-volume work, the languages of a multi-language project. Sometimes the user must construct slices deliberately. For technical documentation, slices are constructed around use-cases (the "Hello world" slice, the "save and load" slice). For a textbook, slices might be by topic area. For a research book, slices might be by argument-strand.

## Slice ordering

Once slices are identified, they must be ordered. Two principles guide the order:

- **Foundation first.** Slices that other slices depend on come earlier. In technical documentation, the "Hello world" tutorial-and-reference slice typically comes first because subsequent how-tos assume tutorial knowledge. In a multi-volume series with shared world-building, the volume that establishes the world goes first.
- **Highest value first within constraints.** When multiple slices are independent, do the one whose completion provides the most value first. For a documentation project, that is usually the slice that covers the most common use case. For a series, it is usually the volume the user most wants to read.

Slice ordering is not the same as content ordering within a slice. Inside a slice, work may proceed in any sensible internal order; between slices, the order is fixed at planning time and not deviated from without good reason.

## Slice completion criteria

A slice is complete when:

- All deliverables within it are at the quality level the project requires
- All cross-references within the slice resolve
- All cross-references from the slice to earlier slices resolve
- Cross-references from the slice to *later* slices are explicitly marked as such (for documentation, this means broken-link-to-future-page is acceptable; for narrative, this means foreshadowing references things that will exist)

A slice is **not** complete just because the user is tired of working on it. The methodology depends on slices actually finishing. A half-finished slice that gets abandoned because the next one looked more interesting is the failure mode the methodology exists to prevent.

## Slice tracking

For projects with more than three slices, maintain a `slices.md` file in the project root with:

- Slice list, ordered
- Per-slice: planned deliverables, current status (planned / in-progress / complete), word count or page count if relevant
- Cross-slice dependencies noted
- The current slice in progress, marked clearly

The file gets updated at the end of every working session. At the start of every session, it is the first thing read after `project.json`.

## When to apply this within the skill

For any project at intake (Phase 1), if the project naturally divides into multiple deliverables (multi-volume, multi-quadrant documentation, multi-language, large reference work with apparatus), propose slice methodology explicitly:

> "This project has [N] natural slices: [list]. I'd suggest we work through them in [proposed order], finishing each before moving to the next. That way you have something usable at every milestone instead of a partial mass of work at the end. Sound good?"

If the user agrees, create `slices.md` as part of Phase 2 (Preparation). If the user prefers parallel work, accept that — but warn that the all-fronts-half-finished trap is the default outcome of parallel work, and help is available to switch to slice methodology mid-project if the trap starts to bite.

For single-deliverable projects (one novel, one short book), slice methodology does not apply. Sequential drafting within the single deliverable is the appropriate approach.
