---
type: Technique
title: Heightfield LOD — spending triangles where the error shows
description: "Picking a level-of-detail scheme for regular-grid terrain, and the crack contract that decides whether it ships."
tags: [rendering, rasterizer, lod, heightfield, real-time]
status: draft
generated: { by: process:claude-code, at: 2026-09-02T00:00:00Z }
sources:
  - { id: strugar2009, tier: F, locator: "the Morph implementation section — morphK and the morphVertex HLSL that this document reproduces — and LOD distances and morph areas, where ranges double per level and the morph area is the last 15 to 30 per cent of each. Headings are unnumbered; the whitepaper gives no closed-form derivation of morphK" }
  - { id: ulrich2002, tier: F, locator: "the screen-space error projection, and the skirt discussion" }
  - { id: deboer2000, tier: F, locator: "§2.3 The Texture Mipmap Analogy for the per-block GeoMipMap chain; §2.3.2 Solving geometry-gaps for the index-buffer edge fix, which omits the finer edge vertices from the connectivity" }
  - { id: losasso2004, tier: P, locator: "§3 nested rings and toroidal 2-D wraparound access; §5 for the newly exposed L-shaped fill; §6.2 for both the transition region and the T-junction removal paragraph that closes it, rendering zero-area triangles along the render region boundaries. §6.3 is Texture mapping, not stitching" }
  - { id: asirvatham2005, tier: F, locator: "§2.3.5 and §2.4, heights read from a vertex texture and the clipmap updated GPU-side" }
  - { id: dupuy2020, tier: P, locator: "§5.2 Dedicated LEB Algorithms for CBTs — split and merge with the same-depth neighbour heap-index maps; §5.3 for the GPU terrain renderer feeding an indirect draw; §4.2 for the parallel update pipeline" }
  - { id: duchaineau1997, tier: P, locator: "§4, the split/merge priority queues" }
---
# Heightfield LOD — spending triangles where the error shows

**Tier: real-time rasteriser.** An 8k × 8k heightfield at full resolution is roughly 134 M
triangles and a frame affords a few million. Every scheme below is the same machine — a
controller holding *projected geometric error* under a pixel budget — and they differ only in
where the control loop runs and what happens at the seam between two levels.

## Use this

**CDLOD: a quadtree over one shared grid mesh, with a per-vertex distance morph.** No canonical
peer-reviewed paper backs this recommendation; standard practice is Strugar's self-published
whitepaper and its reference implementation [strugar2009], and the `F` tier is the honest grade for
it — a journal version exists but nobody here has read it, and `papers-rendering.md` records exactly
what promoting the entry would take. The technique is the 2026 default anyway, on the mechanism
rather than the venue.

Every node draws the same static grid, scaled to the node and displaced from the heightmap in the
vertex shader. Near the node's outer range, vertices at odd grid positions slide onto their even
neighbours, so the node becomes *vertex-identical to its parent* exactly at the boundary.

That single mechanism closes both open problems at once: no crack, because the two levels share
vertices; no pop, because the transition is continuous. Everything else in this family solves them
separately, with two mechanisms that can disagree.

**Cross over to CBT/LEB** [dupuy2020] when the terrain deforms at runtime, when you want the LOD
selection itself GPU-resident, and the team is comfortable in compute — see the crossover below.
**Cross over to geometry clipmaps** [losasso2004] when the world is uniform, streamed, and the
camera keeps a steady altitude.

**Say where the descent runs.** Canonical CDLOD walks the quadtree on the CPU every frame, and
`gpu-driven-culling.md` makes it a rule that no array proportional to world size may be rebuilt on
the CPU per frame. The two compose, but only if you are explicit about which of three shapes you
built:

- **CPU descent, GPU everything else** — the descent is O(*selected cut*), a few thousand nodes,
  not O(world): it early-outs on the range test and never touches a node outside the view's range
  bands. What it uploads is a *candidate* list that the GPU then culls, so the **selected cut is
  not the visible set** — pruning it CPU-side to make it one is the mistake. Leave frustum,
  occlusion, per-pass survivor lists and submission in compute. This is what most shipped CDLOD
  is, and `gpu-driven-culling.md` names it in those words as **not partial adoption**: its rule is
  about what the cost scales *with*, not where the code runs, and the selected cut scales with the
  view. Say so in writing, or the next person "fixes" it.
- **Compute descent** — a persistent node buffer plus a compute kernel that appends selected nodes
  straight into the indirect argument buffer, so the CPU never sees the cut at all. Legitimate;
  CDLOD's descent was simply not designed for it, and the split/merge logic is yours to write.
- **CBT/LEB** [dupuy2020] — natively GPU-resident, with O(1) leaf enumeration feeding the indirect
  draw directly. Runtime deformation is the usual reason to reach for it; *"the pipeline must be
  GPU-driven end to end with no CPU node list"* is the second, and it is the one this document
  used to leave unstated.

## The controller everything shares

A simplified region carries a precomputed maximum geometric error `e` in metres — the largest
vertical deviation from the full-resolution surface, computed over the *actual* vertex removals,
never guessed from a mip level. Project it [ulrich2002]:

```
K   = viewportHeight / (2 * tan(fovY / 2))   // pixels; the perspective scale constant
rho = (e * K) / d                            // projected error in pixels
refine while rho > tau                       // tau = the budget, 1-4 px in practice
```

⚠️ **`rho` is an orientation-independent worst case, not the projected error.** `e` is a *vertical*
deviation, and a vertical segment at distance `d` subtends `e·K·sin θ / d` pixels, where `θ` is the
angle between the view ray and world up. The form above is the `sin θ = 1` case — looking at the
horizon — and the projection falls to zero looking straight down. Taking the orientation-free
maximum is the right engineering call, cheap and conservative, but say that it is one: an engineer
who instruments `rho` and finds measured error consistently *below* prediction otherwise cannot
tell a conservative metric from a broken one, and will distrust the quadrupling diagnostic below.

Three things about this that are wrong in shipped code more often than not:

- **`d` is the distance to the closest point on the region's bounds**, including its height
  extent — not to its centre. Centre distance under-tessellates a large chunk whose near edge is
  at your feet, and mis-measures tall cliff chunks from above.
- **`K` changes with FOV.** Recompute per frame or terrain melts when the player scopes in.
- **`tau` is a quality slider with an honest unit.** Expose it. Under a dynamic-resolution or
  temporal upscaler, scale it with the render target — `K` already moved.

Halving `tau` should roughly quadruple triangle count — **while there is still detail left to
refine into.** The 1/τ² relation saturates: once a region is drawn at the heightfield's own sample
spacing its triangle count cannot grow again, so at small `tau` the near field pins at source
resolution and the measured slope flattens. That is the metric working, not failing, and it is
routine rather than exotic. Run the diagnostic on the band that is still refining, with regions
already at source resolution excluded; if *those* do not roughly quadruple, the error metric is
lying somewhere and no amount of scheme-swapping will fix it.

## The morph, and the two rules that make it work

```
morphK   = saturate((dist - rangeStart) / (rangeEnd - rangeStart));  // 0 inside, 1 at boundary
fracPart = frac(gridPos * meshDim * 0.5) * (2.0 / meshDim);          // 0 for even verts
gridPos  = gridPos - fracPart * morphK;                              // odd verts -> even verts
uv       = worldToHeightmapUV(gridPos);      // ONE mapping, shared with the parent node
height   = lerp(sampleHeight(uv, nodeLod), sampleHeight(uv, nodeLod + 1), morphK);
normal   = normalize(lerp(sampleNormal(uv, nodeLod), sampleNormal(uv, nodeLod + 1), morphK));
```

- **`morphK` must reach exactly 1.0 at the selection boundary.** Not 0.98. A morph that stops
  short leaves a hairline crack that appears only at one camera distance, which is why it
  survives review and ships.
- **Height is *lerped between the two levels' samples*, not merely re-sampled at the morphed
  position.** Those are not two spellings of one rule. Sliding XZ alone leaves the silhouette
  popping while the wireframe looks perfect — but re-sampling closes the pop and leaves the crack,
  because at `morphK = 1` the fine node reads mip `nodeLod` where its parent reads `nodeLod + 1` at
  the *same* XZ, and the two surfaces still disagree vertically. Only the lerp makes the fine
  vertex *become* the parent's sample. Measured below.
- **One `morphK` drives XZ, height and normal.** Three factors are three chances to disagree, and
  the vertex is identical to its parent only if all three reach 1.0 together. Geometry morphing
  under un-morphed normals still pops, and a lighting discontinuity reads louder than a silhouette
  change: across the same field the two levels' normals differ by a median 4.6–5.9° and a p95 of
  11–13° at the shared vertices.
- **Both nodes must share one heightmap registration** — one world-XZ→UV mapping, one reduction
  filter, one mip convention — or `sampleHeight(uv, nodeLod + 1)` on the fine node is not the value
  the parent computed at that XZ. Half a coarse texel of disagreement leaves a residual **4–5×
  larger than the crack the lerp was closing**, so this is a condition on the contract, not a
  detail. A mip chain reduced with a filter centred on the retained sample keeps the registration;
  a half-texel-shifted box does not.

Restrict morphing to the outer band of each range — the CDLOD whitepaper puts the morph area at
"the last 15%-30% of every LOD range", and that is the figure to start from — so most vertices
render un-morphed and the per-frame morph delta stays sub-pixel at real camera speeds.
And make the morph factor a pure function of (vertex, camera): never wall-clock blending after
"the LOD changed", which desynchronises across the shadow and depth passes the moment the camera
teleports or streaming hitches.

**What it beats.** *Geomipmapping* [deboer2000] — fixed chunks with a per-chunk mip chain and
index-buffer edge stitching; a fine baseline for a small world, but cracks and popping need two
separate mechanisms and the adjacency constraint is a standing invariant to police. *Chunked LOD*
[ulrich2002] — pre-simplified static chunks, opaque blobs that stream and compress beautifully;
loses because the content is baked, so a runtime height edit means re-baking, and its skirts leak
(below). *Quadtree with edge index-buffer permutations* — the unnamed workhorse; cheap and robust,
no canonical paper, but it fixes cracks and leaves popping entirely unsolved. *Hardware
tessellation* — a low-effort win if the pipeline already exists, but the factor cap, the
amplification cliffs, and a LOD decision stranded in a fixed pipeline stage make it the wrong
architectural centre in 2026. *ROAM* [duchaineau1997] — dead as shipped (per-triangle CPU work,
per-frame index rebuilds), but read it: its longest-edge-bisection bintree is precisely what
[dupuy2020] resurrected on the GPU. *Cluster/virtualized geometry* — the right answer when the
terrain is a static authored mesh with overhangs; it subsumes this entire document, and it is not
a heightfield technique.

## The crossover that actually changes the answer

Dynamism is the sharpest discriminator, world size the second.

| Situation | Use | Because |
|---|---|---|
| Huge view range, streamed tiles, terrain is a heightfield forever | **CDLOD** [strugar2009] | One mechanism for cracks and popping; tiles map onto the streaming pyramid unchanged |
| Runtime deformation, or a selection that must itself be GPU-resident; compute-comfortable team | **CBT/LEB** [dupuy2020] | Topology is re-derived every frame from a GPU bitfield, so edits are free; conforming by construction, so cracks are impossible rather than patched; adapts to roughness as well as distance |
| Uniform streamed world, GPU displacement, steady camera altitude | **Geometry clipmaps** [losasso2004] [asirvatham2005] | Fixed memory, fixed vertex count, zero per-frame LOD decisions; toroidal addressing of each level's array means a shift writes only the newly exposed L-shaped strip [losasso2004], and the GPU-resident form keeps that array in a vertex texture updated on the GPU [asirvatham2005] |
| Small world, mid hardware, days of budget | Geomipmapping [deboer2000] | Fully adequate; add a dithered cross-fade for popping |

Clipmaps cost triangles that a quadtree would save, because their LOD is distance-only and cannot
coarsen flat terrain. That waste starts to matter somewhere past a ~20 km view range — the
threshold is judgement, the direction is not.

## The crack contract

At every level boundary the finer side has vertices the coarser side lacks. If they leave the
coarse edge's interpolated line, background bleeds through as sub-pixel holes. The doctrine:
**cracks are prevented by contract at design time, never healed by runtime vertex welding.** A
weld pass is an admission that the scheme has no boundary contract; it is order-dependent, it
breaks under streaming, and it fails precisely on the frames where LOD changes.

| Contract | Mechanism | What it costs you |
|---|---|---|
| Vertex morphing | Fine vertices *become* coarse ones by the boundary | A second, mandatory morph — the heightmap mip lerp — plus one registration shared by both nodes; and `morphK` must hit 1.0 exactly |
| Conforming subdivision | A split propagates to the edge-neighbour; T-junction-free by rule [dupuy2020] | The whole CBT machinery; bugs move into the split/merge kernel |
| Transition regions | Ring fringes blend toward the coarser level; the T-junctions that remain are stitched with zero-area (degenerate) triangles along the ring boundary [losasso2004] | Only available inside the clipmap structure |
| Index stitching | The finer chunk drops every other edge vertex [deboer2000] | Heights still pop; needs the ≤1-level adjacency invariant |
| Skirts | A vertical curtain dropped from each chunk edge [ulrich2002] | The curtain is visible to SSAO, fog, shadows and decals as dark seam lines |

**How big is the gap the XZ morph does not close?** Measured on a synthetic 2048² fBm field at
2 m spacing, across four roughness settings and three mip-reduction kernels: at the shared vertices
the mip `L` and mip `L + 1` surfaces disagree by **0.16–0.47 × the coarse level's geometric error
`e` at p95, and 0.25–1.0 × `e` at maximum**. The ratio is the useful form, because the level
boundary is by construction where `e·K/d = tau` — so the gap projects to **0.2–0.5 `tau` at p95 and
up to a full `tau` at worst, at every level, FOV and resolution**, since `K` and `d` cancel. Do not
read sub-`tau` as safe: `tau` prices a surface in the wrong *place*, which is invisible, while this
is a *hole* the background shows through, in a ribbon along every level boundary in the frame.
Substitute the lerp form and the same measurement is **0.000000 m at `morphK = 1`, exactly, in
fp32** — that is what makes it a contract rather than a mitigation.

**A T-junction is a crack even when the vertex lies exactly on the edge.** Watertight
rasterization is guaranteed only between triangles *sharing the same two vertices*; the coarse
edge is interpolated along a different edge equation, so pixel centres along the junction
intermittently land in neither triangle. Eliminate T-junctions structurally. Nudging positions
does not close them. Skirts are the one contract that tolerates them — the curtain hides the
holes, which is exactly why they are cheap and why they leak into every screen-space pass.

## How this fails, and what it looks like

| Symptom | Mechanism | Fix |
|---|---|---|
| Hairline cracks at chunk borders, only at certain distances | `morphK` does not reach exactly 1.0 at the range boundary | Fix the morph constants; sweep the *full* distance range, not one camera position |
| Single-pixel shimmer along straight, otherwise clean seams | T-junction: vertex on the edge, different edge equation | Remove it structurally; do not nudge the vertex |
| Wireframe is continuous but the silhouette still pops | Height sampled at the un-morphed position | Sample at `gridPos` *after* the morph, never before |
| A hairline crack survives a `morphK` verified to reach exactly 1.0 | At the boundary the fine node reads mip `L` and its parent mip `L+1` at one shared XZ | `lerp(sampleHeight(uv, L), sampleHeight(uv, L+1), morphK)`, with one registration on both nodes |
| Geometry morphs but lighting jumps at the band | Normals not morphed with the same factor | Blend both levels' normals by the same `morphK` |
| Vertices swim only inside the morph band | Morph factor depends on frame state, not (vertex, camera) | Make it a pure function; one selection result per frame |
| Terrain silhouette differs between depth prepass and base pass | Each pass selected LOD independently | One selection, shared by every pass including all shadow cascades |
| Shadow acne no bias can fix, tracking LOD changes | Shadow pass selected LOD from the *light's* distance | Reuse the camera's selection, or a uniformly coarser version of it |
| Dark seam lines in AO, fog or decals along chunk edges | Skirt curtains are visible to screen-space passes | Exclude skirts from those passes, or change crack contract |
| Distant slopes sparkle and read over-lit | Full-frequency normal mips under correct geometric LOD | Variance-compensated roughness in the normal mip chain |
| Objects float or sink on distant terrain | Physics samples the authoritative field; render shows error `e` | Keep `tau` small where gameplay happens; match the collision triangulation, diagonal included |
| Halving `tau` does not roughly quadruple triangles | The error metric is not a controller — but first exclude regions already pinned at source resolution, where the relation saturates by design | Find the region whose `e` was guessed rather than measured |
| Vertices jitter beyond ~10 km from the origin | fp32 world-space vertex maths; the morph lerp amplifies quantized endpoints | Chunk origins carry the large translation, not vertices — camera-relative rendering |
