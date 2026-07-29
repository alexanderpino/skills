# Engine-Native Terrain: Unreal Landscape & Friends

This chapter owns the engine-native terrain systems — primarily Unreal's Landscape and its UE5
satellites (Nanite Landscape, RVT, World Partition), with a comparative appendix for Unity, Godot,
O3DE, and CryEngine. It exists because engine terrain is a *contract you inherit*, not an
architecture you choose: the win is knowing which knobs map onto the theory in `01`/`02`/`07`, and
where the engine's fixed decisions will fight you. Almost everything here is D/N-tier — vendor
documentation and engine-branded feature names — and engine internals drift by version, so
version-sensitive claims are tagged `?` rather than asserted as permanently true.

Contents: [Landscape anatomy](#landscape-anatomy) ·
[Height & weight storage](#height--weight-storage) · [Runtime LOD](#runtime-lod) ·
[Nanite Landscape](#nanite-landscape) · [Materials & RVT](#landscape-materials--rvt) ·
[World scale](#world-scale-world-partition--lwc) ·
[Import / roundtrip](#import--roundtrip-contract) ·
[Performance doctrine](#performance-doctrine-checklists) ·
[Other engines](#appendix-other-engines-in-brief) · [Sources](#sources--provenance)

## Landscape anatomy

Unreal Landscape is a uniform-grid heightfield renderer with a fixed decomposition hierarchy:

```
Landscape (actor)
 └─ Components        — the render unit: culling, LOD, streaming, weightmaps, draw call
     └─ Sections      — 1×1 or 2×2 per component: the LOD-selection sub-unit
         └─ Quads     — section size is (2^n − 1) quads: 7, 15, 31, 63, 127, 255
```

The **component** is the atom of everything that matters at runtime: it is the frustum/occlusion
culling unit, the streaming unit (in World Partition), the weightmap-texture allocation unit, and —
on the traditional (non-Nanite) path — roughly one draw call per rendering pass (as of UE 5.x; the
exact batching behaves per-version, verify — **?**). Sections exist only to let LOD decisions
happen at finer granularity than the component without multiplying component overhead.

**The sizing math.** Component size in quads = section size × sections-per-side (1 or 2). Total
landscape resolution = (components-per-side × component-quads) + 1 vertices per axis — the `+1` is
the vertex-centred convention from terrain-architect `08`: N+1 samples span N cells, shared edge
vertices between components. This is why the "recommended" import resolutions are numbers like
1009, 2017, 4033, 8129: they are `k × quads + 1` for a legal quad count, and an arbitrary
power-of-two heightmap (4096²) does *not* fit and will be padded or cropped on import.

**Component count is the master performance dial.** For a fixed world size:

| Fewer, larger components | More, smaller components |
|---|---|
| Fewer draw calls, less per-component CPU overhead | More draw calls, more scene proxies |
| Coarser culling — big components stay visible longer | Tighter frustum/occlusion culling |
| Coarser streaming granularity in World Partition | Finer streaming, smaller memory spikes |
| LOD decided over a larger area (mitigated by 2×2 sections) | Finer LOD selection |
| Larger weightmap textures, fewer shader permutations | More permutations, more small textures |

Doctrine: keep total component count in the low thousands at most for a single landscape actor, and
prefer 2×2 sections to buy LOD granularity before shrinking components. Epic's own recommended-size
table changes across versions — recompute from the math above rather than quoting a stale table
(**?** verify current guidance).

**Edit layers** are a non-destructive stack of sculpt/paint layers merged (GPU-side) into the final
height and weight data — the analogue of the generation DAG's layer stack, but *editor-side only*:
the runtime sees the flattened result. **Landscape holes** are a visibility mask (the material's
Landscape Visibility Mask node) that kills pixels and — separately — collision; a hole is a
material+collision agreement, not a geometry edit, and the two can disagree (pitfall below).
**Splines** are editor tools that deform height and paint layers along a curve, then bake into the
same flattened data; they are authoring sugar, not a runtime primitive.

**Pitfalls.** (1) A hole punched in the material without the collision flag (or vice versa) gives
walk-on-air or invisible-wall bugs — the two channels are independent; test both, `11`. (2) Edge
vertices are shared between components; any tool that writes per-component data without
reconciling shared borders produces cracks — the engine handles this for its own tools, external
writers must too. (3) The vertex-centred `+1` convention: importing an `N`-pixel map into an
`N`-vertex landscape where the source was pixel-centred shifts the world half a cell against every
other authored asset (terrain-architect `08` owns this off-by-one).

## Height & weight storage

**Height is 16-bit, full stop.** Landscape stores height as unsigned 16-bit with 32768 = zero;
world height = `(value − 32768) / 128 × ZScale` cm, so at the default Z scale of 100 the range is
−256 m…+256 m with ~7.8 mm steps, and range scales linearly with Z scale while precision degrades
with it (512 m of range per 100 units of Z scale). Consequences, per terrain-architect `08`'s
precision doctrine: **quantise exactly once, at import**. The generation tool works and ships R32F;
the import step dequantises against the manifest's `heightRange` and requantises into the
landscape's 16-bit + Z-scale encoding. Never round-trip through the landscape's 16 bits and treat
the result as the source of truth — derivatives (normals, curvature, erosion re-runs) computed from
requantised height inherit terracing. Set Z scale from the *actual* height range, not a comfortable
default: a 9000 m mountain range at Z scale 100 clips; a 40 m island at Z scale 3200 wastes 15 of
16 bits and shows staircase normals in low-angle light.

**Weightmaps** are the engine-side splatmaps. Each painted layer needs a **Layer Info object**
(weight-blended or non-weight-blended); weight-blended layers are normalised so weights sum to 1
per texel. Storage is per-component: layers are packed **four channels per RGBA8 weightmap
texture**, and a component allocates as many weightmap textures as ⌈layers-touching-it / 4⌉. This
allocation is *per component*, which is the whole game: a landscape can use 20 layers globally and
stay cheap if any given component touches ≤ 4, because permutation and sampler cost follow the
per-component allocation, not the global palette (see Materials below).

**Pitfalls.** (1) Unnormalised weight input for weight-blended layers (imported masks that don't
partition) → the engine renormalises or leaves black holes where all weights are 0; the fix is
upstream — terrain-architect `06`'s partition rule — not in-engine painting. (2) A stray 1-texel
splat of a fifth layer on a component allocates a whole second weightmap texture *and* a new shader
permutation for that component; audit layer usage per component, don't trust the global count.
(3) Layer Info objects are assets — deleting/recreating one orphans painted data silently.

## Runtime LOD

The traditional Landscape path is a member of `01`'s quadtree-with-geomorphing family, with the
engine's own vocabulary: LOD is selected **per section** from screen size (projected size of the
section), and transitions use **continuous vertex morphing** between LOD levels rather than
discrete pops — the geomorph doctrine of `01`, implemented for you. Each LOD halves resolution;
the deepest usable LOD is bounded by section size. Controls (as of UE 5.x): *LOD 0 Screen Size*
(how long full resolution persists), and the *LOD Distribution* exponents that shape how quickly
successive LODs are reached; there is also a global `r.LandscapeLODBias`-style bias for scalability
tiers (**?** exact cvar names shift by version — verify).

Because LOD is screen-size driven, it is automatically resolution- and FOV-aware — do not
re-implement distance-band LOD on top of it. What you *do* own is the error budget: the engine
morphs geometry but does not know which frequencies your generator put in the heightfield; if the
gameplay-relevant relief lives in the top octave, aggressive distribution settings erase it
silently. Tie the LOD-0 retention distance to the view envelope declared at generation time
(terrain-architect `SKILL.md`, step 1).

**Shadow and collision LOD are separate from visual LOD**, and both mismatches are shipped bugs:

- Shadows may render the landscape at a different (biased) LOD than the camera sees → peter-panning
  or self-shadow acne along ridgelines where the shadow geometry disagrees with the visual
  geometry. Diagnose per `11`; the lighting integration doctrine is `10`.
- Collision uses a fixed mip of the heightfield (*Collision Mip Level*, plus a simpler mip for
  non-player collision). Collision mip > 0 means physics walks a decimated terrain: dropped
  items float or sink on slopes, precise traces (projectile decals, foot IK) hover. Rule: player
  and camera-adjacent collision at mip 0; raise the mip only for far/simple collision, and record
  the decision so QA knows the mismatch is intentional (`11`).

**Pitfall.** LOD morphing assumes the heightfield's own mips are a faithful low-pass of LOD 0.
If an external tool stamps runtime height changes into only the finest data, distant sections
render stale geometry — any runtime height write must update the full mip chain.

## Nanite Landscape

Enabling Nanite on a landscape (a per-landscape flag, UE 5.1+) builds a **Nanite cluster mesh per
component** from the heightfield — the landscape becomes a `02`-style virtualized-geometry citizen:
cluster culling, per-cluster LOD, no per-section geomorph, rasterised through Nanite's pipeline
instead of per-component draws. What you buy: dense geometry at near-constant cost, far better
silhouettes than the LOD ladder, and unified occlusion culling with the rest of the Nanite scene
(`08` owns the GPU-driven submission theory).

What it costs — and these are structural, not tuning issues:

- **The Nanite mesh is baked.** Every sculpt/paint edit requires rebuilding the affected
  components' Nanite meshes — an editor-time cost that scales with landscape size and makes
  iteration on huge worlds noticeably heavier. Budget for it in the authoring loop.
- **No runtime deformation on the Nanite path.** Runtime sculpting, crater stamping, tread
  displacement into the *rendered* terrain are not supported through the baked Nanite
  representation (as of UE 5.x — **?** verify per version; Epic iterates here). Games built on
  destructible/deformable ground should stay on the traditional path or own a custom `02`/`05`
  pipeline.
- **The non-Nanite data does not disappear.** Collision still comes from the heightfield, and a
  fallback path serves platforms/features Nanite doesn't cover (and ray tracing behavior is
  version-dependent — **?**). You ship both representations; keep them in agreement (`11`).

**Nanite tessellation & displacement** is the newer displacement path: heightfield/detail
displacement evaluated within Nanite itself, introduced experimentally around UE 5.3–5.4 and
maturing since. It is the intended successor to both legacy landscape tessellation (removed) and
the Virtual Heightfield Mesh detour. Treat its maturity, platform coverage, and cost model as
version-specific — **?** verify against current engine docs before committing a project to it.

**When NOT to use Nanite Landscape:** heavy runtime deformation gameplay; low-end targets where
Nanite is unsupported or unaffordable (mobile in particular); projects whose edit-rebuild cost on
massive worlds breaks the authoring cadence; or when you need exotic per-vertex runtime logic the
baked path can't express. The traditional path remains fully supported — it is not legacy (**?**
re-verify that statement each major version).

## Landscape materials & RVT

The landscape material graph blends painted layers with dedicated nodes: **Landscape Layer Blend**
(weight / height / alpha blend per layer), **Layer Switch** and **Layer Sample** for branching on a
layer's presence, **Layer Coords** for tiling UVs. Two cost structures dominate:

1. **Per-component shader permutations.** The engine compiles a material variant per distinct
   layer-set actually present on a component (branches for absent layers compile out). This is the
   mechanism that makes a 20-layer palette affordable — *if* discipline keeps most components on
   ≤ 4 layers. It is also a shader-count explosion if painting is careless: N layers scattered
   freely approaches 2^N permutations. Audit with the editor's layer-usage tooling.
2. **Sampler budget.** SM5-class limits (~16 unique samplers) arrive fast at 3–4 textures per
   layer × 4+ layers. Use shared samplers and/or texture arrays for layer texture sets; this is
   standard practice, not an optimisation (`07` owns the deeper material doctrine).

**Runtime Virtual Texture (RVT)** is a world-space GPU-side cache of composited material output:
the landscape (and anything else writing to the RVT volume) renders base color / normal /
roughness / height into virtual texture pages on demand; consumers then sample the cache instead of
re-evaluating the layered blend per pixel per frame. What it buys: (a) the expensive N-layer blend
is amortised — paid on page generation, not every frame; (b) **meshes and decals can blend into the
terrain** by sampling and/or writing the same RVT — the standard mechanism for rock bases, roads,
and splines that "sit in" the ground rather than on it. What it costs: a page-pool memory budget;
page-generation spikes on fast camera cuts (cache warm-up → visible low-res pages for a frame or
two); world-space baking, so anything view-dependent or high-frequency-animated can't live in it;
and a fallback path for platforms without VT support. Distinguish it from **Streaming Virtual
Textures**: SVT streams *authored* texel data from disk; RVT *renders* texels at runtime. Same page
machinery, opposite data source — the mechanics live in `07`.

**Virtual Heightfield Mesh** renders a displaced, adaptively tessellated mesh driven by an RVT
height channel — a pre-Nanite-displacement route to high-detail terrain relief. It shipped as an
experimental plugin and its role is largely superseded by Nanite displacement; treat as **?**
(status in current UE) before recommending it for new work.

**Pitfalls.** (1) RVT hides material cost until the cache misses — profile camera teleports and
fast traversal, not standing still. (2) Writing world-aligned detail into RVT at one resolution
and sampling at another aliases; match RVT resolution to the intended sampling footprint. (3) The
permutation and sampler pressure above interact: a "cheap" fifth layer can simultaneously add a
weightmap texture, a permutation, and blow the sampler budget on that component only — the bug
appears as one component failing to compile or rendering the error material.

## World scale: World Partition & LWC

**World Partition** (UE5) replaces World Composition with automatic grid-cell streaming: actors are
assigned to cells, cells load by distance, one-file-per-actor for concurrent editing. A landscape
under World Partition is split into **Landscape Streaming Proxies** — per-region actors each owning
a slice of components — so terrain streams with the same cell machinery as everything else. The
component-count dial above therefore also sets streaming granularity. **HLODs** are generated for
landscape so unloaded cells still render as cheap far proxies — budget HLOD generation time and
memory for large worlds, and re-generate after terrain edits or distant cells show stale ground.
**Data layers** gate actor sets (variants, story states); landscape proxies participate like any
actor.

**Large World Coordinates (LWC):** UE5 moved world positions to doubles CPU-side, with rendering
performed in a camera-relative (translated) space so the GPU still works in float near the origin.
For terrain this removes the classic far-from-origin vertex jitter *by default* — but custom
material world-position math, world-space RVT sampling, and anything that reconstructs absolute
world position in-shader can reintroduce float precision loss at large coordinates. The precision
doctrine — where jitter comes from and the camera-relative rebasing family of fixes — is `09`;
LWC is Unreal's implementation of one member of that family.

**Pitfalls.** (1) World Partition cell size vs. landscape proxy size mismatch → proxies straddling
cells load late or double; align the landscape grid to the WP grid. (2) HLOD landscape uses a
baked, simplified material — expect visible transitions if the full material relies on RVT or
distance-blended detail that HLOD doesn't reproduce; tune the transition distance where the swap
hides (`06` owns tiled-streaming doctrine; `11` catalogues the pop).

## Import / roundtrip contract

The generation side of this boundary is terrain-architect `08` (output contract) and `27` (engine
data handoff): the tool ships **causes** — R32F height, physical auxiliary fields, partitioned
masks, plus a manifest — and the engine converts them into its own encodings exactly once.

| Input | Engine expectation | Contract notes |
|---|---|---|
| Heightmap | 16-bit grayscale (PNG / raw R16) | Quantise from R32F at import using manifest `heightRange`; set Z scale from the same range, once |
| Resolution | `k × quads + 1` legal sizes | Vertex-centred; pad/crop decisions are yours, not the importer's silent ones |
| Weightmaps | 8-bit grayscale per layer | Must partition (sum to 1) for weight-blended layers — enforce upstream (`06`) |
| Layers | One Layer Info object per layer | Create before import; name-match to weightmap files |
| Tiles | Tiled import for World Partition | Shared-edge (vertex-centred) tiles; apron data from the manifest is for generation, not import |
| Auxiliary maps | Textures feeding the material / RVT | `27`'s registry: wetness, moisture, flow — imported as material inputs, not baked into albedo |

Roundtrip warning: exporting height back out of the engine yields the 16-bit quantised field. If
the generation graph must re-run (more erosion, new masks), re-run it from the tool's R32F master,
never from an engine export — the engine is an emitter target, not an archive (terrain-architect
`SKILL.md`, Part 2).

**Pitfalls.** (1) Importing at a non-legal resolution and letting the importer resample introduces
a resample nobody reviewed — resample in the tool, to a legal size, with a stated filter.
(2) Height and weightmaps authored on different grids (vertex- vs pixel-centred) land half a texel
apart — the shipped-bug of terrain-architect `08`. (3) A per-tile import that re-derives Z scale
per tile creates height discontinuities at tile borders; one Z scale for the whole world.

## Performance doctrine (checklists)

**Component & landscape setup**
- [ ] Component size chosen from the table above, stated with its reasoning; 2×2 sections before
      smaller components.
- [ ] Total component count budgeted against draw calls (traditional path) or Nanite rebuild cost.
- [ ] Landscape grid aligned to the World Partition grid; streaming proxy size deliberate.
- [ ] Z scale derived from actual height range; quantisation happens once, at import.

**Material & layers**
- [ ] Global layer palette may be large; per-component layer count capped (≤ 4 unless justified).
- [ ] Layer usage audited per component — no stray single-texel allocations.
- [ ] Shared samplers / texture arrays in the layer sets; sampler count verified on the worst
      permutation, not the average.
- [ ] RVT for layered-blend amortisation and mesh/terrain blending; page pool sized, camera-cut
      warm-up profiled; fallback path exists.

**LOD & representation agreement**
- [ ] LOD-0 screen size tied to the declared view envelope; distribution tuned by eye at the
      envelope's far end, not at the default camera.
- [ ] Collision mip explicit and recorded; player-space collision at mip 0.
- [ ] Shadow-vs-visual and Nanite-vs-fallback agreement spot-checked per `11`.

**Mobile / low-end**
- [ ] No Nanite path assumed; traditional LOD ladder tuned for the device tier.
- [ ] Layer count per component held to the mobile renderer's affordable few (~3 is the folk
      ceiling — **?** verify current mobile landscape limits per feature level).
- [ ] Material permutations counted for the mobile feature level separately; VT support on target
      devices confirmed before relying on RVT.

## Appendix: other engines in brief

**Unity built-in Terrain.** Patch-based heightfield with pixel-error-driven LOD, GPU-instanced
patch rendering ("Draw Instanced"), Terrain Layers as the splat system (classically four layers
per splat pass — additional layers add passes/cost), plus dedicated detail (grass) and tree systems
with billboard imposters. Known profile: fine for moderate worlds; layer-heavy materials and dense
details are the usual cost cliffs, and large worlds need third-party or hand-rolled streaming.

**Godot.** No built-in terrain node (as of Godot 4.x). The de-facto answer is the community
**Terrain3D** GDExtension (clipmap-based geometry — `01`'s clipmap family — with its own layered
texturing), or the older HTerrain plugin. Evaluate plugin maturity per project; there is no
engine-vendor contract here.

**O3DE.** Terrain Gem: terrain as world components fed by the gradient/surface-data system
(procedural-first authoring), with macro material + detail material split and a clipmap-style
detail renderer (**?** internals — verify against current O3DE docs).

**CryEngine (legacy reference).** The classic unified-terrain-texture heightfield: a baked global
color mega-texture over the heightfield with near-field detail layers, plus terrain holes and voxel
objects for caves. Historically influential (the "megatexture-adjacent" terrain look); consult only
as lineage.

| Engine | Geometry scheme | Texturing | LOD family (`01`/`02`) | Escape hatch needed when |
|---|---|---|---|---|
| Unreal Landscape | Component grid / Nanite clusters | Weightmap layers + RVT | Quadtree+geomorph, or `02` | Runtime deformation on Nanite; caves |
| Unity Terrain | Instanced patches | Terrain Layers (splat passes) | Patch pixel-error | Large streamed worlds; layer-heavy mats |
| Godot + Terrain3D | Clipmap (plugin) | Plugin layer system | Clipmaps | Vendor-grade support requirements |
| O3DE Terrain Gem | Component + clipmap detail | Macro + detail materials | Clipmaps (**?**) | Ecosystem maturity |
| CryEngine (legacy) | Heightfield + voxel objects | Unified texture + detail | Engine-specific | New projects (it's lineage, not a target) |

**When "just use a mesh" wins.** Every built-in above is a *uniform-grid heightfield* with a fixed
material model. Prefer a custom mesh pipeline (`02` clusters, or `01` CDLOD/clipmaps over your own
buffers) when the project needs: caves/overhangs as first-class terrain (`04`/`05`), planetary
domains (`09`), non-uniform sampling density, aggressive runtime deformation, or a material model
the engine's layer system can't express. The built-in buys tooling and editor integration; the
moment you fight its representation rather than its defaults, the custom path is cheaper than it
looks.

## Sources & provenance

This chapter is predominantly **D/N-tier**: official Epic/Unity/Godot/O3DE documentation and
engine-branded feature names, not published papers. Engine internals change per release — every
claim tagged **?** above must be verified against current engine docs before being relied on.

- **D** — Epic UE documentation: Landscape technical guide (components/sections/quads, recommended
  resolutions, 16-bit height encoding, weightmap packing, Layer Info, edit layers, holes, splines,
  collision mip); Landscape material nodes; Runtime Virtual Texturing; World Partition, HLOD, data
  layers; Large World Coordinates.
- **N** — engine-branded features whose names, not internals, are the claim: Nanite Landscape,
  Nanite tessellation/displacement, Virtual Heightfield Mesh, Landscape Streaming Proxy, Terrain3D
  (Godot community), O3DE Terrain Gem, Unity Draw Instanced terrain.
- **D** — Unity Manual: Terrain, Terrain Layers, detail/tree systems. Godot docs (absence of
  built-in terrain). O3DE Terrain Gem docs.
- **T/F** — per-component draw-call intuition, the "≤ 4 layers per component" and mobile "~3
  layers" ceilings, permutation-explosion folklore: long-standing practitioner doctrine (GDC/Unreal
  Fest talks and Epic staff guidance), stable in spirit, numeric specifics **?** per version.
- **?** — explicitly version-sensitive in the text: exact recommended-size tables, LOD cvar names,
  Nanite Landscape runtime-deformation and ray-tracing status, Nanite displacement maturity, VHM
  status, mobile landscape layer limits, O3DE clipmap internals. Verify against current engine
  docs at time of use.
- Cross-references: geometry theory `01`/`02`; materials & VT `07`; GPU submission `08`; planetary
  precision `09`; lighting `10`; verification `11`; streaming `06`; generation-side contracts
  terrain-architect `08` and `27`; BRDF math: the physically-based-rendering skill.
