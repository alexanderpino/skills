---
type: Technique
title: Mesh extraction — getting terrain out of the tool, offline
description: "Turning a heightfield into a triangle mesh an authoring tool can export: quadric-error simplification, the greedy-insertion alternative for pure heightfields, why the quadric cost is not a screen-space error, and whether the exported LOD levels have to be nested."
tags: [rendering, mesh, tin, simplification, export, authoring-time]
status: draft
generated: { by: process:claude-code, at: 2026-09-03T00:00:00Z }
sources:
  - { id: garland1997, tier: P, locator: "§5 eq. (2) — the error at a vertex is the SUM of squared distances to the planes of its incident triangles, with the fundamental quadric K_p = p·pᵀ for a plane p = a b c d normalised so a² + b² + c² = 1; §4 for the additive rule Q̄ = Q1 + Q2 and eq. (1), the 4×4 linear solve for the contraction target; §4.1 for the five-step algorithm and the cost heap; §5.1 Geometric Interpretation for the degenerate level surfaces and when eq. (1) is not invertible; §3.2 for the pair-selection threshold t, where t = 0 is plain edge contraction; §6 Preserving Boundaries, which says of terrain height fields that 'it is necessary to preserve boundary curves while simplifying their shape' and adds perpendicular constraint planes at a large penalty weight" }
  - { id: garland1995, tier: F, locator: "§4 Greedy Insertion and Algorithm I — start from two triangles on the grid corners and repeatedly insert the unused input point of largest error; §3.1 for the local error measure, the vertical difference between the field and the interpolated approximation; §3.6 for the finding that importance measures making no reference to the current approximation 'give no guarantee about the accuracy of their approximations', with the city-versus-rolling-hills failure; §4.4 Algorithm III and the abstract for the expected cost O((m+n) log m) against the O(mn) and O(n log m + m²) of earlier variants; §4.5.1 Combating Slivers, where data-dependent triangulation is traded against a shape-quality term; §5.3 for the RMS error against vertex count fitting m^−0.7 empirically where the L2-optimal triangulation converges as m^−1, and for RMS being the steadier quality measure" }
  - { id: hoppe1996, tier: P, locator: "§3.1 Overview — a progressive mesh is a base mesh plus a sequence of vertex-split records, edge collapse alone being sufficient to build it; §3.2 Geomorphs, where the blend between consecutive levels is defined only because the coarser mesh's vertices are the finer one's, interpolated along the split; §3.3 progressive transmission and §3.5 selective refinement" }
---
# Mesh extraction — getting terrain out of the tool, offline

`heightfield-lod.md` is about a mesh that never exists on disk: CDLOD, clipmaps and CBTs all
synthesise triangles per frame from a heightfield and a camera. **This document is the other
job** — producing an actual triangle mesh, once, offline, that leaves the tool as a file. That
is what an authoring tool in the Gaea or World Machine class exports, and none of the runtime
machinery helps, because there is no camera at export time and the output has to be correct for
every camera.

**Boundary.** Nothing here selects a level of detail, morphs between levels, or closes a crack at
runtime. That is `heightfield-lod.md`, it is a solved and separate problem, and this document
cites it and moves on. What crosses the line between the two is exactly one thing — a number,
the per-mesh geometric error — and getting that number's units and meaning right is most of the
work below.

## Use this

**Iterative edge contraction ordered by a quadric error metric, run to an explicit error
threshold, with the tile boundary constrained** [garland1997]. Give every vertex a symmetric 4×4
matrix `Q` accumulated from the planes of its incident triangles, put every candidate edge in a
heap keyed on the cost of collapsing it, and pop until the cost exceeds your budget. It is the
default in every mesh toolchain for a reason: the state per vertex is ten floats, the work per
step is a heap pop and a few local updates, and it makes no assumption that the surface is a
function of `x, y` — so overhangs, welded tiles, attribute seams and the non-manifold joins
[garland1997] explicitly supports all survive it.

**Cross over to greedy insertion** [garland1995] when the source is a *pure single-valued
heightfield* with no attributes and you want the fewest triangles for a stated vertical error —
the crossover is set out below, and it is sharper than it looks.

**What it beats.** *Vertex clustering* — snap to a grid and merge; fast, and the error is
unbounded and the output is unusable at the low end. *Uniform decimation* (drop every other
sample) — the mip-chain of meshes; it spends the same triangles on a cliff and on a lake bed, which
is the entire thing simplification exists to avoid. *Marching cubes over a signed distance field* —
the right answer if the terrain genuinely has caves and overhangs authored as volume, and a
category error if it is a heightfield: it converts an exact 2.5-D function into an approximated
3-D one and then needs simplifying anyway. *Exporting the full grid and letting the engine
simplify* — defensible, and it moves the same decision to a tool with less information about what
the terrain means.

## The metric, exactly

The metric itself is four lines, and it is worth transcribing rather than paraphrasing,
because every popular summary of it loses one of them.

```
p       = [a, b, c, d]        # a plane, normalised so a^2 + b^2 + c^2 = 1
K_p     = outer(p, p)         # the fundamental error quadric: a symmetric 4x4
Q_v     = sum(K_p for p in planes of the triangles incident on v)
Delta_v = [vx, vy, vz, 1] @ Q_v @ [vx, vy, vz, 1]     # eq. (2): the error at v
```

Three properties, each transcribed and then run:

- **`vᵀ K_p v` is exactly the squared distance from `v` to the plane `p`.** Measured against the
  analytic point-plane distance over 20 000 random points: maximum absolute difference
  **2.8e-14**. This is why the matrix form is worth having at all — it stores a whole set of
  planes in ten floats and adds two sets by adding two matrices.
- **Every original vertex has error zero**, because it lies in all of its own incident planes.
  Measured over a 41×41 triangulated paraboloid: maximum `Δ(v)` at an original vertex
  **1.8e-13**. The paper states it in §5; it is a useful assertion to keep in the code, because
  a non-zero initial error means the plane normals or the `d` term are wrong.
- **The contraction target comes from a 4×4 linear solve**, eq. (1), which places the new vertex
  at the centre of the quadric's level ellipsoid. It is **singular on flat ground** — all the
  incident planes are parallel, so the level surfaces degenerate, exactly as §5.1 says. Measured
  on a flat patch: the condition number of that matrix is `inf`. Fall back to the endpoints or the
  midpoint; do not let a linear solver return a random point on a plateau.

The additive rule `Q̄ = Q1 + Q2` double-counts planes shared by the two vertices, at most three
times each, and [garland1997] accepts that trade deliberately. Keep the trade; the alternative is
carrying explicit plane sets that grow as simplification proceeds.

## The quadric cost is not a screen-space error

This is the crossover between this document and `heightfield-lod.md`, and it is where exported
meshes most often carry a wrong number in their metadata.

`heightfield-lod.md` runs a controller on `rho = e·K/d`, where `e` is **the largest vertical
deviation of the simplified surface from the full-resolution one, in metres**, and `rho` comes out
in pixels. `Δ(v)` is not that quantity, and `sqrt(Δ(v))` is not either. Two reasons, both
measured:

- **`Δ` is a sum over incident planes, so it scales with valence.** Holding the geometric
  displacement fixed at 0.01 world units and varying only how many planes meet the vertex, `Δ`
  came out exactly proportional to the plane count — `Δ / (n·d²)` was **0.8830 at n = 3, 4, 6, 8
  and 12**, constant to four figures, and equal to `cos²(20°)` for the 20°-tilted planes used, which is
  the analytic value — so `sqrt(Δ)` grows as `√n`: 1.63, 1.88, 2.30, 2.66 and 3.26 times the
  true displacement. Same geometric error, five different numbers, decided by mesh valence.
- **On a real surface the gap is large.** Over 3,453 interior edge contractions on the
  paraboloid, mean `sqrt(Δ)` was **0.0175** against a mean true vertical miss of **0.0031** — a
  ratio of **5.60**, ranging 4.17 to 6.94 across the contractions. Feeding `sqrt(Δ)` into the
  runtime controller as `e` therefore over-tessellates *and* by an amount that varies per region,
  which is the worst of both. ⚠️ **The factor is not a constant of the metric — it is a function of
  the surface's slope**, and an earlier draft quoted the single paraboloid above as "roughly 5×".
  Varying only the surface in the same rig: **6.91× at max slope 0.1, 5.59× at slope 1.0** (the
  measured configuration), **4.09× at 2.0, 2.54× at 4.0 and 1.17× at 10.0**. So it is worst on
  gentle ground — most terrain, and exactly where a controller is cheapest to satisfy — and nearly
  honest on cliffs. The direction holds everywhere (the ratio never drops below 1); only the
  magnitude was overreach.

**So use each metric for the job it is for.** The quadric is a **ranking key**: it decides which
edge to collapse next, and its absolute value is meaningful only against itself. The screen-space
budget needs a **measured** `e`. Get it by sampling: after simplification, evaluate the simplified
mesh at the original grid positions and take the maximum absolute vertical difference against the
source heightfield. That is one rasterisation pass per chunk, it is exact by construction, and it
is the number `heightfield-lod.md`'s controller was specified against.

⚠️ Two units traps that follow from the same confusion. `Δ` is in **squared** length units, so a
threshold tuned on a metre-scaled terrain is off by a factor of 10⁴ on a centimetre-scaled one
— the scale factor 100 comes in squared — normalise
your model, or scale the threshold, and never ship a bare quadric threshold as a preset. And a
quadric threshold is **not resolution-independent**: refine the source grid and the same
threshold keeps a different number of triangles, because valence and plane count changed. State
the export target as an error in metres and solve for the threshold.

## Boundaries, or the export that eats its own tiles

The single most destructive thing a naive QEM run does to terrain is quiet, and it is measurable.

On a flat patch, collapsing a **boundary** edge has quadric cost **exactly 0.000e+00** — and
dragging the boundary vertex a full cell *inward* also costs **0.000e+00**. The metric has no
opinion at all, because a point moved within the plane is at zero distance from every plane it
knows about. So the first thing an unconstrained simplifier does to a flat tile edge is eat it,
and if the tile next door is simplified independently the two outlines no longer meet. On the
curved patch the same two measurements are 2.2e-4 and 5.9e-4 — small, and still far too small
to protect the seam against a threshold tuned for the interior.

[garland1997] anticipates exactly this, and names terrain when doing so: §6 says that for models
such as terrain height fields "it is necessary to preserve boundary curves while simplifying
their shape", and adds, for each face along a boundary edge, a **plane perpendicular to that face
through the edge**, converted to a quadric and weighted by a large penalty factor. Implement it.
Then two further rules that the paper does not owe you but a tiled export does:

- **Two tiles that share an edge must simplify that edge identically.** Constraining it is not
  enough — a constrained edge can still be simplified, just expensively. Either freeze the shared
  boundary vertices outright, or simplify the seam once and hand the identical result to both
  tiles. `tiled-streaming.md` owns what happens to those tiles afterwards.
- **The same treatment goes to every discontinuity you care about**, not just the outline: a
  material boundary, a UV seam, a river bank you painted. §6 calls these discontinuity edges and
  handles them with the same constraint planes, which is why marking them is cheap.

## Greedy insertion, and when it wins

The other family runs the opposite direction: start coarse and **refine**. [garland1995] is the
canonical treatment for heightfields specifically — and it is a CMU technical report, not a
peer-reviewed paper. **There is no canonical paper for greedy insertion; standard practice is
this report and the `scape` implementation released with it**, and the report itself notes the
algorithm has been reinvented many times.

```
# Algorithm I, the unoptimised form; sec. 4.2-4.4 remove the full rescan
initialise the TIN to two triangles on the four grid corners
while not done:
    for every unused grid point p:  err(p) = |H(p) - interpolate(TIN, p)|
    insert the p of maximum err into the Delaunay triangulation
```

Four things it gets right that are worth stealing even if you use QEM:

- **The importance measure is the error against the current approximation**, not a feature
  detector. §3.6 reports that measures which never look at the approximation "give no guarantee
  about the accuracy of their approximations", and gives the failure that makes it concrete: a
  dataset containing both a city (rough at small scale, flat at large) and rolling hills (smooth
  small, rough large) sends almost all the vertices to the city.
- **The cost is `O((m+n) log m)` expected** for their optimised Delaunay variant (§4.4), against
  `O(mn)` or `O(n log m + m²)` for earlier published versions — a million-point terrain in under
  a minute on 1995 hardware.
- **Error falls as roughly `m^−0.7`** in RMS against vertex count, measured (§5.3), where the
  L2-optimal triangulation is known to converge as `m^−1`. That is your budgeting law: to halve
  the RMS error of an exported TIN, expect to spend about **2.7×** the vertices, not 2×. It also
  says how far from optimal a greedy result is, which is the honest way to defend it.
- **RMS is the steadier stopping criterion than maximum error**, which is spiky and
  outlier-driven (§5.3). Stop on RMS; *report* the maximum, because the maximum is what the
  screen-space controller consumes.

**The crossover.** Greedy insertion wins when the source is a single-valued heightfield, there are
no per-vertex attributes to preserve, and the deliverable is the fewest triangles for a stated
vertical error — because its importance measure *is* that error, exactly, while the quadric cost
is a proxy for it. QEM wins the moment any of those three fails: an overhang or a cave makes the
surface non-functional and there is nothing to interpolate; attributes and discontinuity curves
need constraint quadrics; and a mesh that arrived from somewhere other than a grid has no "unused
input points" to insert. In an authoring tool, all three fail often enough that QEM is the one to
build and greedy insertion is the one to offer for the heightfield fast path.

## The LOD chain a tool exports, and whether it has to be nested

An export is rarely one mesh. It is a chain — full detail, then a ladder of coarser versions,
usually halving triangle count per step, which the consuming engine picks between. **No canonical
paper prescribes that chain's shape; standard practice is to bake a fixed ladder of independently
simplified levels and let the runtime swap them.** That works, and it makes exactly one decision
you should make deliberately.

**Must the levels be nested — every coarser level's vertices a subset of the finer one's?** Not
for correctness, and yes for anything that blends. The property is what a progressive mesh gives
you by construction: a base mesh plus a sequence of vertex splits, so every intermediate mesh in
the chain is reachable from the one below it by refinement alone [hoppe1996]. §3.2 makes the
consequence explicit — a geomorph between consecutive levels is *definable* precisely because the
coarser mesh's vertices are the finer one's, interpolated along the split. Simplify each level
independently from the source instead and you get a chain with no correspondence between levels,
so there is nothing to interpolate and the only available transition is a hard swap or a
cross-fade.

| Situation | Export | Because |
|---|---|---|
| Fixed levels, the engine cross-fades or pops | Independent per-level runs | Simplest; each level is optimal for its own budget |
| The engine geomorphs between levels | A nested chain — one run, snapshot the ladder | Correspondence is what makes the blend definable [hoppe1996] |
| The engine streams detail progressively | The vertex-split record stream itself | It is lossless and continuous-resolution [hoppe1996] |
| The consumer is a cluster-DAG renderer | Per-cluster simplification with locked cluster borders | The DAG wants independently-simplified groups, not one global chain |

Whichever you pick, **write the measured maximum vertical error into each level's metadata, in
metres, beside its bounding box.** `heightfield-lod.md` is explicit that this number must come
from the actual vertex removals and never from a mip level — and this document is where it is
produced. A chain that ships without it forces the runtime to guess, and every symptom in that
document's failure table starts with a guessed `e`.

Two smaller export contracts worth stating once. **Match the collision mesh's triangulation to
the render mesh's, diagonal included** — a heightfield quad has two triangulations and picking
differently in two exporters puts objects visibly through the ground. And **simplify before you
bake normals, not after**: normals baked from the full-resolution surface onto the simplified one
carry the removed detail, which is the whole point; the reverse loses it permanently.

## How this fails, and what it looks like

| Symptom | Mechanism | Fix |
|---|---|---|
| Tile edges no longer meet after export | Boundary edges collapsed at zero quadric cost | Constraint planes at a large penalty, and freeze or share the seam [garland1997] |
| Adjacent tiles have matching outlines but different vertex counts on the shared edge | Boundary constrained but still simplified, independently on each side | Simplify the seam once, hand the identical result to both |
| Runtime tessellates 1.2× to 7× more than the budget implies, worst on gentle ground | `sqrt(Δ)` exported as the geometric error `e` | Measure `e` against the source grid; the quadric is a ranking key |
| Two chunks with the same true error get different LOD | `Δ` scales with mesh valence, not with deviation | Same fix; `Δ/(n·d²)` is constant, so `Δ` is measuring `n` too |
| An export threshold that worked yesterday keeps 10× the triangles | Model rescaled; `Δ` is in squared units | Specify the target in metres and solve for the threshold |
| Refining the source grid changes the exported triangle count at a fixed threshold | A quadric threshold is not resolution-independent | Same fix; see `node-graph-runtime.md` on parameters that must rescale |
| Random vertices scattered across a plateau | eq. (1)'s matrix is singular on flat ground | Detect it; fall back to endpoints or midpoint [garland1997] |
| Every vertex reports non-zero error before any contraction | Plane normals not unit length, or `d` has the wrong sign | The initial error is provably 0 [garland1997]; assert it |
| All the vertices land in one rough region and the rest of the terrain is coarse | Feature-based importance measure, blind to the approximation | Use error against the current approximation [garland1995] |
| Doubling the vertex budget barely improves the mesh | Expected: RMS goes as about `m^−0.7` | Halving error costs ~2.7× the vertices [garland1995] |
| Stopping criterion oscillates and will not converge | Stopping on maximum error, which is spiky | Stop on RMS; report the maximum [garland1995] |
| Nothing can blend between exported LOD levels | Levels simplified independently, no vertex correspondence | Export a nested chain if the engine geomorphs [hoppe1996] |
| Slivers and near-degenerate triangles in the TIN | Data-dependent triangulation optimises the fit to the height function, and does not care about triangle shape | Add a shape-quality term, as §4.5.1 does [garland1995] |
| Objects clip through exported terrain | Collision and render meshes triangulated with opposite diagonals | Fix the diagonal convention in one place |
