# Tiled Worlds & Streaming

Once the world outgrows what fits in memory, the terrain becomes a **tile pyramid with a residency
problem**: a quadtree of fixed-size tiles, each carrying a geometric error, refined against the same
screen-space-error currency as `01`, and streamed against hard IO, decode, and memory budgets. This
chapter owns the pyramid, the per-tile residency state machine, the IO/decompression path, eviction
math, cross-tile seams, far-field representation, and the split between render streaming and
collision streaming. The tiles themselves — contents, aprons, formats — are produced under the
generation side's output contract (terrain-architect `08`); this chapter consumes that contract.

Contents: [The tile pyramid](#the-tile-pyramid) ·
[Residency: the per-tile state machine](#residency-the-per-tile-state-machine) ·
[IO, decompression, and upload budgets](#io-decompression-and-upload-budgets) ·
[Eviction and the memory budget](#eviction-and-the-memory-budget) ·
[Seams between tiles](#seams-between-tiles) · [HLOD and the far world](#hlod-and-the-far-world) ·
[Collision and gameplay streaming](#collision-and-gameplay-streaming) ·
[Pitfalls](#pitfalls) · [Sources & provenance](#sources--provenance)

## The tile pyramid

The structure is a quadtree (per planet face when spherical — `09`): the root tile covers the whole
world at coarse resolution; each child covers a quarter of its parent at twice the linear
resolution. Every tile stores the **same texel/vertex count** — constant cost per tile, resolution
doubles per level. This "constant-size tile, variable coverage" invariant is what makes budgets,
pool allocation, and upload scheduling tractable; never break it for a special region.

**Geometric error and refinement.** Each tile carries `e(tile)` — the maximum world-space deviation
(metres) of its simplified content from the finest data, computed at bake time by the generation
side and stored in the tile header. At runtime, project it:

```
sse(tile) = e(tile) / d(tile) * screenHeightPx / (2 * tan(vFov / 2))
refine when sse(tile) > tau        // tau in pixels, same currency as `01`
```

`d(tile)` is the distance from camera to the closest point of the tile's bounding volume (never the
centre — a huge coarse tile whose corner touches the camera has d ≈ 0). This is the same SSE the
CDLOD/geometry-clipmap discussion in `01` uses; a world must run **one** error currency or its LOD
seams become unexplainable. Monotonicity contract: `e(child) ≤ e(parent)` must hold in the baked
data, or refinement can oscillate.

**Replacement vs additive refinement.** Two disciplines exist; pick one per pipeline:

| Scheme | What refinement does | Use when | Cost |
|---|---|---|---|
| Replacement | 4 children *replace* the parent's draw | Heightfield terrain, opaque meshes | Must hold parent until all 4 children renderable |
| Additive | Children *add* detail over a still-drawn parent | Point clouds, detail decals, some VT schemes | Overdraw; blending rules at boundaries |

Replacement is the default for terrain geometry. Additive is legitimate for content layered *on*
the terrain (scatter density refinement, detail normal tiers) — mixing the two in one tree without
labelling which payload is which is a classic source of double-drawn geometry.

**Tile contents beyond height.** A production tile is a bundle, not a heightmap:

| Payload | Streams with geometry? | Notes |
|---|---|---|
| Height / vertex data | yes — defines the tile | Plus min/max for culling, `e(tile)` |
| Normals (baked) | yes | Baked from tile+apron (terrain-architect `08`) or lighting shows the grid |
| Splat / material weights | often **separate** (virtual texture, `07`) | Different resolution, different budget |
| Watermask / holes | yes | Needed at draw time for masking |
| Collision | **separate pipeline** | Coarser, different residency guarantee — see below |
| Instance sets (scatter) | separate, keyed to tile ID | Spawn/despawn on residency events, not per frame |

The load-bearing decision is which payloads share the geometry tile's lifecycle and which run their
own (virtual texturing runs its own page residency in `07`; collision runs its own ring below;
auxiliary cause-maps ride the geometry tile's lifecycle and are budgeted by their consumer registry
in `14`; instance sets spawn on residency events and hand off to `15`'s population pipeline).
Payloads that share a lifecycle must ship in **one contiguous blob per tile** — one IO request, one
decode — not as five small files that multiply seek/request overhead.

## Residency: the per-tile state machine

Every tile in the *cut* (the set the traversal wants) is in exactly one state:

```
unloaded --> requested --> loading --> resident --> renderable <---+
   ^ ^           |            |                         |          |
   | |    cancel |     cancel | (discard                v          | promotion: free —
   | +-----------+<-----------+  the completion)    evictable -----+ the tile re-entered
   |                                                    |            the cut
   +----------------------- evict ----------------------+
```

- **requested**: in the priority queue, no IO issued. Cheap to cancel — just drop it.
- **loading**: IO/decode in flight. Cancellation must be supported (camera turned away): mark the
  request abandoned so its completion is discarded, don't block on it. If the IO layer can't
  cancel, at minimum don't *upload* the corpse.
- **resident**: bytes in memory (CPU or GPU pool) but not yet legal to draw.
- **renderable**: uploaded, mips/derived data ready, seam constraints satisfiable. Only renderable
  tiles enter the draw traversal.
- **evictable**: not in the current cut; still in memory. This is your cache — an evictable tile
  re-entering the cut is a free promotion back to renderable.

**Priority function.** Order the request queue by expected visual payoff, not FIFO:

```
priority = sse_projected(tile)                       // dominant term: error on screen NOW
         * frustumFactor                             // in-frustum 1.0; behind ~0.1, never 0
         * predictFactor(cameraVelocity, tile)       // boost tiles the camera is flying toward
```

Never set out-of-frustum priority to zero — a fast camera turn then reveals a wall of unloaded
tiles. Prediction: extrapolate camera position 1–2 s ahead and compute SSE from the *predicted*
position too, take the max. Recompute priorities every frame for `requested` tiles (cheap); do not
reorder tiles already `loading`.

**Hysteresis.** Refine at `sse > tau`, but coarsen only at `sse < tau * h` with `h ≈ 0.7–0.85`
(equivalently: split at tau, merge at tau/1.2–1.4). Without the dead band, a camera hovering at
exactly the threshold splits and merges the same tile every frame — IO thrash, visible flicker.
Apply the same hysteresis to eviction distance.

**The always-renderable guarantee.** The hard rule that separates shippable streamers from tech
demos: **never show a hole**. Concretely:

1. A parent may not be released from renderable until **all four children are renderable**
   (replacement scheme). Refinement is atomic per parent: draw parent OR draw 4 children, never 3
   children + hole, never 3 children + parent (double-draw/z-fight).
2. On coarsen, the parent must be renderable *before* the children are dropped — if the parent was
   evicted, re-request it and keep drawing children until it arrives.
3. The root levels are pinned (never evicted), so the guarantee bottoms out: worst case, the world
   renders blurry, never absent. Blurry-but-present is the whole doctrine.

The renderable cut is therefore a *complete front* through the tree at all times; the streamer's
job is to push that front toward the wanted cut, never to tear it.

## IO, decompression, and upload budgets

The frame must never wait on the disk. Doctrine: **all** streaming work is asynchronous and
budgeted; the render thread consumes whatever finished, and nothing else.

- **Async IO**: overlapped/uring-style reads from a request queue; batch small requests; keep
  enough in flight to saturate NVMe (dozens of concurrent requests — NVMe queue depth is the point
  of NVMe). One-outstanding-read-at-a-time streamers run at HDD-era throughput on NVMe hardware.
- **GPU decompression** (DirectStorage-style, **D**): compressed tiles go disk → GPU memory and are
  decompressed on the GPU (GDeflate et al.), bypassing the CPU copy-and-inflate path. This is the
  2026 default on PC/console for texture-heavy tiles; keep a CPU fallback path and treat the two as
  the same logical stage with different executors.
- **BCn**: store final BCn where possible (decode-free upload). If source is stored in a
  super-compressed transcodable format, transcode to BCn on worker threads *or* GPU — never on the
  render thread. Runtime BCn *encoding* of procedural tiles is a compute pass, budgeted like any
  other (`09` procedural planets rely on this).
- **CPU budget isolation**: decode/transcode workers run at low priority on a bounded pool. The
  symptom of getting this wrong is frame spikes correlated with fast travel — streaming stealing
  cores from the game.
- **Upload ring**: all GPU uploads go through a persistent staging ring with a **per-frame byte
  budget** (typically 8–32 MB/frame at 60 Hz; tune to platform). A tile whose upload doesn't fit
  this frame waits — it is `resident`, not yet `renderable`. Never issue an unbounded burst of
  uploads because "the data is ready"; that is the canonical hitch. Split oversized single payloads
  across frames.
- **Pool defragmentation**: tiles allocate from fixed pools (constant tile size makes this
  trivial — free lists, no fragmentation). Variable-size payloads (meshes, instance sets) need a
  defragmenting heap: move a few blocks per frame under the same upload budget, patch descriptors.
  Never stop-the-world compact.

## Eviction and the memory budget

Eviction policy: **priority-aware LRU**. Pure LRU evicts the tile behind you that you're about to
turn back to; pure priority evicts nothing until crisis. Hybrid: evict from the evictable set the
tile with the lowest `priority`, breaking ties by oldest last-used frame; never evict tiles in the
current cut, tiles pinned (root levels, collision ring), or tiles mid-upload.

Budget math must be done **before** shipping, not discovered in OOM crashes. Worked example:
8×8 km world, height at 1 m/px, 4-layer splat weights at 0.5 m/px, 256 m square tiles
(256² height samples per tile, 512² splat texels per tile), 6 levels (L0 root at 32 m/px … L5 at
1 m/px, L5 = 32×32 = 1024 tiles):

| Payload per tile | Texels | Format | Bytes (+mips where GPU-resident) |
|---|---|---|---|
| Height | 256² (+4-texel apron) | R16 | ~136 KiB |
| Baked normal | 256² | BC5 | 64 KiB, +33% mips ≈ 85 KiB |
| Splat weights (4 layers) | 512² | BC7 (RGBA weights) | 256 KiB, +mips ≈ 341 KiB |
| Watermask | 256² | BC4 | 32 KiB |
| Collision heights (separate pool) | 128² | R16 | 32 KiB |
| **Total per tile** | | | **≈ 0.62 MiB** |

Residency with a ring cut (finest detail within ~1 km, each coarser level covering roughly a
doubled annulus — the standard clipmap-shaped cut):

| Level | m/px | Tiles resident (ring) | MiB |
|---|---|---|---|
| L5 (1 m/px) | 1 | ~50 (r ≈ 1 km) | ~31 |
| L4 | 2 | ~50 | ~31 |
| L3 | 4 | ~50 | ~31 |
| L2 | 8 | ~50 | ~31 |
| L0–L1 (pinned) | 16–32 | 5 | ~3 |
| **Resident set** | | **~205 tiles** | **~127 MiB** |

Two lessons generalize: (a) a ring cut costs **levels × ring**, roughly constant bytes per level —
versus ~845 MiB for the naive "whole pyramid resident" (1365 tiles), and (b) splat weights dominate
height ~3:1 even at these modest settings, which is why materials usually graduate to their own
virtual-texture residency (`07`) with a page cache sized independently. Add 30–50% headroom over
the computed set for in-flight loads, hysteresis band, and the evictable cache, and *assert* the
budget at runtime — a streamer without a budget assert grows until the platform kills it.

## Seams between tiles

Adjacent tiles at different levels re-create `01`'s crack problem at pyramid scale. The crack
contract, restated for tiles:

- **Shared-edge ownership**: adjacent same-level tiles must generate bit-identical edge vertices.
  This requires the generation side to have sampled edges consistently (shared corner convention,
  terrain-architect `08`); the renderer must not resample or re-quantize edges per tile.
- **Cross-level edges**: constrain the fine tile's edge to the coarse neighbour's edge function
  (drop odd edge vertices / stitch strips), or accept skirts.
- **Skirts as the fallback**: a short downward flange around each tile (depth ≥ max plausible
  cross-level gap, derived from `e(parent)`). Skirts are cheap, robust, and hide cracks — at the
  cost of minor texture stretch and occasional shadow artifacts on the flange. Chunked-LOD
  doctrine: skirts by default, exact stitching only when close-up silhouettes demand it.
- **Morph regions**: geomorph vertices near tile edges toward the parent's surface over the outer
  10–25% of the tile so the *pop* at replacement time vanishes, not just the crack (`01` CDLOD).
  Morph needs the parent's height at the child's vertices — either stored per vertex or sampled
  from the still-resident parent (another reason parents stay resident).
- **Attribute continuity needs the apron.** Normals, AO, and splat weights baked per tile diverge
  at edges unless they were baked over tile+apron and the apron discarded — that is exactly the
  apron the generation contract mandates (terrain-architect `08`). If tiles arrive apron-less, the
  renderer cannot fix the lighting seam; reject the data, don't blur it at runtime.

## HLOD and the far world

Beyond the pyramid's practical depth-from-camera, stop paying per-tile geometry cost:

- **Baked merged far tiles (HLOD)**: offline-merge each coarse tile's geometry *and everything on
  it* (rocks, trees, buildings) into one low-poly mesh with one baked atlas. One draw per far tile.
  The merge must bake from the same source data version as the streamed tiles or the swap line
  shows a world change, not just a detail change.
- **Impostors**: octahedral or billboard captures for isolated far features (mountain silhouettes
  handled by terrain tiles rarely need them; forests and structures do).
- **The far world as a texture**: at extreme range the terrain contributes only a silhouette and
  colour gradient — a pre-rendered ring/skybox strip or a single ultra-coarse mesh with baked
  colour. For planets the far field curves and this hands off to the cube-face pyramid of `09`;
  do not stretch a flat far-field hack past the visible-curvature range.
- **Lighting consistency across the swap**: far bakes must use the same sun, sky, and fog model as
  the near real-time path, or the HLOD boundary reads as a colour wall. Bake albedo-only and light
  at runtime where possible; if you bake lighting, re-bake when time-of-day is dynamic or accept a
  fixed-lighting far world (`10` owns this contract).

### 3D Gaussian splatting as a far representation — where it actually fits

⚠️ **Frontier, and narrower than the enthusiasm suggests.** Tier `P`/`D`: the primitive is
well-published and now has engine integrations and a glTF extension in flight, but its established
production use for terrain is **capture and previsualisation**, not the authored far world. Recorded
here so a reader can place it rather than reach for it.

**What it is, in this chapter's vocabulary.** A cloud of anisotropic Gaussians, each with position,
covariance, opacity and a view-dependent colour, rasterised by sorted alpha blending. It is a *far
representation* in exactly the sense the bullets above mean — it replaces per-tile geometry cost
with something cheaper at range — and it competes with impostors and baked HLOD rather than with
the heightfield.

**Why it is tempting for the far world.** It degrades gracefully with distance, has no silhouette
problem, and captures the one thing impostors handle worst: soft, high-frequency aggregate detail
(distant forest canopy, scree slopes, haze-lit rock) where a billboard reads as a card and a merged
mesh reads as fudge.

**Why it is not the answer yet, and each reason is one of this chapter's own contracts:**

- **It does not stream like a tile pyramid.** LOD for splats is an active research area — octree
  and continuous-LOD schemes exist and are recent — and none of them is the clean SSE-driven
  refinement of `01` that the rest of this chapter's residency machinery assumes.
- **It has no collision and no gameplay query.** Everything in *Collision and gameplay streaming*
  below needs a surface; a Gaussian cloud is not one, so the far world would need a parallel
  representation anyway.
- **Alpha-blended, sorted, unlit.** It does not compose with the deferred/visibility-buffer path of
  `08`, and relighting it under `10`'s time-of-day is not a solved problem — which is the same
  *lighting consistency across the swap* trap the bullets above already name, in a harder form.
- **Authoring is capture-shaped.** Its production pipeline is photogrammetry-like: capture a real
  place, import, use as reference or backdrop. That is a genuinely useful terrain workflow and it is
  a *content* pipeline, not a rendering tier.

**The honest 2026 position.** Use it where its shape fits — captured backdrops, previs, a distant
real location — and keep it behind the same far-world swap contract as any other far representation:
same sun, same sky, same fog, or the boundary reads as a wall. Do not plan a terrain LOD chain
around it.

## Collision and gameplay streaming

**Render residency and collision residency are different problems; never couple them.**

- Collision streams as its own coarser pyramid (or single-resolution grid) with a **guaranteed
  ring**: all collision tiles within radius R of any physics-active actor are resident *before*
  the actor is allowed to be there. Guarantee means synchronous-if-needed: gameplay blocks (or the
  actor is frozen/parachuted) rather than falling through the world. Render tiles never get this
  guarantee; blurry is acceptable, falling through is not.
- R is derived from max actor speed × worst-case load latency, plus margin. Fast vehicles need a
  velocity-elongated ring, same prediction as the render priority function.
- **Divergence pitfall**: collision baked from a different LOD than what's rendered means feet
  float or sink at distance-visible boundaries, projectiles hit invisible hills, AI paths clip
  through rendered ridges. Bound the divergence (collision within `e` of some declared render
  level) and verify it — `11` prescribes the render-vs-collision delta check. Gameplay traces that
  must match visuals exactly (bullet decals) should raycast the *render* heightfield, not physics.
- Scatter/instance gameplay data (destructibles, pickups) keys to collision residency, not render
  residency — an object you can hit must exist even when its visual is an impostor.

## Pitfalls

- **Pop-in from priority starvation**: distance-only priority lets a wall of mid-level tiles
  starve behind a stream of near-tile refinements. Priority must be SSE-based (error *on screen*),
  and the queue must age requests so nothing starves forever.
- **Thrash at the eviction boundary**: no hysteresis between the wanted cut and the evict
  threshold → the same tiles load and evict in a loop while the camera strafes the boundary.
  Symptom: sustained IO with a stationary-ish camera. Fix: dead band + minimum-resident-time.
- **Seams from missing aprons**: lighting/splat discontinuities exactly on tile edges. Not a
  renderer bug — the bake violated the apron contract (terrain-architect `08`). Fix the bake.
- **Hitching from synchronous mip generation**: generating mips (or BCn-encoding) on the render
  thread at upload time. All derived-data work happens in the worker/compute budget before the
  tile is declared renderable.
- **Holes during coarsen**: dropping children before the re-requested parent arrived. The
  always-renderable invariant applies in both directions.
- **Unbounded upload bursts after a load spike**: 200 tiles finish decoding in the same frame and
  all upload at once. The ring budget exists precisely for this moment.
- **Tile versioning across patches**: a patched world where old cached/baked tiles mix with new
  ones produces cross-tile seams and HLOD-vs-tile mismatches that no runtime code caused. Version
  every tile blob with a content hash of its source data + bake parameters; the streamer rejects
  mixed versions per region. Determinism of the bake (same inputs → same bytes) is what makes
  patch diffs small and cross-machine caches valid — same seed/determinism contract the
  generation side signs (terrain-architect `08`).
- **Testing only at walking speed**: streamers tune themselves into a corner where flight/teleport
  breaks them. `11`: verification must include max-speed traversal and teleport-to-cold-region.

## Sources & provenance

- **P** — Cozzi & Ring, *3D Engine Design for Virtual Globes* (2011): tile pyramids, screen-space
  error refinement, replacement vs additive refinement, residency and out-of-core rendering
  doctrine. The canonical text for this chapter's pyramid + SSE + residency core.
- **P/T** — Ulrich, "Rendering Massive Terrains using Chunked Level of Detail Control"
  (SIGGRAPH 2002 course): chunked quadtree, per-chunk geometric error, skirts, geomorphing.
- **P** — Strugar, "Continuous Distance-Dependent Level of Detail for Rendering Heightmaps
  (CDLOD)" (2009): morph regions as the pop/crack solution; shared currency with `01`.
- **P** — Losasso & Hoppe, "Geometry Clipmaps" (SIGGRAPH 2004): the ring-shaped residency cut and
  incremental update model the budget example assumes.
- **D** — Microsoft DirectStorage documentation: GPU decompression path, request batching, NVMe
  queue-depth guidance.
- **T** — Andersson, "Terrain Rendering in Frostbite Using Procedural Shader Splatting"
  (SIGGRAPH 2007 course): tile payload split between geometry and material pipelines.
- **T** — GDC terrain-streaming talks from large open-world titles (Far Cry, Ghost Recon
  Wildlands era) cover tile bundles, HLOD swaps, and collision rings; public talks exist — treat
  specific numbers quoted from memory as **F**.
- **T/F** — *Microsoft Flight Simulator* streaming presentations/posts (public talks exist):
  planet-scale tile pyramid + separate material streaming; exact internals unverified.
- **F** — Upload-ring budgets (8–32 MB/frame), hysteresis constants (0.7–0.85), headroom margins:
  standard-practice ranges, no canonical citation; tune per platform and verify per `11`.
