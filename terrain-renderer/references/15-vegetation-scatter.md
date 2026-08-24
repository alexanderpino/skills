---
# --- okf v0.2, written by tools/okf_apply.py -----------------------
type: Reference
title: "Vegetation & scatter rendering"
description: "Vegetation and scatter rendering: instancing, impostors, density fields and the LOD boundary where a plant stops being geometry."
tags: [terrain, vegetation, scatter, instancing]
status: stable
generated: { by: process:claude-code, at: 2026-07-30T09:56:09+02:00 }
# --- end okf v0.2 ----------------------------------------------------
---
# Vegetation & scatter rendering

The generator decides what grows where — terrain-architect `07`/`13` own the placement algorithms
(Poisson disk, density fields, ecosystem simulation) and its `27` ships the results as instance
sets and density/biome maps. This chapter owns turning those into pixels: millions of instances
under a terrain-scale budget, grass generated on the GPU around the camera, trees carried to the
horizon by impostors, and every instance seated on, lit with, and weathered like the terrain it
stands on. Vegetation is where terrain renderers most often lose the frame — not in the terrain
passes but in the overdraw and submission storm sitting on top of them. Leaf/canopy BRDF and
translucency math route to physically-based-rendering; this chapter is systems and budgets.

Contents: [Historical transition](#the-historical-transition-placement-moved-to-the-gpu-seating-became-stricter) ·
[The two pipelines](#the-two-pipelines) ·
[GPU instancing architecture](#gpu-instancing-architecture) · [Grass systems](#grass-systems) ·
[Tree, rock, and prop LOD chain](#tree-rock-and-prop-lod-chain) ·
[Culling & submission](#culling--submission) ·
[Consistency with the terrain](#consistency-with-the-terrain) ·
[Streaming & memory](#streaming--memory) · [The tri-fold ladder](#the-tri-fold-ladder) ·
[Pitfalls](#pitfalls) · [Sources](#sources--provenance)

## The historical transition: placement moved to the GPU, seating became stricter

Early terrain engines placed trees and grass on the CPU, instantiated a bounded list, and baked
each transform against the source heightmap. That matched fixed terrain meshes and short draw
distances. Open worlds broke both assumptions: millions of anonymous instances made CPU
placement/storage/submission dominant, while geomorphing and displacement made the source
heightfield differ from the surface on screen.

The modern pipeline therefore moves anonymous scatter generation, culling, compaction, and
submission to the GPU — but **GPU placement is not permission to approximate the ground**.
Instances must snap to the same evaluated LOD/morph/displacement surface the terrain draws.
Otherwise the pipeline efficiently generates a million floating objects.

## The two pipelines

All scatter rendering is one of two pipelines, and most shipped games run both. Choosing which
category each asset class belongs to is the first design act:

| | Shipped instance sets | Runtime procedural scatter |
|---|---|---|
| What ships | baked transforms per tile (terrain-architect `27`), streamed with tiles (`06`) | density/biome/type maps only; instances exist transiently on the GPU |
| Generated | offline, full placement algorithm budget | per frame/per cell, in compute, camera-local |
| Storage | bytes per instance × world count — real memory | zero world-proportional storage |
| Range | to the horizon (via LOD/HLOD chain) | a camera radius (grass ~50-150 m, detail props ~30-80 m) |
| Editability | artists can touch individual instances | only via the maps; no per-instance authorship |
| Gameplay | can have identity (chop THIS tree, loot persists) | anonymous; nothing may depend on a specific instance |
| Typical use | trees, rocks, buildings, hero props | grass, weeds, pebbles, flowers, forest-floor litter |

**When each wins.** Baked sets win when instances need identity, persistence, artist overrides, or
visibility beyond the generation radius. Runtime scatter wins when counts are enormous, per-unit
value is negligible, and the camera radius covers every distance at which the asset reads —
grass at 300 m is a material tint (`07`), not instances. Horizon Zero Dawn pushed the runtime
path unusually far (GPU placement of props and even wildlife spawn hints from artist-authored
density graphs, GDC 2017); Ghost of Tsushima ran its grass entirely procedurally on the GPU
while trees stayed placed assets. The hybrid is the norm: baked skeleton, procedural flesh.

**The determinism contract.** Runtime scatter must be a pure function of world position and the
shipped maps — the mirror of terrain-architect's seed doctrine on the rendering side:

```hlsl
// One instance slot of one world cell. Inputs: cell coord + slot index. NOTHING else.
uint   seed   = Hash(cellCoord.x, cellCoord.y, slotIndex);      // world-cell hash — never frame
float2 jitter = float2(UnitFloat(seed), UnitFloat(seed * 0x9E3779B9u));
float2 posXZ  = cellOriginXZ + jitter * cellSize;
float  d      = SampleDensity(posXZ);                            // generator maps via `14`
if (UnitFloat(seed * 0x85EBCA6Bu) >= d) return;                 // survival roll — stable per slot
float3 posWS  = float3(posXZ.x, SampleRenderedHeight(posXZ), posXZ.y);
Emit(posWS, TypeFromMaps(posXZ, seed), ScaleRotColor(seed));
```

Hash from the **world cell and slot**, never from frame index, camera position, thread launch
order, or generation-radius entry order. Violate this and grass re-rolls every time the camera
re-approaches (the field visibly reshuffles), save/load screenshots diverge, and multiplayer
clients disagree about what is where. The survival roll must come *before* any camera-dependent
logic: density decides existence, the camera only decides whether an existing instance is drawn.
This is also what makes staggered generation legal — a cell generated this frame or in ten
minutes produces bit-identical instances.

## GPU instancing architecture

The scatter renderer is a specialization of the `08` pipeline — persistent GPU scene, compute
culling, indirect submission — with generation added at the front:

1. **Coarse cell cull.** The world around the camera is a grid (or 2-3 nested grids, clipmap
   style) of scatter cells, 8-32 m for grass, larger for props. Frustum + distance + HiZ-test the
   *cells* first (`08`) — a cell behind a ridge generates nothing. Cheap max-density-per-cell
   metadata (from the generator's tile stats) lets empty desert cells exit before dispatch.
2. **Fine generation/expansion.** Surviving cells dispatch one thread per instance slot: runtime
   cells run the hash-and-sample loop above; baked cells expand their streamed instance list.
   Per-instance culling (frustum, HiZ, distance band per type) happens here, in the same pass.
3. **Append & compact.** Survivors append packed instance records into per-type buckets
   (`InterlockedAdd` on a counter per mesh/material bucket); a tiny pass copies counters into
   indirect argument buffers.
4. **Indirect draw.** One `DrawIndexedInstancedIndirect`/multi-draw per bucket per pass. The CPU
   never learns the counts (`08`'s readback discipline — debug HUDs read them frames late).

**Instance record compression.** At millions of instances, record size is the memory *and* the
bandwidth budget. Position is quantized relative to the cell (the cell origin is the shared
anchor — this is also the planetary-precision answer, `09`: cells are patch-local frames):

| Field | Encoding | Bits |
|---|---|---|
| Position XZ | UNORM relative to cell | 2×16 |
| Height | offset from terrain height at XZ (often implicit = 0) | 0-16 |
| Yaw | UNORM angle (full quat only for slope-aligned types) | 8 (or 32 smallest-three) |
| Uniform scale | UNORM in [min,max] per type | 8 |
| Type/mesh index | bucket-local | 8-10 |
| Color/variation | index into per-type palette, or hue jitter | 8 |

8-16 bytes/instance is the target; a naive float4x4 is 64 and will be the bandwidth bottleneck
of the whole system. Decode in the vertex shader from the cell constants. Baked sets ship in the
same packed form inside tile payloads (`06`), so streamed and generated instances flow through
one culling/submission path.

**Density modulation is a read, not a rule.** The density the survival roll consumes is the
generator's field composed with the runtime aux-map stack (`14`): biome/type maps select species,
slope limits gate placement (grass to ~35-45°, trees less — but the *generator* owns those rules;
the renderer only samples the resulting field), wetness shifts species weighting where the maps
say so, snow depth (`13`) suppresses or swaps low scatter. Re-deriving placement rules in the
scatter shader ("if slope < X and altitude < Y") forks the generator's logic and the two
inevitably diverge — `14`'s consistency rule applies: sample the shipped fields, don't re-decide.

**Pitfall:** appending unbounded. Size append buffers for the worst *legal* case (max density ×
cell count at radius) and clamp with a counter test in the shader; an overflowing append buffer
under a debug camera in a meadow is a device-removed, not a slowdown. Assert occupancy in `11`'s
soak tests.

## Grass systems

Grass is the runtime-scatter pipeline at its extreme: the highest instance counts, the shortest
lifetime, the tightest per-instance budget. The reference point is Ghost of Tsushima (GDC 2021):
blades generated in compute in tiles around the camera, culled in stages before any vertex work,
~2.5 ms for the whole system on PS4 with on the order of 10⁵ blades surviving to raster.

**Blade geometry options:**

| Option | Mechanism | Cost/quality | Use |
|---|---|---|---|
| Cross-quads (2-3 crossed textured quads) | classic alpha-tested card clumps | cheapest; flat lighting, heavy overdraw | indie tier, mobile, far band |
| Procedural blades, vertex-pulled | compute emits blade records; VS builds 5-15 verts/blade from a curve, no alpha test | mid; per-blade motion, near-zero overdraw waste | the modern default near band |
| Bezier blades (Tsushima family) | blade = cubic Bezier spline; VS evaluates curve, widens, twists; tip/curvature animated by moving control points | high quality; wind bends the *curve*, not a bake | AAA near band |
| Mesh-shader blades | amplification stage does per-blade cull + LOD (vert count per blade by distance) | same look, better scaling on modern HW | AAA, HW permitting |

Two Tsushima details worth stealing regardless of tier: **view-space widening** — blades nearly
edge-on to the camera get stretched sideways a pixel or two in view space, otherwise fields
shimmer with sub-pixel blades (specular AA doctrine applied to geometry); and **stage the culls**
— distance, frustum, occlusion, then per-blade LOD (vertex count and density both fall with
distance) so the vertex shader only ever sees survivors.

**Clumping.** Uniform-random blades read as carpet. Generate clump centers with a coarser hash
tier (same determinism contract, larger cells); blades inherit clump identity — shared lean
direction, height multiplier, type, slight color pull toward the clump — plus per-blade jitter.
Two hash tiers cost almost nothing and produce the patchy, combed look of real fields.

**Hierarchical wind.** One layer of sine wind reads as jelly. The shipped decomposition
(Tsushima's wind talk, GDC 2021, is the canonical writeup) is three bands:

1. **Global gusts**: a scrolling low-frequency 2D field (noise or a tiny fluid step) in world
   space, giving whole-field waves that travel — direction comes from the generator's wind
   vectors (`14`), which carry crest speed-up and lee shelter; never a global constant.
2. **Local turbulence**: mid-frequency perturbation (Tsushima advects "vorticle" particles that
   stamp rotational impulses into the wind field; scrolling curl noise is the budget version).
3. **Per-instance phase**: hash-derived phase/stiffness offset so identical neighbors never move
   in lockstep.

Blades consume the summed field by bending their curve (control-point displacement scaled by a
height^k profile so roots stay planted); trees consume the *same field* at branch/trunk
frequencies. The moment grass and canopies sample different wind sources, the world visibly
splits in two — one wind system, many consumers, always.

**Player/object bending** is `13`'s deformation machinery verbatim: the same top-down deformer
capture that carves snow writes a displacement/flatten target around the camera; grass samples
it, bends radially away from the deformer, and recovers with a spring over seconds. Build it
once, feed both consumers. Persistent flattening (trampled paths) is the `13` persistence table
applied to a grass-state target.

**Light grass with the terrain's normal.** A blade shaded by its own geometric normal alternates
lit/unlit per blade and the field sparkles. Ship the read the industry converged on: normal =
terrain normal (the same band the terrain samples at that distance, `10`) for the diffuse term,
optionally bent slightly along the blade near the camera for shape; ambient occlusion darkening
toward the root (cheap fake AO gradient); a wrapped-diffuse or thin-translucency term for
backlit blades (math routes to physically-based-rendering). This *seats* the grass — the field
inherits the terrain's light gradients and reads as one surface with fur, not as clutter on top.
Sample terrain albedo underneath for the base color (below) and the seating completes.

**Shadow participation policy** — decide it, don't discover it in a capture:

| Policy | Cost | Read |
|---|---|---|
| No grass shadows, AO gradient only | ~free | fine for short grass; tall grass floats at low sun |
| Grass receives, never casts | cheap (sampling only) | the usual shipping default |
| Casts into nearest cascade only | moderate; regenerate/redraw for that cascade with caster logic (`08`) | tall grass grounds at golden hour |
| Casts into all cascades / VSM | severe — and wind invalidates cached VSM pages every frame | almost never worth it; fake far grass shadow as a density-driven darkening in the terrain material |

**Density fade at the radius.** Never let the generation radius be a visible wall (the pitfall
list below). Pre-roll density downward over the outer 20-30% of the radius, shrink blade height
toward zero through the band (a zero-height blade is an invisible pop), and hand off to the
material band: a grass-colored roughness/albedo response in the terrain splat (`07`) so the
ground beyond the radius still reads as grassland. The handoff tone must match the lit grass or
the radius returns as a color ring — calibrate with `11`'s worst-case-view capture.

## Tree, rock, and prop LOD chain

The baked-instance pipeline's problem is range: a tree must survive from 2 m to 20 km. The chain
that ships, near to far — each link cut by screen-space error (`01`'s currency), not authored
distances:

**1. Mesh LODs** (full material, wind-animated) for the near field. Vegetation-specific rule:
reduce *element count*, not just triangle count — fewer, larger leaf cards at each step, with
alpha coverage preserved (below). Cross-fade links by dithered opacity resolved by TAA.

**2. Octahedral impostors** for the mid-to-far field — the modern replacement for single
billboards, canonicalized by Ryan Brucks' writeup. Bake the tree from viewpoints on an
octahedral (or hemi-octahedral, for ground-dwelling cameras) direction lattice into an atlas;
at runtime pick the 3 nearest views, blend, and parallax-correct. The load-bearing details:
bake **normals + depth per view**, not just albedo — the impostor is *lit at runtime* with the
scene's sun and shadowing, and depth enables parallax correction plus depth-writing so impostors
intersect terrain and each other correctly. A well-built impostor holds up until the object is
tens of pixels; the handoff from LOD meshes is a dithered cross-fade over a distance band.
Frame-blend or increase view count when the swimming between views shows on hero silhouettes.

**3. Billboard clouds / merged far forest.** Beyond impostor-per-instance range, instances stop
existing: merge whole tiles' canopies into HLOD proxy meshes or coarse card clusters with baked
lighting response — this is `06`'s HLOD machinery; the forest becomes terrain-with-height. The
transition is the hardest seam in the chain: match aggregate color/normal statistics between the
impostor field and the merged proxy or the forest changes tone at a visible ring. Apply `10`'s
Rayleigh/Mie aerial perspective at runtime to impostors and HLOD with the same distance input as
terrain; never bake a fixed fog/sky color into the atlas under a dynamic atmosphere.

**Trees in the `02` cluster path.** Nanite-family renderers can carry bark/trunk/rock geometry
beautifully, but foliage is **aggregate geometry** — thousands of disjoint leaf cards — and
aggregates break cluster simplification and occlusion assumptions: simplifying deletes elements,
so canopies visibly thin with distance, and dense semi-open canopies defeat HiZ. Epic's
documented mitigation (Preserve Area — dilate remaining elements to conserve surface area) makes
Nanite foliage shippable but not free; rocks and trunks are excellent cluster citizens, canopies
remain a specialized problem. Evaluate with `11` captures at forest scale before committing.

**Alpha strategy** — the defining material decision for vegetation:

- **Alpha test + TAA** is the shipping default: opaque-pass depth writes, correct sorting for
  free, TAA softens the hard edge. Cost: TAA flicker on thin geometry (mitigate with the
  view-space widening idea and coverage-correct mips).
- **Dithered opacity** (stochastic transparency resolved by TAA) for LOD cross-fades and soft
  edges without a blend pass.
- **Alpha blending** is reserved for tiny accents; sorted-blend forests are unshippable.
- **Alpha-to-coverage** with MSAA: hardware-dithered coverage from alpha; Ben Golus' writeup is
  the practical reference (including sharpening alpha to restore edge contrast). Where MSAA
  exists (VR, forward renderers), it is the quality answer.

**Hardware-RT note.** On OMM-capable DXR/Vulkan paths, opacity micromaps can classify much of an
alpha-tested card as opaque or transparent during traversal and reduce expensive any-hit shader
work for vegetation shadows/reflections (`18`). They do not reduce raster overdraw, repair bad
coverage mips, or solve canopy LOD; OMM is an RT traversal optimization, not a replacement for
this chapter's alpha and geometry discipline.

**Alpha-test mip shrinkage.** Standard mip generation averages alpha downward, so coverage falls
with each mip and distant trees *thin out and vanish* — the classic symptom Castaño documented on
The Witness. Fixes, in order of adoption: scale each mip's alpha to preserve the base level's
coverage (the de-facto standard; do it in the importer, assert it in `11`'s pipeline checks);
alpha-to-coverage with per-mip rescaling; or compute alpha distance fields. If distant vegetation
looks anorexic, check the mips before touching LOD.

**Overdraw is the #1 vegetation perf killer.** Every alpha-tested quad pays full pixel-shader
cost for its transparent texels, and vegetation stacks dozens deep. Doctrine: keep card counts
low and cards *tight* to the silhouette (shrink-wrapped geometry beats big quads — Horizon's
vegetation talk is explicit about geometry-vs-texture trade discipline); draw near-to-far within
vegetation buckets when cheap (depth rejection does the rest); prepass-then-shade or visibility
buffer (`08`) decouples the storm from material cost; and *measure* with an overdraw debug view
(`11`) from the worst view — a valley of grass and canopy seen from a peak — not from a pleasant
meadow at eye level.

## Culling & submission

All `08` machinery applies per-instance; the vegetation-specific policy layer:

| Type | Distance policy |
|---|---|
| Grass/detail scatter | hard radius 50-150 m (density pre-rolloff), then material-band handoff |
| Bushes/mid props | 100-400 m, impostor optional |
| Trees | mesh LOD to ~100-300 m → impostor to km → merged HLOD to horizon (`06`) |
| Rocks/hero props | screen-size-cut like any static mesh; cluster path if `02` is live |

- **Per-instance frustum + HiZ** in the generation/expansion pass — one AABB or bounding-sphere
  test per instance against the depth pyramid (`08`'s two-phase discipline; instances test
  against phase-1 depth, false negatives re-drawn in phase 2). Instance bounds must include wind
  excursion and scale variation, or gusts make edge-of-screen trees flicker (conservative-bounds
  rule, `08`).
- **Terrain-ridge occlusion** is the vegetation jackpot: the heightfield max-mip occluder (`08`)
  kills entire forests behind ridgelines for microseconds of compute. In hilly worlds this
  routinely outperforms every other cull for scatter; wire it before tuning anything finer.
- **Shadow passes cull with caster logic** (`08`/`10`): an off-screen tree still shadows the
  frame — cull against the light frustum + receiver volume, not the camera. And *regenerate
  nothing per pass*: the same instance survivor set feeds camera and shadow submissions with
  per-pass visibility masks. Regenerating scatter per cascade with different traversal order is
  the direct cause of shadow swimming (pitfalls below).
- Distance cutoffs are per-type and *hysteretic* — a cutoff without a band oscillates instance
  existence at the boundary and TAA smears the flicker into crawl.

## Consistency with the terrain

Vegetation belongs to the terrain; four contracts keep it there.

**Sit on the RENDERED surface, not the source heightfield.** The terrain the player sees is the
LOD'd, morphed, displaced surface of `01`/`02` — coarser and displaced relative to the source
field, increasingly so with distance. Instances placed at source-heightfield height float or
sink exactly where the discrepancy grows (`11` catalogues the symptom: hovering trees at 500 m,
buried rocks in morph bands). The fix is a contract, not a nudge: the scatter height sampler
evaluates the **same function the terrain vertex path evaluates** — same tile mips, same
geomorph factor at that distance, same displacement — ideally by sharing the actual shader
function. For baked sets, bake a height *offset from the source field* and re-add it to the
rendered height at runtime, so the instance rides LOD transitions with the ground under it.
Geomorphing terrain implies instances subtly ride morphs; that is correct and invisible, whereas
a static height against a morphing ground is a visible float/sink pulse.

```hlsl
// Shared-evaluator contract: identical inputs and function to the terrain vertex path.
TileLOD lod     = SelectTerrainLOD(worldXZ, camera);
float   morphT  = TerrainMorph(worldXZ, lod, camera);
float   groundY = EvalTerrainHeight(worldXZ, lod, morphT, displacementState);
instanceWS.y    = groundY + bakedRootOffset;
```

**Symptom → mechanism → fix:** trees pulse above/below the ground only inside morph bands →
scatter sampled source/LOD0 height while terrain interpolated toward its parent → share the
terrain evaluator and its runtime morph factor. For `02` cluster terrain, expose a stable surface
query/proxy because there may be no analytic grid morph function; the contract is shared evaluated
surface, not a particular API.

**Slope alignment per type.** Grass and small scatter align to the terrain normal (inherit it
outright — its shading normal already is the terrain's); rocks blend toward it; trees stay
gravity-upright with only their root spread conforming (real trunks grow vertically on slopes).
One wrong policy — upright grass cards on a 35° hillside, or trees leaning with the slope —
reads instantly wrong. The alignment normal is the *geometric* terrain normal at placement scale
(`10`'s band discipline), not the detail normal.

**Color harmonization.** Sample the terrain's resolved albedo (VT/RVT page or splat result, `07`)
at each grass instance and pull the blade base color toward it (typical: lerp 30-70% at the
root, fading up the blade). This is the single highest-value trick in grass rendering: it kills
the striping where a uniform grass green crosses splat transitions, makes biome/wetness/scorch
variation in the maps propagate into the grass for free, and unifies the radius handoff (the
material-band grass beyond the radius *is* that albedo). UE's Landscape grass output and RVT
sampling (`03`) is the engine-native version of the same idea.

**One weather system.** Whatever `13` did to the ground applies to what stands on it: snow
coverage tints and loads canopies (same potential envelope and up-facing bias, evaluated on the
impostor/canopy normal), wetness darkens grass and drops its roughness with the same porosity
staging, and the deformation targets that carve snow also flatten grass. The test is a single
capture: if the ground is snowed and the grass is summer-green, the world has two weather
systems — the pitfall is shipping exactly that because vegetation shaders were written before
`13` existed. Impostor atlases need the weather applied at runtime (they were baked dry and
bare); bake a canopy-up mask into the atlas so runtime snow knows where to land.

## Streaming & memory

- **Baked instances stream with tiles** (`06`): packed records in the tile payload, uploaded
  into per-tile pool ranges inside the persistent GPU scene (`08`); eviction frees the range.
  No per-instance CPU objects — 400k trees as engine actors is an entity-system outage, not a
  rendering strategy.
- **Runtime scatter is regenerated, never stored** — that is its entire value. Persist only
  deltas with gameplay meaning (cut grass, trampled paths) as sparse state layers (`13`'s
  persistence table), composed over regeneration. Cache-and-keep of generated cells is legal as
  a transient ring (regeneration amortization), but must survive being dropped at any time.

| Category | Live count (order) | Bytes/inst | Memory | Notes |
|---|---|---|---|---|
| Grass blades/patches (runtime) | 10⁵-10⁶ survivors | 8-16 transient | 2-16 MB GPU ring | regenerated; ring sized for worst legal density |
| Detail props (runtime) | 10⁴-10⁵ | 8-16 transient | ~1-2 MB | same path as grass, larger cells |
| Trees/rocks (baked, resident tiles) | 10⁴-10⁵ | 12-24 streamed | 1-10 MB + meshes | packed records; meshes shared |
| Impostor atlases | 10-100 types | — | 30-150 MB | the real memory line; compress (BC7), budget per biome |
| Merged far forest (HLOD) | per `06` budget | — | in `06`'s sheet | |

Numbers are order-of-magnitude for current consoles; assert your own per `11`'s budget doctrine.

**Edit invalidation.** Terrain edits re-scatter: a height/splat edit invalidates the scatter
cells and baked-instance heights it touches (re-sample heights at minimum, re-roll density where
splat/biome changed). Voxel worlds (`04`/`05`) fold this into the remesh pipeline — scatter for
a chunk regenerates from the *new* surface (which may have changed topology, not just height)
in the same job chain, or freshly dug tunnels keep grass floating where the ground was. Editor
tools (`16`) need the same invalidation path at interactive rates — a sculpt brush that leaves
stale scatter behind makes the preview lie.

## The tri-fold ladder

| Tier | Placement | Grass | Trees | Culling |
|---|---|---|---|---|
| Indie / baseline | CPU expansion of baked sets + hash scatter per cell (same determinism contract, CPU-side) | cross-quad clumps, instanced draws, sine-noise wind, terrain-normal lighting | 2-3 mesh LODs → single cross-billboard; coverage-scaled mips from day one | frustum per cell + per-type distance; sort buckets near-to-far |
| Tool viewport (`16`) | preview the generator's density/type maps live — scatter is a *visualization of the fields*, regenerated on every map edit (determinism makes this free) | representative patch rendering, density heat-map overlay toggle | proxy meshes/impostors; counts and budgets displayed, not hidden | simple + robust; correctness of preview > frame perfection |
| AAA | full GPU pipeline: cell cull → compute generate/expand → compact → indirect (`08`) | Bezier/mesh-shader blades, hierarchical wind from `14` vectors, deformation bending, albedo harmonization | LOD → octahedral impostors (normals+depth) → HLOD forests (`06`); `02` path for trunks/rocks | two-phase HiZ per instance, ridge occluder, caster-logic shadow sets |

The ladder is capability, not quality of contract: the determinism rule, the rendered-surface
seating rule, and the mip-coverage rule bind all three tiers — they cost nothing and their
absence is visible at every budget.

## Pitfalls

- **Grass wall at the generation radius** — full density to the edge, then nothing. Pre-roll
  density and height across the outer band, hand off to the material tint, and verify in motion:
  the radius must not be findable in a flythrough capture (`11`).
- **Scatter hashed from frame state** (camera, time, traversal order) — fields reshuffle on
  re-approach, clients diverge. Hash world cell + slot, nothing else.
- **Shadow swimming from per-pass regeneration** — scatter regenerated per cascade/pass with
  different order or seeds; shadows crawl against the base pass. One survivor set per frame,
  per-pass masks.
- **Instances on the source heightfield** — trees float/sink where LOD diverges from source.
  Sample the rendered surface function; bake offsets, not absolute heights.
- **Terrain-normal mismatch** — grass lit by per-blade normals sparkles; grass lit by a *stale*
  or differently-banded terrain normal stripes against the ground at LOD changes. Same normal,
  same band, same source texture as the terrain pass.
- **Wind desync** — grass, canopy, cloth, and VFX sampling different wind sources or the same
  source at different latencies; the world splits into layers. One wind field (`14`), all
  consumers, same frame's values.
- **Alpha overdraw storm in the worst view** — a canopy-and-grass valley from a peak: dozens of
  layers of mostly-transparent texels. Budget from that capture (`11`'s worst-case-view is the
  spec); tight cards, prepass/visibility-buffer shading, overdraw debug view in CI.
- **Distant trees thinning to nothing** — coverage-losing mips (Castaño's symptom) or aggregate
  simplification (`02`/Nanite without area preservation). Fix the mips/build settings; do not
  compensate with bigger LOD distances.
- **Impostor lighting mismatch at the seam** — impostor band visibly flatter/darker than mesh
  band. Bake normals+depth, light impostors through the same BRDF path, include them in the same
  shadow/AO terms, and cross-fade — a hard switch makes even a perfect match pop.
- **Grass casting into cached VSM pages** — wind invalidates every page every frame; the shadow
  budget silently triples. Exclude wind-animated scatter from cached-shadow paths by policy.
- **Append-buffer overflow in the meadow debug camera** — size for worst legal density, clamp in
  shader, assert occupancy in soaks.
- **Two weather systems** — snow/wet ground under dry green vegetation (`13`). Weather state
  applies to everything standing on the terrain, impostors included.

## Sources & provenance

| Claim | Tier | URL |
|---|---|---|
| GPU-generated procedural grass: compute generation around camera, staged culling, Bezier-curve blades, view-space widening, ~2.5 ms class budget — "Procedural Grass in 'Ghost of Tsushima'", Eric Wohllaib, GDC 2021 Advanced Graphics Summit | **T** | https://www.gdcvault.com/play/1027033/ |
| Hierarchical wind: global vector + advected vorticle turbulence, one field consumed by grass/cloth/particles — "Blowing from the West: Simulating Wind in 'Ghost of Tsushima'", Bill Rockenbeck, GDC 2021 | **T** | https://gdcvault.com/play/1027124/Blowing-from-the-West-Simulating |
| Runtime GPU placement from artist-authored density graphs, world assembled around the player — "GPU-Based Run-Time Procedural Placement in 'Horizon: Zero Dawn'", Jaap van Muijden, GDC 2017 | **T** | https://gdcvault.com/play/1024700/GPU-Based-Run-Time-Procedural |
| Vegetation asset/shading/shadow discipline, geometry-vs-texture trade, optimization workflow — "Between Tech and Art: The Vegetation of 'Horizon Zero Dawn'", Gilbert Sanders, GDC 2018 | **T** | https://www.gdcvault.com/play/1025530/Between-Tech-and-Art-The |
| Octahedral impostors: octahedral view lattice, 3-view blend, normals/depth capture, parallax correction — Ryan Brucks, Shader Bits | **F** (canonical community writeup) | https://shaderbits.com/blog/octahedral-impostors |
| Alpha-test mip coverage loss and coverage-preserving mip scaling — Ignacio Castaño, "Computing Alpha Mipmaps", The Witness blog, 2010 | **F** (de-facto industry standard) | http://the-witness.net/news/2010/09/computing-alpha-mipmaps/ |
| Survey of alpha mip strategies incl. distance fields | **F** | https://lisyarus.github.io/blog/posts/exploring-ways-to-mipmap-alpha-tested-textures.html |
| Alpha-to-coverage practice, alpha sharpening for A2C — Ben Golus, "Anti-aliased Alpha Test" | **F** | https://bgolus.medium.com/anti-aliased-alpha-test-the-esoteric-alpha-to-coverage-8b177335ae4f |
| Early instanced-grass canon (batched quads, wind waving) — Kurt Pelzer, GPU Gems ch. 7 | **P/D** | https://developer.nvidia.com/gpugems/gpugems/part-i-natural-effects/chapter-7-rendering-countless-blades-waving-grass |
| Aggregate geometry breaks cluster LOD/occlusion; canopy thinning; Preserve Area dilation — Epic, "Nanite Foliage" / Nanite docs | **D/N** | https://dev.epicgames.com/documentation/unreal-engine/nanite-foliage?lang=en-US |
| Billboard clouds for extreme simplification (Décoret et al., SIGGRAPH 2003) | **P** (attribution from memory, not re-verified) | — |
| GPU-driven cull/compact/indirect pipeline this chapter specializes | **T** (via `08`: Haar & Aaltonen 2015 et al.) | — |
| Instance record packing sizes, budget table, distance bands, harmonization lerp ranges | **F** (order-of-magnitude shipping practice; assert per project, `11`) | — |
| Determinism contract (world-cell hashing) as mirror of generator seed doctrine | **D** (terrain-architect `07`/`27` contract) | — |
