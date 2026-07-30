# Terrain Studio vs QuadSpinner Gaea — node-library gap analysis

**Executive summary**

1. We ship **60** node types (measured from `src/plugins/**/*.js`, not from memory: comb 6, mask 4, filt 11, gen 12, ero 5, effect 7, data 14, out 1).
2. **Gaea 2.3.0.0** ships **183** nodes across 9 families — corroborated three independent ways on `docs.gaea.app` (node-map table, the site's `search.json` lunr index, and `llms-full.txt`), with the accounting closing to zero remainder.
3. Against that list we have a direct equivalent for **41**, a materially weaker partial for **26**, and **no equivalent at all for 116**.
4. Of those 116, roughly **53 are cheap** — compositions of primitives we already own, or single per-pixel/small-kernel ops needing no new engine machinery. The remaining ~63 split into ~40 needing a new kernel and ~23 needing new engine machinery (multi-output ports, subgraph encapsulation, expression variables, mesh/scatter).
5. Our single largest categorical hole is Gaea's **Surface** family (21 nodes of finish detail; we have 1). Our largest *doctrinal* divergence is that Gaea's `Rivers` writes water into the heightfield, which our output contract forbids.

---

## Provenance — what is verified and what is not

Every Gaea claim below is traceable to a URL in this table. Nothing is recited from memory. Where I
could not verify something I have written **UNVERIFIED** in place of a claim.

**The docs moved, and the old host is a trap.** `docs.quadspinner.com` is still live but serves the
**Gaea 1.3** documentation (its own homepage says so). The Gaea 2 reference is at **`docs.gaea.app`**.
Any Gaea-2 claim sourced from `docs.quadspinner.com` is wrong by construction. The task brief named
the old host; this document uses the new one.

| URL | Status | What it gave |
|---|---|---|
| `https://docs.gaea.app/reference/node-map.html` | **OK** (60,761 B) | **The full node table**, with each node's family *and sub-group*. 182 hyperlinks; 191 `<tr>` minus 9 header rows = 182. |
| `https://docs.gaea.app/search.json` | **OK** (1,035,171 B) | The site's lunr index. 198 entries with `hive == "Node Reference"` = **183 node pages** + exactly 15 non-node pages (9 family indexes, nodes index, reference index, node-map, 3 Gaea2Houdini). Accounting closes with zero remainder. |
| `https://docs.gaea.app/llms-full.txt` | **OK** (889,941 B) | The full node list grouped by family with New/Improved/Renamed flags. All 183 slugs present, zero missing. |
| `https://docs.gaea.app/reference` · `/reference/index.html` | **OK** | The 9 family names + one-line family descriptions + the `/reference/nodes/<family>/<node>` URL scheme. Footer date **2026-05-09**. |
| `https://docs.gaea.app/install/gaea-1/migration-guide.html` · `/node-changes.html` | **OK** | Deprecation status: Gaea 1's GeoPrimitives and *all* LookDev nodes retired; `.tor` files incompatible with Gaea 2 `.terrain`. |
| `https://docs.gaea.app/reference/nodes/{terrain,primitive,simulate,surface,modify,derive,colorize,utility,output}/index.html` | **OK** ×9 | Curated "useful starting points" only — **not** full family listings (142 links across all nine). Counting from these undercounts badly. |
| `https://docs.gaea.app/reference/nodes/modify/triplanardisplacement.html` | **OK** | The 183rd node — see the discrepancy note. |
| `https://docs.gaea.app/reference/nodes/simulate/glacier.md` | **OK** | "Glacier creates flowing glaciers on mountain tops." |
| `.../simulate/rivers.md` | **OK** | "Rivers can instantly generate complex river networks on any terrain, whether it can sustain rivers or not." — and that it *modifies terrain* to guarantee unbroken flow paths. |
| `.../simulate/anastomosis.md` | **OK** | "Anastomosis creates interconnected water flow based downcutting, ranging from small pits to large river channels." Two modes: Destructive, Rivers. |
| `.../simulate/scree.md` | **OK** | "Creates accumulations of loose rock fragments scattered across slopes and terrain edges." |
| `.../terrain/volcano.md` | **OK** | "Generates a volcanic landform with a central cone and crater structure." |
| `.../terrain/craterfield.md` | **OK** | "Creates a landscape full of craters." |
| `.../terrain/dunesea.md` | **OK** | "Creates broad fields of dune-like terrain suitable for deserts and wind-shaped landscapes." |
| `.../surface/stratify.md` | **OK** | "Stratify creates broken strata or rock layers on the terrain in a non-linear fashion…" — localised substrata, unlike continuous terracing. |
| `.../surface/sand.md` | **OK** | "Sand creates medium and small level sand patterns. It can also be used to simulate dunes." |
| `.../modify/distance.md` | **OK** | "Generates a distance field from the input, measuring how far each point is from the nearest boundary or feature." |
| `.../modify/slopeblur.md` | **OK** | "…adds directional blurring based on the slopes of a Guide terrain or mask." |
| `.../modify/graphiceq.md` | **OK** | "Applies a multi-band equalizer-style filter to shape terrain features across different scales." Seven bands. |
| `.../modify/threshold.md` | **OK** | "…eliminating values higher or lower than the exact value specified." |
| `.../derive/normals.md` | **OK** | "Generates a normal map from the terrain for shading and downstream workflows." |
| `.../derive/texturizer.md` | **OK** | "Generates terrain texture masks using preset styles and controllable secondary effects." |
| `.../colorize/splat.md` | **OK** | "Splat creates a single heightfield by combining the channels of an RGBA color input." — **not** a splatmap emitter. I had assumed otherwise and the fetch corrected me. |
| `.../output/export.md` | **OK** | "Exports terrain, masks, or textures to external files." Formats/bit depths not in the fetched body. |
| `.../utility/seamless.md` | **OK** | "Seamless can transform any input terrain or color map into a tileable/repeating pattern." |
| `.../utility/layers.md` | **OK** | "…combines multiple layers using blend operations in a stacked workflow." |
| `.../utility/math.md` | **OK** | "Evaluates mathematical expressions to generate or modify terrain data procedurally." |
| `.../utility/var.md` | **OK** | "Reads or modifies named graph variables for procedural control and automation." |
| `https://docs.gaea.app/llms.txt` · `/sitemap.xml` · `/sitemap-0.xml` · `/robots.txt` · `/index.json` · `/lunr-index.json` · `/assets/js/search-index.json` | **404** | Do not exist. |
| `https://docs.gaea.app/node-reference/*` (incl. `node-map`) | **404** | Stale prefix cached by search engines; the live one is `/reference/`. |
| `https://docs.gaea.app/reference/nodes/utility/macro.md` | **404** | Because **there is no `Macro` node** — see the corrections below. |
| GitHub API tree for `QuadSpinner/Gaea2-Docs` | **404** | Footer-referenced but private or renamed. |

The site is server-rendered static HTML — no SPA problem, no blocking, every live page returned real
content. The `.md` suffix on any node URL returns the raw source, which is how the quoted
descriptions below were obtained.

### Corrections and discrepancies, all measured

- **183, not 182 — and the missing one is identified.** The node-map table lists 182; `search.json`
  and `llms-full.txt` both account for 183. The extra is **`TriplanarDisplacement`** (Modify): it has
  a live page and appears in the 2026-05-09 docs changelog, but is absent from the node-map table
  *and* from the Gaea 1→2 Node Changes page. Its sub-group is not published anywhere fetched.
- **Per-family: Primitive 23, Terrain 14, Modify 41, Surface 21, Simulate 25, Derive 14, Colorize 13,
  Output 12, Utility 20** = 183.
- **Two corrections to my own first pass, both caught by cross-checking rather than by re-reading.**
  My initial `llms-full.txt` fetch was summarised by a small model and it (a) **invented a `Macro`
  node** that does not exist — only `MacroPort` does, which is why `macro.md` 404'd — and (b)
  **dropped `ColorThreshold`** (Derive, new in 2.3.0.0). The 404 was the tell and I filed it as
  "UNVERIFIED behaviour" rather than as evidence the node was fictional. *A 404 on a node page from a
  list you trust is evidence about the list, not about the page.*
- **Family index pages are not listings.** They show curated "useful starting points" (142 links
  across all nine families), which is why the Simulate index returned 20 and Utility 19. Not a doc
  inconsistency — a wrong source. Use `node-map.html` or `search.json`.
- **Version: Gaea 2.3.0.0**, pages stamped "Updated on 2026-05-9". `ColorThreshold` is listed in the
  2.3.0.0 changelog and is present in the map, which is what confirms the map is 2.3-current.
- **Naming inconsistency between two official Gaea pages.** The Node Changes page calls two Derive
  nodes **Flow** and **FlowClassic** (noting FlowClassic was formerly "Flow Map"); the node map and
  the live URLs use **FlowMap** and **FlowMapClassic**. This document uses the node-map/URL spelling.
- **No node is marked deprecated.** Legacy markers in Gaea 2 are all *parameter*-level (Crater's
  "Classic" mode, an "Old" accentuation method, "Gaea 1 Style Mask Ports"). Node-level retirement
  happened at the 1→2 boundary: all GeoPrimitives and all LookDev nodes were retired.
- **`llms-full.txt` gives names and change-status only, not per-node descriptions.** I asked it
  explicitly for ~120 node descriptions and it returned "NO DESCRIPTION IN SOURCE" for all of them.
  Every description quoted in this document therefore comes from an individual `.md` node page
  fetched separately. Nodes without a quoted description are ones nobody fetched, and no description
  has been invented for any of them.

### Reconciling with the existing in-repo audit

`NODE-PARITY-AUDIT.md` (`~/.claude/skills/terrain-architect/reference-impl/`, dated 2026-07)
independently counted **183 nodes / 9 families** with the same per-family split, which is a useful
external confirmation. It concludes that exactly **one** genuine gap exists (braided rivers). That is
not in conflict with the 116 here — it answers a different question. That audit measured **atoms**
(distinct generators, physical processes, selector primitives) and explicitly excluded compositions,
colour, output, utility and stylised effects. This document measures **shipped nodes** — what a user
finds in the palette. Both numbers are true. The 116 is the product gap; the 1 is the science gap.

---

## Part 1 — what WE have (measured)

Extracted from `apps/terrain-studio/src/plugins/<cat>/*.js`. Count verified by
`grep -h -oE '^\s*type: "[a-z0-9_]+"' */*.js | sort | wc -l` → **60**, and per-category file counts
match the declared 6/4/11/12/5/7/14/1 exactly.

| Cat | # | Types |
|---|---|---|
| `gen` | 12 | `perlin` `simplex` `ridged` `worley` `gradient` `shape` `mountain` `canyon` `tectonic` `layout` `constant` `import` |
| `comb` | 6 | `blend` `add` `maxmin` `stampn` `smax` `smin` |
| `filt` | 11 | `warp` `terrace` `normalizen` `levels` `curve` `histeq` `blur` `sculpt` `clampn` `transform` `invert` |
| `ero` | 5 | `hydraulic` `erosion2` `thermal` `streampower` `hydrofix` |
| `mask` | 4 | `drawmask` `slopemask` `heightmask` `tempmask` |
| `data` | 14 | `d_height` `d_slope` `d_curvature` `d_flow` `d_peaks` `d_occlusion` `d_deposits` `d_texture` `d_wear` `d_sunshadow` `d_temperature` `d_heat` `d_wind` `d_windmodify` |
| `effect` | 7 | `satmap` `satmapblend` `colormixer` `colorerosion` `weathering` `snow` `water` |
| `out` | 1 | `output` |

Structural facts that bear on the gap analysis, all read from source rather than assumed:

- **One output port per node.** `definePlugin` (`src/core/registry.js`) requires `{cat, name, eval}`;
  `eval` returns a single `Float32Array`. There is no multi-output contract. This is the single
  constraint that makes several Gaea nodes structurally impossible for us today.
- **Dynamic input ports exist, but only for one node.** `colormixer` grows `nd._inputs` from
  `["Layer 1","Layer 2","Layer 3"]` (`src/legacy.js:3053`, `:3892`) up to 15. There is no general
  variadic-port mechanism.
- **Parameter DSL** is `src/core/params.js`: `slider`, `log`, `number`, `int`, `select`, `seg`,
  `tabs`, `text`, `curve`, `seed`, with `WHEN` (conditional visibility) and `GROUP` (panel sections).
  It is expressive enough that most Gaea nodes could be *declared* today; the missing pieces are
  kernels and engine contracts, not UI.
- **Export is an app button, not a node** — `exportHeightmap()` at `src/legacy.js:4210`, wired to
  `#exportBtn` at `:4224`. There is no Output-family node graph.

---

## Part 2 — the three gap tables

### A. WE HAVE, GAEA HAS — parity, with the honest comparison

Gaea counterparts are node **names** from `llms-full.txt`. Where I quote behaviour, the `.md` page is
cited in the Provenance table above; where I have only the name, the comparison note says so.

| Ours | Gaea counterpart(s) | Verdict |
|---|---|---|
| `perlin`, `simplex` | Perlin, Noise, MultiFractal | **Parity.** Both do fBm. Gaea additionally ships Gabor, LineNoise, DotNoise, DriftNoise, WaveShine, Cellular, Cellular3D, Pattern — a much wider noise bench. |
| `ridged` | MultiFractal | **Parity at the ridged-multifractal atom.** Gaea's `Ridge` is a *landform* node, not this. |
| `worley` | Voronoi, Cellular | **Slightly weaker.** We ship 3 modes (F2−F1, F1, 1−F1); Gaea splits Voronoi and Cellular into two nodes, implying more variants. Exact Gaea feature set **UNVERIFIED**. |
| `gradient` | LinearGradient, RadialGradient | **Parity.** We fold both into one node with a `kind` tab. |
| `shape` | Shape, Cone, Hemisphere | **Parity+.** Ours is an SDF (circle/box/line) with aspect, angle, falloff, invert; Gaea splits Cone/Hemisphere out as separate primitives. |
| `mountain` | Mountain, MountainRange, MountainSide | **Materially stronger per-node, narrower in coverage.** Ours is one node with 2 landforms × 4 shape families × 5 mountain types + a skirt curve; but it has no MountainSide (single-flank) mode. |
| `canyon` | Canyon | **Parity, plausibly stronger.** Ours is an evolved simulation (uplift → drainage area → lithology → incision → hillslope retreat) with 5 styles. Gaea's internals **UNVERIFIED**. |
| `tectonic` | Plates, Uplift | **Stronger.** Ours classifies each boundary as collision / subduction / island arc / rift / transform and diffuses uplift inland over an orogen width, then feeds `streampower`'s Uplift port. Gaea's Plates/Uplift internals **UNVERIFIED**. |
| `constant` | Constant | Parity. |
| `import` | File, TileInput | **Weaker on tiling.** We load PNG / 16-bit `.r16` / raw and real SRTM; Gaea's `TileInput` implies a tiled-build workflow we do not have. |
| `blend`, `add`, `maxmin` | Combine, Mixer | Parity. Gaea's `Layers` (stacked blend workflow) is more ergonomic for long chains. |
| `stampn` | Combine + Mask | **Stronger as a named node.** Gaea has no `Stamp`; the placement idiom exists but is assembled. |
| `blur` | Blur | **Materially weaker.** One separable Gaussian. Gaea ships Blur + Median + Denoise + Sharpen + SlopeBlur + VariableBlur — six nodes to our one. |
| `terrace` | Terraces, Steps, FractalTerraces | **Materially weaker.** One node (steps + sharpness) against three, and Gaea additionally has `Stratify` for *non-linear, localised* strata, which we cannot express at all. |
| `normalizen` | Autolevel | **Stronger.** Ours takes a Mask and measures range over the whole field before masking, so a biome edge cannot perturb normalisation. |
| `levels`, `curve`, `clampn`, `invert` | Adjust, Curve, Recurve, Shaper, Clamp, Clip, SoftClip, Threshold | **Weaker in count, comparable in reach.** Gaea's eight tone nodes cover roughly what our four do, plus SoftClip and a true hard Threshold we lack. |
| `histeq` | Equalize | Parity. |
| `transform` | Transform, Transform3D, Flip, Transpose | **Stronger on the axis that matters.** Ours folds the transform into upstream *generator coordinates* when the whole cone is procedural (`filt/transform.js`, `exactChain`/`evalExact`), so placement is exact and the terrain continues past the old tile edge. Falling back to raster resampling costs a measured ~25% of fine detail on one non-integer move. Whether Gaea's Transform resamples is **UNVERIFIED**. We lack Flip and Transpose. |
| `warp` | Warp, DirectionalWarp, SlopeWarp | **Materially weaker.** One isotropic noise warp; Gaea has directional and slope-driven variants. |
| `hydraulic`, `erosion2` | Erosion, Erosion2, EasyErosion, Wizard, Wizard2 | **Weaker in entry-point variety, stronger in model composition.** Gaea ships five hydraulic entry points (presets/engines over one process). Our Hydraulic node exposes virtual-pipe and particle/droplet erosion as independent GPU stages with separate controls; either can run alone or both compose Pipe → Droplet with one final readback. Hex and unsupported float-blend contexts retain a visibly labelled compatibility fallback. |
| `thermal` | Thermal, Thermal2, ThermalShaper | **Weaker in count.** Ours has a real-scale repose-angle mode in degrees, which is a units win. |
| `hydrofix` | HydroFix | Parity (name-for-name). |
| `drawmask` | Draw, Mask | **Stronger.** Ours stores vector strokes in terrain space, so 512² authoring survives a 4K build. Gaea's `Draw` behaviour **UNVERIFIED**. |
| `slopemask`, `heightmask` | Slope + Threshold, Height + Threshold | Parity. Gaea keeps derive and select as separate nodes; we fuse them. |
| `d_height` `d_slope` `d_curvature` `d_flow` `d_peaks` `d_occlusion` | Height, Slope, Curvature, FlowMap, FlowMapClassic, Peaks, Occlusion | **Parity.** Gaea additionally has `Angle` (aspect), `Normals` and `ColorThreshold`, which we lack. |
| `d_deposits` | Soil, Sediments | **Weaker where it counts.** Ours is a derived morphological-closing mask with a physical `refDepth` in metres. Gaea's `Sediments` sits in **Simulate**, implying an actual deposition process. Ours is a prediction, not an accounting — and BACKLOG **C3** records that our erosion computes a mass budget and discards it. |
| `d_texture` | TextureBase, Texturizer | **Weaker.** Ours is a fixed slope/soil/flow mix; Gaea's `Texturizer` ships preset styles. |
| `d_wear` | RockMap | Parity (approximate; Gaea's RockMap internals **UNVERIFIED**). |
| `satmap` | SatMap | Parity. |
| `satmapblend`, `colormixer` | Layers, Mixer, Combine | **Comparable.** Our Color Mixer is a 2–15 layer stack with world-space edge blending — the closest thing we have to Gaea's `Layers`, but colour-only. |
| `colorerosion` | ColorErosion | Parity (name-for-name). |
| `weathering` | Weathering | Parity (name-for-name). Note BACKLOG **W9**: our `dirt` ships at 0.01, effectively off. |
| `snow` | Snow, Snowfield, Dusting | **Stronger physically, weaker in variety.** Ours is a depth field in metres with degree-day melt (mm/°C/day), avalanche repose angle, adhesion depth and optional physical wind scour. Gaea ships three snow nodes; their physics **UNVERIFIED**. |
| `water` | Lake, Sea, Rivers | **Different by doctrine — see the conflict section.** Ours is one node with Hydrology and Sea-level modes that defines *where fluid is*; it does not carve. Gaea's `Rivers` explicitly modifies terrain. |
| `output` | Export, Mesher, PointCloud, Unity, Unreal, AO, Cartography, Halftone, LightX, Shade, Sunlight, TextureBaker | **Our weakest area relative to Gaea.** One viewport terminal against twelve. Our file export exists but as a global button, outside the graph. |

### B. GAEA HAS, WE LACK — the gap

116 nodes with no equivalent. Grouped, with cost class:
**[C]** cheap — composition of what we have, or a per-pixel/small-kernel op needing no new contract ·
**[K]** needs a new kernel ·
**[E]** needs new engine machinery.

Cost classes are **my engineering judgement**, not a measurement. The criterion is stated so it can be
argued with: *[C] if it can be written as a plugin whose `eval` calls only functions already exported
from `legacy.js`/`core`; [K] if it needs a new numerical routine but still returns one field; [E] if it
needs a change to the node/graph contract itself.*

#### Primitive — 10 absent, 3 partial

| Gaea node | What it does | Why it matters | Cost |
|---|---|---|---|
| `Pattern` | Pattern generator (description **UNVERIFIED**) | Man-made and geometric bases; masks for cities, fields, tiles | **[C]** |
| `DotNoise` | Dot-based noise (**UNVERIFIED**) | Sparse feature seeding | **[C]** |
| `Cone`, `Hemisphere` | Analytic primitive solids | Placement bases; we half-cover with `shape` | **[C]** — extend `shape`'s `kind` enum |
| `Cracks` | (**UNVERIFIED**) | Fracture/joint masks — geologically load-bearing for cliff faces | **[K]** |
| `LineNoise` | (**UNVERIFIED**) | Lineament / fault-trace structure | **[K]** |
| `Gabor` | Gabor noise (**UNVERIFIED**) | Anisotropic, directionally-controllable noise — the right tool for bedding and foliation | **[K]** |
| `DriftNoise`, `WaveShine` | (**UNVERIFIED**) | Additional noise character | **[K]** |
| `Cellular3D` | 3D cellular noise (**UNVERIFIED**) | Slice-through-volume detail; caves need a voxel paradigm we do not have (`24`) | **[K]** for the 2D slice, **[E]** for real volume |
| `Object` | (**UNVERIFIED** — likely mesh/object import) | Bringing authored geometry into the terrain | **[E]** |
| `TileInput` | (**UNVERIFIED** — tiled build input) | Multi-tile world builds; unlocks worlds bigger than one field | **[E]** — needs a tiling contract; `14:48-53` warns flow accumulation and stream power **cannot be tiled** |
| `Cellular` | Cellular noise variant | Partially covered by `worley` | **[C]** — add modes |

#### Terrain — 8 absent, 1 partial

| Gaea node | What it does (sourced where quoted) | Why it matters | Cost |
|---|---|---|---|
| `Crater` | Impact crater landform | Rim/ejecta/floor is a distinct profile; sci-fi and lunar work needs it | **[C]** — radial profile through `shape` + `curve` + `stampn` |
| `CraterField` | "Creates a landscape full of craters." | A whole planetary aesthetic in one node | **[C]** — Poisson-disc scatter of the above via `stampn` |
| `Island` | (**UNVERIFIED**) | The single most-requested archetype after "mountain" | **[C]** — radial falloff × existing noise |
| `Rugged` | (**UNVERIFIED**) | Broken, non-hero terrain base | **[C]** |
| `MountainSide` | (**UNVERIFIED**) | A single flank filling the frame — the most common hero-shot composition | **[C]** — `mountain` + directional gradient mask |
| `Volcano` | "Generates a volcanic landform with a central cone and crater structure." | Distinct archetype; pairs with our missing lava story (`19`) | **[C]** — cone + crater + flank noise |
| `DuneSea` | "Creates broad fields of dune-like terrain suitable for deserts and wind-shaped landscapes." | We have **zero** arid coverage despite corpus ch. `16` | **[K]** — but `reference-impl/dunes.py` and `aeolian.py` already exist, so this is a port |
| `Slump` | (**UNVERIFIED**) | Mass-movement landform | **[K]** |
| `Ridge` | (**UNVERIFIED**) | Partially covered by `ridged` noise, but a landform ridge is not fBm | **[C]** |

#### Modify — 29 absent, 5 partial

The largest raw count, and mostly cheap. Gaea ships 41 Modify nodes; we ship 11 filters.

| Gaea nodes | Why they matter | Cost |
|---|---|---|
| `Sharpen`, `Median`, `Denoise` | Unsharp is `in − blur(in)` — we already have `blurField`. Median/bilateral denoise is the standard cleanup after erosion. | **[C]** for Sharpen; **[K]** for Median/Denoise |
| `SlopeBlur` "…directional blurring based on the slopes of a Guide terrain or mask", `VariableBlur` | Guide-driven, spatially-varying smoothing — the difference between "blurred" and "weathered" | **[K]** |
| `GraphicEQ` "…multi-band equalizer-style filter to shape terrain features across different scales" (7 bands) | Independent control of macro/meso/micro relief. Genuinely powerful and we have nothing like it. | **[C]/[K]** — a Laplacian pyramid over `blurField` is a composition; doing it well is a kernel |
| `Filter` | Spectral band filter (**UNVERIFIED** whether FFT) | **[K]** |
| `Distance` "Generates a distance field from the input, measuring how far each point is from the nearest boundary or feature." | A Euclidean distance transform of an *arbitrary* mask — unlocks falloffs, spacing, shore distance (`12:33` requires shore distance and `14` has no row for it) | **[K]** |
| `Dilate`, `Deflate` | Morphology. `d_deposits` already performs a morphological closing, so the kernel exists in-tree. | **[C]** |
| `Threshold` "…eliminating values higher or lower than the exact value specified" | Hard masks. `clampn` clips, it does not threshold. | **[C]** |
| `Flip`, `Transpose`, `Extend`, `Match` | Composition and matching utilities; `Match` (histogram matching to a reference) rides our `histEqualizeField` machinery | **[C]** |
| `SoftClip`, `Shaper`, `Adjust`, `Recurve`, `Clip` | Tone-curve variants over `curveField`/`levelsField` | **[C]** |
| `Swirl`, `Whorl`, `Fold`, `Origami`, `Pixelate` | Stylised deformations; `Fold` is an abs-fold, the rest are coordinate remaps we can already express | **[C]** |
| `DirectionalWarp`, `SlopeWarp` | Anisotropic warping — what makes strata and wind-shaping read correctly | **[C]** for directional (warp with a fixed vector), **[K]** for slope-driven |
| `ThermalShaper` | Thermal-style shaping as a filter rather than a sim | **[K]** |
| `BlobRemover`, `Heal` | Connected-component cleanup and hole repair — production hygiene after erosion | **[K]** |
| `Aperture` | (**UNVERIFIED**) | **[K]** |
| `TriplanarDisplacement` "Use TriplanarDisplacement when you need displacement using triplanar projection across a surface." | The 183rd node, absent from Gaea's own node map. Triplanar projection is a *surface-space* operation — of limited meaning on a single-valued heightfield. | **[K]**, low priority |
| `Meshify`, `Transform3D` | Leave the heightfield paradigm | **[E]** |

#### Surface — 18 absent, 2 partial. **The biggest categorical hole.**

Gaea ships 21 surface-detail nodes. We ship one (`terrace`). This family is the difference between a
correct terrain and a *finished-looking* one, and it is almost entirely cheap.

| Gaea nodes | What they add | Cost |
|---|---|---|
| `Roughen`, `Distress`, `GroundTexture`, `RockNoise`, `Bulbous` | Masked high-frequency breakup driven by slope/curvature/wear — all drivers we already ship as `data` nodes | **[C]** |
| `Contours`, `Grid` | Cartographic/technical overlays | **[C]** |
| `Pockmarks` | Small-scale impact/pitting scatter | **[C]** |
| `Craggy`, `Outcrops`, `Rockscape`, `Stones`, `Shatter` | Rock expression — outcrops emerging through soil, talus blocks, fracture | **[K]** |
| `Bomber` | Scatter-and-stamp of a sub-pattern | **[K]** — needs a scatter primitive; `reference-impl/scatter.py` exists |
| `Sand` "creates medium and small level sand patterns. It can also be used to simulate dunes." | Aeolian ripple detail | **[K]** — `aeolian.py` exists |
| `Sandstone` | Bedded sandstone expression | **[K]** |
| `Shear` | Shear deformation of strata | **[K]** |
| `Stratify` "creates broken strata or rock layers… independent substrata in localized zones — such as between fractured plates — rather than continuous layers" | This is *the* geological finish node and our `terrace` cannot approximate it: ours snaps globally, Gaea's is localised and non-linear | **[K]** — needs a strata coordinate; `reference-impl` has `landforms.strat_coord`/`bed_erodibility` |
| `FractalTerraces`, `Steps` | Terrace variants | **[C]** — modes on `terrace` |

#### Simulate — 12 absent, 6 partial

| Gaea node | What it does (sourced where quoted) | Why it matters | Cost |
|---|---|---|---|
| `Scree` "Creates accumulations of loose rock fragments scattered across slopes and terrain edges."; `Debris`; `Crumble` | Talus aprons at cliff bases. Our `thermal` moves material above repose but does not produce a distinguishable scree deposit as a layer. | **[K]** — `reference-impl/runout.py` (Voellmy) exists |
| `Anastomosis` "creates interconnected water flow based downcutting, ranging from small pits to large river channels." Modes: Destructive, Rivers | Braided/anastomosing channels. Note the fetched description makes this a **downcutting carve**, not a braidplain simulation — the prior audit says the same. | **[K]** — `reference-impl/braided.py` (Murray & Paola 1994) exists |
| `Glacier` "Glacier creates flowing glaciers on mountain tops." | Glacial ice **does not exist in the app at all** (BACKLOG §2). U-valleys, cirques, moraines are unreachable for us. | **[E]** — SIA flow, a genuinely new simulation; `reference-impl/glacier.py` exists |
| `IceFloe` | (**UNVERIFIED**) | See conflicts — BACKLOG already established there is no citable criterion for water-surface ice | **[K]**, F-tier |
| `Trees`, `Shrubs` | Vegetation simulation | Biome dressing. Doctrine says scatter driven by fields (`07`, `13`), not height writes. | **[E]** — needs scatter/instancing output, which one-field-per-node cannot express |
| `Hillify` | (**UNVERIFIED**) | **[C]/[K]** |
| `Lichtenberg` | Dielectric-breakdown branching | Decorative; physical dendritic drainage we already get from flow accumulation | **[K]**, low value |
| `Wizard`, `Wizard2` | Erosion preset chains | One-click quality — the reason Gaea feels fast | **[E]** — requires subgraph machinery, then trivial |
| `Sediments` | Sediment deposition (in **Simulate**, unlike our derived `d_deposits`) | Real accounting rather than a morphological prediction | **[E]** — needs multi-output ports (BACKLOG **W4**, D7 L2) |
| `EasyErosion`, `Thermal2`, `Dusting`, `Snowfield`, `Rivers` | Variants/presets over processes we have | Ergonomics | **[C]** given macros |

#### Derive — 4 absent

| Gaea node | Why it matters | Cost |
|---|---|---|
| `Angle` | Aspect (compass direction of steepest descent). We compute gradients everywhere (`d_wind` uses aspect-like terms) but never expose aspect as a field. Needed for insolation, snow-side, vegetation. | **[C]** |
| `Normals` "Generates a normal map from the terrain for shading and downstream workflows." | `08` requires a normal map in the handoff and we do not emit one as a graph product. | **[C]** |
| `Texturizer` "Generates terrain texture masks using preset styles and controllable secondary effects." | Preset composite masks over `d_texture` | **[C]** |
| `ColorThreshold` (new in 2.3.0.0; behaviour **UNVERIFIED**) | Selecting a mask from a colour branch — the colour→mask direction we have no node for | **[C]** |

#### Colorize — 8 absent, 2 partial

Low priority **by doctrine** (see conflicts) — these are preview products, not handoff.

| Gaea nodes | Cost |
|---|---|
| `Tint`, `Gamma`, `HSL`, `RGBSplit`, `RGBMerge`, `CLUTer` | **[C]** |
| `Splat` "creates a single heightfield by combining the channels of an RGBA color input" (weighted R/G/B/A sum, Autolevel + Clamp Product post) | **[C]** |
| `SuperColor`, `Synth`, `WaterColor` | **[K]** |

#### Output — 10 absent, 2 partial

| Gaea nodes | Why it matters | Cost |
|---|---|---|
| `Export` "Exports terrain, masks, or textures to external files." | Export as a *graph node* — multiple outputs, per-branch formats, named products. We have one global button. | **[K]** — the writer exists (`exportHeightmap`), the node contract does not |
| `Unity`, `Unreal` | Engine-specific emitters | **[E]** — this is BACKLOG **W6** (export profiles + manifest) |
| `TextureBaker` | Bake maps to texture sets | **[E]** — depends on W4 |
| `Mesher`, `PointCloud` | Geometry export | **[E]** |
| `Shade`, `Sunlight`, `LightX`, `AO` | Render products | **[C]** for hillshade/AO (we have `d_occlusion`, `d_sunshadow`) |
| `Cartography`, `Halftone` | Stylised render | **[C]** |

#### Utility — 17 absent, 2 partial. **The workflow hole.**

We have zero graph-machinery nodes. This does not show up in a screenshot and it is what limits graph
size in practice.

| Gaea nodes | What they buy | Cost |
|---|---|---|
| `MacroPort` | The port node of a macro/subgraph facility. **There is no `Macro` *node*** in Gaea's 183 — the existence of `MacroPort` implies subgraph encapsulation lives in the graph model rather than in the palette, but *how* Gaea's macros are authored is **UNVERIFIED**. Whatever the surface, the capability is one we lack entirely: without subgraph reuse a 200-node graph stops being editable. | **[E]** |
| `LoopBegin`, `LoopEnd` | Iteration over a subgraph | **[E]** |
| `Var` "Reads or modifies named graph variables for procedural control and automation.", `Math` "Evaluates mathematical expressions to generate or modify terrain data procedurally." | Parameters driven by expressions; one slider driving twenty nodes | **[E]** — needs a variable scope and an expression evaluator |
| `Switch`, `Gate`, `Route`, `Chokepoint` | Conditional and organisational flow control | **[C]** for Route/Chokepoint (pass-through), **[E]** for Switch/Gate (needs conditional evaluation) |
| `Compare`, `Mask`, `Edge` | Mask helpers; `Edge` (boundary extraction) is genuinely useful and we lack it | **[C]** |
| `Layers` "combines multiple layers using blend operations in a stacked workflow" | A general height/mask layer stack. Our `colormixer` is this idea but colour-only. | **[E]** — variadic ports as a general contract |
| `Seamless` "can transform any input terrain or color map into a tileable/repeating pattern" | Tileability. Required for any tiled world. | **[K]** |
| `Reseed`, `Repeat` | Variation generation | **[K]** |
| `Accumulator`, `DataExtractor` | Data plumbing (**UNVERIFIED**) | **[K]** |

### C. WE HAVE, GAEA LACKS — the differentiators

Negative claims about Gaea here rest on **absence from the verified 183-node list**. That is real
evidence for "Gaea ships no node called X", and weaker evidence for "Gaea cannot do X" — a capability
could hide inside a node whose page I did not fetch. Each row says which claim it makes.

| Ours | The differentiator | Evidence |
|---|---|---|
| **Hexagonal lattice** (engine-level, not a node) | The whole field can be `RES × round(RES·2/√3)` with equilateral cells and a truthful square world (BACKLOG **D1**). D6 one-ring erosion, routing, thermal and Laplacian constants; hex-native blur landed (`_verify_blur_isotropy`: hex 1.0000, was 1.185). | **Ours: measured** (`src/legacy.js` — 150 `lattice`/`isHex` sites; `26-hexagonal-grids.md`). **Gaea's absence: UNVERIFIED** — no node in the fetched list references a lattice choice, but I found no page stating Gaea is square-only. |
| **MFD flow routing (Freeman 1991, p=1.1)** on both lattices — MFD8 on square, **MFD6 on hex** | Water is distributed to *every* downslope neighbour in proportion to slope^p, so the resolved direction is continuous rather than snapped to a lattice spoke. Measured on a cone where drainage is radial by symmetry: facet concentration **1.8161 → 1.0114** (square) and **1.6734 → 1.0220** (hex). Both call sites (`d_flow` and the water refresh) share it. | **Ours: measured** (`src/legacy.js:5356`+, `_verify_flow_facets.js` 12/12). **Gaea: UNVERIFIED** — it ships `FlowMap` and `FlowMapClassic`; whether either is MFD is not stated on any page fetched. **Note: BACKLOG W2 lists MFD6 as open work and is stale — it has landed.** |
| `streampower` — **Stream power with an Uplift input** | `dh/dt = U − K·A^m·S`, Braun–Willett implicit cascade, with a live Uplift port so tectonics drives the incision. Ridges emerge as residue between valleys instead of being authored. Defaults calibrated against real SRTM (p90 9.9 vs 9.3, p99 16.0 vs 15.7, max 24.2 vs 22.8). | **Ours: measured.** **Gaea: no node of this kind in the fetched list** — Gaea's `Uplift` is a Terrain primitive, not an erosion driver. This is our strongest scientific differentiator. |
| `d_temperature`, `d_heat`, `tempmask` | A **physical Celsius temperature field** — datum-aware lapse rate (°C/km) + solar warming — that stays editable downstream, with a modifier node (offset/set/min/max) and a band selector in real degrees. | **Ours: measured.** **Gaea: no temperature node in the 183.** |
| `d_wind`, `d_windmodify` | A **physical horizontal wind-vector field in m/s** from prevailing wind, adjusted for windward speed-up, lee shelter and valley channeling, with an optional mass-consistency projection, plus a regional override node. | **Ours: measured.** **Gaea: no wind node in the 183.** |
| `d_sunshadow` | Deterministic terrain-space solar visibility as an **exportable, blendable data field** with a horizon reach in metres — not a viewport shadow. | **Ours: measured.** Gaea has `Sunlight`/`Shade`/`LightX` but they are in the **Output** (render) family, so the *product* differs even though the phenomenon does not. |
| `snow` | Snow as **depth in metres**: log-scaled snowfall, degree-day melt in mm/°C/day over a melt period in days, avalanche repose angle, adhesion depth, settling, and physical-wind scour into lee cornices. | **Ours: measured.** Gaea has Snow/Snowfield/Dusting; **their units and physics are UNVERIFIED**, so this is "ours is physical", not "theirs is not". |
| `smax`, `smin` | Quilez smooth min/max — crease-free union/intersection of heightfields. Measured to smooth the merge seam across three placed Mountains by **75%** versus a hard Max. | **Ours: measured.** **Gaea: no smooth-min/max node in the fetched list**; whether `Combine` offers smooth modes is **UNVERIFIED**. |
| `layout` | Vector shapes **carrying elevation** — author the terrain's skeleton, optionally embedded into an existing Base. | **Ours: measured.** **Gaea: no Layout node.** (This is World Machine's idea, not Gaea's.) |
| `sculpt` | A masked, non-destructive **merge modifier** — Raise / Lower / Flatten / Smooth blended back by Strength inside a Draw Mask region. Roads and authored regions without leaving the graph. | **Ours: measured.** **Gaea: no equivalent node in the fetched list**; `Draw` is a primitive, not a merge modifier. |
| `transform` (exact mode) | Transforms **fold into upstream generator coordinates** when the cone is procedural, so placement is exact and terrain continues past the tile edge; N stacked transforms compose into one matrix and cost one evaluation. | **Ours: measured** (`filt/transform.js`). **Gaea: UNVERIFIED.** |
| **Physical units throughout** | Metres, °C, °C/km, m/s, mm/°C/day, degrees of repose, m³ — surfaced in the parameter formatters, not just internally. | **Ours: measured** across `params` formatters in 20+ plugins. |

---

## Part 3 — prioritised recommendation

Ranked by (user-visible value) / (implementation cost). Existing BACKLOG item IDs are referenced
rather than re-proposed.

### 1. Surface-detail pack — one node, style enum · **[C]** · *highest ratio in the whole list*

Gaea's Surface family is 21 nodes and ours is 1. It is why Gaea output reads as finished. Almost all
of it is masked high-frequency noise driven by fields we already ship (`d_slope`, `d_curvature`,
`d_wear`, `d_occlusion`) and composited through `stampn`/`maskApply`.

**Do not build 18 nodes.** Build one `surface` plugin with a `style` enum — the pattern `mountain`
already uses (2 landforms × 4 shape families × 5 types in one node). Cover Roughen, Distress,
GroundTexture, RockNoise, Bulbous, Pockmarks, Contours, Grid first. Requires: nothing new. Lands in
**L5 dressing** per D7, but nothing about it is blocked by L1–L4.

### 2. Landform generator pack — Crater, CraterField, Island, Rugged, MountainSide, Volcano · **[C]**

Six archetypes, each a composition of `shape` (radial SDF) + `curve` (profile) + existing noise +
`stampn`. Highest visible value per line of code after #1. `Volcano` needs a cone + crater + flank
noise, verified as "central cone and crater structure". `MountainSide` is `mountain` plus a
directional gradient mask and is the most common hero-shot composition we cannot make.

Requires: nothing new. **Caveat:** these are `gen` nodes, so they must be added to the
transform-commutes table in `params.js` (or deliberately excluded), or `transform`'s exact path will
silently not apply to them.

### 3. Filter completion — Sharpen, Threshold, Dilate/Deflate, Match, SoftClip/Shaper, Flip/Transpose, Fold, DirectionalWarp · **[C]**

Eight to ten cheap nodes closing the widest count gap (Gaea 40 Modify vs our 11 filt). `Sharpen` is
`in − blur(in)`; `Dilate`/`Deflate` reuse the morphology already inside `d_deposits`; `Match` rides
`histEqualizeField`; `Threshold` is genuinely missing (`clampn` clips, it does not threshold).

**Sequence this after W1 (hex-native blur).** Everything unsharp- or morphology-based inherits W1's
correctness, and BACKLOG **C4** records that `boxBlurScalar`/`blurField` are square-separable — adding
blur-derived nodes before W1 multiplies the hex defect across new call sites.

### 4. Graph machinery — subgraphs (`MacroPort`), `Var`, `Math`, `Switch`, `Route`, `Chokepoint`, `Edge` · **[E]**

Not visible in a screenshot; decisive in practice. Without subgraph encapsulation a graph past ~60
nodes stops being editable, and a one-click preset chain in the shape of Gaea's `Wizard`/`Wizard2` is
unbuildable for us. `Var` + `Math` ("evaluates mathematical expressions to generate or modify terrain
data procedurally") is what lets one slider drive twenty nodes.

Requires: subgraph encapsulation in the graph model, a variable scope, and an expression evaluator.
**This is genuinely expensive and it is not in the BACKLOG at all** — it is the largest unscheduled
item this analysis found. Route/Chokepoint/Edge are cheap and can ship first as a down payment.

### 5. Multi-output ports + auxiliary-map registry · **[E]** · **already scheduled — BACKLOG W4**, and D7's L2 gate

Do not re-scope this. It is the prerequisite for a real `Sediments`/`Soil`/`RockMap` (Gaea files
`Sediments` under **Simulate**, we file `d_deposits` under **derived** — a lens error under `27`), and
it is what closes **C2** (both sims compute `flowVelocity` and discard it) and **C3** (erosion computes
its mass budget and discards it). It is also the only route to a `Layers` equivalent for height.

Ranked 5th not because it is low value — it is the highest structural value here — but because #1–#3
deliver visible product without waiting on it, and D7 deliberately puts the 60-node port refactor
after L0/L1 are verified.

### 6. Export as a graph node + profiles · **[K]** node, **[E]** profiles · **already scheduled — BACKLOG W6**

Gaea ships 12 Output nodes; we ship a viewport terminal and a global button (`exportHeightmap`,
`legacy.js:4210`). The immediate cheap win is a per-branch `Export` node reusing the existing writer,
so a graph can emit more than one product. The full answer is W6's export profiles + manifest and
D6's bake-boundary check — **and our variant should not copy Gaea's Unity/Unreal nodes**, because D6
establishes that the exported map set is a function of the target; a profile emitter, not a node per
engine.

### 7. Aeolian pack — DuneSea + Sand · **[K]**, cost already partly paid

We have **zero** arid coverage despite corpus chapter `16` and — measured, by listing the directory —
`reference-impl/dunes.py` and `reference-impl/aeolian.py` already existing in the installed skill.
This is a port, not a derivation. `DuneSea` is a Terrain-family base; `Sand` is Surface-family ripple
detail. Pairs naturally with `d_wind`, which is a differentiator we currently under-use.

### 8. Mass-movement pack — Scree, Debris, Crumble, Slump · **[K]**, cost already partly paid

`reference-impl/runout.py` (Voellmy) exists. Gaea ships four; we ship `thermal`, which moves material
above repose but produces no distinguishable talus deposit. Cliff bases without scree are the most
common "why does this look wrong" in erosion output. Under W4 these should co-update a
`sedimentDepth`/`sandDepth` state map rather than only writing height.

### Ranked below the top 8, but named

- **`Distance` (Euclidean distance transform)** **[K]** — unlocks falloffs and, importantly, the
  **shore distance** that `12:33` requires as an input and that `14`'s registry has no row for.
- **`Angle` (aspect) and `Normals`** **[C]** — two of the cheapest nodes on the list; `08` requires a
  normal map in the handoff and we do not emit one.
- **`Stratify`** **[K]** — the geological finish node `terrace` cannot approximate; `strat_coord` and
  `bed_erodibility` exist in the reference implementation.
- **`GraphicEQ`** **[C]/[K]** — multi-band relief control, buildable as a Laplacian pyramid over
  existing blur.
- **`Seamless`** **[K]** — tileability; prerequisite for `TileInput` and any multi-tile world.
- **`Anastomosis` / braided rivers** **[K]** — `braided.py` exists; note the *Gaea* node is a
  downcutting carve, so matching Gaea here is cheaper than matching reality.
- **`Glacier`** **[E]** — SIA flow. Genuinely absent from the app (BACKLOG §2 states this outright).
  High realism value, high cost, and it is the one entry here where Gaea has a capability we cannot
  approximate at all.

---

## Part 4 — where Gaea's approach CONFLICTS with our doctrine

Copying these would be a regression, not parity. Our variant is named in each case.

### 4.1 `Rivers` carves the heightfield — **do not copy**

**The conflict.** The fetched description of `Rivers` says it generates networks "on any terrain,
whether it can sustain rivers or not", and modifies terrain to guarantee unbroken flow paths. That is
water written into height. `08:126-128` is explicit: *"solid covers (snow, soil, sand) can bake;
**water should not** — bake the sea in and you get the wall you can't swim in."* `27` puts
`waterSurface`/`waterDepth`/`flowVelocity` in the runtime handoff as their own fields.

**Our variant.** Keep `water` as a layer that defines *where fluid is*, and pursue BACKLOG **D5** /
**W5**: authored sources carrying `discharge` (m³/s, seeded into the same accumulation stack as `A`),
with the simulation owning geometry. This is better grounded than Gaea's approach, not merely
different — `03:696-701` is P-tier on it: *"A spring is not a bump in the height field — it is a
source term in the flow field… Stamp a riverbed into the height instead and you get a channel that
ignores the hydrology and stops where you stopped drawing."*

**Where a height write IS legitimate:** drainage conditioning of *bedrock* so the terrain drains at
all. That is our `hydrofix` and Gaea's `HydroFix`, and it is not the same thing as carving a river.
Keep the two nodes distinct and say so in the UI.

### 4.2 The Colorize family and `TextureBaker` — **cap the investment deliberately**

**The conflict.** Gaea ships 13 Colorize nodes plus `TextureBaker`. `27:107` is a strict prohibition:
*"the runtime handoff contains no baked diffuse/colour maps and no predefined materials."* A baked
albedo freezes a decision — this pixel is grass — at one season, one weather state, one art direction.

**Our variant.** `27` explicitly sanctions the satmap/colour emitter as a **preview and review
product** (`09`'s render modes need it), so `satmap`/`satmapblend`/`colormixer`/`colorerosion`/
`weathering` are legitimate exactly as they are. The rule is that **no export profile may depend on
them**. Concretely: add the cheap Colorize nodes if they are wanted for preview (`Tint`, `HSL`,
`RGBSplit`/`RGBMerge`, `CLUTer`, `Splat` — the last is an RGBA→scalar weighted sum, not a splatmap
emitter, per its own page), but spend the *structural* effort on W4's raw-field registry instead.
Ranking Colorize below Surface and Utility in this document is that judgement made explicit.

### 4.3 `Texturizer` / `TextureBase` ship a classification — **ship the drivers**

`Texturizer` "generates terrain texture masks using preset styles". Under the Masking Doctrine a
preset material classification is exactly the decision that belongs to the engine: *"The moment the
tool ships 'grass' instead of 'moisture 0.7, soil 0.4 m, slope 12°, insolation 0.8', the engine can no
longer melt the snow, brown the summer grass, or move the treeline."* Our `d_texture` already sits on
the wrong side of this line (a fixed slope/soil/flow mix), and it is currently harmless only because
it feeds `satmap`, a preview product. **Recommendation:** if we add a Texturizer equivalent, name it a
preview node and keep it out of any export profile; extend `d_slope`/`d_deposits`/`d_flow` as raw
fields instead.

### 4.4 `Sediments` and `Soil` as look-alike derived masks — **implement as STATE, not as a prediction**

Gaea files `Sediments` under **Simulate** and `Soil` under **Derive**. Our `d_deposits` is a
morphological-closing *prediction*. `27`'s co-evolution rule binds here: a process that moves material
must co-update `soilDepth`/`sedimentDepth` **in the same pass**, or the information is destroyed
unrecoverably — which is precisely BACKLOG **C3**. Building a Gaea-shaped derived `Soil` node would
make the app *look* like it has soil while the actual accounting stays discarded. **Recommendation:**
do this only under W4, as state with a lens, not as a new `data` node.

### 4.5 `IceFloe` — **build our own, and mark it F-tier**

BACKLOG §2 already settled this by exhaustive grep of both corpora: `salinity` does not exist as a
field, there is no water-temperature map, and no flow-speed criterion for ice is citable anywhere.
`12:353-359`: *"Sea ice is not terrain, and the first rule is not to make it terrain."* **Our
variant:** `iceThickness` (m, `R32F`) as a transient field riding on `waterSurface`, never entering
`solidTop`, with `iceFree(azimuth, season)` gating fetch. Mark it F/? in our own docs. And note the
recorded trap: an ice rule thresholding `length()` of a *filtered* flow vector grows ice down the
fastest channels at coarse LOD — read a separately-mipped scalar speed channel.

### 4.6 `Trees` / `Shrubs` as Simulate nodes — **UNVERIFIED conflict, flag it**

If Gaea's vegetation nodes write into the heightfield, that conflicts with `07`/`13`, where
vegetation is scatter driven by fields. I did not fetch those pages, so **whether they write height is
UNVERIFIED.** Either way our variant is settled: vegetation is a scatter product over
`moisture`/`temperature`/`soilDepth`/`insolation`, which needs a non-heightfield output port (W4/D7
L2), not a `Trees` node returning a `Float32Array`.

### 4.7 `Mesher`, `Transform3D`, `Meshify` — outside the paradigm, and that is fine

Not a doctrine violation, but worth stating so it does not get scheduled by accident: the heightfield
stack is our source of truth, and a mesh is a *downstream product* of the export contract (W6), not a
node that feeds back into the graph. `Transform3D` on a heightfield is close to meaningless — as
`filt/transform.js` already notes, rotation about anything but the up axis makes the surface
multi-valued.

---

## Appendix — counting method

- **Ours (60):** `grep -h -oE '^\s*type: "[a-z0-9_]+"' src/plugins/*/*.js | sort -u | wc -l`, plus a
  per-directory file count cross-check. Both give 60 and the declared per-category split.
- **Gaea (183):** three independent counts on `docs.gaea.app` that agree after one identified
  exception. `node-map.html` = 182 (182 hyperlinks; 191 `<tr>` − 9 header rows). `search.json` = 198
  `hive == "Node Reference"` entries − 15 non-node pages = 183. `llms-full.txt` = all 183 slugs, zero
  missing. The delta is `TriplanarDisplacement`, which has a live page but no node-map row. Per
  family: Primitive 23, Terrain 14, Modify 41, Surface 21, Simulate 25, Derive 14, Colorize 13,
  Output 12, Utility 20.
- **Mapping (41 covered / 26 partial / 116 absent):** one pass over all 183, each assigned by reading
  our plugin's `desc` and params against the Gaea node name (and, for 24 of them, the fetched page).
  41 + 26 + 116 = 183. ✓
- **Cheap count (~53):** my judgement under the stated criterion, not a measurement. Treat it as an
  estimate with a real error bar; the claim that *roughly half the gap is cheap* is robust, the
  specific 53 is not.
- **Sub-group structure.** Gaea's node map carries a second level below family (e.g. Modify →
  Adjust / Blur / Effect / Profile / Shape / Transform / Utilities / Warp; Simulate → Erosion /
  Scatter / Snow / Vegetation / Water). We have no equivalent grouping in the palette; if the Surface
  and Modify packs above are built, adopting a sub-group level in `CAT` is worth doing at the same
  time, because 60 → ~110 nodes in eight flat categories is not navigable.
