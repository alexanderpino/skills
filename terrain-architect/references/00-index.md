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
| Salt tectonics / diapirism (domes, walls, withdrawal minibasins, crestal grabens) | P | Hudec & Jackson 2007, ESR 82; Jackson & Hudec 2017 (Cambridge) — driver (buoyancy vs differential loading) `?` (`11`) |
| Salt glacier (namakier) | P | Talbot & Rogers 1980 (Science 208); Talbot & Pohjola 2009, ESR 97 — flows only when wetted, arid-only (`11`) |
| Mud volcano / mud diapir | P | Kopf 2002 (Rev. Geophys. 40); Mazzini & Etiope 2017, ESR 168 — gryphons/salses/mud flows (`11`) |
| Stratification / sedimentary layering | P | Beneš & Forsbach 2001, *Layered Data Representation for Visual Simulation of Terrain Erosion*, SCCG |
| Layered terrain with overhangs/arches | P | Peytavie et al. 2009, *Arches: a Framework for Modeling Complex Terrains*, CGF 28(2) |
| Cave networks / karst dissolution | P | Paris et al. 2021, *Synthesizing Geologically Coherent Cave Networks*, CGF |
| Karst closed-depression ladder (doline → uvala → polje) + cenote + karren | P (L for uvala def.) | Ford & Williams 2007 — sink-size ladder, cenote = sink to water table, karren = micro-solution texture (`11`, `03`) |
| Lava flow (animation) | P | Stora et al. 1999, *Animating Lava Flows*, Graphics Interface |
| Lava flow morphology (levées, snouts, thickness) | P | Hulme 1974, GJRAS 39(2) — Bingham yield-stress rheology (`11`) |
| Pahoehoe / ʻaʻā / block lava | P | Macdonald 1953, American Journal of Science 251(3) — surface-texture classification (`11`, `18`) |
| Volcanic cones, calderas, craters, crater fields | F | Primitive + noise + erosion. No paper. |
| Rock hardness layers / lithology | F | A material field feeding erodibility `K`. See Št'ava 2008 for the layered coupling. |
| Soil / regolith production function | P | Heimsath, Dietrich, Nishiizumi & Finkel 1997, Nature 388 — exponential decline with soil depth (`11`) |
| Tors | P | Linton 1955 (Geographical Journal 121); Palmer & Neilson 1962 — joint-controlled deep-weathering residual (`11`, `16`) |
| Tafoni / honeycomb (cavernous weathering) | P (form) / L (single cause) | Mustoe 1982; Rodriguez-Navarro et al. 1999; Turkington & Phillips 2004 — salt + case-hardening self-organising hollowing (`11`) |
| Exfoliation / sheeting joints & domes | P | Martel 2006 (GRL 33) — surface-parallel stress × curvature; Gilbert 1904; Bradley 1963 (`11`, `06`) |
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
| Drumlins, till plains | Streamlined & sheet till under ice; author the form aligned to ice flow, genesis unresolved (Clark 2009) (`12`) |
| Eskers | Sorted fill of subglacial meltwater tunnels; route on the ice-surface potential, not the bed (Shreve 1985) (`12`) |
| Kames & kettle holes (kame-and-kettle) | Ice-contact stratified mounds + melt-out pits (closed basins) (`12`) |
| Outwash plain / sandur | Braided meltwater deposition beyond the terminus (`03`, `12`, `16`) |
| Glacial erratics | Scatter of out-of-lithology boulders — the ice fingerprint (`07`, `12`) |
| Tunnel valleys | Subglacial meltwater channels, often overdeepened → lake chains (`12`) |
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
| Domain boundary status (open / closed / fixed-gradient / looped / source) | F | No canonical paper; the standard formalisation is Landlab's `status_at_node` and fastscapelib's node-status enum (`03`, `22`) |
| Boundary fringe from a uniform open perimeter (the "tablecloth") | L | **Not an algorithm** — the outcome of making every edge cell an outlet. Removed by a simulated margin that export crops, authored outlets, or base level inside the domain (`03`, `09`) |

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
| Wind erosion physics | P | Bagnold 1941, *The Physics of Blown Sand and Desert Dunes* — the saltation-cloud physics is **not implementable as written**, but the threshold `u*_t` and the cubic `u*³` flux law are one expression each per cell (`05`) |
| Aeolian transport → bed change (continuum) | P | **Sauermann et al. 2001**, Phys. Rev. E 64 — flux saturation length + Exner: `∇·q` deflates/deposits. The branch that consumes a wind FIELD, vs. Werner's CA which consumes a direction (`05`). Near-threshold variant: Owen 1964, JFM 20 |
| Dune formation (implementable) | P | **Werner 1995**, Geology 23(12) — the slab CA. Under-cited relative to usefulness. |
| Dune size hierarchy / draa (mega-dunes) | P | Wilson 1972, Sedimentology 19 — ripple/dune/draa orders; compound & complex by superimposition (`05`) |
| Parabolic dunes & blowouts (vegetation-anchored) | P (blowout) / F (parabolic form) | Hesp 2002, Geomorphology 48 — blowout initiation; arms trail upwind, no canonical parabolic paper (`05`, `13`) |
| Coastal / vegetated dunes (foredune, dune belt) | P | Baas 2002 (Geomorphology 48, DECAL model); Hesp 1989/2002; Durán & Moore 2013 (PNAS 110) — beach-fed, onshore wind, vegetation-capped (`12`, `05`) |
| Glacier flow & erosion | P | Argudo et al. 2020, *Simulation, Modeling and Authoring of Glaciers*, ACM TOG 39(6) |
| Snow / avalanche | P | Cordonnier et al. 2018, *Interactive Generation of Time-evolving, Snow-Covered Landscapes with Avalanches*, CGF 37(2) |
| Esker (subglacial tunnel deposit) | P | Shreve 1985, GSA Bull 96 — route on the ice-surface hydraulic potential, not the bed (`12`) |
| Drumlin form & scaling | P (form) / ? (genesis) | Clark et al. 2009, QSR 28 — `E_max ≈ L^(1/3)`; genesis (deforming bed / instability / meltwater) unresolved (`12`) |
| Tunnel valleys | P (review) | Kehew et al. 2012, ESR 113 — subglacial meltwater channels, formation debated (`12`) |
| Glacial depositional suite (moraine, kame, kettle, sandur, till) | L | Compositions over the ice-erosion budget; synthesis Benn & Evans 2010 (`12`) |
| Coastal erosion / cliff retreat | F | No canonical graphics paper. Coastal engineering: Bruun 1962. **In practice a look, not a simulation** (`12`). |
| Mangrove coast (biogenic muddy progradation) | P | Woodroffe 1992; Furukawa et al. 1997; Alongi 2008 — traps mud, damps waves, keeps pace with sea level (`12`) |
| Chenier / chenier plain | P | Otvos & Price 1979; Augustinus 1989 — coarse ridges on mud, marking mud-supply lulls (`12`) |
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
| Insolation (terrain-shadowed solar radiation, sun-arc) | F | Standard solar geometry × the horizon-angle test (`06`) — **not AO**, which integrates the whole sky. GIS practice (GRASS `r.sun`, ArcGIS Solar Analyst); tool papers `?` until verified. Drives snow melt & aspect asymmetry (`13`, `27`) |
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
| Hexagonal grid (planar working grid, in its own right) | P (sampling) / F (coords) | Optimal 2D sampling lattice — ~13.4% fewer samples than square, realised via ~15% coarser spacing (Petersen & Middleton 1962; Mersereau 1979); 6 equidistant edge-neighbours ⇒ **no D4/D8 √2 ambiguity**, D6 flow routing (no metric bias; coarser 60° quantisation — striping shrinks, doesn't vanish), more isotropic CA/diffusion — renormalise the Laplacian (`2/(3d²)`); one-ring gradient/normal stencil (`Σhₖeₖ/(3d)`, isotropic leading error); hex-tile meshes carry two vertex classes (`N` centres + `2N` corners, two owned per cell) with closed-form normals for both; axial/cube/offset coords (Red Blob Games, F). A grid system, not the square raster's poor cousin (`26`, `03`, `09`) |
| Rhombille tiling — the structure of a hex heightfield | F | Joining centres to their corners partitions the plane into 60°–120° rhombi (Conway's rhombille; dual of trihexagonal/kagome, physics' *dice lattice*, the *tumbling blocks* pattern). **One rhombus = one neighbour pair**: vertices `A,B` (centres) + `p,q` (shared corners), sides `s = cellSize/√3`, long diagonal `AB = cellSize` (the link), short diagonal `pq = s` (the tile edge); `3N` rhombi over `3N` vertices. The three meshes are its three projections — dual = long diagonals, 6-fan = **split every rhombus on the short diagonal** (halves are equilateral, and *are* the fan wedges), corner-only = short diagonals (the honeycomb). Hence: hex's "which diagonal" **has a right answer** (the two diagonals aren't symmetry-exchangeable as a square quad's are — short gives 60°, long gives 30°–120°–30° and loses the tile outline); 4- and 6-meshes are watertight against each other; per-pair edge data (D6 flux, pipe flow) is `3N` not `6N`. Decline the 3-quads-per-tile cut (the isometric cube) — non-planar, so the GPU picks the diagonal (`26`, `03`, `04`) |
| Hex storage — a sheared 2D array | F | The index quad `(q,r),(q+1,r),(q,r+1),(q+1,r+1)` is a diamond of the same 60–120 shape as the rhombille's — though not one of *them*: four centres, `√3` larger, turned 30°, so a hex field is a square-grid field under a shear — exactly, not by analogy. Three adjustments: (1) **`cellSize` becomes a 2×2 shear matrix** `B` — `cellSize·[[1,½],[0,√3/2]]` pointy-top, `cellSize·[[√3/2,0],[½,1]]` flat-top (a 30° rotation apart), `diag(B,1)` in 3D since height never shears. Distance via `G = BᵀB` (off-diagonal `½ = cos60°`, the term square code assumes is 0; **same `G` for both orientations**), area/handedness via `det B = (√3/2)cellSize² > 0`, and **gradients/normals via the inverse transpose `B⁻ᵀ`, never `B`** — the classic shear bug, worth up to **30.5°** of gradient-direction error and a `√3` slope-magnitude spread (`0.82`–`1.41`), hitting lighting (`09`), slope masks (`06`) and repose thresholds (`05`). `cellSize`+`hexOrientation` determine `B`; don't store a second copy that can drift, and note the domain-area check *is* a `det B` check; (2) the quad diagonal is **pinned to the anti-diagonal** `(q+1,r)–(q,r+1)` — the only one that is a neighbour link — giving equilateral halves = `cornerA(q,r)`/`cornerB(q+1,r)`; (3) one array per class: cells `Q×R`, corners `2×Q×R`, edges/rhombi `3×Q×R` via `rhombus(k,q,r) = {(q,r), (q,r)+eₖ}`, `e = (1,0),(1,−1),(0,1)` — bijective, and `k` is the orientation (0°/60°/120°). Free: chunking, apron (an ordinary array border in index space), LOD by 2× decimation (basis `2B`, still triangular), upload as a plain R16/R32F texture. Traps: **hardware bilinear ≠ hex interpolation** (bilinear over a sheared rhombus, privileges a non-adjacent pair; affine-exact so a ramp misses it — use barycentric on the dual triangle); index-space `2×2` box filters are `√3`-anisotropic (use the 7-cell kernel, then decimate); a parallelogram array over a rectangular world wastes ~37% (square) / ~25% (16:9), the alternative being offset coords and the row-parity bug (`26`) |
| Hex ports of the simulation/analysis families | F | Every lattice-touching chapter carries its hex note; `26`'s **porting map** routes them. The pattern: world-space quantities stay world-space (wind, azimuths, samplers — never snapped to the 6 lattice directions), cell lookups via `cube_round`, continuous sampling barycentric, and the two constants that change together are the **cell area** `(√3/2)·cellSize²` and the **edge/contour width** `cellSize/√3`. Per family: D6/D6-MFD with Quinn's contour split gone (`03`); 6-pipe hydraulics, one length (`04`); droplet erosion = barycentric sample + barycentrically-interpolated `gradient6` (continuous — the sampled triangle's own plane gradient kinks at every edge) (`04`); thermal with one `dLimit` — the √2 bug unwritable (`05`); Werner dunes with world-space wind + `cube_round` landing (`05`); curvature via **`hessian6`** — the full Hessian from 3 antipodal second differences, exact on quadratics, trace = `laplacian6` (`06`); TWI with both hex constants or neither (`06`); AO/fetch marches unchanged but sampled barycentrically (`06`, `12`); per-cell jitter = uniform-in-hexagon via the 3-rhombi decomposition (`07`); lava CA keeps Monte Carlo — quantisation outlives the metric fix (`19`). Stream power consumes the D6 graph as-is; noise/SDFs never see the lattice (`26`) |
| Sea ice as a coastal modifier | P (process) / F (implementation) | **Not a landform** — a transient crust on `waterSurface`, never `solidTop` (`08`). First-order effect is *gating*: shore-fast ice and pack ice give an **open-water season**, so the coastal loop runs part-time and fetch is ice-limited. The trap: this does **not** mean less erosion — ice-rich permafrost bluffs (`17`) retreat by **thermal abrasion** (thaw niche → block collapse on ice wedges), driven by water temperature and open-water duration, *not* fetch, and are among Earth's fastest-retreating coasts; using the wave model for them is the defect. Ice rafting is a **net offshore sediment export** term with no wave analogue (dropstones; paleo record **Heinrich 1988**, *Quaternary Research* 29) that a wave-only budget misses. Plus ice push/shove ramparts and ice-keel seabed gouging; the floe/lead/ridge surface is composition (`01`, `10`), not simulation. **No graphics paper exists** — process literature only, as with coastal erosion (`12`) |
| Side-channel mask registry ("accumulator") | F | The sim→splatmap fan-in as one node. Two non-discretionary rules, both consequences of `14`'s purity contract: (1) its input set is **undeclared**, so the Merkle key misses it — adding a simulation leaves the key unchanged and every consumer serves a **stale, silently-wrong** splatmap; desugar at plan time and hash the *resolved* `(producerId, outPort)` set into the key. (2) Overlaps need a **documented total order** (snow → water → vegetation → debris → base), never a bare `max` (`10`) and never traversal order, which would make output depend on node insertion order. It is `LOCAL` but its cone is the whole graph, so it inherits its worst producer's tiling contract — and it is the natural single place to assert `Σ masks ≤ 1` (`06`, `09`) |
| Lattice anisotropy vs field anisotropy | F (framing) / P (the physics it names) | The two senses of the word, which must never be conflated. **Lattice**: the discretisation printing through — always a defect, because the preferred direction is a property of the array and nothing in the world put it there. **Field**: real directional structure, sourced from a cause — strike/dip and differential erodibility (`11`), fault fabric (`02`), wind (`05`, `16`), ice flow (`12`), aspect/insolation (`13`) — and terrain without it looks generic (trellis drainage, hogbacks and strike valleys exist *because* erosion is directional). The deciding rule: **a directional control is legitimate exactly when its direction comes from a field, not the grid**; a single global angle lands on the axes. The test is **rotate the domain** with an isotropic control for the interpolation floor — measured separation ~an order of magnitude (`0.09`–`0.13` vs `0.014`–`0.020`) — but the angle must **not** be a lattice symmetry: at 90° on a square grid an axis-locked operator scores exactly `0.000`. Swapping to hex (`26`) fixes one and does nothing to the other, which is the proof they differ (`09`) |
| Hex-native operations — what does **not** port from a square grid | F | The counterweight to the shear framing: it licenses **storage and geometry**, not algorithms. If an op needs only positions and linear interpolation, `B` carries it; if it branches on **neighbour structure, distance, rounding or axis-separability**, there is nothing to port. `for dx,dy in −1..1` → a 6-entry table (row-parity dependent in offset coords); the 4-vs-8 branch → **deleted**, no diagonal exists; Manhattan/Chebyshev → `(|x|+|y|+|z|)/2` in cube coords; `floor(p/cellSize)` → **`cube_round`** (per-axis rounding picks the wrong cell **16.8%** of the time — rounding draws rhombi, cells are hexagons); bilinear → **barycentric on the dual triangle** (split at `fq+fr = 1`, affine-exact); Bresenham → cube lerp + `cube_round`; box loops → ring `6k` / disc `1+3k(k+1)`; **separable 1D×1D blur → not separable** (two axes at 60° give a `√3` aspect; three-axis passes measure isotropic); 90° → 60° rotation as a cube permutation. The one *gain*: marching squares' ambiguous saddle has **no analogue** — marching triangles has 8 cases, all unambiguous (`26`, `03`, `12`) |
| Hex terrain in a square-grid engine — quadtrees under a shear | F | Because `B` is affine, every index-only structure a square-terrain engine owns stays valid over the axial array: **quadtrees**, Morton keys, chunked LOD, clipmaps, streaming pages (subdivision/nesting/containment are affine-invariant). **Cull in index space** — a world plane `n·x = d` pulls back to `(Bᵀn)·p = d`, so transform frustum normals by `Bᵀ` and stock AABB tests are exact; world AABBs around sheared nodes cost a constant **1.5×** area slack at every depth. **LOD distance must be world distance** (`G`) — an index circle is a `√3`-elongated ellipse (semi-axes `1.22`/`0.71·cellSize`). Folding `B` into the model matrix is free, but the normal matrix is then `transpose(inverse(M))` and an engine's rigid-transform `mat3(M)` fast path becomes the 30.5° bug. The quadtree refines the **lattice, not the cells** — centres nest under `2B`, but a coarse hex is not the union of four fine ones (hexagons don't tile a hexagon), so it buys render LOD and *no* gameplay hierarchy; that needs a hex aperture hierarchy (3/4/7, H3). LOD levels still T-junction — skirts/stitching as usual. **Physics is the exception**: heightfield colliders take rigid + per-axis scale, no shear parameter, so collision still wants the square raster (`26`, `24`) |
| Hex tile triangulation — 6-triangle fan vs 4-triangle corner-only | F | The fork *inside* a visible tile, and it is not about triangle count: `n−2` makes **4** the minimal triangulation of a hexagon (corners only, `2N` verts), an interior vertex adds 2 more → the **6-triangle centre fan** (`3N` verts), whose 7th vertex **is `h(q,r)`**. Corner-only therefore drops the cell's own sample: corners are means-of-3, so the surface is `(1/3)hᴀ + (1/9)Σring` — affine-exact (ramp/cone can't see it) but a one-cell spike `H` renders as a flat plateau at **`H/3`**; detector is an **impulse**, not the sun sweep. Exact & free where tops are flat (prisms, water, UI tiles) or as a far LOD tier — the two are **watertight against each other**, same 6 boundary edges, no T-junction, no skirts. Hexagon has 14 triangulations (Catalan `C₄`) = **6 fan + 6 zigzag + 2 ear-and-core**, enumerated; min angle is exactly 30° for *all fourteen*, so the centre fan's 60° beats the whole space and the choice among them is about symmetry, never triangle quality. Prefer **ear-and-core** (3-fold symmetric, equilateral core over the tile centre) to a corner fan (1 mirror; centre height = 2 opposite corners); min angle 30° for all 14 vs the centre fan's 60° (`26`, `09`) |
| Hex prism / "pillar" stepped-tile rendering | F | Quantise height to `stepHeight` and extrude each cell into a flat-top prism — the hex-strategy-game and relief-model look. Still a **heightfield**, not voxels (`24` does not apply): one column per cell, no overhangs. Quantise **last** — it is `11`'s terrace op at mesh-build time; quantise early and slope goes 0-or-infinite, killing flow routing and erosion. **One scalar per cell is the whole vertex data** — no corner heights, no derived per-vertex anything, no apron; prisms differ only by xy translate + z extent, so instancing is the default. Normals are 7 enumerated constants (top `+Z` + 6 walls), hard edges so vertices are *not* shared, and AO carries the form read (`26`, `11`, `06`) |
| Cube-sphere grid (equidistant / equiangular) | P | Chan & O'Neill 1975 (QSC / COBE); Sadourny 1972; Ronchi et al. 1996 (equiangular) (`08`) |
| Icosahedral hexagonal DGGS (Goldberg polyhedron) | P | The planar hex grid closed onto the sphere: hexagons + **exactly 12 pentagons** (Euler; Goldberg 1937); equal-area via ISEA (Snyder 1992; ISEA7H); DGGS survey Sahr, White & Kimerling 2003; Uber H3 (aperture-7, **gnomonic — not equal-area**, ~1.6× cell-area spread, F/N). The low-anisotropy **procedural-planet** grid (`08`, `25`) |
| HEALPix spherical grid | P | Górski et al. 2005 — equal-area, iso-latitude *quadrilateral pixels* (not hexagons); no seams (`08`) |
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
| Wind fields (terrain-adjusted) | F | A per-cell **flow field** (speed + direction), not a constant: authored base + crest speed-up (Jackson & Hunt 1975 — over a fetch secant, so it peaks AT the crest), lee shelter (`05` 15° separation shadow), channelling along a structure-tensor valley axis, mass-consistent cleanup (Sherman 1978) (`13`). Under a constant wind `∇·q ≡ 0` and wind moves no terrain at all. Real CFD out of scope. |
| Snow line, permafrost, aridity index | F | Threshold definitions |
| Climate zones / biome classification | P | Köppen–Geiger (Köppen 1900; Peel et al. 2007 for the modern map); Whittaker 1975 biome diagram |
| Altitudinal life zones (explicit elevation belts) | P | Holdridge 1947 (Science 105(2727)), 1967 (*Life Zone Ecology*) — biotemperature + precip + PET; named montane→alpine→nival belts up a mountain (`13`) |
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
| Pediment (bedrock piedmont) | P | Dohrenwend 1994 (Geomorphology of Desert Environments) — erosional bedrock surface, sharp piedmont angle; the fan's opposite (`16`) |
| Lunette / clay dune | P | Bowler 1973, ESR 9 — source-bordering ridge on the playa lee, clay-pellet, records deflation (`16`, `05`) |
| Playa (endorheic basin floor) | L | An unfilled `03` sink; evaporite flat |
| Oasis (deflation / fault-line / artesian) | L | Deflation basin floored *at the water table* + endorheic sabkha + groundwater-gated palms; blueprint (`20`) |
| Desert pavement | P | McFadden, Wells & Jercinovich 1987, Geology 15 — born-at-top, not a lag |
| Loess / sand sheets | F | Aeolian deposition (the deposition side of `05`) |
| Evaporite zonation & salt-crust (tepee) polygons | P | Warren 2016; Eugster & Hardie 1978; Kinsman 1969 (sabkha); Lokier 2012 (crust polygons) — carbonate→gypsum→halite→bittern by salinity (`16`) |
| Saltern pink/red colour (biogenic) | P (mechanism) / L (hue) | Oren & Rodríguez-Valera 2001; Oren 2005 — *Dunaliella* β-carotene + haloarchaeal bacterioruberin, salinity-zoned (`16`, `18`) |
| Obstacle dunes — echo / climbing / falling | P (echo/climbing) / L (family) | Tsoar 1983, *Eolian Sediments & Processes* (Dev. Sedimentology 38) + Qian et al. 2011, JGR-ES 116 (~60° separation threshold) — windward-angle control; lee capture + synthesis Pye & Tsoar 2009 (`05`, `16`) |
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

## 18. Hexagonal working grids → `26-hexagonal-grids.md`

The **other planar grid**, end to end, and a *flat-terrain* chapter first — the sphere is one further
domain it closes onto, not the reason it exists. `08` keeps the manifest fields and the deliver-a-raster
rule; `26` owns everything else.

| Component | Tier | Source |
|---|---|---|
| Hexagonal-lattice sampling optimality | P | Petersen & Middleton 1962; Mersereau 1979 — ~13.4% fewer samples for the same isotropic bandwidth, realised as ~15% coarser spacing |
| Axial / cube / offset coordinates | F | Red Blob Games (Amit Patel) — the de-facto standard, no paper |
| D6 / MFD flow routing on a hex mesh | P | Liao et al. 2020 (HexWatershed); Liao et al. 2025 (ISEA equal-area) (`03`) |
| Renormalised stencils (Laplacian `2/(3d²)`, one-ring gradient `Σhₖeₖ/(3d)`) | F | Lattice-moment identities (`Σeₖ = 0`, `Σeₖeₖᵀ = 3I`, `Σuₘuₘᵀ = (3/2)I`) — derivable in four lines (`05`, `06`) |
| Sheared-array storage: `B`, `G = BᵀB`, normals via `B⁻ᵀ` | F | Elementary linear algebra; the inverse-transpose rule is the classic shear bug (up to 30.5° of normal error, `√3` slope-scale spread) |
| Rhombille tiling as the meshing structure | F | Classical tiling (Conway; dual of trihexagonal/kagome); the mesh counts are Euler's formula |
| Tile triangulation: 6-triangle fan vs 4-triangle corner-only | F | `n−2` minimal triangulation vs an added interior vertex; the ×1/3 extremum attenuation is a two-line derivation (`09`) |
| Index-space quadtrees / culling under a shear | F | Engineering — affine invariance of subdivision; 1.5× AABB slack, `√3` LOD-ring anisotropy |
| Hex prism / "pillar" stepped-tile rendering | F | Rendering and art-direction convention; the quantisation is `11`'s terrace op at mesh-build time (`06`, `11`) |

## 19. Auxiliary maps & engine data handoff → `27-engine-data-handoff.md`

The **contract altitude** — like `08`/`14`, this chapter owns rules, not new simulations; every map
in its registry routes to a producer chapter that already exists. Doctrine throughout, resting on
P/F-tier producers.

| Concern | Tier | Source |
|---|---|---|
| First-class auxiliary maps & the co-evolution rule | Doctrine | `27`, `SKILL.md` — every auxiliary layer a persistent R32F field on a typed port; a node that alters terrain co-updates the maps its process touches, in the same pass |
| State vs derived map lifecycle | Doctrine | `27` — state maps (soil, wetness, snow) are path-dependent, carried through the sim, never reconstructed from final geometry; derived maps (curvature, AO, insolation) recomputed after the last height write (`06`, `SKILL.md` Legal Order) |
| The Masking Doctrine (raw causes out; no baked diffuse / predefined materials in the runtime handoff) | Doctrine | `27` — the hydrology handoff (`SKILL.md`) generalised to the whole export surface; `08`'s satmap demoted to a preview/review product |
| Standard map registry (climate / geology / hydrology / geometry) | — | Producers all routed: moisture & temperature & wind `13`, insolation `06`, soil depth `11`, strata hardness `11`, state wetness `13` / TWI `06`, flow velocity `03`, curvature & AO `06` |
| The Snow Rule ("no moisture = no new snow") + its three displacement channels | Doctrine over P | Gating already in `13`'s snowStep (`precip · (T<0)`); displacement: wind-loading (Werner shadow-zone logic, `05`/`13`), avalanches (Cordonnier et al. 2018, `13`), glacial flow (SIA, `12`) — nothing else moves snow |
| Handoff verification (layer-stack budget, dry-snow attribution, derived-map re-derivation) | Engineering check | `27`, registered in `09`'s checklist; runnable: `reference-impl/tests/asserts.py` (`assert_layer_budget`), `reference-impl/snow.py` (`dry_snow_attribution`) |

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

A fuller map from the **branded nodes** you meet in Gaea, World Machine, Houdini and Vue to the
**algorithm family** underneath and the reference that covers it. This is the practical companion to
"The terrain graph" in `SKILL.md`: it turns "which node do I reach for / what is this node really"
into a routing decision. The node names are *examples*, not exhaustive, and mix tools deliberately —
the point is the family, not the brand. **Internals stay proprietary:** this maps a node to *what
family it must belong to*, and `09` tells you how to read the output to confirm which member. Never
upgrade a crosswalk row into a claim about a specific paper inside a closed-source node.

The Vue names below are mapped from documented UI behavior and practitioner guidance (Pandhi 2011,
`99`), not from source code. They are therefore **N/F-tier descriptions of controls**, never proof
of the proprietary implementation or of a physical process.

**Generators**

| Branded node (examples) | Family | Ref |
|---|---|---|
| Perlin, Simplex, Voronoi / Cellular, Ridged, Billow, Worley | Noise / FBM / multifractal | `01` |
| Mountain, Terrain, Ridge, Dunes, Canyon, Crater, Island | Primitive + noise, or a landform composition | `01`, `10`, `20` |
| Vue Terrain Fractal; MetaScale / Largest Feature / Smallest Feature | Multiscale noise controls: domain scale, largest wavelength and lower band limit. Useful initial condition, **not** erosion or a mountain-range process | `01`, `02`, `04` |
| Vue Strata Filter / Confined Strata | Usually a terrace/quantised-height look; for defensible geology use a tilted/folded stratigraphic coordinate feeding lithology and `K` instead | `10`, `11` |
| Vue HyperTerrain / MetaBlob + displacement | Implicit/SDF or volumetric base shape plus procedural displacement. Use a non-heightfield representation when arches, caves or overhangs are required | `10`, `11`, `24` |
| Constant, Gradient, Radial, Shape, Line, Draw / Spline | Primitives & SDF | `10` |
| File / Import, DEM, Heightmap in | An input field — evaluate in world space, never tile-local | `08` |

**Erosion & natural process**

| Branded node (examples) | Family | Ref |
|---|---|---|
| Erosion, Erosion2, Wizard, Hydro, Channeled Erosion, `erode` | Hydraulic — pipe or droplet (ask which; `09` reads it off the output) | `04` |
| Thermal, Thermal2, Slump, Talus | Thermal / mass wasting to the repose angle | `05` |
| Debris, Rockfall, Fragments | **Overloaded name — check which** — the heightfield scree/talus surface is `05`; a generator of discrete rock *fragments* is scatter, and its sizes/orientations belong to `07`'s clasts (scree clasts are normal-aligned, unlike river bars) | `05`, `07` |
| Wind, Sand | Aeolian transport / dunes | `05`, `16` |
| Anisotropy / Direction / Grain / Strike (as *controls on* an erosion or filter node) | **Field anisotropy** — legitimate only if the direction comes from a field (strike/dip `11`, fault fabric `02`, wind `05`, ice flow `12`, aspect `13`). A single global angle will land on the axes and is `09`'s lattice-anisotropy defect wearing the feature's clothes; rotate the domain to tell them apart | `09`, `11`, `05` |
| Vegetation, Trees, Plants, Foliage | Ecosystem simulation — iterative colonisation/competition/self-thinning driven by climate & hydrology, then scattered | `13`, `07` |
| Rivers, Lakes, Sea, Coast | Flow routing + fluvial / coastal | `03`, `12` |
| Snow, Glacier | Snow accumulation / SIA glacial | `13`, `12` |
| Icefloe, Sea Ice, Pack Ice | **Sea ice** — a transient lid on the water surface, never terrain; its real role is gating the coastal loop (open-water season, ice-limited fetch) plus ice rafting, push ridges and keel gouging | `12`, `17` |
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
| Vue EcoSystem / Variable Density / Layer Affinity / Repulsion | Rule-based scatter or ecosystem simulation, with density fields and cross-layer distance constraints | `07`, `13` |
| Accumulator, Mask registry, Global masks | A **side-channel mask registry** — editor sugar over the sim→splatmap fan-in. Must be desugared before evaluation: hash the *resolved* producer set into the cache key or adding a sim serves stale output, and carry an explicit precedence or the result depends on node insertion order | `14`, `08` |
| SatMap, Colorizer, CLUTer, Tint | Colour LUT indexed by a field | `08`, `10` |
| Texture, Splat, Mask export | Splatmap from `06` masks | `08` |
| Vue Aerial Perspective / camera-scale controls | Downstream atmosphere/presentation, not terrain generation. They may change perceived scale but must not change world units or process parameters | `08`, `09` |
| Build, Export, Mesh, Unreal / Unity out | Tiling / LOD / quantise — **last, and once** | `08` |

**The two rules that keep this honest:** (1) a branded node maps to a *family*, never a claimed
internal — say "pipe or droplet, and here's how to tell" (`09`), not "it's Mei 2007". (2) The
combiners are where graphs silently fail — `normalize`, bare `max`, and `mul`-as-mask are the defects
`10` catalogues; a crosswalk that sends you to `10` for every "Combine" node is doing its job.
