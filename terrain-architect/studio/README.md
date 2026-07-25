# Terrain Studio — node-based WebGL terrain generator

A self-contained, single-file terrain generator that runs in the browser: a **node graph** drives a
live **WebGL 3D viewport**. It's the interactive companion to this skill's pure-NumPy `reference-impl/`
atoms — the same algorithms (fractal noise, domain warp, thermal & hydraulic erosion, histogram
equalisation, slope/height masks, real-DEM import) exposed as a graph you build and tune by eye.

**Open `index.html`** in any modern browser — no build step, no server, no dependencies. Everything
(UI, terrain kernels, WebGL renderer) is inline in that one file.

![Terrain Studio](../reference-impl/gallery.png)

## What it does

- **Node graph** (the core): drag nodes, wire outputs into inputs, and every node shows a live
  hill-shaded **thumbnail** of its own output — so you read the pipeline at a glance.
- **AAA deferred-PBR surface + SatMap colour** (the Gaea-class look): the terrain renders through a
  **true deferred pipeline**. The terrain pass writes only **albedo** (SatMap colour + rock on steeps
  + snow) and a per-material **smoothness** into a G-buffer; a single fullscreen composite then does
  *all* the lighting from the height field:
  - **per-pixel surface normals** reconstructed from central differences of the height texture
    (finer than the mesh vertex normals),
  - **sun** (Lambert) **+ hemispheric sky-irradiance ambient** — a warm ground-bounce → cool sky-dome
    gradient, so shadowed faces read *blue* instead of flat grey (the single biggest realism lever),
  - **GGX microfacet specular** driven by material smoothness (soil rough, rock glossier, snow sheen)
    with a Schlick Fresnel,
  - **soft ray-marched cast shadows** toward a **movable sun** (azimuth + elevation sliders) and
    **horizon ambient occlusion** (crevice darkening), folded into the same pass,
  - a richer **analytic sky** (horizon→zenith gradient, sun disk, aureole, near-sun horizon scatter)
    and distance-tinted **aerial perspective**, resolved through **ACES** tone mapping and
    **supersampled** for anti-aliased silhouettes.
- **SatMaps genuinely derived from real satellite imagery** (not hand-picked): pick from ~26 palettes
  in the viewport. The core set (Temperate, Alpine, Verdant, Canyon, Arid, Dune, Volcanic, Mars, Lunar,
  Arctic, Tundra) plus **Estuary/Dusk** and a **13-strip set** (Steel, Moss, Pewter, Copper, Chrome,
  Ash, Terracotta, Savanna, Frost, Fjord, Amber, Brass, Harvest) **traced from Gaea SatMap screenshots**
  — each gradient strip read as a per-column median of the bar (Dusk being the selected in-range window).
  Of the core set, **seven are extracted from real public-domain top-down satellite/aerial imagery** — the
  source image is ordered by luminance into an elevation ramp by the skill's own `reference-impl`
  `extract_satmap`, the same method Gaea describes for its SatMap library, done reproducibly rather
  than by eye. Derived: **Alpine** (Ligurian Alps), **Dune** (Rub′ al Khali / Terra), **Verdant**
  (Amazon / Landsat), **Volcanic** (Icelandic lava / ESA), **Arctic** (Greenland), **Tundra**
  (Iceland / ESA), **Lunar** (LROC). The pipeline (`satmaps/extract_satmaps.py`) fetches from
  Wikimedia Commons (satellite-image categories guarantee orbital framing — no sky to pollute the
  ramp), masks out space + open ocean, and rejects false-colour / off-biome frames with a hue guard;
  provenance and licences are recorded in `satmaps/derived.json` (NASA/USGS = public domain, ESA =
  CC BY). Temperate/Canyon/Arid/Mars stay authored (labelled as such) where no on-biome true-colour
  source was found.
  - **Make your own in-app — SatMap Studio** (the **＋LUT** button). A **SatMap LUT is a 1-D colour
    gradient** — low elevation on the left → high on the right, baked to a 256-px strip and indexed by
    each point's normalised height. SatMap Studio is a **gradient editor** in a full-width bottom sheet
    (the 3D viewport stays visible above and **recolours live** as you edit):
    - **Drag stops** along the bar to set their elevation, **click the bar** to add one, **click a stop
      then pick its colour**, and remove with **－ Stop**. The **current terrain's elevation histogram**
      is drawn behind the bar, so a stop's position maps to how much of the surface it paints.
    - **Start from…** a built-in SatMap and tweak; toggle **Smooth ↔ Bands** interpolation; **Reverse**
      the ramp; and apply global **hue / brightness / contrast / saturation**.
    - **From image…** opens a photo panel: **Auto-extract** orders the whole image by luminance into a
      ramp (the same method as the derived built-ins), or click the image to **eyedrop** the selected
      stop's colour.
    - **Apply** bakes the LUT into the SatMap list and selects it. (Ordering is by brightness, the usual
      elevation proxy; the colour picker and eyedropper let you override any stop.)
- **Live 3D viewport** with **multi-stage rendering**: WebGL2 lit terrain mesh (SatMap / slope /
  grey shading, orbit + zoom, wireframe), rendered in two passes —
  1. **Opaque terrain + snow** — a snow-accumulation stage that settles snow on high, gentle ground
     and leaves steep faces bare, with a specular snow sheen (driven by a **Snow** effect node).
  2. **Translucent water** — a separate alpha-blended pass with depth-based colour (shallow teal →
     deep blue), a Fresnel edge, animated ripples, and shoreline foam. It uses a **hydrologically
     correct water surface**, not a flat cut through the heightmap:
     - **Lakes** (**FLOW** on) fill each closed basin to its own **spill level** via a
       **priority-flood depression fill** (Barnes 2014) — flat lakes whose edges follow the basin
       rim, at the right elevation for each basin.
     - **Rivers** (**River flow** param) are the **flow-accumulation** drainage network (D8 on the
       filled DEM): a thin water film that **follows the terrain downhill**, widening with catchment.
     - **Sea level** mode instead lays a flat ocean at a chosen level — the simple, level-based water.
     The water-surface normal is computed from that surface (flat in lakes, sloped along rivers). This
     is the same `priority_flood_fill` + `d8_accumulation` pair the reference-impl uses.

  **Screen-space (deferred) compositing — the fullscreen-triangle technique.** On WebGL2 the water and
  sky are drawn *without geometry*, the same way a skydome is rendered from one fullscreen triangle:
  the terrain renders into an offscreen **colour + depth** G-buffer, then a single fullscreen triangle
  reconstructs each pixel's world position from the depth texture and composites analytically —
  **sky** on the background, and **water** by sampling the water-height texture. Because it has the
  depth buffer and the terrain colour, the water gets **refraction** (the lakebed sampled with a
  normal-based offset), **Beer–Lambert depth absorption** from the real view-ray thickness, a
  **Fresnel** sky reflection, sun glint and soft foam — quality a forward transparent plane can't
  reach. (WebGL1 falls back to the forward geometry-water pass; wireframe uses it too. The one
  tradeoff is that terrain silhouettes lose the forward MSAA, softened by the device-pixel-ratio
  supersample on hi-dpi displays.)
- **Real heightmaps as a base**: the **Import DEM** node has a one-click **Use real SRTM sample**
  (a real public-domain USGS/SRTM crop of the Colorado Plateau, embedded in the page) *and* loads your
  own PNG or square 16-bit `.r16` raw — including real USGS/SRTM tiles exported from
  `reference-impl/heightfield_io.py`. So you can add erosion and effects to real-world areas, then
  **Export** the result as a heightmap PNG. (An in-browser live fetch of the USGS/SRTM buckets isn't
  possible — they send no CORS headers — which is why `heightfield_io.py` does the fetching and the
  Studio imports the file, plus the embedded sample for zero-setup real terrain.)

### Node library (mirrors the reference-impl atoms)

| Group | Nodes |
|---|---|
| **Generator** | Perlin fBm · Ridged MF · Voronoi (F1/F2−F1) · Gradient (linear/radial) · Constant · **Layout** (authored vector skeleton with per-vertex elevation) · **Mountain** (placeable Peak / Massif, 5 styles) · **Shape** (SDF placement mask) · **Import DEM** (file *or* one-click real SRTM sample) |
| **Combine** | Blend (factor or mask) · Combine (add/sub/mul) · Max/Min · **Smooth Max** (crease-free union) · Smooth Min (intersection) · **Stamp** (place a patch onto a base through a mask) |
| **Filter** | Warp (domain warp) · **Transform** (translate/rotate/scale about a pivot, maskable, exact over procedural chains) · Terrace · Levels · Curve (bias/gain) · **Histogram EQ** · Blur · Clamp · Invert |
| **Erosion** | Thermal (talus) · Hydraulic (droplet sim, brush-distributed scour) |
| **Mask** | Slope select · Height select |
| **Data map** | **Slope** · **Curvature** (profile/plan/mean) · **Flow** (accumulation) · **Occlusion** (horizon AO) · **Deposits** (soil) · **Wear** · **Peaks** · **Texture** (slope+soil+flow composite) |
| **Effect** | **Water** (Hydrology = lakes + rivers, or Sea = a flat level) · **Snow** · **SatMap** (colour LUT node) · **SatMap Blend** (merge two colour branches) |
| **Output** | Output (drives the viewport / export) |

**Water, snow and colour are nodes, not global switches.** Add a **Water**, **Snow** or **SatMap** node and
wire it into the pipeline (e.g. `… → erosion → Snow → Water → SatMap → Output`); the viewport picks up
whichever effect nodes feed the Output. The **Water** node's **Mode** is either **Hydrology** (basin lakes +
downhill rivers) or the simple **Sea level** (a flat ocean at a level). Effect nodes pass the height through
unchanged — they add a scene layer, so deleting one removes just that effect.

**Art direction — Shape masks and the universal Mask input.** A procedural graph that only generates
*everywhere* can't be directed, so two things make it placeable, mirroring Gaea (where "almost every
node contains a Mask input port… the processing of that node is applied only within the masked area"):

- A **Shape** generator — an SDF placement mask (circle / box / line) with position, size, aspect,
  rotation and a soft **falloff**, authored as a fraction of the terrain so it stays put when the
  resolution changes. Like Gaea's Mask-as-Primitive it is *both* a mask and a heightfield: wire it into
  a Mask input to confine an effect, or erode it directly into a landform.
- A **Mask** input on **Thermal**, **Hydraulic**, **Warp**, **Terrace** and **Blur** — the effect runs,
  then applies only where the mask is bright (`base + (modified − base) · mask`). Because it is a
  post-process, changing the mask never re-runs the erosion. Verified: with a circular Shape mask, mean
  change inside the mask is 5.2e-4 and **outside is exactly 0**.

Both mirror `reference-impl/placement.py` (`disc`/`rect`/`capsule`/`polygon`/`path_mask`,
`apply_masked`, `stamp`), where placements are authored in **metres**.

**Placing a feature takes three things**, and the studio has one node for each:

| | Node | Question it answers |
|---|---|---|
| **Transform** | Filter ▸ Transform | *Where does it go, which way does it face, how big is it?* |
| **Placement mask** | Generator ▸ Shape | *How far does it reach, and how soft is the edge?* |
| **Stamp** | Combine ▸ Stamp | *How does it meet the terrain already there?* |

The **Transform** is a full TRS: **Move X/Y** (shown in metres against the terrain definition),
**Rotation**, **Scale** + **Scale Y**, and a **Pivot**. Rotation is about the **up axis** — the only
rotation a heightfield admits, because tipping the surface would make it multi-valued, two heights over
one point. The **Pivot** is what rotation and scale turn about: leave it centred to spin a ridge in
place, move it to swing that ridge around a point instead. It also has a **Mask** input, so a move can
be confined — verified, change outside the mask is **exactly 0**.

**Stamp** is `placement.stamp`: **Max** unions a landform in without trenching what is already there
(the default, and the only mode that cannot dig a hole), **Add** accumulates relief so overlapping fans
build into a bajada, **Replace** overwrites — which only reads well inside a soft-edged mask. Without a
Mask the patch applies everywhere it is defined; the mask is what turns a global combine into a
*placement*.

Verified in `_verify_trs.js` — the placed centroid lands exactly where asked (`0.7, 0.4` requested and
measured); a 90° turn about the tile centre swings a disc from `(0.75, 0.5)` to `(0.5, 0.75)` with its
radius preserved, while the same turn about a pivot **on** the disc leaves it at `(0.75, 0.5)`; scale
gives **4.00×** and **0.25×** area for 2× and 0.5× exactly as the square law demands; and Stamp's Max
never drops below the base, Add accumulates, Replace overwrites, `Amount 0` and a missing Patch are both
the identity.

Exact and raster sampling describe the *same* placement including the pivot: correlation **0.9977**
across the tile interior. Over the whole tile it drops to 0.944, and that gap is not disagreement about
placement — it is the two modes' different edge policy, since exact mode has real terrain past the old
tile edge where raster has clamped smear. Scoring the interior separates the two.

### Building a mountain range from placed massifs

The reference implementation prescribes the workflow in `landforms.mountain`'s own docstring — *"place
it, combine several (`np.maximum` / `ops_filters.smax`), then run a real hydraulic + thermal pass"* — so
the studio has a node for each step.

1. **Mountain** ×N, in **Peak** form. A placeable massif, ported from `reference-impl/landforms.py` (Génévaux et al. 2015
   *Terrain Modelling from Feature Primitives*; Guérin et al. 2016). Not thresholded isotropic noise,
   which reads as "noise on a lump": a wandering **crest skeleton** of polyline SDFs sets a non-circular
   envelope, a **modulated-Voronoi ridge network** dissects it — cell *edges* become ridgelines, cell
   *interiors* valleys, and a two-scale domain distortion bends them off Voronoi's straight edges into
   spurs — then the style bakes in its weathering. Five styles matching Gaea's presets: **Basic**,
   **Eroded**, **Alpine**, **Old**, **Strata**. Placement is *built in* (Position / Reach / Trend) rather
   than a Transform above it, mirroring the reference impl's `place=`: the crest skeleton is constructed
   at the placed position, so it is exact by construction. 157–482 ms per massif at 192².
2. **Smooth Max** to union them. Union of two *surfaces* is a **max** — the merged terrain is whichever
   is higher.
3. **Thermal** or **Hydraulic** over the union. This is the step that actually makes it a *range*.

### Art direction: author the skeleton, generate the detail

All three reference tools converge on the same idea, and it is not "a mask that gates an effect":

| Tool | How you art-direct |
|---|---|
| **World Machine** | [Layout Generator](https://help.world-machine.com/topic/layout-generator/) — vector polygons/paths/primitives with per-shape elevation, opacity, falloff distance *and profile* (linear / squared / sqrt / S-curve), positive or negative, "breakup" fractal participation, bezier splines, and **per-vertex elevation with keypoints**. Source mode generates; Modifier mode embeds into incoming terrain. Overlaps resolve by greatest height. |
| **Houdini** | [HeightField Project](https://www.sidefx.com/docs/houdini/nodes/sop/heightfield_project) ray-casts real 3D geometry (curves, meshes) into the heightfield with Replace/Add/Multiply/Max/Min, and [Mask by Feature](https://www.sidefx.com/docs/houdini/nodes/sop/heightfield_maskbyfeature.html) derives selections from height, slope, curvature and direction. |
| **Gaea** | Geo primitives (Mountain, Ridge, Crater, Badlands, Dunes), Mask as a primitive, and an [explicitly retired Draw node](https://docs.quadspinner.com/Reference/Primitives/Draw.html) now rebuilt in Gaea 3 to combine vector *and* brush modes. Erosion2 exposes **Shape** and **Shape Sharpness** to trade authored shape against simulated reshaping. |

The **Layout** node is that idea: a list of vector shapes carrying elevation, evaluated as distance →
falloff profile → combine. Academically this is [Hnaidi et al. 2010](https://onlinelibrary.wiley.com/doi/abs/10.1111/j.1467-8659.2010.01806.x),
curves carrying elevation/slope/roughness constraints with the surface diffused between them.

```
path width=0.03 falloff=0.26 profile=scurve op=max breakup=0.45 seed=3
  0.10,0.70,0.35  0.28,0.62,0.85  0.44,0.66,0.55
  0.62,0.52,1.00  0.80,0.46,0.62  0.93,0.52,0.30
```

Shape kinds are `path`, `point` and `poly`; ops are `max` (greatest height wins, as in World Machine),
`add`, `sub` and `replace`; falloff profiles are `linear`, `squared`, `sqrt` and `scurve`; `breakup`
lets a fractal distort the outline so it is not geometric. With no **Base** wired the node generates
(Source); wire one and it embeds instead (Modifier).

**Elevation is per vertex, and that is the whole point.** A path is not a constant-height ribbon — it
carries a height profile along its length, so summits fall out at the high vertices, saddles at the low
ones, and faces fall away either side. Verified in `_verify_layout.js`: vertices authored at
0.30 / 0.90 / 0.45 / 1.00 measure **0.31 / 0.90 / 0.46 / 1.00**, values between vertices interpolate,
and the resulting spine scores 4 summits and 2 saddles along its crest with height falling away
perpendicular. The four falloff profiles are all distinct at the same distance (sqrt 0.698, linear
0.488, scurve 0.482, squared 0.238); overlapping shapes resolve to the greater height; Modifier mode
leaves the base at 0.25 away from the shape and lifts it to 0.80 on it.

#### Do not overthink the mountain — layout is what combining and masks are for

Worth stating as numbers, because it is easy to build the wrong thing and not notice. The measure is
**topographic prominence** — the same one mountaineers use: flood the terrain top-down, and when two
basins merge, the lower summit's prominence is its height above that saddle. A peak has *one* prominent
summit; noise has hundreds.

| | summits >10% relief | 2nd/1st prominence | texture vs a cone |
|---|---|---|---|
| ideal cone | 1 | 0 | 1× |
| **Mountain — Peak** | **1** | **≤0.08** | **29.6×** |
| **Mountain — Massif** | 4–8 | 0.25–0.35 | — |
| ridged fBm | 109 | 0.56 | — |

Note what the first two columns cannot tell you: a smooth cone scores perfectly on both. Texture is the
column that catches it, which is why it is measured now — and why the renders get looked at.

Neither form is noise — both sit at the cone end of the hypsometric scale, an order of magnitude away
from fBm on summit count. But they are different landforms, and the distinction matters when you are
choosing what to place three of:

- **Peak** — a dissected dome. One dominant summit across all five styles and every seed tested
  (second summit at ≤8% of the first), descending monotonically, and **29.6×** more textured than a
  smooth cone of the same footprint. This is the unit you place.

  Getting here took two wrong turns, both worth recording because they were the *same* mistake. First
  `env(r) × spurs(θ)` — a radially symmetric envelope with flutes — a fluted cone. Then a ridge
  skeleton evaluated as planes anchored on arêtes, which measured *better* on asymmetry and still
  produced a **smooth pyramid**, because planar faces carry no texture at all. Both passed every
  statistic being measured — one summit, monotonic descent, prominence — since a cone satisfies all of
  them. The statistics were not wrong; they simply do not measure the thing that makes a mountain look
  like one, and nobody had rendered the output to check.

  **The skirt is the difference between a mountain and a pudding.** An outside review called the
  render "pudding on a plate" and blamed the base noise, suggesting we swap in Cellular or Ridged
  instead of Perlin. That part was wrong — the basis was already modulated Voronoi (`worleyAt` F2−F1,
  two octaves) with two-scale domain warping. The real defect was the envelope: `(1−r²)^p` has a
  measured slope of **−0.001 at the summit**, i.e. flat on top and steepest halfway out. That is a
  *bell*, and no amount of texture rescues a bell. `(1−r)^skirt` is steep at the summit (−1.386) and
  convex all the way out to −0.302 at the rim — the concave **pediment / talus apron** a real massif
  grades into, reaching exactly zero so there is no seam to feather. The **Skirt curve** parameter is
  that exponent: 1 is a straight cone, higher gives a sharper peak with a wider sprawling apron, below
  1 gives a plateau with an abrupt rim.

  **The skirt is drawn, not typed.** The exponent is gone; the Mountain node carries a curve editor in
  the properties panel. X is distance from the centre (0 at the summit, 1 at the radius), Y is the
  elevation multiplier (1 → 0). Drag control points to shape the apron, click empty space to add one,
  double-click to remove; endpoints stay pinned in X so the curve always spans exactly centre → rim.
  Presets: **Cone**, **Apron**, **Sweeping**, **Plateau**.

  | | |
  |---|---|
  | Interpolation | Monotone cubic Hermite (Fritsch–Carlson) |
  | Baked to | 256-entry `Float32Array` LUT, once per evaluation |
  | Read as | one lerped lookup per cell — cheaper than the `pow()` it replaced |

  Monotone cubic rather than a plain bezier or Catmull–Rom for a specific reason: **an overshooting
  spline is an invalid envelope.** Above 1 puts terrain higher than the summit; below 0 puts it under
  the plane. Monotone cubic cannot overshoot by construction, so every curve an artist can draw is
  valid. Verified against a deliberately nasty control set (a near-vertical drop between two nearly
  flat runs): the LUT stayed inside [0, 1] and stayed monotone throughout. The bake also reproduces
  the analytic `(1−r)^1.4` it replaced to a max error of ~1e-3, with exact endpoints.

  The curve genuinely drives the landform — mean apron height at 70% of the radius, by preset:
  Plateau **0.299**, Cone **0.196**, Apron **0.121**, Sweeping **0.043**, all distinct and ordered as
  the shapes imply. A hand-drawn curve matching no exponent works the same. Dragging a control point
  in the live widget changes the terrain (mean |Δ| 0.016).

  The footprint cut is now **binary at the envelope's own support** rather than a linear collar over
  the last 6% of the radius. The collar was mine, added to kill erosion speckle, and it re-introduced
  exactly the hard seam it was meant to hide.

  Measured against Gaea's default Alpine mountain, the macro shape *is* roughly a radial dome. What
  makes it read as a mountain is the **density of drainage dissection** — dozens of fine valleys
  running out from the high ground with sharp spurs between them. So Peak is a wobbled dome envelope,
  dissected by a dense modulated-Voronoi drainage network, then eroded. **Drainage detail** is the
  parameter that actually controls how mountainous it looks.

- **Massif** — `Crest lines` unioned into a small range, which is what `landforms.mountain` builds by
  design (its docstring: *"n_ridges crest lines unioned into a small range"*). Right for a shoulder or a
  plateau edge; wrong as the thing you place three of, because you would be unioning three small ranges.

**Two parameter bugs found the same way.** `Spurs` (in an earlier polar-Voronoi form) had no effect
at all — 4, 7 and 12 all produced ~22–30 angular maxima. Its replacement, `Drainage detail`, had the
*opposite* of the intended effect: fine-detail energy **fell** from 0.0089 to 0.0056 as detail went
0.6 → 3.4, because the Voronoi network was normalised by a hardcoded constant while Worley F2−F1 scales
with cell size, so finer cells incised more shallowly. Normalising by a percentile of the network makes
incision scale-free; detail then spans **2.9×** across its usable range and **saturates** past ~2–3×,
where the talus pass relaxes anything finer than its own scale. That is a real floor on feature size,
and it is why the default sits at 2.6. On heavily eroded styles the sweep reads flat (ratio 0.96)
because erosion overprints the network — a fact about erosion, not about the knob.

Two of the measurements used to check this were themselves broken and had to be thrown out: an angular
crest count saturated at ~130 regardless of input at 192², and requiring *exactly* one summit is what
let the smooth pyramid through. The invariants that survive are scale-free — fine-detail energy per
unit height, one clearly dominant summit, few summits.

Giving `basic` a talus pass was a real fix that fell out of this: with zero weathering, dense
dissection left **45** crumpled Voronoi spikes rather than a mountain. A surface with no talus is
unphysical whatever the style.

The primitive also stays strictly inside its own footprint (total height outside it is exactly **0**),
because erosion otherwise scatters deposit onto ground the primitive does not own — and a primitive
that respects its footprint is the one that composites cleanly under Stamp and a placement mask.

**Every placed node gets its own seed.** Node parameters used to be initialised straight from the
type defaults, so three placed Mountains were three *identical* mountains and the whole
place-and-combine workflow was pointless. A node carrying a `seed` now derives it from its own id —
**derived, not random**, so the same graph built the same way reproduces exactly across reloads and in
the verifiers. Three fresh Mountains get seeds 459 / 895 / 604; rebuilding the graph gets the same
three. Verified with the control that gives the number meaning: two mountains sharing a seed are
bit-for-bit identical, while two with different seeds differ by **10%** of total height inside the
footprint. *Duplicate* stays a true copy — nudge the Seed slider to fork it.

Verified in `_verify_range.js`. Three Mountains placed at X = 0.26 / 0.50 / 0.74 land at measured
centroids **0.281 / 0.505 / 0.722**, each with relief ≈ 0.84–1.08. Unioning with Smooth Max instead of a
hard Max cuts the curvature crease along the seam (135 seam cells) by **74.9%**.

The finding worth stating plainly: **three unioned massifs are not yet a range.** Thresholded at 35% of
peak height, the union is **4 disconnected components**. After a thermal pass it collapses to **1**
component of 20,833 cells. Erosion is what knits separate massifs into one connected landform, which is
also why the primitive is documented as *"ready for further erosion"* rather than finished.

**Smooth Max vs Smooth Min.** These are not interchangeable, and the studio previously had only the
wrong one — `smin` was labelled "crease-free smooth union", which it is not for a heightfield. `smin`
takes the *lower* envelope: applied to three peaks it produced a mean height of **−0.037** and collapsed
relief to 0.047, deleting every summit. Smooth **Max** is the union; Smooth **Min** is the intersection,
useful for carving. Both ship, correctly described, mirroring `ops_filters.smax` / `smin`.

**The SatMap node — Gaea's colouring model.** In Gaea a SatMap is a *node* that colours a terrain through a
gradient, driven by **whatever grayscale you feed it** (not only height). This node mirrors that: it takes
an **In** (the height, passed through unchanged), an optional **Driver** input, and an optional **Mask**
input, with **Driven by** = *Driver ▸ / Height*, *Height*, or *Slope*. So you can colour by **elevation**
(the classic SatMap), by **slope** (cliffs one colour, benches another), or by **any field you wire into
Driver** (flow, a mask, a Blend). It picks a **Gradient** from the library (including ones you author in
SatMap Studio) and applies **Reverse**, **Range** (use just a slice of the gradient) and **Shift** (offset
the lookup) — the same transforms Gaea's SatMap node exposes.

- **Bind a SatMap to any Data map — the same channels Gaea offers.** In Gaea a SatMap is a CLUT fed by
  *any* grayscale, and what you feed it comes from the **Derive / Data Maps** family (Slope, Curvature,
  FlowMap, Occlusion, Peaks, Soil, RockMap, Texture…) or from simulation data outputs (Erosion emits
  **Wear** = where sediment was stripped, **Deposits** = where it came to rest, **Flow** = the path
  between). The **Data map** node group mirrors that set: **Slope**, **Curvature** (Zevenbergen–Thorne
  profile/plan/mean), **Flow** (priority-flood + D8 accumulation), **Occlusion** (horizon AO),
  **Deposits** (morphological closing − surface, i.e. what piles into hollows), **Wear** (convex, steep,
  exposed ground), **Peaks** (prominence over the local mean), and **Texture** (Gaea's composite
  slope + soil + flow driver). Wire any of them into a SatMap's **Driver** — or into a **Mask** — so
  colour follows rivers, cavities, sediment or ridges rather than only elevation. All mirror
  `reference-impl/analysis.py` + `flow.py`. *(Difference to note: Gaea's Erosion node emits Wear/Deposits/
  Flow as extra output ports of the simulation; our graph gives one output per node, so these are
  standalone nodes that derive the same channels from the height field.)*
- **Colour flows through the graph — branch, blend and stack.** Colour is resolved by walking the graph:
  a SatMap **composites its ramp over the colour already coming down its In chain** (so chaining
  `… → SatMap(base) → SatMap(rock) → Output` stacks them, each with **Opacity**, **Blend**
  (Normal / Multiply / Screen) and an optional **Mask**); a **SatMap Blend** node **merges two separate
  SatMap branches** — wire `SatMap A → A`, `SatMap B → B`, a mask into **Mask** — exactly Gaea's
  SatMap-combine; and any other node (erosion, filter) just passes colour through. So you can build a real
  colour graph — e.g. an elevation SatMap and a flow-driven SatMap blended by a slope mask. It's resolved
  per-vertex on the CPU into the terrain's albedo. Blend modes are **Normal / Max / Min / Multiply /
  Screen / Overlay** — Gaea's own documented SatMap-blend technique is two SatMaps through a Combine node
  at **Max**, masked by noise, which this reproduces.
- **2D biome (altitude × slope).** Switch **Mode** to *2D biome* and the node blends **two** gradients — a
  flat-ground **Gradient** and a steep-ground **Steep gradient** — by slope: green valleys and gentle
  ground read from the first, cliffs and scree from the second. That's the classic 2D terrain LUT
  (altitude on one axis, slope on the other), built from two 1-D ramps.

With no SatMap node in the graph, the viewport falls back to the global SatMap dropdown driven by elevation.

## Controls

- **Double-click** empty canvas (or **＋ Add node**) to add a node.
- Drag a node's **right port** into another node's **left port** to wire them (cycles are rejected).
- Click a node to edit its parameters on the right; **Duplicate** / **Delete** or press <kbd>Del</kbd>.
  Deleting a mid-chain node **auto-bridges** its neighbours (its input source reconnects to its outputs)
  when the input is unambiguous, so the pipeline stays connected.
- Pan with **middle-drag** / space-drag / empty-drag; **wheel** to zoom the graph.
- In the 3D view: **drag** to orbit, **wheel** to zoom, <kbd>F</kbd> to frame.
- **Auto** recomputes on every edit; turn it off and use **Build** for heavy graphs.

## Design — learning from Gaea, World Machine and Houdini

The brief was to learn from the strengths *and* weaknesses of the three baselines:

- **Adopted — Gaea:** a per-node **live preview thumbnail** and beautiful, sensible defaults, so the
  graph is legible and the first result already looks like terrain.
- **Adopted — World Machine:** a clean, single-window **device-graph** model — generators → filters →
  erosion → output — with an explicit Output node, easy to reason about.
- **Adopted — Houdini:** real **procedural depth** (physically-motivated erosion, masks, warps that
  compose arbitrarily) rather than a fixed pipeline.
- **Avoided:** Houdini's learning cliff (approachable palette grouped by category, no network of
  wrangles to learn), World Machine's dated UI (a modern, calm dark theme with a considered
  hypsometric-amber accent), and node sprawl (a curated, meaningful node set — every node maps to a
  grounded atom, nothing decorative).

The palette is cool deep-slate grounds with a single warm **hypsometric sand/amber** accent (elevation
/ contour, from topographic cartography) and a restrained water-teal for flow; monospace, tabular
readouts give it the feel of a precision instrument. Light and dark themes are both first-class.

## How it relates to the rest of the skill

Compute runs on the **CPU** (deterministic `Float32Array` heightfields) so it mirrors the verified
`reference-impl/` algorithms exactly; the **WebGL** layer is the 3D render. It is a *look-and-feel*
authoring tool — the numerically-validated implementations, oracles and cross-checks live in
`reference-impl/`. Verified headless with Playwright (graph eval, WebGL init, all interactions,
import/export — no console/page errors) during development.

### Spatial scale — the same effect over a bigger or smaller area

Two Gaea mechanisms, both now here:

- **Feature Scale** on **Thermal** and **Hydraulic erosion**. Gaea's Erosion node describes it as
  *"the lateral size of the largest erosion features in meters: width of largest valleys and ridges
  between them."* Ours is a `1×–8×` multiplier: the simulation is run on a grid that many times
  **coarser** (so its footprint is that many times wider) and only the *change* is resampled back onto
  the full-resolution terrain — fine detail survives, the erosion's footprint grows. The coarse cell is
  `feature × cellSize` metres, which is the lateral size the sim actually sees. Measured: the erosion
  delta widens 2.76 → 4.32 → 5.8 cells at 1× / 3× / 6× (the metric saturates for wide features, so read
  it as monotonic rather than proportional) — and it gets *faster*, 183 ms → 5 ms, since the grid is smaller.
- **Transform** node (Filter group) — Gaea's Transform: **Scale**, **Scale Y**, **Angle**, **Offset X/Y**
  and a Clamp / Wrap / Mirror edge mode, usable anywhere in the graph. Scale >1 magnifies. Verified
  against an analytic oracle: transforming a sine reproduces `sin()` at the inverse-mapped coordinate to
  **max error 0 / 0.0064 / 0.008** at 1× / 2× / 4× (bilinear interpolation error only).

**Place before you sample — the Transform is exact over a procedural chain.**
A procedural generator is a *function of position*, so evaluating it at transformed coordinates moves,
turns and resizes the feature **exactly**: the same function, sampled somewhere else. Transforming the
finished *raster* instead costs a bilinear resample, and bilinear is a low-pass filter. So the Transform
node checks what is upstream and picks:

| Upstream chain | Mode | What happens |
|---|---|---|
| Only generators (Perlin, Ridged, Voronoi, Gradient, Shape, Constant) and per-pixel ops (Levels, Curve, Clamp, Invert, Terrace, Blend, Combine, Max/Min, Smooth Min) | **Exact** | The placement is folded into the generators' coordinates and the chain is re-evaluated. No filtering, no detail loss — and the terrain *continues* past the old tile edge instead of clamping, so **Edges** is unused. |
| Anything that reads neighbours or the whole field — erosion, Warp, Blur, Histogram EQ, an imported DEM | **Raster** | The finished heightmap is resampled, as in Gaea and World Machine. Move the Transform *below* the erosion to get the exact path back. |

**Sampling** (*Exact* / *Raster*) forces the choice, and the properties panel says which one is live.
Stacked Transforms **compose into one matrix**, so N moves still cost exactly one evaluation — this is
`reference-impl/placement.py`'s `affine` / `compose` / `sample_coords` in normalised tile units, where
`sample_coords` applies `M⁻¹` because the feature moves by `M` while the *sampler* moves the opposite way.

Measured on fBm as mean |laplacian| (`_verify_exact_transform.js`) — exact placement loses **none** of the
fine detail at any depth, while each raster hop is another low-pass:

| Operation | Detail lost, raster | Detail lost, exact |
|---|---|---|
| 2× magnify | 27.2% | 0% |
| 1 non-integer move | 24.7% | 0% |
| 4 chained moves | 53.8% | 0% |

Also verified: identity is **bit-for-bit** the untransformed field (max diff `0`); the exact 2× result
matches an independent direct evaluation of the transformed coordinates to **max diff `0`**; `2× ∘ 2×`
equals a single `4×` to **`0`** in both matrix and field; the graph picks *exact* for a Perlin chain and
*raster* after a thermal node; and **CPU/GPU parity survives the transform** (max diff `2.5e-5`, the same
float32 floor as before — the placement matrix is a shader uniform, so both paths sample identical
coordinates).

### Terrain definition (real-world scale) and **Real Scale**

Deselect everything and the properties panel shows the **Terrain definition** — the world this heightfield
represents, in metres. Defaults match Gaea's: **5000 m across × 2600 m tall**, a **vertical ratio of 0.52**
(`height ÷ scale`), which is also the viewport's vertical exaggeration. Cell size is `scale ÷ RES`
(26 m at 192², 4.9 m at 1024²).

That is what makes slope **angles** physical, so — as in Gaea, where *"the only place the terrain scale
affects how your terrain is processed is when `Real Scale` is turned ON in the Erosion, Snow, or Thermal
nodes"* — the **Thermal erosion** node has a **Real Scale** switch. With it on, `Repose angle` is a true
angle: the per-cell drop becomes `tan(angle) · cellSize ÷ height`, which is *inherently* resolution
independent. Verified — a 35° repose stays exactly 35° at 128², 192², 256² and 512², with the per-cell
drop halving as the cells do.

### Resolution independence (the **Res Lock** toggle)

Several node parameters are expressed **in cells**, so raising the resolution silently changes what they
mean. The worst offender is thermal `talus`, a height drop *per cell*: cell spacing is `1/RES`, so the
repose **angle** it encodes is `atan(talus·RES)` — **66° at 192² but 85° at 1024²**. At high resolution the
talus angle is near-vertical, thermal erosion barely runs, and the build comes out **spiky**. Droplet
density (a fixed count spread over `RES²` cells) and blur/deposit/peak radii have the same problem.

**Res Lock** (on by default) converts these to resolution-independent quantities against a 192² reference:
`talus/k` (constant angle), `iters·k` (constant travel distance), `droplets·k²` (constant density),
radii `·k`. Measured on the default graph, comparing a 1024² build downsampled to 192²:

| scaling | spikiness vs 192² | build cost |
|---|---|---|
| off | **3.15×** | 4.6 s |
| talus only | 1.97× | 4.5 s (free) |
| talus + droplets·k² | 1.85× | 15.3 s |
| talus + iters·√k | 1.55× | 7.2 s |
| **full (default)** | **1.21×** | 25.4 s |

Fixing the talus angle is the single biggest win and costs nothing; the rest buys the remaining parity by
doing proportionally more work — which is the honest price of resolution independence, and why a 1024²
build is a **Build**, not an Auto-recompute. (Gaea documents the same goal: a 512² preview keeps *"essential
parity for all major erosion features"* with a 4K/8K build.) Turn **Res Lock** off for fast iteration at
high res, at the cost of a spikier surface. Timings are under a software rasteriser; the droplet term is
the CPU sim, so a GPU pipe-model hydraulic would remove most of that cost.

### GPU fast path (WebGL2 GPGPU)

The **CPU kernels remain the reference implementation**. On top of them there is an optional GPU path
(the **GPU** button in the toolbar) that runs the heavy, embarrassingly-parallel kernels as fragment
shaders over a fullscreen triangle into `RGBA32F` ping-pong render targets — the same technique as the
deferred composite. Currently GPU-accelerated: **Perlin fBm**, **Ridged MF** and **thermal erosion**.

It produces the *same* terrain as the CPU because the 32-bit integer hash is reproduced exactly in GLSL
`uint` (the CPU hash now uses `Math.imul`; plain `*` silently rounded past 2⁵³). `_verify_gpu.js` is the
parity check — measured **max |Δ| ≈ 2.6e-5 (Perlin), 1.1e-4 (ridged), 4.8e-7 (thermal)**, i.e. float32
-vs-float64 rounding, not algorithmic drift.

This is what makes **512² and 1024²** practical: a 1024² build is 1,048,576 cells / 2.09M triangles.
Selecting ≥512² switches **Auto** off so you drive it with **Build**.

Thermal runs as **two passes** — one memoising each cell's `(move, sum)`, one redistributing — because the
obvious single-pass version recomputes every neighbour's `moveSum` (72 texture fetches per cell vs ~27).
Profiling a 1024² build showed thermal at **84% of total time**; the split cut the whole build from
**10.6 s → 3.9 s** with parity unchanged.

Honest scope: **hydraulic (droplet) erosion is still CPU** — the particle sim scatters writes, so it wants
the virtual-pipes model to go on GPU (planned, mirroring `reference-impl`'s `pipe_erode`). It is only ~17%
of a 1024² build, so it is no longer the bottleneck. The priority-flood + D8 pair behind lakes/rivers is
inherently sequential and stays CPU; it is now skipped entirely unless a **Water** node needs it. Each GPU
node still reads its result back to a `Float32Array` for the next node — keeping the field resident in a
texture across nodes is the remaining big win. Timings measured in CI are under **swiftshader** (a
*software* rasteriser) and so understate real-GPU gains substantially.

## Verification

Every measured number in this file comes from a headless script that anyone can re-run — they ship
alongside the app rather than being scratch:

```sh
npm i playwright-core@1.49.0
node _verify_exact_transform.js      # exact vs raster placement, compose, CPU/GPU parity under XF
node _verify_trs.js                  # translate/rotate/scale about a pivot, Transform mask, Stamp
node _verify_range.js                # place 3 Mountains, union with Smooth Max, erode into one range
node _verify_peak.js                 # prominence: Peak is one summit, Massif is several, neither is noise
node _verify_curve.js                # skirt curve: monotone bake, LUT contract, widget drag
node _verify_layout.js               # Layout: per-vertex elevation, falloff profiles, ops, Source/Modifier
node _verify_gpu.js                  # CPU/GPU bit-parity + timings
node _verify_placement.js            # SDF Shape masks + the universal Mask rule
node _verify_featurescale.js         # Transform against an analytic sine oracle; Feature Scale widths
node _verify_resparity.js            # Res Lock: same terrain at 192² / 384² / 768²
node _verify_realscale.js            # Real Scale: repose angle in degrees, resolution independent
node _verify_data.js                 # the eight Data Map channels
node _verify_satnode.js              # SatMap node: stacking, branch+blend, 2D biome
node _verify_satgen.js               # SatMap Studio extraction + LUT build
node _verify_highres.js              # 512² / 1024² build timings
node _verify.js                      # graph editor interactions (add/wire/rewire/cycle/delete/pan/zoom)
```

They drive the real page in Chromium and assert on the actual field data, not on screenshots. Note that
CI runs them under **swiftshader**, a software rasteriser, so every GPU timing they print is a floor —
real hardware is substantially faster. Non-timing results (parity, oracles, invariants) are unaffected.

Claims that cross into the Python skill are pinned twice: the raster-vs-exact detail loss quoted above,
for instance, is enforced by `reference-impl/tests/test_placement.py::test_raster_transform_loses_detail_that_placement_keeps`
as well as by `_verify_exact_transform.js`, and the two independent implementations agree to within
0.6 percentage points.
