---
type: Technique
title: Heightfield ray marching — one traversal kernel, many consumers
description: "Fixing the pixel and searching the terrain along a ray: the max-mip traversal that serves primary rendering, shadows, occlusion and picking, and how heightfields enter a ray-tracing pipeline."
tags: [rendering, ray-traced, raymarching, heightfield, near-real-time]
status: draft
generated: { by: process:claude-code, at: 2026-09-02T00:00:00Z }
sources:
  - { id: tevs2008, tier: P, locator: "§3.1 Data Structure for the max-reduce mipmap and its build cost table; §3.2 Intersection Algorithm for the hierarchical traversal loop; §3.3 for level of detail. §4 is Comparison, not the method" }
  - { id: drobot2010, tier: F, locator: "GDC 2010 deck: slide 24 builds the quadtree by mipmapping with a min operator, slides 26–27 and 44 give the traversal and the cell-boundary intersection test, slides 45–49 the refinement, iteration cap and LOD; height blending is slides 81–84 and 91–92" }
  - { id: dummer2006, tier: F, locator: "the per-texel cone opening" }
  - { id: policarpo2007, tier: F, locator: "ch. 18, the relaxed cone and its one-overshoot-then-bisect search. NOT OPENED -- the GPU Gems 3 chapter was not obtained here; the attribution rests on papers-rendering.md own sentence about it and on the audit X11, so no page range is asserted" }
  - { id: tatarchuk2006, tier: P, locator: "§4, view-angle-adaptive step counts and refinement" }
  - { id: policarpo2005, tier: P, locator: "§3, linear search plus binary refinement" }
  - { id: smacke, tier: F, locator: "the front-to-back bullet in README.md and the Python listing under it, where ybuffer holds the highest drawn y per screen column and DrawVerticalLine clips against it" }
  - { id: dxrspec, tier: F, locator: "the Intersection shaders - procedural primitive geometry section; Acceleration structure updates with Bottom-level acceleration structure updates and Acceleration structure update constraints; Opacity micromaps for what those do and do not classify" }
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
level = coarsestMip; t = tEnter; steps = 0          // tEnter = max(0, ·), tExit: ray ∩ [mapMin, mapMax]
                                                    // both FINITE and NON-NEGATIVE
while (t < tExit) {
  node      = texelAt(rayPos(t), level)             // explicit-LOD fetch: SampleLevel or Load, never Sample
  tExitNode = min(exitDistance(node, ray), tExit)   // DDA to the node boundary, CLAMPED
  // The predicate stated above, written directly: is the ray at or below node.maxH
  // ANYWHERE in [t, tExitNode]? Ray height is linear in t, so the endpoints decide it.
  if (min(rayHeight(t), rayHeight(tExitNode)) < node.maxH) {   // a hit is possible here
    if (level == 0) return refine(t, tExitNode)     // binary or secant refine, 5-8 iterations
    if (rayDir.y < 0) {                             // only a DESCENDING ray may advance
      tCross = tWhereRayHeightEquals(node.maxH, ray)
      t = max(t, tCross)                            // the span before tCross is provably clear
    }
    level--                                         // descend
  } else {                                          // safe skip, pop up
    t     = max(t, tExitNode) * (1.0f + 2.38418579e-7f)  // RELATIVE step — never `+ eps`
    level = min(level+1, coarsestMip)
  }
  if (++steps > stepCap) return miss                // a belt, NOT the termination argument
}
return miss
```

⚠️ **The `never Sample` on the `texelAt` line is a language rule, not a preference.** A loop that
can exit early puts its *whole* body inside varying flow control — this one has no `break`, it
`return`s from two places, and the specification counts `ret` with `break` — and there the
derivative and implicit-LOD instructions are forbidden on one API and undefined on the other, and
compile on both. `shader-craft.md` carries the specification text for that; the *different* rule
for the fetch at the hit below, where the flow is uniform again, so the derivative is legal and
still wrong and the fix is a different instruction; and a second reason the fetch must not filter:
a bilinear tap on a max-reduce pyramid returns a convex combination, so it lands at or *below* the
bound this loop's skip test needs.

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

⚠️ **Advance relatively, and clamp the node exit — the two lines that make the loop terminate.**
The skip branch is where this loop hangs. `t = tExitNode` lands the ray exactly on a node boundary;
pop up, descend again, and `exitDistance` at the finer level returns that same `t`, so the branch
assigns `t = t` forever. **An absolute nudge is not a fix**: `t + 1e-4` is a *no-op in fp32 for
every `t ≥ 2048 m`*, half a ULP there already exceeding it (ULP 2.4e-4) — the guard evaporates at exactly the
distances a terrain marcher lives at. `max(t, tExitNode)·(1 + 2⁻²²)` moves 2–4 ULP *at every positive normal
magnitude* (1 mm at 5 km, 23 mm at 100 km, and the skipped sliver sits inside a span the predicate
just proved clear), and the `max` keeps the increase unconditional when the boundary rounds back
behind `t`. Advancing the DDA's integer cell index instead and deriving `t` from it is equally
sound and is the better choice for a kernel that carries per-level DDA state; it is not available
*here*, because this block is stateless — it re-derives `node` from `rayPos(t)` every iteration and
changes `level` between them, so there is no one cell index to increment.

The clamp is not tidiness. A straight-down picking ray — a use this kernel is sold for — never
leaves its column, so `exitDistance` is `+inf` and the level-0 branch calls `refine(t, ∞)`, a
binary search on an unbounded interval. Clamping to a finite `tExit` removes that, and every
unbounded operand with it. ⚠️ It does **not** remove every NaN: a reciprocal-form DDA
(`invD = 1/0 = ∞`) on a ray with `dir.x == 0` sitting exactly on an x-boundary computes
`(bound − o.x)·invD = 0·∞ = NaN`, and `min(NaN, tExit)` is still NaN. Which branch that takes
depends on your `min`: a NaN-propagating one skips and reports clear line of sight through
terrain it never tested; an IEEE `minNum` descends instead. Test the one your target ships.
**Termination is then structural, given `tEnter ≥ 0`** — each iteration strictly increases `t` or
decreases `level`, and `level` only rises on the branch that increases `t`. ⚠️ The precondition is
load-bearing and the caller owns it: at `t = 0` the relative advance is `0·(1+2⁻²²) = 0` and the
loop cycles, and at negative `t` the multiply moves *away* from zero, i.e. backward, to an exact
fixed point. Clamp `tEnter` with `max(0, ·)`; the textbook slab entry for an origin inside the
map is negative. That is why the step cap is a belt against a pathological
field, not the argument. Say that out loud in review: a capped livelock looks exactly like a slow
frame.

**Registration, which the block assumes and which nothing else pins.** A level-`L` texel `(i,j)`
owns the half-open square `[i·s_L, (i+1)·s_L)`, `s_L = s₀·2^L`, and carries its sample at that
square's centre; `texelAt` is `floor(pos.xz / s_L)`, never a rounded texel-centre lookup, and
`node.maxH` is the max over that footprint **plus a one-texel apron at level 0** — dilate the base
samples 3×3 and max-reduce *that*, which stays conservative at every level, where aproning per
level over-bounds by 2^L and aproning only the top level is not conservative below it — if the
surface is
reconstructed bilinearly, since interpolation inside an edge texel reaches the neighbour's sample
and an un-aproned reduce is not conservative there. Leave this unstated and even the failure is
unstable: two independent transcriptions of the unfixed block — different fields, different DDAs,
different ray sets — livelocked on 14.8% and 63.0% of 600 rays each, and a third, in fp32, ranged
over 36–63% with nothing changed but the registration convention.

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
dissolve into noise exactly where this technique's silhouettes were the selling point. **The rule
is about the pixel quad, not about normals, so it covers every fetch at the hit**: albedo, splat
weights, detail UVs. `ddx/ddy` of anything derived from the hit position is garbage across a
silhouette, so a plain `Sample` there is the same defect wearing a mip-noise costume instead of a
normal-noise one. Use `SampleGrad` with gradients built from **ray differentials** — the
neighbouring pixel's ray, evaluated at this hit's distance — which is a quantity the marcher
already has and the quad does not.

**What it beats.** *Uniform stepping with refinement* — simple, bounded, and wrong: any feature
thinner than a step is skipped, and N must be sized for the worst grazing ray. *Cone step mapping*
[dummer2006] — a per-texel empty-cone opening is provably safe and converges beautifully, but it
touches the surface only in the limit, so silhouette-grazing rays creep. The **relaxed** variant —
one permitted overshoot, then a binary search back — is *not* Dummer's: it is Policarpo and
Oliveira's, GPU Gems 3 chapter 18 (2007), which is where most readers meet the cone technique at
all and why the two are so routinely conflated. Both bake in minutes for a large map, which makes
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
| Relaxed cone step — Policarpo & Oliveira [policarpo2007], over Dummer's cone [dummer2006] | 4–12 | heavy bake | Static detail maps only |
| Quadtree / max-mip [drobot2010] | median ≈1.4·log(res), p99 far higher | mip chain | Long tail on grazing rays; wins at 1k+ detail maps and steep relief |

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
  with a coarse proxy prepass, or run the march in compute before the opaque pass. **Name the
  direction, or the declaration is a lie the hardware believes**: the promise is *never nearer than
  the rasterized proxy*, which is `SV_DepthLessEqual` under **reversed-Z — this corpus's mandate —
  and `SV_DepthGreaterEqual` under standard depth**, the two being opposite tokens for one
  promise. It holds only if the proxy is a **max-height** surface — the marcher's own max-reduce,
  a hull that encloses the terrain, so its depth is at or nearer than the hit for every pixel it
  covers. A mean-height or raster-LOD proxy sits behind the hit somewhere in every frame, and the
  hardware then culls pixels that should have been drawn. A layer that only alpha-composites over
  the frame is a screenshot technique, not a renderer.
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
| Some pixels hang, or the shader TDRs, and only far from the camera | The skip branch set `t = tExitNode`, landing on a node boundary that re-derives the same node — `t = t` forever. An absolute `+ eps` hides it near the camera and is absorbed by fp32 ULP past 2048 m | `t = max(t, tExitNode)·(1 + 2⁻²²)`; a step cap only converts the hang into a slow frame |
| A picking or straight-down ray never returns | `exitDistance` is `+inf` for a column-locked ray, so `refine(t, ∞)` bisects an unbounded interval; a reciprocal-form DDA can make `exitDistance` NaN, which the clamp does not remove, the predicate false, and the query reports clear sight | `tExitNode = min(exitDistance(...), tExit)` before the predicate |
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
