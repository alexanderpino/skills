# Output Contract

Contents: [The field contract](#the-field-contract) · [The layer stack](#the-layer-stack) ·
[Precision](#precision) · [Tiling & aprons](#tiling--aprons) · [Seams](#seams) · [LOD](#lod) ·
[Splatmaps](#splatmaps) · [Satmap & colour map](#satmap--colour-map) ·
[Normal & AO maps](#optimised-normal--ao-maps) · [Synthesising a material](#synthesising-a-material) ·
[Compositing with the splatmap](#compositing-with-the-splatmap) · [Emitters](#emitters)

## The field contract

The graph produces these fields. Engines consume them. Nothing engine-specific goes upstream
of this boundary.

| Field | Unit | Format | Notes |
|---|---|---|---|
| `height` | metres, absolute | R32F working / R16 export | Sea level = 0 |
| `waterSurface` | metres | R32F | Lakes + sea; `NaN` or a mask where dry |
| `sandDepth` / `sedimentDepth` | metres | R16 | Layer thickness above bedrock |
| `normal` | unit vector | RG8/BC5 (reconstruct Z) | Baked from R32F, always — see Normal & AO maps |
| `ao` | [0,1] | R8/BC4 | Baked from R32F |
| `albedo` (colour map) | linear RGB | RGB8 / BC7 | Composited from masks — see Satmap & colour map. **No directional light baked in.** |
| `masks[i]` | [0,1] | R8 per channel | Must partition — see `06` |
| `flowAccum` (`A`) | m² | R32F | Log-scaled for storage if needed |
| `scatter[i]` | positions + attrs | Point list | World-space |

Plus a manifest, and the manifest is not optional:

```
{
  "origin":        [x, y],        // world-space, metres
  "extent":        [w, h],        // metres
  "resolution":    [px, py],
  "cellSize":      float,         // metres — extent / (resolution - 1) or extent / resolution?  STATE IT
  "heightRange":   [min, max],    // metres, for R16 dequantisation
  "seaLevel":      float,
  "rootSeed":      uint64,
  "tileIndex":     [i, j],
  "apron":         int            // cells of overlap included, if any
}
```

**`cellSize = extent / resolution` or `extent / (resolution − 1)`?** This is the
off-by-one that produces a half-cell shift between your terrain and everything else in the
world. Decide once, write it down, and be aware that engines disagree: a heightmap is
conventionally *vertex-centred* (so `N` samples span `N−1` cells) but a texture is
*pixel-centred* (so `N` texels span `N` cells). Terrain heightmaps are vertex-centred; masks
and splatmaps are pixel-centred. **They are not the same grid**, and the half-texel offset
between them is a real and commonly-shipped bug.

## The layer stack

The fields above are not independent textures — they are an **ordered stack over the bedrock** (the
doctrine in `SKILL.md`), and *which surface you mean* depends on which layers you count. Three
surfaces come out of the one stack, and an engine needs all three kept apart:

| Surface | = | Used for |
|---|---|---|
| **Solid / collision** | bedrock + soil + sand (the solid covers) | Walking, physics, where things rest |
| **Water** | `waterSurface` (sea, lakes) | The water plane, buoyancy, swimming |
| **Rendered** | solid + water where wet + snow where cold | The final look |

```
solidTop   = bedrock + soilDepth + sandDepth         # collision — the walkable surface
waterDepth = max(0, waterSurface − solidTop)          # >0 where submerged; buoyancy / swim here
snowTop    = solidTop + snowDepth                      # 13; melts, so it is seasonal
```

**Emit each layer, not a flattened height.** The classic bug is baking water into the terrain
height so the "sea" is solid ground at sea level — now nothing can swim, boats rest on a wall, and
a tide can't move the shoreline. Ship `solidTop` as the collision/mesh height, `waterSurface` as a
**separate animated surface** carrying a depth field, and `snowDepth` as an overlay the engine can
melt. Each is already a field in the contract; the discipline is to keep them *separate* fields
through to the emitter.

**Baking a layer in is a real option — for solid covers — and it is *not* just albedo.** Keeping a
layer live is for what *changes* (tides, seasonal snow, flowing water); a *static* solid cover — a
perpetual snowcap, established soil, a fixed sand sheet — can be **baked into the terrain** to save
the engine the work. But baking snow is not painting the albedo white; it commits the layer's
**whole stack contribution**:

- **Geometry** — add the layer's thickness to `solidTop`. Baked snow *raises and reshapes* the
  ground: it fills hollows, rounds ridges, and settles at its own repose (`13`), so the surface is a
  different shape than the bare rock underneath. Snow drawn as flat white albedo on the rock's own
  geometry is the classic fake — it ignores that snow accumulates, drifts, and thickens.
- **Material** — the splat/material becomes snow / soil / sand where baked (`06`), which drives
  friction, footstep sound, and particles — not only colour.
- **Derived maps** — re-bake **normals and AO from the post-bake height** (precision, below); baked
  snow lit with the rock's normals reads wrong.

So the satmap (colour) is *one output* of a bake, not the bake itself — a bake touches height,
material, normals, AO, and physics, the whole contract. And the asymmetry holds: **solid covers
(snow, soil, sand) can bake; water should not** — bake the sea in and you get the wall you can't
swim in. Bake only what is genuinely static; keep live whatever melts, migrates, or flows.

**Solid vs fluid vs transient** — the three layer kinds and what each obeys:

- **Solid covers** (soil `11`, sand `05`) move slowly by erosion/deposition and are part of the
  collision surface. They follow the layered erosion model (Št'ava 2008, `04`; Beneš & Forsbach
  2001, `11`): erosion eats the cover before the bedrock, which is what gives rock-above-scree.
- **Fluid** (water) has a dynamic surface — tides (`12`), waves and flow (`03`, `04`), lake spill
  level (`03`) — and a depth you traverse. It is never part of the collision height.
- **Transient** (snow `13`) accumulates and melts on top of everything, sliding off steep ground by
  its own thermal pass.

When the stack needs **voids** — overhangs, sea caves, arches — rather than stacked thicknesses, the
field stack is the wrong representation: switch to the per-column material stack of `11` (Peytavie's
Arches 2009) or a volume. That is a representation decision, and it is made here, at the contract,
not discovered later in the engine.

## Precision

**Work in R32F. Quantise once, at export, after every derivative has been taken.**

R16 gives 65,536 levels. Across a vertical range:

| Range | R16 step |
|---|---|
| 1,000 m | 1.5 cm |
| 8,000 m | 12 cm |
| 20,000 m | 30 cm |

12 cm sounds harmless. It is not, for two reasons:

1. **On a gentle slope, the quantisation step becomes a terrace.** A 0.5° slope at 1 m/px
   rises 8.7 mm per cell — so with a 12 cm step, the terrain is *flat for 14 cells and then
   steps*. You get visible contour terracing across every plain, and it is the classic "why
   does my terrain look like a topographic model" artefact.
2. **Derivatives of a quantised field are combs.** Slope becomes a series of zeros and spikes.
   Curvature — a second derivative — is essentially a picture of the quantisation. Normals
   facet. AO rings.

So: bake normals, AO, slope, curvature, and all masks from R32F. Export R16 height *last*,
and only if the engine demands it. If the engine supports R32F heightmaps, use them; the
memory cost is real but the alternative is baking the artefact in permanently.

**Dequantisation must be exact and shared.** `h = heightRange.min + (u16 / 65535.0) * (max - min)`.
Note `65535`, not `65536`. If the engine uses `65536` and you used `65535`, you have a
sub-millimetre error that nobody will find but which will haunt a seam somewhere.

**Float precision at large world coordinates** — see `01`. At 100 km from the origin, fp32
has ~8 mm of mantissa resolution. Terrain vertices computed in absolute world space that far
out will jitter. Use camera-relative or tile-relative rendering coordinates.

## Tiling & aprons

**Erosion is not tile-local.** This is the hardest problem in the file.

A droplet crosses tile boundaries. Sediment deposits downstream of where it eroded, possibly
in the next tile. Flow accumulation is *global by definition* — a river's drainage area
includes everything upstream, which may be twenty tiles away. Running any of `03`, `04`, or
`05` per-tile in isolation produces:

- Discontinuous height at the seam (visible crack or ridge)
- Rivers that stop at the tile edge
- Different erosion character per tile (each tile's droplets had different neighbourhoods)

**The apron rule:**

```
apronWidth ≥ maxTransportDistance
```

| Model | Max transport distance |
|---|---|
| Droplet | `maxLifetime × 1 cell` — typically 30–64 cells |
| Pipe | `iterations × Δt × maxVelocity / cellSize` — measure it; often 100s of cells |
| Thermal | `iterations × 1 cell` — bounded and small |
| Stream power | **unbounded** — `A` is a global quantity |

So:

- **Thermal** tiles fine with a small apron. It's local.
- **Droplet** tiles with a 64-cell apron and a bit of care. Discard the apron after.
- **Pipe** tiles poorly. The apron needed is large enough that you're mostly recomputing.
- **Stream power does not tile at all.** Drainage area is global. You must run it on the whole
  domain at once, then cut tiles from the result.

**The honest recommendation:** run erosion at the **highest resolution you can hold globally**
(a 8k or 16k R32F field is 256 MB / 1 GB — this is affordable offline), then tile the *result*
and add tile-local detail (noise, thermal) afterwards. Do not try to make global erosion
streamable. Every tool that appears to do so is either (a) precomputing globally and streaming
the output, or (b) producing seams and hoping.

If you *must* erode per-tile:

```
1. Load tile + apron from neighbours (or generate the apron's base terrain — it's
   deterministic from world-space noise, so this is free)
2. Run erosion over tile+apron
3. Crop to the tile
4. Crossfade the outermost few cells against the neighbour's result
```

Step 4 is a lie that mostly works for droplet and thermal, and does not work for anything with
long-range transport.

## Seams

The four causes, in the order you should check them:

1. **Tile-local noise coordinates.** `noise(uv)` instead of `noise(worldPos)`. Produces an
   obvious hard discontinuity. See `01`.
2. **Tile-local erosion without an apron.** See above.
3. **Vertex vs pixel centring mismatch.** Half-texel offset — produces a fine crack, easy to
   mistake for a z-fighting issue.
4. **Independent normal baking per tile.** The normal at the tile edge needs the neighbour's
   height. Bake normals from the tile+1-cell apron, or your lighting has a visible grid.

**Edge vertex sharing.** Adjacent tiles must share the *exact same float* at the boundary,
not "the same value computed twice". Two different evaluation paths that should give the same
answer will differ in the last bit, and at a silhouette that's a visible pinhole. Compute the
edge once and copy, or make the evaluation bit-identical by construction.

## Planetary / spherical domains

Everything above assumes a **flat, rectangular heightfield** — the right default, and wrong the moment
the domain is a whole planet. You cannot wrap one rectangular grid around a sphere without a
singularity (the lat–long "pole pinch": cells shrink to zero area and the timestep dies at the poles).
Two grid families solve it, and the choice is the planetary version of the tiling decision above.

**Cube-sphere — six faces, six flat grids.** Project the sphere onto a cube and grid each face; a
point on face +X at face-local `(a,b)` maps to the sphere by normalising:

```
p = normalize(1, a, b)                          # gnomonic (equidistant) cube-sphere
```

The plain (equidistant) version bunches cells toward face centres — a **corner-to-centre area ratio of
~5.2**. The **equiangular** variant (Ronchi et al. 1996) grids each face in *angle* (`a = tan ξ`,
`ξ ∈ [−π/4, π/4]`), which nearly uniformises cell area (ratio ~2) at the cost of a `tan`/`atan` per
lookup. Origin of the quadrilateralized spherical cube: Chan & O'Neill 1975 (the COBE grid); the
finite-difference lineage is Sadourny 1972. The **six faces are six of the tiles above** and the
**twelve cube edges are the seams** — the Seams problem again, now with a *rotation* between faces.

**Geodesic / HEALPix — no faces, no seams.** Tile the sphere with hexagons and twelve pentagons
(icosahedral geodesic), or with the equal-area pixels of **HEALPix** (`N_pix = 12·N_side²`, every
pixel exactly equal-area; Górski et al. 2005). These have **no face seams** and near-uniform cells —
why climate and cosmology grids use them — at the cost of a non-rectangular neighbour structure (a
cell has 6 neighbours, sometimes 5).

**Distortion is the load-bearing correction.** A fixed-resolution grid sampled through any projection
carries a per-cell **scale factor `h`** (Snyder 1987): true ground distance is `Δground = Δpixel / h`.
Every metre-denominated operator — slope, flow routing, erosion transport distance — **must divide
gradients by `h`**, or it biases flow toward the high-distortion regions and the world-unit invariants
of `SKILL.md` break on the sphere exactly as they break under `normalize` (`10`).

**Flow routing across the seams.** D8/D∞ (`03`) run unchanged *inside* a face; the only hard part is
neighbour lookup at a face edge or corner, and it is **F-tier engineering** — there is no canonical
paper for cube-face-seam flow routing:

```
neighbors(face f, i, j):
    for (di,dj) in D8:
        if in-range: yield (f, i+di, j+dj)                  # interior — trivial
        else:        yield remap(SEAM_TABLE[f][edge], rot)  # crossed an edge → rotate onto neighbour face
    # cube corners are 3-valent: the 8 corners have only 7 neighbours — special-case them
flowDir(cell): steepest descent over neighbors(), with Δs = h · arcDistance   # metric-corrected
```

Depression handling (`03`) then runs on the resulting global graph unchanged. To avoid seams
entirely, route on a **hex/HEALPix DGGS** instead — there is real published flow-routing work on those
grids (Liao et al. 2020, 2025), whereas the cube-seam handling stays folklore.

**Verify.** Height and `A` are continuous across a cube-face seam and resolution-consistent; there is
no pole pinch; and gradients are divided by the scale factor `h` so erosion doesn't bias toward
high-distortion cells (`09`, *Checks for the extended families*).

**Tier.** The cube-sphere and equiangular mappings are P (Chan & O'Neill 1975; Sadourny 1972; Ronchi
et al. 1996); HEALPix is P (Górski et al. 2005); map-distortion scale factors are P (Snyder 1987);
DGGS flow routing is P (Liao et al. 2020, 2025). Cube-face-**seam** flow routing is **F** — halo cells
plus per-face rotation tables, solved ad hoc with no canonical paper; say so rather than inventing one.

This section is the **grid substrate**; the processes that run *on* a whole globe — Euler-pole
tectonics, the latitude climate bands, geoid sea level, sphere noise, planet-scale LOD and the
alien-world regimes — are consolidated in `references/25-planetary-spherical.md`, which routes back
here for everything above.

## DEM & sensor realism

A synthetic heightfield is *too clean* to be a real DEM. Real elevation data is **measured**, and
measurement leaves fingerprints — sensor geometry, processing steps, and a spatially-structured error
field. Two reasons to care: **matching real survey data** (author a heightfield that reads as SRTM or
lidar), and **consuming it** (a graph fed a real DEM must undo the artefacts before routing). The one
review reference is Fisher & Tate 2006; the rest are per-artefact.

**Correcting a real DEM (before it enters the graph).**
- **Hydrological enforcement / pit removal** — real DEMs are full of spurious pits (noise, bridges,
  vegetation) that wreck flow routing (`03`). Remove them by **priority-flood** fill with an epsilon
  gradient (`03`), or during interpolation (Hutchinson 1989, ANUDEM), which enforces monotone drainage
  to mapped outlets. **Stream burning** lowers cells under a known channel network by 5–20 m so
  accumulation converges onto it — do it *before* the fill so the channels win.
- **Void filling** — SRTM and photogrammetric DEMs have holes (radar shadow, cloud). The **delta-surface**
  method (Reuter et al. 2007) fills a void from an auxiliary DEM snapped to the SRTM datum: interpolate
  the boundary bias `Δ = z_srtm − z_aux` across the void, add it back to `z_aux` — auxiliary *texture*,
  SRTM *level*, no patch seam. Pick the interpolator by void size × terrain (spline in dissected relief,
  kriging/IDW on flats).
- **Bare-earth filtering (lidar)** — raw lidar is first-return (canopy, buildings); the bare-earth DEM is
  the ground beneath. Progressive-densification TIN (Axelsson 2000) or a **growing-window morphological
  opening** (Zhang et al. 2003): a cell is non-ground if it stands above the opened surface by more than
  a slope-scaled threshold `dhₜ = dh₀ + s·Δw·c`, the window growing to catch bushes → cars → buildings
  without shaving real relief.

**Synthesising realism (make a clean heightfield read as measured).**
- **Correlated error, not white noise.** Real DEM error is a **spatially-autocorrelated random field**
  (Fisher & Tate 2006): `z_obs = z_true + e`, `e ~ GRF(bias, σ, ρ(h))` with e.g. `ρ(h)=exp(−h/a)`, range
  `a` of tens–hundreds of metres. Synthesise by filtering white noise with a Gaussian of `σ = a/cellSize`,
  then rescale to the target RMSE. Per-cell independent noise looks *gritty* and fake; the autocorrelation
  range is what sells it.
- **Quantisation & posting.** Round to the vertical step (`z_q = round(z/q)·q`, `q≈1 m` for SRTM →
  contour-like stair-stepping on gentle slopes, the same terracing as the R16 precision trap above), and
  resample to the real ground sample distance (30 m / 90 m) to lock in blocky ridgelines.
- **Sensor geometry (SAR).** Side-looking radar warps slopes by look angle `θ`: **foreshortening** where
  the foreslope faces the sensor, **layover** (order reversed, elevation ambiguous) where slope toward the
  sensor `≥ θ`, and **shadow** (a data void) where the backslope tilts past `90°−θ`; add multiplicative
  Gamma **speckle**. These are the tells that a heightfield came off a radar mission (Hanssen 2001).
- **Striping.** SRTM/ASTER carry near-periodic banding (~hundreds of m wavelength, ~1–2 m amplitude) and
  isolated mosaic-seam pits — a sinusoid along the track plus a few spikes.

**Tier.** Hydro-enforcement (Hutchinson 1989), void-fill (Reuter et al. 2007), lidar filtering (Axelsson
2000; Zhang et al. 2003) and the error-field model (Fisher & Tate 2006) are P; SAR layover/shadow geometry
and quantisation/striping are F (textbook geometry / product-validation practice, no canonical paper). All
are `08` data-contract operations, not terrain *processes* — they change what the field *is measured as*,
never what the land *did*.

## LOD

**Do not decimate a heightfield with a box filter.** Averaging heights removes peaks and fills
valleys, so at every LOD level the terrain shrinks toward the mean. The mountains get shorter
as you fly away. This is very noticeable and extremely common.

Better options:

- **Max/min alternating or max-filtered mips** for silhouette preservation. Peaks survive.
  Slightly inflates the terrain, which is the safer error (geometry never sinks below the
  high-res version, so no popping *up*).
- **Proper decimation** (Garland & Heckbert 1997, quadric error metrics) if you're producing
  meshes rather than mips. Preserves features by construction.
- **Geometry clipmaps** (Losasso & Hoppe 2004) if the terrain is a streamed heightfield.
  Nested regular grids centred on the viewer, each level twice the extent and half the
  resolution. The key details: the coarser level must be *filtered from the same source* the
  finer one uses (else the transition pops), and the transition band between levels must
  morph vertices smoothly (`alpha` blend between the fine vertex height and the interpolated
  coarse height across a band of ~2 cells).

**The T-junction problem.** Where two LOD levels meet, the fine side has vertices the coarse
side doesn't, so the edge splits and you get pinhole cracks. Fixes: stitch with a skirt
(cheap, slightly wrong, universally used), or degenerate triangles along the boundary, or
morph the fine vertices to the coarse edge line (correct, and what clipmaps do).

**Normal maps do not LOD like heights.** A normal map mipped with a box filter loses variance,
so distant terrain becomes flat and shiny. Use a variance-preserving mip chain (Toksvig, or
LEAN/LEADR mapping) that pushes lost normal variance into the roughness channel. Otherwise
your distant mountains look like wet plastic.

## Splatmaps

Packing masks into channels. The constraint is that a 4-channel splatmap holds 4 materials,
and terrain wants more.

- **Weightmaps** — one R8 per material, `N` textures. Flexible, expensive.
- **Splatmaps** — RGBA, 4 materials per texture, `ceil(N/4)` textures. Standard.
- **Index+blend** — two channels: a material index (R8, 256 materials) and a blend weight.
  One texture, unlimited materials, but only 2 materials can blend at any point. For terrain
  this is usually *fine* and it's the cheapest good answer. Sample with point filtering on the
  index and blend manually, or you'll interpolate between index 3 and index 7 and get material
  5, which is a spectacular bug.

**Normalisation.** Splat weights must sum to 1. Either enforce it in the graph (`06`) or
normalise in the shader. Doing neither means your material blend brightness varies with the
mask sum, which reads as inexplicable blotchy lighting.

**Resolution.** Splatmaps are usually 1/2 or 1/4 the heightmap resolution. They're
pixel-centred while the heightmap is vertex-centred (see above) — mind the offset.

## Satmap & colour map

Two different things travel under these names, and conflating them is exactly the N-tier slip this
skill warns about (`00`):

- **SatMap — the gradient (an *input*).** Gaea's *SatMap* is a **colour gradient: a 1D LUT indexed
  by a scalar field**, altitude by default (you can drive it with any mask). The library "satmaps"
  are gradients sampled from real satellite / DEM imagery — which is where the name comes from. It
  is an **authoring operator**, not an output: it *turns a field into colour*. The **2D** case is a
  LUT indexed by *two* fields — the Whittaker biome diagram (`13`) is precisely a
  `(temperature, precip) → colour` 2D satmap.
- **Colour map / albedo — the result.** The top-down **basecolour** texture (World Machine's
  *colour map*) that an engine actually samples. It is *composited* from the fields, and a gradient
  is one of the operators you build it with.

The gradient is a `curve` / LUT (`10`), so it inherits that node's one real trap: **height is
Gaussian-ish, not uniform** (`01`), so a gradient applied to raw altitude bunches most of its
colours into the mid-band and starves the peaks and troughs. Histogram-match the field, or remap
against a measured range, *before* the LUT (`10`).

Composite the albedo from the same masks as the splatmap (`06`): `height → analysis → masks → albedo`.

```
albedo = Σ_i  mask[i] * materialAlbedo[i]              # composite by the SAME masks as the splatmap
       * (0.85 + 0.15 * macroNoise)                     # low-freq colour variation, or it reads flat
       * lerp(1, cavity, cavityStrength)                # curvature darkens crevices (06, 11)
albedo = lerp(albedo, satmap1D(height), tintAmt)        # a 1D altitude gradient (a "satmap") as a tint
```

**The cardinal rule: no directional light in the albedo.** A colour map with a hillshade or
sun-cast shadows baked in is wrong the instant the engine relights it — you get shadows crossed
with shadows and it cannot be undone. Albedo is view- and light-independent. The *only*
shading-like terms allowed are the direction-independent ones — **ambient occlusion and
cavity** (`06`) — and even those belong in their own channel where the engine can choose to
apply them, not multiplied irreversibly into the colour. If you must bake AO in for a flat
preview, keep an AO-free master.

**It must agree with the splatmap.** The colour map and the splatmap are two encodings of the same
material decision — composite both from the identical `06` masks, or the low-res colour map and the
runtime material blend will disagree and the terrain will visibly change colour as the camera
approaches and the engine crossfades from baked to blended.

**Resolution & streaming.** Colour maps are large and are the usual reason a terrain needs virtual
texturing / a megatexture (`00`: Barrett 2008, Mittring 2008 — GDC/SIGGRAPH talks, F-tier).
Author per tile and stream; do not ship one 32k texture. Cheaper: store only the low-freq macro
colour and blend a tiled high-freq detail albedo in the shader, which keeps the stored colour map
small and the near-field crisp.

## Optimised normal & AO maps

The baking *maths* is in `06` (Sobel normals, horizon AO). This is the *export* side — encoding,
compression, and whether to bake at all.

**Often you should not bake a base normal map.** Terrain doesn't deform, so the surface normal
is a pure function of the height you already ship — derive it in the shader from the heightmap
and spend the texture budget on a **tangent-space detail** normal instead. Bake a stored normal
map when the height is decimated for LOD (so the fine normal outlives the coarse geometry — the
whole point of normal-mapped LOD, see [LOD](#lod)) or when the consumer can't sample height in
the shading path.

**Normal encoding — two channels, reconstruct Z** (the survey of schemes is Cigolle et al. 2014,
*A Survey of Efficient Representations for Independent Unit Vectors*, JCGT 3(2) — `00`):

```
store (n.x, n.y);   n.z = sqrt(max(0, 1 - n.x² - n.y²))   # z is always +ve for a heightfield normal
```

- Compress with **BC5** (two-channel RG, built for exactly this). **Never BC1/DXT1** — 5:6:5
  colour compression bands normals visibly and there's no third channel to spare anyway.
- If you need a full sphere of directions (object-space, or detail normals that tilt past
  horizontal), **octahedral** encoding (Cigolle et al. 2014) packs a unit vector into two
  channels with near-uniform error — the standard modern choice above bare reconstruct-Z.
- A terrain *base* normal baked from the heightfield is effectively **world/object-space** (the
  surface has no independent tangent frame); detail and decal normals are **tangent-space**.
  Don't mix the two conventions in one map.

**AO — one channel.** BC4 (single-channel), or pack it into a spare channel of another map: the
**ORM** convention (**O**cclusion / **R**oughness / **M**etallic in RGB) is standard and lets one
BC7 texture carry three. Keep AO **out of the albedo** (see Satmap). For directional occlusion,
bake a **bent normal** alongside — the average unoccluded direction — and the shader gets both an
AO term and a shifted diffuse direction from one extra map.

**The two rules that carry over from `06`/`08`:**

- **Bake from R32F.** A normal or AO map baked off quantised R16 facets and rings — the failure
  catalogue's "faceted normals / ringed AO". Non-negotiable.
- **Mip with variance preservation.** A box-mipped normal map loses variance and distant terrain
  goes flat and shiny ("wet plastic", see [LOD](#lod)). Use **Toksvig** or **LEAN/LEADR** (`00`)
  to push the lost normal variance into the roughness channel — which is exactly why the ORM pack
  is convenient: roughness rides alongside the normal that feeds it.

**Resolution.** A baked normal/AO map only needs to match the frequency of detail it is
*carrying*. If the shader derives base normals from height and the baked map is only detail, it
can be lower-resolution and tiled. If it's the sole normal source for a decimated LOD, it must
match the pre-decimation height frequency or the detail is thrown away twice.

## Synthesising a material

The compositing recipe below blends per-material tiling sets — but where does the "rock" set (its
albedo, normal, roughness, AO, height) *come from*? Two routes, and the key realisation is that the
first one is **this skill at a finer scale**.

**A material is a tiny tiling heightfield.** A rock texture is a few-centimetre relief field, and its
PBR channels come out of that relief by exactly the derivations terrain uses (`06`) — the
scale-recursion doctrine (`SKILL.md`) made literal:

```
pattern = FBM (01)                                   # the rough base
        + Worley/Voronoi cells (01)                  # jointing, blocks, cracks — the "rock" tell
        + high-freq grain (01)
        warped by domain warp (01)                   # break the lattice
        relaxed by a little thermal/erosion (05/04)  # rounded and weathered, not raw noise
# then derive the PBR set from the pattern-as-height, the SAME way terrain derives its maps:
height    = pattern                                  # for the splat height-blend (compositing, below)
normal    = sobel(height) (06)                       # tangent-space detail normal
ao/cavity = horizonAO(height) (06)                   # micro-occlusion in the pits
albedo    = baseColour * (1 - k*cavity) * weather(curvature, 06) * colourNoise
roughness = lerp(smooth, rough, exposure)            # rougher where exposed, smoother in cavities / wet
metallic  = 0                                        # terrain rock is a dielectric
emissive  = crackMask * blackbody(T)                 # 0 for cold materials — see below
```

**Emissive — the incandescent-crack channel.** Molten and cooling materials (a lava lake's crust,
fresh flow margins, a Mustafar-style lava world, `11`) need one more PBR channel: **emission**. The
recipe reuses machinery already here:

```
crackMask = worley_F2minusF1(p) thresholded          # 01 — the crack pattern IS the cell-boundary noise
T         = T_melt * exp(-age/τ) * nearCrack(p)      # hot in the cracks, cooling with crust age
emissive  = crackMask * blackbodyRamp(T)             # 1D gradient: dull red → orange → yellow-white
```

- **The crack pattern is Worley `F2−F1`** (`01`) — the same cell-boundary noise the skill already
  uses for jointing and mud cracks; on a lava crust the plates are the cooled cells and the glow
  lives in the boundaries. Advect/stretch the cells along the flow direction (`01` warp) and the
  plates read as rafted crust, not static tiles.
- **The colour ramp is physics, not taste**: incandescence follows a blackbody sequence — dull red
  (~700 °C) → orange (~1000 °C) → yellow-white (~1200 °C). It is exactly a 1D satmap (above): a
  gradient indexed by temperature. Drive `T` down with crust age and distance from the crack and
  the crust self-organises into dark plates with bright seams.
- **Emission is separate from albedo** — the no-light-in-albedo rule holds. The crust's *albedo*
  stays near-black basalt; the glow goes in the emissive channel where the engine can bloom and
  light with it. Baking the glow into the colour map gives a crust that neither glows nor darkens
  correctly.
- Emission belongs in the **material property bundle** (`18`): molten materials carry `T` the same
  way rock carries `K` — one field, many consumers (height stops flowing below yield `11`, material
  emits above ~600 °C).

The **cellular / Voronoi** term (Worley 1996, `01`) is what makes rock read as rock — jointed blocks
and cracks, not smooth lumps; **Gabor** noise (Lagae 2009, `01`) gives the anisotropic bedding of
sandstone or schist. And the weathering is the same **curvature / slope / AO selectors** (`06`) you
use on terrain, now at cm scale: dust and darkening in the cavities (concave), wear and lighter
colour on the exposed edges (convex). That is the whole trick — **a material is terrain's own
operators (`01`, `04`/`05`, `06`) run at a finer scale and derived into PBR channels**, which is the
scale-recursion doctrine (`SKILL.md`) applied to appearance.

**Tileable, or it seams.** Synthesise on a torus (periodic noise, or offset-and-blend the edges) so
the material repeats without a visible seam — the same world-space discipline as `01`, at tile scale.

**By-example, when you have a scan or photo.** The other route is to *synthesise from an exemplar*
instead of authoring a noise graph — grow a large, non-repeating texture from a small sample. The
lineage: **Efros & Leung 1999** (non-parametric, pixel-by-pixel), **Wei & Levoy 2000** (fast,
tree-structured VQ), **Lefebvre & Hoppe 2006** (appearance-space, parallel); and to *tile* a scanned
material without ghosting, **Heitz & Neyret 2018** (compositing, below). To go straight from a single
flash photo to a full PBR set (albedo / normal / roughness / specular), the learned route is
**Deschaintre et al. 2018** — verify before leaning on it; this area moves fast (the learned-methods
caveat in `00`).

**Tier.** Pure-procedural material authoring is **N-tier tool practice** — Substance Designer, Gaea's
material nodes, Quixel Mixer are noise graphs producing PBR channels, built on the `01` primitives;
no single paper. By-example synthesis is **P-tier** (Efros & Leung 1999; Wei & Levoy 2000; Lefebvre &
Hoppe 2006; Heitz & Neyret 2018); the learned photo→material route is verify-first (Deschaintre et
al. 2018).

## Compositing with the splatmap

The maps above come at **two frequencies**, and the splat material system's whole job is to combine
them. Get it wrong and the terrain either tiles visibly or turns to mush at every material boundary.

- **Per-material tiling set** — each material (rock, grass, sand, snow) is a *repeating* texture set:
  albedo, tangent-space normal, AO/cavity, roughness, and often a **height** channel. Authored
  assets, sampled at high frequency in world UV.
- **Terrain-wide macro maps** — the colour map, the base normal (from the heightfield, `06`), and the
  horizon AO (`06`): one low-frequency layer over the whole terrain.

The splatmap **blends the tiling set**; the macro maps **modulate** it. Channel by channel:

**Albedo.** Blend per-material tiling albedos by splat weight, modulate by the macro colour map, and
fade to the macro map at distance to hide the tiling:
```
albedo = Σ_i  splat[i] * tile(materialAlbedo[i], worldUV * tileScale[i])
albedo = lerp(albedo, macroColourMap, distanceFade)      # detail near, colour map far
```

**Normal.** Two combinations, and the order matters. First blend the per-material *detail* normals
across the splat (height-weighted, below — a plain lerp-and-normalise flattens strong detail). Then
combine the blended detail (tangent space) with the terrain **base** normal, and the correct operator
is **Reoriented Normal Mapping** (Barré-Brisebois & Hill 2012, *Blending in Detail*): reorient the
detail so it follows the base surface. Cheaper approximations, rising in quality:
partial-derivative → **UDN** → **whiteout** → RNM (nearest ground truth). **Never** average two normal
*vectors* linearly and call it done — that is the flat, plastic tell.

**AO.** Multiply **macro** occlusion (large-scale horizon AO from the heightfield, `06`) by **micro**
occlusion (per-material cavity/AO from the tiling set):
```
ao = macroAO(horizon, 06) * Σ_i splat[i] * tile(materialAO[i], tiledUV)
```
Macro darkens valleys and cliff bases; micro darkens the pits in the rock. Different scales, both
needed — using only one is the usual "flat" (no macro) or "dirty" (no micro) tell. For directional
occlusion bake a **bent normal** alongside (see Normal & AO maps above).

**Height-blending the splat (the transition).** A linear splat blend gives a soft 50/50 crossfade —
mud. Give each material a **height** channel and let the more prominent one win the boundary
(**Mishkinis 2013**, *Advanced Terrain Texture Splatting*): sand runs into the cracks between stones
and the stone tops stay bare, instead of a grey halfway mix.
```
h_i       = tile(materialHeight[i], tiledUV) + splat[i]
w_i       = max(0, h_i − (max_j h_j − transition))       # only near-top materials contribute
weight[i] = w_i / Σ w                                     # renormalise → sharp, natural seams
```

**Steep slopes → triplanar.** UV-mapped tiling stretches into smears on a cliff. Project the material
along the three world axes and blend the samples by the surface normal (**triplanar mapping** — Geiss
2007, *GPU Gems 3* ch. 1), applied to albedo *and* normal (mind the per-axis normal swizzle). Gate it
by a slope selector (`06`), or blend it in by slope.

**Hiding the repeat.** A tiling material repeats visibly at grazing angles. Break it with **stochastic
/ by-example tiling** — the histogram-preserving blend of **Heitz & Neyret 2018** samples the tile at
randomised offsets and blends *without* the ghosting naive random tiling causes. Cheaper folklore: two
octaves of the same tile at different scales, multiplied.

**What the graph owes the shader.** Partitioned splat weights (`06` — must sum to 1), the per-material
assignment, and the macro maps baked from **R32F** (precision above). The shader does the blend, but
the colour map, splatmap, and material blend are three views of *one* material decision — composite
them from the **same `06` masks** or they drift apart as the camera closes in.

**Tier.** Stochastic tiling (Heitz & Neyret 2018) is P-tier; RNM (Barré-Brisebois & Hill 2012),
triplanar (Geiss 2007), and height-blend (Mishkinis 2013) are documented practice (F, real named
sources); macro×micro AO and distance fade are F-tier shader folklore. None of it is a terrain
*algorithm* — it is the **consumption contract** for the maps the graph emits.

## Emitters

Each emitter converts the field contract into a target format. Emitters are thin and
disposable. They must not make decisions the graph should have made.

| Target | Height | Materials | Notes |
|---|---|---|---|
| Nebula | R32F or R16 tiles | Splat/index | Direct — you own the format |
| Unreal | R16 PNG, `(v - 32768) * zScale/128` | Landscape layers | Landscape resolution must be `n*componentSize + 1`; the `+1` is the vertex-centring |
| Unity | R16 RAW, `[0,1]` normalised to `terrainData.size.y` | `TerrainLayer` alphamaps | Unity heightmaps are `2^n + 1`; alphamaps are `2^n` |
| glTF / mesh | Baked mesh | Vertex colour or UV | For DCC round-trip |
| GeoTIFF | R32F + CRS | — | For GIS round-trip; carries `cellSize` properly |

Note that both Unreal and Unity want `2^n + 1` heightmaps and `2^n` masks — which is the
vertex/pixel distinction showing up in the shipped API. That's confirmation the distinction is
real, not pedantry.

**The emitter must not resample.** If the emitter is resampling to fit the engine's expected
resolution, the graph produced the wrong resolution and should be fixed. Resampling in the
emitter reintroduces every artefact the graph was careful to avoid.
