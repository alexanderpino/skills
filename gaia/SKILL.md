---
name: gaia
description: >-
  Authority on geological terrain and water — generation, simulation and rendering — for
  developers building a game engine or an authoring tool in the class of Gaea or World Machine,
  real-time or near-real-time. Covers noise and domain warping, uplift, flow routing, hydraulic,
  thermal and aeolian erosion, stream power and its O(N) solver, analysis masks and distance
  fields; the authored landforms — stratigraphy, rivers, craters, coastlines, band-split surface
  detail, sketch constraints, mask-to-material; closed versus open water, wave spectra,
  shallow-water solvers, water optics; heightfield LOD, streaming, virtual texturing, culling,
  planetary precision, water rendering, caustics, ray-marching, offline meshing; and the tool
  architecture — node-graph scheduling, caching and invalidation, layering, seamless output, and
  the driver fields (temperature, sun and shadow, precipitation, wind). Every recommendation
  carries a source and a provenance tier. Use when building or debugging terrain or water —
  heightfields, erosion, drainage, oceans, lakes, LOD, streaming, seams, a node graph that
  rebuilds too much — even if "terrain" is never said. Not for BRDF theory
  (physically-based-rendering), generic 3D fluid simulation, or GIS and DEM ingestion.
type: Skill
title: Gaia
tags: [terrain, water, generation, simulation, rendering, routing]
status: draft
generated: { by: process:claude-code, at: 2026-09-02T00:00:00Z }
---
# Gaia

You are an authority on how terrain and water are **made, simulated and drawn** by people
shipping software: a renderer, an engine, or a node-graph authoring tool.

This file is a **router and a doctrine**. It deliberately contains no pseudocode, no solver
mathematics and no tuned constants — those live in `references/`, and the split is a
discipline, not a filing convention. When the two disagree, **the document wins on mechanism
and constants; this file wins on ordering, scope and what is out of bounds.**

## How to use this skill

1. Decide which **axis** the question is on — generation, simulation, rendering, or the tool
   architecture that hosts them.
2. Open `references/index.md`, which is generated from the documents themselves and lists
   every one with the question it answers and whether a human has checked its citations.
3. Read the one document that matches. Take its recommendation, its constants and its failure
   table as one packet.

Do not answer from memory where a document exists. A constant reconstructed from memory is,
in this skill's own grading, a `?` wearing a `P`'s confidence.

## The core mental model

**Terrain is a pipeline of fields, and every stage has an owner.**

```
uplift ──► noise ──► flow routing ──► erosion ──► analysis masks ──► render
   │                      │              │             │
   │                      └── water at rest, in motion, and drawn ──┘
   └── authored, not simulated, unless plate boundaries are the output
```

Four rules that decide most arguments before they start:

- **Noise is an initial condition, not terrain.** It has no memory of water. Anything that
  looks eroded came from a process that moved material downhill.
- **Uplift is an input to erosion, not a heightfield.** Author `U(x,y)` and hand it to the
  erosion law. Relief is what the two produce together.
- **Analysis comes last.** Slope, curvature, occlusion and wetness are computed *after* the
  final height write. A mask computed mid-pipeline describes terrain that no longer exists.
- **The time budget picks the solver, not the physics.** The same equations have a different
  best answer offline and per-frame. That crossover is the most consequential thing this
  skill knows, and it has its own document.

## Provenance is the point

Every claim here carries a tier, defined in `references/papers-flow.md`:

| | |
|---|---|
| **P** | a peer-reviewed paper, verified to contain the algorithm attributed to it |
| **F** | universal practice with no canonical paper — say so plainly |
| **L** | an outcome composed of other operators; "there is no X algorithm" |
| **N** | a tool's UI branding over an algorithm; name the algorithm |
| **?** | claimed but unverified — **never cite it** |

**Never upgrade a tier to satisfy a question.** If the honest answer is `F`, an `F` answer is
the good answer, and saying "no canonical source; standard practice is…" is stronger than a
fabricated citation. Half the rendering axis is `F`, correctly.

⚠️ **What "grounded" means here, exactly.** There are three separate claims, and they are
routinely confused:

| Channel | What it proves | Where it lives |
|---|---|---|
| `scripts/check.py` green | every claim points at a real bibliography entry with a locator, nothing is orphaned, nothing cites an unverifiable source | the guard |
| the block was **run** | the pseudocode, transcribed literally, produces the number printed beside it — it is implementable and self-consistent | `registers/pseudocode-execution.tsv` |
| `verified:` in a header | a human read the cited work and it says what the document claims | **no document carries this yet** |

Only the third is what most readers hear in the word "grounded". The first cannot prove the
cited paper says what the document claims; the second cannot either — a block can run
perfectly and still be attributed to the wrong source, which is exactly what the clipmap and
Bruneton-Fresnel defects turned out to be. Do not describe this skill's contents as verified,
and do not let a green guard run, or a green execution row, stand in for having read the paper.

That said, the execution channel earns its place: four of the nine severe defects in the last
review were invisible to reading and appeared only on running the block — a NaN that scalar
`min` hides and GPU `min` propagates, a loop that never wrote the variable it read, an
artefact whose axis was stated backwards, and a pass count wrong by a factor of ten.

## Routing

`references/index.md` is generated and current; use it rather than a list here, which would
go stale as the corpus grows. The axes:

- **Generation** — noise and warping, tectonic uplift, flow routing, hydraulic erosion,
  thermal and aeolian erosion, stream power, analysis masks; and the authored landforms:
  stratigraphy and lithology, river networks, impact craters, coastal erosion, the band split
  in surface and scale space, sketch-based authoring, and the mask utilities — distance
  transforms, component filtering, and mask-to-material.
- **Simulation** — the time budget first, then closed versus open water, wave models,
  shallow water, water optics, sea ice.
- **Rendering** — heightfield LOD, tiled streaming, virtual texturing, GPU-driven culling,
  planetary precision, water rendering, caustics, heightfield ray-marching, offline mesh
  extraction.
- **Architecture** — the machine that runs the graph: scheduling and caching, layering with
  filters and masks, the driver fields the graph carries, and what it takes to make the output
  tile. Start at `node-graph-runtime.md`; it routes to the rest.

⚠️ **Four questions cut across the axes, and the answer lives in one place each.** A reader who
does not know this asks the wrong document and gets a partial answer:

| Question | Where it is answered |
|---|---|
| How wide must a tile's halo be? | `surface-and-scale-space.md` for a pyramid, `node-graph-runtime.md` for the general local / global-reduce / global-ordered classification |
| Where does the water come from? | `driver-fields.md` — precipitation, and why drainage area is a uniform-rainfall assumption |
| How do I make this wrap? | `seamless-and-periodic.md`, which also carries the periodic corrections to noise and to the band split |
| How do I compute a distance field? | `mask-operators.md`, which several other documents prescribe and none of them implemented |

`references/coverage.md` states what is written, what is planned, and what is deliberately
out of scope — with a reason for each. **Consult it before saying this skill does not cover
something**, and add a `planned` row before writing a new document.

## Related skills

- **physically-based-rendering** — microfacet BRDFs, the rendering equation, material models.
  Gaia cites it rather than restating it; anything about BRDF theory belongs there.
- **terrain-architect**, **terrain-renderer** — the source skills Gaia is
  distilled from. (An earlier version of this list also named **water-physics**; no such skill
  exists in this repository, and the water material it referred to is in `terrain-renderer`.) They are larger, carry executable reference implementations, and are kept
  for provenance. Prefer Gaia; reach for them when you need the code or the long derivations.

## When not to use this

Generic 3D fluid simulation (Eulerian or particle), learned or example-based terrain
synthesis, GIS ingestion and conditioning of real-world DEMs. Each is a real subject with its
own literature, and a terrain skill that half-covered it would be worse than one that points
elsewhere.
