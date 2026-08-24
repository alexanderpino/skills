---
type: Reference
title: "Smooth Voxel Terrain: Isosurface Extraction & LOD"
description: "Smooth voxel terrain: isosurface extraction, the marching-cubes case count and its ambiguous faces, dual methods, and LOD across chunk seams."
tags: [terrain, voxel, isosurface, marching-cubes, dual-contouring]
status: stable
generated: { by: process:claude-code, at: 2026-08-23T18:35:25Z }
---
# Smooth Voxel Terrain: Isosurface Extraction & LOD

You are rendering a scalar field somebody else authored — the density/SDF comes from the
generation side (terrain-architect `24`, geological voids `11`); this chapter owns everything
after the field exists: extracting a mesh from it, keeping LOD seams closed, shading it, and
re-extracting it fast when the player digs. The core tension of the whole chapter is one
triangle-count-vs-correctness trade made three times: which extractor, which crack solution,
which re-mesh budget. Get the field representation wrong first and no extractor saves you.

Contents: [The field you render](#the-field-you-render) ·
[Extraction algorithms](#extraction-algorithms) ·
[LOD and the crack problem](#lod-and-the-crack-problem) ·
[Normals and materials](#normals-and-materials) ·
[The editing pipeline](#the-editing-pipeline) ·
[GPU extraction](#gpu-extraction) ·
[Hybrid worlds and when to choose smooth voxels at all](#hybrid-worlds-and-when-to-choose-smooth-voxels-at-all) ·
[Failure catalogue](#failure-catalogue) · [Sources & provenance](#sources--provenance)

## The field you render

The input contract is a **scalar field sampled on a uniform grid per chunk**: signed distance
(preferred) or unbounded density, with the surface at the zero crossing (or iso-value `c` —
normalise to zero at ingest and never carry `c` through the renderer). Everything downstream
assumes the field is *continuous across chunk borders*, which means chunks must be sampled with
a **1+ voxel apron** shared with neighbours — the same apron doctrine as tiled erosion
(terrain-architect `08`), for the same reason: derivatives and cell lookups at the border need
neighbour data, and recomputing them from a truncated domain produces seams (`11` here).

**Storage precision is a rendering decision, not just a memory one.**

| Format | Bytes/voxel | Behaviour |
|---|---|---|
| f32 SDF | 4 | Reference quality; wasteful at scale |
| f16 SDF | 2 | Fine for terrain; watch large-magnitude far-field values |
| 8-bit quantized, clamped to ±k voxels | 1 | Production default — **iff** the clamp band and quantization step are chosen together |
| 1-bit occupancy | ⅛ | Not a smooth-voxel input; extractors need gradient information |

The classic defect is **terracing from 8-bit quantization**: with the surface position
reconstructed by interpolating the two cell-corner values, quantizing those values snaps the
crossing point to ~256 discrete positions along the edge. On near-flat terrain the surface
becomes visible stair-steps — the isosurface twin of heightfield precision terracing. The fix
is to quantize *distance within a narrow band* (e.g. ±2 voxels mapped to [0,255]), giving
sub-voxel resolution of ~4/256 voxel — not to quantize a huge world-space range. Verify with a
near-flat slab at a shallow grazing angle; terracing hides on rough terrain and screams on flat.

**Narrow-band storage.** Almost all voxels are trivially inside or outside. Store per-chunk
uniformity flags (all-solid / all-empty chunks carry no voxel payload), and within mixed chunks
consider narrow-band schemes: only voxels within ±k of the surface carry real distances, the
rest carry the clamp value. This also gates extraction — homogeneous chunks skip meshing
entirely, which is most of your frame budget at planetary scale (`09`).

**Hermite data for sharp features.** Marching Cubes and Surface Nets need only corner scalars.
Dual Contouring additionally needs **hermite data**: for every grid edge that crosses the
surface, the exact crossing position *and the field normal at that crossing*. If the generation
side can evaluate the analytic gradient, capture it at write time; otherwise reconstruct via
central differences at the interpolated crossing (adequate, but blunts the sharp features DC
exists to preserve). Hermite data does not need dense storage — it is derivable on demand from
the scalar field except for the normals of *CSG-authored* sharp edges, which are exactly where
derived gradients are wrong. If sharp man-made/geological edits matter, the edit pipeline must
write hermite normals from the CSG primitive, not the blended field.

**Per-voxel material IDs** ride alongside density: one ID per voxel (not per corner), typically
u8/u16 into a material table. The renderer's job is deciding which of the (up to 8) corner-cell
materials a vertex inherits and how triangles blend them — see
[Normals and materials](#normals-and-materials).

**Pitfalls:** quantizing before the apron exchange (neighbours reconstruct different surfaces →
cracks); storing density in engine/format units instead of voxel-relative distance (breaks when
voxel size changes per LOD); forgetting that iso-value ≠ 0.5 conventions differ between the gen
tool and the renderer — normalise once at the boundary and write the convention down.

## Extraction algorithms

Three families matter in production. All walk the cells of the grid; they differ in *where the
vertex goes* and *which cells own triangles*.

**Marching Cubes (Lorensen & Cline 1987).** Primal method: vertices live **on grid edges**,
triangles live inside cells. Each cell's 8 corner signs form a 256-entry case index, reduced by
symmetry to 15 base cases; a triangle table maps case → edge triples. Vertex position is linear
interpolation along the crossing edge: `t = d0 / (d0 - d1)`.

⚠️ **"Fifteen" is a count under a *specific* symmetry group, and the literature quotes four
different numbers for this one algorithm.** Computed here by building the cube group from signed
permutation matrices and counting orbits of the 256 sign masks (`D`,
[`reference-impl/tables.py`](../reference-impl/tables.py), guarded by `validate_terrain.py`):

| symmetry allowed | classes |
|---|---|
| rotation + complement, **no reflection** | **15** — the familiar number |
| rotation + reflection + complement | **14** — two of the fifteen are mirror images and nothing else |
| rotation alone | 23 |
| rotation + reflection | 22 |

This is not pedantry: **an implementer copying a table whose author allowed a different group gets
a subtly different expansion**, and the symptom is holes in one configuration out of 256 — on some
meshes, sometimes. Check which group your source assumed before you check its triangles.

⚠️ **And the ambiguity is not a corner case.** Counted by enumeration: **120 of the 256
configurations carry at least one ambiguous face** — 47% — so "marching cubes sometimes leaves
holes" is a near-certainty on real data rather than bad luck. The raw table is
**ambiguous**: cases with diagonal corner pairs (face ambiguity, and the interior ambiguity of
case 4/13 families) can be triangulated two ways, and adjacent cells choosing inconsistently
punch holes in the mesh.

**Why the asymptotic decider closes the hole, in one property.** On a face, trilinear
interpolation restricts to a *bilinear* function whose contour is a hyperbola with a saddle at
`S = (f_a f_c − f_b f_d)/(f_a + f_c − f_b − f_d)`; the sign of `S` says which diagonal pair the
contour joins. The decisive part is that **`S` is a function of the shared face's four values
alone, and is invariant under the face's own half-turn** — so two neighbouring cells, which
enumerate that face starting from different corners, reach the *same* answer and cannot disagree.
Any per-cell choice, however consistent-looking, disagrees half the time. Both properties are
guarded rows. Production answer: use an extended, consistency-resolved table (the
asymptotic-decider / MC33-style corrected tables — resolve the ambiguous face by the sign of the
bilinear saddle point) or simply take Lengyel's published Transvoxel tables, which are
hole-free and come with the LOD transition tables you will need anyway (see next section).
Never hand-derive the tables; this is the single most re-fabricated data structure in graphics.
Take them from an authoritative source: Bourke's "Polygonising a Scalar Field" page carries the
classic edge/tri tables (by Cory Gene Bloyd) that most implementations trace back to
(https://paulbourke.net/geometry/polygonise/ — URL verified 2026-07), and transvoxel.org
carries Lengyel's corrected + transition tables. The cell convention those tables assume:

```
        4--------5          corners: bit i of the 8-bit case index     case index:
       /|       /|          edges:   12 edges, numbered per the           mask = 0
      7--------6 |                   table's convention — adopt it        for i in 0..7:
      | |      | |                   verbatim, do not renumber              if d[i] < iso:
      | 0------|-1          a corner inside the surface sets its              mask |= 1<<i
      |/       |/           bit; mask selects the tri-table row;
      3--------2            crossed edges get interpolated verts
```

The one non-negotiable: corner numbering, edge numbering, and winding are a *single convention
package* from whichever table you adopt — mixing Bourke corner order with another table's edge
order produces meshes that are subtly inside-out or hole-punched only on some cases (`11`).

**Surface Nets (Gibson 1998) / "naive surface nets".** Dual method: **one vertex per cell**
that has any sign change, placed at the average (or smoothed position) of that cell's edge
crossings; then for every grid **edge** with a sign change, emit a quad connecting the four
vertices of the cells sharing that edge. Consequences: no case tables at all, dramatically
fewer vertices than MC (one per cell vs up to ~3 per cell), no ambiguity holes by construction,
and the averaged placement acts as a low-pass filter — smoother, better-shaped triangles, ideal
for organic terrain. The cost: sharp features are rounded (the vertex is an average, not a
feature point), and the raw output can self-intersect on pathological fields since the vertex
is not constrained to produce non-overlapping quads. For smooth *natural* terrain with no CSG
hard edges, surface nets are the highest value-per-line-of-code extractor in this chapter.

**Dual Contouring (Ju, Losasso, Schaefer & Warren 2002).** Surface nets' topology with a
smarter vertex: place each cell's vertex at the minimiser of the **QEF** (quadratic error
function) over the cell's hermite samples — the point minimising Σ(nᵢ·(x-pᵢ))². Where the
crossings' normals agree (flat region) the QEF is rank-deficient and the minimiser is a plane
point; where they disagree (edge, corner) the minimiser snaps to the sharp feature. This is the
only mainstream extractor that reconstructs CSG-crisp cliff edges and carved tunnels' rims.

Two numerical/topological rules are non-negotiable:

1. **Solve the QEF by SVD with singular-value clamping.** Form `A x = b` from the hermite
   planes, solve via SVD, and zero (or damp) singular values below a threshold (~0.1 of the
   largest); otherwise near-planar cells are rank-deficient and the naive normal-equation solve
   fires the vertex kilometres away. Solve *relative to the cell's mass point* (mean of
   crossings), so the pseudo-inverse's minimum-norm bias pulls the vertex toward the cell, not
   toward the origin. Then **clamp the solved position to the cell bounds** — a clamped vertex
   is a slightly rounded feature; an unclamped runaway vertex is a spike through the world.
2. **Accept the manifold caveat.** Plain DC can emit non-manifold topology (a vertex shared by
   two disjoint surface sheets crossing one cell) and self-intersections. Manifold-preserving
   DC variants exist that split the cell vertex per surface component (attribution `?` —
   several papers claim the fix; verify before citing one). If the mesh feeds physics cooking
   or nav-mesh generation, either use a manifold variant, run a repair pass, or use surface
   nets/MC for the collision mesh and DC only for the visual (`11`).

**Dual/hybrid variants** (describe, don't over-attribute): *Dual Marching Cubes* denotes at
least two distinct techniques in the literature — one contouring on the dual of an adaptive
octree, one building MC-style patches over a dual grid to fix MC's ambiguity — attribution and
which-is-which `?`; treat the name as ambiguous in reviews. *Cubical marching squares* and
other crack-free adaptive primal schemes exist (`?` attribution). In practice the 2026 shipping
set is: MC/Transvoxel, surface nets, DC — pick from these unless a paper-specific requirement
forces otherwise.

| | Marching Cubes | Surface Nets | Dual Contouring |
|---|---|---|---|
| Vertex placement | Edge interpolation | Cell average of crossings | QEF minimiser (hermite) |
| Sharp features | No (rounded) | No (rounded, smoothest) | Yes |
| Manifold output | Yes with corrected tables | Yes topologically; can self-intersect | No guarantee; variants `?` |
| Vertex/tri counts | Highest (up to 3 verts/cell, slivers) | Lowest, well-shaped quads | Low, like nets |
| Input needed | Corner scalars | Corner scalars | Corner scalars + hermite |
| LOD stitching story | **Transvoxel — the canonical solved path** | Ad-hoc (skirts/borders) | Octree stitching — notoriously hard |
| Implementation difficulty | Low (tables published) | Lowest | High (QEF + topology) |
| GPU friendliness | Excellent (table-driven, no cross-cell deps) | Good (2-pass: verts then quads) | Moderate (QEF solve per cell, hermite fetch) |

Decision rule: **surface nets** for smooth natural terrain and fast iteration; **MC +
Transvoxel** when you need the mature, documented LOD story and don't need sharp features;
**DC** only when CSG-sharp editing is a core mechanic and you have budget for the QEF and
manifold work. Do not pick DC "because it's the best one" — it is the most expensive answer to
a question (sharp features) most terrain games are not asking.

## LOD and the crack problem

The standard scaffold: **chunked uniform grids under an octree** (or distance-banded chunk
grid). Each chunk extracts at a resolution set by its LOD level — level *n* samples every 2ⁿth
voxel. Neighbouring chunks at different levels disagree about where the surface crosses the
shared face, because the coarse chunk never sampled the fine chunk's interior crossings. That
disagreement is **the crack problem**, and it is the dominant engineering cost of smooth-voxel
LOD. Restrict the tree so adjacent chunks differ by **at most one level** — every solution
below assumes 2:1 balance, and enforcing it costs far less than generalising past it.

**Transvoxel (Lengyel, dissertation ~2010; transvoxel.org).** The canonical answer for MC.
Mechanism: a chunk that borders a coarser neighbour shrinks its regular cells slightly along
that face and inserts a layer of **transition cells** — flat, half-voxel-thick cells whose
coarse-facing side has the 4 corner samples of the coarse grid and whose fine-facing side has
the full 9 samples (3×3) of the fine grid. A transition cell therefore has 9 distinct sample
locations → 2⁹ = 512 sign cases, reduced by symmetry to a published set of transition classes
with their own vertex/triangle tables, exactly analogous to the regular MC tables. The
transition layer's triangles are *guaranteed* to meet the fine mesh on one side and the coarse
face's crossings on the other — watertight by table construction, not by post-hoc welding. Cost:
a second, larger table set, per-face "transition mask" bookkeeping on each chunk, and the tables
assume 2:1. This is solved, documented, and shipped in multiple engines; take the tables from
the published source, do not re-derive.

**Skirts.** Extrude the mesh's boundary edge loop downward/inward along the face (or along
-gradient) by ~1 coarse voxel, hiding the crack behind overlapping geometry. Pros: trivial,
extractor-agnostic, works for surface nets and DC too. Cons: it *hides* cracks rather than
closing them — visible at grazing angles and silhouettes, double-shaded overlap, texture
stretching on the skirt, garbage for collision (never cook skirts into physics), and lighting
discontinuity where skirt normals diverge. Acceptable for distant LOD rings and prototypes;
teams that ship skirts up close always regret it in the silhouette review.

**DC octree stitching.** Dual contouring on an adaptive octree can produce crack-free
multi-resolution meshes by recursively contouring across cell faces/edges of mixed depth
(`faceProc`/`edgeProc` recursion in the original paper's framing). Doctrine warning: this is
**notoriously fiddly — a graveyard of hobby voxel engines**. The recursion is easy to get
subtly wrong (missing face orientations, wrong child pairings), debugging is miserable because
errors present as sparse pinholes at specific depth transitions, and the simplification side
(collapsing octree leaves while keeping the QEF error bounded *and* topology safe) is a second
project on top. If your team has not shipped it before, the risk-adjusted choice is chunked
Transvoxel or per-chunk nets with border constraints, not the elegant octree.

**Clipmap-style concentric LOD.** Concentric boxes of decreasing voxel resolution centred on
the camera, re-extracted as the camera crosses re-centre thresholds — the volumetric analogue
of geometry clipmaps (`01`). Pairs naturally with GPU extraction (fixed voxel budget per ring,
no octree management). Ring boundaries still need Transvoxel-style transition cells or skirts;
crossing a ring boundary re-extracts a shell, so budget for the burst (`06` streaming doctrine).

**Geomorphing.** On heightfield grids (`01`) geomorphing is trivial because vertex identity is
implicit in the grid. On extracted isosurfaces there is **no vertex correspondence** between
LOD levels — different levels have different topology and counts, so "morph vertex to its
coarse position" is undefined. Workable approximations: morph fine vertices toward the coarse
*surface* by projecting along the field gradient (needs field access in the vertex shader, or a
baked morph-target offset computed at extraction by sampling the coarse field); or fade via
dithered cross-blend of the two meshes for a few frames. Both cost more than they do on grids;
many shipped games simply accept a well-budgeted pop hidden by distance and fog. Do not promise
geomorphing in a smooth-voxel schedule without prototyping the correspondence answer first.

**Pitfalls:** unbalanced trees breaking Transvoxel's 2:1 assumption (holes exactly at 4:1
seams); extracting LOD *n* from a *re-sampled coarse field* instead of decimating sample stride
on the same field (surfaces drift between levels → cracks even with transition cells);
forgetting that a chunk's transition mask changes when its *neighbour* changes LOD, requiring a
re-extract of the border layer, not just the neighbour.

## Normals and materials

**Gradient normals, not face normals.** Compute the vertex normal as the normalised negative
central difference of the field at the vertex position (`n = -normalize(∇d)`, sign per your
inside-negative convention). Gradient normals are C⁰ across triangle, chunk, *and LOD*
boundaries because they come from the shared field, not from the level-dependent triangulation
— they are the cheapest LOD-stability win in this chapter. Face/averaged-face normals encode
the triangulation and therefore pop at every re-extraction and seam at every chunk border.
Requirements: the apron must be wide enough for the stencil (±1 voxel beyond any vertex —
central differences at a border vertex read neighbour voxels), and take the gradient of the
*continuous* field, never of quantized-then-dequantized data at coarse step (quantization noise
amplifies through the derivative — same rule as terrain-architect's "never take derivatives of
quantized fields").

**Materials.** The voxel grid stores material IDs; the mesh needs per-vertex material
influence. Standard pipeline: each vertex gathers the material IDs of its owning cell's solid
corners/voxels, producing per-vertex weights; fragment shading samples a **texture array** by
material index with **triplanar projection** (no UVs exist on an isosurface — projection math,
blend-zone width, and normal-map handling live in `07`). Naive interpolation of material *IDs*
is meaningless (blending ID 3 and ID 7 is not material 5) — interpolate *weights*, never IDs.

The classic bandwidth trick (**F**, folklore — widely shipped, no canonical paper): limit each
*triangle* to at most 3 materials, assign one material per corner, and pass barycentric-style
weights so the fragment shader blends exactly its triangle's three materials from the array.
Costs a triangle split where 4+ materials meet in one cell (rare) and buys a fixed, small
per-fragment sample count.

**Hard geological boundaries** (strata lines, ore veins, cave walls from terrain-architect
`11`) should *not* be blended over a full voxel — a 1-voxel smear across a stratum contact
reads as mud. Options: snap weights (sharpen the blend curve, e.g. `pow`/smoothstep-threshold
on weights), duplicate vertices along the material boundary for a hard shading edge, or carry a
per-material "blend hardness" scalar into the splat. Decide per material pair; sand↔grass
blends, rock-stratum↔rock-stratum cuts.

**Pitfalls:** normals recomputed after an edit using stale apron data (lighting seam exactly on
the chunk border — see `11`); triplanar sampling the material of the *vertex-interpolated*
dominant ID instead of blending (flicker at boundaries); gradient normals from an f16/8-bit
field at large clamp bands (banding in the normal → shading terraces even when geometry is fine).

## The editing pipeline

Edits are **CSG operations on the field**, never on the mesh: carve = `d = max(d, -sphere(p))`
(subtract), add = `d = min(d, sphere(p))` (union), with smooth variants (smooth-min) for soft
brushes. The mesh is a cache of the field; the field is the truth. This is the whole reason the
representation exists — never special-case "dig a hole" as mesh surgery.

The re-extraction loop, same budget/queue doctrine as blocky voxels (`04`):

```
apply CSG to field over brush AABB
mark dirty: every chunk whose sample domain (including apron!) intersects the AABB
enqueue dirty chunks: priority = f(distance to camera, is-visible, edit recency)
per frame: remesh at most N chunks / M ms; coalesce repeated dirties on the same chunk
swap mesh atomically per chunk (build off-thread, swap on-thread)
```

The apron clause is the classic miss: an edit within k voxels of a chunk border dirties the
*neighbour* too, because the neighbour's border cells and gradient stencils read those voxels.
Miss it and you get geometry cracks and lighting seams that appear only after edits near
borders — the signature bug of every first-draft voxel editor (`11`).

**Collision latency.** The visual remesh and the physics remesh are different deadlines. Visual
can be 1–3 frames late behind a swap; collision cooking (convex/BVH build in the physics
engine) is often slower than extraction itself. If the player digs and immediately walks in,
stale collision means walking on air or clipping into ground. Production patterns: cook
collision for the edited chunk *synchronously or highest-priority* while visual chunks queue;
keep the character controller on a locally-queried field (sphere-trace the SDF directly for
ground contact) so gameplay never waits on cooked meshes; or briefly constrain movement into
freshly-edited volumes until cooking lands. Also decide *which* mesh cooks — a lower-LOD or
nets-extracted collision mesh is cheaper to cook and physics does not care about your DC
feature vertices (and cares a lot about their non-manifoldness).

**Undo** is field-domain, not mesh-domain: before applying a brush, snapshot the affected
voxels (AABB region delta, compressed — deltas are tiny because brushes are local) and push
onto the undo stack; undo = write the delta back and dirty the same chunk set. Never attempt
mesh-level undo; you cannot reconstruct the field from the mesh.

**Pitfalls:** remeshing on the edit thread (hitch per brush stroke); not coalescing dirties
during a drag (queue floods with N remeshes of the same chunk); undo deltas taken *after* the
CSG (snapshot order bug — you saved the post state); smooth-min brushes silently violating the
narrow band clamp so distant voxels change and dirty far more chunks than the brush AABB.

## GPU extraction

Marching cubes is embarrassingly parallel and the compute-shader pipeline is standard:

```
pass 1  classify: per cell, compute case index; write triangle/vertex counts
pass 2  prefix sum (scan) over counts → output offsets; total → indirect args buffer
pass 3  generate: per active cell, interpolate vertices + gradient normals,
        write into vertex/index buffers at scanned offsets
draw    DrawIndexedInstancedIndirect / vkCmdDrawIndexedIndirect from the args buffer
```

The load-bearing property is **no readback**: counts feed an indirect draw, so the CPU never
learns the triangle count and the frame never syncs on extraction. Keep per-chunk output
buffers sized to worst-case-observed with overflow detection (clamp + flag for CPU-side
re-allocation next frame), or sub-allocate from a large pool driven by the scan totals.

**When GPU extraction wins:** high edit frequency (dozens of chunks dirty per frame — digging
machines, deformation-heavy gameplay), dense fields already resident on GPU (the generator ran
in compute — terrain-architect `15`), clipmap schemes with predictable fixed budgets, and any
time the mesh is *only* rendered. **When CPU wins:** you need the mesh bytes anyway for
collision cooking, nav-mesh, serialisation, or server authority (a GPU mesh you must read back
loses its whole advantage); modest edit rates where a worker-thread pool already hits budget;
platforms where async compute contends with rendering. Many shipping titles split: GPU for the
visual remesh of the near ring, CPU for the collision mesh of the same chunks — accepting the
double extraction because the consumers genuinely differ.

**2026 frontier:** mesh-shader direct expansion — classify in an amplification/task shader,
expand each active cell's triangles in the mesh shader, no intermediate vertex buffer at all —
and workgraph-driven extraction. Real wins reported in engine talks, but no settled canonical
pipeline yet; treat specific claimed speedups as `?`/F and prototype before committing. The
compaction pipeline above remains the safe default. Cluster/meshlet integration of extracted
geometry (feeding chunks into a GPU-driven meshlet pipeline) is `02`'s business; culling of the
chunk set is `08`'s.

## Hybrid worlds and when to choose smooth voxels at all

A volumetric field costs O(N³) against a heightfield's O(N²); you pay it *everywhere* to get
caves, overhangs, and dig-anywhere *somewhere*. Interrogate the requirement before adopting:

| Requirement | Right substrate |
|---|---|
| No caves/overhangs, no digging | Heightfield LOD (`01`) or cluster pipeline (`02`) — full stop |
| Blocky aesthetic, cubic edits | Blocky voxel (`04`) — cheaper meshing, different culture |
| Caves/overhangs authored, not player-edited | Heightfield + authored mesh set-pieces, or localised voxel patches |
| Dig-anywhere, smooth organic terrain | This chapter |
| Planet-scale + all of the above | This chapter + `09`'s precision and `06`'s streaming, and a large team |

The production compromise is the **hybrid world**: heightfield terrain (`01`/`03`) for the vast
open surface, smooth-voxel volumes only where volumetric features exist — cave systems,
overhang cliffs, dig zones. Conversion contract at the boundary: the voxel field must ingest
the heightfield as its initial SDF (`d = (z - h(x,y))·cosθ` approximation, or a proper
narrow-band redistance) with **matching sample alignment at the boundary shell**, and the
seam is hidden by construction — the voxel region's boundary surface must reproduce the
heightfield surface exactly (extract with boundary samples pinned to heightfield-derived
values), or be masked by geometry/blend volumes. Materials must map across the boundary
(splat weights ↔ voxel material IDs, `07`), and lighting must not change regime at the seam
(`10`). Games that ship "dig anywhere" on top of a heightfield are usually shipping exactly
this: a lazily-allocated voxel patch that overrides the heightfield where edits exist.

## Failure catalogue

Symptom → mechanism → minimal fix. The `11` chapter carries the full cross-cutting catalogue;
these are the smooth-voxel signatures.

| Symptom | Mechanism | Minimal fix |
|---|---|---|
| Pinholes/cracks exactly at LOD boundaries | Coarse/fine chunks disagree on face crossings; no transition handling, or 2:1 balance violated | Transvoxel transition cells; enforce 2:1 tree balance; re-extract border on neighbour LOD change |
| Sparse holes in flat single-LOD mesh | MC ambiguous cases resolved inconsistently across cells | Corrected/consistency-resolved tables (asymptotic decider / Transvoxel tables); never hand-rolled tables |
| Physics/nav cooking fails or ghost collisions | Non-manifold DC output, self-intersections, or skirts cooked into collision | Cook from nets/MC mesh; manifold-DC variant or repair pass; exclude skirts from physics |
| Spikes shooting out of terrain | QEF solved without SVD clamping; vertex outside cell | SVD with singular-value clamp, solve about mass point, clamp result to cell AABB |
| Stair-step shading/geometry on flat ground | 8-bit quantized density over too-wide a band; or gradient of quantized field | Quantize narrow-band distance only; widen precision; compute normals from unquantized field |
| Lighting seam on chunk borders (geometry fine) | Normals recomputed without apron / from stale neighbour data after edit | ±1 voxel apron for gradient stencil; dirty neighbours whose apron overlaps the edit AABB |
| Geometry crack appears only after edits near borders | Edit dirtied the owning chunk but not the neighbour whose apron it touched | Dirty every chunk whose sample-domain-plus-apron intersects the brush AABB |
| Whole terrain shimmers/pops during digging | Full-chunk visual pop on remesh swap each frame of a drag | Coalesce dirties, swap at most once per chunk per N frames, consider border-preserving remesh |
| Sliver triangles, z-fighting, degenerate normals | Crossings extremely close to cell corners (near-zero-crossing cells) | Snap crossing `t` to [ε, 1−ε] or weld vertices within ε of corners; drop zero-area triangles |
| Player falls through freshly dug hole | Collision cook lags visual remesh | Priority/sync collision cook for edited chunk; or query the SDF directly for ground contact |
| Surface drifts between LOD levels even with transitions | LOD sampled from a re-generated coarse field, not strided samples of the same field | Extract every LOD from the same field at stride 2ⁿ |

## Sources & provenance

- **P** Lorensen, W. & Cline, H. — *Marching Cubes: A High Resolution 3D Surface Construction
  Algorithm*, SIGGRAPH 1987. The 15 base cases and table-driven extraction.
- **P** Nielson & Hamann — *The Asymptotic Decider*, IEEE Visualization 1991: resolving MC face
  ambiguity by the bilinear saddle sign. (Extended complete-case tables, "MC33", follow-on
  literature — attribution of the definitive corrected table `?`.)
- **F/D** Bourke, P. — *Polygonising a Scalar Field* (1994; tables by Cory Gene Bloyd) — the
  canonical public MC edge/tri tables most implementations trace back to. URL verified 2026-07:
  https://paulbourke.net/geometry/polygonise/
- **P** Gibson, S. — *Constrained Elastic Surface Nets*, MICCAI 1998. Origin of surface nets;
  the "naive surface nets" simplification used in games is folklore-named (**F**).
- **P** Ju, T., Losasso, F., Schaefer, S. & Warren, J. — *Dual Contouring of Hermite Data*,
  SIGGRAPH 2002. QEF vertex placement, sharp features, octree contouring recursion.
- **D** Lengyel, E. — *Voxel-Based Terrain for Real-Time Virtual Simulations* (dissertation,
  ~2010) and transvoxel.org: the Transvoxel algorithm, transition-cell tables, and the
  hole-free regular-cell tables.
- **?** Manifold dual contouring variants (per-component cell vertices) — technique described
  above is real and published; specific attribution intentionally unpinned.
- **?** "Dual Marching Cubes" — name collides across at least two distinct published methods;
  do not cite without checking which paper a claim means.
- **F** Three-materials-per-triangle barycentric splatting; skirts for crack hiding; GPU
  classify→scan→generate MC pipeline shape (widely shipped and talked about, no single
  canonical paper).
- **T/?** Mesh-shader / workgraph direct isosurface expansion — discussed in recent engine and
  vendor talks; no settled canonical reference, performance claims unverified here.
- **F** SVD-with-clamping QEF solve and mass-point bias — standard practice descending from the
  DC paper's discussion and years of implementation folklore.
