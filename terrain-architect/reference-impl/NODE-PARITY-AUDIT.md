# Node-Parity Audit — Gaea vs World Machine vs Houdini vs our atoms

Question: what do the three baseline tools ship out of the box, and which **atoms** do we not have yet?

**Scope rule (per request): composites are excluded.** A node counts as a gap only if it is a genuine
*atomic* capability — a distinct generator, physical process, or selector primitive — that cannot be
built from atoms we already have. Excluded from "gap" status: nodes that are compositions of our atoms
(e.g. MountainRange = union of mountains), color/output/render/export, graph-plumbing/utility,
interactive paint/draw, and stylized/decorative-only effects.

Inventories collected from the official references (2026-07):
- **Gaea 2** — 183 nodes / 9 families (Primitive 23, Terrain 14, Modify 41, Surface 21, Simulate 25,
  Derive 14, Colorize 13, Output 12, Utility 20). `docs.gaea.app/reference` (`TOC_Reference.js`, `llms-full.txt`).
- **World Machine 4** ("Artist Point") — ~90 Devices / 9 categories (Generator, Filter, Natural,
  Combiner, Selector, Output, Texture, Utility, Parameter). `help.world-machine.com`, `learn.php?page=devref`.
- **Houdini 20.5** — 40 `HeightField*` SOPs (generation, erosion, flow, masks, layers, I/O, transform,
  scatter/shade). `sidefx.com/docs/houdini`.

---

## The genuine atomic gaps (composites excluded)

| # | Capability | Where it ships | Verdict |
|---|---|---|---|
| **1** | **Braided / anastomosing rivers** — *multi-thread* channels that split and rejoin around bars (not a single meandering thread) | Gaea **Anastomosis** (and partly **Rivers**) | ◑ **FILLED at reduced-complexity tier** — implemented as `braided.braided_river` (Murray & Paola 1994 cellular model: split flow + **per-branch** super-linear transport that banks bars at splits + lateral relaxation), with oracles (`tests/test_braided.py`: braids index>1, the super-linearity banks bars = exports far less than m=1, sediment conserved, deterministic). **Honest limits:** (a) statistically braided, not a photoreal woven planform — the documented ceiling of reduced-complexity cellular models; a crisp braid needs a CFD morphodynamic solver (Delft3D/BASEMENT), out of pure-NumPy scope. (b) Gaea's own "Anastomosis" is **not** a braidplain simulation — it's a stylized downcutting *carve* on existing terrain, so the tool baseline here is a look, not physics. See `CANON-COMPARISON.md` follow-up 6 + `references/03-flow-routing.md`. |

That was the **only** clear-cut atomic geomorphic gap across all three tools — now filled at the
reduced-complexity tier (a photoreal braid is a CFD-tier gap we do not fake; see above).

### Now covered — the File Input/Output node (was scoped out as "I/O")
Gaea **File**, World Machine **File Input / File Output**, Houdini **HeightField File** — load an
external/real heightmap as a base, write the result back. Originally excluded here as non-atomic I/O,
but it is what makes real-world workflows possible ("add erosion to a real USGS/SRTM area"). Now
implemented as `heightfield_io.py` (`load_heightfield`/`save_heightfield` for `.npy`/16-bit `.png`/raw
`.r16`/`.r32`/SRTM `.hgt`, `fetch_srtm` for real AWS Terrain-Tiles, `window` to crop) — every atom
already takes a plain float array, so a real DEM drops straight into stream-power/thermal/analysis.
Verified by `tests/test_heightfield_io.py`; demo tile "08 Real DEM base + erosion" in the grid.

### Borderline — noted, not counted as gaps
- **Spectral / multi-band terrain filter** (Gaea *Filter*, *GraphicEQ*) — isolate/suppress features at
  chosen scales. We already carry FFT machinery (`winds.divergence_spectral`, `isostasy.flexure_fft`),
  so a band-pass terrain filter is a **composite**, just not yet exposed as a named atom. Cheap to add.
- **Lichtenberg / dielectric-breakdown branching** (Gaea *Lichtenberg*) — stylized branching cracks.
  The *physical* branching (dendritic drainage) we already produce via flow accumulation; the DLA look
  is decorative, so excluded.
- **3D / volumetric noise → caves & overhangs** (Gaea *Cellular3D*) — needs a voxel field, not a 2.5D
  heightfield. Out of the heightfield paradigm entirely (we scope voxel/overhang work in chapter `24`).
- **Seamless / tileable synthesis** (Gaea *Seamless*, WM *Crop&Transform* mirror/repeat) — periodic-noise
  utility; a wrap-mode on the generators, not a new process.

---

## Why everything else is covered — the mapping

### Erosion / weathering / mass-movement — fully covered
Gaea *Erosion / Erosion2 / EasyErosion / Wizard / Wizard2* (hydraulic), *Thermal / Thermal2*, *Glacier*,
*Snow / Snowfield / Dusting*, *Scree / Debris / Crumble*, *Sediments*; WM *Erosion (+Legacy) / Thermal /
Coastal / Snow / Strata / Flow Restructure*; Houdini *Erode / Erode Hydro / Erode Thermal / Erode
Precipitation / Slump / Flow Field* →
`erosion_streampower`, `erosion_droplet`, `erosion_pipe`, `shallow_water`, `erosion_thermal`,
`diffusion.hillslope_diffuse`, `glacier.glacier_carve`, `snow.snow_step`, `runout.voellmy_runout`
(scree/debris runout), `flow.priority_flood_fill` (= WM *Flow Restructure* / Gaea *HydroFix*: make the
terrain drain), `flow.d8/mfd_accumulation` (= *Flow Field*/*FlowMap*). The many Gaea erosion *variants*
(Wizard/EasyErosion/Erosion2) are presets/engines over the same hydraulic process — composites.

### Hydrology / water — covered or composite
Gaea *Rivers / Lake / Sea / Anastomosis*; WM *Create Water / River / Reach Character* →
single-thread rivers = `meander.meander_belt` (cut-bank/point-bar/oxbow); lakes/seas =
`flow.priority_flood_fill` + `hydrology.water_surface` + `sims_illustrative.coastal_retreat`;
drainage networks = `flow` accumulation. **Braided rivers (Anastomosis) is the exception → gap #1.**

### Generators / landforms — covered or composite
Gaea *Mountain / MountainRange / MountainSide / Ridge / Canyon / Crater / CraterField / DuneSea /
Volcano / Plates / Uplift / Island / Rugged / Slump*; WM *Advanced Perlin / Voronoi / Layout*; Houdini
*HeightField Noise / Pattern* →
`landforms.mountain (×5 styles)`, `ridge`, `volcano (×2)`, `canyon`, `impact_crater`, `dunes`,
`tectonics.plate_uplift` (= *Plates*/*Uplift*), `fault_block_butte`, `alluvial_fan`; noise bases =
`noise.*` (perlin/simplex/worley/fbm/ridged/hybrid/gabor/domain_warp/curl). MountainRange/MountainSide/
Island/Rugged = composites (union / radial×noise / ridged overlay).

### Modify / warp / filter — covered or composite
Gaea *Warp / DirectionalWarp / SlopeWarp / Swirl / Whorl / Fold / Distance / Blur / Median / Denoise /
Sharpen / Clamp / Clip / Curve / Terrace / FractalTerraces / Dilate / Deflate / Threshold / Autolevel /
Equalize*; WM *Blur / Clamp / Curves / Terrace / Expander / Ramp*; Houdini *Blur / Terrace / Clip /
Distort / Remap* →
`noise.domain_warp`/`ops_filters.twist`/`.bend`/`.curl`, `landforms.fold`, `ops_filters.sd_*` (distance
fields), `ops_filters.gaussian`/`.median`/`.bilateral`/`.guided_filter`/`.perona_malik`, morphology
(`dilate`/`erode`/`opening`/`closing`), `landforms.terrace`, `.remap`, band/threshold via
`analysis.band_select` + histogram ops.

### Derive / selectors / masks — fully covered
Gaea *Slope / Angle / Height / Curvature / Peaks / Occlusion / Normals / FlowMap / Soil / RockMap /
TextureBase*; WM *Select Height / Slope / Convexity / Direction / Roughness / Wetness / Water*; Houdini
*Mask by Feature / Occlusion / Geometry* →
`analysis.slope`/`aspect`/`northness`/`curvature`/`horizon_ao`/`twi`/`normals` + `analysis.band_select`,
`analysis.derive_substances`/`derive_materials` (soil/rock/texture masks). (Roughness selector =
`h − blur(h)` band-select — composite.)

### Surface detail, Colorize, Output, Utility, Parameter — out of scope / composite
Gaea *Surface* family (Rocks/Stones/Outcrops/Craggy/Distress/GroundTexture/Sand/Sandstone/Shear/Stratify…),
all *Colorize*, *Output*, *Utility*; WM *Texture / Output / Utility / Parameter*; Houdini layers/I-O/
transform/scatter →
scatter overlays = `scatter.*`; strata/shear = `landforms.strat_coord`/`bed_erodibility`/`fold`; color =
`render.satmap`/`extract_satmap`/`splat_blend`/`material_rgb`/`photoreal`; shading = `render.hillshade`/
`sun_sky_shade`; the graph runtime, caching, and export = `graph_demo.py` + `render.write_png`. None are
terrain *atoms*.

---

## Bottom line

After excluding composites, **one** genuine atomic geomorphic capability is missing versus all three
baseline tools: **braided / anastomosing river channels**. Everything else the tools ship is an atom we
have, a composite of atoms we have, or a non-atomic category (color/output/utility/stylized). The two
cheap "exposed-composite" follow-ups are a spectral band terrain filter and a seamless/tileable wrap
mode; caves/overhangs (3D noise) are a separate voxel paradigm (chapter `24`), not a heightfield atom.

**Recommended next atom:** braided rivers via the Murray & Paola (1994) braided-stream cellular model
(discharge split among multiple threads around emergent bars; lateral switching), with an oracle for
multi-thread topology (braiding index > 1) — the one addition that closes the last node-level gap.

Sources: Gaea `docs.gaea.app/reference`; World Machine `help.world-machine.com` + `learn.php?page=devref`;
Houdini `sidefx.com/docs/houdini`. Braided-river grounding: Murray & Paola 1994 (*A cellular model of
braided rivers*, Nature 371); Nicholas 2013 (*Modelling the continuum of river channel patterns*).
