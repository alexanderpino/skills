---
type: Technique
title: Tiled streaming — residency without holes
description: "Streaming a terrain tile pyramid: the residency state machine, the priority function, and the invariant that separates a shippable streamer from a demo."
tags: [rendering, rasterizer, streaming, residency, real-time]
status: draft
generated: { by: process:claude-code, at: 2026-09-02T00:00:00Z }
sources:
  - { id: cozzi2011, tier: F, locator: "the tile-pyramid and out-of-core residency chapters" }
  - { id: ulrich2002, tier: F, locator: "per-chunk geometric error stored with the chunk" }
  - { id: strugar2009, tier: F, locator: "the morph band, applied at tile boundaries" }
  - { id: losasso2004, tier: P, locator: "§3, the ring-shaped resident cut" }
  - { id: directstorage, tier: F, locator: "GPU decompression and queue-depth guidance" }
  - { id: andersson2007, tier: F, locator: "the geometry/material pipeline split" }
---
# Tiled streaming — residency without holes

**Tier: real-time rasteriser.** Once the world outgrows memory, terrain stops being a mesh problem
and becomes a **residency** problem: a quadtree of constant-size tiles, refined against the same
screen-space error currency the LOD controller uses, streamed against hard IO, decode and memory
budgets. This document owns the pyramid and its residency; the LOD scheme that consumes the tiles
is `heightfield-lod.md`.

## Use this

**A quadtree of constant-size tiles, each carrying its own baked geometric error, held resident by
a priority-aware LRU cache under one hard invariant: never show a hole** [cozzi2011].

Three parts, none optional:

1. **Constant texel/vertex count per tile, doubling resolution per level.** Coverage varies, cost
   does not. This is what makes pool allocation, upload scheduling and budget arithmetic
   tractable. Never break it for a special region.
2. **`e(tile)` in the tile header**, computed at bake time [ulrich2002], with `e(child) ≤ e(parent)`
   enforced in the data — refinement oscillates otherwise.
3. **The always-renderable front**: the set of drawn tiles is a *complete* cut through the tree at
   all times, and the streamer pushes that front toward the wanted cut without ever tearing it.

**Crossover — do not build this at all** when the full pyramid fits in the memory budget with
headroom. A resident world needs none of this machinery, and the machinery has a permanent cost
in complexity and in bugs that only appear at speed. Run the budget arithmetic first; it is one
spreadsheet, and it decides whether the rest of this document applies to you.

## The residency state machine

```
unloaded --> requested --> loading --> resident --> renderable <---+
   ^ ^           |            |                         |          |
   | |    cancel |     cancel | (discard                v          | free promotion:
   | +-----------+<-----------+  the completion)    evictable -----+ back into the cut
   |                                                    |
   +----------------------- evict ----------------------+
```

- **requested** — queued, no IO issued. Free to cancel.
- **loading** — IO or decode in flight. Cancellation must be supported: mark the request
  abandoned and discard its completion. If the IO layer cannot cancel, at minimum do not *upload*
  the corpse.
- **resident** — bytes in memory, not yet legal to draw.
- **renderable** — uploaded, derived data ready, seam constraints satisfiable.
- **evictable** — out of the cut, still in memory. This is the cache, and a re-entering tile is a
  free promotion.

**The invariant, stated three ways.** A parent is not released until all four children are
renderable — draw the parent, or draw four children, never three children and a hole, never three
children *and* the parent. On coarsening, the parent must be renderable before the children are
dropped; if it was evicted, re-request it and keep drawing children. The root levels are pinned,
so the guarantee bottoms out: worst case the world is blurry, never absent. Blurry-but-present is
the whole doctrine.

## The priority function, and why FIFO fails

Order the queue by expected visual payoff:

```
priority = sse_projected(tile)                  // error on screen NOW — the dominant term
         * frustumFactor                        // in-frustum 1.0; behind ~0.1, never 0
         * predictFactor(cameraVelocity, tile)  // extrapolate 1-2 s, take the max SSE
```

Never zero the out-of-frustum term: one fast turn then reveals a wall of unloaded tiles.
Recompute priorities every frame for `requested` tiles; never reorder tiles already `loading`.
Age requests so nothing starves — distance-only priority lets a stream of near-tile refinements
starve a whole mid-distance band indefinitely.

**Hysteresis is not a polish item.** Refine at `sse > tau`, coarsen at `sse < tau·h` with
`h ≈ 0.7–0.85`. Without the dead band a camera hovering at the threshold splits and merges the
same tile every frame: sustained IO with a near-stationary camera, and visible flicker. Apply the
same band to the eviction distance.

**What it beats.** *Pure LRU* — evicts the tile immediately behind you, the one you are about to
turn back toward. *Pure priority* — evicts nothing until the crisis. The hybrid evicts the lowest
priority *evictable* tile, breaking ties by last-used frame, and never touches tiles in the cut,
pinned tiles, or tiles mid-upload. *A fixed ring cut* [losasso2004] — clipmap-shaped residency is
the right *shape* for the resident set and the wrong *mechanism* for choosing it, because it
cannot spend more on the ridge in front of you than on the flat behind. *Zone/cell load-on-cross*
— the old open-world pattern; it hitches at the boundary by construction and has no notion of
partial detail.

## The frame must never wait on the disk

- **Async IO with real queue depth.** NVMe wants dozens of concurrent requests. A streamer with
  one outstanding read runs at HDD-era throughput on NVMe hardware [directstorage].
- **GPU decompression** — compressed tiles go disk → GPU memory and inflate there, bypassing the
  CPU copy-and-inflate path [directstorage]. Keep the CPU fallback and treat both as one logical
  stage with two executors.
- **One blob per tile for payloads that share a lifecycle.** One IO request, one decode. Five
  small files per tile multiplies seek and request overhead by five for nothing.
- **A per-frame upload byte budget** through a persistent staging ring — 8–32 MB/frame at 60 Hz is
  the usual band, tuned per platform. A tile whose upload does not fit this frame stays
  `resident`. The canonical hitch is 200 tiles finishing decode in one frame and all uploading
  because "the data is ready". Split oversized payloads across frames.
- **No derived-data work on the render thread.** Mip generation and BCn encoding happen in the
  worker or compute budget, before the tile is declared renderable.

**Which payloads share the tile's lifecycle is the load-bearing decision.** Height, baked normals,
watermask and holes ride with the geometry. Material weights usually graduate to their own
residency system with an independently sized cache [andersson2007] — see
`virtual-texturing.md`. **Collision runs its own pyramid and its own guarantee**, and coupling it
to render residency is a bug: render tiles may be blurry, collision tiles may not be absent. All
collision within radius R of a physics-active actor must be resident *before* the actor is
allowed there, R derived from max actor speed × worst-case load latency. Gameplay blocks; it does
not fall through the world.

## Seams, and the apron the renderer cannot fake

Tile boundaries re-create the crack problem at pyramid scale, and the contracts are those of
`heightfield-lod.md` restated per tile: adjacent same-level tiles must generate bit-identical edge
vertices, cross-level edges constrain the fine tile to the coarse neighbour's edge function, and
morph regions over the outer 10–25% of a tile remove the *pop* at replacement as well as the crack
[strugar2009]. Morphing needs the parent's height at the child's vertices, which is one more
reason parents stay resident.

⚠️ **Attribute continuity is not a renderer problem.** Normals, AO and material weights baked
per tile diverge at edges unless they were baked over tile + apron with the apron discarded. If
tiles arrive apron-less, the lighting seam cannot be fixed at runtime — reject the data and fix
the bake. Blurring the seam hides it at one distance and reveals it at every other.

## How this fails, and what it looks like

| Symptom | Mechanism | Fix |
|---|---|---|
| Frame hitches while moving | Synchronous IO or decode on a critical thread, or a whole tile uploaded in one frame | Async IO; slice uploads against a per-frame byte budget; assert worst-frame bytes |
| The world visibly assembles after a teleport | Cold start: everything requested at once at equal priority | Prioritise by projected error; prefetch on teleport intent; budget the storm |
| Tiles flicker between two levels; sustained IO with a still camera | No hysteresis band between refine and coarsen | Separate the thresholds; add a minimum-resident time |
| A hole, or the sky, where terrain should be | Parent released before all four children were renderable, or children dropped before a re-requested parent arrived | The always-renderable invariant, enforced in both directions |
| Double-drawn, z-fighting terrain at one tile | Parent and children both drawn during a transition | Refinement is atomic per parent |
| Distant tiles never sharpen | Requests dropped silently — queue overflow, or IDs recycled by the streamer | Count every drop; key requests by stable tile ID |
| A visible seam in lighting exactly on tile edges | Per-tile bakes ran without a neighbour apron | Re-bake with an apron at least the kernel radius; do not blur at runtime |
| Resident set grows through a long flight and never plateaus | Eviction never reaches the cache, or evictable tiles are pinned by a stale reference | Plot the resident-set curve on a soak; it must plateau |
| Cross-tile seams appear only after a patch | Old baked tiles mixed with new ones | Version every tile blob by a content hash of source data plus bake parameters; reject mixed versions per region |
| Players fall through the world at speed | Collision residency coupled to render residency, or R sized without the latency term | Separate pyramid, guaranteed ring, R from max speed × worst-case latency |
| Everything works at walking speed | The streamer was tuned only at walking speed | Verify at max traversal speed and by teleporting into a cold region |
