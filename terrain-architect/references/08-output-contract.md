# Output Contract

Contents: [The field contract](#the-field-contract) · [The layer stack](#the-layer-stack) ·
[Precision](#precision) · [Tiling & aprons](#tiling--aprons) · [Seams](#seams) · [LOD](#lod) ·
[Splatmaps](#splatmaps) · [Satmap & colour map](#satmap--colour-map) ·
[Normal & AO maps](#optimised-normal--ao-maps) · [Emitters](#emitters)

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
