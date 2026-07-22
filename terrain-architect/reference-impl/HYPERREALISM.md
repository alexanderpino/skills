# Toward hyperrealism — what each archetype would need

A research-grounded ledger of what it takes to push the archetype/screen-world tiles from
"recognisable illustrative composition" toward **photoreal**. Compiled from a survey of the terrain
literature and the geomorphology of each landform (sources at the end).

**Honest scope first.** The `reference-impl` is a numpy-only, verified, *illustrative* sandbox at
small tile size. It can move a long way toward realism — colour/materials, real erosion, ambient
occlusion, atmosphere — but true film-grade hyperrealism (Infinigen / Terragen / Houdini class: PBR
surfaces, high-res multi-scale detail, instanced vegetation, path-traced atmosphere) is a separate,
much larger system. This doc separates **the shared render/erosion pipeline** (buys realism for
*every* tile) from **the per-archetype geomorphology** (what makes each one specifically read true),
and gives a staged roadmap.

---

## Part 1 — The shared photoreal pipeline (biggest bang first)

The core lie of grey hillshade: it shows only *shape*, under one hard light, with no colour, no
material, no drainage, no atmosphere. Photoreal terrain stacks four systems — **erosion** (correct
structure), **multi-scale detail**, **materials/colour** (the largest single jump), and **PBR-ish
compositing** (soft light + AO + aerial perspective). Ranked by realism-per-effort:

1. **Materials / splatmap colour** — a slope+altitude splat (rock on steep, soil/grass on flats,
   snow above a *noisy, slope-limited* snow line, sediment in valleys) is the biggest delta. Grey
   reads as "data"; colour reads as "place". Blend masks with `smoothstep`, never hard bands.
2. **Hydraulic droplet erosion** (~**5·N²** droplets; radius 3, capacity 4, erode/deposit ~0.3,
   evaporate 0.01, gravity 4, lifetime 30 — Beyer/Lague defaults). This is what makes terrain look
   *carved by water*: dendritic drainage, V-valleys, ridgelines, sediment fans. Feed its
   **deposition + flow maps back into the splatmap** (sediment vs bedrock, riverbeds).
3. **Thermal / talus erosion** (repose `tan θ ≈ 0.6`, ~**33°**; ~300–1000 cheap local sweeps). Kills
   the "too-steep-everywhere noise" tell and builds scree aprons. A finisher, not a base.
4. **Ambient / sky occlusion**, multiplied under the light (multi-directional line-sweep, ~8–16 azi;
   combine a narrow radius for creases + a wide radius for valleys). Sells depth a single hillshade
   physically cannot.
5. **Sun + sky two-light + soft cast shadows** (horizon line-sweep toward the sun), not hard `N·L`.
   Warm sun, cool hemispheric sky fill so shadows aren't black.
6. **Domain warping + feature-aware roughness** — warp the noise domain (`noise(p+amp·noise(p))`)
   for organic non-blobby ridges; scale fine-octave amplitude by local slope (rough rock, smooth
   sand/sediment).
7. **Aerial perspective + tonemap** — distant/low ground desaturates and lifts toward atmosphere
   blue; finish with a filmic curve and warm-highlight/cool-shadow grade.

Mental model: `final = tonemap( aerial( material × (sun·shadow + skyfill) × AO ) )`.

`reference-impl` already has the ingredients: `erosion_droplet`, `erosion_thermal`, `flow`,
`analysis.derive_materials` / `horizon_ao`, `render.material_rgb`, `noise.domain_warp`.

**Status — Stage 1 is now implemented.** `render.sun_sky_shade` + `render.photoreal` (a pure-numpy
composite: `material × (sun+sky) × AO + rivers + aerial`) and a per-world `PALETTES`/`_rich` path in
`archetypes.py` now drive **both montages** — `archetypes.png` and `screen_worlds.png` render in
colour, not grey hillshade. One composite serves Earth / Mars / Moon / desert / ice / salt: the
palette recolouring the same material splat is the only difference. This was the largest, cheapest
jump; what remains (Stages 2–4) is per-tile geomorphology, itemised below.

## Part 2 — Three cross-cutting principles (from the geomorphology)

These matter *more than any single feature* — they are why a landform reads as real:

- **Break-of-slope is the #1 cue.** Real erosional landforms have sharp transitions — caprock cliff →
  talus, dune crest → slip face, tower → plain, sea cliff → wave-cut platform. Fakes smooth these
  into gradients. Almost every tile below fails here first.
- **Slope-angle discipline.** Loose granular debris caps at **~30–37°** (scree 34–37°, dune slip
  face ~34°, pyroclastic flanks ~33°); rock cliffs stand **near-vertical**; structural/depositional
  flats are **genuinely flat** (playa, mesa top, interdune, fjord sill, mare). Three distinct
  regimes, not one continuous gradient.
- **Process leaves a network / sequence signature.** Glacial = cirques + U-troughs + hanging
  valleys; fluvial canyon = stratified cliff/bench steps; aeolian = *asymmetric oriented* dunes;
  karst = abrupt-based towers; extensional desert = parallel ranges + fans + playa; Moon = r⁻²
  crater size-frequency + a fresh→ghost degradation gradient; Mars = an **overprint age order**
  impacts→fluvial→aeolian→dust. Getting the pattern/sequence right beats the silhouette.

## Part 3 — Per-archetype requirements (must-haves · the tell · our current gap)

| Archetype | Must-have features | The tell a fake gets wrong | Our current gap |
|---|---|---|---|
| **Alpine** | cirques + tarns, arêtes/horns, **U-troughs** (flat floor, steep walls), hanging valleys w/ waterfalls, moraines, scree 34–37° | V-valleys with tributaries joining *at grade* (should be U + hanging) | no cirques/U-profile; blobby, fluvial-only |
| **Canyon** | **cliff-and-bench stair-steps** from hard/soft beds, strata *continuous & horizontal across both rims*, caprock, inner gorge, incised meanders | one uniform smooth V wall | incision good; strata benches too faint, no differential hard/soft |
| **Mesa/tepui** | flat **structural** top under a resistant caprock, near-vertical wall, **sharp break to talus apron**, accordant summit levels | a domed/rounded top; no caprock→talus break | flat top + caprock rim + cliff→**talus break** now via `_butte` ✓; accordant tops next |
| **Erg** | **asymmetric** dunes (gentle windward ~12°, **steep lee slip face ~34°**), oriented by wind; barchan/transverse/linear/star; flat interdunes | symmetric sine-wave ridges | now **asymmetric** stoss/slip-face transverse dunes + flat interdunes ✓; single wind, one dune type |
| **Basin & range** | parallel ranges, **straight range-front fault + triangular facets**, alluvial **fans→bajada→playa** sorting, back-tilted blocks | blobby scattered mountains; no fans/playa | have tilted blocks; missing facets, fans, bajada, true playa |
| **Badlands** | dense rilling, **capped hoodoos** (top-heavy, banded), fins→windows→hoodoos series, knife-edge divides | smooth tapered cones, no banding/cap | good dissection; no discrete capped hoodoos/fins |
| **Tower karst** | towers **springing abruptly from a flat plain** at ~90° with a **basal dissolution notch**; fenglin vs fengcong | tapering footslopes / cones | now sparse near-vertical towers + **basal notch** ✓; fenglin only |
| **Stratovolcano** | **concave-up** profile (gentle base→steep summit), small summit crater, **radial barrancas** | straight-sided constant-slope triangle | cone ok; profile too linear, gullies ok |
| **Caldera** | wide **collapse** depression ≫ vent, steep rim scarps of a *truncated* cone, **resurgent dome / Wizard-Island cones**, lake | a neat funnel atop an intact cone | now has jagged rim + dome ✓; could add rim-wall terraces |
| **Fjord** | drowned **U-trough**, **overdeepened inland + shallow sill at mouth**, hanging valleys w/ waterfalls | uniformly deepening estuary with sloping banks | inlets ok; no sill/overdeepening, no hanging valleys |
| **Sea cliffs** | near-vertical cliff, **wave-cut notch**, **wave-cut platform** (~1–4° seaward), arch→stack→stump, stacks share bedding | stacks "floating" with no platform/notch | coastal retreat ok; no platform/notch/stacks |
| **Lunar cratered** | **saturation** + **r⁻² size-frequency**, fresh→ghost degradation gradient, d/D≈1:5 fresh, simple→complex >15–20 km, ejecta + **herringbone secondaries** | uniform-random equal craters, all fresh | good chaos; add SFD power law + degradation states + secondaries |
| **Lunar maria** | smoothness vs highlands, **wrinkle ridges** (sinuous, ~10s m), sinuous rilles, sparse craters, embayed drowned rims | too much relief / too many craters | smooth ✓; ridge too subtle, no rilles/embayment |
| **Mars** | **overprint order** impacts→fluvial→aeolian→dust: valley networks, outflow+chaos, **inverted channels**, bright static **TARs** vs dark active dunes, dust mantle | features with no age order / no dust drape | have craters+channel; add TARs, inversion, dust mantle, order |
| **Arrakis** *(Wadi Rum)* | **flat-vs-vertical binary**: dead-flat sand valleys meeting sheer **jebels**, 3-layer sandstone, fault-grid straight cliffs, honeycomb weathering, sand aprons | uniform Perlin bumpiness | now jebels+sand ✓; add fault-straight edges, layer banding |
| **Monument Valley** | **3-layer butte** (shale slope base / sandstone cliff / caprock), talus apron, mesa→butte→spire series, isolated on a plain | cookie-cutter cylinders / gears | caprock butte (top→cliff→**talus break**) + mesa→butte→spire series ✓; 3-layer banding next |
| **Zhangjiajie/Pandora** | >3000 **angular fracture-bounded** quartz-sandstone columns, joint-aligned corridors, vegetated tops | rounded limestone-style cones | now **sheer near-vertical** columns ✓; make joint-aligned/angular, vegetate tops |
| **Ha Long/Skull Is.** | drowned towers straight from the sea, **waterline notch** undercut, h/w up to ~6, fenglin+fengcong | towers with beaches / no notch | now sparse sheer **high-h/w** drowned towers ✓; add waterline notch |
| **Uyuni/Crait** | metre-scale **hexagonal** salt polygons w/ raised ridges, dead-flat, brine mirror (wet look) | raw straight-edged Voronoi | domain-warped cracks ✓; make hexagonal + raised ridges |
| **Hoth/Norway** | U-troughs drowned/iced, **nunataks** (jagged rock through ice), **roches moutonnées** (stoss/lee asymmetry), hanging valleys | perfect-circle "bullet-hole" rock spots | irregular nunataks ✓; add roches moutonnées, U-troughs |
| **Miller's world** | shoreless shallow sea over a **braided sandur**, one mountainous **irregular** wave | a straight gradient-line wave | wandering wave ✓; add braided channels under the water |

## Part 4 — Staged roadmap (and where the sandbox honestly tops out)

1. **Shared realistic render** (buys realism for *all* tiles at once): a `render`-side composite of
   **material colour × (sun+sky) × AO + rivers + aerial haze**. This is the largest, cheapest win —
   **done**: `render.photoreal` + per-world palettes now drive both montages (grey → colour). Next
   sub-step here is resolution: render the montage tiles at 2–4× for finer carved detail.
2. **Erosion on every fluvial/hillslope tile**: droplet (~5·N²) + interleaved thermal (33°), and
   feed deposition/flow into the splatmap. Fixes "blobby" alpine, canyon, badlands, mars.
3. **Break-of-slope + slope-discipline per archetype** (*in progress*): the highest-impact set is
   **done** — caprock top→cliff→**talus break** (`_butte`: mesa, Monument Valley), dune **slip-face
   asymmetry** (erg), **abrupt near-vertical tower bases + notch** (tower karst, Pandora, Skull
   Island). Remaining: canyon differential hard/soft benches, wave-cut platform+notch (coast),
   sill/overdeepening (fjord), badlands capped hoodoos — the rest of the per-tile work in Part 3.
4. **Sequence/statistics** where they define the look: r⁻² crater SFD + degradation classes (Moon),
   the impacts→fluvial→aeolian→dust overprint (Mars).
5. **Beyond the sandbox** (would need a new system, not numpy tiles): true PBR surfaces, instanced
   vegetation/rock scatter, high-res detail transfer, and path-traced atmosphere — the Infinigen /
   Terragen tier. Worth naming as the ceiling so "hyperreal" stays honest.

## Sources

Pipeline & rendering: Galin et al., *A Review of Digital Terrain Modeling*, CGF 2019; Génévaux et
al., *Terrain from hydrology*, TOG 2013; Cordonnier et al., *Tectonic uplift + fluvial erosion*;
Raistrick et al., *Infinigen*, CVPR 2023 (princeton-vl/infinigen); Beyer/Lague droplet params
(jobtalle.com, nickmcd.me); line-sweep AO/shadows (rreusser, karim.naaji.fr); Frostbite procedural
shader splatting; World Machine / Gaea / Houdini heightfield docs. Geomorphology: NPS & USGS
(glacial U-valleys/fjords, Basin & Range, Crater Lake), OpenTextBC Physical Geology, AntarcticGlaciers
(cirques, roches moutonnées), NPS Grand Canyon stratigraphy, Britannica (barchan, coastal erosion),
Waltham (fenglin/fengcong), UNESCO (Zhangjiajie, Ha Long), Riedel 2020 & Krüger 2018 (lunar crater
degradation & simple→complex), TARs morphology (Balme et al.), Salar de Uyuni & Wadi Rum & Monument
Valley geology guides. Full URLs are in the research transcripts backing this doc.
