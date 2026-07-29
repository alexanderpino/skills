# Cluster / Meshlet Virtualized Geometry for Terrain

The Nanite family: fixed-size triangle clusters in a simplification DAG, a GPU-selected cut whose
screen-space error stays under a pixel, and a visibility-buffer raster path that makes triangle
count nearly irrelevant. This chapter owns the representation, the build pipeline, the runtime cut,
and the decision of when terrain should be a cluster mesh at all. Grid-native LOD stays in `01`,
cull/submission mechanics in `08`, Unreal specifics in `03`, shadow depth in `10`.

Contents: [The idea](#the-idea-a-dag-of-cluster-groups) ·
[The runtime](#the-runtime-cull-cut-rasterize-shade) · [Streaming](#streaming-cluster-pages) ·
[Terrain fit](#terrain-fit-when-to-convert-a-heightfield) ·
[DIY outside Unreal](#diy-outside-unreal-meshlets-and-the-build-pipeline) ·
[Shadows](#shadows-why-this-pairs-with-virtual-shadow-maps) ·
[Comparison & decision](#comparison--decision) · [Pitfalls](#pitfalls) ·
[Sources & provenance](#sources--provenance)

## The idea: a DAG of cluster groups

Take an arbitrary mesh — no grid assumption — and split it into **clusters** of a fixed triangle
budget (~128 tris in Nanite; 64–256 is the practical family range). Clusters are the atomic unit of
everything downstream: culling, LOD selection, rasterization, streaming. Then build coarser levels:

1. **Group** a set of adjacent clusters (a few dozen; Nanite groups up to ~32) by min-cut graph
   partition on shared boundary edges, so groups have small perimeters.
2. **Merge** the group into one mesh and **simplify** it to ~half the triangles with the group's
   *outer boundary edges locked* (QEM with locked border, see the build sketch below).
3. **Re-split** the simplified mesh into new ~128-tri clusters. These are the parents.
4. Repeat on the new level until one root cluster remains.

**Why this is a DAG and not a tree.** The re-split in step 3 is followed, one level up, by a *new*
grouping that ignores parentage: the next level's groups draw clusters descended from many previous
groups. A cluster therefore has multiple ancestry paths — the structure is a directed acyclic
graph. This is not incidental; it is the load-bearing trick. In a tree (BVH-style: split space,
simplify each node independently), node boundaries are the *same edges at every level*. Locked
boundary edges are never simplified, so after k levels the mesh is a web of full-resolution seams —
the LOD scheme fails exactly where meshes are expensive. Group-boundary **alternation** guarantees
an edge locked at level L falls in some group's *interior* at level L+1 and gets simplified there.
No edge is locked forever; boundaries migrate; the DAG is the price and the point.

**Monotonic error, group-shared.** Each simplification records an error (max surface deviation, in
object units). Force monotonicity: `G.error = max(simplifyError, max(child cluster errors))`, and
force the group's LOD bounding sphere to enclose all child LOD spheres. Store the group's
error/bounds in two places — as **self** data on the parent clusters it produced, and as **parent**
data on the child clusters it consumed. Level-0 clusters get self error 0; roots get parent error
∞.

**The runtime cut.** Every cluster can now decide *in isolation, in parallel*:

```
projSelf   = ProjectErrorToPixels(c.selfError,   c.selfBounds,   view)   // conservative
projParent = ProjectErrorToPixels(c.parentError, c.parentBounds, view)
onCut      = (projSelf <= tau) && (projParent > tau)                     // tau ~ 1 px
```

Monotonic error + monotonic bounds means `projParent >= projSelf` always, so exactly one level
passes per ancestry path — the cut is well defined with no sequential traversal needed to agree on
it. And because every cluster in a group shares identical self data (and its siblings-by-parentage
share identical parent data), all clusters split from one group flip together: **the LOD transition
always falls on a group boundary, whose edges were locked when the coarser side was built**. The
two sides are bitwise the same vertices. Crack-free by construction — no skirts, no stitching, no
T-junction tables. This is `01`'s screen-space-error controller generalized from grids to arbitrary
meshes: same τ-vs-projected-error contract, but the "grid level" became a DAG cut and the crack
handling moved from runtime stitching to build-time boundary locking.

Default τ is ~1 pixel of error (UE: `r.Nanite.MaxPixelsPerEdge`), at which point LOD is visually
lossless and pop is sub-pixel — TAA absorbs it. Raising τ is the knob for cheaper platforms.

## The runtime: cull, cut, rasterize, shade

### Per-cluster culling and hierarchy traversal

Clusters carry: bounding sphere/AABB, normal cone (axis + apex angle for backface rejection: if the
whole cone faces away, the cluster cannot contribute front faces), and the LOD error data above.
Culling is frustum + cone + **two-phase HiZ occlusion**: phase 1 tests against last frame's
reprojected HiZ and draws survivors; a fresh HiZ is built; phase 2 retests what phase 1 rejected
and draws the disoccluded remainder. Mechanism detail, false-positive behavior, and the HiZ build
live in `08` — the interaction to know here is that occlusion runs *per cluster and per hierarchy
node*, so an occluded mountain costs a few node tests, not a mesh's worth of vertex work.

Traversal of the cluster/group hierarchy runs on GPU. Naive dispatch-per-level serializes on
barriers and idles at the narrow top of the hierarchy; the production pattern is
**persistent-threads style**: a worker grid loops on a global multi-producer multi-consumer work
queue, popping nodes, testing cull + `projParent > tau`, pushing children or emitting cut clusters
to the raster lists. One dispatch, no per-level sync, load-balanced regardless of hierarchy shape.

### Hardware vs software rasterization, into a visibility buffer

The cut produces clusters whose triangles are *roughly pixel-scale by design* — that is what a
~1 px error target does. Hardware rasterizers are inefficient there (fine-grained 2×2 quad
scheduling, fixed-function setup per tiny triangle), so the pipeline splits per cluster by
projected size: big clusters go through the hardware rasterizer (mesh/primitive shader path);
pixel-scale clusters go to a **compute rasterizer** that iterates the (tiny) triangle's pixels
in-thread and writes with a 64-bit atomic:

```
u64 payload = (u64(depth) << 32) | (visibleClusterIdx << 7) | triIdx;
InterlockedMax(visBuffer[pixel], payload);       // depth test + write, one atomic
```

Depth in the high bits makes `InterlockedMax` a depth test; the low bits are the **visibility
buffer** payload (Burns & Hunt 2013): per pixel, which triangle of which cluster won. No attribute
interpolation, no material evaluation, no overshading during raster.

### Deferred material evaluation

Shading is a separate full-screen pass (or per-material passes selected via a material depth /
tile-classification trick): fetch the cluster+triangle ID, load the three vertices, recompute
barycentrics analytically from the pixel ray, interpolate attributes, compute analytic derivatives
for texture LOD (screen-space differencing of IDs does not work — neighbors are different
triangles), then run the material into the G-buffer or forward path. BRDF and material math belong
to the physically-based-rendering skill; terrain material *binding* — which layers, how virtual
texturing feeds this pass — is `07`. The consequence that matters: material cost is per *pixel*,
decoupled from triangle count, which is the second half of why triangle count stops mattering.

## Streaming: cluster pages

The full DAG of a dense mesh does not fit in memory and never needs to: the cut only touches
clusters near the current error band.

- **Pages.** Clusters are packed offline into fixed-size pages (~128 KB in Nanite) grouped by
  hierarchy locality, so a cut at a given error touches few pages. The top of the DAG is packed
  into **root pages that are always resident** — every object is drawable at *some* quality with
  zero streaming latency.
- **GPU feedback.** Traversal *is* the request generator: when the cut wants to descend into
  clusters whose page is not resident, it records the page ID + priority (how far projected error
  overshoots τ) into a request buffer and draws the coarser resident ancestor instead. Readback,
  dedupe, prioritize, load into a **fixed-size pool**, evict LRU. Misses degrade quality smoothly —
  never holes, never hitches, because the fallback is structural, not exceptional.
- **Fixed budget.** The pool size caps memory regardless of scene density; pressure shows up as
  error above τ, which is measurable (`11`) rather than as OOM.

**Interaction with tiled world streaming (`06`).** These are two layers, not competitors. World
streaming owns *existence*: which terrain components/cells/actors are loaded at all, driven by
distance rings and gameplay. Cluster paging owns *density within* a loaded object, driven by
screen-space error. Do not double-manage: if the world streamer tries to also swap "LOD meshes" of
a cluster-virtualized object it fights the DAG cut and re-creates pop. Keep world cells coarse
(existence + collision + gameplay data), let the DAG handle every visual density decision, and size
the two budgets separately — page pool pressure and cell residency pressure fail differently and
must be telemetered separately (`11`).

## Terrain fit: when to convert a heightfield

Unreal's Nanite Landscape converts each landscape component's heightfield patch into a cluster
mesh offline and renders it through this pipeline (engine specifics, rebuild triggers, and the
component workflow: `03`). The general decision is engine-independent:

**What conversion buys:**

- **One representation for everything.** Cliffs, overhangs, arches, cave mouths, blended rock
  meshes — no more "heightfield terrain + separate cliff meshes with a seam to hide" (`01`'s
  structural blind spot). The sculpted result is the rendered result.
- **No authored LODs, no LOD tuning.** The DAG is automatic and near-lossless at τ≈1 px; the
  entire `01` apparatus of morph regions, stitching, and per-chunk LOD bias disappears.
- **Kilometer-scale sub-meter detail** with cost proportional to pixels, not to source resolution;
  render density fully decoupled from the source grid step.

**What it costs — and the cost is structural, not incidental:**

- **Memory.** A heightfield is the cheapest terrain "compression" there is: implicit XY, implicit
  topology, one 16-bit scalar per two rendered triangles, and the same array serves collision,
  gameplay queries, and painting. A cluster mesh stores explicit (quantized) positions plus the
  DAG plus per-cluster metadata — competitive per-triangle after aggressive quantization, but it
  is a *second copy*: you keep the heightfield anyway for collision and gameplay, so conversion is
  strictly additive on disk and in the streaming budget.
- **Edits require offline rebuild.** The DAG is a global-ish offline artifact (per-component
  builds bound the blast radius, but a rebuild is still an authoring-time operation, not a frame
  operation). Runtime-destructible or player-editable terrain is therefore the wrong customer —
  route it to blocky voxels `04` or smooth isosurfaces `05`, whose whole design center is cheap
  local re-mesh.
- **Aggregates are a poor fit.** Grass, dense foliage, scree fields: simplification cannot merge
  topologically disconnected blades/leaves without destroying them, so the DAG bottoms out
  shallow; and at pixel scale aggregates become massive overdraw in the software rasterizer (see
  Pitfalls). Keep aggregates on the instanced/impostor path (`08`).
- **Deformation is bounded, not free.** WPO/vertex animation must be declared with a max
  displacement so cluster bounds can be inflated for culling; large or unbounded deformation
  guts culling efficiency or clips geometry. Skeletal-style deformation of terrain is out.

Rule of thumb: **static sculpted terrain → convert; anything that changes at runtime → don't.**

## DIY outside Unreal: meshlets and the build pipeline

The pipeline is reproducible on any DX12 Ultimate / Vulkan mesh-shading stack; none of it is
engine magic.

**Runtime substrate.** Mesh shaders (D3D12 mesh shader tier / `VK_EXT_mesh_shader`) consume
meshlets directly — typical limits ~64–128 vertices, ~124–256 primitives per meshlet. The
amplification/task stage is where per-meshlet frustum/cone/HiZ culling runs on the hardware path;
the compute rasterizer is a plain compute pass and needs 64-bit image atomics (widely available;
have a 32-bit split fallback plan or drop SW raster on hardware without it).

**Meshlet building.** Use meshoptimizer as the reference: `meshopt_buildMeshlets` produces
spatially coherent clusters under explicit vertex-reuse limits (vertex budget matters as much as
the triangle budget — locality of the shared-vertex set is what makes clusters compress and
transform well), and `meshopt_computeMeshletBounds` emits the sphere + normal cone used for
culling. Simplification with locked borders: `meshopt_simplify` with `LockBorder`, or your own QEM
(Garland–Heckbert) with boundary vertices constrained.

**Why a naive meshlet LOD tree fails.** The tempting shortcut — per terrain chunk, build meshlets
at several precomputed LODs and swap per chunk — reintroduces `01`'s crack problem exactly:
adjacent chunks at different LODs disagree along the shared edge, and now you have no grid
structure to stitch with. You will end up hand-rolling skirts around free meshes, which is worse
than the grid version. The group/simplify/re-split alternation *is* the fix; it is not optional
polish, it is the part that makes cluster LOD sound.

**Offline build sketch:**

```
build(mesh):
    level = Clusterize(mesh, MAX_TRIS)                    # level 0; selfError = 0
    while |level| > 1:
        next = []
        for G in PartitionGroups(level, GROUP_SIZE):      # min-cut graph partition on shared
            M          = Merge(clusters in G)             #   boundary edges (METIS-class)
            S, eSimp   = SimplifyQEM(M, tris(M)/2, lock = outerBoundaryEdges(G))
            G.error    = max(eSimp, max c.selfError for c in G)      # monotonic error
            G.bounds   = enclosingSphere(c.selfBounds for c in G)    # monotonic bounds
            for c in G:      c.parentError, c.parentBounds = G.error, G.bounds
            kids = Clusterize(S, MAX_TRIS)
            for k in kids:   k.selfError,   k.selfBounds   = G.error, G.bounds
            next += kids
        level = next                                      # next PartitionGroups regroups kids
    root.parentError = INF                                #   across parentage → the DAG
```

Persist per cluster: cull bounds (tight), LOD bounds + self/parent error (monotonic, group-shared),
normal cone, quantized vertices + local indices, material range, page ID. Build a coarse BVH over
groups for the traversal entry point. Validate offline: monotonicity asserts on every edge of the
DAG, and a cut-watertightness pass (pick random τ and views, render cluster IDs, flood-fill for
background bleed through the surface — `11` owns the harness).

If simplification stalls (error explodes at some level, group perimeters stop shrinking), the
usual causes are: groups too small (boundary-to-interior ratio too high), degenerate/non-manifold
input from the heightfield-to-mesh step (weld first — terrain-architect `27` owns the export
contract), or aggregate-like disconnected components that should not be in the DAG at all.

## Shadows: why this pairs with virtual shadow maps

Classic CSM re-renders the scene N times into N cascades. With megageometry that is untenable —
you would pay the full cut + raster N more times per light, at shadow resolutions that want *more*
geometry than the main view, not less. The production answer is **virtual shadow maps**: a huge
virtual shadow page table per light, physical pages cached across frames, only pages invalidated
by movement or newly needed by the camera get re-rendered — and each page render reuses this exact
cluster pipeline (its own cut at the page's effective resolution, its own HiZ, SW raster for tiny
triangles). Cached static terrain pages make kilometer shadow ranges affordable. Page management,
invalidation rules, filtering, and light-type specifics: `10`. The coupling to remember here:
VSM assumes it can re-render *small subsets* cheaply — which only holds because cluster culling is
fine-grained. Bolting VSM onto a monolithic-draw terrain forfeits the entire benefit.

## Comparison & decision

| Axis | `01` grid LOD (clipmap/CBT/quadtree) | Cluster DAG (this chapter) | Blocky voxel `04` | Smooth isosurface `05` |
|---|---|---|---|---|
| Source data | Heightfield (implicit topology) | Arbitrary mesh (explicit) | Voxel grid | SDF / density grid |
| Overhangs & caves | No (skirt hacks only) | Yes, native | Yes | Yes |
| Runtime edits | Cheap (rewrite samples) | No — offline rebuild | Cheap, local | Moderate, local re-mesh |
| Memory for pure terrain | Cheapest possible | 2nd copy + DAG overhead | High raw, compresses well | High |
| LOD mechanism | Grid levels + SSE (`01`) | DAG cut + SSE, ~1 px | Chunk LOD / distance | Chunked contouring LOD |
| Crack handling | Runtime stitch/morph/skirt | Build-time boundary locks | Face culling rules | Transition cells / stitching |
| Cull granularity | Patch/chunk | Cluster (~128 tris) | Chunk / region | Chunk |
| Aggregates (grass, scree) | Separate instanced path | Poor fit — separate path | Blocks are the aggregate | Poor fit |
| Best 2026 fit | Streamed procedural, huge worlds, editable heightfields | Static sculpted/photogrammetric terrain, hero cliffs | Buildable/destructible worlds | Smooth diggable terrain |

Decision doctrine for 2026: **static, sculpted, art-directed terrain → cluster DAG** (in UE, via
`03`; elsewhere, DIY above). **Streamed procedural or runtime-editable terrain → heightfield `01`
or voxels `04`/`05`.** The hybrid is legitimate and common: heightfield base via `01` for the
editable/procedural bulk, cluster-DAG meshes for cliffs, rock formations, and hero landmarks —
but then the seam between the two representations is yours to own (material match via `07`,
intersection hiding, consistent shadowing via `10`), so keep the boundary in steep rock where
blending is forgiving. At planetary scale, add `09`'s precision regime on top of either.

## Pitfalls

- **Cluster bounds vs displacement.** Any material displacement/WPO applied after the offline
  build moves geometry the culler and the LOD projector never saw. Symptoms: clusters vanish at
  frustum/HiZ edges, shadow acne from mismatched depth passes, LOD selected for the undisplaced
  surface. Fix: declare max displacement, inflate cull *and* LOD bounds by it, and accept the
  culling-efficiency loss — or bake the displacement into the mesh before the build.
- **Software-raster overdraw with aggregates.** The 64-bit-atomic rasterizer has no early-out
  benefit when dozens of pixel-scale triangles stack on one pixel — every one pays the atomic.
  Dense foliage through this path is a worst case (deep overdraw × atomic contention). Aggregates
  go to the instanced/impostor pipeline (`08`); this is a routing rule, not a tuning problem.
- **Quantization grid consistency.** Quantize vertex positions on a single object-space
  power-of-two lattice and store cluster-locally *relative to that lattice*. Quantizing each
  cluster on its own local grid puts shared boundary vertices on different lattices → hairline
  cracks that appear only at certain scales/distances and defeat the whole watertight-cut
  guarantee. Same discipline as `01`'s vertex snapping, one level more subtle.
- **Error metric must include attributes.** Pure geometric QEM error lets the simplifier shred
  UVs and normals while staying under τ geometrically — textures swim and lighting crawls across
  LOD changes that are "sub-pixel" in position only. Fold attribute/UV deviation into the
  simplification error (attribute-extended quadrics) so the stored cluster error bounds what the
  *shaded* pixel can do, not just the silhouette. Material-blend weights on terrain are an
  attribute too (`07`).
- **Cut flicker and hysteresis.** `projError ≈ τ` oscillates with sub-pixel camera motion, and a
  group flipping at 1 px error is invisible under TAA but visible without it (or with sharpening
  stacked on top). Keep the decision *identical* for all clusters in a group (shared self/parent
  data — never "optimize" this into per-cluster values), make the projection conservative and
  deterministic (same math in traversal and any debug view), and add hysteresis: a small τ band
  (switch down at τ, up at τ·k, k≈1.2) or quantized projected error. If the pipeline has no TAA,
  budget τ < 1 px, not "about a pixel".
- **Monotonicity rot.** Any post-build touch-up (per-platform re-quantization, mesh patching,
  bounds "tightening") that edits errors or bounds without re-propagating breaks
  `parent >= child`, which breaks the parallel cut — holes or double-shaded surfaces at specific
  distances. Re-run the offline monotonicity assert after *any* pipeline stage that rewrites
  cluster data (`11`).

## Sources & provenance

| Claim | Tier | Source |
|---|---|---|
| Cluster DAG (group/simplify/re-split), locked group boundaries, monotonic group-shared error, parallel cut test, persistent-threads traversal, HW/SW raster split, 64-bit-atomic visibility buffer, cluster pages + GPU feedback + root-page fallback | **T** | Karis, Stubbe, Wihlidal — "Nanite — A Deep Dive", SIGGRAPH 2021, Advances in Real-Time Rendering course |
| Visibility buffer (per-pixel triangle ID, deferred attribute fetch/shade) | **P** | Burns & Hunt, "The Visibility Buffer: A Cache-Friendly Approach to Deferred Shading", JCGT 2013 |
| Cluster-hierarchy LOD with batched GPU-friendly units (pre-Nanite lineage) | **P** | Cignoni et al., "Adaptive TetraPuzzles" (SIGGRAPH 2004); Cignoni et al., "Batched Multi Triangulation" (IEEE Visualization 2005) |
| QEM simplification; attribute-extended quadrics | **P** | Garland & Heckbert, "Surface Simplification Using Quadric Error Metrics", SIGGRAPH 1997 (attributes: Garland & Heckbert 1998) |
| View-dependent continuous LOD lineage | **P** | Hoppe, "Progressive Meshes", SIGGRAPH 1996 |
| Two-phase (previous-frame HiZ, retest) occlusion culling | **T** | Haar & Aaltonen, "GPU-Driven Rendering Pipelines", SIGGRAPH 2015, Advances in Real-Time Rendering course |
| Persistent-threads GPU work-queue pattern | **P** | Aila & Laine, "Understanding the Efficiency of Ray Traversal on GPUs", HPG 2009 |
| Meshlet building, vertex-reuse limits, cone bounds, locked-border simplify | **D/F** | meshoptimizer (Kapoulkine), github.com/zeux/meshoptimizer — docs + established community practice |
| Mesh/amplification (task) shader model and meshlet limits | **D** | D3D12 Mesh Shader spec (DirectX 12 Ultimate); Vulkan `VK_EXT_mesh_shader` |
| Nanite Landscape (per-component heightfield conversion), WPO max-displacement declaration, `r.Nanite.MaxPixelsPerEdge`, Virtual Shadow Maps as Nanite's shadow partner | **D/N** | Epic Games UE5 official documentation (engine-branded features; workflow detail in `03`, `10`) |
| Specific constants: 128-tri clusters, ~1 px default error target | **T** | Stated in the Nanite deep dive / UE docs |
| Specific constants: group size ~up to 32 clusters, ~128 KB pages, METIS-class partitioner in the builder | **T/?** | Widely repeated from the deep dive; verify against the talk before quoting numbers |
| "Heightfield is the cheapest terrain compression; keep it for collision/gameplay even when converted" | **F** | Standard industry practice; see terrain-architect `27` for the data-handoff side |
| Hysteresis band k≈1.2 for cut stability | **F/?** | Community practice for SSE-style controllers; no canonical published constant |
