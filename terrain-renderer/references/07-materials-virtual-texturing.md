---
# --- okf v0.2, written by tools/okf_apply.py -----------------------
type: Reference
title: Terrain materials, splatting, and virtual texturing
description: Terrain materials, splatting and virtual texturing, including the cache-invalidation traps that runtime state walks into.
tags: [terrain, materials, splatting, virtual-texturing]
status: stable
generated: { by: process:claude-code, at: 2026-08-23T18:38:25Z }
# --- end okf v0.2 ----------------------------------------------------
---
# Terrain materials, splatting, and virtual texturing

This chapter owns how terrain gets its surface: splat/weight blending, blend quality, the
anti-tiling arsenal, projection, and virtual texturing in both its streaming and runtime forms.
The generation side of every mask lives in terrain-architect `27` (causes in, engine derives
effects); BRDF and material math route to the physically-based-rendering skill and are never
duplicated here. Geometry LOD is `01`, engine-native systems `03`, streaming `06`, lighting `10`.

Contents: [Material-resolve evolution](#the-material-resolve-evolution-each-era-removed-one-bottleneck) ·
[The splat pipeline](#the-splat-pipeline) · [Blend quality](#blend-quality) ·
[Tiling breakup arsenal](#tiling-breakup-arsenal) · [Projection](#projection) ·
[Virtual texturing](#virtual-texturing) · [Terrain-mesh integration](#terrain-mesh-integration) ·
[Material AA at distance](#material-anti-aliasing-at-distance) · [Pitfalls](#pitfalls) ·
[Sources](#sources--provenance)

## The material-resolve evolution: each era removed one bottleneck

Terrain texturing history is a sequence of bottleneck transfers. Do not prescribe a technique
without naming the cost it was invented to remove:

| Stage | What it did | Bottleneck it solved | What forced the next stage |
|---|---|---|---|
| **Detail texturing** | One macro/base color multiplied or blended with a high-frequency tiled detail texture | Early texture memory could not hold close-range surface detail over a whole terrain | Every square meter still repeated the same material identity; grass, rock, and mud could not vary spatially |
| **Alpha/weight splatting** | Several tiling material layers blended by painted or generated weights | Gave each region material identity while reusing small tiling textures | Cost became `active layers × maps × projection samples` every visible pixel, every frame; texture-unit and sampler budgets capped variety |
| **id Tech MegaTexture / SVT** | Authored unique surface texels stored in a huge virtual address space and streamed as pages | Removed visible tiling and decoupled world uniqueness from VRAM capacity | Unique texel storage and IO became the budget; authored pages could not cheaply express continuously changing material state |
| **Runtime Virtual Texturing (RVT)** | GPU resolves expensive splats/decals into cached pages on demand | Amortized mostly static material composition instead of recomputing it per pixel per frame | Cache invalidation became the hard limit: dynamic weather or seasons inside pages turn global state changes into redraw storms |
| **Visibility buffer / deferred material evaluation** | Raster stores the winning primitive/cluster ID; a later screen-space pass fetches attributes and evaluates only visible pixels, optionally bucketed by material | Decoupled material evaluation from triangle submission and microtriangle overshading; made cost follow visible shaded pixels | It does not eliminate the need for VT/RVT or material discipline; it changes *when and where* the resolve runs |

The 2026 AAA path is usually a composition, not a winner-takes-all replacement: visibility
resolves which surface pixels exist (`02`, `08`); SVT supplies unique authored data; RVT caches
stable terrain/road/decal composition; this chapter's sample-time layers apply transient state.
The architecture is wrong if a visibility buffer merely defers the same unbounded N-layer blend
or if RVT is asked to cache global time.

## The splat pipeline

### Where weights come from

The weightmap is an **effect**, and effects are derived, not authored. The generation tool exports
cause fields — slope, flow, wetness, soil depth, curvature, snow potential (terrain-architect
`27`'s registry) — and the material system derives layer weights from them, either baked at cook
time or in-shader. Hand-painted weightmaps are a legitimate *override* channel on top of derived
weights, never the primary source: painted weights describe the terrain as it looked the day the
artist painted, and silently rot when the heightfield regenerates. Whatever produces them, at the
shader boundary weights are a per-texel partition of unity across N material layers.

### Cost reality: samples = layers × maps

An N-layer blend samples every map of every layer it blends: 8 layers × (albedo + normal +
roughness/AO/height pack) = 24 texture samples per pixel *before* any anti-tiling or triplanar
multiplier — and those multipliers are multiplicative on top (8 layers, triplanar, hex-tiled is
24 × 3 × 3 = 216 samples: absurd). Everything in this section is machinery for refusing to pay
that: pack, cap the active set, renormalize, or replace the per-pixel blend with an ID map + a
virtual-texture cache.

The **4-layer packing convention**: one RGBA weightmap carries 4 weights; since weights sum to 1,
the 4th channel is recoverable as `1 - (r+g+b)` if you'd rather spend the channel elsewhere.
Engines that support more layers stack additional weightmaps in groups of 4 (UE Landscape
allocates weightmap channels this way — `03`). Per-chunk, record which layers are actually
present and compile/select a shader permutation or branch that touches only those: most chunks
use 2-4 layers even in 16-layer worlds, and the worst-case chunk should be a content bug you
hunt (`11` has the layer-count heatmap check), not a budget you size for.

**Top-K selection**: independent of storage, the per-pixel blend should keep only the K largest
weights (K = 2 or 3), zero the rest, and renormalize. Beyond K=3 the extra layers are visually
invisible and financially real.

### Texture arrays as the substrate

Put every layer's maps in `Texture2DArray`s (one array per map type: albedo array, normal array,
packed-ARM array), indexed by layer ID in-shader. This is what makes top-K, ID maps, and dynamic
layer sets possible — a loop over K indices instead of N hardcoded samplers. The constraint is
the contract: **every slice shares resolution, format, and mip count.** Author to it. A single
4k "hero" layer in a 1k array forces the whole array to 4k or the hero down to 1k; decide at
material-palette design time, not integration week.

### Weight renormalization

Weights stop summing to 1 the moment anything touches them: 8-bit quantization, bilinear
filtering between texels of different partitions, top-K zeroing, painted overrides. Blending with
un-normalized weights scales the result's energy — the terrain visibly darkens (sum < 1) or blows
out (sum > 1) in bands along layer boundaries. Rule: **renormalize in the shader, after top-K,
every time**: `w_i /= max(sum(w), eps)`. The `eps` guard matters — all-zero weight texels exist
(new layers, freshly streamed tiles) and dividing by zero paints NaN speckle that TAA smears into
streaks.

### Mip halos from filtered weightmaps

Weightmaps get mip chains and bilinear filtering like any texture, and at coarse mips a texel
averages weights across a layer boundary — that part is correct and is what makes distant blends
smooth. The halo bug appears when weights and weighted *content* are filtered independently: any
baked composite (a per-tile baked albedo, an RVT page and its mips, a downsampled preview) that
was built as `sum(w_i * color_i)` per texel and then mipped will ring at boundaries where a layer's
weight fades to zero but its color still contributes to the average — the classic dark/bright
fringe, same mathematics as non-premultiplied alpha halos. The fix is the same as alpha's:
**build mips in premultiplied space** — filter `(w·color, w)` pairs and divide by filtered `w`
after — or generate each mip from re-blending at that resolution rather than box-filtering the
composite. ID maps are the extreme case: IDs are labels, not quantities, and must never be
bilinearly filtered or mipped at all (below).

### ID maps + virtual texturing: the modern alternative

The N-layer per-pixel blend does redundant work: it re-resolves the same blend every frame for
every pixel. Two-stage alternative:

1. **ID map**: a point-sampled map storing per-texel material IDs — commonly two IDs plus a blend
   ratio (`R8G8` IDs + `R8` blend, or packed). The shader fetches IDs, indexes the texture
   arrays, blends 2 layers. Cost is constant no matter how many materials exist in the palette —
   this is how 100-material terrains ship. The tax: hardware filtering is meaningless on IDs, so
   smooth transitions require manually fetching the 4 neighboring ID texels and blending their
   resolved colors (4× cost locally), or dithering the transition and letting TAA resolve it.
2. **Runtime virtual texturing**: cache the fully composited result in a VT page pool so the
   expensive resolve (however many layers, hex-tiling, triplanar) runs only on page fault, not
   per pixel per frame. See [Virtual texturing](#virtual-texturing).

Use per-pixel splatting for ≤ ~4-6 active layers with dynamic weights; move to ID maps when the
palette is large and authored; add RVT when the per-pixel resolve cost dominates and inputs are
mostly static.

## Blend quality

### Height-based blending: the biggest upgrade per line of code

Linear weight blending crossfades layers like ghosts — mud fades through rock as a translucent
film. Height-based blending uses each layer's height map to decide *which texels win* inside the
transition band: grass grows up between cobblestones, sand fills rock crevices. It is standard
practice everywhere (F — no canonical paper) and is the single largest visual return on ~5 lines:

```hlsl
// wA + wB = 1; hA, hB from each layer's height map in [0,1]; contrast ~0.05-0.3
float fa = hA + wA, fb = hB + wB;
float m  = max(fa, fb) - contrast;              // only texels within 'contrast' of the top survive
float ba = max(fa - m, 0), bb = max(fb - m, 0);
result   = (texA * ba + texB * bb) / (ba + bb); // renormalized sharp blend
```

Requirements: per-layer height maps (pack into the layer's ARM-style texture — do not add a
sample), and `contrast` exposed per layer pair. Failure mode: contrast too low degenerates to a
hard aliasing edge that shimmers at distance — widen contrast with distance or fade to linear
blending by mip level. Apply the same height-competition to *weights themselves* before sampling
when using top-K: it sharpens which K win.

### Normal blending done right

Lerping normal vectors and renormalizing is wrong twice: it flattens detail (the average of two
unit vectors is shorter, renormalization redistributes but biases toward the mean) and it loses
the base/detail semantic (detail should *perturb* base, not average with it). The accepted
options, in descending order of correctness and cost — Reoriented Normal Mapping (RNM),
whiteout, UDN, and partial-derivative (slope-space) blending — come from the "Blending in
Detail" analysis (Barré-Brisebois & Hill 2012); *why* each works is theirs to explain, but the
formulas are load-bearing terrain code and belong here.

**RNM** rotates the detail normal so its +Z follows the base surface — a shortest-arc rotation
folded into a few ALU ops. For raw `[0,1]` tangent-space texture samples `base`, `detail`:

```hlsl
float3 t = base.xyz   * float3( 2,  2, 2) + float3(-1, -1,  0);   // unpack, z biased +1
float3 u = detail.xyz * float3(-2, -2, 2) + float3( 1,  1, -1);   // unpack, xy negated
float3 n = normalize(t * dot(t, u) / t.z - u);                    // reorient detail onto base
```

(For already-unpacked unit vectors: `t = n1 + float3(0,0,1); u = n2 * float3(-1,-1,1);` then the
same last line.) The cheaper approximations, when RNM's ~7 extra ALU matter or for mip-faded
detail:

```hlsl
float3 whiteout = normalize(float3(n1.xy + n2.xy, n1.z * n2.z));  // decent grazing behavior
float3 udn      = normalize(float3(n1.xy + n2.xy, n1.z));         // cheapest, flattens detail
// slope-space (partial-derivative), the right frame for WEIGHTED N-way blends:
float2 s = (w1 * (-n1.xy / n1.z) + w2 * (-n2.xy / n2.z)) / (w1 + w2);
float3 pd = normalize(float3(-s, 1));
```

Terrain-specific doctrine: **layer-vs-layer** blends (two splat layers, arbitrary weights) live
in slope space — slopes combine linearly, normals don't; **base-vs-detail** blends (macro
terrain normal + tiling detail normal) use RNM (whiteout when budget-bound); and the *geometric*
terrain normal joins the stack per the `10` normal pipeline, not as another lerp participant.
Deeper theory (specular response of blended normals, filtering interactions) routes to
physically-based-rendering.

### Procedural masks in-shader vs baked

Slope/altitude masking in the shader (from per-pixel normal and world height) is tempting:
infinite resolution, zero storage, reacts to runtime deformation. Its limits: renderer slope is
not simulation slope (different sample spacing, different LOD — the mask *changes with LOD*,
`01`), and the shader cannot see causes — no flow, no wetness, no soil depth, so in-shader rock
masks put cliffs where the simulation put scree. Doctrine: **causes are baked** (generation-side
masks per terrain-architect `27`), **cosmetic breakup is in-shader** (high-frequency jitter on
the baked mask's threshold, slope-sharpening near the camera). If a shader mask disagrees with a
generation mask about where a material belongs, the generation mask is right.

## Tiling breakup arsenal

Ordered by cost. Deploy from the top; stop when screenshots at gameplay distance stop showing
grids. All of this is standard practice (F) except where cited.

| Technique | Extra cost | Kills tiling at | Enough when |
|---|---|---|---|
| Macro variation map | 1 sample, whole terrain | mid-far (tint/brightness) | always deploy; mandatory baseline |
| Distance-scaled UV cascades | ~2× samples in blend bands | all distances (frequency) | tiling only visible as scale repeat |
| Detail normal layer | 1-2 samples near camera | near (adds unique high freq) | near-field monotony, not repeats |
| Stochastic / hex-tiling | 3× samples + LUT per layer | all distances (pattern) | repeats survive the above; hero layers |
| Texture bombing | branchy samples per splat | discrete features | needs identifiable features (leaves, stones) |

- **Macro variation map**: one low-frequency color/brightness texture (or cheap noise) over the
  whole terrain, multiplied or overlay-blended into every layer's albedo, optionally perturbing
  roughness. One sample; breaks the "wallpaper" read at distance where all tiling techniques
  matter most. There is no excuse for shipping without it.
- **Distance-scaled UV cascades**: sample the layer at 2-3 UV scales (e.g. 1×, 1/8×, 1/64×) and
  blend by distance band so the visible frequency stays comfortable at every range; near-band
  shows texel detail, far-band shows a re-scaled version whose repeat distance is km, not m.
  Blend bands cost double samples; keep them narrow. Beware doubled normal strength in bands —
  blend normals properly (above), don't add.
- **Stochastic / hex-tiling by-example** (Heitz & Neyret 2018, P; Mikkelsen's hex variant, D/?):
  tile UV space with a triangle/hex lattice; each cell samples the texture at a randomized offset
  (decorrelation — kills the repeat), and the 3 overlapping cell samples are blended by
  partition-of-unity weights. Naively, linearly blending 3 decorrelated samples averages the
  texture with itself, collapsing variance — contrast dies, the result is oatmeal. The
  histogram-preserving trick: precompute an invertible transform taking the texture through its
  histogram to a Gaussian distribution; blend *in the Gaussian domain* with variance-preserving
  weights (`w_i / sqrt(sum w²)` semantics), where the blend of Gaussians is the same Gaussian;
  map back through the inverse-histogram LUT. Statistics — contrast, color distribution — survive
  exactly. Costs 3× samples plus a small LUT per texture; works best on stochastic textures
  (gravel, grass, rock grain) and visibly breaks long-range structure (brick courses, wood
  planks). Handle normal/roughness channels with care — transform channels independently and
  expect slight energy drift (F); route roughness consequences to the physically-based-rendering
  skill.
- **Texture bombing** (Glanville, GPU Gems 2004, P): procedurally splat randomized decal
  features (rotation, scale, selection from an atlas) over a base. Right tool for discrete
  identifiable repeats — distinctive stones, flowers — wrong tool for continuous texture.

## Projection

### Heightfield UV luxury

A heightfield gets planar mapping for free: `uv = worldPos.xz / tileScale` — world-space, so
texture never swims when chunks re-LOD, seam-free by construction, aniso-friendly. Its one
failure is slope stretching: texels elongate by `1/cos(slope)`, and past ~45-60° the smearing is
unmissable. Options in cost order: accept it with stretch-tolerant textures on steep layers; or
blend to triplanar only where a slope mask says so.

### Triplanar mapping

Project the texture along all three axes and blend by the normal:

```hlsl
float3 w = pow(abs(n), sharp);  w /= (w.x + w.y + w.z);      // sharp ~ 4-8
col = w.x * tex(uv_yz) + w.y * tex(uv_xz) + w.z * tex(uv_xy); // 3 samples PER MAP
```

Cost is the headline: 3× every map of every layer it applies to — which is why heightfields
restrict it to steep-slope layers and voxel engines eat it globally. **Weight sharpening**: raw
`abs(n)` weights blend over huge regions, ghosting three projections together into blur; `pow`
with exponent 4-8 (then renormalize) narrows the blend to edges. Too sharp → visible seam lines
where projections switch; too soft → doubled/ghosted texture on every non-axis-aligned face.

**Normal handling is the part everyone ships wrong.** A tangent-space normal map sampled in a
planar projection is expressed in *that projection's* tangent frame; using it raw lights two of
the three projections with sideways normals. Correct options (F/D — Golus's triplanar-normal
analysis is the standard writeup): reconstruct a per-plane tangent basis (correct, more ALU) or
per-plane swizzle with whiteout/UDN-style blending of the plane-space perturbations onto the
geometric normal (cheap, standard). Never blend the three raw tangent-space samples first and
transform once.

**Biplanar** (F/D — Quilez): pick only the two most-aligned projections per pixel and blend
those, dropping a third of the samples; artifacts concentrate near the corner direction where
the dropped plane mattered. Worth it when triplanar is global (voxel worlds) and sample-bound.

### When terrain forces triplanar

Blocky and smooth-isosurface voxel terrain (`04`, `05`) has overhangs, caves, and no natural 2D
parameterization: triplanar (or biplanar) in world space is the default, not the fallback, and
the layer count discipline above matters triply. Heightfield renderers should treat triplanar as
a scoped tool — a slope-masked layer blend — and keep the planar path for the 90% of pixels that
are walkable ground.

## Virtual texturing

### Plumbing common to both kinds

Virtual texturing decouples address space from residency. The **virtual texture** is a huge
logical mip pyramid divided into pages (commonly 128² payload texels + border). Resident pages
live in a **physical page pool** (texture atlas or texture-array pages, BCn-compressed). An
**indirection / page table texture** — one texel per virtual page per mip — maps virtual page →
physical page origin + scale; the shader translates `uv → page table lookup → physical uv` and
samples with hardware filtering inside the page.

- **Feedback / request pass**: something must discover which pages pixels *want*. Classic: render
  a small feedback buffer (e.g. 1/8-1/16 res) writing `(pageID, mip)` per pixel, read back, dedupe,
  prioritize (coarse mips first), stream/produce, update page table (van Waveren, Mittring — T).
  Modern variants append requests to a GPU buffer from the material shader directly. Latency is
  1-3 frames minimum; design for it (fallbacks, prefetch), don't deny it.
- **Page borders**: bilinear and anisotropic filtering read neighbors; at page edges the neighbor
  is unrelated pool memory. Each physical page stores a border (typically 2-4 texels) duplicated
  from adjacent virtual pages. **Border width caps usable anisotropy** — an aniso footprint wider
  than the border reads across the page seam, so VT samplers clamp max aniso (4-8× typical) and
  the shader must compute gradients from *virtual* UVs, not post-indirection UVs, or mip/aniso
  selection goes wrong at page boundaries.
- **Transcoding**: disk pages are stored in a dense format (JPEG-family or crunched/supercompressed
  BCn) and transcoded to GPU BCn at load — budget CPU/GPU time per frame for it; a page pipeline
  that can decode only N pages/frame defines your worst-case sharpen latency.
- **Fallback mips**: the top few mips of the whole virtual texture stay permanently resident, so
  any miss renders *blurry, never black or checkerboard*. The page-table lookup falls back to the
  finest resident ancestor page automatically (store per-texel "finest available" in the table).
- **Cache sizing math**: a screen shows at most ~`screenPixels × overdraw × anisoSlack` unique
  texels; at 4K that is order 10-30M texels ≈ 600-2000 pages of 128² — so a physical pool of a few
  thousand pages (a 4096² atlas holds 1024 pages; use 2-4 atlases or an array) covers steady state,
  and the pool exists to absorb *churn* (camera motion, turns), not steady state. Size by measuring
  eviction age (`11`): if pages are evicted younger than ~2-3 seconds of camera motion, grow the
  pool or bias mips down.

### Streaming VT vs runtime VT — different problems, same plumbing

| | Streaming VT (SVT) | Runtime VT (RVT) |
|---|---|---|
| Page producer | disk (authored/baked texel content) | GPU compositor (splat resolve, decals) |
| Ancestry | MegaTexture / id Tech 5 (T) | caching the splat pipeline above |
| Invalidation | never (content immutable) | whenever composited inputs change |
| Cost center | IO + transcode | page render (full material graph) |
| What it buys | unique authored texels, huge worlds | resolve-once for expensive blends |

SVT answers "my authored texture data exceeds VRAM": id's MegaTexture lineage, unique texels
everywhere. Do the **unique-texel budget math** before promising it: 100 km² at 1 texel/cm is
10¹² texels — ~1 TB even at 1 byte/texel compressed. Nobody ships that; real worlds mix a VT for
the near-unique layer with tiling detail layered on top, or drop density to texels-per-decimeter
for the far field. If the math says the disk can't hold it, no cache architecture will fix it.

RVT answers "my per-pixel material resolve is too expensive to run every frame": composite the
splat/ID blend, hex-tiling, decals into pages on demand and sample the cache. UE's Runtime
Virtual Texture is the branded example (`03`, N/D) — landscape materials render into RVT pages,
meshes and grass sample them back. RVT's defining constraint is **invalidation**: anything
dynamic baked into pages (time-varying wetness, moving decals) either forces page re-render or
goes stale. Keep dynamic terms out of the cache (below).

### The cache boundary: stable spatial composition only

RVT is a cache, not the terrain's state database:

| Legal inside RVT pages | Forbidden inside RVT pages |
|---|---|
| Static splat/ID resolve, macro color, stable geometry-derived masks | Season amount or season blend |
| Static roads, persistent replayable decals, terrain/mesh contact blend | Global wetness, rain response, puddle level |
| Authored substrate variation and static biome material selection | Snow accumulation, melt, footprints, tire compression |
| Any input whose dirty region is bounded and replayable | Any input driven by global time, weather, camera, or per-frame interaction |

The required two-layer composition is explicit:

```hlsl
Surface base      = SampleRVT(worldXZ);                    // stable, cached
Surface seasonal  = ApplySeasonOverlay(base, seasonState); // global/sample-time
Surface weathered = ApplyWetSnowDeform(seasonal, StateRT); // 13 camera/paged overlays
```

**Non-negotiable:** a slow season transition is still dynamic global state. Do not "solve" it by
staggering a world-wide RVT invalidation; that only spreads the cache-coherency defect over more
frames. Page invalidation is for bounded persistent edits and static content changes. Seasons,
wetness, and transient snow always remain post-RVT overlays (`13`, `14`).

**Clipmap texturing is the ancestor** (Tanner et al. 1998, P): a nested-resolution toroidally
updated texture stack centered on the viewer — residency as a pure function of view distance.
VT generalizes the residency set from concentric rings to arbitrary sparse pages; the clipmap
survives inside `01` (geometry clipmaps) and `10` (VSM clipmap levels). **Adaptive VT** (Far
Cry 4's scheme, T) extends VT to huge worlds by giving each world sector its own virtual
allocation whose resolution adapts to view distance, sidestepping a single impossibly-large page
table.

### Failure modes

- **Feedback latency pop**: camera cuts/teleports show 1-N frames of fallback blur, then a wave of
  sharpening. Mitigate: prefetch along predicted camera motion, prime requests for cut targets
  before the cut, render the feedback pass for the destination during fades. Accept that a hard
  cut into a new vista *will* resolve visibly; budget the transcode pipeline for the burst.
- **Page thrash**: working set exceeds the pool → evict/reload oscillation, permanent blur plus IO
  saturation. Detect with eviction-age histograms; fix by pool growth, mip bias, or reducing the
  aniso/feedback resolution overshoot that inflated the working set.
- **Border bleed**: wrong border fill (or gradients computed post-indirection) shows the page grid
  as hairline seams, worst under aniso at grazing angles — the terrain-viewing angle. Verify with
  a page-border debug palette (`11`).
- **Stale RVT pages**: a "cheap" global change (season tint, snow amount) that lives inside page
  composites invalidates *every* page — a full-cache re-render spike. Structure the material so
  global dynamics apply at sample time, outside the cache; `13` owns the season/weather state
  targets and `14` owns their compositing order.

## Neural texture compression, and what it does to this chapter's arithmetic

⚠️ **Frontier, not doctrine.** Tier `D`/`T`: the API is standardised and the SDKs are public; it is
**not yet in shipped games** as of 2026-08, and engine integration is announced rather than
delivered. Treat everything here as a budget you can *plan* against and not a technique to
prescribe. Re-verify before quoting — this is the fastest-moving row in the skill.

**What it is.** Instead of a fixed block-compression codec, a small neural network — a couple of
layers, a handful of neurons wide — reconstructs texel values on demand from compact learned latent
features. The decode runs *inside the shader* at sample time, which is what makes it a streaming and
residency technique rather than an offline one.

**Why it lands on terrain first.** Terrain is the most texture-hungry system in the frame: a virtual
texture over a large world, plus splat layers, plus the aux-map registry of `14`. The budget in
[Virtual texturing](#virtual-texturing) above is dominated by resident tile bytes, and NTC multiplies
exactly that term.

| | |
|---|---|
| the mechanism it replaces | fixed BCn block compression, ~4:1 (BC7) |
| reported ratios | **16:1 to 32:1** at quality comparable to BC7 at 4:1 |
| one vendor demo, end to end | **6.5 GB of BCn → 970 MB**, image quality close to the original |
| what carries it | DirectX **cooperative vectors** (Shader Model 6.9) and the equivalent Vulkan path, on hardware matrix units |

**The consequence for the budget is a multiplier on one term, and it is worth being precise about
which.** Resident bytes fall; the *page table*, the feedback pass, the indirection and the tile count
do not move at all. So a virtual-texturing system that was page-table-bound or feedback-bound gains
nothing, and one that was VRAM-bound gains most of the ratio. `reference-impl/budget.py`'s
`tile_bytes` is where that multiplier goes, and the residency rows are already written so that
changing the codec changes one input rather than the model.

⚠️ **Three things it does not fix**, and each is a place this chapter has already warned about:
decode cost is per *sample* rather than per *tile*, so a shader that samples the same page many
times pays repeatedly where a decompressed tile would have paid once; filtering across a neural
decode is not free and the naive answer (decode, then filter) is not the same as filtering the
underlying signal; and **nothing about it changes the mip-halo defect** of independently filtered
weights and content, which is a compositing error and survives any codec.

**What to do about it in 2026.** Keep the codec behind the same interface the rest of the chapter
assumes — a tile is bytes with a format — so the budget is a parameter rather than an assumption.
That is the whole preparation, and it costs nothing if the technology slips.

## Terrain-mesh integration

- **Meshes sampling the terrain composite**: rocks, cliffs, and debris meshes intersecting the
  terrain betray themselves with a hard material line at the contact. The standard fix in RVT
  worlds: the mesh material samples the terrain's composited RVT at its world XZ near the contact
  and blends its own material toward it by height above the sampled terrain (UE RVT's marquee use
  case — N/D; generic technique F). Blend geometry too: dithered opacity or pixel-depth-offset
  over the last N cm hides the polygon intersection line. Without RVT, sample the same weightmaps
  + layer arrays the terrain uses — costlier but identical logic.
- **Decals**: deferred decals work on terrain like anything else, with two terrain traps: decals
  projected onto *morphing* LOD geometry slide as vertices morph (`01`), and in RVT worlds static
  decals should composite *into* the pages (free after fault) while dynamic ones stay in the
  deferred pass.
- **Wetness / snow / runtime overlay layers**: the generation side exports the *cause* fields —
  snow accumulation potential per the terrain-architect `27` Snow Rule, wetness from hydrology,
  porosity from soil — and the renderer applies the *current* amounts (weather state, season) as
  a final material layer: albedo darkening + roughness drop for wetness, a snow layer blended by
  potential × current-snow-level with height-based blending against the underlying material.
  Because these are dynamic, they live outside RVT caches (above) and outside baked composites.
  The division of labor is exactly `27`'s handoff contract: simulation-derived spatial masks are
  immutable inputs; the scalar "how much right now" is runtime state.

## Material anti-aliasing at distance

Distant terrain is the specular-aliasing worst case: kilometers of high-frequency normal detail
at grazing sun angles, minified to sub-texel footprints (`10` owns the lighting-side symptoms).

- **Specular AA / normal-variance-to-roughness**: as normal map mips average detail away, the
  *variance* that detail represented must reappear as widened roughness, or distant slopes render
  glittery and too bright — the vMF/Toksvig/LEAN family. The math lives in the
  physically-based-rendering skill; the terrain doctrine is only: **bake variance-compensated
  roughness mips for every terrain layer**, and verify the distant-slope sparkle check in `11`.
- **Mip-flattening of detail normals**: independently, fade detail-normal *strength* toward flat
  with distance/mip — it saves ALU and removes shimmer — but only in tandem with the roughness
  compensation above, or distant terrain turns waxy-smooth instead.
- **Texture LOD bias under TAA/upscalers** (D — DLSS/FSR integration guides): temporal upscalers
  reconstruct output-resolution detail, so texture mip selection at *render* resolution is too
  blurry; apply a negative sampler bias ≈ `log2(renderRes / outputRes)` (plus a small tuned
  offset) to color/detail textures. Discipline: the bias applies to *detail content* only — never
  to weightmaps, ID maps, page tables, or any data-semantic texture, where sharper mips mean
  *different data* and reintroduce halos and thrash; and biased detail must still pass the
  sparkle check, since the bias deliberately re-admits high frequencies that TAA is now
  responsible for integrating.

## Pitfalls

- Weights not renormalized after top-K/quantization/filtering → banded darkening along blend
  edges; all-zero weight texels → NaN speckle without the `eps` guard.
- Weightmaps, ID maps, or height-blend maps flagged sRGB → subtly wrong blends everywhere; these
  are data, always linear.
- Baked composites / RVT mips box-filtered in straight (non-premultiplied) space → halos at every
  layer boundary at distance.
- ID maps bilinearly filtered → garbage interpolated IDs sampling wrong array slices; point-sample
  and blend manually, or dither.
- Normal lerp-and-renormalize between layers → flattened, biased lighting; use the accepted blend
  operators (physically-based-rendering skill).
- Triplanar without per-plane normal reorientation → two of three projections lit sideways;
  reads as inexplicable shading seams on slopes.
- Hex-tiling applied to structured textures (brick, planks) → broken long-range features; it
  preserves statistics, not structure.
- In-shader slope masks fighting generation-side masks → materials that migrate when LOD changes
  and disagree with scatter/gameplay masks; causes are baked (`27`).
- VT gradients computed after indirection → wrong mip/aniso at page borders; page-grid seams.
- Aniso set above what page borders support → border bleed at grazing angles exactly where
  terrain is always viewed.
- Global dynamic effects (snow amount, season) composited into RVT pages → full-cache
  invalidation spikes or stale terrain.
- Negative TAA/upscaler mip bias applied globally, including data maps → weight halos, ID noise,
  page-table corruption-lookalikes.
- Texture-array palette with mismatched slice resolutions discovered at integration → forced
  re-author; fix the palette contract on day one.
- Layer-count worst case unmeasured → one chunk with 12 active layers sets the frame budget;
  heatmap it (`11`).

## Sources & provenance

| Claim | Tier |
|---|---|
| Histogram-preserving blending / by-example stochastic texturing — Heitz & Neyret 2018 (HPG), "High-Performance By-Example Noise using a Histogram-Preserving Blending Operator"; companion Deliot & Heitz report on tiling-and-blending | **P** |
| Practical real-time hex-tiling — Mikkelsen (JCGT-family venue, as remembered) | **D/?** (technique solid; venue cited from memory) |
| Clipmap texturing — Tanner, Migdal, Jones 1998, "The Clipmap: A Virtual Mipmap" (SIGGRAPH) | **P** |
| MegaTexture / id Tech 5 virtual texturing — van Waveren talks & "Software Virtual Textures"; Mittring, "Advanced Virtual Texture Topics" (SIGGRAPH Advances course 2008); Barrett, "Sparse Virtual Textures" (GDC 2008) | **T** |
| Adaptive virtual texturing for large open worlds — Far Cry 4 GDC presentation (Ka Chen, as remembered) | **T/?** (speaker/title from memory) |
| Texture bombing — Glanville, GPU Gems (2004) | **P** |
| UE Runtime Virtual Texture: landscape composite cached in pages, meshes sample it back | **N/D** (`03`) |
| UE Landscape weightmap channel packing in groups of 4 | **N/D** |
| DLSS/FSR negative texture LOD bias ≈ log2(renderRes/outputRes) | **D** (vendor integration guides) |
| Height-based blending with contrast — "the biggest upgrade per line of code" | **F** (universal practice, no canonical paper) |
| RNM / whiteout / UDN / partial-derivative normal blending — Barré-Brisebois & Hill, "Blending in Detail", 2012 (formulas inlined above; URL verified 2026-07: https://blog.selfshadow.com/publications/blending-in-detail/) | **D/F** |
| Triplanar weight sharpening pow 4-8; per-plane normal handling (Golus writeup); biplanar variant (Quilez) | **F/D** |
| 4-layer RGBA weight packing; sum-to-1 with inferred 4th channel; top-K blend, K=2-3 | **F** |
| Premultiplied-weight mip generation to kill composite halos | **F** (alpha-premultiplication math applied to weights) |
| ID map (2 IDs + ratio) + texture arrays for large palettes; manual 4-tap or dithered ID filtering | **F** |
| VT page size 128² + 2-4 texel borders; border width caps aniso; virtual-UV gradients | **T/F** (id-lineage talks + practice) |
| Fallback resident top mips; feedback pass at reduced res; 1-3 frame latency | **T/F** |
| Cache sizing from unique-texel screen coverage; eviction-age thrash detection | **F** |
| Unique-texel budget arithmetic (100 km² @ 1 texel/cm ≈ 10¹² texels) | **F** (arithmetic) |
| Macro variation map / distance UV cascades / detail normals ordering | **F** |
| Specular AA via normal-variance-to-roughness (Toksvig/vMF/LEAN family) | **P** (family), math routed to physically-based-rendering |
| Slope stretching 1/cos(slope); triplanar-only-on-steep-layers hybrid | **F** |
