# Algorithm Index

The skill's map of its own knowledge. Every row carries a **provenance tier**, because the
failure mode this file exists to prevent is *confident fabrication of a citation*.

## Provenance tiers

| Tier | Meaning | How to talk about it |
|---|---|---|
| **P** | **Paper.** Peer-reviewed source, verified to actually contain the algorithm attributed to it. | Cite it directly. |
| **F** | **Folklore.** Universal practice with no canonical paper. A blog post, a thesis, a repo, or nothing. | Say "no canonical paper; standard practice is…". Naming Quilez or a repo is fine — just don't dress it as peer review. |
| **L** | **Landform, not algorithm.** An *outcome*. Produced by composing other nodes. | "There is no X algorithm. X emerges from A + B + C." Then give the recipe. |
| **N** | **Node, not algorithm.** A UI surface over one or more operators, usually a tool's branding. | Name the underlying algorithm. |
| **?** | **Claimed but unverified.** Plausible, commonly repeated, not confirmed. | **Do not cite.** Say it needs checking, and search if you can. |

**The rule that makes this work: never upgrade a tier to satisfy a question.** If someone asks
for the paper on sea-stack formation, the correct answer is that there isn't one — not a
plausible-looking guess. An L-tier row answered with a citation is the exact defect this skill
was built to stop, and it is the defect in most terrain-algorithm reference tables in
circulation.

If a question lands on `?`, say so and offer to search. Being usefully uncertain beats being
confidently wrong; a fabricated citation costs the reader a day.

## Verification status

The tier says *what kind* of source a claim has; this says *how far it has been checked*. They are
not the same — the gap between "the paper exists" and "the number is right" is where errors hide.

- **Citations** — author, venue, volume, and pages verified against primary sources for the
  references added and audited to date. Never add a citation you have not looked up.
- **Numbers & equations** — the load-bearing formulae and constants have been verified against
  primary sources: the SIA velocity and `H^(n+2)` flux-diffusivity (`12`), Glen's `A` (Cuffey &
  Paterson 2010), Shields `θc ≈ 0.045` (`04`), Bagnold's `u*³` law and threshold (`05`), Werner and
  repose-angle values (`05`), Freeman's MFD `p = 1.1` (`03`), Leopold & Maddock's *downstream*
  hydraulic-geometry exponents `w∝Q^0.5, d∝Q^0.4` (`03`), stream-power `m/n ≈ 0.5` (`04`), Hulme's
  lava thickness and levée relations (`19`), the crater depth/diameter `≈0.2`, rim `≈0.04D`,
  simple↔complex transition and its `~1/g` scaling (`11`), basalt eruption/solidus temperatures
  (`19`), environmental/adiabatic lapse rates (`13`), and the Wentworth / USDA grain-and-soil
  boundaries (`04`, `18`). Every one checked in this pass held (a few gained a precision fix or a
  clarified label). **The remaining parameter-table values are order-of-magnitude starting points**
  — tune them against each family's verification checks (`09`) and re-check any figure against its
  source before publication-critical use.
- **Dimensional consistency** — the load-bearing equations have been unit-checked and are
  dimensionally sound (stream power `K·A^m·S^n` → m/yr with `[K]=yr⁻¹` at m=½; Shields → Pa; Bagnold
  `q` → kg/m/s; SIA velocity → m/s and flux-diffusivity → m²/s; lava cooling → K). The check *found*
  and fixed a real imprecision — the lava Bingham flux is per-unit-width `[m²/s]`, so it needs the
  explicit flux→thickness conversion `ΔL = q·Δt/cellSize` (`19`), exactly as the pipe model does
  (`04`). Units analysis is a code-free error detector and is worth running on any equation added.

This is deliberately honest, not reassuring. Errors *have* surfaced and been fixed by exactly this
process — a reversed crater transition, a Braun/Gain author swap, an `H⁴`-vs-`H⁵` flux slip — so
assume more remain until the pseudocode is implemented and the numbers independently reviewed. The
skill is most useful when the reader knows which claims are anchored and which are informed
estimates.

**Runnable reference implementations** of the core sims — droplet/pipe/thermal/stream-power erosion,
flow routing & depression fill, hillslope diffusion, dunes, isostatic flexure, mass-consistent wind
(Sherman), Voellmy runout, and the analytic families (tephra, age–depth, PDC, avulsion) — live in
`reference-impl/` (numpy, pytest-verified
against the `09` checks, with optional RichDEM/pysheds cross-validation for flow operations). See its README for the
module → oracle → library map. This is how the pseudocode becomes *executable and checkable* rather
than merely asserted.

---

## 1. Noise & procedural synthesis → `01-noise.md`

| Algorithm | Tier | Source |
|---|---|---|
| Value noise | F | No canonical paper |
| Perlin noise | P | Perlin 1985, *An Image Synthesizer*, SIGGRAPH |
| Improved Perlin | P | Perlin 2002, *Improving Noise*, ACM TOG 21(3) |
| Simplex noise | P | Perlin 2001/2002; **Gustavson 2005** is the readable derivation, not the origin |
| OpenSimplex2 | F | KdotJPG, public-domain repo. No paper. |
| Worley noise | P | Worley 1996, *A Cellular Texture Basis Function*, SIGGRAPH |
| Voronoi | P | Voronoi 1908 — the **tessellation**, a maths paper. Not a noise paper. Don't cite it for a noise node. |
| Gabor noise | P | Lagae et al. 2009, *Procedural Noise using Sparse Gabor Convolution*, ACM TOG 28(3) |
| Wavelet noise | P | Cook & DeRose 2005, *Wavelet Noise*, ACM TOG 24(3) |
| Sparse convolution noise | P | Lewis 1989, *Algorithms for Solid Noise Synthesis*, SIGGRAPH |
| Spectral synthesis | P | Voss, in Peitgen & Saupe (eds.) 1988, *The Science of Fractal Images* |
| Midpoint displacement / diamond-square | P | Fournier, Fussell & Carpenter 1982, CACM 25(6) |
| FBM | P | Mandelbrot & Van Ness 1968; Mandelbrot 1982, *The Fractal Geometry of Nature* |
| Ridged multifractal | P | Musgrave 1993 (thesis); Ebert et al., *Texturing & Modeling*, Musgrave's chapters |
| Hybrid multifractal | P | Musgrave, as above |
| Heterogeneous multifractal | P | Musgrave, as above |
| Domain warping | F | Quilez, iquilezles.org. Widely used, no paper. |
| Vector warping | F | No canonical paper |
| Curl noise | P | Bridson et al. 2007, *Curl-Noise for Procedural Fluid Flow*, SIGGRAPH |
| Noise survey (read this) | P | Lagae et al. 2010, *A Survey of Procedural Noise Functions*, CGF 29(8) |

**Learned / example-based** — verify before citing; this area moves fast and post-dates much
of what's reliable here.

| Algorithm | Tier | Source |
|---|---|---|
| Example-based terrain synthesis | P | Zhou, Sun, Turk & Rehg 2007, *Terrain Synthesis from Digital Elevation Models*, IEEE TVCG 13(4) |
| Sketch/example authoring with cGANs | P | Guérin et al. 2017, *Interactive Example-Based Terrain Authoring with Conditional GANs*, ACM TOG 36(6) |
| Terrain amplification | P | Guérin et al. 2017, as above |
| Diffusion-based terrain generation | P | **Was `?`, now real:** Lochner et al. 2023, *Interactive Authoring of Terrain using Diffusion Models*, CGF 42(7); Hu et al. 2024, *Terrain Diffusion Network*, AAAI 38(11) |
| GAN terrain generation & amplification | P | Guérin et al. 2017 (cGAN authoring/amplification); Zhao et al. 2019, *Multi-theme Generative Adversarial Terrain Amplification* (GATA), ACM TOG 38(6) |
| DEM super-resolution (neural) | P | Demiray, Sit & Demir 2021, *D-SRGAN*, SN Computer Science 2(1) — can hallucinate high-frequency detail; verify against ground truth |
| Neural-implicit terrain (representation) | P | Feng, Xu & De Floriani 2024, *ImplicitTerrain*, CVPR Workshop — analysis/compression, **not** a generator |
| Neural terrain authoring — the moving frontier | ? | Sketch/style tools (StyleDEM), latent joint geometry+texture (TerraFusion), GNN sketching — real work but metadata-incomplete or preprint-only; **verify venue & authors before citing** (`SKILL.md` frontier note) |

## 2. Macro & geological formation → `02-macro-tectonics.md`, `11-geological.md`

| Algorithm | Tier | Source |
|---|---|---|
| Tectonic uplift + fluvial erosion | P | **Cordonnier et al. 2016**, CGF 35(2). *This is the "2015 tectonics" paper and the "2016 stream power" paper — one paper, not two.* |
| Ecosystem + erosion authoring | P | Cordonnier et al. 2017, ACM TOG 36(4) |
| Plate partitioning / boundary classification | F | Voronoi + velocity vectors. No canonical paper for the graphics version. |
| Plate tectonics on a sphere (Euler-pole rotation) | P | McKenzie & Parker 1967 (*tectonics on a sphere*, Nature 216); Morgan 1968 — rigid rotation about an Euler pole (`25`) |
| Procedural whole-planet tectonics | P | Cortial, Peytavie, Galin & Guérin 2019, *Procedural Tectonic Planets*, CGF 38(2), Eurographics (`25`) |
| Fault displacement / fault networks | F | No canonical paper |
| Folding | F | Coordinate warp of the stratum field. No paper. |
| Stratification / sedimentary layering | P | Beneš & Forsbach 2001, *Layered Data Representation for Visual Simulation of Terrain Erosion*, SCCG |
| Layered terrain with overhangs/arches | P | Peytavie et al. 2009, *Arches: a Framework for Modeling Complex Terrains*, CGF 28(2) |
| Cave networks / karst dissolution | P | Paris et al. 2021, *Synthesizing Geologically Coherent Cave Networks*, CGF |
| Lava flow (animation) | P | Stora et al. 1999, *Animating Lava Flows*, Graphics Interface |
| Lava flow morphology (levées, snouts, thickness) | P | Hulme 1974, GJRAS 39(2) — Bingham yield-stress rheology (`11`) |
| Pahoehoe / ʻaʻā / block lava | P | Macdonald 1953, American Journal of Science 251(3) — surface-texture classification (`11`, `18`) |
| Volcanic cones, calderas, craters, crater fields | F | Primitive + noise + erosion. No paper. |
| Rock hardness layers / lithology | F | A material field feeding erodibility `K`. See Št'ava 2008 for the layered coupling. |
| Soil / regolith production function | P | Heimsath, Dietrich, Nishiizumi & Finkel 1997, Nature 388 — exponential decline with soil depth (`11`) |
| Volcano edifice classification & dimensions | P | Pike & Clow 1981, USGS OFR 81-1038 — shield/strato/cinder/caldera (`11`) |
| Impact crater morphology (simple/complex, ejecta) | P | Melosh 1989; Pike 1977 — depth/diameter, central-peak transition (`11`) |
| Feature-primitive terrain authoring | P | Génevaux et al. 2015, CGF 34(6) — construction tree of peaks/ridges/rivers/cliffs (`13`) |
| Example-based world / element authoring | P | Emilien et al. 2015, *WorldBrush*, ACM TOG 34(4) (`13`) |
| Digital terrain modelling — the survey | P | Galin et al. 2019, CGF 38(2). Read first when architecting a whole world (`13`) |
| Isostasy — Airy (local) & flexural (elastic plate) | P | Turcotte & Schubert 2014; Watts 2001 — `D∇⁴w+Δρgw=q`; spectral solve (`02`) |
| Glacial isostatic adjustment (postglacial rebound) | P | Peltier 1974; Peltier 2004 — viscous mantle relaxation, raised shorelines (`02`, `12`) |
| Erosional isostasy (unloading rebound) | P | Molnar & England 1990 — peaks rise as valleys incise; the chicken-or-egg caution (`02`) |
| Tephra fallout (exponential thinning; advection–diffusion) | P | Pyle 1989; Suzuki 1983; Armienti et al. 1988; Bonadonna et al. 2005 (TEPHRA2) (`11`) |
| Pyroclastic density currents (energy cone; granular flow) | P | Sheridan 1979; Malin & Sheridan 1982; Patra et al. 2005 (TITAN2D); Dade & Huppert 1996 (`11`) |
| Caldera collapse (piston subsidence) | P | Roche & Druitt 2001; Geshi et al. 2002; Cole et al. 2005; Acocella 2007 (`11`) |
| Duricrust (calcrete / silcrete / ferricrete) as a resistant cap | material/`K` | Goudie 1973; Nash & McLaren 2007 — a low-`K` horizon (`11`) |
| Relief inversion (inverted topography / channels) | L | Pain & Ollier 1995 — valley-fill cap + differential erosion (`11`) |
| Reservoir sedimentation (trap efficiency) | P | Brune 1953; Morris & Fan 1998 — delta + drawdown benches (`20`, `12`) |
| Dam-break flood wave | P | Ritter 1892 — dry-bed shallow-water, front at `2√(g·h₀)` (`20`) |
| Anthropogeomorphology (humans as geomorphic agent) | P | Hooke 2000; Haff 2010; Tarolli & Sofia 2016; Goudie, *The Human Impact* (`20`) |

**L-tier — landforms, not algorithms.** No implementation and no paper exists for these. They
are compositions. The recipe is the answer. This table is *one landform each*; for whole
recognisable places (the Alps, the Grand Canyon, a Namib erg, Niagara & Victoria Falls) assembled
end-to-end as regime settings over the Legal Order, see the **archetype blueprints** in
`20-archetypes.md`.

| Landform | Composition |
|---|---|
| Continents, islands | Low-freq noise + shelf remap + sea level after erosion (`02`) |
| Archipelagos | Islands + Poisson-distributed centres (`07`) |
| Ring islands, atolls | Volcanic edifice + subsidence + photic-zone coral accretion + wave exposure — Darwin's subsidence sequence (`12`) |
| Mountain ranges, ridge networks | Uplift field + stream power (`02`, `04`) — **not** ridged noise |
| Valley networks | Flow routing + fluvial incision (`03`, `04`) |
| Waterfalls | Knickpoint pinned on a hard bed, base-level fall, or hanging valley (`04`, `11`, `12`) |
| Mountain lakes (tarn, paternoster, ribbon) | Glacial / landslide / crater basin, left unfilled (`03`, `12`) |
| Oxbow lakes, meander scrolls, floodplains | Meander migration + neck cutoff on a low-slope reach (`03`) |
| Gravel bars, pebble beaches, boulder gardens | Bedload deposition where competence drops; scatter clasts by grain size (`04`, `07`) |
| Plateaus, mesas, buttes | Hard caprock layer in `K` + fluvial erosion (`11`) |
| Canyons, badlands | High uplift + high `K` contrast + stream power (`04`, `11`) |
| Entrenched / incised meanders, river gorges | Meander belt (`03`) + uplift (`02`) + bedrock incision (`04`); in karst → the Ardèche / Pont d'Arc (`11`) — full blueprint in `20` |
| Fjords | Glacial erosion + sea-level rise (`12`) |
| Deltas, alluvial fans | Deposition-dominant hydraulic erosion at a base level (`04`, `12`) |
| Coastal cliffs, sea stacks, coastal arches, coastal caves | Wave erosion band + hardness variation (`12`) |
| Spits, tombolos, barrier islands, bay bars | Longshore drift + deposition + sheltering (`12`) |
| Marine terraces | Wave-cut platform loop across a sea-level / uplift history (`12`) |
| Rias (drowned valleys) | Fluvial valley network + sea-level rise (`03`, `12`) |
| Natural arches, hoodoos | Differential erosion of layered rock; needs a **non-heightfield representation** (`11`) |
| Karst terrain | Dissolution of a soluble layer; caves need volume (`11`) |
| Tower / cone karst (fenglin, fengcong) | Dissolution + differential vertical lowering to a base level (`11`) |
| Lava fields, lava lakes, lava worlds (Mustafar) | Stacked levéed flows; ponded fluid lava in closed basins; fluid layer = lava (`08`, `11`, `13`) |
| Agricultural terraces (rice paddy, dry-stone) — *anthropogenic* | Contour level-sets + cut-and-fill benches + per-bench water layer; the file's first human-made landform, blueprint in `20` |
| Field-mosaic farmland (large grids, small bocage) — *anthropogenic* | Pattern+material overprint on gentle terrain; lithology→soil→land use (terroir: vines on limestone vs sandstone); blueprint in `20` |
| Miniature-scale world (insect / Smurf / Bikini Bottom) | Scale regime, not a landform: surface tension > gravity, grains as boulders, biology as relief, rain-splash micro-erosion; blueprint in `20` |
| Fissure eruptions, flood basalts (traps) | Line-source flows along a rift/fault (`02`) + stacking → basalt plateau; dissection → stepped traps (`11`) |
| Geothermal field (geysers, sinter, hot springs) | Fracture-gated vents + sinter/travertine *deposition* + temperature-zoned microbial palette — blueprint in `20` |
| Sandstone pillar forest (Zhangjiajie, Meteora) | Resistant strata + orthogonal joints as process mask + joint-gated incision — *not* karst; blueprint in `20` |
| River terraces (strath / fill) | Alternating lateral planation and incision across a base-level / climate / sediment history (`03`) |
| Delta lobes (stacked, switching) | Repeated avulsion near the delta apex across the delta cycle (`03`) |
| Guyot (drowned flat-topped seamount) | Volcanic edifice + wave truncation + age–depth subsidence past the photic zone (`11`, `12`) |
| Seamount / hotspot chain | Age-progressive edifices (`11`) subsiding along a plate-motion line over a fixed hotspot (`02`, `12`) |
| Submarine canyon, turbidite fan | Turbidity-current erosion then deposition below wave base (`12`) |
| Channeled scabland, coulees, giant current ripples | Extreme-discharge megaflood over jointed bedrock — outburst source (`12`) routed by `03`/`04` |
| Inverted relief (inverted channels, capped former valleys) | Resistant valley-fill cap (duricrust / lava / cemented gravel) + differential erosion (`11`) |
| Reservoir delta & bathtub shorelines — *anthropogenic* | Dam traps the inflow load (Brune) → head delta + horizontal drawdown benches (`20`) |
| Mine benches, spoil heaps, valley fills — *anthropogenic* | Cut to design benches; waste piled to the repose angle; drainage buried (`20`, `05`) |
| Engineered ground (grading, levees, canals) — *anthropogenic* | Cut-and-fill to a design surface; prisms extruded along polylines (`20`, `10`) |

## 3. Composition & filtering → `10-primitives-ops-filters.md`

| Algorithm | Tier | Source |
|---|---|---|
| Add/Sub/Mul/Div/Min/Max/Lerp/Clamp/Invert/Threshold/Switch | F | Operators. No papers. Real gotchas — see `10`. |
| Smooth min / max | F | Quilez. No paper. |
| Normalise | F | **Reviewed as a defect by default** — destroys world units, breaks tiling (`10`) |
| Histogram equalisation | F | Standard image processing |
| Curve remapping / quantisation | F | — |
| Box / Gaussian blur | F | Separable. Wrong default for terrain (`10`). |
| Median filter | F | Tukey 1977, *Exploratory Data Analysis* — the book, not an algorithm paper |
| Bilateral filter | P | Tomasi & Manduchi 1998, *Bilateral Filtering for Gray and Color Images*, ICCV |
| Guided filter | P | He, Sun & Tang 2010, *Guided Image Filtering*, ECCV |
| Anisotropic diffusion | P | Perona & Malik 1990, IEEE PAMI 12(7) |
| Morphological dilation/erosion/opening/closing | P | Serra 1982, *Image Analysis and Mathematical Morphology* |
| Distance transform | P | Felzenszwalb & Huttenlocher 2012, *Distance Transforms of Sampled Functions*, Theory of Computing 8; also Danielsson 1980, Meijster 2000 |
| Signed distance fields | P | Frisken et al. 2000, *Adaptively Sampled Distance Fields*, SIGGRAPH |
| Laplacian / edge detection / band-pass | F | Standard image processing |
| Bicubic / Lanczos reconstruction | F | Standard signal processing |
| Twist / Bend / Shear / Fold | F | Coordinate warps. No papers. (`10`) |

## 4. Hydrology → `03-flow-routing.md`

| Algorithm | Tier | Source |
|---|---|---|
| D8 flow routing | P | O'Callaghan & Mark 1984, CVGIP 28(3) |
| D∞ flow routing | P | Tarboton 1997, Water Resources Research 33(2) |
| MFD | P | **Freeman 1991**, Computers & Geosciences 17(3) — `p = 1.1` |
| MFD (contour-length variant) | P | Quinn et al. 1991, Hydrological Processes 5(1) — `p = 1`. **Not the same as Freeman.** |
| Priority-Flood / depression filling | P | Barnes, Lehman & Mulla 2014, Computers & Geosciences 62 |
| Depression filling (alternative) | P | Planchon & Darboux 2002, Catena 46(2–3) |
| Depression breaching / hybrid | P | Lindsay 2016, Hydrological Processes 30(6) |
| Lake graph / minima contraction in-loop | P | Cordonnier, Bovy & Braun 2019; coupled terrain application in Cordonnier et al. 2016 |
| O(N) stack ordering | P | Braun & Willett 2013, Geomorphology 180–181 |
| Stream ordering | P | Strahler 1957, Trans. AGU 38(6); Horton 1945 |
| Flow accumulation / drainage area / watershed labelling | P | Barnes et al. 2014 (labelling); accumulation itself is F |
| Topographic wetness index | P | Beven & Kirkby 1979, Hydrological Sciences Bulletin 24(1) |
| River meandering, bank erosion, oxbow cutoff | P | Ikeda, Parker & Sawai 1981 (bend theory — curvature-driven migration); Howard & Knutson 1984 (`03`) |
| Channel patterns — braided / meandering / straight | P | Leopold & Wolman 1957, USGS Professional Paper 282-B (`03`) |
| River widening / depth estimation | F | Hydraulic geometry scaling (`w ∝ Q^0.5`, Leopold & Maddock 1953) |
| Channel-reach morphology (cascade / step-pool / pool-riffle) | P | Montgomery & Buffington 1997, GSA Bulletin 109(5) (`03`) |
| Hydrology-based terrain (river network first) | P | Génevaux et al. 2013, ACM TOG 32(4), SIGGRAPH '13 (`03`) |
| Water sources & discharge routing (`Q` vs area) | P | Springs / inflows as source terms (Št'ava 2008); route `Q`, stream power on `Q^m` (`03`, `04`) |
| River terraces (strath / fill; cover-limited incision) | P | Hancock & Anderson 2002 (numerical model); Bull 1990, 1991; Merritts, Vincent & Wohl 1994; Pazzaglia & Brandon 2001; autogenic caveat Limaye & Lamb 2016 (`03`) |
| River avulsion & superelevation criterion | P | Slingerland & Smith 2004; Mohrig et al. 2000; Jerolmack & Mohrig 2007; cellular Jerolmack & Paola 2007; 3-D stochastic Mackey & Bridge 1995 (`03`) |
| Delta-lobe switching (the delta cycle) | L | Coleman 1988; Roberts 1997 — a composition over repeated avulsion (`03`) |
| Glacial outburst flood (jökulhlaup) / megaflood | P | Nye 1976; Clarke 1982, 2003; Walder & Costa 1996; Björnsson 2003; Baker 1973; Bretz 1923, 1969 (`12`, `03`/`04`) |
| Flood fill / sea level | F | — |

## 5. Erosion → `04`, `05`, `12`

| Algorithm | Tier | Source |
|---|---|---|
| Virtual-pipe hydraulic erosion | P | **Mei, Decaudin & Hu 2007** — *this is the pipe/grid model, NOT particle*; the pipe *abstraction* is older (O'Brien & Hodgins 1995, splashing fluids) — Mei makes it an erosion model |
| Pipe + slippage + layers | P | **Št'ava et al. 2008** — *also a pipe model; an extension of Mei, not a different family* |
| Droplet / particle hydraulic erosion | F | **Beyer 2015**, TU München bachelor thesis, after Musgrave et al. 1989. **No canonical paper.** Popularised by Sebastian Lague. |
| Grid hydraulic erosion (origin) | P | Musgrave, Kolb & Mace 1989, SIGGRAPH |
| Stream-power erosion | P | **Braun & Willett 2013** (the O(N) implicit solver — *the paper that matters*) + Cordonnier et al. 2016 (the terrain application) |
| Knickpoint / waterfall retreat | P | Whipple & Tucker 1999; Crosby & Whipple 2006; Berlin & Anderson 2007. **No graphics "waterfall" algorithm** — it's a knickpoint (`04`). |
| Bedrock river incision (saltation–abrasion) | P | Sklar & Dietrich 2004; Whipple 2004 — the physics under stream power in steep channels (`03`, `04`) |
| Grain-size classification (Wentworth φ scale) | P | Wentworth 1922; Udden 1914 (`04`) |
| Incipient motion / critical shear (which grains move) | P | Shields 1936 (`04`); wind analogue = Bagnold threshold (`05`) |
| Bedload transport (gravel / pebbles) | P | Meyer-Peter & Müller 1948; Parker 1990 (gravel-bed, surface-based) (`04`) |
| Downstream fining (boulders → pebbles → sand) | P | Sternberg 1875, `D = D0·e^(−αx)` — abrasion + selective sorting (`04`) |
| Shallow-water erosion | P | Beneš et al. 2006, *Hydraulic Erosion*, CAVW 17(2) |
| Thermal erosion / talus-angle | P | Musgrave et al. 1989 |
| Talus fast approximation | P | Olsen 2004, tech report, Univ. of Southern Denmark |
| Wind erosion physics | P | Bagnold 1941, *The Physics of Blown Sand and Desert Dunes* — physics, **not implementable as written** |
| Dune formation (implementable) | P | **Werner 1995**, Geology 23(12) — the slab CA. Under-cited relative to usefulness. |
| Glacier flow & erosion | P | Argudo et al. 2020, *Simulation, Modeling and Authoring of Glaciers*, ACM TOG 39(6) |
| Snow / avalanche | P | Cordonnier et al. 2018, *Interactive Generation of Time-evolving, Snow-Covered Landscapes with Avalanches*, CGF 37(2) |
| Coastal erosion / cliff retreat | F | No canonical graphics paper. Coastal engineering: Bruun 1962. **In practice a look, not a simulation** (`12`). |
| Longshore transport | F | CERC formula; measured basis Komar & Inman 1970 (coastal engineering, not graphics). Drives spits/tombolos/barriers (`12`) |
| Marine terrace / wave-cut platform | F | Coastal notch loop across a sea-level/uplift history (`12`). A look, not a sim. |
| Lacustrine (lake) shore erosion / lake terraces | F | The coastal loop at lake level; lake-level history → shoreline terraces. Gilbert 1890 (Lake Bonneville) (`12`) |
| Gilbert (lacustrine) delta | P | Gilbert 1890 — topset/foreset/bottomset delta prograding into standing water (`12`) |
| Shoreface / submarine equilibrium profile | F | Dean 1991 equilibrium profile (`depth ∝ dist^⅔`), coastal engineering — author, don't erode (`12`) |
| Tides / intertidal zone / tidal flats | F | Authored oscillation of the water plane; astronomy, a look. Water is a dynamic layer (`08`, `12`) |
| Seafloor age–depth subsidence (ridge → abyssal plain) | P | Parsons & Sclater 1977 (√age half-space); Stein & Stein 1992 (GDH1 plate model) (`12`) |
| Hotspot track / seamount / guyot | P (age progression) / P-hypothesis (plume) | Wilson 1963; Morgan 1971; Hess 1946 (guyot truncation) (`11`, `12`) |
| Turbidity currents (self-accelerating; layer-averaged) | P | Parker, Fukushima & Pantin 1986; Middleton 1993; Meiburg & Kneller 2010; Bouma 1962 (sequence) (`12`) |
| Shallow landslide susceptibility (wetness-coupled) | P | **Montgomery & Dietrich 1994**, WRR 30 — the SHALSTAB model; steep + convergent + wet fails (`05`) |
| Debris flows | P | Iverson 1997, Rev. Geophys. 35(3) — the physics, **not implementable as written** (like Bagnold); terrain realisation is F (`05`) |
| Landslide runout / rockfall / slump (terrain realisation) | F | Scar + steepest-descent runout + thermal relaxation — no canonical graphics paper (`05`) |
| Runout stop rules (angle of reach; Voellmy friction) | P | Corominas 1996, Can. Geotech. J. 33(2) — `L = H/tan(α)`, volume-dependent; Voellmy 1955 (`05`) |
| Soil creep | P | = hillslope diffusion, `D·∇²h`. See Culling 1960, *Analytical Theory of Erosion*, J. Geology 68 |

## 6. Terrain analysis → `06-analysis-masks.md`

| Algorithm | Tier | Source |
|---|---|---|
| Slope / aspect | P | Horn 1981, Proc. IEEE 69(1) |
| Curvature (profile, plan) | P | Zevenbergen & Thorne 1987, ESPL 12(1) |
| Mean / Gaussian curvature | P | Differential geometry — no terrain-specific paper needed |
| Laplacian, convexity, concavity | F | — |
| Selectors — masks from height/slope/aspect/curvature | F | Threshold + smoothstep over an analysis field → reusable `MaskField` (`06`) |
| Horizon angle / occlusion | P | **Timonen & Westerholm 2010**, *Scalable Height Field Self-Shadowing*, CGF 29(2) — O(1)/cell sweep |
| HBAO | P | Bavoil et al. 2008, SIGGRAPH talks. **Screen-space weighting; not the correct integral for a baked terrain AO map** (`06`) |
| Sky-view factor | P | Zakšek, Oštir & Kokalj 2011, Remote Sensing 3(2) |
| Terrain ruggedness index | P | Riley, DeGloria & Elliot 1999, Intermountain J. Sciences 5 |
| Hypsometric (area–altitude) curve | P | Strahler 1952, *Hypsometric (Area-Altitude) Analysis of Erosional Topography*, GSA Bulletin 63 — the maturity diagnostic (`09`, `20`) |
| Topographic position index | F | Weiss 2001 (ESRI poster) — widely used, not peer-reviewed |
| Ridge / valley / peak / pit / saddle detection | F | Morse theory in principle; in practice curvature thresholds |
| Prominence / isolation | F | Definitions from mountaineering, computed by flood fill |
| Roughness, local relief | F | — |

## 7. Population → `07-scatter.md`

| Algorithm | Tier | Source |
|---|---|---|
| Poisson-disk sampling | P | **Bridson 2007**, SIGGRAPH sketches. Two pages. |
| Best-candidate | P | Mitchell 1991, SIGGRAPH |
| Blue-noise / void-and-cluster tiles | P | Ulichney 1993, SPIE 1913 |
| Sample elimination | P | Yuksel 2015, CGF 34(2) |
| Maximal Poisson-disk (parallel) | P | Ebeida et al. 2011, ACM TOG 30(4) |
| Parallel Poisson-disk | P | Wei 2008, ACM TOG 27(3) |
| Jittered / stratified sampling | F | — |
| Clustered / parent-child point processes | P | Neyman–Scott / Matérn cluster processes (spatial statistics) |
| Ecosystem simulation | P | **Deussen et al. 1998**, *Realistic Modeling and Rendering of Plant Ecosystems*, SIGGRAPH |
| Plant community distributions | P | Lane & Prusinkiewicz 2002, Graphics Interface |
| Multi-scale plant ecosystems | P | Makowski et al. 2019, ACM TOG 38(4) |
| Plants interacting with environment | P | Měch & Prusinkiewicz 1996, SIGGRAPH |
| Constraint-based placement (slope/height/aspect/material) | F | — |
| Clast scatter (boulders / cobbles / pebbles), imbrication | F | Grain-size field (`04`) drives size & density in scatter (`07`); pebbles dip upstream |
| Coral growth-form & zonation (light + wave energy) | P | Graus & Macintyre 1976; Chappell 1980; Done 1982, 1983 — form as scatter/ecosystem (`12`, `07`) |
| Coral accretive-growth morphogenesis (Péclet / Laplacian) | P | Kaandorp et al. 1996, 2005; Merks et al. 2003; Kaandorp & Kübler 2001 (`12`) |
| Spur-and-groove reef morphology | P | Shinn 1963; Storlazzi et al. 2003; Duce et al. 2016 (`12`) |
| Reef zonation / motu / sand cays | L | Composition over Done 1982/1983 zonation (`12`) |

## 8. Conversion & runtime → `08-output-contract.md`

| Algorithm | Tier | Source |
|---|---|---|
| Marching squares / cubes | P | Lorensen & Cline 1987, SIGGRAPH |
| Dual contouring | P | Ju, Losasso, Schaefer & Warren 2002, ACM TOG 21(3) |
| Layered surface stack (solid / fluid / transient) | P | Beneš & Forsbach 2001; Št'ava 2008; Peytavie 2009 — soil/sand/water/snow over bedrock, emitted as separate layers (`08`, `11`) |
| Mesh simplification / quadric error metrics | P | Garland & Heckbert 1997, SIGGRAPH |
| Geometry clipmaps | P | Losasso & Hoppe 2004, ACM TOG 23(3) |
| ROAM | P | Duchaineau et al. 1997, IEEE Visualization |
| BDAM | P | Cignoni et al. 2003, CGF 22(3) |
| Chunked LOD | P | Ulrich 2002, SIGGRAPH course notes |
| CDLOD | P | Strugar 2009, J. Graphics Tools 14(4) |
| Virtual texturing / sparse virtual textures | F | Barrett 2008 (GDC), Mittring 2008 (SIGGRAPH course) — talks, not papers |
| SatMap gradient (1D/2D colour LUT) & colour-map compositing | F | SatMap = a colour gradient indexed by a field (Gaea, `10` curve/LUT); the colour map = the composited albedo (`08`). No directional light baked in. |
| Normal / AO map encoding (BC5 reconstruct-Z, BC4, ORM pack) | F | Export packing (`08`); baking maths in `06` |
| Unit-vector (normal) encoding — reconstruct-Z, octahedral | P | Cigolle et al. 2014, JCGT 3(2) — the survey of schemes (`08`) |
| Normal map mipping (variance) | P | Toksvig 2005, JGT 10(3) |
| LEAN mapping | P | Olano & Baker 2010, I3D |
| Normal-map blending (RNM / UDN / whiteout) | F | Barré-Brisebois & Hill 2012, *Blending in Detail* — combine base + detail normals (`08`) |
| Height-based splat blending | F | Mishkinis 2013 — per-material depth maps for natural transitions (`08`) |
| Triplanar texturing | F | Geiss 2007, *GPU Gems 3* ch. 1 — tiling on steep slopes without UV stretch (`08`, `11`) |
| Stochastic / by-example tiling | P | Heitz & Neyret 2018, I3D — hide tiling repeats without ghosting (`08`) |
| Procedural material synthesis (the "rock" texture) | N | Substance/Gaea material nodes over `01` noise; derive PBR like terrain maps (`06`, `08`) |
| Texture synthesis by example | P | Efros & Leung 1999; Wei & Levoy 2000; Lefebvre & Hoppe 2006 (`08`) |
| Learned material from a photo (SVBRDF) | ? | Deschaintre et al. 2018 — verify; moving fast (`08`) |
| Emissive material channel (incandescent cracks) | F | crackMask (Worley F2−F1, `01`) × blackbody temperature ramp (`08`) |
| Floating origin / large-world coords | F | Thorne 2005 — widely cited but not a strong result; the technique is folklore |
| Cube-sphere grid (equidistant / equiangular) | P | Chan & O'Neill 1975 (QSC / COBE); Sadourny 1972; Ronchi et al. 1996 (equiangular) (`08`) |
| Geodesic / HEALPix spherical grid | P | Górski et al. 2005 (HEALPix); icosahedral geodesic — no seams (`08`) |
| Map-projection distortion (scale factor `h`) | P | Snyder 1987 — divide gradients by `h` or erosion biases (`08`) |
| Equirectangular / plate carrée (planetary interchange & delivery) | P (proj.) / F (resample) | Snyder 1987 — the lat-long DEM lingua franca (MOLA/LOLA/SRTM/GEBCO); an I/O format, **not** a sim grid — generate on cube-sphere/HEALPix, resample out with `cosφ` weighting (`08`, `25`) |
| Flow routing on a spherical / DGGS grid | P | Liao et al. 2020 (hex); Liao et al. 2025 (ISEA equal-area) (`08`, `03`) |
| Cube-face-seam flow routing | F | Halo cells + per-face rotation tables; no canonical paper (`08`) |
| DEM hydrological enforcement / pit removal | P | Hutchinson 1989 (ANUDEM); priority-flood + stream burning (`08`, `03`) |
| SRTM void filling (delta-surface) | P | Reuter, Nelson & Jarvis 2007 (`08`) |
| Lidar bare-earth filtering | P | Axelsson 2000 (adaptive TIN); Zhang et al. 2003 (morphological) (`08`) |
| DEM error field (spatially autocorrelated) | P | Fisher & Tate 2006 (`08`) |
| SAR layover/foreshortening/shadow; DEM striping & quantisation | F | Sensor geometry / product-validation practice (`08`) |
| Quadtree terrain, chunked heightfield, streaming, crack prevention, seam stitching | F | Engineering practice. No papers. (`08`) |

## 9. Climate → `13-climate-ecosystem.md`

| Algorithm | Tier | Source |
|---|---|---|
| Orographic rainfall / rain shadow | P | **Smith & Barstad 2004**, *A Linear Theory of Orographic Precipitation*, J. Atmos. Sci. 61 |
| Elevation lapse rate | P | Standard atmospheric physics — 6.5 °C/km environmental |
| Latitude temperature, seasonality, continentality | F | — |
| Wind fields (terrain-adjusted) | F | Authored base + crest speed-up (Jackson & Hunt 1975), lee shelter (`05` shadow), channelling, mass-consistent cleanup (Sherman 1978) (`13`). Real CFD out of scope. |
| Snow line, permafrost, aridity index | F | Threshold definitions |
| Climate zones / biome classification | P | Köppen–Geiger (Köppen 1900; Peel et al. 2007 for the modern map); Whittaker 1975 biome diagram |
| Multi-biome / regional composition (Hyrule, Middle-earth) | L | One global substrate + hydrology; masks vary parameters, not geometry (`13`). Survey: Galin et al. 2019. |
| Off-Earth regime (no water, low gravity) | L | Cratering + aeolian dominate; gravity rescales craters & dunes. Melosh 1989; Kok et al. 2012 — `SKILL.md` doctrine (`11`, `16`); worked blueprints (lunar highlands & maria, Mars, Titan/Europa/Io) in `20` Group J |
| Evaporation / evapotranspiration / soil moisture | F | For terrain, use TWI (`06`) as the proxy |
| Wetlands (swamp, marsh, bog) | L | High TWI + flat + impermeable substrate → mask + peat/mud + thin water layer (`13`, `18`) |
| Peat / bog accumulation (self-limiting growth) | P | Clymo 1984 — acrotelm/catotelm, `M_max = p/α`, domed profile (`13`) |
| Microbialites / stromatolites | L | Grotzinger & Knoll 1999 — photic-gated layered accretion (`13`) |
| Nebkha / vegetation-anchored dunes | L | Tengberg & Chen 1998 — cover raises the aeolian threshold (`13`, `05`, `16`) |
| Bioturbation mounds (termite / Mima / earthworm) | L / ? | Tarnita et al. 2017 (spacing mechanism `?`); Darwin 1881 (soil turnover as diffusivity) (`13`) |
| Fire spread (slope- and wind-driven front) | P | Rothermel 1972, USDA Forest Service Res. Pap. INT-115 (`13`) |
| Post-fire erosion response (repellency, debris flows) | P | Shakesby & Doerr 2006, Earth-Science Reviews 74 (`13`, `05`) |
| Burned land (char, snags, severity mosaic, succession) | L | Disturbance state: materials + scatter + ecosystem reset (`13`, `18`) |

## 10. Arid & desert → `16-arid-desert.md`

| Algorithm / landform | Tier | Source |
|---|---|---|
| Desert geomorphology (overview) | P | Cooke, Warren & Goudie 1993, *Desert Geomorphology* (UCL Press) |
| Yardang (wind abrasion) | P | Ward & Greeley 1984, GSA Bulletin 95(7) |
| Bornhardt / inselberg | F | Twidale 1982, *Granite Landforms* — differential subsurface weathering + stripping (L-tier landform) |
| Alluvial fan / bajada | P | Blair & McPherson 1994, JSR A64; Bull 1977, Prog. Phys. Geog. 1 |
| Playa (endorheic basin floor) | L | An unfilled `03` sink; evaporite flat |
| Oasis (deflation / fault-line / artesian) | L | Deflation basin floored *at the water table* + endorheic sabkha + groundwater-gated palms; blueprint (`20`) |
| Desert pavement | P | McFadden, Wells & Jercinovich 1987, Geology 15 — born-at-top, not a lag |
| Loess / sand sheets | F | Aeolian deposition (the deposition side of `05`) |
| Obstacle dunes — echo / climbing / falling | P (echo/climbing) / L (family) | Tsoar 1983, *Eolian Sediments & Processes* (Dev. Sedimentology 38) — windward-angle control; lee capture + synthesis Pye & Tsoar 2009 (`05`, `16`) |
| Sand ramp (aeolian–colluvial–fluvial apron) | P | Lancaster & Tchakerian 1996, Geomorphology 17 — composite deposit banked on a range front, mostly relict (`05`, `16`) |
| Shadow dune (aerodynamic lee of an obstacle) | P | Hesp 1981, J. Sed. Petrol. 51(1); vegetation-anchored = nebkha (`13`, `05`) |

## 11. Periglacial & permafrost → `17-periglacial.md`

| Algorithm / landform | Tier | Source |
|---|---|---|
| Periglacial geomorphology (overview) | P | French 2018, *The Periglacial Environment* (4th ed.); Washburn 1979, *Geocryology* |
| Sorted patterned ground (self-organization) | P | Kessler & Werner 2003, Science 299 — the same Werner as the dune model (`05`) |
| Solifluction | P | Matsuoka 2001, Earth-Science Reviews 55 |
| Rock glacier | P | Wahrhaftig & Cox 1959, GSA Bulletin 70 |
| Thermokarst, pingos | F | Ground-ice collapse / heave (French 2018) |
| Blockfield (felsenmeer) | F | In-place frost shattering; angular clast scatter (`07`) |

## 12. Surface materials → `18-materials.md`

| Topic | Tier | Source |
|---|---|---|
| Material as a property bundle (K, repose, permeability, appearance, stack role) | — | Doctrine (`18`, `SKILL.md`) — not a texture ID |
| Rock families (igneous / sedimentary / metamorphic) | — | Standard geology; `K` per lithology in `11`, appearance in `08` |
| Soil texture classes (sand/silt/clay → 12 classes) | P | USDA soil texture triangle, Soil Survey Manual (Handbook 18) |
| Grain-size classes (boulder → clay) | P | Wentworth 1922 (`04`) |
| Repose angles per material | P | `05` (Olsen 2004; Bagnold 1941 for sand) |

## 13. Lava simulation → `19-lava.md`

| Algorithm | Tier | Source |
|---|---|---|
| Lava rheology (Bingham, yield stress → levées, thickness) | P | Hulme 1974, GJRAS 39(2) (`11`, `19`) |
| Lava flow CA (grid, Monte Carlo anisotropy fix) | P | Miyamoto & Sasaki 1997, Computers & Geosciences 23(3) |
| Physics-based lava CA (Bingham Navier–Stokes flux) | P | MAGFLOW, INGV Catania — Bull. Volcanol. 2008 (Etna 2004); CUDA port in Annals of Geophysics |
| Channel thermo-rheological model (where a flow stops) | P | Harris & Rowland 2001, *FLOWGO*, Bull. Volcanol. 63 |
| Pahoehoe ↔ ʻaʻā transition (~5–10 m³/s) | P | Rowland & Walker 1990, Bull. Volcanol. 52 |
| SPH lava animation | P | Stora et al. 1999, Graphics Interface |
| Lava surface classification | P | Macdonald 1953, AJS 251(3) |
| Emissive crust material | F | crackMask × blackbody(T) — the sim's own `T`/crust fields (`08`, `19`) |

## 14. Owned / clean-room implementation → `21-clean-room-implementation.md`

| Concern | Tier | Source |
|---|---|---|
| Reference-informed engine-native implementation | Engineering mode | Papers and approved open source ground neutral pseudocode; redesign the runtime for the engine |
| Dependency-free implementation | Engineering property | Ship owned engine code even when approved source was consulted |
| Source-independent implementation | Engineering mode | Implementer uses papers/specifications and `09` oracles, not an existing codebase |
| Formally separated clean-room implementation | Legal-process mode | Specification author and implementer are separated; counsel defines the boundary |
| Independent verification | Engineering mode | Closed-form solutions, invariants and signatures from `09`; optional libraries are test-only comparison targets |
| License/provenance record | Engineering control | Record papers, code consulted, data/assets, patents checked, test fixtures and implementation authorship |

## 15. Complete generator delivery → `22-open-source-grounding.md`, `23-generator-blueprint.md`

| Concern | Tier | Source |
|---|---|---|
| Pre-grounded algorithm behavior | Engineering evidence | `22` records upstream revision, licence, source symbols, adopted decisions and deviations |
| Offline / pre-cooked generator | Architecture | `23` assembles GLOBAL high-quality terrain, analysis, materials, scatter, LOD and export |
| Runtime generator | Architecture | `23` maps LOCAL/NEIGHBOURHOOD work to frame-budgeted CPU/GPU execution |
| Hybrid generator | Architecture | `23` bakes the global process history and synthesises deterministic local detail at runtime |
| Implementation completeness | Engineering gate | Every node has fields/units, locality, precision, boundaries, determinism, oracle and version |

## 16. Voxel & streaming (chunk) generation → `24-voxel-streaming-generation.md`

A **family** paradigm — chunked, seeded, streamed, editable voxel worlds. **Minecraft is the
documented exemplar** (public datapack worldgen format, Cubiomes-reverse-engineered); the *family*
also includes cubic-voxel siblings (Creativerse, Luanti/Minetest, Terasology, Vintage Story) and
smooth-voxel cousins (Astroneer, No Man's Sky-style). **F/N-tier throughout; no papers.** It
deliberately suspends the heightfield-truth, process-history and mandatory-flow-routing doctrines and
substitutes local noise. Sources: documented/open generators (Minecraft's format, Luanti and
Terasology source), developer talks (Kniberg), reverse-engineering (Cubiomes) — **never a closed
clone's guessed internals** (N-tier discipline).

The rows below are **Minecraft's instantiation** (the best-documented); members vary along axes —
world extent, representation, mesher, biome model, generation authorship — set out in `24`.

| Component (Minecraft's instance) | Tier | Source |
|---|---|---|
| Density-function terrain (3D scalar; `d>0` solid) | F | Game noise-router / `noise_settings` datapack format; sampled on a coarse lattice + trilinearly interpolated (`01`, `15`) |
| Multi-noise biome (6-parameter climate space) | F | Game `multi_noise` biome source; temperature/humidity biome-only, continentalness/erosion/weirdness/depth drive shape (`13`) |
| Spline shape (climate → offset/factor → density) | F | Kniberg (Mojang) design talks — a developer source, not a paper |
| Proto-chunk stage pipeline & determinism | F | Engineering practice; seam-ownership = `08`/`23`; reverse-engineered by Cubiomes |
| Noise caves (cheese/spaghetti/noodle) + aquifers | F | Local noise water-tables, decoupled from drainage — **not** karst dissolution (`11`) |
| Meshing — greedy cubic vs smooth (MC/dual-contour/Transvoxel) | F | Lysenko "0fps" (cubic); smooth cousins mesh the same field differently (`08`) |
| Legacy 2D biome cascade (pre-1.18 GenLayer zoom; many clones) | F | Layered zoom + biome-blended 2D height noise |

**The trap this section prevents:** the *parameter* named "erosion" is a noise axis, not the erosion
of `04`/`05` — it moves no sediment and conserves no mass. And a runtime voxel world cannot produce
real drainage networks; if the brief needs them, that is a **hybrid** bake (`23`), not this paradigm.

## 17. Planetary & spherical worlds → `25-planetary-spherical.md`

The **whole-globe altitude** — a *consolidating* chapter. The spherical grid/seam/distortion substrate
lives in `08` and is **not** duplicated; `25` owns what changes above it and routes the rest. Mixed
tier, honest about which is which.

| Component | Tier | Source |
|---|---|---|
| Spherical grid, seams, distortion `h`, DGGS flow | P (F for cube-seam) | Already in `08` — cube-sphere/HEALPix/Snyder/Liao |
| Plate tectonics on a sphere (Euler-pole rotation) | P | McKenzie & Parker 1967; Morgan 1968 — rigid rotation, transform faults on small circles, spreading rate ∝ sin(distance) |
| Procedural whole-planet tectonics (graphics) | P | Cortial, Peytavie, Galin & Guérin 2019, *Procedural Tectonic Planets*, CGF 38(2) (Eurographics) |
| Global circulation & latitude climate bands | P physics / F realization | Three-cell model + Coriolis (Hadley 1735); terrain use is authored bands feeding `13`'s orographic model |
| Ocean gyres / boundary currents / coastal upwelling deserts | P physics / F realization | Ekman/Sverdrup/Stommel; the Namib–Atacama mechanism (`12`, `13`) |
| Sea level as geoid / oblate-spheroid equipotential | P geodesy | Earth `f ≈ 1/298`; flood-fill on potential, not radius (`03`) |
| 3D/4D noise on the sphere (no pole seam) | F | Sample 3D noise at surface points; standard practice, no paper (`01`) |
| Planet-scale precision, per-face LOD, streaming | F | Floating origin (Thorne 2005); quadtree-per-face + horizon culling (`08`, `23`) |
| Alien-world regimes (gravity/water; tidally-locked) | doctrine / L | `SKILL.md` off-Earth doctrine; worked worlds in `20` Group L |

**The traps this section prevents:** plate motion is a **rotation** about an Euler pole, not a
translation (straight-line plates read as wrong at a glance); the circulation **bands are physics, not
decoration** (a desert on the equator or rainforest at 30° is visibly wrong); and "sea level" is an
**equipotential**, not a constant radius.

---

## Node types (N-tier) — not algorithms

Commercial tools brand nodes. The brand is not the algorithm, and the mapping is usually
undocumented. **Do not claim to know what a specific tool's node does internally** unless it
is publicly documented — that's an unsupported claim about a proprietary product.

| You'll hear | It's really |
|---|---|
| "Erosion" node (any tool) | Some hydraulic model — pipe, droplet, or bespoke. Ask which. |
| "Wizard" / "Erosion2" / branded presets | A parameter preset over an unpublished implementation. Unknowable from outside. |
| "Fractal Terrace" | Terrace (`10`) with noise-perturbed levels |
| "Sediment" | Deposition output of an erosion node (`04`) |
| "Flow" / "Wear" / "Deposits" | Analysis outputs of an erosion sim, not separate algorithms |
| "Combine" / "Chokepoint" / "Sanctuary" | Tool-specific composites |

When someone asks "how does Gaea's Erosion node work" — the honest answer is that it isn't
documented, here's what the *family* of algorithms it plausibly belongs to does, and here's how
to tell from the output which one it is (`09`).

## The tool-node crosswalk

A fuller map from the **branded nodes** you meet in Gaea, World Machine and Houdini to the
**algorithm family** underneath and the reference that covers it. This is the practical companion to
"The terrain graph" in `SKILL.md`: it turns "which node do I reach for / what is this node really"
into a routing decision. The node names are *examples*, not exhaustive, and mix tools deliberately —
the point is the family, not the brand. **Internals stay proprietary:** this maps a node to *what
family it must belong to*, and `09` tells you how to read the output to confirm which member. Never
upgrade a crosswalk row into a claim about a specific paper inside a closed-source node.

**Generators**

| Branded node (examples) | Family | Ref |
|---|---|---|
| Perlin, Simplex, Voronoi / Cellular, Ridged, Billow, Worley | Noise / FBM / multifractal | `01` |
| Mountain, Terrain, Ridge, Dunes, Canyon, Crater, Island | Primitive + noise, or a landform composition | `01`, `10`, `20` |
| Constant, Gradient, Radial, Shape, Line, Draw / Spline | Primitives & SDF | `10` |
| File / Import, DEM, Heightmap in | An input field — evaluate in world space, never tile-local | `08` |

**Erosion & natural process**

| Branded node (examples) | Family | Ref |
|---|---|---|
| Erosion, Erosion2, Wizard, Hydro, Channeled Erosion, `erode` | Hydraulic — pipe or droplet (ask which; `09` reads it off the output) | `04` |
| Thermal, Thermal2, Slump, Debris, Talus | Thermal / mass wasting to the repose angle | `05` |
| Wind, Sand | Aeolian transport / dunes | `05`, `16` |
| Rivers, Lakes, Sea, Coast | Flow routing + fluvial / coastal | `03`, `12` |
| Snow, Glacier | Snow accumulation / SIA glacial | `13`, `12` |
| Sediment, Deposits, Wear, Flow, Fluvial (as *outputs*) | **Not separate algorithms** — analysis outputs of one erosion sim | `04`, `06` |

**Analysis & selectors**

| Branded node (examples) | Family | Ref |
|---|---|---|
| Slope, Angle | Slope (Horn 1981) | `06` |
| Curvature, Convexity, Concavity | Curvature (Zevenbergen & Thorne 1987) | `06` |
| Height / Select Height, Selective, Range, Clamp-select | Threshold + smoothstep selector → `MaskField` | `06` |
| Flow, FlowMap, Wetness | Flow accumulation / topographic wetness index | `03`, `06` |
| Occlusion, AO, Sky, Cavity | Horizon AO / sky-view factor | `06` |

**Combiners, remaps & filters** — *where graphs quietly break*

| Branded node (examples) | Family | Ref |
|---|---|---|
| Combine, Blend, Mixer, Merge, Layers | Operators — add / blend / smin / smax (**never bare max/mul**) | `10` |
| Clamp, Curve, Adjust, Autolevel, Transform | Remap / histogram | `10` |
| Warp, Shear, Fold, Twist | Coordinate warps | `10` |
| Blur, Sharpen, Median, Denoise | Filters (prefer bilateral / guided over Gaussian) | `10` |

**Scatter & output**

| Branded node (examples) | Family | Ref |
|---|---|---|
| Scatter, Distribute, Populate | Poisson-disk / blue-noise / density-driven | `07` |
| SatMap, Colorizer, CLUTer, Tint | Colour LUT indexed by a field | `08`, `10` |
| Texture, Splat, Mask export | Splatmap from `06` masks | `08` |
| Build, Export, Mesh, Unreal / Unity out | Tiling / LOD / quantise — **last, and once** | `08` |

**The two rules that keep this honest:** (1) a branded node maps to a *family*, never a claimed
internal — say "pipe or droplet, and here's how to tell" (`09`), not "it's Mei 2007". (2) The
combiners are where graphs silently fail — `normalize`, bare `max`, and `mul`-as-mask are the defects
`10` catalogues; a crosswalk that sends you to `10` for every "Combine" node is doing its job.
