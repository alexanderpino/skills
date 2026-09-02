---
type: Technique
title: Heightfield ray marching — one traversal kernel, many consumers
description: "Fixing the pixel and searching the terrain along a ray: the max-mip traversal that serves primary rendering, shadows, occlusion and picking, and how heightfields enter a ray-tracing pipeline."
tags: [rendering, ray-traced, raymarching, heightfield, near-real-time]
status: draft
generated: { by: process:claude-code, at: 2026-09-02T00:00:00Z }
sources:
  - { id: tevs2008, tier: P, locator: "§4, the maximum-mipmap pyramid and its hierarchical traversal" }
  - { id: drobot2010, tier: F, locator: "the quadtree displacement traversal, applied to material displacement" }
  - { id: dummer2006, tier: F, locator: "the per-texel cone opening and the relaxed variant" }
  - { id: tatarchuk2006, tier: P, locator: "§4, view-angle-adaptive step counts and refinement" }
  - { id: policarpo2005, tier: P, locator: "§3, linear search plus binary refinement" }
  - { id: smacke, tier: F, locator: "the y-buffer column loop in the reference implementation" }
  - { id: dxrspec, tier: F, locator: "intersection shaders for procedural AABB geometry; BLAS refit vs rebuild" }
---
# Heightfield ray marching — one traversal kernel, many consumers

**Tier: near-real-time and ray-traced, with one component that ships in every rasteriser.** This is
the other way to draw a heightfield — fix the pixel and search along the ray, instead of pushing
triangles and letting the hardware find the pixels. The lineage runs from 1992 software column
raycasters through per-pixel relief mapping to heightfields as procedural primitives in ray-tracing
pipelines, and the *same kernel* is infrastructure for shadows, occlusion, picking and gameplay
queries.

The recurring engineering pattern, learned once and reused by every member: **a precomputed
conservative bound turns a blind fixed-step march into a safe adaptive one.**

## Use this

**A max-reduce mipmap pyramid over the heightfield, traversed top-down with safe skips**
[tevs2008]. At each node: if the ray stays above `node.max` across the node's footprint, skip to
the node's exit and pop up a level; otherwise descend. Step count is roughly logarithmic in
distance rather than linear, the build is a mip chain (cheap enough to rebuild per frame on a
deforming field), and the pyramid *is* the LOD — selected per step by footprint, with no LOD
machinery to write.

```
level = coarsestMip; t = tEnter
while (t < tExit) {
  node      = texelAt(rayPos(t), level)
  tExitNode = exitDistance(node, ray)               // DDA to the node boundary
  // The predicate stated above, written directly: is the ray at or below node.maxH
  // ANYWHERE in [t, tExitNode]? Ray height is linear in t, so the endpoints decide it.
  if (min(rayHeight(t), rayHeight(tExitNode)) < node.maxH) {   // a hit is possible here
    if (level == 0) return refine(t, tExitNode)     // binary or secant refine, 5-8 iterations
    if (rayDir.y < 0) {                             // only a DESCENDING ray may advance
      tCross = tWhereRayHeightEquals(node.maxH, ray)
      t = max(t, tCross)                            // the span before tCross is provably clear
    }
    level--                                         // descend
  } else { t = tExitNode; level = min(level+1, coarsestMip) }   // safe skip, pop up
}
return miss
```

⚠️ **Test the predicate, not the crossing.** The form of this loop that circulates most widely asks
"does the ray cross `node.maxH` before it leaves the node?" and descends only then. That is correct
*only for a descending ray*. A ray whose height **increases** with `t` — a shadow ray toward the
sun, a long-range occlusion ray, an upward line-of-sight query, which is to say precisely the
consumers the shared kernel below is sold on — can sit below `node.maxH` across the node's whole
span with no crossing inside it at all. `tCross` then lands beyond `tExitNode`, the skip branch
fires, and the traversal **skips a node that can contain a hit**. That is a *missed* hit, not a
conservative one: shadows leak through ridges and a line-of-sight query reports clear sight through
a mountain. The interval test above has no such asymmetry, and the crossing is used only for what
it is actually good for — advancing a falling ray past the part of the span that is provably above
the node. Ascending and horizontal rays simply enter the candidate span at `t`.

**Build it once and share it.** The same kernel — parameterized by start bias, max distance, mip
clamp, and whether refinement runs — serves primary marching, sun shadows, long-range occlusion,
cursor picking, and gameplay line-of-sight. Divergent copies rot independently, and the classic
symptom is shadows that disagree with the rendered silhouette because the two marchers treat texel
centres or bilinear filtering differently. Pin one written convention: texel-centre registration,
bilinear versus point, apron ownership. The CPU gameplay mirror cannot literally be the GPU code,
so hold the two together with a conformance test against an analytic field such as
`h = a·sin(kx)`, asserting hit-error bounds on both.

**At the hit**: refine, then reconstruct the normal **analytically** from heightmap central
differences at a mip matched to the hit's footprint. Never take screen-space derivatives of the hit
position — neighbouring pixels hit wildly different terrain across a silhouette, so the normals
dissolve into noise exactly where this technique's silhouettes were the selling point.

**What it beats.** *Uniform stepping with refinement* — simple, bounded, and wrong: any feature
thinner than a step is skipped, and N must be sized for the worst grazing ray. *Cone step mapping*
[dummer2006] — a per-texel empty-cone opening is provably safe and converges beautifully, but it
touches the surface only in the limit, so silhouette-grazing rays creep; the relaxed variant
allows one overshoot and binary-searches back. Both bake in minutes for a large map, which makes
them right for static detail tiles and wrong for a heightfield that streams or deforms.
*Back-to-front painter's traversal* — works and silently costs 5–20× overdraw. *Voxel Space column
raycasting* [smacke] — the 1992 original, and no voxels are involved: two 2D arrays, one march per
screen column, occlusion by an ascending y-buffer costing one compare per column per step. It died
because the colour map *is* the lighting, attitude freedom is limited, and it produces no depth to
composite polygons against; it survives as a genuine aesthetic and a good teaching artefact.

## The relief-mapping tier is a different question, not a weaker answer

Shrink the same march into a thin tangent-space shell inside a rasterized mesh's pixel shader and
it becomes a *material* feature — displacement the mesh does not have. This is the one member of
the family that ships in essentially every rasteriser, and it belongs to the material band, not to
the geometry band.

| Rung | Samples/px | Precompute | Notes |
|---|---|---|---|
| Normal map only | 1 | none | The floor, and the distance tier for everything below |
| Parallax offset | 1–2 | none | Swims at steep angles; fine for shallow relief |
| **POM** [tatarchuk2006] | 8–32 + refine | none | **The shipping default**; step count scales with view angle |
| Relief, linear + binary [policarpo2005] | 8–16 + log refine | none | Better on thin features than pure linear search |
| Relaxed cone step [dummer2006] | 4–12 | heavy bake | Static detail maps only |
| Quadtree / max-mip [drobot2010] | ~log(res) | mip chain | Wins at 1k+ detail maps and steep relief |

**The structural limit, stated so nobody spends a week on it:** the march lives in the interpolated
tangent frame of a rasterized triangle, so **the silhouette is still the mesh's**. Relief detail
slides past object edges and terrain horizon lines unmodified. The honest fixes are to keep the
displaced amplitude well below the mesh-silhouette scale, to tessellate for the geometry band, or
to graduate to true per-pixel terrain marching.

Under a temporal upscaler: sample detail maps with gradients from the *undisplaced* UV, keep the
march deterministic across jitter (jitter the refinement only), and remember that motion vectors
are the mesh's — high-amplitude POM under a fast camera smears, and the fix is less amplitude, not
more TAA.

## Marching as primary, and the frame integration that actually costs

A fullscreen pass reconstructs a world ray per pixel, clips it to `[mapMin, mapMax]`, and runs the
traversal above. No terrain mesh exists.

*Where it wins*: pixel-exact silhouettes at any zoom with zero LOD machinery; displacement-scale
detail with no tessellation; memory is the heightfield you already stream. *Where it loses*:
horizon-grazing rays take the maximum step count **and** diverge within a wave, so the worst view
costs many times the average; no early-Z or raster culling helps; and every material feature the
raster pipeline gives free needs bespoke plumbing.

Three integration duties, all of which are where the real cost and the real bugs live:

- **Write true depth from the hit.** `SV_Depth` disables early-Z; use conservative depth output
  with a coarse proxy prepass, or run the march in compute before the opaque pass. A layer that
  only alpha-composites over the frame is a screenshot technique, not a renderer.
- **Derive motion vectors analytically** — reproject the hit's world position through last frame's
  matrices. Otherwise every temporal upscaler receives garbage.
- **Jitter the first step per pixel** so residual banding becomes noise a temporal resolve can
  integrate.

## Heightfields in a ray-tracing pipeline

Terrain is ray-tracing-*secondary* in almost every shipped title: rays start from G-buffer surfaces
and terrain must be hit *consistently*, not reproduce the raster microcut.

**Default: a stable pre-triangulated BLAS proxy** at a deliberately chosen ray-tracing LOD, using
the hardware ray-triangle path. Do **not** feed the camera-selected raster cut into the
acceleration structure — geomorphs and quadtree topology changes would turn camera motion into
acceleration-structure churn, and a dense near-coplanar heightfield floods memory with triangles
secondary rays do not need. Fixed-topology height edits may **refit**; topology changes require a
**rebuild**, and rebuilds are streamed, amortized work, never a camera-driven mid-frame event
[dxrspec].

**Cross over to procedural AABBs plus an intersection shader** running the traversal above when
memory is the binding constraint or the field deforms often: memory is roughly the heightfield
itself, and an edit is a texture update plus a pyramid rebuild with no geometry churn. The cost is
that intersection shaders forgo the hardware triangle test, and incoherent secondary rays make the
divergence worse; the gap is vendor- and generation-dependent [dxrspec].

⚠️ **The proxy is at a different LOD than the raster terrain, so rays originating on raster
surfaces self-intersect or float.** Offset ray origins along the geometric normal by a bound
derived from the error `e` between the two representations — the same `e` the LOD controller
already tracks — not by a magic epsilon. Register `e_proxy`, the intended ray uses, the update
policy and the resident cost per tile in the same budget sheet as raster and streaming. **A ray
proxy with no declared error is an invisible second terrain.**

⚠️ **Opacity micromaps are not the displacement answer** [dxrspec]. They classify alpha coverage so
traversal can accept or reject hits in hardware — a real win for alpha-tested grass and leaf cards
hammering any-hit shaders. They add no displacement and track no height edits. Displacement
micromaps can encode microdisplacement on supported paths, but API, hardware and tooling support
remain platform-sensitive; treat that as a capability tier to verify, never as the portable
baseline.

## How this fails, and what it looks like

| Symptom | Mechanism | Fix |
|---|---|---|
| Concentric contour steps on slopes | The march found the crossing one step late | Binary or secant refinement, then per-pixel first-step jitter, then a temporal resolve. Raising the raw step count is the expensive non-fix |
| Frame rate collapses only on the mountaintop horizon shot | Grazing rays take max steps and diverge within the wave | Budget from the worst-case capture; cap steps with a graceful miss; prefer pyramid traversal, whose step count degrades logarithmically |
| Normals dissolve into noise at silhouettes | Screen-space derivatives of the hit position across a silhouette | Analytic central differences at a footprint-matched mip |
| Shadows leak through ridges, or objects vanish behind them | One pyramid shared by the marcher and the occlusion proxy | Max-**height** reduce for the ray pyramid, min-**height** reduce for the occluder proxy — opposite conservative directions, two pyramids. (Both are reductions over *height*; the HiZ depth pyramid's min/max is over *depth* and is a separate choice — see `gpu-driven-culling.md`) |
| Shadows leak through ridges while the primary march is pixel-perfect | The traversal descends on `tCross < tExitNode`, which is true only for descending rays; the ascending shadow ray skips nodes that hold the occluder | Descend on the interval test `min(rayHeight(t), rayHeight(tExitNode)) < node.maxH`; advance to `tCross` only when the ray is falling |
| Self-shadow acne, or shadows detached from contact | Shadow rays launched from the undisplaced surface against the displaced field | Start at the displaced hit; bias along the light by a bound tied to the local texel size |
| Shadows disagree with the rendered silhouette | Two copies of the traversal with different texel-centre or filtering conventions | One kernel, one written convention, an analytic-field conformance test on both sides |
| Ghosting and smearing under a temporal upscaler | The pass rasterizes nothing, so no motion vectors were written | Derive velocity analytically from the hit's world position |
| The march composites over foreground geometry | Only alpha-composited; no true depth written | Write depth from the hit and test the depth buffer |
| Ridges missing where a march crosses a streaming tile edge | No apron: the ray exits the tile and misses the neighbour's geometry | One texel of neighbour data resident, per the streaming apron contract |
| Hitches at LOD bands; ray-traced shadows pop a frame late | Raster LOD selection or geomorph topology was reused as the acceleration-structure input | A stable proxy or procedural AABBs; camera motion is never an acceleration-structure invalidation |
| Ray-traced contacts float or acne at 100 km | World-space rays marched in fp32 at planetary magnitude | March camera-relative or patch-local; the heightfield lookup carries the large offset, not the ray parameter |
| Relief detail slides past the object's edge | The silhouette belongs to the mesh; it always did | Reduce amplitude, tessellate, or move to primary marching |
