# Heightfield LOD: from geomipmapping to CBT

This chapter owns the LOD machinery for regular-grid heightfield terrain: the screen-space
error metric every scheme is secretly a controller for, the technique family tree (ROAM →
geomipmapping → chunked LOD → clipmaps → CDLOD → hardware tessellation → CBT/LEB), the crack
contract, and geomorphing doctrine. Cluster/meshlet virtualized geometry is `02`; engine-native
implementations are `03`; streaming the tiles this LOD selects is `06`; the culling and
submission machinery that draws the result is `08`.

Contents: [Problem statement](#the-problem-statement-error-control) ·
[Technique survey](#technique-survey) · [Comparison table](#comparison-table) ·
[Crack contract](#the-crack-contract) · [Geomorphing & popping](#geomorphing--popping-doctrine) ·
[Vertex pipeline patterns](#vertex-pipeline-patterns) ·
[Hex lattice, render-side](#the-hexagonal-lattice-render-side) ·
[Selection guidance](#selection-guidance) ·
[Pitfalls](#pitfalls) · [Sources](#sources--provenance)

## The problem statement: error control

A 8k×8k heightfield at full resolution is ~134M triangles; a frame budget affords a few
million, most of which must be spent near the camera. Every heightfield LOD scheme in this
chapter — however different the machinery — is the same thing: a controller that keeps
**projected geometric error** below a pixel budget while minimizing triangle count, CPU cost,
and popping. Judge any scheme by what it uses for error, how it projects it, and what it does
at LOD boundaries. If a scheme cannot state its error metric, it is a heuristic, not a
controller, and it will over- or under-tessellate somewhere you can't predict.

The standard projection: a simplified region carries a precomputed **maximum geometric error**
`e` in meters — the largest vertical deviation between the simplified geometry and the full-res
surface (compute it over the *actual* vertex removals, not as a guess from mip level). Its
screen-space error in pixels at distance `d` meters:

```
K   = viewportHeight / (2 * tan(fovY / 2))     // pixels; the perspective scale constant
rho = (e * K) / d                              // projected error in pixels
refine while rho > tau                         // tau = error budget, typically 1-4 px
```

Notes that matter:

- **Distance variant vs perpendicular variant.** The formula above uses radial distance `d` and
  treats `e` as if perpendicular to the view ray — an upper bound, standard practice (Ulrich
  2002 form). The tighter variant projects only the component of `e` perpendicular to the view
  direction; it buys triangles when looking straight down at terrain (error is vertical, view
  is vertical, projected error ≈ 0) but goes degenerate at grazing angles and needs clamping.
  Ship the simple radial form unless top-down views dominate.
- `d` must be distance to the **closest point** on the region's bounds, not to its center — see
  Pitfalls.
- `tau` is a *quality slider with an intuitive unit*. Expose it; 1 px is near-imperceptible,
  2-4 px is the common shipping range, and dynamic-resolution systems should scale `tau` with
  the render target, since `K` already changes with it.
- FOV changes (ADS zoom, cutscenes) change `K`. Recompute per frame; a cached `K` from the
  default FOV is a classic "terrain melts when I scope in" bug.

## Technique survey

### ROAM (1997) — historical, but its bintree survived

Duchaineau et al. 1997. Per-triangle split/merge on a **binary triangle tree** driven by
priority queues, re-run on the CPU every frame. Dead as shipped: per-triangle CPU work and
per-frame index buffer rebuilds are exactly what GPUs punish hardest. Study it anyway, for two
ideas that survived: (a) frame-coherent split/merge queues, and (b) the **longest-edge
bisection** bintree, which is precisely the structure CBT/LEB (below) resurrected on the GPU.

### Geomipmapping (2000)

de Boer 2000. Cut the heightfield into fixed chunks (e.g. 33×33 vertices); each chunk holds a
power-of-two mip chain of grid resolutions with a precomputed max error per mip; select mip per
chunk from the rho test. Cracks handled by index-buffer edge stitching against neighbors,
with the constraint that adjacent chunks differ by ≤ 1 level (see crack contract). Trivially
simple, still a fine baseline for small-to-mid worlds; the quadtree chunk systems below are its
adaptive descendants.

### Chunked LOD (2002)

Ulrich 2002. A quadtree of **pre-simplified static chunks**: each node stores a self-contained
mesh at some resolution plus its max error `e`; refine into children while `rho > tau`. Cracks
covered by skirts; popping hidden by per-chunk geomorph. Its enduring virtues: chunks are
opaque blobs — they can be arbitrary meshes (TINs, not just grids), they compress and stream
beautifully (`06`), and the renderer needs zero knowledge of how they were built. Its cost:
content is baked, so runtime height edits mean re-baking chunks; and skirt artifacts (below).
This is the direct ancestor of virtualized-geometry terrain — when chunks become clusters with
a finer-grained error DAG, you have arrived at `02`.

### Geometry clipmaps (2004) and the GPU implementation (2005)

Losasso & Hoppe 2004; GPU version Asirvatham & Hoppe, GPU Gems 2 (2005). Not a quadtree at all:
**nested square rings of grid resolution centered on the viewer**, each ring 2× coarser than
the one inside it. LOD is a pure function of viewer distance, so the mesh topology is *static
forever* — only the height data changes. Each level's heights live in a texture updated
**toroidally** (wrap-around addressing; on camera motion, write only the newly exposed L-shaped
strip, never scroll the texture). Between levels, a **transition region** on the outer fringe
of each ring blends vertex height (and normal) toward the coarser level so the boundary is
continuous; ring boundaries are stitched with **degenerate triangles** so rasterization is
watertight where vertex densities meet. Strengths: fixed memory, fixed vertex count, zero
per-frame LOD decisions, ideal fit for GPU displacement and uniform streaming. Weaknesses: LOD
is distance-only (no adaptivity to rough vs flat terrain — flat ocean floor costs the same as a
ridge), and view-centering means every level updates every frame the camera moves.

### CDLOD (~2009)

Strugar's whitepaper (~2009). Quadtree selection like chunked LOD, but all nodes render the
same static grid mesh scaled to the node, displaced from the heightmap in the vertex shader —
and cracks/popping are both solved by **continuous per-vertex morph**: near a node's outer
distance range, vertices at odd grid positions slide toward the position (and height) of the
neighboring even vertex, so the mesh *becomes* the parent LOD exactly at the range boundary.
The morph math:

```
// gridPos in [0,1]^2 across the node's mesh, meshDim = grid vertex count per side
morphK   = saturate((dist - rangeStart) / (rangeEnd - rangeStart));   // 0 inside, 1 at boundary
fracPart = frac(gridPos * meshDim * 0.5) * (2.0 / meshDim);           // 0 for even verts
gridPos  = gridPos - fracPart * morphK;                                // odd verts -> even verts
height   = sampleHeight(gridPos);                                      // re-sample AFTER morph
```

Two non-negotiables: `morphK` must reach exactly 1.0 at the selection boundary (parent and
child are then vertex-identical → no crack, no pop), and the morph range per level must be wide
enough that a vertex never jumps levels within it — Strugar computes per-level morph constants
on the CPU to guarantee monotonicity. Height must be re-sampled at the *morphed* position (or
lerped between the two levels' samples), not just the XZ slid — otherwise the silhouette still
pops. CDLOD remains the default recommendation for huge-view-range streamed heightfields in
2026.

### Quadtree chunks with index-buffer edge permutations

The unnamed workhorse of many shipped engines (no canonical paper; standard practice): quadtree
selection, one shared vertex grid per chunk, and a small library of precomputed index buffers —
one per combination of coarser-neighbor edges (16 permutations for 4 edges, fewer by symmetry).
The chunk picks the index buffer whose edges drop every other vertex on sides facing a coarser
neighbor. Requires the ≤ 1 level adjacency constraint. Cheap, robust, no skirt artifacts;
popping must still be handled separately (geomorph or cross-fade).

### Hardware tessellation (DX11 era)

Hull/domain shader pipelines: coarse patch grid, per-edge tessellation factors from the rho
metric, displacement in the domain shader. The crack rule is absolute: **shared edges must
receive bit-identical factors from both patches**, which means computing each edge's factor
purely from data symmetric in the two patches (e.g. edge midpoint + edge length), never from
patch-interior data. Use `fractional_even`/`fractional_odd` partitioning for continuous LOD
(integer partitioning pops). In 2026 this path is legacy-leaning: fixed-function tessellators
have unfriendly performance cliffs, factors cap at 64, and compute/mesh-shader subdivision
(CBT, `02`) does the same job with more control — but it remains a low-effort win when the
engine already has the pipeline and the terrain is a moderate-size single domain.

### CBT / LEB adaptive GPU subdivision (2020s)

Dupuy 2020 (HPG), "Concurrent Binary Trees", with the GPU-tessellation groundwork in Khoury,
Dupuy & Riccio (GPU Zen 2). The ROAM bintree reborn as a GPU-resident bitfield: the whole
terrain is one **longest-edge-bisection** triangulation encoded in a concurrent binary tree — a
sum-reduction over a bit-per-leaf array that supports lock-free split/merge from thousands of
threads plus O(1) leaf enumeration for indirect draw. Per frame, a compute pass tests each leaf
triangle against the rho metric and splits/merges; LEB's bisection rules keep the triangulation
**conforming by construction** (a split propagates to the edge-neighbor), so cracks are
impossible rather than patched. One mesh, one indirect draw (or meshlet emission), fully
adaptive to both distance *and* terrain roughness, and — because topology is re-derived every
frame — indifferent to runtime height edits. Costs: the least off-the-shelf of the family
(sophisticated compute, careful memory budgeting for the CBT), and frustum/occlusion culling
must be integrated into the subdivision criterion rather than bolted on per-chunk (`08`).

## Comparison table

| Scheme | Memory | GPU fit | Cracks | Popping | Streaming fit | Runtime edits | Impl. cost |
|---|---|---|---|---|---|---|---|
| ROAM | low | terrible (CPU/frame) | bintree conforming | per-tri (fine) | poor | good | high, obsolete |
| Geomipmapping | low | good | index stitching | geomorph (add-on) | fair | good | low |
| Chunked LOD | high (baked meshes) | good | skirts | per-chunk geomorph | excellent | poor (re-bake) | medium |
| Geometry clipmaps | fixed, low | excellent | transition blend + degenerates | transition blend | excellent (uniform) | excellent | medium |
| CDLOD | low | excellent | per-vertex morph | same morph (free) | excellent (`06`) | good | medium |
| Quadtree + edge IB permutations | low | good | index stitching | separate (fade/morph) | good | good | low-medium |
| HW tessellation | low | fair (tess cliffs) | matched edge factors | fractional partitioning | fair | good | medium |
| CBT/LEB | low (bitfield + heightmap) | excellent (compute) | conforming by construction | continuous subdivision | single-domain bias | excellent | high |

## The crack contract

At every boundary between two LOD levels, the finer side has vertices the coarser side lacks.
If those extra vertices displace off the coarser edge's interpolated line, the mesh tears:
background bleeds through as sub-pixel holes. The doctrine: **cracks are prevented by contract
at LOD-boundary design time — never healed by post-hoc geometry welding.** A weld pass (snap
nearby vertices at runtime) is an admission the LOD scheme has no boundary contract; it is
order-dependent, breaks under streaming, and fails exactly on the frames where LOD changes.

The five legitimate contracts:

| Strategy | Mechanism | Cost | Failure mode |
|---|---|---|---|
| Skirts | Vertical curtain dropped from every chunk edge, deep enough to cover max neighbor error | ~4·(N−1) extra tris/chunk; zero coordination | Curtain geometry catches shadows, fog, SSAO, decals; visible as dark seam lines; wrong in shadow maps (`10`) |
| Index stitching / edge permutations | Finer chunk drops every other edge vertex via alternate index buffer | Precomputed IB set; needs ≤1 level adjacency | Combinatorics if adjacency constraint slips; the *heights* still pop at the edge without morphing |
| Vertex morphing | Fine vertices continuously become coarse ones by the boundary (CDLOD; clipmap transition regions) | Vertex shader ALU; morph-range bookkeeping | If morph ≠ exactly 1.0 at boundary, hairline cracks that only appear at specific distances |
| Matched tessellation factors | Shared edge gets bit-identical factor from both patches | Discipline in factor computation | Any patch-interior term in the edge factor → cracks; also FP non-determinism if the two sides compute the "same" value differently |
| Conforming subdivision (LEB) | Split propagates to edge-neighbor; triangulation is T-junction-free by rule | The whole CBT machinery | None at boundaries; bugs move into the split/merge kernel instead |

**T-junctions are a crack even when the vertex lies exactly on the edge.** A fine vertex placed
mathematically on the coarse edge still sparkles: watertight rasterization is only guaranteed
between triangles *sharing the same two vertices*. The coarse edge is interpolated in float by
fixed-function hardware along a different edge equation, so pixel centers along the junction
intermittently fall in neither triangle — single-pixel holes that shimmer under motion (D3D/
Vulkan rasterization rules). Eliminate T-junctions structurally (all five contracts above do);
do not try to "close" them by nudging positions. Skirts are the one contract that tolerates
T-junctions — the curtain hides the holes — which is why they're the cheap option and why they
leak in every screen-space and shadow technique that sees the curtain.

## Geomorphing & popping doctrine

Popping is **managed, never eliminated** — any discrete LOD change moves geometry; the job is
to move it below perceptual threshold or spread it over time. Rules:

- **Morph in the vertex shader from the parent-LOD position.** Store or recompute where this
  vertex sits on the coarser level; lerp position (primarily height) by a morph factor driven
  by the same distance metric used for selection. Never morph by "the LOD just changed, animate
  over N frames" wall-clock blending — camera teleports, streaming hitches, and shadow passes
  all desynchronize it. Morph factor must be a pure function of (vertex, camera), so it is
  stable across frames and identical in every pass that draws the terrain.
- **Morph regions**: restrict morphing to the outer band (commonly the last ~25-35%) of each
  LOD range so most vertices render un-morphed at full detail, and so the band is wide enough
  that per-frame morph deltas are sub-pixel at typical camera speeds.
- **Normals must fade too.** Geometry morphing with un-morphed normals still pops — lighting
  discontinuities read louder than silhouette changes. Blend between the two levels' normal
  maps (or recompute normals from the morphed height) with the same morph factor. Same for any
  height-derived material inputs (slope masks, AO — `07`).
- **Dithered LOD cross-fade + TAA** is the modern alternative when morphing is awkward (baked
  chunk meshes, `02`-style clusters): draw both LODs during transition with complementary
  screen-door dither masks and let TAA resolve the stipple. Costs double geometry in the band
  and inherits TAA's failure modes (ghosting on the fade, visible stipple if TAA is off — offer
  a fallback). No canonical paper; standard practice across 2015+ engines.

## Vertex pipeline patterns

- **Vertex-pulled grids.** No vertex buffer at all: derive grid coordinates from `SV_VertexID`
  (or index into a tiny shared patch IB), compute world XZ from the chunk transform, fetch
  height from texture. One shared static index buffer (plus edge permutations if stitching)
  serves every chunk at every level. This is the default in 2026 — it kills per-chunk VB
  memory, makes streaming a pure texture problem (`06`), and feeds GPU-driven submission (`08`)
  since a "draw" is just a chunk ID.
- **Displacement source.** Heightmap texture, R16 unorm (with `min/max` scale-bias) or R32F.
  Precision, quantization, and tiling of that texture are the *generator's* output contract —
  route to terrain-architect `08`; the renderer's job is to not undo it (no silent R16→R8,
  no resampling through a filtered mip chain). Sample with explicit `Load`/`Gather` at texel
  centers in the vertex path — bilinear at an unintended mip level is a geometry bug, not a
  blur.
- **Normals: sampled, not derived, at runtime.** Deriving normals in-shader from height
  differences ties normal quality to the *current LOD's* sample spacing — normals then visibly
  degrade and pop with LOD. Prefer a generator-baked normal map sampled like any material
  texture with its own mip chain (aliasing doctrine → `10`). In-shader derivation is acceptable
  for truly dynamic heightfields (deformation, craters) where baking can't keep up — accept the
  LOD coupling or derive from a fixed-resolution height texture regardless of mesh LOD.
- **Shadow passes.** The shadow map must see terrain geometry consistent with the main view.
  Selecting LOD from the *light's* distance gives a different mesh than the camera sees →
  self-shadow acne and peter-panning that no bias fixes, plus shadow shimmer as light-space LOD
  changes. Standard practice: reuse the camera's LOD selection (or a uniformly biased-coarser
  version of it) for all shadow cascades; verify with the `11` mismatch checks; bias doctrine
  in `10`. Same rule for any depth pre-pass: identical geometry or equal-depth guarantees,
  never "similar".

## The hexagonal lattice, render-side

Some pipelines sample terrain on a hex lattice (terrain-architect `26` owns that choice, its
storage, and its stencils; hex-map *games* arrive here too). A hex grid rasterizes only after a
triangulation choice, and the choice trades vertices against fidelity to the per-hex sample.
With N hexes there are asymptotically 2N unique corners (each corner shared by 3 hexes):

| Triangulation | Verts | Tris/hex | Height fidelity | Use when |
|---|---|---|---|---|
| **Corner-only** | ~2N | 4 | Corners only — each corner is a 3-hex average, so per-hex extrema (peaks, pits) are *attenuated*; high-frequency amplitude visibly shrinks | Cheapest smooth terrain; relief is low-frequency; memory-bound |
| **Center-fan** | ~3N (2N corners + N centers) | 6 | Center vertex carries the hex's own sample exactly; corners still average — preserves amplitude and per-hex authorship | Default for simulation-faithful terrain; anything where a hex's value must survive to the silhouette |
| **Flat per-hex (prism/extrusion)** | 6 per hex (unshared) | 4 top + sides | Exact and *discontinuous* — gameplay-readable steps, not terrain relief | Hex-map strategy rendering; the "board game" read |

Two render-side rules: the corner average is a *resampling* — treat corner-only triangulation
as a half-band low-pass and don't be surprised when verification (`11`) shows amplitude loss
against the source field; and normals on hex meshes come from the lattice-correct gradient
(terrain-architect `26`'s stencils), not from a square-grid Sobel run over a resampled raster —
the square stencil on sheared storage silently skews every slope. LOD on hex terrain usually
resamples to coarser hex rings or hands off to a raster pyramid at distance; crack handling at
ring boundaries follows the same contract taxonomy as squares (skirts and morphs port; index
stitching does not, because the neighbor topology differs).

## Selection guidance

| Situation | Pick | Why |
|---|---|---|
| Small-to-mid world (≤ ~8 km), single load, mid HW | Geomipmapping / quadtree + edge IBs | Days of work, fully adequate; add cross-fade for popping |
| Uniform streamed world, GPU displacement, steady camera altitude | Geometry clipmaps | Fixed memory & vertex count, toroidal updates match streaming (`06`) |
| Huge view ranges (10-100+ km), tiled streaming, terrain is a heightfield forever | CDLOD-style quadtree | Continuous morph solves cracks+popping in one mechanism; proven at scale; tiles map to `06` |
| Single-domain adaptive detail, runtime deformation, high-end HW, compute-comfortable team | CBT/LEB | Adapts to roughness, edits are free, one indirect draw; highest impl. cost |
| Terrain is a static *authored mesh* (sculpted cliffs, overhangs) | Route to `02` | Cluster/virtualized geometry subsumes heightfield LOD entirely for static meshes |
| Engine-native (UE Landscape/Nanite, Unity) | Route to `03` | Fight the engine's scheme only with a reason in writing |
| Blocky / smooth voxel worlds | Route to `04` / `05` | Different remeshing-driven LOD paradigm; this chapter's error metric still applies |

Dynamism is the sharpest discriminator: chunked LOD's baked meshes are the wrong answer the
moment gameplay edits heights at runtime; CBT and clipmaps are the strongest answers. World
size is second: clipmaps' distance-only LOD wastes triangles on flat distant terrain that a
quadtree would coarsen, which starts to matter past ~20 km view ranges.

## Pitfalls

- **Float precision / vertex swimming at large coordinates.** World-space vertex math in fp32
  beyond ~10-100 km jitters visibly (morphing amplifies it — the morph lerp operates on already
  quantized endpoints). Camera-relative rendering and the full precision doctrine live in `09`;
  the LOD-specific rule is that chunk origins, not vertices, carry the large translation.
- **Physics-vs-render LOD divergence.** Collision must sample the *authoritative* heightfield,
  never the rendered LOD — but then rendered geometry at distance deviates from collision by up
  to `e` meters. Ragdolls and vehicles at distance float or sink by exactly your error budget.
  Keep `tau` small where gameplay happens, and never run gameplay traces against morphed
  geometry.
- **Heightmap bilinear vs vertex grid mismatch.** The renderer shows vertices at texel-center
  samples with linear interpolation along triangle edges (diagonal split direction matters);
  physics libraries interpolate the same heightfield bilinearly (or with the *other* diagonal).
  The surfaces differ between samples — objects visually hover in valleys of the discrepancy.
  Make the collision mesh's triangulation (including diagonal orientation) match the render
  grid's, or accept and bound the error.
- **LOD metric from distance-to-center.** Using chunk-center distance under-tessellates large
  chunks whose near edge is close (rho computed too small) and can over-refine elsewhere. Use
  distance to the closest point on the chunk's AABB — and include the height extent, or tall
  cliff chunks mis-measure when the camera is above/below them.
- **Normal aliasing at distance.** Correct geometric LOD with full-frequency normal maps gives
  sparkling, over-lit distant terrain; normal mip chains must roughen (specular AA / vMF-style
  normal-to-roughness — doctrine in `10`, BRDF math in the physically-based-rendering skill).
- **Morph factor mismatch between passes.** Any pass (shadow, depth, velocity) computing the
  morph factor even slightly differently (different camera constant, different LOD table)
  renders different geometry → acne, velocity garbage, TAA ghosting. One selection result,
  shared by all passes, per frame.
- **Verification**: hairline-crack sweeps, T-junction sparkle checks, and the pop-magnitude
  harness live in `11`. Run the crack sweep across the *full* distance range — morph-boundary
  cracks appear only at specific camera distances.

## Sources & provenance

| Claim | Tier |
|---|---|
| ROAM — Duchaineau et al. 1997, "ROAMing Terrain: Real-time Optimally Adapting Meshes" (IEEE Visualization) | **P** |
| Geomipmapping — W.H. de Boer 2000, "Fast Terrain Rendering Using Geometrical MipMapping" (self-published whitepaper) | **P** |
| Chunked LOD, radial screen-space error form, per-chunk geomorph, skirts — T. Ulrich 2002, "Rendering Massive Terrains Using Chunked Level of Detail Control" (SIGGRAPH course) | **P/T** |
| Geometry clipmaps — Losasso & Hoppe 2004 (SIGGRAPH); nested rings, transition regions | **P** |
| GPU clipmaps, toroidal texture updates, degenerate-triangle stitching — Asirvatham & Hoppe, GPU Gems 2 (2005) | **P** |
| CDLOD quadtree + per-vertex distance morph — F. Strugar, CDLOD whitepaper (~2009) | **P** |
| CBT/LEB — J. Dupuy 2020, "Concurrent Binary Trees (with application to longest edge bisection)", HPG | **P** |
| Compute-shader adaptive GPU tessellation precursor — Khoury, Dupuy & Riccio, GPU Zen 2 | **P** |
| rho = e·K/d projection with K = viewportHeight/(2·tan(fovY/2)) — standard LOD literature form | **P/F** |
| Perpendicular-error projection variant and its grazing-angle degeneracy | **F** |
| Watertight rasterization only guaranteed across shared-vertex edges; T-junction sparkle | **D** (D3D/Vulkan rasterization rules) + **F** (terrain-specific reading) |
| Skirt artifacts in SSAO/fog/shadows; skirts tolerate T-junctions | **F** |
| Index-buffer edge permutations + ≤1 level adjacency constraint | **F** (no canonical paper; standard practice) |
| Matched tessellation edge factors from edge-symmetric data; fractional partitioning for continuity | **D/F** (D3D11 tessellation docs + practice) |
| Dithered LOD cross-fade resolved by TAA | **F** |
| Vertex-pulled grids via SV_VertexID; heightmap displacement R16/R32F | **F** |
| Reuse main-view LOD selection for shadow passes | **F** |
| Physics bilinear vs render triangulation mismatch; diagonal orientation matters | **F** |
| Distance-to-closest-point (not center) for the LOD metric | **F** |
| "Chunked LOD is the ancestor of virtualized-geometry terrain" framing | **?** (interpretive) |
| Tess factor cap of 64 in D3D11 | **D** |
| Clipmap distance-only LOD wastes triangles vs quadtrees past ~20 km view range | **?** (directionally sound, threshold is judgment) |
| Hex triangulation options (corner-only ~2N / center-fan ~3N / flat prism) and amplitude trade-offs | **D** (terrain-architect `26`'s catalog, restated render-side; vertex counts are lattice arithmetic) |
