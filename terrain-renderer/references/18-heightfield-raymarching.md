---
# --- okf v0.2, written by tools/okf_apply.py -----------------------
type: Reference
title: "Heightfield Ray Marching: from Voxel Space to Relief Mapping and Heightfield Ray Tracing"
description: Heightfield ray marching from Voxel Space to relief mapping, and the step-count arithmetic that decides whether it is affordable.
tags: [terrain, raymarching, relief-mapping]
status: stable
generated: { by: process:claude-code, at: 2026-07-30T09:56:09+02:00 }
# --- end okf v0.2 ----------------------------------------------------
---
# Heightfield Ray Marching: from Voxel Space to Relief Mapping and Heightfield Ray Tracing

This chapter owns the other way to draw a heightfield: fix the pixel and search the terrain along
a ray, instead of pushing triangles through the rasterizer and letting hardware find the pixels
(`01`, `02`). The lineage runs from 1992 software column raycasters (Comanche's "Voxel Space")
through GPU per-pixel relief/parallax techniques and max-mip traversal to heightfields as
procedural primitives in RT pipelines — and the same traversal kernel is infrastructure for
shadows (`10`), occlusion (`08`), picking (`16`), and gameplay queries (`17`).

Contents: [The family in one frame](#the-family-in-one-frame) ·
[Voxel Space](#voxel-space-1992-column-raycasting) ·
[Per-pixel marching as primary](#per-pixel-heightfield-ray-marching-as-primary) ·
[The relief-mapping tier](#the-relief-mapping-family-the-near-field-tier) ·
[Rays as infrastructure](#heightfield-rays-as-infrastructure) ·
[RT-era heightfields](#heightfield-ray-tracing-in-the-rt-era) ·
[Hybrids](#hybrid-architectures) · [Decision table](#decision-table) ·
[Pitfalls](#pitfalls) · [Sources](#sources--provenance)

## The family in one frame

Five members, one primitive — `march a ray against h(x, y)` — in five roles:

| Member | Role | Granularity | Status 2026 |
|---|---|---|---|
| Voxel Space column raycasting | Whole-terrain primary (historical/retro) | Per screen column | Indie/retro revival; trivially GPU-portable |
| Per-pixel heightfield marching | Whole-terrain primary, no mesh | Per pixel | Niche primary; standard for detail layers |
| Relief / POM / cone-step | Near-field material displacement on a rasterized mesh | Per pixel, in a thin shell | Shipping everywhere (`07`'s material band) |
| Rays as infrastructure | Shadows, AO, occlusion, picking, LOS | Per query | Standard AAA machinery (`08`, `10`) |
| Heightfield ray tracing | Intersection shaders / triangulated BLAS in RT pipelines | Per RT ray | Growing; raster-primary + RT-secondary default |

The recurring engineering pattern: a **precomputed conservative bound** (cone map, max-mip
pyramid) turns a blind fixed-step march into a safe adaptive one. Learn that once; every member
reuses it.

## Voxel Space (1992): column raycasting

**Honest naming first.** NovaLogic's "Voxel Space" (Kyle Freeman; shipped in Comanche: Maximum
Overkill, 1992; patented — US 6,020,893, filed 1997, granted 2000, now expired) stores **no
voxels**. It is 2.5D heightmap column raycasting over two 2D arrays: a height map and a color
map (1024×1024, one byte each in Comanche). Outcast (Appeal, 1999) is the same family; its lead
developer says outright they "misused the term voxel" for a heightfield with software raycasting.
Say "column raycasting" in design docs; keep "voxel space" for history.

**Mechanism.** For each depth `z` front to back, sample the map along a line parallel to the view
plane (rotated by yaw), project each sample's height to a screen row with a perspective divide,
and draw a vertical segment per column — but only the part *above* the highest pixel already
drawn in that column (the ascending **y-buffer**). Occlusion costs one compare per column per
step; no depth buffer, no sorting.

```
// front-to-back, per depth line; ybuffer[x] = topmost drawn pixel, starts at screenH
z = zNear; dz = 1.0
while (z < zFar) {
  pl = cam.xy + rot(yaw) * float2(-z, z)              // left frustum edge at depth z
  pr = cam.xy + rot(yaw) * float2(+z, z)              // right frustum edge
  for (x = 0; x < screenW; x++) {
    p = lerp(pl, pr, x / screenW)                     // map sample for this column
    y = (camH - height[p]) / z * scaleH + horizon     // perspective height projection
    if (y < ybuffer[x]) {                             // visible only if above prior max
      drawVLine(x, y, ybuffer[x], color[p])
      ybuffer[x] = y
    }
  }
  z += dz; dz += 0.02                                 // LOD: step grows with distance
}
```

```
 side view, one column:                screen column x:
 cam ●— steps → . . .  .   .    .        ┌──┐ sky
  camH \      ___          ___           │▒▒│ ← segment from far ridge (drawn 2nd,
        \    /   \___     /              ├──┤    only the part above ybuffer)
 ground  \__/        \___/               │██│ ← near hill (drawn 1st, sets ybuffer)
   far ridge pokes above near hill  →    └──┘ ybuffer only ever rises
```

Notes that matter: marching along **view-plane-parallel lines** (not per-column polar rays) gives
perspective-correct results with no fisheye correction. Pitch is a horizon shift; roll is a
per-column lerp of the horizon between two values (shearing the columns). Both are approximations
that hold for flight-sim attitudes and fall apart looking straight down — there is no true 6DOF.

**Why it won in 1992**: per-pixel terrain detail with zero triangles at a time when polygon
engines drew flat-shaded hills from hundreds of triangles; the color map carries pre-baked
lighting and shadows, so the inner loop does no shading at all. **Why it died**: the baked
colormap *is* the lighting — dynamic sun, shadows, and material response mean repainting the map;
attitude freedom is limited; the CPU is fill-bound (every screen pixel touched by the march);
and composition with polygonal objects needs per-pixel depth the algorithm doesn't naturally
produce. Outcast's answer — raycast terrain composited with a polygon engine for objects,
bridges, and roofs — is the ancestor of this chapter's hybrid section. **Modern revival**: the
loop is embarrassingly parallel (one thread per column, or a per-pixel variant) and a popular
retro/indie aesthetic; the s-macke writeup is the canonical modern reference.

Pitfalls: step size larger than a map texel makes thin ridges shimmer and crawl under yaw
(sample coarser mips as `dz` grows — the same Nyquist rule as everywhere); map wraparound must be
intentional (tiling worlds) or clamped; drawing back-to-front without the y-buffer "works" and
silently costs 5-20× overdraw.

## Per-pixel heightfield ray marching as PRIMARY

The GPU generalization: a fullscreen pass (the same single-triangle plumbing as `12`'s
screen-space water) reconstructs a world ray per pixel, clips it to the terrain volume
`[mapMin, mapMax]`, and finds the first crossing of `h(x, y)`. No terrain mesh exists at all.

**Uniform stepping** (N fixed steps + refinement) is the baseline: simple, bounded, wrong — any
feature thinner than a step can be skipped, and N must be sized for the worst (grazing) ray.
Production marchers use a **safety-radius structure**:

- **Cone step mapping** (Dummer; relaxed variant Policarpo & Oliveira, GPU Gems 3 ch. 18): each
  texel stores the opening of the widest cone, apex on the surface, containing no terrain. Step
  to the ray/cone intersection — provably safe, converges from above but only touches the surface
  in the limit, so silhouette-grazing rays creep (cap iterations, then refine). Relaxed cones
  allow one overshoot and binary-search back — fewer steps, needs the refinement pass. Cone maps
  are expensive to bake (minutes for large maps) — fine for static detail tiles, wrong for a
  heightfield that streams or deforms.
- **Maximum mipmaps / quadtree traversal** (Tevs, Ihrke & Seidel, I3D 2008; Drobot's QDM in GPU
  Pro is the same idea shipped for material displacement): build a max-reduce mip pyramid over
  the heightfield — **the same pyramid `08` uses as a terrain occluder and `10` marches for sun
  shadows; one pyramid, three consumers, one build pass per edit.** Traverse top-down: at the
  current node, if the ray stays above `node.max` across the node's footprint, skip to the node's
  exit and pop up a level; otherwise descend. Build cost is a mip chain (negligible, per-frame
  fine for deforming terrain), and step count is ~logarithmic in distance:

```
level = coarsestMip; t = tEnter
while (t < tExit) {
  node  = texelAt(rayPos(t), level)
  tExitNode = exitDistance(node, ray)                 // DDA to node boundary
  tCross    = tWhereRayHeightEquals(node.maxH, ray)   // ray dips below node max here
  if (tCross < tExitNode) {                           // possible hit inside this node
    if (level == 0) return refine(tCross)             // binary/secant refine, 5-8 iters
    level--                                           // descend into the pyramid
    t = max(t, tCross)
  } else { t = tExitNode; level = min(level+1, coarsestMip) }  // safe skip, pop up
}
return miss
```

**At the hit**: refine (binary halving between last-above and first-below sample, or one secant
step — kills the staircase), then reconstruct the normal **analytically** from heightmap central
differences at a mip matched to the hit's footprint. Never use screen-space derivatives of the
hit position: neighboring pixels can hit wildly different terrain across silhouettes and the
normals dissolve into noise exactly where the technique's silhouettes are its selling point.

**Frame integration** is where the real cost hides, and the doctrine is `12`'s fullscreen-water
doctrine verbatim: write real depth from the hit (`SV_Depth` disables early-Z — use conservative
depth `SV_DepthGreaterEqual` with a coarse proxy prepass, or run the march in compute before the
opaque pass); derive **motion vectors analytically** (re-intersect or reproject the hit's world
position with last frame's matrices — TAA and upscalers get garbage otherwise); and jitter the
first step per pixel so residual banding becomes TAA-resolvable noise.

**When it beats meshes**: pixel-exact silhouettes at any zoom with zero LOD machinery (the mip
pyramid *is* the LOD, selected per step by footprint); displacement-scale detail with no
tessellation; memory = the heightfield you already stream (`06`). **When it loses**: grazing rays
near the horizon cost hundreds of steps and diverge within waves (the worst-case view is the
spec); no hardware early-Z or fine raster culling helps you; every material/shading feature the
raster pipeline gives for free (decals `17`, VT feedback `07`) needs bespoke plumbing. As a
whole-screen primary it is a specialist's choice; as a *band* (far terrain, or a near detail
layer) it composites beautifully — see Hybrids.

## The relief-mapping family: the NEAR-FIELD tier

The same march, shrunk into the material band `07` alludes to: rasterize the terrain mesh
(`01`), and inside the pixel shader march a *detail* heightfield through a thin tangent-space
shell to displace the surface the mesh doesn't have. Lineage: parallax offset (single-sample
Kaneko/Welsh line) → **POM** (Tatarchuk, I3D 2006: linear march + refinement, soft self-shadows)
→ **relief mapping** (Policarpo, Oliveira & Comba, I3D 2005: linear + binary search, arbitrary
surfaces) → **cone-step / relaxed cone** (precomputed safety) → **QDM** (Drobot: per-texel max
pyramid, best at steep + high-res). Cost ladder, cheap to rich:

| Rung | Samples/px (typ.) | Silhouettes | Precompute | Notes |
|---|---|---|---|---|
| Normal map only | 1 | none | none | The floor; distance tier for everything below |
| Parallax offset | 1-2 | none | none | Swims at steep angles; fine for shallow relief |
| POM | 8-32 + refine | none | none | The shipping default; steps scale with view angle |
| Relief (binary) | 8-16 + log refine | none | none | Better thin features than pure linear |
| Relaxed cone step | 4-12 | none | heavy bake | Static detail maps only |
| QDM / max-mip | ~log(res) | none | mip chain (cheap) | Wins at 1k+ detail maps, steep relief |

The structural limit: the march lives in the interpolated tangent frame of a rasterized triangle,
so **the silhouette is still the mesh's** — relief detail slides past object edges and terrain
horizon lines unmodified. Depth-corrected and curved-shell variants exist but are fragile; the
honest fixes are (a) accept it and keep displaced amplitude ≪ mesh-silhouette scale, (b) real
tessellation for the geometry band, or (c) graduate to true per-pixel terrain marching above.
Under TAA/upscalers: the *shaded* position no longer matches the *rasterized* position, so
sample detail maps with gradients from the undisplaced UV (or explicit mip) to avoid derivative
seams, keep the march deterministic across jitter (jitter only the refinement), and remember
motion vectors are the mesh's — high-amplitude POM under a fast camera smears; reduce amplitude,
not TAA. Fade steps → parallax → normal-map-only with distance, and assert the fade in `11`'s
material-aliasing sweep.

## Heightfield rays as infrastructure

Even a fully mesh-rendered terrain (`01`/`02`) wants heightfield rays everywhere:

| Client | Ray | Chapter |
|---|---|---|
| Sun/terrain shadows | hit-point → light, max-mip accelerated; cone for penumbra | `10` |
| Horizon/AO precompute | N azimuthal horizon scans per texel at bake/edit time | `10` |
| Long-range occlusion | terrain pyramid kills props/tiles behind ridgelines | `08` |
| Picking / brush projection | cursor ray → terrain point for tool viewports | `16` |
| Gameplay LOS / projectiles / AI vis | CPU-side query against the authoritative field | `17` |

The maintenance rule is the point: **one tested traversal implementation, many consumers.** The
same kernel, parameterized by (start bias, max distance, mip clamp, refinement on/off, coarse-out
for shadows where the first hit's exact `t` doesn't matter). Divergent copies rot independently —
the classic symptom is shadows that disagree with the rendered silhouette because the shadow
marcher and the primary renderer treat texel centers or bilinear differently. The CPU gameplay
mirror cannot be the GPU code, so pin both to one written convention (texel-center registration,
bilinear vs point, apron ownership per `06`) and hold them together with `11`'s analytic-terrain
conformance test: march known rays against `h = a·sin(kx)`, assert hit error bounds on both.

## Heightfield ray TRACING in the RT era

When terrain must participate in hardware RT (shadow/GI/reflection rays from the whole scene),
three architectures:

1. **Stable pre-triangulated BLAS proxy.** Bake terrain tiles to triangles at a deliberately
   chosen RT LOD and use the hardware ray-triangle path. Do **not** feed the camera-selected
   raster cut into the BLAS: geomorphs and quadtree topology changes would turn camera motion
   into acceleration-structure updates, and a dense near-coplanar heightfield floods memory with
   triangles that secondary rays do not need. The proxy remains stable across raster LOD bands,
   carries a conservative error bound `e_proxy`, and is coarse enough to fit the RT memory and
   traversal budget. Fixed-topology height edits may use **refit**; topology/primitive-count
   changes require **rebuild**. Rebuilds are streamed/amortized work (`06`), never a camera-driven
   mid-frame event. This is the common 2026 shape because terrain is RT-*secondary* in almost
   every shipped title: rays start from G-buffer surfaces, and terrain must be hit consistently
   enough for shadows, GI, and reflections rather than reproduce the raster microcut.
2. **Procedural AABB + intersection shader.** Declare per-tile AABBs; the intersection shader
   runs the max-mip traversal from this chapter. Memory ≈ the heightfield itself; edits are a
   texture update + pyramid rebuild, no BLAS geometry churn. Cost: intersection shaders forgo
   the hardware triangle test and are generally costlier than built-in triangle intersection;
   the gap is vendor/generation-dependent, and incoherent secondary rays make divergence worse.
3. **Hybrid**: triangulated coarse BLAS for most rays + intersection-shader detail only where
   rays demand it. Rarely worth the complexity today — mark it a specialist move.

Contract to enforce regardless: the RT representation is a *proxy* at a different LOD than the
raster terrain, so rays originating on raster surfaces self-intersect or float. Offset ray
origins along the geometric normal by a bound derived from the LOD error `e` between the two
representations (the same `e` the LOD controller already tracks, `01`) — not by a magic epsilon.
Register `e_proxy`, intended ray uses, update policy, and resident-memory cost per tile in the
same budget sheet as raster and streaming. A ray proxy with no declared error is an invisible
second terrain.

### Micromaps: opacity is established; displacement is not universal

**Opacity Micromaps (OMM)** solve an adjacent terrain-ecosystem problem, not the heightfield BVH
problem itself. Alpha-tested grass, shrubs, and leaf cards make RT shadow rays repeatedly invoke
any-hit shaders to discover that a triangle is transparent. OMM-capable DXR/Vulkan paths encode
opaque/transparent/unknown micro-regions so traversal can accept or reject many hits in hardware,
substantially reducing any-hit work. They belong to `15`'s vegetation RT path and remain valid
only while the asset's opacity mapping remains compatible with the built micromap.

**Non-negotiable distinction:** OMM does not add terrain displacement, does not track a
geomorphed heightfield, and does not make raster LOD topology legal for BLAS reuse. Displacement
micromaps can encode geometric microdisplacement on supported paths, but API, hardware, tooling,
and update support remain platform/vendor-sensitive in 2026. Treat DMM as a capability tier to
verify, never as the portable terrain baseline.

## Hybrid architectures

The shipping shapes, all sharing one contract — **depth-correct compositing**: the ray-marched
layer writes true scene depth at its hits and tests the existing depth buffer, so meshes, water
(`12`), and VFX interleave correctly. A raymarched layer that only alpha-composites over the
frame is a screenshot technique, not a renderer.

- **Mesh near + raymarched far**: near field keeps decals, VT, and physics parity on triangles;
  beyond a radius, a fullscreen march (cheap per pixel at distance — steps are large, pyramid
  levels coarse) replaces far tiles and their LOD/streaming cost. The seam is a depth handoff at
  the radius with hysteresis, morphing the march's start plane to the mesh's last LOD ring.
- **Raymarched detail layer over coarse mesh**: rasterize a coarse terrain, then a per-pixel
  march *from the coarse surface* adds displacement the mesh lacks — true silhouettes within a
  band, unlike POM. Bound the displacement so culling stays conservative (`08`'s displaced-bounds
  rule), and start the march behind the rasterized depth by the displacement bound, never at it.
- **Retro/stylized**: Voxel-Space columns as the entire far-field under a polygonal near field —
  Outcast's architecture, still valid for its aesthetic.

## Decision table

| Approach | Silhouettes | Dynamic terrain | Integration cost | Pick when |
|---|---|---|---|---|
| Mesh LOD pipelines (`01`/`02`) | mesh-LOD-bounded | edit → remesh/refit | baseline; everything integrates | Default. All three profiles; tooling, decals, physics all native |
| Voxel Space columns | pixel-exact | repaint colormap | own the whole framebuffer | Retro aesthetic, jams, teaching; far-field stylized layer |
| Per-pixel marching primary | pixel-exact at any zoom | texture update + pyramid | high: depth, MVs, materials all bespoke | Extreme close-up displacement, planet-to-boulder zoom, no-mesh renderers |
| Relief/POM near-field | none (mesh's) | detail maps mostly static | low; it's a material feature (`07`) | Always, as the material band's parallax tier; amplitude ≪ silhouette scale |
| Rays as infrastructure | n/a | pyramid rebuild per edit | low; one shared kernel | Always — shadows (`10`), occlusion (`08`), picking (`16`), LOS (`17`) |
| RT: triangulated BLAS | RT-proxy LOD | refit/rebuild budget | medium; proxy-vs-raster offset contract | RT-secondary (shadows/GI) — the 2026 default |
| RT: intersection shader | pixel-exact to rays | texture + pyramid only | medium-high; shader cost per hit | Memory-bound worlds, frequent deformation, heightfield-native engines |
| RT: opacity micromaps | n/a — opacity coverage, not height | rebuild when coverage mapping changes | medium asset/build integration | Alpha-tested grass/foliage any-hit reduction on supported hardware |

## Pitfalls

- **Staircase banding** (concentric contour steps on slopes): the march found the crossing a
  step late. Cure in order: binary/secant refinement at the crossing, per-pixel first-step
  jitter, TAA resolve. Increasing raw step count is the expensive non-fix.
- **Grazing-angle blowup**: horizon-grazing rays take the max step count *and* diverge within a
  wave/warp, so the worst view costs many times the average. Budget from `11`'s worst-case
  capture (mountaintop horizon shot), cap steps with a graceful miss (fade to far-field color or
  mesh fallback), and prefer pyramid traversal — its step count degrades logarithmically, not
  linearly.
- **Pyramid convention bugs** — `08`'s HiZ warning, same disease: the ray-marching pyramid must
  be **max-reduce** (never miss the surface — conservative toward hits); `08`'s terrain occluder
  proxy must be **min-reduce** (never overclaim occlusion). Same source texture, *opposite*
  conservative directions, two pyramids or two channels. One shared "the" pyramid silently makes
  either shadows leak or objects pop out of existence behind ridges. Also: pad non-power-of-two
  reductions with the non-conservative extreme, and pin texel-center vs corner registration in
  the one shared kernel.
- **Self-shadow acne / detachment**: shadow rays launched from the *undisplaced* surface (the
  rasterized mesh, or the pre-march ray origin) against the *displaced* heightfield self-
  intersect (acne) or skip contact (peter-panning). Start shadow rays at the displaced hit
  point, bias along the light direction by a bound tied to the local step/texel size, and keep
  primary and shadow marchers on identical sampling conventions (see infrastructure rule).
- **BLAS rebuild follows the camera**: raster LOD selection or geomorph topology was reused as the
  RT input. The renderer hitches at LOD bands and RT shadows/reflections pop one frame later.
  Keep a stable RT proxy or procedural AABBs; camera motion is never a terrain-AS invalidation.
- **Opacity micromap category error**: OMM was proposed as the fix for changing terrain height.
  OMM classifies alpha coverage only. Keep the terrain proxy/update contract above; apply OMM to
  alpha-tested ecosystem geometry (`15`).
- **Precision at planetary scale**: marching world-space rays in fp32 at 100 km jitters the hit
  by meters — march in camera-relative or patch-local coordinates with the ray origin rebased
  per `09`'s doctrine; the heightfield lookup, not the ray parameter, carries the large offset.
- **Tile-border leaks**: a march that crosses streaming-tile boundaries needs the apron
  convention from `06` — one texel of neighbor data resident, or rays exiting a tile edge miss
  ridges owned by the neighbor and shadows strobe as tiles stream.
- **Screen-derivative normals at silhouettes** — analytic gradients only (see primary section);
  the same rule TAA motion vectors already forced on you.

## Sources & provenance

| Claim | Tier | URL |
|---|---|---|
| Voxel Space = 2.5D height+color map column raycasting; y-buffer front-to-back; `(camH-h)/z*scale+horizon` projection; growing `dz` LOD; 1024² byte maps; ~20-line loop — s-macke VoxelSpace repo | **F** (canonical community reconstruction) | https://github.com/s-macke/VoxelSpace |
| Interactive demo of the above | **F** | https://s-macke.github.io/VoxelSpace/ |
| Comanche: Maximum Overkill 1992; Kyle Freeman / NovaLogic lineage; Voxel Space 2/32 in Delta Force family | **F** (encyclopedic) | https://en.wikipedia.org/wiki/Voxel_Space |
| US Patent 6,020,893 "System and method for realistic terrain simulation", Freeman/NovaLogic, filed 1997, granted 2000, expired; multi-resolution elevation databases | **P** (patent, fetched) | https://patents.google.com/patent/US6020893A/en |
| Second NovaLogic terrain patent US 6,700,573 | **P** (seen in search results only) | https://patents.google.com/patent/US6700573B2/en |
| Outcast: raycast heightfield terrain + polygon engine for objects; Sauer: "misused the term voxel" | **T/F** (developer's own site + community) | https://francksauer.com/index.php/games?view=article&id=47%3Aoutcast-pc&catid=15%3Apublished-games |
| Outcast engine description corroboration | **F** | https://en.wikipedia.org/wiki/Outcast_(video_game) |
| Maximum mipmaps: max-reduce pyramid + hierarchical ray stepping, accurate & scalable, cheap precompute for dynamic heightfields — Tevs, Ihrke & Seidel, I3D 2008, pp. 183-190 | **P** | https://dl.acm.org/doi/10.1145/1342250.1342279 |
| Author project page + released shader code for the above | **P/D** | http://www.tevs.eu/project_i3d08.html · https://github.com/cgart/i3d08.research |
| Relief mapping on arbitrary polygonal surfaces: GPU ray-heightfield intersection, linear+binary search — Policarpo, Oliveira & Comba, I3D 2005 | **P** | https://dl.acm.org/doi/10.1145/1053427.1053453 |
| POM with approximate soft shadows; grazing-angle artifact reduction vs prior relief mapping — Tatarchuk, I3D 2006 | **P** | https://dl.acm.org/doi/10.1145/1111411.1111423 |
| Relief mapping of non-height-field surface details (family extension) — Policarpo & Oliveira, I3D 2006 | **P** | https://dl.acm.org/doi/10.1145/1111411.1111422 |
| Cone step mapping (Dummer): per-texel empty-cone map for safe steps; relaxed cones trade one overshoot for fewer steps + binary refine — as documented in GPU Gems 3 ch. 18 (Policarpo & Oliveira) | **P** (Dummer's original attributed via GPU Gems 3; original whitepaper not fetched) | https://www.oreilly.com/library/view/gpu-gems-3/9780321545428/ch18.html |
| Quadtree displacement mapping with height blending: top-down pyramid traversal for material displacement, ~66% step reduction claim — Drobot, GPU Pro (GDC 2010 talk) | **P/T** | https://www.gamedevs.org/uploads/quadtree-displacement-mapping-with-height-blending.pdf · https://www.gdcvault.com/play/1012014/Quadtree-Displacement-Mapping-with-Height |
| DXR/Vulkan RT: intersection shaders only for procedural AABB geometry; costlier than built-in hardware triangle tests; BLAS structure differs for procedural vs triangle | **P/D** (Proceduray paper + Ray Tracing Gems II Vulkan chapter) | https://arxiv.org/pdf/2012.10357 · https://link.springer.com/content/pdf/10.1007/978-1-4842-7185-8_16.pdf |
| Opacity micromaps: hardware-visible opacity classification for ray traversal; alpha-tested geometry use, not displacement | **D** | https://microsoft.github.io/DirectX-Specs/d3d/Raytracing.html · https://registry.khronos.org/vulkan/specs/1.3-extensions/man/html/VK_EXT_opacity_micromap.html |
| Displacement micromaps: displaced microtriangle geometry; Vulkan vendor extension and capability-sensitive adoption | **D/?** | https://registry.khronos.org/vulkan/specs/1.3-extensions/html/chapters/VK_NV_displacement_micromap.html |
| Max-mip machinery reused for terrain soft shadows (post-2008 continuation) | **P** (seen in results, not fetched) | https://arxiv.org/pdf/2005.06671 |
| View-plane-parallel line marching avoids fisheye; pitch-as-horizon-shift, roll-as-column-shear approximations | **F** (folklore consistent with s-macke construction) | — |
| Analytic normals/motion vectors over screen derivatives for marched hits; SV_Depth vs early-Z; conservative-depth workaround | **F/D** (standard practice; conservative depth is API-documented) | — |
| Max-reduce for ray pyramid vs min-reduce for occluder proxy (opposite conservative directions) | **F** (this skill's `08`/`10` conventions, consolidated) | — |
| "Raster-primary + RT-secondary with triangulated terrain proxy is the 2026 default"; hardware displacement/micromap trajectory | **?** (directional industry read; verify against current vendor docs) | — |
| Cone-map bake cost "minutes for large maps"; POM sample counts; hybrid seam-morph details | **F/?** (order-of-magnitude practice, not benchmarked here) | — |
