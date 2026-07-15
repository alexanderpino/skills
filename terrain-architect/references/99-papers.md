# Bibliography

Grouped by family. Where a citation is commonly mangled, the correction is noted — those are
at the top because they are the ones that send implementers to the wrong paper.

## Attribution corrections

These errors circulate widely in terrain-generation reference tables. Do not propagate them.

| Common claim | Reality |
|---|---|
| "Hydraulic (Particle) — Mei et al. 2007" | **Mei et al. 2007 is a grid/pipe model**, not particle. It is the canonical virtual-pipe paper. |
| "Hydraulic (Grid/Pipe) — Št'ava et al. 2008" | **Št'ava et al. 2008 is also a pipe model** — an extension of Mei, adding sediment slippage, layers, and boundary handling. Mei and Št'ava are the same family, not two families. |
| Droplet/particle erosion has a canonical paper | It doesn't. It descends from **Musgrave et al. 1989** and reaches its modern form in **Beyer's 2015 TU München thesis**, which borrowed Mei's transport-capacity formulation and applied it per-droplet. Popularised by Sebastian Lague. |
| "Tectonic Plates — Cordonnier 2015" | The paper is **Cordonnier et al. 2016**, and it is *the same paper* as the stream power citation. One paper covers both; there is no separate 2015 tectonics paper. |
| "Stream power — Cordonnier et al. 2016" | Correct, but incomplete: the O(N) implicit solver that makes stream power tractable is **Braun & Willett 2013**. Cordonnier builds on it. If you cite only Cordonnier, the implementer will miss the solver. |

## Noise

- **Perlin, K. (1985).** *An Image Synthesizer.* SIGGRAPH '85. — Original Perlin noise; cubic
  fade `3t²−2t³`.
- **Perlin, K. (2002).** *Improving Noise.* ACM TOG 21(3), SIGGRAPH '02. — Quintic fade
  `6t⁵−15t⁴+10t³`; the 12-gradient set. Use this, not the 1985 version.
- **Perlin, K.** US Patent 6,867,776, *Standard for perlin noise.* — Covered simplex-type
  gradient noise in 3D+. **Expired January 2022.** Simplex is now unencumbered.
- **Gustavson, S. (2005).** *Simplex noise demystified.* Linköping University technical note.
  — The readable derivation of the skew/unskew constants and the reference 2D/3D/4D code.
- **KdotJPG.** *OpenSimplex2.* github.com/KdotJPG/OpenSimplex2 — Public domain. Reference
  implementation; includes the lattice-rotated `noise3_ImproveXY` variants. Don't reimplement
  from memory.
- **Worley, S. (1996).** *A Cellular Texture Basis Function.* SIGGRAPH '96. — F1/F2 cellular
  noise. Note Worley specifies a Poisson-distributed feature-point count per cell; the
  one-point-per-cell simplification everyone uses is a deviation.
- **Musgrave, F.K.** Chapters in **Ebert, Musgrave, Peachey, Perlin & Worley,** *Texturing and
  Modeling: A Procedural Approach* (3rd ed., 2002). — The authoritative source for ridged
  multifractal and hybrid multifractal, including the weight-feedback formulations that most
  online versions omit. Also **Musgrave, F.K. (1993),** *Methods for Realistic Landscape
  Imaging*, PhD thesis, Yale.
- **Quilez, I.** *Domain warping.* iquilezles.org/articles/warp — The `fbm(p + fbm(p + fbm(p)))`
  construction.
- **Bridson, R., Houriham, J. & Nordenstam, M. (2007).** *Curl-Noise for Procedural Fluid Flow.*
  ACM TOG 26(3), SIGGRAPH '07. — Divergence-free noise.

## Tectonics & landscape evolution

- **Cordonnier, G., Galin, E., Gain, J., Benes, B., Guérin, E., Peytavie, A. & Cani, M.-P.
  (2016).** *Large Scale Terrain Generation from Tectonic Uplift and Fluvial Erosion.*
  Computer Graphics Forum 35(2) (Eurographics 2016). — Tectonic uplift + stream power +
  lake-graph local-minima handling. **This is the "2015 tectonics" paper and the "2016 stream
  power" paper — they are one and the same.**
- **Cordonnier, G., Braun, J., Cani, M.-P., Benes, B., Galin, E., Peytavie, A. & Guérin, E.
  (2017).** *Authoring Landscapes by Combining Ecosystem and Terrain Erosion Simulation.*
  ACM TOG 36(4), SIGGRAPH '17. — The follow-up; couples vegetation to erosion.
- **Braun, J. & Willett, S.D. (2013).** *A very efficient O(N), implicit and parallel method to
  solve the stream power equation governing fluvial incision and landscape evolution.*
  Geomorphology 180–181, 170–179. — **The paper that matters for stream power.** The O(N)
  stack ordering + unconditionally stable implicit solver. Known in the geoscience community
  as the basis of FastScape.
- **Whipple, K.X. & Tucker, G.E. (1999).** *Dynamics of the stream-power river incision model:
  Implications for height limits of mountain ranges, landscape response timescales, and research
  needs.* Journal of Geophysical Research 104(B8), 17661–17674. — The reference for stream-power
  incision dynamics and knickpoint behaviour (`04`).
- **Crosby, B.T. & Whipple, K.X. (2006).** *Knickpoint initiation and distribution within fluvial
  networks: 236 waterfalls in the Waipaoa River, North Island, New Zealand.* Geomorphology
  82(1–2), 16–38. — Where waterfalls come from and how they propagate through a network. The
  empirical anchor for "a waterfall is a knickpoint" (`04`).
- **Berlin, M.M. & Anderson, R.S. (2007).** *Modeling of knickpoint retreat on the Roan Plateau,
  western Colorado.* Journal of Geophysical Research 112(F3). — A quantitative knickpoint-retreat
  model (`04`).

## Hydraulic erosion

- **Musgrave, F.K., Kolb, C.E. & Mace, R.S. (1989).** *The Synthesis and Rendering of Eroded
  Fractal Terrains.* SIGGRAPH '89. — The origin of both thermal erosion and grid-based
  hydraulic erosion in graphics. Everything downstream traces here.
- **Mei, X., Decaudin, P. & Hu, B.-G. (2007).** *Fast Hydraulic Erosion Simulation and
  Visualization on GPU.* Pacific Graphics 2007. — **The virtual pipe model.** Grid-based, not
  particle-based. The 8-step formulation with the outflow scaling factor.
- **Št'ava, O., Beneš, B., Brisbin, M. & Křivánek, J. (2008).** *Interactive Terrain Modeling
  Using Hydraulic Erosion.* SCA 2008. — Extends Mei: sediment slippage, material layers,
  boundary conditions, `lmax` shallow-water capacity ramp. Also a pipe model.
- **Beyer, H.T. (2015).** *Implementation of a Method for Hydraulic Erosion.* Bachelor thesis,
  Technische Universität München. — The modern droplet/particle formulation. Borrows Mei's
  transport capacity, applies it per-droplet. This is what "particle erosion" actually means
  in practice.
- **Lague, S.** *Hydraulic Erosion.* github.com/SebLague/Hydraulic-Erosion — Not a paper, but
  the implementation most people have actually read. Follows Beyer. Useful as a cross-check on
  the brush/point asymmetry.

## Thermal & aeolian

- **Musgrave et al. (1989)** — above. Thermal erosion originates here.
- **Olsen, J. (2004).** *Realtime Procedural Terrain Generation.* Technical report, University
  of Southern Denmark. — Fast approximations for thermal/talus, including the sweep-based
  variant.
- **Bagnold, R.A. (1941).** *The Physics of Blown Sand and Desert Dunes.* Methuen, London. —
  The physics. Threshold friction velocity, the `u*³` saltation law. Not directly
  implementable; cite it for *why*, not *how*.
- **Werner, B.T. (1995).** *Eolian dunes: Computer simulations and attractor interpretation.*
  Geology 23(12), 1107–1110. — **The implementable dune model.** Slab CA with shadow zone and
  differential deposition probability. Produces barchan/transverse/linear/star dunes from wind
  regime alone. Under-cited relative to its usefulness.

## Flow routing

- **O'Callaghan, J.F. & Mark, D.M. (1984).** *The extraction of drainage networks from digital
  elevation data.* Computer Vision, Graphics and Image Processing 28(3), 323–344. — D8.
- **Tarboton, D.G. (1997).** *A new method for the determination of flow directions and upslope
  areas in grid digital elevation models.* Water Resources Research 33(2), 309–319. — D∞.
  The 8-facet construction.
- **Freeman, T.G. (1991).** *Calculating catchment area with divergent flow based on a regular
  grid.* Computers & Geosciences 17(3), 413–422. — MFD with the calibrated exponent `p = 1.1`.
- **Quinn, P., Beven, K., Chevallier, P. & Planchon, O. (1991).** *The prediction of hillslope
  flow paths for distributed hydrological modelling using digital terrain models.* Hydrological
  Processes 5(1), 59–79. — The sibling MFD variant: `p = 1` with contour-length weighting.
  Often conflated with Freeman; they are not the same.
- **Barnes, R., Lehman, C. & Mulla, D. (2014).** *Priority-Flood: An optimal depression-filling
  and watershed-labeling algorithm for digital elevation models.* Computers & Geosciences 62,
  117–127. — The fill algorithm, including the epsilon variant that preserves a gradient
  across filled basins.
- **Planchon, O. & Darboux, F. (2002).** *A fast, simple and versatile algorithm to fill the
  depressions of digital elevation models.* Catena 46(2–3), 159–176. — The other standard fill.
- **Lindsay, J.B. (2016).** *Efficient hybrid breaching-filling sink removal methods for flow
  path enforcement in digital elevation models.* Hydrological Processes 30(6), 846–857. —
  Breaching, and the hybrid breach/fill policy. The right default for terrain generation.

## Analysis

- **Zevenbergen, L.W. & Thorne, C.R. (1987).** *Quantitative analysis of land surface
  topography.* Earth Surface Processes and Landforms 12(1), 47–56. — The 3×3 quartic fit;
  profile and plan curvature.
- **Horn, B.K.P. (1981).** *Hill shading and the reflectance map.* Proceedings of the IEEE
  69(1), 14–47. — The slope/aspect method GIS tools use.
- **Beven, K.J. & Kirkby, M.J. (1979).** *A physically based, variable contributing area model
  of basin hydrology.* Hydrological Sciences Bulletin 24(1), 43–69. — TOPMODEL; the
  topographic wetness index.
- **Timonen, V. & Westerholm, J. (2010).** *Scalable Height Field Self-Shadowing.* Computer
  Graphics Forum 29(2) (Eurographics 2010). — O(1)-per-cell horizon computation via sweep +
  incremental convex hull. The one to use for large-radius terrain AO.
- **Bavoil, L., Sainz, M. & Dimitrov, R. (2008).** *Image-space horizon-based ambient
  occlusion.* SIGGRAPH '08 talks. — HBAO. Note its `sin h − sin t` form is a screen-space
  weighting, not the cosine-weighted hemisphere integral; for a baked terrain AO map with an
  up normal the `cos²` form is the correct integral.

## Sampling & scatter

- **Bridson, R. (2007).** *Fast Poisson Disk Sampling in Arbitrary Dimensions.* SIGGRAPH '07
  sketches. — Two pages. The `r/√n` grid, active list, `k = 30`.
- **Mitchell, D.P. (1991).** *Spectrally optimal sampling for distribution ray tracing.*
  SIGGRAPH '91. — Best-candidate.
- **Ulichney, R.A. (1993).** *Void-and-cluster method for dither array generation.* SPIE 1913.
  — Tileable blue-noise masks. The right answer for high-count ground cover.
- **Yuksel, C. (2015).** *Sample Elimination for Generating Poisson Disk Sample Sets.* Computer
  Graphics Forum 34(2) (Eurographics 2015). — Exact sample counts with excellent spectra.
- **Ebeida, M.S., Patney, A., Mitchell, S.A., Davidson, A., Knupp, P.M. & Owens, J.D. (2011).**
  *Efficient Maximal Poisson-Disk Sampling.* ACM TOG 30(4), SIGGRAPH '11.
- **Wei, L.-Y. (2008).** *Parallel Poisson disk sampling.* ACM TOG 27(3), SIGGRAPH '08.

## Rendering & output

- **Losasso, F. & Hoppe, H. (2004).** *Geometry clipmaps: terrain rendering using nested
  regular grids.* ACM TOG 23(3), SIGGRAPH '04. — Nested grids, vertex morphing across the
  transition band.
- **Garland, M. & Heckbert, P.S. (1997).** *Surface simplification using quadric error metrics.*
  SIGGRAPH '97. — QEM decimation, for mesh LOD that preserves features.
- **Toksvig, M. (2005).** *Mipmapping Normal Maps.* Journal of Graphics Tools 10(3). —
  Variance-preserving normal mips. Prevents distant terrain going flat and shiny.
- **Olano, M. & Baker, D. (2010).** *LEAN Mapping.* I3D 2010. — The more principled successor
  to Toksvig; pushes normal variance into roughness properly.
- **Cigolle, Z.H., Donow, S., Evangelakos, D., Mara, M., McGuire, M. & Meyer, Q. (2014).** *A
  Survey of Efficient Representations for Independent Unit Vectors.* Journal of Computer Graphics
  Techniques 3(2), 1–30. — Normal-vector encodings: reconstruct-Z, octahedral, and their error.
  The reference for packing normal maps (`08`).

## Noise (additional)

- **Lagae, A., Lefebvre, S., Drettakis, G. & Dutré, P. (2009).** *Procedural Noise using Sparse
  Gabor Convolution.* ACM TOG 28(3), SIGGRAPH '09. — Gabor noise; spatially varying spectrum
  and orientation.
- **Lagae, A., Lefebvre, S., Cook, R., DeRose, T., Drettakis, G., Ebert, D., Lewis, J.P.,
  Perlin, K. & Zwicker, M. (2010).** *A Survey of Procedural Noise Functions.* Computer Graphics
  Forum 29(8). — **The best single overview.** Read before choosing a noise.
- **Cook, R.L. & DeRose, T. (2005).** *Wavelet Noise.* ACM TOG 24(3), SIGGRAPH '05. — Genuinely
  band-limited noise; the anti-aliasing argument.
- **Lewis, J.P. (1989).** *Algorithms for Solid Noise Synthesis.* SIGGRAPH '89. — Sparse
  convolution noise; ancestor of Gabor and wavelet.
- **Fournier, A., Fussell, D. & Carpenter, L. (1982).** *Computer Rendering of Stochastic
  Models.* CACM 25(6). — Midpoint displacement / diamond-square. Historically important,
  obsolete in practice (`01`).
- **Voss, R.** in **Peitgen, H.-O. & Saupe, D. (eds.) (1988),** *The Science of Fractal Images.*
  — Spectral synthesis; "random fractal forgeries".
- **Mandelbrot, B. (1982).** *The Fractal Geometry of Nature.* — FBM's origin.

## Terrain synthesis (learned / example-based)

- **Zhou, H., Sun, J., Turk, G. & Rehg, J.M. (2007).** *Terrain Synthesis from Digital Elevation
  Models.* IEEE TVCG 13(4). — Patch-based example synthesis from real DEMs.
- **Guérin, É., Digne, J., Galin, E., Peytavie, A., Wolf, C., Benes, B. & Martinez, B. (2017).**
  *Interactive Example-Based Terrain Authoring with Conditional Generative Adversarial Networks.*
  ACM TOG 36(6), SIGGRAPH Asia '17. — Sketch-to-terrain and amplification.
- Diffusion-based terrain generation and terrain super-resolution: **no verified reference
  here.** This area post-dates what this file can vouch for. Search before citing.

## Authoring & world composition

- **Galin, E., Guérin, E., Peytavie, A., Cordonnier, G., Cani, M.-P., Benes, B. & Gain, J.
  (2019).** *A Review of Digital Terrain Modeling.* Computer Graphics Forum 38(2), 553–577
  (Eurographics 2019 STAR). — **The survey.** Maps procedural, simulation, and example-based
  terrain methods and how they compose. Read first when choosing an architecture for a whole
  multi-biome world (`13`).
- **Génevaux, J.-D., Galin, É., Peytavie, A., Guérin, É., Briquet, C., Grosbellet, F. & Beneš, B.
  (2015).** *Terrain Modelling from Feature Primitives.* Computer Graphics Forum 34(6). — A
  construction tree of feature primitives (peaks, ridges, rivers, cliffs) composited into terrain.
  The authoring model for placing named features on a map (`13`).
- **Emilien, A., Vimont, U., Cani, M.-P., Poulin, P. & Beneš, B. (2015).** *WorldBrush:
  Interactive Example-based Synthesis of Procedural Virtual Worlds.* ACM TOG 34(4), SIGGRAPH '15.
  — Example-based authoring of the *distributions* of world elements: paint a region "like this
  one" (`13`).

## Geological formation

- **Beneš, B. & Forsbach, R. (2001).** *Layered Data Representation for Visual Simulation of
  Terrain Erosion.* SCCG 2001. — Layered material representation.
- **Peytavie, A., Galin, E., Grosjean, J. & Mérillou, S. (2009).** *Arches: a Framework for
  Modeling Complex Terrains.* Computer Graphics Forum 28(2) (Eurographics 2009). — **The
  answer when a heightfield can't represent the landform.** Per-column material stacks with
  voids: arches, overhangs, caves.
- **Paris, A., Guérin, É., Peytavie, A., Collon, P. & Galin, E. (2021).** *Synthesizing
  Geologically Coherent Cave Networks.* Computer Graphics Forum. — Karst cave networks.
- **Ford, D. & Williams, P. (2007).** *Karst Hydrogeology and Geomorphology.* Wiley. — The standard
  karst reference. Tower (fenglin) and cone (fengcong) karst as differential dissolution and
  vertical lowering to a base level (`11`). No graphics paper exists for tower-karst surface
  morphology; cite this for the mechanism.
- **Stora, D., Agliati, P.-O., Cani, M.-P., Neyret, F. & Gascuel, J.-D. (1999).** *Animating Lava
  Flows.* Graphics Interface '99.
- **Culling, W.E.H. (1960).** *Analytical Theory of Erosion.* Journal of Geology 68(3). —
  Hillslope diffusion / soil creep as `D·∇²h`. The origin of the diffusion term in `04`.

## Glacial & coastal

- **Argudo, O., Galin, E., Peytavie, A., Paris, A. & Guérin, É. (2020).** *Simulation, Modeling
  and Authoring of Glaciers.* ACM TOG 39(6), SIGGRAPH Asia '20. — **The glacier reference.**
  SIA-based flow, erosion, authoring.
- **Glen, J.W. (1955).** *The creep of polycrystalline ice.* Proc. Royal Society A 228. — Glen's
  flow law, `ε̇ = A·τⁿ`, n=3. The physics under every glacier model.
- **Cordonnier, G., Ecormier, P., Galin, E., Gain, J., Benes, B. & Cani, M.-P. (2018).**
  *Interactive Generation of Time-evolving, Snow-Covered Landscapes with Avalanches.* Computer
  Graphics Forum 37(2) (Eurographics 2018).
- **Bruun, P. (1962).** *Sea-level rise as a cause of shore erosion.* J. Waterways & Harbors
  Division, ASCE 88. — The Bruun rule. **Coastal engineering, not terrain generation.** Cited
  here because there *is* no graphics paper for coastal erosion, and saying so is the honest
  answer (`12`).
- **Komar, P.D. & Inman, D.L. (1970).** *Longshore sand transport on beaches.* Journal of
  Geophysical Research 75(30), 5914–5927. — The measured basis of the CERC longshore-transport
  formula (the `sin 2α` dependence). Drives spits, tombolos, and barrier islands (`12`). Coastal
  engineering, not graphics.
- **Dean, R.G. (1991).** *Equilibrium beach profiles: characteristics and applications.* Journal of
  Coastal Research 7(1), 53–84. — The `depth ∝ distance^⅔` shoreface profile. Author the nearshore
  as an equilibrium ramp; do not erode a seabed into shape (`12`).
- **Rosenbloom, N.A. & Anderson, R.S. (1994).** *Hillslope and channel evolution in a marine
  terraced landscape, Santa Cruz, California.* Journal of Geophysical Research 99(B7),
  14013–14029. — Marine terraces, and the knickpoint-celerity result `C = K·A^m` used in `04`.
- **Darwin, C. (1842).** *The Structure and Distribution of Coral Reefs.* Smith, Elder & Co. —
  **The subsidence theory of atolls**: volcano → fringing reef → barrier reef → atoll, as the
  island sinks and coral grows up to keep pace with sea level. Confirmed a century later by
  drilling to volcanic basement at Enewetak. Cite it for *why* atolls form (`12`); it is not a
  graphics method.
- **Gilbert, G.K. (1890).** *Lake Bonneville.* USGS Monograph 1. — The foundational study of
  **lacustrine shorelines**: wave-cut lake terraces from a lake-level history, and the
  topset/foreset/bottomset **Gilbert delta**. The freshwater analogue of the marine coastal suite
  (`12`). Not graphics — cite it for the mechanism.

## Climate & ecosystems

- **Smith, R.B. & Barstad, I. (2004).** *A Linear Theory of Orographic Precipitation.* Journal of
  the Atmospheric Sciences 61(12), 1377–1391. — **The orographic precipitation reference.**
- **Deussen, O., Hanrahan, P., Lintermann, B., Měch, R., Pharr, M. & Prusinkiewicz, P. (1998).**
  *Realistic Modeling and Rendering of Plant Ecosystems.* SIGGRAPH '98. — **The ecosystem
  reference.** Iterative competition and self-thinning.
- **Měch, R. & Prusinkiewicz, P. (1996).** *Visual Models of Plants Interacting with Their
  Environment.* SIGGRAPH '96. — Open L-systems.
- **Lane, B. & Prusinkiewicz, P. (2002).** *Generating Spatial Distributions for Multilevel
  Models of Plant Communities.* Graphics Interface 2002.
- **Makowski, M., Hädrich, T., Scheffczyk, J., Michels, D.L., Pirk, S. & Palubicki, W. (2019).**
  *Synthetic Silviculture: Multi-scale Modeling of Plant Ecosystems.* ACM TOG 38(4),
  SIGGRAPH '19.
- **Whittaker, R.H. (1975).** *Communities and Ecosystems* (2nd ed.). — The biome diagram:
  biome as a function of temperature and precipitation. A 2D LUT.
- **Peel, M.C., Finlayson, B.L. & McMahon, T.A. (2007).** *Updated world map of the
  Köppen-Geiger climate classification.* Hydrology and Earth System Sciences 11. — The modern
  Köppen map.

## Hydrology (additional)

- **Strahler, A.N. (1957).** *Quantitative analysis of watershed geomorphology.* Transactions,
  AGU 38(6). — Stream ordering. (Horton 1945 is the predecessor.)
- **Ikeda, S., Parker, G. & Sawai, K. (1981).** *Bend theory of river meanders. Part 1. Linear
  development.* Journal of Fluid Mechanics 112, 363–377. — **The meander-migration model.** Bank
  migration rate ∝ near-bank excess velocity, driven by *upstream-weighted* curvature. The reason
  meanders skew downstream and overturn instead of staying symmetric (`03`).
- **Howard, A.D. & Knutson, T.R. (1984).** *Sufficient conditions for river meandering: A
  simulation approach.* Water Resources Research 20(11). — Meander migration with the upstream
  curvature weighting; the simulation form used for terrain (`03`).
- **Leopold, L.B. & Maddock, T. (1953).** *The hydraulic geometry of stream channels and some
  physiographic implications.* USGS Professional Paper 252. — Channel width/depth scaling with
  discharge. Use for river widening.
- **Beneš, B., Těšínský, V., Hornyš, J. & Bhatia, S.K. (2006).** *Hydraulic Erosion.* Computer
  Animation and Virtual Worlds 17(3–4). — Shallow-water erosion.
- **Montgomery, D.R. & Buffington, J.M. (1997).** *Channel-reach morphology in mountain drainage
  basins.* GSA Bulletin 109(5), 596–611. — **The mountain-channel classification**: cascade /
  step-pool / plane-bed / pool-riffle / dune-ripple by slope. What a river flowing down a mountain
  actually looks like (`03`).
- **Whipple, K.X. (2004).** *Bedrock rivers and the geomorphology of active orogens.* Annual Review
  of Earth and Planetary Sciences 32, 151–185. — Bedrock channels in mountains; the detachment-
  limited regime behind stream power (`03`, `04`).
- **Sklar, L.S. & Dietrich, W.E. (2004).** *A mechanistic model for river incision into bedrock by
  saltating bed load.* Water Resources Research 40(6). — The saltation–abrasion incision model —
  the physics under the stream-power erodibility `K` (`04`).
- **Génevaux, J.-D., Galin, É., Guérin, É., Peytavie, A. & Beneš, B. (2013).** *Terrain Generation
  Using Procedural Models Based on Hydrology.* ACM TOG 32(4), SIGGRAPH '13. — Author terrain from
  its river network first, then raise the relief around it. The graphics reference for
  river-driven terrain (`03`).

## Sediment & bedload

The physics of grain size, transport, and gravel bars — old, canonical, and the grounding for
boulders/cobbles/pebble beaches in a river like the Ardèche (`04`).

- **Udden, J.A. (1914).** *Mechanical composition of clastic sediments.* GSA Bulletin 25. — The
  φ grade scale, refined by Wentworth.
- **Wentworth, C.K. (1922).** *A scale of grade and class terms for clastic sediments.* Journal of
  Geology 30(5), 377–392. — **The grain-size classification** (boulder / cobble / pebble / … ).
- **Sternberg, H. (1875).** *Untersuchungen über Längen- und Querprofil geschiebeführender
  Flüsse.* Zeitschrift für Bauwesen 25. — **Downstream fining**, `D = D0·e^(−αx)`. Boulders at the
  source, rounded pebbles then sand downstream.
- **Shields, A. (1936).** *Anwendung der Ähnlichkeitsmechanik und der Turbulenzforschung auf die
  Geschiebebewegung.* Mitteilungen der Preußischen Versuchsanstalt für Wasserbau und Schiffbau,
  Heft 26, Berlin (doctoral thesis). — **Critical shear stress for incipient motion.** Which grains
  move at a given flow; the water twin of Bagnold's wind threshold (`05`).
- **Meyer-Peter, E. & Müller, R. (1948).** *Formulas for bed-load transport.* Proc. 2nd Meeting
  IAHR, Stockholm, 39–64. — **The canonical bedload transport formula**, `q_b ∝ (τ*−τ*_c)^1.5`.
- **Parker, G. (1990).** *Surface-based bedload transport relation for gravel rivers.* Journal of
  Hydraulic Research 28(4), 417–436. — The modern gravel-bed relation; surface armour and grain
  hiding.
- **Leopold, L.B., Wolman, M.G. & Miller, J.P. (1964).** *Fluvial Processes in Geomorphology.*
  Freeman. — The classic text: competence, bars, sorting, imbrication. General grounding for the
  gravel-bar and pebble-beach material.

## Analysis (additional)

- **Zakšek, K., Oštir, K. & Kokalj, Ž. (2011).** *Sky-View Factor as a Relief Visualization
  Technique.* Remote Sensing 3(2).
- **Riley, S.J., DeGloria, S.D. & Elliot, R. (1999).** *A terrain ruggedness index that
  quantifies topographic heterogeneity.* Intermountain Journal of Sciences 5(1–4).
- **Felzenszwalb, P.F. & Huttenlocher, D.P. (2012).** *Distance Transforms of Sampled
  Functions.* Theory of Computing 8. — O(n) exact Euclidean distance transform. (Danielsson
  1980 and Meijster et al. 2000 are the alternatives.)

## Filtering

- **Tomasi, C. & Manduchi, R. (1998).** *Bilateral Filtering for Gray and Color Images.* ICCV '98.
- **He, K., Sun, J. & Tang, X. (2010).** *Guided Image Filtering.* ECCV 2010; extended in IEEE
  PAMI 35(6), 2013. — **Better than bilateral for terrain**: O(1) per cell, no gradient reversal.
- **Perona, P. & Malik, J. (1990).** *Scale-space and edge detection using anisotropic
  diffusion.* IEEE PAMI 12(7).
- **Serra, J. (1982).** *Image Analysis and Mathematical Morphology.* Academic Press.
- **Frisken, S.F., Perry, R.N., Rockwood, A.P. & Jones, T.R. (2000).** *Adaptively Sampled
  Distance Fields: A General Representation of Shape for Computer Graphics.* SIGGRAPH 2000.

## Conversion & runtime (additional)

- **Lorensen, W.E. & Cline, H.E. (1987).** *Marching Cubes: A High Resolution 3D Surface
  Construction Algorithm.* SIGGRAPH '87.
- **Ju, T., Losasso, F., Schaefer, S. & Warren, J. (2002).** *Dual Contouring of Hermite Data.*
  ACM TOG 21(3), SIGGRAPH '02.
- **Duchaineau, M., Wolinsky, M., Sigeti, D.E., Miller, M.C., Aldrich, C. & Mineev-Weinstein,
  M.B. (1997).** *ROAMing Terrain: Real-time Optimally Adapting Meshes.* IEEE Visualization '97.
- **Cignoni, P., Ganovelli, F., Gobbetti, E., Marton, F., Ponchio, F. & Scopigno, R. (2003).**
  *BDAM — Batched Dynamic Adaptive Meshes for High Performance Terrain Visualization.* Computer
  Graphics Forum 22(3).
- **Ulrich, T. (2002).** *Rendering Massive Terrains using Chunked Level of Detail Control.*
  SIGGRAPH 2002 course notes. — Course notes, not a paper.
- **Strugar, F. (2009).** *Continuous Distance-Dependent Level of Detail for Rendering
  Heightmaps.* Journal of Graphics Tools 14(4). — CDLOD.
- Virtual texturing: **Barrett, S. (2008)**, *Sparse Virtual Textures* (GDC) and **Mittring, M.
  (2008)**, *Advanced Virtual Texture Topics* (SIGGRAPH course). Talks, not papers — cite as such.

## Reading order

If someone is implementing from scratch and asks what to read first:

1. **Braun & Willett 2013** — if the map is large. It is the highest-leverage paper here; the
   solver is three lines and it makes the difference between hours and seconds.
2. **Barnes et al. 2014** — because nothing downstream works without depression handling.
3. **Mei et al. 2007** — if the map is small-to-medium and you want water.
4. **Musgrave et al. 1989** — short, and it grounds thermal erosion.
5. **Bridson 2007** — two pages, and you'll need scatter eventually.

Everything else is reference-on-demand.
