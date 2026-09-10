---
type: Technique
title: Tiled streaming — residency without holes
description: "Streaming a terrain tile pyramid: the residency state machine, the priority function, and the invariant that separates a shippable streamer from a demo."
tags: [rendering, rasterizer, streaming, residency, real-time]
status: draft
generated: { by: process:claude-code, at: 2026-09-02T00:00:00Z }
sources:
  - { id: cozzi2011, tier: F, locator: "ch. 12 Massive-Terrain Rendering — §12.1 level of detail, §12.2 preprocessing, §12.3 out-of-core rendering, §12.4 culling" }
  - { id: ulrich2002, tier: F, locator: "per-chunk geometric error stored with the chunk" }
  - { id: strugar2009, tier: F, locator: "the LOD distances and morph areas section — the morph area covers the last 15 to 30 per cent of every LOD range. The whitepaper section headings are unnumbered" }
  - { id: losasso2004, tier: P, locator: "§3 Clipmap regions — the render region is the hollowed frame between active_region of l and of l+1" }
  - { id: directstorage, tier: F, locator: "Queue depth and Best Practices → Queue management in the GDK DirectStorage overview, which is the Xbox Series X|S page — submit every outstanding request, and size the queue at four times the per-frame request count. That page's Decompression section is console fixed-function hardware and never names GDeflate: it does NOT support the GPU-inflate claim in the body, which is Windows DirectStorage 1.1+ and needs a locator of its own that nobody has resolved here" }
  - { id: andersson2007, tier: F, locator: "§5.2.4 Static Sparse Mask Textures — material masks in their own sparse quadtree with an indirection texture and atlas — against §5.4.1 Geometry LOD" }
---
# Tiled streaming — residency without holes

**Tier: real-time rasteriser.** Once the world outgrows memory, terrain stops being a mesh problem
and becomes a **residency** problem: a quadtree of constant-size tiles, refined against the same
screen-space error currency the LOD controller uses, streamed against hard IO, decode and memory
budgets. This document owns the pyramid and its residency; the LOD scheme that consumes the tiles
is `heightfield-lod.md`.

## Use this

**A quadtree of constant-size tiles, each carrying its own baked geometric error — copied into a
small always-resident node index, because the priority function has to read it before the tile
exists in memory — held resident by a priority-aware LRU cache under one hard invariant: never
show a hole.** No peer-reviewed paper defines this architecture; standard practice is the
treatment in *3D Engine Design for Virtual Globes* [cozzi2011] — a textbook, and `F` for that
reason however canonical it is — converging with what shipped globe and open-world streamers
arrived at independently.

Four parts, none optional:

1. **Constant texel/vertex count per tile, doubling resolution per level.** Coverage varies, cost
   does not. This is what makes pool allocation, upload scheduling and budget arithmetic
   tractable. Never break it for a special region.
2. **`e(tile)` baked per tile** [ulrich2002], with `e(child) ≤ e(parent)` enforced in the data.
   A violation does *not* make refinement oscillate: for a single node `sse > tau` and
   `sse < tau·h` are mutually exclusive whatever the baked numbers say, and the two thresholds of
   the dead band below sit a factor `1/h` apart in camera distance — a ratio `e(child)` never
   enters. What a violation costs is the
   *bound*. The cut comes to rest at a node that passes `tau` while a descendant exceeds it, so
   the error the frame is drawing is no longer the error the controller measured, and that node
   jumps several levels the moment it does split.
3. **`e` and the tile's vertical extent in a resident node index**, not only in the tile header.
   The index is the quadtree itself — one small record per node, loaded and pinned before
   streaming starts; the XY footprint follows from the node address under part 1, so it need not
   be stored. Without it the priority function below is unevaluable for exactly the tiles it has
   to order: a `requested` tile has issued no IO, so its header is not in memory, and the
   cold-start row in the failure table prescribes ordering by projected error in the one state
   where nothing but the pinned roots is resident. Substitute a constant for the missing term and
   you get the equal-priority storm that row names; substitute distance and you get the starved
   mid-distance band the priority section names. Neither is a fix — carry the index.
4. **The always-renderable front**: the set of drawn tiles is a *complete* cut through the tree at
   all times, and the streamer pushes that front toward the wanted cut without ever tearing it.

**Crossover — do not build this at all** when the full pyramid fits in the memory budget with
headroom. A resident world needs none of this machinery, and the machinery has a permanent cost
in complexity and in bugs that only appear at speed. Run the budget arithmetic first, over the
drawn cut *plus its parent level* — morphing reads parent height, so the parents are resident
whether or not you budgeted them. It is one spreadsheet, and it decides whether the rest of this
document applies to you.

## The residency state machine

```
unloaded --> requested --> loading --> resident --> renderable <---+
   ^ ^           |            |            |            |          |
   | |    cancel |     cancel | discard    |            v          | free promotion:
   | +-----------+<-----------+<-----------+        evictable -----+ back into the cut
   |                                                    |
   +----------------------- evict ----------------------+
```

- **requested** — queued, no IO issued. Free to cancel.
- **loading** — IO or decode in flight. Cancellation must be supported: mark the request
  abandoned and discard its completion. If the IO layer cannot cancel, at minimum do not *upload*
  the corpse.
- **resident** — bytes in memory, not yet legal to draw. **A tile whose want expired before its
  upload ran is discarded from here, not completed.** Without that exit, an exhausted upload
  budget (below) parks it in `resident` until it has been uploaded and built anyway — one
  mechanism behind the resident set that never plateaus. Demoting it to `evictable` instead is
  the wrong edge: that state's whole property is that re-entry is a *free* promotion, and a tile
  that was never uploaded cannot deliver one.
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
sse_now  = sse_projected(tile, camera)           // error on screen now, in px
sse_pred = sse_projected(tile, extrapolate(camera, 1-2 s))   // same tile, predicted camera

priority = max(sse_now, sse_pred)                // the error term — dominant by construction
         * frustumFactor                         // in-frustum 1.0; behind ~0.1, never 0
```

Prediction is a **max over the window, not a third multiplier**. Fold it in as a factor and the
queue no longer obeys the rule the factor is named for: a tile at 2 px now that reaches 12 px
inside the window loses to a steady 5 px tile, 2×12 = 24 against 5×5 = 25, while the max ranks
the closing tile first. Both `sse_projected` and `extrapolate` are ordinary functions of a camera
and a tile; there is no third term left undefined.

Never zero the out-of-frustum term: one fast turn then reveals a wall of unloaded tiles.
Recompute priorities every frame for `requested` tiles; never reorder tiles already `loading`.
Age requests so nothing starves — distance-only priority lets a stream of near-tile refinements
starve a whole mid-distance band indefinitely.

**Hysteresis is not a polish item.** Refine at `sse > tau`, coarsen at `sse < tau·h` with
`h ≈ 0.7–0.85`. Without the dead band a camera hovering at the threshold splits and merges the
same tile every frame: sustained IO with a near-stationary camera, and visible flicker. Apply the
same band to the eviction distance.

**What it beats.** *Pure LRU* — recency is a poor proxy for future value. It **protects**
everything you have just driven past, because that is exactly what carries the newest use stamp,
and it is blind to the high-error tile ahead: it has no notion of projected error or camera
velocity, so the only thing it can order by is the past. *Pure priority* — evicts nothing until
the crisis. The hybrid evicts the lowest priority *evictable* tile, breaking ties by last-used
frame, and never touches tiles in the cut, **the parents of tiles in the cut**, pinned tiles, or
tiles mid-upload. That parent clause is load-bearing and easy to omit: morphing reads the
parent's height (see the seams section), and priority alone will not hold the parent for you.
Monotonicity gives `e(parent) ≥ e(child)`, and at essentially the same distance that makes
`sse(parent) ≥ sse(child) > tau·h` — so a parent does sit near the top of the evictable set. That
buys ordering, not a guarantee: it means only that the hybrid reaches the parent once the rest of
the evictable set is drained, and the two regimes that drain it are the two the failure table
below already names, a cold start or teleport and sustained max traversal speed. *A fixed ring
cut*
[losasso2004] — clipmap-shaped residency is the right *shape* for the resident set and the wrong
*mechanism* for choosing it, because it cannot spend more on the ridge in front of you than on
the flat behind. *Zone/cell load-on-cross* — the old open-world pattern; it hitches at the
boundary by construction and has no notion of partial detail.

## The frame must never wait on the disk

- **Async IO with real queue depth.** NVMe wants dozens of concurrent requests, and dozens is the
  floor, not the target: a streamer with one outstanding read runs at HDD-era throughput on NVMe
  hardware. [directstorage] retires the old balancing act outright — the 12–16 requests in flight
  it used to recommend were for a rotational drive, and the rule now is to submit *every*
  outstanding request and let the queue absorb them, sizing that queue at a capacity of at least
  four times the largest number of requests any one frame creates. Capacity is not the same
  quantity as in-flight depth; size the ring by the requests you create, not by the ones you hope
  are outstanding.
- **GPU decompression** — compressed tiles go disk → GPU memory and inflate there, bypassing the
  CPU copy-and-inflate path. The platforms reach that by different routes: on Windows it is
  DirectStorage 1.1+ inflating GDeflate on compute, on console it is fixed-function decompression
  hardware, and they are not one path. ⚠️ The [directstorage] locator this document carries is
  the GDK console overview, which documents the fixed-function path only and never names
  GDeflate — it does **not** support the GPU-inflate claim in this bullet, which needs the Windows
  DirectStorage documentation cited in its own right. Treat that citation as owing a source until
  someone resolves it. Keep the CPU fallback either way, and treat all of these as one logical
  stage with different executors.
- **One blob per tile for payloads that share a lifecycle.** One IO request, one decode. Five
  small files per tile multiplies seek and request overhead by five for nothing. The node index of
  part 3 is the deliberate exception: it is resident before any blob is, precisely because it must
  be readable for tiles whose blob has not been requested.
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
morph regions over the outer band of a tile remove the *pop* at replacement as well as the crack —
the CDLOD whitepaper sizes that band at the last 15–30% of each LOD range [strugar2009]. Morphing
needs the parent's height at the child's vertices, which is why parents are *excluded from
eviction* above rather than merely favoured by priority. Budget for them: refinement is atomic per
parent, so the cut is whole sibling quads and its distinct parents number a quarter of it — at the
constant per-tile size of part 1, at most **+25% of drawn bytes**. Steady state is well under that
bound, since only tiles inside their morph band need the parent this frame, but size for the
bound. `heightfield-lod.md` prices the resident set that follows; take its numbers rather than
deriving a second set here.

⚠️ **Attribute continuity is not a renderer problem.** Normals, AO and material weights baked
per tile diverge at edges unless they were baked over tile + apron with the apron discarded. If
tiles arrive apron-less, the lighting seam cannot be fixed at runtime — reject the data and fix
the bake. Blurring the seam hides it at one distance and reveals it at every other.

⚠️ **The line that survives a correct apron is a different defect, and the derivative is not it.**
The drawn set is a *complete cut* through the tree, so neighbouring tiles routinely sit one level
apart, and the two sides then hand **different inputs** — a different texel size, a different
detail-UV scale, a different resident mip — to their own, correct screen-space derivatives. Under a
rasteriser two tiles are two primitives, so no shading quad ever spans the boundary and no
derivative is taken across it; "fixing the derivative" changes nothing, and neither does re-baking
an apron that was already right. `shader-craft.md` carries the specification text, the full list of
the differing inputs, the one shading path where the no-quad-spans-it argument does not hold, and
the fix: make the LOD-dependent inputs agree across the boundary, or take the gradients from a
quantity that does not depend on which level a tile is at. `heightfield-lod.md` states the same
defect along its morph bands.

## How this fails, and what it looks like

| Symptom | Mechanism | Fix |
|---|---|---|
| Frame hitches while moving | Synchronous IO or decode on a critical thread, or a whole tile uploaded in one frame | Async IO; slice uploads against a per-frame byte budget; assert worst-frame bytes |
| The world visibly assembles after a teleport | Cold start: everything requested at once at equal priority | Prioritise by projected error — read `e` from the resident node index, since no tile header is in memory yet; prefetch on teleport intent; budget the storm |
| Tiles flicker between two levels; sustained IO with a still camera | No hysteresis band between refine and coarsen | Separate the thresholds; add a minimum-resident time |
| A hole, or the sky, where terrain should be | Parent released before all four children were renderable, or children dropped before a re-requested parent arrived | The always-renderable invariant, enforced in both directions |
| Double-drawn, z-fighting terrain at one tile | Parent and children both drawn during a transition | Refinement is atomic per parent |
| Distant tiles never sharpen | Requests dropped silently — queue overflow, or IDs recycled by the streamer | Count every drop; size the queue at 4× the per-frame request count so it cannot overflow under its own submissions; key requests by stable tile ID |
| A pop, or a crack, along a morph band after a long flight or a teleport | The parent of a cut tile was evicted, so morphing has no parent height to blend toward | Exclude parents of cut tiles from eviction, and budget the parent level with the cut |
| A visible seam in lighting exactly on tile edges | Per-tile bakes ran without a neighbour apron — or the apron is correct, and the two sides sit at different pyramid levels feeding different inputs to their own correct derivatives | Re-bake with an apron at least the kernel radius; do not blur at runtime. If a correct apron does not move it, it is the cross-level filtering discontinuity and not the bake — see the seams section |
| Resident set grows through a long flight and never plateaus | Eviction never reaches the cache; evictable tiles are pinned by a stale reference; or `resident` tiles whose want expired have no discard edge, so they hold their bytes until the upload budget finally reaches them | Plot the resident-set curve on a soak; it must plateau. Give `resident` an exit |
| Cross-tile seams appear only after a patch | Old baked tiles mixed with new ones | Version every tile blob by a content hash of source data plus bake parameters; reject mixed versions per region |
| Players fall through the world at speed | Collision residency coupled to render residency, or R sized without the latency term | Separate pyramid, guaranteed ring, R from max speed × worst-case latency |
| Everything works at walking speed | The streamer was tuned only at walking speed | Verify at max traversal speed and by teleporting into a cold region |
