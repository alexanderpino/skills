# Terrain Studio — node-based WebGL terrain generator

An installable terrain generator that runs in the browser: a **node graph** drives a live **WebGL 3D
viewport**. It's the interactive companion to this skill's pure-NumPy `reference-impl/` atoms — the
same algorithms (fractal noise, domain warp, thermal & hydraulic erosion, histogram equalisation,
slope/height masks, real-DEM import) exposed as a graph you build and tune by eye.

**Run it:** `.\run-studio.ps1` (dev, `:5173`) · `-Mode pwa` (production build + preview, `:4173`) ·
`-Mode build` (build only). There are no runtime dependencies — the toolchain is Vite and Playwright,
and the app itself imports nothing.

> **Opening `index.html` from disk no longer works, and that is deliberate.** The app is an ES
> module, and module scripts are fetched with CORS semantics: a `file://` origin is opaque, so the
> page comes up blank. It needs an origin. `localhost` counts as a secure one, which is also what
> lets the service worker register — so the same change that ended `file://` is what made the app
> installable and offline-capable.

The build emits a small set of files rather than one: `index.html`, a hashed JS bundle, the
manifest, icons, and `sw.js`. The single-file build this README used to describe was never
engineered — it fell out of the script happening to be inline, and a service worker needs real,
separately-addressable, content-hashed assets to cache and update. That trade was taken knowingly.

![Terrain Studio](../reference-impl/gallery.png)

## What it does

- **Production authoring workspace**: the **stacked vertical layout is the first-run default**,
  with the live rendering above the graph while Properties remains full-height; switch to the side
  layout when wanted. The rendering has a
  real browser **fullscreen** control, deliberate **Hero / Plan** cameras, and an **Output / Selected**
  display flag so any intermediate node can drive the viewport without rewiring the graph. Graph edits
  are undoable/redoable (including topology, node moves, parameters and terrain definition), and each
  node reports its last evaluation time directly on the graph.
- **Node graph** (the core): drag nodes, wire outputs into inputs, and every node shows a live
  hill-shaded **thumbnail** of its own output — so you read the pipeline at a glance.
- **Scene-linear deferred PBR surface + SatMap colour**: the terrain renders through a two-stage
  deferred pipeline. Authored SatMap colours are decoded from **sRGB to scene-linear albedo before
  lighting**, and the final HDR image is exposed, ACES-tonemapped, then encoded back to sRGB. This
  fixes the chalky, low-contrast result caused by lighting display-space colours. The terrain pass
  writes only **albedo** (SatMap colour + terrain-aware mineral exposure + snow) and per-material
  **perceptual roughness** into a G-buffer; a fullscreen composite then does all lighting:
  *all* the lighting from the height field:
  - **per-pixel surface normals** reconstructed from central differences of the height texture
    (finer than the mesh vertex normals),
  - **sun** (Lambert) **+ hemispheric sky-irradiance ambient** — a warm ground-bounce → cool sky-dome
    gradient, so shadowed faces read *blue* instead of flat grey (the single biggest realism lever),
  - an energy-balanced **Cook–Torrance GGX** BRDF with Smith visibility and Schlick Fresnel, driven by
    soil / rock / snow roughness, plus derivative-based specular anti-aliasing,
  - subtle multi-scale, non-directional albedo breakup and material normals, so a SatMap does not read
    as smooth elevation bands while still remaining an unlit material map,
  - **soft ray-marched cast shadows** toward a **movable sun** (azimuth + elevation sliders) and
    **horizon ambient occlusion** (crevice darkening), folded into the same pass,
  - a richer **analytic sky** (horizon→zenith gradient, sun disk, aureole, near-sun horizon scatter)
    and distance-tinted **aerial perspective**, resolved through **ACES** tone mapping and
    **supersampled** for anti-aliased silhouettes,
  - **Realistic, Clay, Albedo, Slope, and Normals** viewport styles. Albedo is deliberately unlit, so
    SatMaps can be judged without the sun; Clay isolates terrain form; Slope and Normals expose data.
    Sun azimuth/elevation, **exposure in stops**, and **haze** are live look-development controls.
  - Water uses dielectric Fresnel (F0 ≈ 0.02), wavelength-dependent **Beer–Lambert absorption**, a
    screen-stable shoreline, restrained ripples, and reflected scene-linear sky radiance.
- **SatMaps genuinely derived from real satellite imagery** (not hand-picked): pick from ~26 palettes
  in the viewport. The core set (Temperate, Alpine, Verdant, Canyon, Arid, Dune, Volcanic, Mars, Lunar,
  Arctic, Tundra) plus **Estuary/Dusk** and a **13-strip set** (Steel, Moss, Pewter, Copper, Chrome,
  Ash, Terracotta, Savanna, Frost, Fjord, Amber, Brass, Harvest) **traced from Gaea SatMap screenshots**
  — each gradient strip read as a per-column median of the bar (Dusk being the selected in-range window).
  Of the core set, **seven are extracted from real public-domain top-down satellite/aerial imagery** — the
  source image is ordered by luminance into an elevation ramp by the skill's own `reference-impl`
  `extract_satmap`, following the colour-lookup workflow Gaea documents, done reproducibly rather
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
- **Live 3D viewport** with **multi-stage rendering**: WebGL2 lit terrain mesh (the five render
  styles above, orbit + zoom, wireframe), rendered in two passes —
  1. **Opaque terrain + snow** — the **Snow** effect node produces a world-metre thickness field.
     Its mass-conserving stability pass unloads steep faces into gullies and hollows, physically
     displaces the mesh, rebuilds its normals, and drives a rough snow material. Temperature, lapse
     rate, mixed rain/snow, degree-day melt, and equator-facing solar warming determine what remains.
  2. **Water surface + composite** — a rasterized fluid-depth layer followed by screen-space
     refraction, absorption, Fresnel reflection, restrained animated ripples, and shoreline foam.
     It uses a **hydrologically
     correct water surface**, not a flat cut through the heightmap:
     - **Lakes** fill each closed basin to its own **spill level** via a
       **priority-flood depression fill** (Barnes 2014) — flat lakes whose edges follow the basin
       rim, at the right elevation for each basin.
     - **Rivers** are the **flow-accumulation** drainage network (D8 on the filled DEM): **River
       network** changes its catchment threshold and **River depth** changes its visible water film.
       A sub-visible epsilon gradient routes flow across filled flats instead of terminating in them.
     - **Sea level** mode instead lays a flat ocean at a chosen level — the simple, level-based water.
     The water-surface normal is computed from that surface (flat in lakes, sloped along rivers). This
     is the same `priority_flood_fill` + `d8_accumulation` pair the reference-impl uses.

  **Surface-aware deferred compositing.** On WebGL2 the terrain first renders into an offscreen
  **colour + depth** G-buffer. The hydrological surface is then rasterized into a separate
  **water-mask + water-depth** layer, after copying terrain depth so only genuinely visible fluid wins.
  A fullscreen triangle reconstructs both the lakebed and the actual fluid-plane world positions and
  composites **sky** and **water** analytically. Because it has the
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
| **Generator** | Perlin fBm · **Simplex fBm** (triangular-lattice, isotropic noise) · Ridged MF · Voronoi (F1/F2−F1) · Gradient (linear/radial) · Constant · **Layout** (authored vector skeleton with per-vertex elevation) · **Mountain** (Mountain / Mountain range; 4 shape families × 5 geomorphic types) · **Canyon** (cached landscape evolution: uplift, drainage competition, stream-power incision, lithology and hillslope retreat; five formation styles) · **Shape** (SDF placement mask) · **Import DEM** (file *or* one-click real SRTM sample) |
| **Combine** | Blend (factor or mask) · Combine (add/sub/mul) · Max/Min · **Smooth Max** (crease-free union) · Smooth Min (intersection) · **Stamp** (place a patch onto a base through a mask) |
| **Filter** | Warp (domain warp) · **Transform** (translate/rotate/scale about a pivot, maskable, exact over procedural chains) · Terrace · **Normalize** (maskable) · Levels · Curve (bias/gain) · **Histogram EQ** · Blur · **Sculpt** (Raise/Lower/Flatten/Smooth through a mask) · Clamp · Invert |
| **Erosion** | Thermal (talus) · Hydraulic (GPU pipes / CPU droplets) · **Erosion 2** (multi-scale hydraulic, sediment discharge, shape) · **HydroFix** (low-amplitude drainage repair) · **Stream power** (fluvial incision, Braun–Willett implicit solver) |
| **Mask** | **Draw Mask** (editable vector brush strokes) · Slope select · Height select · **Temperature select** (physical °C biome band) |
| **Data map** | **Height** · **Sun Shadow** (terrain-horizon visibility) · **Temperature** (base climate field) · **Temperature Modify** (localized heat/cooling) · **Wind** (terrain-adjusted physical vectors) · **Wind Modify** (masked regional circulation) · **Slope** · **Curvature** (profile/plan/mean) · **Flow** (accumulation) · **Occlusion** (horizon AO) · **Deposits** (soil) · **Wear** · **Peaks** · **Texture** (slope+soil+flow composite) |
| **Effect** | **Water** (Hydrology = lakes + rivers, or Sea = a flat level) · **Snow** (metre-depth placement, melt, avalanches) · **SatMap** (one colour LUT) · **Color Erosion** (pigment transport/deposition) · **Weathering** (exposure/recess ageing) · **Color Blend** (two branches + mask) · **Color Mixer** (ordered 2–15 layer stack) |
| **Output** | Output (drives the viewport / export) |

**Water extent, snow and colour are nodes, not global switches.** Add and wire them into the pipeline; for example,
`… → erosion → SatMap → Color Erosion → Weathering → Output`. The viewport picks up whichever effect nodes
feed the Output. The **Water** node's **Mode** is either **Hydrology** (basin lakes + downhill rivers) or the
simple **Sea level** (a flat ocean at a level); its **Temperature** input controls liquid/ice phase independently
of Snow. Wave pattern, strength, scale, speed, and refraction are
**global renderer settings** in the viewport's Water Surface flyout: they describe how every fluid surface
is viewed, not where water exists. Waves are sampled at the reconstructed water-plane world position—not the
terrain/lakebed position—so motion cannot look glued to the heightmap. Effect nodes pass height through unchanged and add
or transform a separate scene/colour stream, so deleting one removes just that effect.

The default terrain ships with the full surface graph already wired:
`Thermal → SatMap → Color Erosion → Weathering → Water → Snow → Output`, plus
`Thermal → Deposits → Color Erosion.Sediment` and the explicit climate branch
`Weathering → Height → Sun Shadow → Temperature → Temperature Modify`, plus
`Height → Wind`, with those final physical fields wired to Water/Snow temperature and Snow wind.
Water is deliberately before
Snow: open liquid masks terrain snow out, while frozen standing water can receive a separate raised
snow-on-ice layer. Its Snow node starts with a 3 m settled-snow event, temperature/lapse melt, aspect
warming, and avalanche settling. The renderer supplies subtle animated ripples globally.

**Art direction — Shape masks and the universal Mask input.** A procedural graph that only generates
*everywhere* can't be directed, so two things make it placeable, mirroring Gaea (where "almost every
node contains a Mask input port… the processing of that node is applied only within the masked area"):

- A **Shape** generator — an SDF placement mask (circle / box / line) with position, size, aspect,
  rotation and a soft **falloff**, authored as a fraction of the terrain so it stays put when the
  resolution changes. Like Gaea's Mask-as-Primitive it is *both* a mask and a heightfield: wire it into
  a Mask input to confine an effect, or erode it directly into a landform.
- A **Draw Mask** node for artist-authored roads, corridors and regions. **Draw on terrain…** opens a
  plan-view editor over the optional Reference input with Draw/Erase, width, hardness, opacity, stroke
  undo and clear. Strokes are stored as normalized vectors rather than a fixed-resolution bitmap, so
  masks painted at 512² remain crisp when the graph builds at 2K or 4K.
- A mask-aware **Sculpt** merge modifier. Feed the existing terrain into **In**, Draw Mask into
  **Mask**, then choose **Raise**, **Lower**, **Flatten**, or **Smooth**. The modified copy is blended
  back only through the mask, so outside the painted road or region stays bit-identical. Blur the mask
  before Sculpt when a road needs broad, soft shoulders.
- A **Mask** input on **Thermal**, **Hydraulic**, **Warp**, **Terrace**, **Blur**, and **Sculpt** — the effect runs,
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

### Tectonic uplift — Voronoi plates as the structural skeleton

Ported from `reference-impl/tectonics.py`'s `plate_uplift` (chapter 02). Voronoi cells are the classic
model for plate and block structure, but raw Voronoi edges are dead straight and that is the giveaway
in any plate map — so the coordinates are **domain-warped** before assignment and the sites are
**Lloyd-relaxed** so plates come out evenly sized instead of slivered. Each boundary is classified from
the relative velocity of its two plates — continent–continent collision, subduction, island arc, rift
(diverging, so subsidence) or transform (shear, ~no uplift) — and the uplift is diffused **inland**
over the orogen width, because a mountain belt is a broad welt rather than a line.

Its purpose is to drive Stream power's **Uplift** input: **this gives the structure, the rivers give
the topography.** F-tier — a plausible planar plate sketch, not plate physics.

Verified: orogen width monotonically widens the belt (0.019 → 0.063 → 0.131 of the tile), more plates
give more boundary, warping relocates 21% of belt cells, and handing the result to stream power yields
terrain **4.8× more textured than the uplift that produced it** with a drainage network reaching 1434
cells.

**A continent rises as a whole, not only along its belts.** Uplift confined to boundary belts leaves
the rest of the tile at base level, so the carved result came out **90% dead flat with razor blades
where the belts were** — slope median 0 and p90 0.47 against a real SRTM tile's 2.45 and 9.26, with a
maximum of 44.3 against the real tile's 22.8, i.e. edges twice as steep as anything real. **Continental
uplift** restores the per-plate base the reference includes, and the land mask is blurred over the
orogen scale so plate margins are shelves rather than cliff walls.

**The slope distribution is checked against the embedded real SRTM tile**, which is the strongest
grounded test in the studio and the thing that identified "spiky and erratic" precisely:

| | median | p90 | p99 | max |
|---|---|---|---|---|
| real SRTM | 2.45 | 9.26 | 15.72 | 22.8 |
| tectonic → stream power, shipped defaults | 3.72 | 10.27 | 16.49 | 24.8 |

Within about 1–2 units at every percentile. One caveat worth stating: the embedded DEM is the Colorado
**Plateau**, so matching its slope distribution does not by itself validate mountain-*range*
morphology — it rules out razor edges and dead-flat plains, not much more.

**Zero has to mean zero in an uplift field.** Rifts contribute *negative* boundary values, and
normalising the result mapped that negative floor to 0 — pushing "no uplift" up to the middle of the
range. Measured, the 25th, 50th and 75th percentiles all sat at **0.377**: a constant uplift over most
of the tile, which is why everything came out mountainous instead of just the belts. Clamping
subsidence away and scaling by the peak fixed three separate failing assertions at once — belt width,
plate count and drainage all became monotonic — because they were one bug, not three.

### Stream power — the process that organises a landscape

`dh/dt = U − K·A^m·S^n` (n = 1), Braun & Willett 2013's O(N) implicit solver, ported from
`reference-impl/erosion_streampower.py` where it is cross-validated against Landlab.

This is the piece that was missing, and its absence explains a lot. Drainage area **A** is what makes
valleys join into a tree and deepen downstream, so ridges emerge as *what is left between them*.
Droplet erosion cuts local gullies; this builds topography. A mountain is not an object you add — it
is the residue after a river network incises high ground, which is why authoring the summit directly
kept producing a children's-drawing triangle.

Verified against the slope–area law, not by eye: at steady state `S ∝ A^(−m/n)`, a straight line of
slope −m on a log–log plot of channel cells.

| m | fitted exponent | error |
|---|---|---|
| 0.4 | −0.387 | 0.013 |
| 0.5 | −0.490 | 0.010 |
| 0.6 | −0.591 | 0.009 |

all inside the reference's 0.1 tolerance, and stable across 100 / 200 / 400 / 800 iterations
(−0.468, −0.505, −0.490, −0.494) so it is converged rather than passing at one lucky count.

**Getting that oracle to work exposed a harness bug, not a solver bug.** Driven from structured fBm
with unbalanced uplift, the fitted exponent wandered between −0.28 and +0.02 and r² collapsed to 0 —
because that regime never reaches steady state. Reproducing the reference's own conditions (small
uniform noise so the network self-organises, `U·dt = K·dt`) it lands on −m immediately. Working code
came close to being "fixed" on the strength of a broken measurement.

**Hillslope diffusion is the other half of the equation.** The full detachment-limited form is
`dh/dt = U − K·A^m·S^n + D·∇²h`. Stream power sharpens interfluves without limit — run it alone from a
smooth uplift field and you get a field of razor blades. Diffusion relaxes them, giving hillslopes a
length and valleys a width. It runs *inside* the loop; one relaxation afterwards cannot undo ridges
that sharpened for 200 iterations. Measured, ridge sharpness falls **0.048 → 0.032 → 0.024 → 0.016**
across the Hillslope range while relief stays flat — relaxing ridges and flattening a landscape are
different things. (`reference-impl` has `hillslope_diffuse` but never couples it to stream power,
which is a gap there too.)

**Terrain built entirely by uplift and incision.** Wire a field into the **Uplift** input and the
rivers carve it: feed in a smooth featureless blob (texture 0.0006) and the result carries texture
0.0235 — **39× more structure than went in**, all of it residue between channels. No summit is
authored anywhere. This is the workflow the node exists for, and the answer to why authoring the
summit directly kept producing a children's drawing.

**D/K sets drainage density.** Past a point, diffusion does not blur the channel network — it erases
it:

| Hillslope (D·dt at K·dt = 2) | max drainage area | fitted exponent | r² |
|---|---|---|---|
| 0 | 3969 | −0.490 | 0.62 |
| 0.01 | 2758 | −0.521 | 0.69 |
| 0.04 | 973 | −0.531 | 0.18 |
| 0.08 | 707 | −0.352 | 0.06 |

That was nearly misread as "diffusion contaminates the fit". Raising the area threshold to escape the
contamination made the exponent *worse* (−0.35 → −0.61 → −1.11), and above A = 1000 there were **zero**
channel cells — because there was no fluvial domain left to fit. Higher D means fewer, longer
hillslopes and a sparser network, which is the textbook D/K competition rather than a defect.

**Uplift 0 will erode your terrain away, and that is correct.** Rivers reduce a landmass that has
stopped rising. Measured on a Mountain, peak height goes **0.687 → 0.530 → 0.196 → 0.000** as incision
rises with uplift at 0. The shipped defaults sit well clear of that (they keep 77% of peak relief while
still measurably carving), and the node says so in its panel rather than letting you discover it.

### Building a mountain range from placed massifs

The reference implementation prescribes the workflow in `landforms.mountain`'s own docstring — *"place
it, combine several (`np.maximum` / `ops_filters.smax`), then run a real hydraulic + thermal pass"* — so
the studio has a node for each step.

1. **Mountain** ×N, in **Mountain** landform mode. The primary mass is a variable-height, asymmetric
   crest ribbon with connected cellular shoulders and broad, unequal face basins — not a radial cone
   with grooves stamped into it. **Shape family** selects one of four clean-room uplift generators:
   **Dominant peak**, **Compound peaks** (default), **Ridgeline**, or **Broad dome**. Independently,
   **Mountain type** selects **Basic**, **Eroded**, **Old**, **Alpine**, or **Strata**; these change the
   core profile, cellular response, basin expression, and process history, not just viewport shading.
   Placement is built in (Position / Reach / Trend), so the feature is evaluated directly in world
   space rather than moved as a finished raster. Typical warmed default build: about 250–300 ms at
   192².
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

#### Mountain: public Gaea contract, clean-room implementation

The public Gaea references clarify the abstraction. The current
[Mountain](https://docs.gaea.app/reference/nodes/terrain/mountain) is described as a modulated Voronoi
pattern plus distortions and exposes five styles: Basic, Eroded, Old, Alpine, and Strata. The older
[Mountain reference](https://docs.quadspinner.com/Reference/GeoPrimitives/Mountain.html) explicitly
says its Type control selected “four different generative algorithms,” but does not publish those
algorithms. Gaea's older [geo-variant Voronoi](https://docs.quadspinner.com/Reference/Primitives/Voronoi.html)
does publish several mountain-oriented cellular forms. The studio therefore implements the observable
contract without claiming proprietary internals: four genuinely different cellular uplift families,
followed by five genuinely different geomorphic types.

The topology gate uses **topographic prominence**: flood the terrain top-down, and when two basins
merge, the lower summit's prominence is its height above that saddle. Unlike the previous
one-summit-only gate, the expected result depends on the selected shape family.

| | summits >10% relief | 2nd/1st prominence | texture vs a cone |
|---|---|---|---|
| ideal cone | 1 | 0 | 1× |
| **Mountain — Dominant peak** | **1** | **0.066** | — |
| **Mountain — Compound peaks (default)** | **3** | **0.138** | **96.3×** |
| **Mountain range** | 12 | 0.353 | — |
| ridged fBm | 122 | 0.553 | — |

Note what the first two columns cannot tell you: a smooth cone scores perfectly on both. Texture is the
column that catches it, which is why it is measured now — and why the renders get looked at.

The four Mountain shape families are deliberately different landforms:

- **Dominant peak** favours one strong cellular uplift and a short hero summit.
- **Compound peaks** joins several high uplift cells through real saddles; it is the natural default.
- **Ridgeline** lengthens the connected crest and favours cellular boundaries.
- **Broad dome** favours cell interiors, wider faces, and a broader summit shoulder.

The five Mountain types then alter that chosen mass: **Basic** is restrained, **Eroded** deepens
cellular faces and runs hydraulic weathering, **Old** broadens and relaxes the profile while retaining
residual gullies, **Alpine** narrows and sharpens the rock divisions, and **Strata** applies a layered
elevation response. With weathering disabled, the least pairwise normalized field difference is
**0.0675** between shape families and **0.0245** between Mountain types, proving both settings change
generator geometry.

**A good texture stack cannot rescue the wrong mass.** The rejected version was a convex radial ramp
with summit-to-rim seams — the tipi tent failure. The current primary envelope is instead a
variable-height crest ribbon with unequal widths on its two faces. Connected cellular volumes add
shoulders and buttresses; broad basin heads begin at different crest positions; only then do meso
fracture and erosion operate. The editable skirt still supplies distinct upper-crag, shoulder, face,
talus, and pediment slope bands, but it no longer defines the whole landform as a solid of revolution.

  **Shape variation — so the mask does not stamp every mountain into one shape.** The seed alters
  reach, aspect, trend, and the low-order outline while leaving Position exact. The default Compound
  family is already elongated at zero variation; increasing the control broadens the distribution of
  areas, orientations, and aspect ratios across seeds.

  | Shape variation | elongation range | area spread |
  |---|---|---|
  | 0 | 1.90 – 1.96 | 0.011 |
  | 0.55 (default) | 1.44 – 2.28 | 0.105 |
  | 1.0 | 1.14 – **2.45** | 0.181 |

  **Character — macro structure, not a noisier cone.** Character expands the uplift cluster, warps
  level sets, and changes the balance between the crest ribbon, shoulders, and cellular crags. The
  authored Position remains the dominant high area.

  Raw field correlation was discarded as a misleading metric because radial bulk dominates it even
  when the shoulders differ strongly. The replacement measures the mid-elevation contour and the
  normalised L1 difference against a 90° rotation. A cone scores **0.020** difference. With variation
  and baked weathering disabled to isolate this control, Character 0 / 0.3 / default 0.72 / 0.9 score
  **0.419 / 0.540 / 0.612 / 0.631**: the control changes macro shape, not just high-frequency texture.

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
  an analytic `(1−r)^1.4` preset to a max error of 0.011, with exact endpoints.

  The curve genuinely drives the landform — mean apron height at 70% of the radius, by preset:
  Plateau **0.0486**, Cone **0.0295**, Apron **0.0168**, Sweeping **0.0064**, all distinct and ordered as
  the shapes imply. A hand-drawn curve matching no exponent works the same. Dragging a control point
  in the live widget changes the terrain (mean |Δ| 0.0026 in the current interaction probe).

  The footprint cut is now **binary at the envelope's own support** rather than a linear collar over
  the last 6% of the radius. The collar was mine, added to kill erosion speckle, and it re-introduced
  exactly the hard seam it was meant to hide.

  **Drainage is topology, cellular structure is rock mass.** Mountain authors only a few broad,
  unequal basin heads beginning on different shoulders. A coarse distorted-cellular band divides the
  primary faces and a finer band fractures them; the hydraulic pass supplies the smaller connected
  flow hierarchy. **Drainage detail** changes basin and fracture scale; **Reduce details** suppresses
  the cellular/micro bands independently.

- **Mountain range** — `Massif crests` unioned into a small range, which is what `landforms.mountain` builds by
  design (its docstring: *"n_ridges crest lines unioned into a small range"*). Right for a shoulder or a
  plateau edge; wrong as the thing you place three of, because you would be unioning three small ranges.

**The controls own independent axes.** The current quality gate verifies Height is linear (0.5 gives
exactly half the pre-weathering peak), High Bulk has over 25% more mass than Low, Reduce Details cuts
Alpine fine energy by at least 18%, and Weathering produces a materially different surface. Drainage
  detail rises monotonically from 0.6× through 3.4×, spanning **2.9×** in scale-free fine energy instead
of reversing or saturating.

Two of the measurements used to check this were themselves broken and had to be thrown out: an angular
crest count saturated at ~130 regardless of input at 192², and requiring *exactly* one summit is what
let the smooth pyramid through. The invariants that survive are scale-free — fine-detail energy per
unit height, family-appropriate summit topology, few summits, pairwise generator differences, and
render review.

The primitive also stays strictly inside its own footprint (total height outside it is exactly **0**).
At 192² versus 384², including baked weathering, the 48² macro comparison has RMS **0.0062** and max
error **0.0375** (the raw fine-detail comparison is 0.0079 RMS); the landform therefore survives
preview/build resolution changes while resolution-appropriate fracture detail is allowed to differ.

**Every placed node gets its own random seed, and you can still change it.** Node parameters used to
be initialised straight from the type defaults, so three placed Mountains were three *identical*
mountains and the whole place-and-combine workflow was pointless. A node carrying a `seed` now gets a
fresh random one in **[0, 1 000 000]**, on placement and on duplicate alike — a duplicate is a new
feature, not a clone, while every other parameter is copied.

The trade that makes, stated plainly: a graph is no longer reproducible from its construction order,
because reloading re-rolls every seed. **Reproducibility comes from the seed values instead**, which is
why the control is a typable number field with a **↻** reroll button rather than a slider — a million
values through a few hundred pixels cannot address a specific one, and the earlier requirement was that
you be able to *change* the seed, not just perturb it.

Verified: three fresh Mountains get three distinct in-range seeds, a second batch rolls different ones
again, typing `4242` takes and reroll moves off it, and — the control that gives the rest meaning — two
nodes forced to the same seed produce **bit-for-bit identical** terrain while two different-seeded ones
differ by **33%** of total height inside the footprint.

Verified in `_verify_range.js`. Three Mountains placed at X = 0.26 / 0.50 / 0.74 land at measured
centroids **0.281 / 0.505 / 0.722**, each with relief ≈ 0.84–1.08. Unioning with Smooth Max instead of a
hard Max cuts the curvature crease along the seam (135 seam cells) by **74.9%**.

The finding worth stating plainly: **three unioned massifs are not yet a range.** Thresholded at 35% of
peak height, the union is **4 disconnected components**. After a thermal pass it collapses to **1**
component of 20,833 cells. Erosion is what knits separate massifs into one connected landform, which is
also why the primitive is documented as *"ready for further erosion"* rather than finished.

#### Canyon: drainage competition and landscape evolution

Gaea publicly describes [Canyon](https://docs.gaea.app/reference/nodes/terrain/canyon.html) as a fast,
drainage-based river-canyon landscape with **Classic, Eroded, Eroded 2, Strata, and Both** styles.
Its implementation is proprietary, so Terrain Studio follows that public control contract with a
clean-room, research-grounded landform rather than claiming to reproduce hidden internals. The landform
claim is the terrain-architect **Grand Canyon-type plateau canyon** composition: an antecedent river
incises a broad uplifted plateau made from alternating resistant and weak beds. **Structural warp**
changes the weak regional substrate, while **Detail warp** changes sub-catchment erodibility.

The implementation stages now have explicit provenance:

- A shallow regional sag, tectonic uplift, non-uniform lithologic weakness, and tiny initial relief
  establish *potential* drainage. They are initial conditions, not rendered channel curves.
- An outlet-seeded Priority-Flood gives every cell a depression-safe route, followed by
  distance-corrected **D8** (O’Callaghan & Mark, 1984) and contributing-area accumulation.
- Channel heads activate from an area–slope condition rather than a branch count, following
  [Montgomery & Dietrich's field relation](https://www.nature.com/articles/336232a0) (1988):
  the source area needed for a channel decreases as the local valley gradient increases.
- Repeated implicit `n = 1` stream-power steps magnify the drainage winners using
  [Braun & Willett's O(N) solver](https://www.sciencedirect.com/science/article/pii/S0169555X12004618)
  (2013). External contributing area enters at one boundary and follows the current receiver graph
  to the outlet, giving one through-going antecedent trunk without specifying an interior path.
- Base level **falls on a schedule** rather than starting as a pre-dug notch, so canyon depth is
  transmitted upstream by the incision solve instead of being present before anything erodes. `K` is
  therefore a knickpoint *celerity*: in the implicit `n = 1` solve a cell moves `C/(1+C)` of the way to
  its receiver per step, so an upstream-travelling signal decays by that factor **per cell**, and a
  value too small for the grid leaves the interior untouched no matter how long it runs.
- Slope-limited **thermal erosion** ([Musgrave, Kolb & Mace, 1989](https://dl.acm.org/doi/10.1145/74334.74337))
  replaces linear hillslope diffusion — it does not supplement it. Linear `D·∇²h` has no threshold in
  it and so cannot express a repose angle; it drove every hillslope toward one equilibrium gradient,
  which is why the surface previously showed a single ~14.5° slope mode in *all five* styles.
  This competition between convergent incision and hillslope transport follows the
  mechanism in [Perron, Kirchner & Dietrich](https://www.nature.com/articles/nature08174) (2009),
  where initially irregular valleys compete for drainage area and develop an emergent spacing.
- **One bed table sets both erodibility and repose angle.** That pairing is load-bearing: bedded `K`
  with a uniform talus angle lets thermal shave off the cliffs differential erosion just built, while
  bedded talus with uniform `K` puts cliffs where nothing pins them. Together they produce cliff bands
  standing over debris slopes. Talus delivered onto a channel is carried away at the river's capacity,
  because otherwise a deep canyon buries itself under its own walls faster than it can cut.
- The rock column is a non-uniform hard/soft bed table using the layered terrain representation
  of **Beneš & Forsbach (2001)**. Bed thickness and erodibility vary; equal contour bands and the
  cylindrical ellipse “remnants” have been removed.
- A channel head continues upslope as a decaying colluvial hollow along its strongest real donor.
  It therefore tapers into the divide instead of ending in the rounded capsule left by segment SDFs.
  Natural confluences emerge from the shared receiver tree; no branch spline, ellipse, cylinder, or
  distance-to-line trench is constructed anywhere in the production path.
- The area–slope test decides where a channel *begins*, not whether it survives each cell downstream,
  so channel **membership** is propagated along the receiver graph: once initiated, a channel stays a
  channel to base level. Its **strength is derived locally** from that reach's own contributing area
  rather than inherited from its head. This distinction is load-bearing. Copying the head's amplitude
  downstream saturates every reach to the same size, erases the discharge hierarchy, and flattens the
  central amphitheatre until it is no wider than the canyon ends. Downstream hydraulic geometry sizes a
  reach by its own discharge, and a carried reach — one crossing a low-gradient, more depositional
  stretch — stays subordinate to a reach that crosses the initiation threshold on its own.

The result is fractal-like over its resolved scale range, but fractal noise is not the generator.
Rainfall-fed drainage trees exhibit fractal scaling and are commonly measured with Horton–Strahler
hierarchy ([Stepinski et al., 2004](https://agupubs.onlinelibrary.wiley.com/doi/full/10.1029/2003JE002098)).
More importantly, [Perron et al. (2012)](https://www.nature.com/articles/nature11672) found that the
fine branching pattern is an organized signature of coupled valley-widening and channel-incision
instabilities—not random topology. Terrain Studio therefore verifies stream order and branching on
the evolved receiver tree; noise only supplies small substrate/initial-condition heterogeneity that
the environmental process may amplify or erase.

**Classic** and **Tributary density = 0** remain the defaults and favor one principal antecedent canyon.
Values 1–8 progressively lower the area–slope initiation threshold; they do not request that many
branches. This is also why two seeds need not produce the same count: uplift, slope, weak beds and
catchment capture decide which hollows survive.

Style selects a geomorphic regime rather than a surface preset. **Classic** balances scarps, benches,
side valleys, hard/soft scarps, and talus. **Eroded** broadens its headwater basins, increases wall
retreat, and builds a rounder colluvial toe. **Eroded 2** carries the densest, deepest drainage
hierarchy. **Strata** most strongly preserves the non-uniform hard/soft bed response.
**Both** keeps that lithologic response while applying stronger
drainage and retreat. These are formation modes inside the primitive—not aliases for a downstream
erosion node and not five noise amplitudes over one shared trench.

For the demonstrated production graph, choose **File → New Canyon landscape** (also available from the
compact menu and command palette). It creates `Canyon → Erosion 2 → HydroFix → Output`: Erosion 2 applies
broad hydraulic ravines before a nested fine pass, exposes separate Duration, Downcutting, Erosion Scale,
sediment-discharge, and Shape controls, while HydroFix uses priority-flood routing and low-amplitude
accumulation downcutting to reconnect drainage without replacing the landform. This remains clean-room:
Gaea's [Erosion 2](https://docs.gaea.app/reference/nodes/simulate/erosion2.html) and
[HydroFix](https://docs.gaea.app/reference/nodes/simulate/hydrofix.html) documentation defines the public
roles and controls, not the proprietary implementation.

The primitive remains a starting landscape, consistent with Gaea's description of
[geological primitives](https://docs.gaea.app/using/using-gaea/crafting-the-surface/noises-primitives-and-landscapes.html):
put Erosion 2 downstream when the canyon needs a fully evolved sediment budget. The primitive performs
global topology on a bounded, cached process grid (192² for a 512² viewport; 256² for 2K/4K builds),
then resamples the evolved surface. The rendered height is an **affine view** of that solve — compose
subtracts a gain from a datum and does nothing else — so Depth is a vertical gain that never re-runs the
process, and no compose-time operator can invent structure the solve did not produce. Compose previously
rebuilt the output from the *pre-erosion* surface minus a triple-blurred incision mask, plus a bed-snapping
remap that was a terrace filter applied to a finished heightfield; both are gone.
It is a dimensionless, art-directable landscape-evolution model, not a calibrated claim about years or
rock units.

`_verify_canyon_evolution.js` verifies the geomorphology rather than a screenshot. Every active channel
cell in the density-4 reference reaches the single outlet; the antecedent trunk crosses the tile at
**206** cells; the network reaches **Strahler order 7**; density 7 produces more active drainage and
heads than density 0; the median immediate junction angle is **90°** on the D8 grid but well under
**0.3%** are T-like (>150°); and the median headward continuation tapers to a small fraction of
channel-head incision. On the verification machine the first 512² build takes about **1.6 s**, while a
depth-only edit is a **0.6 ms** affine remap of the cached solve.

`_verify_canyon_relief.js` guards the property the primitive nearly lost: **depth must be cut by the
solve, not stamped on afterwards.** Before it existed, the evolution loop cut 99% of the map by under
**21 m** into a 185 m plateau, a hand-set outlet notch supplied **46%** of the entire landscape range
before anything eroded, and compose invented the remaining **94%** of the advertised depth with a 5.86×
vertical stretch — correlation between the evolved surface and what reached the screen was **0.478**.
Every downstream mechanism was inert for the same reason: with bed thicknesses of 32–87 m against a
21 m cut, no bed was ever cut through, so lithology had nothing to express on. It now measures p99
fluvial cut **1,760 m**, median cross-section relief **1,741 m**, **6 of 7** beds exposed across more
than 5% of the map, plateau preserved at **66%**, and `composeCorr` **1.000**. It also audits the
weathering pass's mass budget — source must equal deposit plus what leaves the tile — because the
published form of that recipe *adds* material, and a silent sink is indistinguishable from a bug.

`_verify_canyon_gridscale.js` holds the landform invariant under a resolution change — the skill calls
this the cheapest possible detector of the most pervasive defect in terrain graphs, which is a length or
an area written in *cells* rather than in metres. Contributing area accumulates in cells, so a bare
cell-count channel threshold means a different physical area at every resolution and simply raising the
process grid would have channelised the whole map; the incision coefficient drifts as `(n−1)^(2m−1)` for
the same reason, and the colluvial hollow was a fixed number of cells rather than a length. All three are
now expressed relative to a reference grid. Solving the same world at 160², 192² and 256² gives a
coarse-landform correlation of **0.93** and **0.94**, relief identical to **0%**, and drainage density —
reported in **1/m**, never in cells, because a count carries the grid inside it — stable within **12.7%**.

The process grid stays at 192² (256² for 2K/4K) for **cost, not correctness**. 224² measured 2.5 s against
a 3 s budget, and since every parameter except Depth triggers a rebuild that is felt on every slider drag.
Because the parameters are now non-dimensional, raising it is a one-line change whenever the budget allows,
and the oracle above is what makes that safe. Note also what this pass deliberately does **not** buy:
facets, benches and talus aprons at 20–120 m, yes — but not rills. A rill is a *fluvial* feature, and
producing one at 9.8 m would require flow routing and stream power at output resolution, which is the
second global erosion pass the doctrine forbids. Raising the process grid is the legitimate route there.

`_verify_canyon_slopes.js` is the cliff-and-talus oracle, and its design matters more than its numbers.
A bimodal slope histogram is only meaningful if it is traceable to two entries in the *material* table;
one produced by a height threshold looks identical in a screenshot and is a known defect. So the
decisive assertion is not "is it bimodal" but **"do the modes move when the bed table moves"** — they
shift **49°**. The distribution now peaks at **40.5°** (debris) and **75.5°** (rock face) with a
prominence ratio of **0.74**, where linear diffusion gave a single mode at 13.5–14.5° in all five
styles at a ratio of 0.013. The debris mode is further required to land inside a bracket the bed table
itself predicts, so the test recalibrates with the material instead of against a fixed band.

Two of that file's channel-continuity oracles deserve comment, because one of them was quietly useless.
The original `connectivity` metric walks the receiver graph from each active cell to the outlet — but
the receiver graph reaches base level from *every* cell by construction, so the metric reported 100%
even with channel propagation completely disabled. It could not fail, which is why disconnected
channels shipped. It is retained as a routing sanity check and is no longer the continuity gate.
**`activeChainFraction`** is: it requires that every cell on an initiated channel's path to the outlet
is *itself* still a channel. It reads **1.0**, and drops to **0.0** when the propagation pass is
disabled, so it is a real oracle rather than a tautology. **`gapMaxAreaFrac`** complements it on the
rendered field, reporting the largest share of outlet discharge carried by any reach that goes visually
faint between two visible reaches: **0.0008** at density 4, so effectively nothing above a fraction of a
percent of trunk discharge ever breaks up. The remaining faint reaches are the intended headward taper.

`depthSpread` is reported but deliberately **not** asserted. It was added to guard against channels
saturating to a uniform depth, and measurement showed it moves the *wrong* way under exactly that
regression (6.7 healthy vs 12.7 saturated), because saturation lifts the high percentile while faint
heads hold the low one. The discriminating oracle for that failure is the central-amphitheatre width
ratio in `_verify_canyon_classic.js` (**1.53** healthy vs **1.06** saturated). A statistic that cannot
distinguish the defect it names is worse than no statistic, so it carries a comment saying as much.

`_verify_canyon.js` covers independent controls, all five style responses, deterministic output and
grouped UI; `_verify_canyon_process.js` covers the recommended `Canyon → Erosion 2 → HydroFix`
production chain.

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
SatMap Studio) and applies **Reverse**, **Range** (use just a slice), **Bias**, Roughness, HSL grading,
and **Enhance** (None / Autolevel / Equalize), matching Gaea's documented public SatMap controls.

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
  `… → SatMap(base) → SatMap(rock) → Output` makes the second a normal masked overlay).
  **Color Erosion** and **Weathering** then transform
  that upstream colour as independent graph nodes; height-only nodes pass colour through unchanged. Each
  colour node can be masked and composited, and **Color Blend** merges any two colour branches—not only
  SatMaps. Wire any SatMap / Color Erosion / Weathering branch into **A** or **B**, then optionally feed a
  grayscale field into **Mask**. Color Blend exposes Gaea-style methods: **Blend, Add, Screen, Subtract,
  Difference, Multiply, Divide, Divide 2, Max, Min, Hypotenuse, Overlay, and Power**. The result is
  resolved per vertex into terrain albedo.
- **SatMap is a surface lookup, not hidden strata.** The layered sediment appearance comes from an explicit
  graph. Start with one or more SatMaps driven or masked by height, slope, curvature, flow, wear, and
  deposits; pass that colour through **Color Erosion** to transport upstream pigment downhill; then use
  **Weathering** to bleach exposed relief and darken protected recesses. A typical chain is
  `height → SatMap → Color Erosion → Weathering → Output`, with `Deposits → Color Erosion.Sediment`.
  This creates material/sediment-like surface layers without pretending that the 1-D SatMap itself is a
  subsurface geology simulation.
- **Every colour result remains blendable.** Color Erosion retains its transport **Blend** control and
  Weathering has physical **Amount** plus **Opacity** and **Blend mode**. SatMap, Color Erosion, and
  Weathering all accept masks; any output can feed **Color Blend**. **Color Mixer** is the layer-oriented
  convenience node: add, remove, and reorder from 2 up to 15 color inputs, with opacity and blend method
  per layer. Layer 1 is the base; a standalone masked SatMap connected to a higher layer carries that
  mask as biome alpha. Black remains bit-identical to the layers below, white applies the biome, and
  the per-layer **Edge** control adds a world-space transition band without blending biome interiors.
- **One SatMap, one gradient; biomes stay explicit.** A SatMap can receive another SatMap through **In**
  when the second node is a masked overlay. For a true biome split, branch the height into one SatMap per
  biome, derive or draw a biome mask, and connect the masked branches to Color Mixer. The same result can
  be expressed explicitly in **Color Blend**, whose Mask, Opacity, and full blend-method set make the
  transition visible and configurable instead of hiding a second gradient inside one SatMap node.
- **One authored region, reused everywhere.** For art-directed worlds such as a hot desert beside an
  arctic province, create one Draw Mask per region and fan its output into both the region's SatMap Mask
  and Temperature Modify Mask—and into Wind Modify when that region has a distinct circulation regime.
  Chain those regional edits over the one global Temperature and Wind fields, then feed the final fields
  into Snow and Water. The material boundary and physical freeze/melt/wind boundaries therefore use the
  same footprint; soften the drawn mask or Color Mixer Edge to form an ecotone rather than a hard line.
- **Visual SatMap library lives on the node.** The SatMap Gradient property opens a scrollable palette
  library rendered directly from the LUT stops that feed that node. The viewport has no global SatMap
  selector. Newly authored LUTs appear immediately after **Apply**.

With no SatMap node in the graph, the viewport uses a neutral inspection material; adding a SatMap node is
the only way to author a palette.
Each SatMap node also has **None / Low / Medium / High / Ultra Roughness**. It coherently perturbs the
lookup coordinate, matching Gaea's documented “scatter the pixels of the colour map” behavior instead of
adding directional light or indiscriminate RGB noise to the exported albedo.

## Controls

- The stacked vertical layout—rendering above the graph—is the first-run default. Use **⬌/⬍** in the
  top bar to switch between stacked and side layouts; an explicit choice persists. In the stacked
  layout, drag the horizontal divider to resize the graph. Its preferred graph height is remembered
  in pixels, so a larger window gives the extra room to the terrain view; the graph yields only when
  needed to preserve a usable terrain viewport.
- Use **⛶** in the rendering or <kbd>Shift</kbd>+<kbd>F</kbd> for rendering fullscreen.
- **Output / Selected** moves the viewport display flag between the final Output and the selected
  intermediate node. **Plan / Hero** switches between top-down inspection and the perspective camera.
- The rendering stays visually quiet: a compact right-side **icon rail** owns preview, camera,
  display, lighting, global water rendering, help, and fullscreen. Flyouts are mutually exclusive;
  the persistent gesture banner and large look-development panel no longer cover the terrain.
- The application menubar owns **File / Edit / View / Help**. **File → New terrain**
  (<kbd>Ctrl/Cmd</kbd>+<kbd>N</kbd>) starts a clean graph containing only Output; **New from default
  setup** restores the production climate/water/snow starter. Starting either document asks before
  discarding the current graph and clears the old document's undo history. Import/export also live
  under File instead of consuming permanent toolbar space.
- Below 940 px the menubar becomes one hamburger menu with the same command set and expandable
  sections. Desktop menus, the hamburger, keyboard shortcuts, toolbar controls, and command search
  share one command dispatcher, so adding a command does not create divergent implementations.
- The top bar keeps only frequent work visible: **Auto**, **Build**, history, build profile, and layout.
  The **Build profile** popover owns resolution/quality/GPU/Res Lock, while the searchable
  **Commands** menu (<kbd>Ctrl/Cmd</kbd>+<kbd>K</kbd>) holds graph locators, organization, toolbox,
  fullscreen, theme, and other occasional actions. This keeps the toolbar extensible at narrow widths.
- Choose **Realistic / Clay / Albedo / Slope / Normals** in the Display flyout. The Lighting flyout
  controls sun azimuth, elevation, exposure, and atmospheric haze.
- The **Water** node owns fluid extent and shoreline authoring. **Shore smoothing** filters only
  the signed-depth coverage used for rendering, preserving terrain and hydrology data; **Shore foam**
  controls the transition band. The viewport's global **Water Surface** flyout chooses **Cross ripples**,
  **Wind waves**, **Interference rings**, or **None**, then controls strength, scale, speed, and refraction
  for every Water node. Hydrology exposes Lakes, Minimum lake depth, River network, and River depth;
  Sea level hides those controls because it is an independent flat-water mode.
- Properties use mode tabs and show only settings that affect the active algorithm. This applies to
  Water, Hydraulic and Thermal erosion, Mountain/Mountain range, Gradient, Transform, and Sculpt;
  hidden values are preserved when switching modes.
- Select **Draw Mask** and choose **Draw on terrain…** to paint a reusable mask over its Reference
  input. For roads, connect terrain to Draw Mask.Reference and Sculpt.In, then Draw Mask to
  Sculpt.Mask; Flatten or Smooth produces the road bed without destructively editing the source.
- Undo/redo with the toolbar buttons or <kbd>Ctrl/Cmd</kbd>+<kbd>Z</kbd> /
  <kbd>Ctrl/Cmd</kbd>+<kbd>Shift</kbd>+<kbd>Z</kbd>.
- Open **＋ Nodes** inside the graph view for the searchable, category-grouped node toolbox. Clicking
  a toolbox item places it in the visible graph area and keeps the toolbox open for building a chain.
  **Double-click** empty canvas still opens the compact add-node menu at that exact position. Dragging
  a connection from an output and releasing it on empty canvas opens the same search with only
  connectable node types; choosing one creates it at the release point and links it in one undoable edit.
- **Right-click the graph** for **Organize all**, **Frame all**, Add-at-cursor, and the node toolbox.
  Right-click a node to organize its **connected branch**, only its **upstream** inputs, or only its
  **downstream** dependants; the same menu can frame the branch, preview, duplicate, or delete it.
  Organization uses a deterministic layered DAG layout with crossing-reduction passes, preserves
  disconnected graph islands, is undoable, and never evaluates or dirties terrain data.
- Drag a node's **right port** into another node's **left port** to wire them (cycles are rejected).
- Connections are first-class selections: click near a curve using its generous hit area to inspect
  its source, destination port, live field range, and state. A selected link gets a high-contrast
  stroke and a visible **×** handle; remove it with that handle, <kbd>Del</kbd>, the Properties panel,
  or its right-click menu. Right-clicking a connected input port opens the same menu, which keeps
  even very short links easy to reach. Connections can also be **Muted** without deleting them. Mask connections
  additionally report coverage and restate the `0 = bypass, 1 = apply` contract. Blend behavior stays
  explicit in Blend / Color Blend / Color Mixer nodes rather than becoming hidden edge processing.
- Click a node to edit its parameters on the right; **Duplicate** / **Delete**, press
  <kbd>Ctrl/Cmd</kbd>+<kbd>D</kbd>, or press <kbd>Del</kbd>.
  Deleting a mid-chain node **auto-bridges** its neighbours (its input source reconnects to its outputs)
  when the input is unambiguous, so the pipeline stays connected.
- Pan with **middle-drag** / space-drag / empty-drag; **wheel** to zoom the graph.
- Hover any numeric slider and use the **wheel** for one-step adjustment; hold <kbd>Shift</kbd> for
  ten steps. This follows the normal edit path, so preview invalidation and undo behave exactly like
  dragging the slider.
- In the 3D view: **drag** to orbit, <kbd>Shift</kbd>-drag or right-drag to pan, and **wheel**
  to cursor-focused deep zoom. The camera can dolly from a full-terrain view down to roughly
  `0.012` world units (about 30 m at the default 5 km extent); its near plane scales with distance
  so the inspected surface is not clipped. Press <kbd>F</kbd> to restore the framed Hero camera.
- **Auto** recomputes on every edit; turn it off and use **Build** for heavy graphs.
  Auto uses frame-coalesced, domain-aware invalidation: a burst of slider events evaluates the newest
  value once per display frame. SatMap, Color Erosion, and Weathering parameter edits preserve the
  downstream heightfield and update only terrain colour; Water updates only its fluid-surface buffers.
  Geometry, normals, height textures, and hydrology rebuild only when a height-producing node changes.

## Design — learning from Gaea, World Machine and Houdini

The brief was to learn from the strengths *and* weaknesses of the three baselines:

- **Adopted — Gaea:** a graph → viewport → properties loop, per-node thumbnails, a lockable
  intermediate preview, 2D/3D inspection, and beautiful, sensible defaults.
- **Adopted — World Machine:** a clean single-window device graph, live property preview, standard
  undo/redo, and an explicit Output node.
- **Adopted — Houdini:** movable display state for inspecting any intermediate result, per-node
  performance data, flexible pane layouts, and real procedural depth (grounded erosion, masks and
  composable warps) rather than a fixed pipeline.
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
represents, in metres. Defaults are **5000 m across × 2600 m relief** above a **0 m ASL base elevation**,
a **vertical ratio of 0.52** (`relief ÷ scale`), which is also the viewport's vertical exaggeration.
Cell size is `scale ÷ RES` (9.8 m at the default 512², 4.9 m at 1024²). It also owns the
**fallback sea-level temperature/lapse rate**, **climate sun elevation**, **latitude**, **map north**,
and the prevailing **wind-from direction and speed**.
The fallback is used only by unconnected Snow/Water consumers. The panel reports the derived 0 °C freezing altitude.
North is authored clockwise from the heightfield's top edge; latitude decides which side points toward
the equator. The viewport compass projects both directions through the orbit camera. Beside it, the
wind indicator projects the local flow arrow through the same camera and reports speed plus the
meteorological **from** bearing; it samples a previewed/connected Wind field at the terrain under the
view focus, or uses a dashed Terrain Definition fallback when no physical field is active. The temperature
chip reports air temperature at that focus; click it to toggle °C / °F.

### Terrain-aware wind

Prevailing wind belongs to Terrain Definition rather than to a biome: air crosses material and
climate borders, so one continuous regional circulation is the source of truth. The **Wind** node
takes Height and emits a physical horizontal vector field (`u`, `v`, and speed in m/s, capped at 80 —
the cap applies to the *vector*, not just the display scalar, or consumers deriving unit directions
got "unit" vectors up to 1.875 long and snow's saltation reach silently doubled; cross-model
review). It accelerates flow up windward slopes and *onto* crests (the raw upwind-slope form left
the ridge line an exactly-unaccelerated notch — the windward face's lift is carried ~60 m onto the
crest, and the corpus's own pseudocode note was corrected upstream), detects terrain on the upwind
horizon to shelter lee cells, and turns wind toward concave valley axes. The bounded
Helmholtz–Hodge projection **reduces divergence ~4×** (measured 0.24 ratio; gate armed at 0.35):
its first form paired central div/grad with a compact Laplacian — a Nyquist-blind combination that
*converged* at ~2× while claiming mass consistency — and now runs an exact-adjoint stencil pair
(forward div, compact Laplacian, backward grad, whose composition *is* that Laplacian) with two
V-cycles. Honest label: a strong divergence reducer, not the reference-impl's spectral
machine-precision projection. This is a terrain-adjusted climate approximation, not CFD; the
shaping constants (tanh 2.5, the 3–15° shelter band, 0.75 max shelter — above 13's 0.2–0.5 range —
and the /30 m/s coupling saturation) are authored and flagged as such in the code.

Biomes may still author regional circulation. Chain **Wind Modify** nodes over the base field and
reuse each biome's Draw Mask in the Modify Mask input. The masked boundary rotates direction along
the shortest angular path and blends speed, so an ecotone remains continuous — and the node's
**Mass consistency** tab chooses the price: **Project** (default) re-projects after the override,
so a hard biome seam *lowers* divergence instead of raising it 39% (measured pre-fix, with the
diagnostics stamped inverted), at the cost of flow bleeding across the seam; **Preserve exactly**
holds the authored values to 1e-3 everywhere and knowingly keeps the seam divergence. Display →
**Wind** renders direction as hue and speed as brightness. Snow consumes the final vector field
directly, per cell (event duration from the p95 of field speed — a max let one gusty DEM cell
double the whole map's transport); with no Wind connection its legacy strength/direction controls
remain a backward-compatible fallback, and note the shipped default graph *does* wire Wind → Snow,
which changed the default terrain's snow (5 → 6 transport passes). The same physical field is
intended for future orographic precipitation, dune transport, fire spread, vegetation exposure,
and wave fetch rather than duplicating a direction knob in every consumer.

That is what makes slope **angles** physical, so — as in Gaea, where *"the only place the terrain scale
affects how your terrain is processed is when `Real Scale` is turned ON in the Erosion, Snow, or Thermal
nodes"* — the **Thermal erosion** node has a **Real Scale** switch. With it on, `Repose angle` is a true
angle: the per-cell drop becomes `tan(angle) · cellSize ÷ height`, which is *inherently* resolution
independent. Verified — a 35° repose stays exactly 35° at 128², 192², 256² and 512², with the per-cell
drop halving as the cells do.

### Snow, ice, and a shared freezing climate

The Snow node keeps bedrock unchanged and computes a separate `SnowField.depthM` in **world metres**:

1. **Placement:** settled snowfall is partitioned between rain and snow across a −3 °C to +2 °C
   transition. **Snowfall and degree-day melt use logarithmic sliders** with decade tick marks
   rendered under the track: their useful ranges span decades (a dusting is 5 cm, a heavy winter
   10 m), and on a linear 0–20 m track everything interesting lived in the first few pixels.
   Params always store the real value — only the track is warped, so serialisation, digests and the
   mouse-wheel step (which becomes multiplicative, as it should be on a log scale) are unaffected.
   Temperature comes from the physical field connected to Snow. Terrain Definition's
   clearly labelled fallback temperature/lapse values apply only when that input is absent or invalid.
   Relative Height is converted to altitude with both **Base elevation** (datum) and **Relief height**,
   so an artist can keep a cropped alpine tile above sea level by authoring its datum. Imported
   grayscale files do not infer ASL metadata automatically.
2. **Insolation + ablation:** an equator-side climate sun supplies incidence from slope/aspect, then
   a logarithmic horizon march casts shadows from both nearby and distant terrain. Two separable
   spatial blur passes turn binary visibility into soft penumbra/diffuse exposure. That spatial map
   adds solar warming before positive temperature removes depth with a configurable degree-day
   factor. Rotating map north, changing hemisphere, changing climate sun elevation, or sheltering a
   slope behind a ridge therefore changes which snow survives. **Height**, **Sun Shadow**, and
   **Temperature** are explicit Data map nodes, so these fields can be previewed, blended, masked, and
   reused elsewhere. The Temperature node owns editable numeric fields for **sea-level temperature**,
   **altitude lapse rate**, and **solar warming**; it combines those with Height and Sun Shadow to
   generate the base map. These are physical sliders with useful climate ranges: −50…+50 °C at
   sea level, −10…+15 °C/km lapse rate (including inversions), and 0…50 °C solar warming.
   Volcanic and geothermal extremes remain the responsibility of Temperature Modify rather than
   making ordinary climate controls too coarse.
3. **Temperature composition:** the map is not metadata stranded on its generator. Its physical
   Celsius contract follows only unit-preserving spatial operations (Blur, Warp, Transform), or
   Blend/Min/Max when both value inputs are Temperature fields. Tonal remaps, arithmetic combines,
   terraces, and arbitrary grayscale inputs deliberately lose/reject the contract instead of decoding
   ordinary 0–1 data as −100…1400 °C. **Temperature Modify** adds/removes degrees, approaches a target,
   or enforces a minimum/maximum through an optional Driver and Mask. A lava simulation can therefore heat its footprint, a shadow/microclimate branch
   can cool a valley, and every downstream consumer sees the edited result. The scalar transport
   encoding spans −100…1400 °C; physical Celsius values remain available to nodes and the viewport.
   **Temperature Select** converts Celsius intervals into ordinary 0–1 masks, allowing the same
   climate field to drive tundra, alpine, temperate, arid, and volcanic SatMap/Color Mixer biome
   branches.
4. **Stability:** simultaneous, distance-corrected transfers relax the combined
   `bedrock + snow depth` surface toward the snow repose angle. Only snow moves, and the transfer is
   volume-conserving, so steep faces unload into real deposits in couloirs and hollows. Transport
   acts only on the **mobile surplus above a holding depth** — the snow that adheres to the ground.
   This term is load-bearing, and its absence was a measured defect: the instability term contains
   the bedrock drop, which removing snow cannot reduce, so on ground steeper than repose the only
   equilibrium was ZERO depth, approached as a drain front — on a planar over-steep face transport
   is a conveyor, so only the topmost divergent cell net-drains, then its neighbour, one cell per
   iteration. Ridges stripped bare with a band exactly `iterations x cellSize` wide, symmetric on
   both flanks (a pattern real ridges never show), and snow cover moved ~15 pp with build quality
   alone. The holding depth is a **repose-anchored taper**, `H0 * min(1, tan(repose)/slope) *
   roughness`, where roughness comes from the terrain's own Laplacian (ledgy ground holds more,
   smooth slab sheds sooner). The corpus's 50–60° shed band was tried as the retention law first
   and rejected with numbers: in the viewport's autoleveled frame ~90% of this map exceeds 60°, so
   a band law left 23.7% of the most-convex decile below the render-opaque threshold — streaks
   where the reference look needs cover. The taper keeps the **repose slider physical** (it now
   drives both transport and retention), thins to translucent streaks by ~80°, and `Adhesion depth
   = 0` restores the strip-to-bare behaviour exactly. Measured, uniform cold: convex-decile bare
   **81.7% → 0.0%**, cover change between build qualities **15.6 pp → 0.0 pp**. Coverage is now
   convergent; drift depths above the hold keep maturing with iterations (the deferred
   deposition-bound work), which is why the claim is scoped to coverage.
5. **Wind:** Snow consumes the terrain-adjusted physical Wind field cell by cell (or its legacy
   local fallback when unconnected). It scours where the snow surface rises into the local vector —
   capped at a **0.5 m transportable surface layer per pass**, because
   saltation moves loose surface snow, not the consolidated pack — and each scoured parcel walks
   downwind to the **shadow zone**: the first cell where the surface stops rising into the wind,
   just past the local drift crest (walk capped at ~30 m regardless of grid). Both refinements were
   forced by face-integrated measurement, not taste: the reference port's fixed one-cell deposit,
   on terrain whose settled drifts decouple from bedrock, landed mass on still-windward ground and
   produced the exact inversion of the process (windward faces **gained** 9.3%); uncapped, single
   20 m drift shoulders donated 8 m per pass and swamped every face budget. Final measured
   signature, wind 0.7 vs calm: windward bedrock faces **−2.6%**, lee faces **+2.5%**, crest-line
   cornice 4.04 m lee vs 3.67 m brow. Event duration scales with strength (3–8 passes); wind
   deliberately ignores the holding depth — scour is precisely the process that strips adhered
   snow — and cornices are not re-settled afterwards, because a cornice IS an over-steepened lee
   deposit.
6. **Frame consistency:** the climate stack simulates the **same terrain the viewport draws** —
   and establishing which frame that actually is consumed one full review cycle, so it is recorded
   here. The viewport **autolevels** every displayed field to the full `[datum, datum + height]`
   span, and its climate readout and fallback temperature derive from that normalised height.
   `metricHeightField` matches it. During this work the opposite "physical" contract
   (`datum + field*height`, no renormalisation) was briefly shipped, on the strength of two
   independent investigations that both mis-read the renderer — they saw `hgt*height` consumers
   downstream of an already-normalised `hgt` and missed the normalisation at fill time. That
   change made the solver simulate a world 2.12× *flatter* than drawn: the exact inversion of the
   defect it claimed to fix, caught by a cross-model review before commit. The moral is encoded as
   `_verify_snow_physics.js` gate **G0**, which mirrors the viewport's composition independently
   rather than trusting anyone's reading of it — including this paragraph's.
7. **Rendering:** the depth field displaces geometry and normals. A composed solid-surface heightfield
   also includes frozen-water support plus snow-on-ice, while the underlying bedrock stream stays
   non-destructive for downstream geology/hydrology. The same field controls a
   high-albedo, rough dielectric material; deferred shadows, AO, water intersection, and terrain
   normals sample the displaced surface too. Two display-only treatments (the physics depth field is
   never modified): a **depth-weighted drape** relaxes the snow top toward a smoothed composite —
   snow is a blanket, and a surface deep enough to bury a feature cannot also express that feature,
   so thin dustings follow the ground exactly while deep pack rounds it off, with displacement
   bounded symmetrically at 0.6× the local depth because a blanket redistributes within its own
   thickness — unbounded lift filled couloirs with metres of displayed snow that had no mass behind
   it, and on a crag whose curvature exceeds the local pack the clamp binds, correctly: a 3 m
   blanket cannot bury a 7 m spike — and the coverage edge
   is modulated by the same surface noise the ground albedo uses, because a pure depth threshold
   draws the snowline as a clean painted rim where real melt edges are patchy at grain scale.

`_verify_snow_physics.js` gates all of this and was landed **red on the unmodified build**: convex-
decile bare 81.7% → **0.0%**; quality delta 15.6 → **0.0 pp**; synthetic 45°/75° roofs, crest stripped
to 0.000 → retained **0.96 m**, identical at 18 and 72 iterations, with flanks genuinely thinned (so
retention cannot be satisfied by a dead avalanche mechanism); wind absent → windward faces **−2.6%**
/ lee faces **+2.5%** vs a calm run, mass conserved to 5e-9. Three of its own metrics were discarded
during development for measuring the wrong thing — a face-mean diluted by the saltation conveyor, and
two crest-line selections biased by which surface detected the crest — each replaced by one that
fails on the defect it names. Deposition remains unbounded (max drift grows ~37% between 18 and 32
iterations; reported, not gated) — bounding it needs its own design.

The climate Sun Shadow intentionally is not a cascaded shadow map. A CSM partitions the current
**camera frustum** to improve perspective shadow-map resolution, so it is view-dependent and can change
or shimmer as the camera moves ([Microsoft, *Cascaded Shadow Maps*](https://learn.microsoft.com/en-us/windows/win32/dxtecharts/cascaded-shadow-maps)).
Graph data must instead be deterministic in terrain space; the studio uses logarithmic heightfield
horizon queries plus a spatial penumbra filter, in the scalable heightfield self-shadowing family
described by [Timonen & Westerholm (2010)](https://onlinelibrary.wiley.com/doi/abs/10.1111/j.1467-8659.2009.01642.x).
The viewport may use camera shadow maps for presentation, but they never become simulation input. TAA
is temporal anti-aliasing and is likewise not a climate signal.

Standing water uses its own connected Temperature field rather than reaching through Snow. Across a
spatially filtered transition around 0 °C, flat lake
and sea surfaces become **ice**: liquid ripples and refraction stop and a rough, frosted material takes
over. The renderer removes bed snow anywhere water covers terrain, then adds snow back only where the
standing-water phase is frozen. There is therefore no floating snow on liquid water; removing the Snow
node leaves bare ice. The flatness gate avoids converting sloping river films into raised white ribbons.
The ice transition remains local—sheltered coves may freeze while warmer water stays liquid—but a physical
three-degree transition plus explicit bilinear field sampling removes block-sized phase stair steps without
a full-resolution CPU blur on every edit. A one-cell dry-side surface guard keeps shoreline
triangles on the water plane; signed depth still clips coverage, eliminating mountain-sized shoreline fins.
The fallback Water model is intentionally lapse-only; connect the Temperature graph for the same solar/shadow
climate used by Snow.

The render mesh now performs **height-aware edge spinning**. For every heightmap quad it fits both candidate
triangle pairs to reference gradients estimated from the surrounding 3×3 height samples. This preserves
ridge and valley creases that a simple shortest-diagonal rule can erase when both diagonal endpoints happen
to have similar elevations. Perfectly planar or genuinely ambiguous cells retain a deterministic checkerboard
tie-break, so terrain stays stable without camera-dependent topology flicker. Accumulated snow participates
because it is displaced geometry; water level, colour, climate, and camera-only changes do not rebuild terrain
topology.

WebGL2 vertex/fragment shaders cannot write an element buffer, and expanding every quad into an instanced
six-vertex draw would discard indexed vertex reuse at exactly the resolutions where it matters most. The studio
therefore streams the edge decisions directly into a GPU indexed buffer in bounded row batches. Rasterization
remains GPU-indexed, while even a 4096² mesh uses less than 3 MiB of temporary CPU staging instead of a roughly
384 MiB monolithic index array. A future WebGPU clipmap can move topology generation fully into compute without
changing this normal-fit contract.

This placement/stability split follows John Fearing's
[*Computer Modelling of Fallen Snow*](https://graphics.stanford.edu/courses/cs448-01-spring/papers/fearing.pdf)
and its [UBC doctoral thesis record](https://www.cs.ubc.ca/labs/imager/th/2000/Fearing2000/).
Temperature, sun exposure, melt and small avalanche layers follow the model family in Cordonnier et al.,
[*Interactive Generation of Time-evolving, Snow-Covered Landscapes with Avalanches*](https://www.cs.purdue.edu/cgvlab/www/publications/Cordonier18CGF/).
The surface-relaxation approach is also consistent with Festenberg's
[*Diffusive Surface Generation for Realistic Snow Cover Generation in Virtual Worlds*](https://tud.qucosa.de/landing-page/?tx_dlf%5Bid%5D=https%3A%2F%2Ftud.qucosa.de%2Fapi%2Fqucosa%253A25416%2Fmets).

Interactive builds cap the avalanche solve at 512² and reconstruct only the transient depth at the
working resolution; this keeps 1K–4K property edits bounded while preserving world-scale cell spacing.
Final quality removes the cap.

### Resolution independence (the **Res Lock** toggle)

Several node parameters are expressed **in cells**, so raising the resolution silently changes what they
mean. The worst offender is thermal `talus`, a height drop *per cell*: cell spacing is `1/RES`, so the
repose **angle** it encodes is `atan(talus·RES)` — **66° at 192² but 85° at 1024²**. At high resolution the
talus angle is near-vertical, thermal erosion barely runs, and the build comes out **spiky**. Droplet
density (a fixed count spread over `RES²` cells) and blur/deposit/peak radii have the same problem.

**Res Lock** (on by default) converts these to resolution-independent quantities against a 192² reference.
The toolbar's **Interactive / Final** tier separates iteration latency from final parity:

- **Interactive** (default) keeps physical talus scaling but caps simulation travel — at most 1.5×
  the authored iteration count for the thermal/snow family, and a travel multiplier of at most 2
  for the erosion kernels (see *Res Lock inside the erosion solvers* below). It is the live
  authoring tier.
- **Final** uses the full resolution-scaled iteration/droplet budget when the export needs the
  longer-travel simulation rather than the responsive preview.

The earlier CPU/reference measurements explain the trade:
`talus/k` (constant angle), `iters·k` (constant travel distance), `droplets·k²` (constant density),
radii `·k`. Measured on the default graph, comparing a 1024² build downsampled to 192²:

| scaling | spikiness vs 192² | build cost |
|---|---|---|
| off | **3.15×** | 4.6 s |
| talus only | 1.97× | 4.5 s (free) |
| talus + droplets·k² | 1.85× | 15.3 s |
| talus + iters·√k | 1.55× | 7.2 s |
| **full (Final tier)** | **1.21×** | 25.4 s |

Fixing the talus angle is the single biggest win and costs nothing; the rest buys the remaining parity by
doing proportionally more work — which is the honest price of resolution independence, and why a 1024²
build is a **Build**, not an Auto-recompute. (Gaea documents the same goal: a 512² preview keeps *"essential
parity for all major erosion features"* with a 4K/8K build.) Use **Interactive** for authoring and
**Final** when longer settling is worth the cost; turning **Res Lock** off is still available for raw
cell-unit experiments.

### Res Lock inside the erosion solvers (grid-scale invariance)

The scalings above are what a node eval can fix from *outside* the kernel — talus, counts, radii. The
four erosion solvers also carried length scales **inside** their loops, and those drifted the same way:
the same node on the same world-space input modified the terrain **less** the finer the grid. Measured
by `_verify_erosion_gridscale.js` (each node's pure eval on a world-coherent fbm source, 192² vs 384²,
Res Lock on; depthRatio = rms modification depth at 384 over 192, target 1.0):

| node (case) | depthRatio before | after | modification corr after |
|---|---|---|---|
| Stream power (m=0.5) | 0.719 | **1.004** | 0.992 |
| Stream power (m=0.2 / m=0.8) | — | **0.991 / 1.004** | 0.999 / 0.971 |
| Stream power at k=3, Final (576²) | — | **1.010** | 0.989 |
| Hydraulic (CPU droplets) | 0.809 | **1.021** | 0.966 |
| Hydraulic (GPU pipes) | **0.383** | **1.020** | 0.940 |
| Erosion 2 (GPU) | 0.499 | **1.077** | 0.984 |
| HydroFix (corridor-dominated, pre-filled input) | ~0.70 | **0.934** | 0.908 |

The landform gate correlates the **modifications** (`out − in`) across the grid change, not the
outputs: an untouched fbm field already correlates 0.9991 with its own downsample, so an absolute
gate would pass an identity node — the first form of this suite did exactly that on four of its
gates and was replaced in review. An identity guard (`depth ≥ 2·10⁻⁵`) backs it.

Per-kernel mechanism, each an application of "express the length scale in world units":

- **Stream power** — the first mapping shipped a plausible derivation ("K is a celerity; the
  incision signal travels one cell per iteration, so iterations scale k×") whose *travel half*
  cross-model review dismantled by measurement: this solver is the Braun–Willett *implicit
  cascade* — receivers are solved before donors in one ordered sweep, so a base-level signal
  crosses the entire network in a **single** iteration. (K's per-cell decay is real — it is why K
  needs boosting beyond the steady-state exponent at all.) That mapping was also a single-point
  fit that read 1.30 by 768² while its celerity term sat at exponent zero (a no-op) in every gate,
  because the default `m=0.5` makes `2m−1 = 0`. The shipped form keeps **iterations unchanged**
  (incision cost is resolution-independent) and carries a **calibrated** K exponent,
  `k^(1.198−1.018m)`, fitted by sweeping `m ∈ {0.2, 0.5, 0.8} × k ∈ {2, 3}` on the reference
  input and gated across both axes; uplift is untouched (same iterations, same total). The
  diffusion *dose* scales `k²`, absorbed by the kernel substepping past its per-pass stability
  bound — with the substep bound at **1/6**, not the 0.25 stability edge, because c ∈ (0.125,
  0.25) is the explicit scheme's *ringing corner* (Nyquist amplification near 1 with sign flips;
  a 0.24 bound made grid-scale damping a sawtooth in the dose, measured as a 627→335 channel-head
  jump crossing Ddt 0.24→0.25). That dose is the one k-growing cost term (k⁴ total Laplacian
  work — 41.6 s of diffusion measured at 2048² Final), so the **dose takes the Interactive tier
  cap of 2** and Final pays it in full. The calibration itself is **live evidence, not memory**:
  `_verify_streampower_calibration.js` re-derives the per-m roots each run and gates the shipped
  line within ±0.12 — and it has already done its job once: tightening the substep bound moved
  the m=0.8 root by 0.17, the harness went red, and the line was re-fitted (residuals ≤ 0.02 at
  all three m). Calibration, not derivation — the code says so.
- **CPU droplets** — a step is one cell, so per-step fractional rates (erode, deposit, evaporation)
  become `1−(1−r)^(1/k)` — identical total effect over the `k×` steps that now cover the same world
  distance — and the capacity's slope term is restored to reference-cell units. Speed and gravity need
  nothing: energy already sums the same total drop along the same world path.
- **GPU pipes** — water crosses one cell per iteration, so iterations scale `k×`; per-iteration
  quantities rescale accordingly (rain and the erosion cap by `1/k`, relaxation rates by the
  exponential form, evaporation and momentum by `^(1/k)`), and the head-difference terms — slope in
  the capacity law, flux gain — go back *up* by `k`, because a per-cell head drop halves when cells
  halve.
- **HydroFix** — two mechanisms with different lattice contracts. The soft accumulation *corridor* is
  a landform: its blur radius follows the grid and its amplitude is restored by the box-dilution
  factor (a 1-cell-wide channel line spread over a `(2R+1)` band loses exactly that factor — the
  `1/√k` fade the table shows). The descent *enforcement* stays one cell wide on purpose: it is a
  breach, a lattice operation like depression breaching itself, so its rms contribution shrinks
  `~1/√k` by design — the oracle reports it and refuses to gate it, because a band wide enough to
  pass it would be vacuous. The gated corridor case is corridor-*dominated*, not pure (~15% of its
  delta energy is the eps-descent across fill-flats, carrying the breach signature); deconvolved,
  the pure corridor sits at ~0.97, so the reported 0.934 under-states the fix.

Everything anchors to the **node-level** `k = RES/192`, measured before `atFeatureScale` coarsens the
grid — so `k=1` at the reference and the tuned look is preserved *by construction*; every factor is
exactly 1 there. The mountain/peak macro-weathering callers invoke the kernels without `gridK` and
stay byte-identical (digest re-baselined for exactly the compensated nodes, including the massif
exercise pin). Two per-node policies, stated once: **widths** (brush and blur radii) always follow
the full grid ratio — geometry, not travel; **travel** multipliers (pipe/droplet transport) take the
**Interactive** tier, which since the preview-parity fix below runs each hydraulic/Erosion 2 pass as
a *full-quality simulation on a 384-capped grid, delta-upsampled* (algebraically identical to the
old caps at RES ≤ 384), and **Final**, which simulates on the working grid. Stream power's incision
has no travel multiplier (iterations unchanged), so only its diffusion *dose* takes the Interactive
cap of 2. Invariance is *certified at the measured points* — k=2 for every node, k=3 (Final) and
the m-axis for stream power, inside the [0.80, 1.25] band — not claimed "at any grid"; the
exponential-family compensations should drift slowly beyond, and the oracle is where that claim
gets extended, not this paragraph. The oracle also REPORTS, live, the Interactive tier's parity at
the app-default 512² (pipes depth ratio **0.978** under the tier-grid contract — it read 0.669
under the old starve-the-sim caps) and what the legacy path drifts (`SCALE_RES` off: depth 0.680,
modification corr 0.779 at k=2), so the armed thresholds stay measurements, not memories. On the whole default graph, `_verify_resparity.js` now reads scaled rms 0.0462
(unscaled 0.0586) with the 768² build at 0.7× the reference's slope roughness (unscaled: 2.5×
spikier).

### Five targeted fixes, each measured red-first

- **Color Erosion routed pigment with no depression handling** — the Legal Order's most common
  defect, in miniature: on the shipped defaults, **98.8% of all deposited pigment mass landed on
  the 1.2% of cells that are pits** (an 80× concentration) and the channels got nothing. Routing
  now fills first (for *routing only* — deposition and the visual pass still read the real
  surface): capture factor 80.6 → **3.1**. The `min(resScale(), 2.5)` cap that froze transport in
  cells above 480² is gone; the 96-step clamp is the cost guard.
- **Deposits normalized away its own units** — a half-amplitude terrain produced the *identical*
  deposit mask (measured ratio 1.000): `normalize()` laundered a depth field into a self-scaled
  mask, reference `10`'s defect verbatim. The mask is now physical: fill depth in metres against a
  **Full-mask depth** slider (default 25 m — the old normalize implicitly saturated at whatever the
  map's own max was, 224 m on the default mountain, so masks read near-black *and* meant nothing
  across terrains). The closing also ran a square structuring element; an octagonal one (square
  `r1 = √2·rd` plus diagonal `rd = r/(2+√2)` passes equalize axis and diagonal reach) takes the
  directional bias on a radial-groove probe from 1.153 to **1.086**.
- **HydroFix's shipped default did nothing** — at fix = 0.52 it removed 10 of 750 pits
  (rms 2.3·10⁻⁴). The mechanism was the tell: enforcement was `lerp(out, target, fix)`, and **52%
  of a breach is a dam**. `fix` now controls *where* the node acts (channel extent, exponential
  across the slider), never *how much* — a breach always fully connects. The default now removes
  61 pits at 12× the action, the slider is smooth across its range (36/61/95/158 pits removed at
  .25/.52/.75/1.0), fix = 0 is an exact bypass, and fix = 1 is continuous with the old top end
  (enforcement identical; the threshold differs at the 10⁻¹⁶ relative level).
- **Thermal's only physical control was unreachable** — Real scale shipped default-off, so a fresh
  node had no Repose slider at all, and repose 25° vs 45° measured *identical* slope percentiles.
  Real scale is now the default (cell units remain the escape hatch; saved graphs keep their
  stored value). Stated honestly: repose now steers (p75 50.2° vs 52.3° at 30 iterations on
  mountain-grade relief) but convergence toward the target is slow on big terrain — 80 iterations
  buy only ~2° more. That is mass conservation doing its job (the talus apron has to go
  somewhere); the full cure is a wash/export term like the Canyon's Musgrave pass, which is queued
  work, not something to smuggle into a defaults fix.
- **The Interactive preview starved the simulation instead of shrinking it** — the old dose caps
  (droplet count `min(4,k²)`, gridK `min(k,2)`, applied on the *full* grid) previewed at **0.64×**
  of Final's depth at the default 512², and rate compensation cannot close that gap
  (capacity-limited dynamics saturate; measured 0.647). Interactive is now a **full-quality
  simulation on a 384-capped grid, delta-upsampled** — exactly what A2's grid invariance licenses:
  preview/Final depth **0.92 (droplets) / 0.94 (pipes) / 1.00 (Erosion 2)** with modification
  correlation ≥ 0.96, and the droplet preview got 1.9× *faster* (a coarse grid is cheaper than a
  starved fine one). At RES ≤ 384 the new arithmetic equals the old caps exactly — digest-verified
  bit-identical below the cap. Honest limits: the parity is *amplitude* parity — the preview keeps
  base-terrain fine detail Final would erode (high-frequency energy 1.18–1.45× at 1024²) and
  cannot contain sub-tier structure at 2048²+, and Erosion 2's fine gully pass rides the 384 grid
  on Interactive; Deposits' sibling `Texture` still self-normalizes its composite (kept: a
  composite *driver* is a relative mix by contract), so only its soil term carries the physical
  units.

### Cross-engine honesty: what the hydraulic "auto" tab actually costs

The Hydraulic node's two engines are two different simulations behind one tab, and at identical
sliders the pipe engine modifies the terrain at **~0.37×** the droplet engine's depth
(modification correlation ~0.59 — broad pipe valley systems vs dendritic particle tracks). A
parity retune was attempted and **reverted, with the numbers kept**: raising pipe iterations to
~160 reaches depth parity (0.89–1.0) but breaks the grid invariance above (1.42 at k=2), and
scaling the per-iteration erosion cap leaves cross-engine depth *flat* while the grid ratio runs
to ~2.0 — the pipe engine's resolution invariance partly *rests on* that k-scaled cap clamping
the fine grid, so dose and invariance are coupled and no cheap knob buys both. What ships
instead: the measured relationship is **gated** in `_verify_gpu.js` (depth band [0.25, 0.55],
correlation floor 0.40 — a drift stop, explicitly not a parity claim), the Pipe iterations slider
maximum is raised to 360 so the depth-parity trade is available *by choice*, and closing the gap
properly — re-deriving the pipe dose family under clamp saturation — is queued kernel work, not
something to force through a defaults change that trades one measured invariant for another.

### GPU fast path (WebGL2 GPGPU)

The **CPU kernels remain the reference implementation**. On top of them there is an optional GPU path
(the **GPU** button in the toolbar) that runs the heavy, embarrassingly-parallel kernels as fragment
shaders over a fullscreen triangle into `RGBA32F` ping-pong render targets — the same technique as the
deferred composite. Currently GPU-accelerated: **Perlin fBm**, **Simplex fBm**, **Ridged MF**, **Warp**, **thermal
erosion**, and the default **Hydraulic erosion** engine.

Canyon is intentionally not in that list. WebGL2 fragment shaders do not provide the global mutable
queue/graph synchronization needed by Priority-Flood, flow accumulation, and receiver-first implicit
incision. Its bounded CPU topology solve is cached; the full-resolution resample, mesh upload and
rendering remain GPU work. This avoids pretending that a one-pass fragment shader is geological
evolution while keeping 2K/4K output practical.

It produces the *same* terrain as the CPU because the 32-bit integer hash is reproduced exactly in GLSL
`uint` (the CPU hash now uses `Math.imul`; plain `*` silently rounded past 2⁵³). `_verify_gpu.js` is the
parity check — measured **max |Δ| ≈ 2.6e-5 (Perlin), 4.1e-5 (Simplex), 1.1e-4 (ridged), 4.8e-7 (thermal)**, i.e. float32
-vs-float64 rounding, not algorithmic drift.

The studio opens at **512²**. The build profile also exposes **1024², 2048², and 4096²** targets; selecting
1024² or above queues the new target and switches **Auto** off so the existing viewport remains usable until
an explicit **Build**. A 1024² build is already 1,048,576 cells / 2.09M triangles, so 2K/4K are deliberately
treated as intentional build operations rather than live slider resolutions.

Build and live recomputation use a progressive DAG evaluator. The compact status HUD reports elapsed
time, the active node, and completed dirty nodes as a segmented bar; cached nodes do not inflate the
total. Evaluation yields between measured-heavy nodes and periodically through cheap chains, allowing
the browser to repaint without adding a full animation frame to every passthrough. Starting a newer
edit cancels the older run at the next yield, preventing a stale graph from replacing the newest result.
A single long simulation is still one honest segment—its clock and active-node pulse continue, but the
studio does not invent sub-step percentages the kernel cannot report.

**The diamond-plate artifact (fixed).** Smooth snow faces rendered with soft rhombus-shaped plates
outlined by creases — reported from a live session, diagnosed as the adaptive mesh diagonal's tie
band: on a drape-smoothed surface the normal-fit signal collapses (median |fitDelta| 6.8·10⁻⁶
against the old 1·10⁻⁶ tie threshold), so *noise* chose the diagonal and the wins clustered into
~100-quad same-diagonal patches (measured: 37% of all quads flipped from the checkerboard, 36,608
patches). The band is now decisive-only at 1·10⁻⁴: flips fall to 2.4%, the largest patch is 31
quads and elongated along genuine creases (the real-crease signal is p99 2·10⁻³, 20× above the
band), and every ridge/valley case in `_verify_edge_spin.js` still chooses the fitted diagonal.

Thermal runs as **two passes** — one memoising each cell's `(move, sum)`, one redistributing — because the
obvious single-pass version recomputes every neighbour's `moveSum` (72 texture fetches per cell vs ~27).
Profiling a 1024² build showed thermal at **84% of total time**; the split cut the whole build from
**10.6 s → 3.9 s** with parity unchanged.

Hydraulic now has two honest engines. **GPU pipes** is a Mei-style four-neighbour virtual-pipe solver:
bed, water, suspended sediment and directional flux stay in `RGBA32F` textures for the whole simulation,
with outflow clamped to available water and sediment transported by the same flux field. **CPU droplets**
keeps the older scatter-write particle reference for comparisons. At 192² under SwiftShader, GPU pipes
finish 48 iterations in **47 ms**, produce both erosion (20,350 cells) and deposition (16,514 cells), and
remain finite; Warp matches its CPU reference to max |Δ| **4.4e-5**.

**What erodes must deposit — or be counted as export.** Both engines used to leak their terminal
suspended load, and the two leaks turned out to be different stories. The GPU readback kept only the
bed channel, discarding every unit of sediment still in transport when iterations end — **91.9% of
net-eroded volume vanished** at reference settings, which is why the node could never finish a fan or
a delta: the sediment sliders modulated a sink. The fix settles the blue channel where it stands (bed
and suspended sediment are exchanged strictly 1:1, same units), **rim included** — a rim exclusion was
tried first, on the theory that the flux shader's permanent −0.03 edge head concentrates suspension
there, and was **rejected by measurement** in cross-model review: the edge head *flushes* suspension
off-grid, the rim carries the least suspended load of any ring (mean 0.0025 vs 0.0064 interior), a
deposit lip is geometrically impossible (rim max suspension is half the rim's mean net erosion), and
the exclusion only deepened the existing one-cell border trench by ~15%. Measured after the fix:
deficit **0.919 → 0.345**, deposition-to-erosion ratio **0.08 → 0.65**, 231 units settled, max
single-cell rise 0.033 (no beading); the remaining deficit is genuine in-sim export through the edge
pipes — exact by elimination, so the GPU ledger flags it `exportedDerived` and no closure gate accepts
it as evidence. The CPU droplet ledger read differently: most of its apparent **42.9%** loss was
droplets *legitimately* exporting off-grid with their load (the boundary is base level); the true
interior leak — dry-out and life-cap exits — was ~2% of eroded volume on open terrain (closed basins
should raise the settled share *by mechanism* — a drying droplet is the pan filling — though the
oracle measures open fbm only). Both engines now write a `hydroMassDiag` ledger
(`{sumIn, sumOut, settled, exported, exportedDerived, lost, brushClipGain}`); the first closure form
tolerated 5% mismatch, and re-review found that tolerance absorbing a real unnamed mass *source* —
border-clipped brush cells remove nothing from the terrain while the droplet credits itself in full
(+1.25 units at radius 2, growing with the radius slider). Named in the ledger, the budget closes to
**5.7e-8** — float accumulation, not tolerance. `_verify_erosion_mass.js` (9 gates) also proves the
settle flag is **opt-in**: Mountain/Peak macro-weathering callers stay byte-identical — the mountain
node's massif form is now digest-pinned via an `ex=` exercise entry, closing the one opt-out call
the baseline digest never reached — and the digest was re-baselined for exactly `hydraulic`,
`erosion2`, and that coverage extension; 55 of 57 node types unchanged. Two honest
caveats: the ledger is a *kernel* property, not a node property (Erosion 2 runs the kernel twice on a
feature-scale-coarsened grid and post-shapes; a wired mask rescales the kernel's output — recovered
mass included — per cell), and the ledger records only the most recent kernel run.

On the default graph, the combined GPU-pipe + GPU-warp + Interactive-tier change cut a 1024² evaluation
under the software-GPU harness from **14.7 s to 3.6 s (4.1×)**. Real hardware should be faster; these
figures are deliberately the conservative floor.

The priority-flood + D8 pair behind displayed lakes/rivers is inherently sequential and stays CPU; it is
skipped unless a Water node needs it. GPU nodes still read their result back to a `Float32Array` between
nodes, so a fully texture-resident graph runtime is the next large architectural win.

## Hexagonal lattice mode

The Terrain definition panel's **Grid lattice** toggle switches the working grid to the hexagonal
lattice of `references/26-hexagonal-lattice.md` — odd-r offset storage on the same Float32Array,
nothing about the node graph changes. What changes, and what `_verify_hex.js` holds:

- **Static equilateral topology.** The hex lattice has a *unique* equilateral triangulation — a
  row-parity alternation of the two quad patterns the square mesh already used — so edge spinning
  ceases to exist: `buildIndex()` uploads the index buffer once and it is hash-identical across
  any height edit (gate H1). The water plane shares the same lattice, or shorelines would tear.
- **Toggling the lattice does not re-roll your terrain.** Two coordinate systems, kept apart.
  Everything *authored* — generators, Position X/Y, shapes, painted strokes, warp displacement —
  lives in the **domain** (`u = (x + ½(y&1))/n`, `v = y/n`), so the same seed draws the same
  landscape on either lattice: **corr 0.9999** on a single fbm node, **0.992** end-to-end on the
  default graph. Everything *physical* — erosion, routing, wind, snow, normals, AO, picking, DEM —
  reads **world metres**, where rows sit √3/2 apart and the footprint is truthfully rectangular
  (`scale × scale·√3/2` m).

  This replaced a world-point seed contract, and the reasoning is the useful part. Agreeing at
  matched world points is self-consistent, but a hex map is only 0.866 as tall, so it means
  *cropping* the noise — measured **corr 0.574**, which is the "why did my terrain change?" users
  actually hit. The unit domain cannot map isotropically onto a non-square world, so the real
  choice is **squash or crop**, and squash is the cheaper half: a 13.4% aspect squash of an FBM
  field is indistinguishable from a slightly different frequency (noise has no canonical aspect
  ratio), whereas a crop is a different draw. The **lattice** stays isotropic under either choice,
  so every D6 kernel keeps its correctness untouched.

  The contract change also *demoted the old gate's negative control*, which is worth recording:
  with generators in the domain, dropping the odd-row half-cell shift is a sub-pixel change that
  correlation cannot see — it reads **0.999 for the broken build too**. H4b therefore controls the
  shift with the D6 Laplacian, which sees the row-parity zig-zag the shift exists to prevent:
  **1.000 = shift dead, 1.313 = shift alive**, bound at 1.15 between two measured endpoints.
- **D6 thermal** — six equidistant neighbours, one distance, one threshold (the √2 distance split
  the square kernel must correct simply does not exist). Mass conserved to 2·10⁻¹⁰; the relaxed
  cone's talus ring reaches repose uniformly to **0.3%** azimuthal anisotropy (H2, H3).
- **Six-neighbour normals** (`Σh·eₖ/(3d)` — the centre height drops out) and exact picking.
- **A real wireframe.** The overlay used to reinterpret the triangle index buffer as a
  `LINE_STRIP`, which invents a segment from each triangle's last vertex to the next triangle's
  first: ~**131,000 fake segments** (8.4%) and 511 real edges never drawn, *on both lattices*. A
  deduplicated edge buffer now carries exactly `3(n−1)²+2(n−1)` = 784,385 edges at 512², zero
  fakes, zero duplicates — which is what makes the hex topology checkable by eye.
- **Everything else that touches the lattice.** The shared bilinear sampler (relative error
  **6.07e-2 → 4.06e-8** on a world-linear ramp, where correct interpolation is exact), `warpField`,
  DEM import/export (**2.6e-3 → 5.4e-8**), D6 flow routing (**40.4% → 0.00%** of receivers that
  were not lattice neighbours), `slopeOf` (cone ring anisotropy **1.147 → 1.000**, against the
  2/√3 = 1.1547 the mechanism predicts), curvature, occlusion, droplet erosion, water shoreline,
  wind fetch/horizon, snow saltation, the Deposits structuring element, and the deferred
  compositor's per-pixel sampling.
- **Byte-safety:** on the square lattice everything is bit-identical (H5, plus the 60/60 digest).

**The close-out check** (`_verify_hex_parity.js`) is the one tied to what started this work —
toggling the lattice on the *default* graph changed the terrain far more than it should. Some
difference is legitimate: the map is a different shape, and D6 erosion genuinely routes water
differently from D8. What is *not* legitimate is a kernel misreading the lattice, and the two
separate cleanly — a geometric difference is smooth, while a misread leaves **row-parity
structure**. Measuring each node's odd/even row comb against its own column comb, the worst node
sits at **1.105×** its square character (bound 1.15). End to end the default graph now toggles at
**corr 0.992**, mean **2.4%** of range, down from 10.9% before the domain contract.

Honest limits, also stated in the toggle's hint: GPU compute is square-texture end to end and is
forced off on hex, so hex runs the CPU path throughout (the toolbar chip says so). Sampling uses a
two-row lerp — exact on linear fields, differing from 26's
true barycentric 3-tap only on high-frequency content. Single-receiver D6 is the bar here; MFD6
(multi-receiver dispersion) is the chapter's own further step, and D∞ has no hex analogue at all.
And one
measured finding that *corrects* the naive chapter reading: against a well-implemented
distance-corrected D8 thermal, D6's win is **exactness**, not facet diversity — the corrected D8
has 8 facet families to D6's 6 (facet-direction concentration 1.41 vs 1.17, reported in H3's
REPORT line and upstreamed to `references/26`).

## Verification

Every measured number in this file comes from a headless script that anyone can re-run — they ship
alongside the app rather than being scratch:

```sh
npm i playwright-core@1.49.0
node _verify_exact_transform.js      # exact vs raster placement, compose, CPU/GPU parity under XF
node _verify_trs.js                  # translate/rotate/scale about a pivot, Transform mask, Stamp
node _verify_range.js                # place 3 Mountains, union with Smooth Max, erode into one range
node _verify_peak.js                 # prominence, dissection, solid-of-revolution, mask shape variation
node _verify_streampower.js          # slope-area law S ~ A^-m, convergence, hillslope coupling
node _verify_tectonic.js             # Voronoi plates: warped boundaries, orogen width, drives incision
node _verify_curve.js                # skirt curve: monotone bake, LUT contract, widget drag
node _verify_layout.js               # Layout: per-vertex elevation, falloff profiles, ops, Source/Modifier
node _verify_gpu.js                  # CPU/GPU parity, GPU hydraulic invariants + timings
node _verify_erosion_mass.js         # erosion mass budget: terminal settle, export ledger, opt-in contract
node _verify_simplex.js              # Simplex determinism, Perlin distinction, transform + GPU parity
node _verify_all_canyon.js           # whole Canyon suite, one summary line per test (--quick to skip shared)
node _verify_canyon.js               # drainage primitive, controls/styles, determinism
node _verify_canyon_relief.js        # depth is cut by the solve; compose is affine; weathering mass budget
node _verify_canyon_slopes.js        # cliff/talus modes must track the bed table, not the geometry
node _verify_canyon_gridscale.js     # landform must survive a process-resolution change
node _verify_canyon_identity.js      # cache-key correctness + build-to-build digest for refactors
node _verify_canyon_process.js       # Erosion 2/HydroFix invariants, starter graph, hero/plan evidence
node _verify_build_progress.js       # elapsed clock, dirty-node progress, active node, completion/dismissal
node _verify_toolbar.js              # build profile, 512 default, queued 2K/4K, commands, responsive widths
node _verify_menubar.js              # File/Edit/View/Help, New Terrain resets, responsive hamburger
node _verify_workflow.js             # persistent/clamped splitter, layouts, fullscreen, preview, undo/redo
node _verify_quick_create.js         # drag-out search, compatible creation, auto-link, one-step undo
node _verify_viewport_ui.js          # quiet icon rail, exclusive flyouts, responsive viewport controls
node _verify_toolbox.js              # graph-owned categorized node toolbox, search, placement, quick menu
node _verify_organize.js             # deterministic graph layout, branch scopes, context actions, no rebuild
node _verify_edges.js                # selectable/mutable links, hit target, removal paths, mask contract
node _verify_placement.js            # SDF Shape masks + the universal Mask rule
node _verify_featurescale.js         # Transform against an analytic sine oracle; Feature Scale widths
node _verify_resparity.js            # Res Lock: same terrain at 192² / 384² / 768²
node _verify_erosion_gridscale.js    # erosion-family grid invariance: modification depth + landform, 192 vs 384
node _verify_streampower_calibration.js  # re-derives the stream-power K-exponent roots; gates the shipped line
node _verify_hex.js                  # hexagonal lattice: static topology hash, D6 mass + ring isotropy, seed contract, square byte-safety
node _verify_hex_parity.js           # close-out: default graph toggled square<->hex differs only by the seed contract, not by lattice misreads
node _verify_hex_deferred.js         # compositor GLSL sampler vs the CPU sampler at matched world points (probe lifted from the shipped shader)
node _verify_hex_sampling.js         # the shared bilinear sampler is exact on hex; callers pass world units
node _verify_hex_dem.js              # DEM import places cells at their world point; export resamples back to square
node _verify_hex_flow.js             # D6 routing: receiver adjacency, reported distances, slope ring isotropy
node _verify_wireframe.js            # wireframe draws real mesh edges (both lattices), no invented segments
node _verify_realscale.js            # Real Scale: repose angle in degrees, resolution independent
node _verify_data.js                 # the eight Data Map channels
node _verify_satnode.js              # one-gradient SatMap: stacking + explicit biome branch/blend
node _verify_satpicker.js            # visual LUT-strip library + graph-bound selection
node _verify_colormixer.js           # dynamic 2–15 layer stack, ordering, modes, opacity
node _verify_satgen.js               # SatMap Studio extraction + LUT build
node _verify_render.js               # colour pipeline, PBR/data views, exposure, image contrast
node _verify_edge_spin.js            # ridge/valley-aware topology + bounded GPU index streaming
node _verify_snow.js                 # snow depth/displacement, aspect melt, ice cover, mass, compass
node _verify_wind.js                 # terrain wind physics, regional masks, Snow input, HUD direction/readout
node _verify_water_surface.js        # global waves/refraction + rasterized fluid-surface depth layer
node _verify_water_hydrology.js      # lake filter + river density/depth controls and sea separation
node _verify_mask_draw.js            # resolution-independent vector masks + masked Sculpt merge
node _verify_param_visibility.js     # active mode tabs hide irrelevant controls and preserve values
node _verify_zoom.js                 # cursor-focused deep zoom, pivot pan, clipping, frame reset
node _verify_colorfx.js              # SatMap -> Color Erosion -> Weathering node semantics
node _verify_realtime.js             # coalesced live edits + colour/water/height buffer invalidation
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
