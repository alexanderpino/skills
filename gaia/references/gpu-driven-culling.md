---
type: Technique
title: GPU-driven culling — the CPU stops counting chunks
description: "Moving per-frame terrain visibility and LOD onto the GPU: the persistent scene, the culling ladder, two-phase HiZ occlusion, and indirect submission."
tags: [rendering, rasterizer, culling, gpu-driven, real-time]
status: draft
generated: { by: process:claude-code, at: 2026-09-02T00:00:00Z }
sources:
  - { id: haar2015, tier: F, locator: "pp. 13–21 of the combined course PDF — the pipeline overview, per-instance GPU data persistent for static instances, cluster chunk expansion, index compaction, multi-draw; pp. 51–52 for two-phase occlusion culling against last frame depth pyramid" }
  - { id: karis2021, tier: F, locator: "slide 19 states the two-pass rule, slides 75–77 are Nanite own version and the culling dataflow" }
  - { id: wihlidal2016, tier: F, locator: "compute backface-cone and small-primitive culling" }
  - { id: burns2013, tier: P, locator: "§2 The Visibility Buffer — a four-byte triangle id plus instance id per sample; §3.2 The Visibility Buffer Pipeline for the three phases that defer attribute fetch to shading" }
  - { id: d3d12indirect, tier: F, locator: "the ExecuteIndirect reference page — the MaxCommandCount parameter description and the Remarks pseudo-code, CommandCount = min of the count buffer value and MaxCommandCount" }
---
# GPU-driven culling — the CPU stops counting chunks

**Tier: real-time rasteriser.** Terrain is the ideal customer for a GPU-driven pipeline and should
be the first system moved to one: thousands to millions of near-identical units, homogeneous
shading, no skinning, no per-object gameplay logic, bounds known analytically from the heightfield,
and a spatial hierarchy that already exists for LOD. General scenes pay complexity for
heterogeneity; terrain gets the win almost for free.

## Use this

**A persistent GPU scene, culled in compute, submitted indirectly, with two-phase HiZ occlusion.**
There is no canonical paper for this architecture; standard practice is the formulation given in
the *GPU-driven rendering pipelines* SIGGRAPH course talk [haar2015] — a conference talk about a
shipped title, not peer review, and the tier reflects that. What follows is the division of labour
as that talk laid it out, which every subsequent public description of a GPU-driven pipeline has
restated rather than replaced:

- **The CPU owns policy.** Camera, budgets, streaming decisions, what exists in the world. It
  uploads *deltas* into a persistent structured buffer of chunk records — bounds, LOD links,
  material and page IDs, offsets into shared vertex and heightmap pools.
- **The GPU owns per-frame truth.** Which chunks are visible, at what LOD, in which passes —
  decided in compute, written into indirect argument buffers, consumed without the CPU ever seeing
  the answer. Per-object CPU cost is zero and total CPU cost never scales with the world — at worst
  O(selected cut). The CPU issues a handful of
  dispatches and one indirect draw per pass, regardless of world size.

**The test for whether you have actually built this**: if any array proportional to world size is
rebuilt on the CPU each frame, you have a CPU renderer with GPU-flavoured syntax.

**What it beats.** *The CPU visible-list architecture it replaced* — walk every resident chunk,
frustum-test it, select its LOD, patch the visible list, submit one draw each; O(resident) on the
render thread even when nothing is visible, and per-frame argument uploads make the GPU wait on a
serial producer. *Explicit-API driver-overhead reduction alone* — it made the O(N) controller
cheaper per item without removing it. *Partial adoption* — keeping a CPU visibility pass "for
safety" and uploading its results pays both costs and adds a frame of latency; this is the one
failure mode worth naming as a rule rather than a pitfall. The rule is about what the cost scales
*with*, not where the code runs: O(selected cut) CPU work that produces a *candidate* list the GPU
then culls — a CDLOD descent that early-outs on range, a few thousand nodes — is not partial
adoption — it is the *selected* cut of `heightfield-lod.md`. CPU work that scales with the world is.

## The ladder

Cull coarse to fine; each stage runs in compute and compacts survivors for the next. Skipping a
stage is legitimate. Reordering them is not.

| Stage | Granularity | Mechanism | Where it earns |
|---|---|---|---|
| Horizon | chunk | one dot product against the horizon plane/cone | Planets — the only stage whose kill rate *grows* with world size |
| Frustum | chunk | 6 plane-vs-AABB tests, positive-vertex form | Everywhere |
| Cone / backface | cluster | normal cone vs view vector [wihlidal2016] | Rolling terrain; **nearly useless on plains**, where every normal points up |
| Occlusion | chunk, then cluster | two-phase HiZ | The big one in hilly terrain; weak on open plains |
| Triangle | triangle | compute backface, zero-area, small-primitive [wihlidal2016] | Only when triangles are small enough that fixed-function rejection is the bottleneck |

**The small-primitive test carries a rasterizer assumption.** It rejects a triangle whose
screen-space bounds enclose no pixel *centre*. That is the rasterizer's rule only for
single-sample, non-conservative pixels. Under MSAA coverage is evaluated at *sample*
positions, so the test culls triangles that legitimately cover samples and the edge anti-aliasing
goes ragged; under conservative rasterization any overlap of the pixel *area* counts, so it culls
triangles that must draw. Under coarse-rate VRS coverage is still resolved on the pixel grid and
the test survives — the trap there is deriving it from the *shading* rate instead. Snap the test to
the active sample pattern, or skip the stage, whenever the pass is not single-sample and
non-conservative: it is the one rung of the ladder whose correctness depends on pipeline state, and
it passes every single-sample test you will write for it.

⚠️ **Conservative bounds are the terrain-specific trap** — a different sense of the word from the
rasterizer state above, and this document's own doctrine is that a shared word is how a sign gets
copied to the wrong place. The tested bound must contain the
geometry *as rasterized*: inflate by the chunk's height min/max, by skirt depth, by geomorph
excursion — a morphing vertex sweeps between two levels' heights, so bound the union — and by any
material displacement. Under-inflated bounds fail *at the screen edge*, where a chunk whose peak
enters the frustum but whose base AABB does not gets culled and pops in as the camera pans. The
bug hides in flat test terrain and ships. Give every inflation term a named owner.

## Two-phase occlusion, and the conventions that break it

The problem is circular — you need depth to cull, and culling to build depth. Single-phase answers
are wrong in a characteristic way: last frame's depth reprojected misses disocclusions, so
newly-visible objects pop in one frame late. Two phases close the loop inside one frame
[haar2015], and the same structure drives cluster-based virtualized geometry [karis2021]:

```
Phase 1: draw everything visible LAST frame (per-chunk visibility bit)
         -> build the HiZ pyramid from that depth
Phase 2: test ALL candidates against HiZ
         -> draw those not already drawn that now pass  (the disocclusions, this frame)
         -> write this frame's visibility bits
```

Phase 1's set is **not** a superset of true visibility — it is last frame's answer, so it is
missing exactly this frame's disocclusions, which is why phase 2 exists. What camera coherence buys
is narrower and sufficient: the objects that occluded the view last frame are almost all still
occluding it, so phase 1's depth is a **nearly complete occluder set** even though it is an
incomplete visible set. No reprojection, no artist-placed occluder proxies, no one-frame
lag. It costs two culling rounds, two submission rounds, and a visibility-bit buffer keyed by
**stable IDs** — streaming must not recycle an ID mid-frame, or a recycled slot inherits a dead
chunk's visibility and phase 1 draws the wrong thing.

Three HiZ build details, in the order they bite:

1. **Reduction convention — and say which quantity you are reducing.** This document uses two
   different reductions and they are not the same word: a HiZ pyramid min/max-reduces **depth**, a
   terrain occluder proxy min/max-reduces **height**. Write the quantity every time. For the HiZ:
   standard depth (near = 0) needs the *farthest* depth in the footprint → **max-depth** reduce;
   reversed-Z needs **min-depth** reduce. Backwards gives *false occlusion*: geometry near
   silhouettes disappears for a frame under motion.
2. **Odd dimensions.** A naive 2×2 reduction of an odd-sized mip drops the last row and column, so
   those depths never propagate and the pyramid claims occlusion where sky was. Gather 3×2 / 2×3 /
   3×3 at the edges, or pad with the *non-occluding* extreme for your convention.
3. **Footprint mip.** Project the bound's corners, clamp to screen, choose the mip where the rect
   spans at most 2×2 texels — computed from the *larger* dimension, log2 rounded up, so one texel
   is at least as wide as the rect and the four corner taps cover it at *any* alignment. That
   coverage is the whole invariant, and losing it has the sign bullet 2 already stated. Too **fine**
   leaves texels *inside* the rect unread between the corner taps while the corner texels still
   spill *outside* it, so `sampled ≥ trueMax` no longer holds: `zNear > sampledMax` can fire where
   truth says draw, and **visible geometry is culled**. Too **coarse** still covers a superset of
   the rect, so the sampled max stays ≥ the true max and the test is merely conservative — it looks
   correct and saves nothing.

   Worked on a 64 px rect, standard Z, max-depth reduce, a ridge at depth 0.3 with a 24 px sky gap
   through it, and the object at 0.6. The rule gives mip 6 (64 px texels), and at mip 6 the taps
   see the gap, `0.6 > 1.0` is false, and the object draws — correct. One level finer, at mip 5, a
   rect not aligned to 32 px straddles three 32 px texels — 31 of the 32 offsets do — and the corner
   taps read only the outer two in x, so the gap sits in the middle texel that nothing sampled: the
   max comes back 0.3, `0.6 > 0.3` fires, and an object you can plainly see through the gap is
   culled. Now a *second* 64 px rect, sitting on the mip-6 grid at x = [0, 64) with that same gap
   starting 36 px past its right edge: at mip 6 one 64 px texel covers it exactly, the max is 0.3,
   and it is culled — correct, it really is behind the ridge. One level coarser, at mip 7, the
   128 px texel [0, 128) reaches the gap, the max comes back 1.0, `0.6 > 1.0` is false, and the cull
   is silently lost. Under-reading is the direction that costs you pixels, whether
   the cause is a dropped edge texel or a mip chosen too fine; over-reading only costs you the win.

**After a teleport or camera cut there is no history.** Treat everything as visible for one frame
and budget the spike. Never carry stale visibility bits across a cut: with feedback-driven
streaming, one frame of the wrong world also requests the wrong pages.

## Submission

- **Indirect with a count buffer.** Culling appends surviving args and bumps an atomic counter;
  the draw reads the count GPU-side [d3d12indirect]. Without count-buffer support you draw the
  worst case with zeroed args — functional, wasteful on the front end.
- **Atomic append or prefix sum.** Append is simplest and fine at terrain scales. Prefix-sum
  compaction preserves the survivors' *input* order, which append does not — so the list is
  deterministic frame to frame and capture comparison works. It does **not** give front-to-back:
  input order is the scene buffer's order, and that is view-independent. Early-Z ordering needs a
  view-dependent sort or a depth-bucket pass after compaction. Worth it once counts reach hundreds
  of thousands, or as soon as you need bit-exact captures.
- **Vertex pulling makes terrain args degenerate.** With one shared patch index buffer, a draw is
  just a chunk ID; every arg differs only in its constants. Use instancing when topology is truly
  shared, indirect draws when edge-permutation index buffers vary the index count.
- **Bindless, or you are back to per-draw CPU descriptor binding** — which reintroduces exactly
  the per-object cost this architecture exists to remove. The material and page IDs this pipeline
  indexes with are per-pixel, not per-wave: a descriptor index that is not wave-uniform must be
  wrapped in `NonUniformResourceIndex()` (HLSL) / `nonuniformEXT` (GLSL, the SPIR-V `NonUniform`
  decoration), or the compiler may
  assume uniformity and broadcast one lane's index to the wave — the classic bug that renders
  correctly on one vendor and ships. `shader-craft.md` carries the specification text behind that
  rule and two consequences this bullet does not: one wrapped index suffices on a
  multi-dimensional resource array, and a divergent index degrades the **derivative** as well, so a
  per-pixel material ID and an implicit-LOD `Sample` are a bad pair even with the intrinsic in
  place.
- **Per-pass visibility bits, one dispatch per stage, N frusta.** Opaque, skirts, water and each
  shadow cascade are different pipeline states and therefore different survivor lists — and the
  cascades are different *frusta*. The shape is: each stage's dispatch reads the persistent scene once,
  every frustum (the camera's, plus each cascade's light frustum) tested in-kernel against the
  same chunk record, N bit-planes written, N compactions. The HiZ occlusion stage runs for the
  camera bucket only; a cascade that wants occlusion builds its own HiZ from its own depth. "Cull
  once" means *read the scene once* — not test one frustum and reuse the answer, which drops
  every caster outside the camera frustum. Do not merge water into the opaque list.

**Two terrain-specific cuts general pipelines do not have.** Per-cascade shadow culling gets exact
caster AABBs free from per-chunk height bounds — but casters must be tested against the *light's*
frustum, never the camera's HiZ, since a caster invisible to the camera still casts into view. And
**the heightfield is the best long-range occluder in the scene**: rasterize a coarse terrain proxy
into the phase-1 depth before building HiZ and the standard test culls whole cities behind
ridgelines. The proxy's heightfield must be built with a **min-height** reduce — conservatively
*below* true terrain — or it culls visible objects along the ridge. (That is a reduction over
height, not the **min-depth** reduce of the reversed-Z HiZ above; the two are independent choices,
and the shared word is how a sign gets copied to the wrong place.) It is also the opposite
conservative direction from the **max-height** pyramid used for ray marching; see
`heightfield-raymarching.md`. Same source texture, two pyramids, and sharing one silently breaks
whichever consumer got the wrong sign.

## Feedback, and the rule with no exceptions

LOD selection discovers wants — finer tiles, texture pages. Write requests to a GPU buffer, copy
to a readback ring, consume on the CPU **N frames later**. Readback is asynchronous, the latency
is a design constant, and *nothing* ever waits on it. One synchronous map of an in-flight buffer
flushes the pipeline and costs more than the entire culling system saves.

**Crossover — the visibility buffer** [burns2013]. Rasterize (chunk ID, triangle ID) plus depth and
shade in a later compute pass, bucketed by material. Terrain needs *no* vertex attributes at all on
this path: grid position comes from the triangle ID, height from the heightmap, UVs analytically.
Worth it when triangles approach pixel size — at 1 px/tri nearly every pixel is a quad-overshading
edge — or when the material is a heavy layered stack. When triangles are large and the material is
one splat blend, the reconstruction cost (manual attribute fetch, analytic derivatives for mip
selection) is pure overhead. Decide on measured triangle size, not fashion.

## How this fails, and what it looks like

| Symptom | Mechanism | Fix |
|---|---|---|
| Geometry pops in at the screen edge while panning | Bounds not inflated for displacement, skirts or geomorph excursion | Conservative bounds with a named inflation term per contributor |
| One-frame disappearances at silhouettes under motion, or objects vanishing behind a ridge they are visible through a gap in | HiZ reduce op wrong for the depth convention, NPOT edge texels dropped, or the footprint mip too **fine** — three ways to under-read the max, all of which produce false occlusion | Reversed-Z → min-**depth** reduce; gather the odd row and column; mip from the rect's *larger* dimension, ceil the log2 |
| Occlusion culling "works" but saves nothing | Footprint mip too **coarse** — the corner taps over-cover the rect and read the sky beside it, so the test is conservative and looks correct | Same mip rule; draw the chosen level against the projected rect in a debug view — one texel should already cover the rect |
| Objects flicker in and out behind ridges | The terrain occluder proxy used max-**height** reduce and sits above true terrain | Min-**height** reduce for the occluder proxy; keep it separate from the max-**height** ray-marching pyramid |
| A chunk draws the wrong thing for one frame after streaming | Visibility bits keyed by array slot; streaming compacted the scene | Key history by persistent chunk ID; clear on recycle; no slot reuse between phases |
| Shadows missing from objects the camera cannot see | Casters culled against the camera frustum or the camera's HiZ — "cull once" read as one frustum instead of one scene read | Test each cascade's light frustum, extruded along the light, in the same dispatch; its own bit-plane, its own HiZ if any |
| GPU idle bubbles correlated with streaming | The CPU maps a buffer the GPU wrote this frame | N-deep readback ring, consumed N frames late; grep for synchronous maps |
| A wrong or empty draw with no validation error | Indirect argument corruption — silent by construction | Permanent atomic counters per stage (in → out), an args readback ring, breadcrumb writes |
| Per-frame flicker at any threshold boundary | No hysteresis on a binary state — LOD, occlusion, cascade membership | Split at `tau`, merge at `tau·h`, `h ≈ 0.7–0.85` |
| Culling profiled great, ships slow | Kill rates measured on the canyon frame | Profile the peak-vista frame: plains defeat occlusion, flat ground defeats cone culling |
