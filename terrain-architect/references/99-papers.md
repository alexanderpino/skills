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
- **Bridson, R., Hourihan, J. & Nordenstam, M. (2007).** *Curl-Noise for Procedural Fluid Flow.*
  ACM TOG 26(3), SIGGRAPH '07. — Divergence-free noise.

## Tectonics & landscape evolution

- **Cordonnier, G., Braun, J., Cani, M.-P., Benes, B., Galin, E., Peytavie, A. & Guérin, E.
  (2016).** *Large Scale Terrain Generation from Tectonic Uplift and Fluvial Erosion.*
  Computer Graphics Forum 35(2), 165–175 (Eurographics 2016). — Tectonic uplift + stream power +
  lake-graph local-minima handling. **This is the "2015 tectonics" paper and the "2016 stream
  power" paper — they are one and the same.** (Jean Braun is a co-author — the same Braun as the
  solver below, which is why the paper builds on it.)
- **Cordonnier, G., Galin, E., Gain, J., Benes, B., Guérin, E., Peytavie, A. & Cani, M.-P.
  (2017).** *Authoring Landscapes by Combining Ecosystem and Terrain Erosion Simulation.*
  ACM TOG 36(4), article 134, SIGGRAPH '17. — The follow-up; couples vegetation to erosion.
- **Cortial, Y., Peytavie, A., Galin, E. & Guérin, E. (2019).** *Procedural Tectonic Planets.*
  Computer Graphics Forum 38(2), Eurographics 2019. — Whole-**planet** terrain from approximated
  plate subduction/collision under user-controlled plate motion; continents, ridges, arcs, then
  amplified. The graphics anchor for spherical tectonics (`25`).
- **McKenzie, D.P. & Parker, R.L. (1967).** *The North Pacific: an example of tectonics on a
  sphere.* Nature 216, 1276–1280. — The founding "paving-stone" result: rigid plates move as
  rotations about an **Euler pole**; independently **Morgan, W.J. (1968)**, *Rises, trenches, great
  faults, and crustal blocks*, JGR 73(6), 1959–1982. Transform faults follow small circles about
  the pole; spreading rate ∝ sin(angular distance from it) (`25`).
- **Braun, J. & Willett, S.D. (2013).** *A very efficient O(N), implicit and parallel method to
  solve the stream power equation governing fluvial incision and landscape evolution.*
  Geomorphology 180–181, 170–179. — **The paper that matters for stream power.** The O(N)
  stack ordering + unconditionally stable implicit solver. Known in the geoscience community
  as the basis of FastScape.
- **Cordonnier, G., Bovy, B. & Braun, J. (2019).** *A versatile, linear complexity algorithm for
  flow routing in topographies with depressions.* Earth Surface Dynamics 7(2), 549–562. —
  Basin graph + minimum-spanning-tree depression routing. This is the specific general routing
  source; do not conflate it with the 2016 terrain-generation application.
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

### Isostasy, flexure & seafloor tectonics

- **Turcotte, D.L. & Schubert, G. (2014).** *Geodynamics* (3rd ed.). Cambridge University Press,
  623 pp. — Standard text for Airy isostasy (root `r = ρc·h/(ρm−ρc)`) and thin-elastic-plate flexure
  (`D∇⁴w + Δρ·g·w = q`); the grounding for the isostasy section (`02`).
- **Watts, A.B. (2001).** *Isostasy and Flexure of the Lithosphere.* Cambridge University Press,
  458 pp. — The flexure reference: flexural rigidity `D = E·Te³/[12(1−ν²)]`, effective elastic
  thickness `Te`, and the flexural response kernel solved by convolution (`02`).
- **Peltier, W.R. (1974).** *The impulse response of a Maxwell Earth.* Reviews of Geophysics and
  Space Physics 12(4), 649–669. — Viscoelastic (Maxwell) Earth response; the basis of glacial
  isostatic adjustment as a lagged relaxation (`02`, `12`).
- **Peltier, W.R. (2004).** *Global glacial isostasy and the surface of the ice-age Earth: the
  ICE-5G (VM2) model and GRACE.* Annual Review of Earth and Planetary Sciences 32, 111–149. —
  The modern GIA ice-history + mantle-viscosity model; raised/tilted post-glacial shorelines (`02`).
- **Molnar, P. & England, P. (1990).** *Late Cenozoic uplift of mountain ranges and global climate
  change: chicken or egg?* Nature 346(6279), 29–34. — **Erosional isostasy**: incision unloads a
  range and the summits rebound by ~`ρc/ρm`, so peak uplift is not by itself proof of tectonic
  uplift (`02`).
- **Parsons, B. & Sclater, J.G. (1977).** *An analysis of the variation of ocean floor bathymetry
  and heat flow with age.* Journal of Geophysical Research 82(5), 803–827. — The **√age**
  ridge-flank subsidence law (`d = d₀ + C·√t`, `d₀ ≈ 2500 m`, `C ≈ 350 m/√Myr`) (`12`).
- **Stein, C.A. & Stein, S. (1992).** *A model for the global variation in oceanic depth and heat
  flow with lithospheric age.* Nature 359(6391), 123–129. — GDH1 plate model; the flattening of old
  seafloor the half-space law misses (`12`).
- **Wilson, J.T. (1963).** *A possible origin of the Hawaiian Islands.* Canadian Journal of Physics
  41(6), 863–870. — The **hotspot** hypothesis: an age-progressive volcanic chain over a fixed
  source (`11`, `12`). A hypothesis, still debated — attribute as such.
- **Morgan, W.J. (1971).** *Convection plumes in the lower mantle.* Nature 230(5288), 42–43. — The
  mantle-plume mechanism proposed for hotspots (`12`).
- **Hess, H.H. (1946).** *Drowned ancient islands of the Pacific Basin.* American Journal of Science
  244(11), 772–791. — **Guyots**: wave-truncated seamounts carried down by subsidence (`12`).

## Hydraulic erosion

- **Musgrave, F.K., Kolb, C.E. & Mace, R.S. (1989).** *The Synthesis and Rendering of Eroded
  Fractal Terrains.* SIGGRAPH '89. — The origin of both thermal erosion and grid-based
  hydraulic erosion in graphics. Everything downstream traces here.
- **O'Brien, J.F. & Hodgins, J.K. (1995).** *Dynamic Simulation of Splashing Fluids.* Proc.
  Computer Animation '95, 198–205. — The origin of the **virtual-pipe height-field water model**: a
  fluid surface as height columns, each coupled to its eight neighbours by a pipe that moves water on
  the head difference. Not an erosion paper; Mei 2007 applies this pipe abstraction to erosion. The
  lineage runs O'Brien & Hodgins → Mei → Št'ava.
- **Mei, X., Decaudin, P. & Hu, B.-G. (2007).** *Fast Hydraulic Erosion Simulation and
  Visualization on GPU.* Pacific Graphics 2007. — **The virtual pipe model applied to erosion.**
  Grid-based, not particle-based. The 8-step formulation with the outflow scaling factor.
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
- **Tsoar, H. (1983).** *Wind tunnel modeling of echo and climbing dunes.* In M.E. Brookfield &
  T.S. Ahlbrandt (eds), *Eolian Sediments and Processes*, Developments in Sedimentology 38, Elsevier,
  Amsterdam, pp. 247–259. — **Anchored (obstacle) dunes.** The windward-slope angle sets whether sand
  is trapped upwind (echo), mantles the face (climbing), or falls into the lee — the gate `05` branches
  on (`05`, `16`).
- **Hesp, P.A. (1981).** *The formation of shadow dunes.* Journal of Sedimentary Petrology 51(1),
  101–112. — The tapering **sand shadow** in the lee of a single obstacle; the small-obstacle end of
  the shadow-zone capture, kin to the nebkha (`05`, `13`, `16`).
- **Qian, G., Dong, Z., Luo, W. & Lu, J. (2011).** *Mean airflow patterns upwind of topographic
  obstacles and their implications for the formation of echo dunes: a wind tunnel simulation of the
  effects of windward slope.* Journal of Geophysical Research: Earth Surface 116, F04026. — Quantifies
  the windward-angle gate: the boundary layer separates into an upwind reverse eddy above **~60°** (the
  echo-dune regime); gentler faces give climbing dunes (`05`, `16`).
- **Pye, K. & Tsoar, H. (2009).** *Aeolian Sand and Sand Dunes.* Springer, Berlin (1st ed. Unwin
  Hyman, London, 1990). — The synthesis of aeolian bedforms, including the topographically-controlled
  (anchored) dune family — echo, climbing, falling and lee dunes (`05`).
- **Wilson, I.G. (1972).** *Aeolian bedforms — their development and origins.* Sedimentology 19(3–4),
  173–210. — The **bedform size hierarchy**: ripples → dunes → draa, and compound/complex mega-dunes by
  superimposition (`05`).
- **Bowler, J.M. (1973).** *Clay dunes: their occurrence, formation and environmental significance.*
  Earth-Science Reviews 9(4), 315–338. — **Lunettes**: source-bordering clay/gypsum-pellet ridges on the
  lee margin of a deflating playa (`16`, `05`).
- **Hesp, P.A. (2002).** *Foredunes and blowouts: initiation, geomorphology and dynamics.* Geomorphology
  48(1–3), 245–268. — **Blowouts** as deflation hollows in vegetated sand; the seed of a parabolic dune
  (`05`, `13`).

## Mass wasting

- **Montgomery, D.R. & Dietrich, W.E. (1994).** *A physically based model for the topographic
  control on shallow landsliding.* Water Resources Research 30(4), 1153–1171. — **The
  shallow-landslide susceptibility model** (basis of SHALSTAB): wetness from drainage area coupled
  to infinite-slope stability. Failures concentrate in steep, convergent, wet hollows (`05`).
- **Iverson, R.M. (1997).** *The physics of debris flows.* Reviews of Geophysics 35(3), 245–296. —
  The debris-flow physics reference: solid–fluid mixture mechanics. Like Bagnold, cite it for
  *why*, not *how* — it is not implementable as written (`05`).
- **Corominas, J. (1996).** *The angle of reach as a mobility index for small and large landslides.*
  Canadian Geotechnical Journal 33(2), 260–271. — The **runout stop rule**: `L = H/tan(α)`, with the
  reach angle shrinking as volume grows (204 landslides). Big failures run far; small ones don't (`05`).
- **Voellmy, A. (1955).** *Über die Zerstörungskraft von Lawinen.* Schweizerische Bauzeitung 73. —
  The **two-parameter runout friction** (Coulomb `μ` + turbulent `v²/ξ` drag) under RAMMS-class
  avalanche and debris-flow models (`05`).

## Flow routing

- **O'Callaghan, J.F. & Mark, D.M. (1984).** *The extraction of drainage networks from digital
  elevation data.* Computer Vision, Graphics and Image Processing 28(3), 328–344. — D8.
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
- **Barré-Brisebois, C. & Hill, S. (2012).** *Blending in Detail.* blog.selfshadow.com/publications/
  blending-in-detail/. — **Reoriented Normal Mapping (RNM)**: reorient a detail normal to follow the
  base normal — the correct way to combine a terrain base normal with a material detail normal (`08`).
  Blog post, not peer-reviewed.
- **Mishkinis, A. (2013).** *Advanced Terrain Texture Splatting.* GameDev.net. — **Height-based splat
  blending**: per-material depth maps let the more prominent material win the boundary, so sand fills
  the cracks and stone tops stay bare (`08`). Article, not peer-reviewed.
- **Geiss, R. (2007).** *Generating Complex Procedural Terrains Using the GPU.* In *GPU Gems 3*,
  ch. 1, NVIDIA / Addison-Wesley. — GPU procedural terrain (marching cubes) and **triplanar
  texturing** for steep slopes (`08`, `11`). Book chapter.
- **Heitz, E. & Neyret, F. (2018).** *High-Performance By-Example Noise using a Histogram-Preserving
  Blending Operator.* Proceedings of the ACM on Computer Graphics and Interactive Techniques 1(2),
  article 31 (I3D 2018). — **Stochastic / by-example tiling**: hide the repeat of a tiling material
  without the ghosting of naive random tiling (`08`).

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
- **Zhao, Y., Liu, H., Borovikov, I., Beirami, A., Sanjabi, M. & Zaman, K. (2019).** *Multi-theme
  Generative Adversarial Terrain Amplification* (GATA). ACM TOG 38(6), art. 200, SIGGRAPH Asia '19. —
  Learned amplification of low-res terrain to high-res with selectable themes. The principal
  learned-amplification reference after Guérin 2017.
- **Lochner, J., Gain, J., Perche, S., Peytavie, A., Galin, E. & Guérin, É. (2023).** *Interactive
  Authoring of Terrain using Diffusion Models.* Computer Graphics Forum 42(7), Pacific Graphics '23. —
  The safe canonical **diffusion** terrain-authoring cite; user-guided synthesis competitive with cGANs.
- **Hu, Z., Hu, Y., Mo, L., Pan, B. & Wang, Y. (2024).** *Terrain Diffusion Network: Climatic-Aware
  Terrain Generation with Geological Sketch Guidance.* AAAI 2024, 38(11), 12565–12573. — Diffusion with
  geological-sketch and climatic control.
- **Demiray, B.Z., Sit, M. & Demir, I. (2021).** *D-SRGAN: DEM Super-Resolution with Generative
  Adversarial Networks.* SN Computer Science 2(1), 48. — Neural DEM super-resolution; beats
  interpolation baselines but can hallucinate high-frequency detail — verify against ground truth.
- **Feng, H., Xu, L. & De Floriani, L. (2024).** *ImplicitTerrain: a Continuous Surface Model for
  Terrain Data Analysis.* CVPR 2024 Workshop (arXiv:2406.00227). — SIREN-based implicit representation
  for analysis/compression — **not** a generator; don't cite it as one.
- **The moving frontier (verify before citing).** Sketch/style tools (StyleDEM), latent joint
  geometry+texture (TerraFusion), GNN-based example sketching, and neural-implicit *generation* are real
  and active but carry incomplete metadata or preprint-only status. This area moves fast — confirm
  venue and authors against the primary source, and keep the `?` boundary firm (`SKILL.md` frontier
  note; `00`).

## Texture & material synthesis

Generating the *material* appearance (the "rock" texture and its PBR channels), as opposed to the
terrain shape (`08` synthesising a material). The pure-procedural route is N-tier tool practice
(Substance Designer / Gaea material nodes) built on the `01` noise primitives; the by-example route
is below.

- **Efros, A.A. & Leung, T.K. (1999).** *Texture Synthesis by Non-parametric Sampling.* ICCV 1999. —
  The Markov-random-field, grow-pixel-by-pixel classic; the root of by-example synthesis (`08`).
- **Wei, L.-Y. & Levoy, M. (2000).** *Fast Texture Synthesis using Tree-structured Vector
  Quantization.* SIGGRAPH 2000, 479–488. — Two orders of magnitude faster; deterministic search (`08`).
- **Lefebvre, S. & Hoppe, H. (2006).** *Appearance-space Texture Synthesis.* ACM TOG 25(3),
  541–548 (SIGGRAPH '06). — Appearance vectors + dimensionality reduction; parallel, real-time (`08`).
- **Deschaintre, V., Aittala, M., Durand, F., Drettakis, G. & Bousseau, A. (2018).** *Single-Image
  SVBRDF Capture with a Rendering-Aware Deep Network.* ACM TOG 37(4) (SIGGRAPH '18), article 128. —
  Learned recovery of a full PBR set (albedo / normal / specular / roughness) from one flash photo.
  Verify before leaning on it; the field moves fast (`00`, `08`).
- **Heitz, E. & Neyret, F. (2018)** — see *Rendering & output* above; the histogram-preserving blend
  is also how you *tile* a synthesised or scanned material without ghosting.

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
- **Hudec, M.R. & Jackson, M.P.A. (2007).** *Terra infirma: understanding salt tectonics.*
  Earth-Science Reviews 82(1–2), 1–28. — Salt as a viscous fluid, and the argument that **differential
  loading**, not pure buoyancy, usually drives diapirs. The salt-tectonics review (`11`).
- **Jackson, M.P.A. & Hudec, M.R. (2017).** *Salt Tectonics: Principles and Practice.* Cambridge
  University Press, 498 pp. — The textbook: domes, salt walls, withdrawal minibasins, crestal collapse
  grabens (`11`).
- **Talbot, C.J. & Rogers, E.A. (1980).** *Seasonal movements in a salt glacier in Iran.* Science
  208(4442), 395–397. — Namakiers **flow only when wetted** — seasonal, rain-triggered advance (`11`).
- **Talbot, C.J. & Pohjola, V. (2009).** *Subaerial salt extrusions in Iran as analogues of ice
  sheets, streams and glaciers.* Earth-Science Reviews 97(1–4), 155–183. — The canonical **namakier**
  (salt-glacier) morphology paper; arid-only, since halite dissolves in rain (`11`, `12`).
- **Kopf, A.J. (2002).** *Significance of mud volcanism.* Reviews of Geophysics 40(2), 1005. — The
  mud-volcanism review: overpressure-driven rise, gas seepage, compressional settings (`11`).
- **Mazzini, A. & Etiope, G. (2017).** *Mud volcanism: an updated review.* Earth-Science Reviews 168,
  81–112. — Mud-volcano forms — gryphons, salses, calderas, radial flows — and their gas drivers (`11`).
- **Stora, D., Agliati, P.-O., Cani, M.-P., Neyret, F. & Gascuel, J.-D. (1999).** *Animating Lava
  Flows.* Graphics Interface '99. — The graphics lava simulation (SPH, temperature-coupled
  viscosity).
- **Hulme, G. (1974).** *The Interpretation of Lava Flow Morphology.* Geophysical Journal of the
  Royal Astronomical Society 39(2), 361–383. — **Lava as a Bingham (yield-stress) fluid**: the yield
  stress sets flow thickness and predicts levées. Why lava flows have steep snouts and channels
  instead of spreading like water (`11`).
- **Macdonald, G.A. (1953).** *Pahoehoe, aa, and block lava.* American Journal of Science 251(3),
  169–191. — The surface-texture classification: ropey pahoehoe, clinkery ʻaʻā, angular block —
  a material distinction (`11`, `18`).
- **Rowland, S.K. & Walker, G.P.L. (1990).** *Pahoehoe and aa in Hawaii: volumetric flow rate
  controls the lava structure.* Bulletin of Volcanology 52, 615–628. — The transition is a **flow-
  rate threshold** (~5–10 m³/s): pahoehoe below, ʻaʻā above. Expose the eruption rate; the surface
  style falls out (`19`).
- **Miyamoto, H. & Sasaki, S. (1997).** *Simulating lava flows by an improved cellular automata
  method.* Computers & Geosciences 23(3), 283–292. — The gridded lava CA, with the **Monte Carlo
  neighbour selection** that removes square-lattice anisotropy (`19`).
- **Harris, A.J.L. & Rowland, S.K. (2001).** *FLOWGO: a kinematic thermo-rheological model for lava
  flowing in a channel.* Bulletin of Volcanology 63, 20–44. — March a control volume down a
  channel, evolving heat budget and rheology until it stops; validated against Mauna Loa, Kīlauea,
  and Etna flow lengths. The model for *authored* flows along a spline (`19`).
- **MAGFLOW** (INGV Catania — Vicari, Del Negro and colleagues). *Simulations of the 2004 lava flow
  at Etna volcano using the MAGFLOW cellular automata model.* Bulletin of Volcanology (2008), DOI
  10.1007/s00445-007-0168-8. — CA whose evolution function derives from a steady-state
  Navier–Stokes solution for a **Bingham** fluid + simplified heat transfer; run operationally at
  Etna; GPU-ported (*Porting and optimizing MAGFLOW on CUDA*, Annals of Geophysics) (`19`, `15`).
- **Culling, W.E.H. (1960).** *Analytical Theory of Erosion.* Journal of Geology 68(3). —
  Hillslope diffusion / soil creep as `D·∇²h`. The origin of the diffusion term in `04`.

### Explosive volcanism (tephra, PDCs, calderas)

- **Pyle, D.M. (1989).** *The thickness, volume and grainsize of tephra fall deposits.* Bulletin of
  Volcanology 51(1), 1–15. — **Exponential thinning** of an ashfall with distance, `T = T₀·exp(−k·r)`;
  the drape model for a tephra blanket (`11`).
- **Suzuki, T. (1983).** *A theoretical model for dispersion of tephra.* In Shimozuru & Yokoyama
  (eds), *Arc Volcanism: Physics and Tectonics*, Terra Scientific (TERRAPUB), Tokyo, pp. 95–113. —
  First numerical advection–diffusion tephra-dispersal model (a book chapter, not a journal paper) (`11`).
- **Armienti, P., Macedonio, G. & Pareschi, M.T. (1988).** *A numerical model for simulation of
  tephra transport and deposition: applications to May 18, 1980, Mount St. Helens eruption.* JGR
  93(B6), 6463–6476. — Advection–diffusion–sedimentation of ash by grain class (`11`).
- **Bonadonna, C., Connor, C.B., Houghton, B.F., Connor, L., Byrne, M., Laing, A. & Hincks, T.K.
  (2005).** *Probabilistic modeling of tephra dispersal.* JGR 110, B03203. — The TEPHRA2 analytic
  advection–diffusion–sedimentation form (`11`).
- **Sheridan, M.F. (1979).** *Emplacement of pyroclastic flows: a review.* In *Ash-Flow Tuffs*, GSA
  Special Paper 180, 125–136. — Origin of the **energy-line / energy-cone** runout construction (`11`).
- **Malin, M.C. & Sheridan, M.F. (1982).** *Computer-Assisted Mapping of Pyroclastic Surges.*
  Science 217(4560), 637–640. — The **energy-cone** hazard-mapping model: runout where the `H/L`
  energy line clears the topography (`11`). (In *Science*, not JGR.)
- **Dade, W.B. & Huppert, H.E. (1996).** *Emplacement of the Taupo ignimbrite by a dilute turbulent
  flow.* Nature 381, 509–512. — The dilute turbulent-gravity-current (box-model) alternative for
  PDC runout (`11`).
- **Branney, M.J. & Kokelaar, P. (2002).** *Pyroclastic Density Currents and the Sedimentation of
  Ignimbrites.* Geological Society of London Memoir 27, 143 pp. — Ignimbrite emplacement; the welded
  tuff that later erodes into hoodoos/tuff towers (`11`, `20`).
- **Patra, A.K., Bauer, A.C., Nichita, C.C., Pitman, E.B., Sheridan, M.F. et al. (2005).** *Parallel
  adaptive numerical simulation of dry avalanches over natural terrain* (TITAN2D). Journal of
  Volcanology and Geothermal Research 139(1–2), 1–21. — Depth-averaged (Savage–Hutter) granular flow
  with Coulomb friction; the physical tier above the energy cone (`11`).
- **Roche, O. & Druitt, T.H. (2001).** *Onset of caldera collapse during ignimbrite eruptions.*
  Earth and Planetary Science Letters 191(3–4), 191–202. — Roof force balance; coherent piston
  collapse when roof aspect `R/h ≳ 1` (`11`).
- **Geshi, N., Shimano, T., Chiba, T. & Nakada, S. (2002).** *Caldera collapse during the 2000
  eruption of Miyakejima Volcano, Japan.* Bulletin of Volcanology 64(1), 55–68. — Observed
  incremental piston subsidence tracking withdrawn volume (`11`).
- **Cole, J.W., Milner, D.M. & Spinks, K.D. (2005).** *Calderas and caldera structures: a review.*
  Earth-Science Reviews 69(1–2), 1–26. — Caldera types and ring-fault structure (`11`).
- **Acocella, V. (2007).** *Understanding caldera structure and development: an overview of analogue
  models compared to natural calderas.* Earth-Science Reviews 85(3–4), 125–160. — Analogue-model
  synthesis of collapse geometry (`11`).

## Glacial & coastal

- **Argudo, O., Galin, E., Peytavie, A., Paris, A. & Guérin, É. (2020).** *Simulation, Modeling
  and Authoring of Glaciers.* ACM TOG 39(6), SIGGRAPH Asia '20. — **The glacier reference.**
  SIA-based flow, erosion, authoring.
- **Glen, J.W. (1955).** *The creep of polycrystalline ice.* Proc. Royal Society A 228. — Glen's
  flow law, `ε̇ = A·τⁿ`, n=3. The physics under every glacier model.
- **Cuffey, K.M. & Paterson, W.S.B. (2010).** *The Physics of Glaciers* (4th ed.). Academic Press /
  Elsevier, 704 pp. — The glaciology text; the source of the recommended rate-factor value
  `A ≈ 2.4×10⁻²⁴ Pa⁻³ s⁻¹` at 0 °C and its Arrhenius temperature dependence (`12`).
- **Cordonnier, G., Ecormier, P., Galin, E., Gain, J., Benes, B. & Cani, M.-P. (2018).**
  *Interactive Generation of Time-evolving, Snow-Covered Landscapes with Avalanches.* Computer
  Graphics Forum 37(2) (Eurographics 2018).
- **Benn, D.I. & Evans, D.J.A. (2010).** *Glaciers and Glaciation* (2nd ed.). Hodder Education,
  London, 802 pp. — The standard glacial-geomorphology text; the synthesis reference for the whole
  **glacial depositional suite** — moraines, drumlins, eskers, kames, kettles, sandur, till (`12`).
- **Shreve, R.L. (1985).** *Esker characteristics in terms of glacier physics, Katahdin esker system,
  Maine.* GSA Bulletin 96(5), 639–646. — Eskers are casts of subglacial water-filled tunnels; the flow
  follows the **hydraulic potential**, dominated ~11× by the ice-surface gradient, so eskers cross
  divides and climb the bed. Route on the ice surface, not the bed (`12`).
- **Clark, C.D., Hughes, A.L.C., Greenwood, S.L., Spagnolo, M. & Ng, F.S.L. (2009).** *Size and shape
  characteristics of drumlins, derived from a large sample, and associated scaling laws.* Quaternary
  Science Reviews 28(7–8), 677–692. — Drumlin **morphometry**: 250–1000 m long, elongation ~2–4, with
  a maximum-elongation limit `E_max ≈ L^(1/3)`. Author the form from this; genesis stays open (`12`).
- **Kehew, A.E., Piotrowski, J.A. & Jørgensen, F. (2012).** *Tunnel valleys: concepts and
  controversies — a review.* Earth-Science Reviews 113(1–2), 33–58. — The review of subglacial
  **tunnel valleys** and the still-open steady-vs-outburst debate over how they form (`12`).
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
- **Woodroffe, C.D. (1992).** *Mangrove sediments and geomorphology.* In A.I. Robertson & D.M. Alongi
  (eds), *Tropical Mangrove Ecosystems*, Coastal and Estuarine Studies 41, pp. 7–41. American
  Geophysical Union. — **Mangroves as a geomorphic agent**: trapping mud, building intertidal flats,
  prograding tropical muddy shorelines (`12`).
- **Furukawa, K., Wolanski, E. & Mueller, H. (1997).** *Currents and sediment transport in mangrove
  forests.* Estuarine, Coastal and Shelf Science 44(3), 301–310. — Canopy/root drag traps ~80% of the
  suspended sediment a spring tide carries in; ~0.1 cm/yr accretion (`12`).
- **Alongi, D.M. (2008).** *Mangrove forests: resilience, protection from tsunamis, and responses to
  global climate change.* Estuarine, Coastal and Shelf Science 76(1), 1–13. — Mangrove soils **keep
  pace with sea-level rise** via mineral + organic surface-elevation gain (`12`).
- **Otvos, E.G. & Price, W.A. (1979).** *Problems of chenier genesis and terminology — an overview.*
  Marine Geology 31(3–4), 251–263. — **Cheniers**: coarse sand/shell ridges resting on mudflat, marking
  lulls in mud supply (`12`).
- **Augustinus, P.G.E.F. (1989).** *Cheniers and chenier plains: a general introduction.* Marine
  Geology 90(4), 219–229. — Chenier-plain formation as episodic wave reworking during mud-supply lulls
  on a prograding muddy coast (`12`).
- **Otvos, E.G. (2000).** *Beach ridges — definitions and significance.* Geomorphology 32(1–2), 83–108.
  — The chenier-vs-beach-ridge distinction: substrate (mud beneath the ridges) is the discriminator (`12`).
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

### Glacial outburst floods & megafloods

- **Nye, J.F. (1976).** *Water flow in glaciers: jökulhlaups, tunnels and veins.* Journal of
  Glaciology 17(76), 181–207. — The **tunnel-enlargement runaway**: a subglacial conduit melts wider
  as discharge rises, giving the exponential-rise / abrupt-cutoff outburst hydrograph (`12`).
- **Clarke, G.K.C. (1982).** *Glacier outburst floods from "Hazard Lake", Yukon, and the problem of
  flood magnitude prediction.* Journal of Glaciology 28(98), 3–21. — Nye theory extended with
  reservoir/temperature effects (`12`).
- **Clarke, G.K.C. (2003).** *Hydraulics of subglacial outburst floods: new insights from the
  Spring–Hutter formulation.* Journal of Glaciology 49(165), 299–313. — The modern jökulhlaup model (`12`).
- **Walder, J.S. & Costa, J.E. (1996).** *Outburst floods from glacier-dammed lakes: the effect of
  mode of lake drainage on flood magnitude.* Earth Surface Processes and Landforms 21(8), 701–723. —
  Tunnel drainage vs bodily ice-dam failure; the latter peaks higher and sharper (`12`).
- **Björnsson, H. (2003).** *Subglacial lakes and jökulhlaups in Iceland.* Global and Planetary
  Change 35(3–4), 255–271. — The Icelandic type locality (`12`).
- **Bretz, J H. (1923).** *The Channeled Scabland of the Columbia Plateau.* Journal of Geology
  31(8), 617–649. — The founding (long-ridiculed, later vindicated) megaflood interpretation (`12`).
- **Bretz, J H. (1969).** *The Lake Missoula floods and the Channeled Scabland.* Journal of Geology
  77(5), 505–543. — The mature statement of the flood hypothesis (`12`).
- **Baker, V.R. (1973).** *Paleohydrology and Sedimentology of Lake Missoula Flooding in Eastern
  Washington.* GSA Special Paper 144, 79 pp. — The quantitative paleohydrology: scabland, coulees,
  giant current ripples, streamlined residual islands (`12`).
- **Baker, V.R. & Nummedal, D. (eds) (1978).** *The Channeled Scabland.* NASA Planetary Geology
  Program, 186 pp. — Field guidebook to the megaflood landforms (formally published, not
  journal-refereed) (`12`).

### Turbidity currents & submarine deposits

- **Parker, G., Fukushima, Y. & Pantin, H.M. (1986).** *Self-accelerating turbidity currents.*
  Journal of Fluid Mechanics 171, 145–181. — The layer-averaged 3-/4-equation model and
  **autosuspension**; the underwater sibling of the fluvial machinery (`12`).
- **Middleton, G.V. (1993).** *Sediment deposition from turbidity currents.* Annual Review of Earth
  and Planetary Sciences 21, 89–114. — Deposition mechanics and the fining-upward record (`12`).
- **Meiburg, E. & Kneller, B. (2010).** *Turbidity currents and their deposits.* Annual Review of
  Fluid Mechanics 42, 135–156. — The modern review; submarine canyons and fans (`12`).
- **Bouma, A.H. (1962).** *Sedimentology of Some Flysch Deposits.* Elsevier, 168 pp. — The **Bouma
  sequence** (Ta–Te): the vertical structure a waning turbidity current leaves (`12`).

### Coral as ecosystem (growth form, zonation, spur-and-groove)

- **Graus, R.R. & Macintyre, I.G. (1976).** *Light control of growth form in colonial reef corals:
  computer simulation.* Science 193(4256), 895–897. — Light alone selects colony growth form, by
  simulation; the driver behind depth-zoned coral morphology (`12`, `07`). (In *Science*.)
- **Chappell, J. (1980).** *Coral morphology, diversity and reef growth.* Nature 286, 249–252. —
  Coral form as a function of **light and mechanical wave stress** together (`12`).
- **Done, T.J. (1982).** *Patterns in the distribution of coral communities across the central Great
  Barrier Reef.* Coral Reefs 1(2), 95–107. — Coral **zonation** across the reef profile (`12`).
- **Done, T.J. (1983).** *Coral zonation: its nature and significance.* In Barnes (ed.),
  *Perspectives on Coral Reefs*, 107–147. — The zonation synthesis (`12`).
- **Kaandorp, J.A., Lowe, C.P., Frenkel, D. & Sloot, P.M.A. (1996).** *Effect of nutrient diffusion
  and flow on coral morphology.* Physical Review Letters 77(11), 2328–2331. — Accretive growth as a
  diffusion-vs-flow (Péclet) competition: open branches vs compact colonies (`12`).
- **Merks, R.M.H., Hoekstra, A.G., Kaandorp, J.A. & Sloot, P.M.A. (2003).** *Models of coral growth:
  spontaneous branching, compactification and the Laplacian growth assumption.* Journal of
  Theoretical Biology 224(2), 153–166. — Branching morphogenesis (`12`).
- **Kaandorp, J.A. & Kübler, J.E. (2001).** *The Algorithmic Beauty of Seaweeds, Sponges and
  Corals.* Springer. — The accretive-growth reference for benthic form (`12`).
- **Kaandorp, J.A. et al. (2005).** *Morphogenesis of the branching reef coral Madracis mirabilis.*
  Proceedings of the Royal Society B 272(1559), 127–133. — Validated single-species growth model (`12`).
- **Shinn, E.A. (1963).** *Spur and groove formation on the Florida Reef Tract.* Journal of
  Sedimentary Petrology 33(2), 291–303. — The classic **spur-and-groove** description (`12`).
- **Storlazzi, C.D., Logan, J.B. & Field, M.E. (2003).** *Quantitative morphology of a fringing reef
  tract from high-resolution laser bathymetry: southern Molokai, Hawaii.* GSA Bulletin 115(11),
  1344–1355. — Wave control on reef morphology (`12`).
- **Duce, S., Vila-Concejo, A., Hamylton, S.M. et al. (2016).** *A morphometric assessment and
  classification of coral reef spur and groove morphology.* Geomorphology 265, 68–83. — Groove length
  and orientation track wave exposure across thousands of grooves (`12`).

## Climate & ecosystems

- **Smith, R.B. & Barstad, I. (2004).** *A Linear Theory of Orographic Precipitation.* Journal of
  the Atmospheric Sciences 61(12), 1377–1391. — **The orographic precipitation reference.**
- **Jackson, P.S. & Hunt, J.C.R. (1975).** *Turbulent wind flow over a low hill.* Quarterly Journal
  of the Royal Meteorological Society 101, 929–955. — The **crest speed-up** theory: fractional
  wind speed-up over a hill scales with its slope. The anchor for terrain-adjusted wind (`13`).
- **Sherman, C.A. (1978).** *A Mass-Consistent Model for Wind Fields over Complex Terrain.* Journal
  of Applied Meteorology 17(3), 312–319. — MATHEW: adjust an interpolated wind field in a weighted
  least-squares sense to satisfy continuity. The divergence-cleanup step for terrain wind (`13`).
- **Rothermel, R.C. (1972).** *A Mathematical Model for Predicting Fire Spread in Wildland Fuels.*
  USDA Forest Service Research Paper INT-115, Ogden, 40 pp. — **The fire-spread model** (still the
  core of operational fire-behaviour systems): spread accelerates upslope and downwind. The shape
  of a burn scar (`13`).
- **Shakesby, R.A. & Doerr, S.H. (2006).** *Wildfire as a hydrological and geomorphological agent.*
  Earth-Science Reviews 74, 269–307. — **The post-fire geomorphology review**: soil water
  repellency, runoff amplification, post-fire erosion and debris flows. Why a burn scar gullies in
  its first wet season (`13`, `05`).
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
- **Holdridge, L.R. (1947).** *Determination of world plant formations from simple climatic data.*
  Science 105(2727), 367–368. — The **life-zone** system: vegetation formation from biotemperature and
  precipitation (`13`).
- **Holdridge, L.R. (1967).** *Life Zone Ecology* (rev. ed.). Tropical Science Center, San José, Costa
  Rica, 206 pp. — The full triangular chart with explicit **altitudinal belts** (basal → nival)
  parallel to the latitudinal zones; the reference for named vegetation belts up a mountain (`13`).
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
- **Leopold, L.B. & Wolman, M.G. (1957).** *River channel patterns: Braided, meandering, and
  straight.* USGS Professional Paper 282-B. — The planform classification; braiding starts as a
  central bar of stalled coarse bedload (`03`).
- **Beneš, B., Těšínský, V., Hornyš, J. & Bhatia, S.K. (2006).** *Hydraulic Erosion.* Computer
  Animation and Virtual Worlds 17(2), 99–108. — Shallow-water erosion.
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

### River terraces

- **Bull, W.B. (1990).** *Stream-terrace genesis: implications for soil development.* Geomorphology
  3(3–4), 351–367. — The strath-vs-fill terrace distinction and the base-level/threshold framing (`03`).
- **Bull, W.B. (1991).** *Geomorphic Responses to Climatic Change.* Oxford University Press, 326 pp.
  — Climate-driven aggradation/degradation cycles; complex response (`03`).
- **Merritts, D.J., Vincent, K.R. & Wohl, E.E. (1994).** *Long river profiles, tectonism, and
  eustasy: a guide to interpreting fluvial terraces.* JGR 99(B7), 14031–14050. — Straths record
  steady vertical incision via lateral channel wandering (`03`).
- **Pazzaglia, F.J. & Brandon, M.T. (2001).** *A fluvial record of long-term steady-state uplift and
  erosion across the Cascadia forearc high.* American Journal of Science 301(4–5), 385–431. — The
  steady-state incision + strath-genesis model (`03`).
- **Hancock, G.S. & Anderson, R.S. (2002).** *Numerical modeling of fluvial strath-terrace formation
  in response to oscillating climate.* GSA Bulletin 114(9), 1131–1142. — **The numerical model**:
  cover-limited bedrock incision + lateral erosion under oscillating supply; the terrace-loop
  algorithm (`03`).
- **Limaye, A.B.S. & Lamb, M.P. (2016).** *Numerical model predictions of autogenic fluvial terraces
  and comparison to climate change expectations.* JGR: Earth Surface 121(3), 512–544. — Terraces can
  form **autogenically**, with no external forcing; the caution against over-reading a terrace flight (`03`).

### River avulsion & delta lobes

- **Slingerland, R. & Smith, N.D. (2004).** *River avulsions and their deposits.* Annual Review of
  Earth and Planetary Sciences 32, 257–285. — The canonical review; the **setup vs trigger**
  distinction (`03`).
- **Mohrig, D., Heller, P.L., Paola, C. & Lyons, W.J. (2000).** *Interpreting avulsion process from
  ancient alluvial sequences.* GSA Bulletin 112(12), 1787–1803. — The ~one-channel-depth
  **superelevation** threshold in the rock record (`03`).
- **Jerolmack, D.J. & Mohrig, D. (2007).** *Conditions for branching in depositional rivers.*
  Geology 35(5), 463–466. — The avulsion timescale (`T_A ≈ depth / aggradation rate`) and the
  single-thread-vs-branching criterion (`03`).
- **Jerolmack, D.J. & Paola, C. (2007).** *Complexity in a cellular model of river avulsion.*
  Geomorphology 91(3–4), 259–270. — A cellular, heightfield-native avulsion model (`03`).
- **Mackey, S.D. & Bridge, J.S. (1995).** *Three-dimensional model of alluvial stratigraphy: theory
  and applications.* Journal of Sedimentary Research 65B(1), 7–31. — 3-D stochastic avulsion with
  slope-ratio + flood-stage rules (`03`).
- **Coleman, J.M. (1988).** *Dynamic changes and processes in the Mississippi River delta.* GSA
  Bulletin 100(7), 999–1015. — Delta-lobe switching timescales (`03`).
- **Roberts, H.H. (1997).** *Dynamic changes of the Holocene Mississippi River delta plain: the
  delta cycle.* Journal of Coastal Research 13(3), 605–627. — The six-lobe **delta cycle** (`03`).

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
- **Weiss, A. (2001).** *Topographic Position and Landforms Analysis.* Poster, ESRI User
  Conference, San Diego. — The **topographic position index** (TPI): elevation minus its
  neighbourhood mean, at multiple radii, to classify ridge/slope/valley positions. Widely
  used, **not peer-reviewed** — an F-tier convenience, cite it as such (`06`).
- **Felzenszwalb, P.F. & Huttenlocher, D.P. (2012).** *Distance Transforms of Sampled
  Functions.* Theory of Computing 8. — O(n) exact Euclidean distance transform. (Danielsson
  1980 and Meijster et al. 2000 are the alternatives.)

## Filtering

- **Tukey, J.W. (1977).** *Exploratory Data Analysis.* Addison-Wesley. — Origin of the
  **median filter** (running median), the despike tool for salt-and-pepper outliers. A book,
  not an algorithm paper — cite it as the source of the idea, not a method paper (`10`).
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
  Heightmaps.* Journal of Graphics, GPU, and Game Tools 14(4). — CDLOD.
- Virtual texturing: **Barrett, S. (2008)**, *Sparse Virtual Textures* (GDC) and **Mittring, M.
  (2008)**, *Advanced Virtual Texture Topics* (SIGGRAPH course). Talks, not papers — cite as such.

### Planetary / spherical domains

- **Chan, F.K. & O'Neill, E.M. (1975).** *Feasibility Study of a Quadrilateralized Spherical Cube
  Earth Data Base.* Computer Sciences Corp., EPRF Technical Report 2-75. — The **quadrilateralized
  spherical cube** (later the COBE quad-sphere); origin of the cube-sphere grid (`08`).
- **Sadourny, R. (1972).** *Conservative finite-difference approximations of the primitive equations
  on quasi-uniform spherical grids.* Monthly Weather Review 100(2), 136–144. — The cube-based
  quasi-uniform grid; precursor of the modern cubed sphere (`08`).
- **Ronchi, C., Iacono, R. & Paolucci, P.S. (1996).** *The "Cubed Sphere": a new method for the
  solution of partial differential equations in spherical geometry.* Journal of Computational
  Physics 124(1), 93–114. — The **equiangular** gnomonic cubed sphere; near-uniform cell area (`08`).
- **Górski, K.M., Hivon, E., Banday, A.J. et al. (2005).** *HEALPix: a framework for high-resolution
  discretization and fast analysis of data distributed on the sphere.* The Astrophysical Journal
  622(2), 759–771. — The equal-area, iso-latitude spherical pixelisation; a seam-free alternative (`08`).
- **Snyder, J.P. (1987).** *Map Projections — A Working Manual.* USGS Professional Paper 1395,
  383 pp. — Projection scale factors and distortion; divide gradients by the scale factor `h` or
  erosion biases toward high-distortion regions (`08`).
- **Liao, C., Tesfa, T., Duan, Z. & Leung, L.R. (2020).** *Watershed delineation on a hexagonal mesh
  grid.* Environmental Modelling & Software 128, 104702. — HexWatershed: mesh-independent flow
  routing on a hexagonal DGGS — seam-free spherical hydrology (`08`, `03`).
- **Liao, C., Engwirda, D., Cooper, M.G., Li, M. & Fang, Y. (2025).** *Discrete global grid
  system-based flow routing datasets in the Amazon and Yukon basins.* Earth System Science Data 17,
  2035–2062. — Flow routing on an icosahedral equal-area (ISEA) DGGS (`08`, `03`).

### DEM & sensor realism

- **Hutchinson, M.F. (1989).** *A new procedure for gridding elevation and stream line data with
  automatic removal of spurious pits.* Journal of Hydrology 106(3–4), 211–232. — ANUDEM; drainage-
  enforced interpolation that removes pits during gridding (`08`, `03`).
- **Reuter, H.I., Nelson, A. & Jarvis, A. (2007).** *An evaluation of void-filling interpolation
  methods for SRTM data.* International Journal of Geographical Information Science 21(9), 983–1008. —
  Void-fill by void size × terrain; basis of the CGIAR-CSI hole-filled SRTM (`08`).
- **Axelsson, P. (2000).** *DEM generation from laser scanner data using adaptive TIN models.*
  International Archives of Photogrammetry and Remote Sensing XXXIII(B4), 110–117. — Progressive-
  densification TIN — the bare-earth lidar filter (`08`).
- **Zhang, K., Chen, S.-C., Whitman, D., Shyu, M.-L., Yan, J. & Zhang, C. (2003).** *A progressive
  morphological filter for removing nonground measurements from airborne LIDAR data.* IEEE TGRS
  41(4), 872–882. — Growing-window morphological bare-earth filter (`08`).
- **Hanssen, R.F. (2001).** *Radar Interferometry: Data Interpretation and Error Analysis.* Kluwer,
  Dordrecht. — The InSAR reference; the geometry behind radar layover, foreshortening and shadow (`08`).
- **Fisher, P.F. & Tate, N.J. (2006).** *Causes and consequences of error in digital elevation
  models.* Progress in Physical Geography 30(4), 467–489. — DEM error as a **spatially autocorrelated**
  random field, not white noise; the model to synthesise realistic DEM error (`08`).

## Weathering, arid, periglacial & planetary

- **Heimsath, A.M., Dietrich, W.E., Nishiizumi, K. & Finkel, R.C. (1997).** *The soil production
  function and landscape equilibrium.* Nature 388(6640), 358–361. — Soil production declines
  exponentially with soil depth, from cosmogenic ¹⁰Be/²⁶Al. The regolith the erosion pipeline
  consumes (`11`).
- **USDA (2017).** *Soil Survey Manual* (Agriculture Handbook 18), Soil Science Division Staff. —
  The **soil texture triangle**: 12 classes from sand / silt / clay proportions (sand 2–0.05 mm, silt
  0.05–0.002 mm, clay <0.002 mm; triangle adopted 1951). The soil material palette (`18`).
- **Cooke, R.U., Warren, A. & Goudie, A.S. (1993).** *Desert Geomorphology.* UCL Press, London,
  526 pp. — The desert-landforms text (`16`).
- **Warren, J.K. (2016).** *Evaporites: A Geological Compendium* (2nd ed.). Springer, Cham, 1813 pp. —
  The evaporite reference: the concentration/precipitation sequence (carbonate → gypsum → halite →
  bittern) and sabkha/salina/playa settings (`16`).
- **Eugster, H.P. & Hardie, L.A. (1978).** *Saline lakes.* In A. Lerman (ed.), *Lakes: Chemistry,
  Geology, Physics*, ch. 8, pp. 237–293. Springer, New York. — Brine evolution and mineral zonation in
  closed-basin saline lakes (`16`).
- **Kinsman, D.J.J. (1969).** *Modes of formation, sedimentary associations, and diagnostic features
  of shallow-water and supratidal evaporites.* AAPG Bulletin 53(4), 830–840. — The **sabkha**: nodular
  evaporites growing displacively within supratidal sediment (`16`).
- **Lokier, S.W. (2012).** *Development and evolution of subaerial halite crust morphologies in a
  coastal sabkha setting.* Journal of Arid Environments 79, 32–47. — Halite-crust **tepee/thrust
  polygons** by desiccation, thermal cycling and crystallisation pressure (`16`).
- **Ward, A.W. & Greeley, R. (1984).** *Evolution of the yardangs at Rogers Lake, California.* GSA
  Bulletin 95(7), 829–837. — Yardang form (teardrop 1:4) and its wind-tunnel evolution (`16`).
- **Lancaster, N. & Tchakerian, V.P. (1996).** *Geomorphology and sediments of sand ramps in the
  Mojave Desert.* Geomorphology 17(1–3), 151–166. — **Sand ramps**: composite aeolian + colluvial +
  fluvial aprons banked against range fronts; their size and mixed provenance separate them from
  climbing/falling dunes, and they read as paleoclimate archives (`16`, `05`).
- **Blair, T.C. & McPherson, J.G. (1994).** *Alluvial fans and their natural distinction from rivers
  based on morphology, hydraulic processes, sedimentary processes, and facies assemblages.* Journal
  of Sedimentary Research A64(3), 450–489. — Fans as debris-flow / sheetflood landforms, distinct
  from rivers (`16`).
- **Bull, W.B. (1977).** *The alluvial-fan environment.* Progress in Physical Geography 1(2),
  222–270. — Fan processes and morphology (`16`).
- **Dohrenwend, J.C. (1994).** *Pediments in arid environments.* In A.D. Abrahams & A.J. Parsons (eds),
  *Geomorphology of Desert Environments*, pp. 321–353. Chapman & Hall, London. — The **pediment**: a
  bedrock erosion surface at the mountain front, distinct from the depositional fan (`16`).
- **McFadden, L.D., Wells, S.G. & Jercinovich, M.J. (1987).** *Influences of eolian and pedogenic
  processes on the origin and evolution of desert pavements.* Geology 15(6), 504–508. — Desert
  pavement is born at the surface over accreting dust, **not** a deflation lag (`16`).
- **Twidale, C.R. (1982).** *Granite Landforms.* Elsevier, Amsterdam. — Bornhardts and inselbergs by
  differential subsurface weathering and stripping of the regolith (`16`).
- **Linton, D.L. (1955).** *The problem of tors.* The Geographical Journal 121(4), 470–487. — **Tors**
  as a two-stage deep-weathering-then-stripping residual, controlled by joint spacing (`11`).
- **Palmer, J. & Neilson, R.A. (1962).** *The origin of granite tors on Dartmoor, Devonshire.*
  Proceedings of the Yorkshire Geological Society 33(3), 315–339. — The **periglacial** tor pathway:
  frost shattering + solifluction stripping, leaving a clitter/blockfield apron (`11`, `17`).
- **Mustoe, G.E. (1982).** *The origin of honeycomb weathering.* GSA Bulletin 93(2), 108–115. —
  **Tafoni/honeycomb** as salt-crystallisation granular disintegration behind a case-hardened rind (`11`).
- **Rodriguez-Navarro, C., Doehne, E. & Sebastian, E. (1999).** *Origins of honeycomb weathering: the
  role of salts and wind.* GSA Bulletin 111(8), 1250–1255. — Salt and wind as the honeycomb drivers (`11`).
- **Turkington, A.V. & Phillips, J.D. (2004).** *Cavernous weathering, dynamical instability and
  self-organization.* Earth Surface Processes and Landforms 29(6), 665–675. — Why cavities **self-deepen**:
  a case-hardened rind + depth-accelerating hollowing is a self-organising instability (`11`).
- **Gilbert, G.K. (1904).** *Domes and dome structure of the high Sierra.* GSA Bulletin 15(1), 29–36.
  — The classic description of **exfoliation/sheeting** domes (`11`).
- **Bradley, W.C. (1963).** *Large-scale exfoliation in massive sandstones of the Colorado Plateau.*
  GSA Bulletin 74(5), 519–528. — Sheeting as **unloading** parallel to the topographic surface (`11`).
- **Martel, S.J. (2006).** *Effect of topographic curvature on near-surface stresses and application to
  sheeting joints.* Geophysical Research Letters 33(1), L01308. — The mechanism: surface-parallel stress
  × curvature vs overburden opens sheeting under **convex** surfaces — an implementable equation (`11`).
- **Kessler, M.A. & Werner, B.T. (2003).** *Self-Organization of Sorted Patterned Ground.* Science
  299(5605), 380–383. — Stone circles / polygons / stripes from freeze–thaw feedbacks; slope selects
  the form. The **same Werner** as the dune model (`05`, `17`).
- **Matsuoka, N. (2001).** *Solifluction rates, processes and landforms: a global review.*
  Earth-Science Reviews 55(1–2), 107–134. — Solifluction as frost-gated slope diffusion (`17`).
- **Wahrhaftig, C. & Cox, A. (1959).** *Rock glaciers in the Alaska Range.* GSA Bulletin 70(4),
  383–436. — The founding rock-glacier study (`17`).
- **French, H.M. (2018).** *The Periglacial Environment* (4th ed.). Wiley, Chichester. — The
  periglacial text (`17`).
- **Washburn, A.L. (1979).** *Geocryology: A Survey of Periglacial Processes and Environments.*
  Edward Arnold, London. — The other periglacial reference (`17`).
- **Pike, R.J. & Clow, G.D. (1981).** *Revised classification of terrestrial volcanoes and catalog of
  topographic dimensions.* USGS Open-File Report 81-1038. — Edifice height / flank width / summit
  dimensions for 697 volcanoes (`11`).
- **Melosh, H.J. (1989).** *Impact Cratering: A Geologic Process.* Oxford Monographs on Geology and
  Geophysics 11, Oxford University Press. — The impact-cratering reference: crater mechanics, ejecta,
  and gravity scaling (`11`, `SKILL.md`).
- **Pike, R.J. (1977).** *Size-dependence in the shape of fresh impact craters on the Moon.* In Roddy,
  Pepin & Merrill (eds), *Impact and Explosion Cratering*, Pergamon, pp. 489–509. — Simple→complex
  transition; depth/diameter and rim-height ratios (`11`).
- **Kok, J.F., Parteli, E.J.R., Michaels, T.I. & Bou Karam, D. (2012).** *The physics of wind-blown
  sand and dust.* Reports on Progress in Physics 75(10), 106901. — Aeolian saltation and dunes on
  Earth, Mars, Venus, and Titan; the reference for wind-blown sand off-Earth (`16`, `SKILL.md`).
- **Goudie, A.S. (1973).** *Duricrusts in Tropical and Subtropical Landscapes.* Clarendon Press,
  Oxford, 174 pp. — The duricrust reference: calcrete, silcrete and ferricrete as resistant near-
  surface caps — a low-`K` horizon (`11`).
- **Nash, D.J. & McLaren, S.J. (eds) (2007).** *Geochemical Sediments and Landscapes.* Blackwell,
  Oxford (RGS-IBG Book Series). — Duricrusts and other surface cements as landscape components (`11`).
- **Pain, C.F. & Ollier, C.D. (1995).** *Inversion of relief — a component of landscape evolution.*
  Geomorphology 12(2), 151–165. — **Relief inversion**: a capped former valley becomes a ridge; the
  inverted-channel landform, an Earth and Mars analogue (`11`).

## Biogenic landforms

- **Clymo, R.S. (1984).** *The limits to peat bog growth.* Philosophical Transactions of the Royal
  Society B 303(1117), 605–654. — The acrotelm/catotelm peat-growth model; self-limiting height
  `M_max = p/α` — the raised bog's domed profile (`13`).
- **Grotzinger, J.P. & Knoll, A.H. (1999).** *Stromatolites in Precambrian carbonates.* Annual Review
  of Earth and Planetary Sciences 27, 313–358. — Microbial layered carbonate buildups (`13`).
- **Oren, A. & Rodríguez-Valera, F. (2001).** *The contribution of halophilic Bacteria to the red
  coloration of saltern crystallizer ponds.* FEMS Microbiology Ecology 36(2–3), 123–130. — Why a
  crystalliser pond is red: haloarchaeal bacterioruberin + *Dunaliella* β-carotene at NaCl saturation (`16`).
- **Oren, A. (2005).** *A hundred years of Dunaliella research: 1905–2005.* Saline Systems 1, art. 2. —
  *Dunaliella salina* accumulating >10% dry weight as β-carotene under salt-and-light stress (`16`).
- **Tengberg, A. & Chen, D. (1998).** *A comparative analysis of nebkhas in central Tunisia and
  northern Burkina Faso.* Geomorphology 22(2), 181–192. — Vegetation-anchored sand mounds (`13`, `16`).
- **Tarnita, C.E., Bonachela, J.A., Sheffer, E. et al. (2017).** *A theoretical foundation for
  multi-scale regular vegetation patterns.* Nature 541(7637), 398–401. — Regular termite-mound spacing
  from inter-colony competition; the mechanism, not a closed-form spacing law (`13`).
- **Darwin, C. (1881).** *The Formation of Vegetable Mould, through the Action of Worms.* John Murray,
  London. — The founding work on soil bioturbation / turnover (as a hillslope diffusivity) (`13`).

## Anthropogenic & engineered landforms

Humans are now the dominant geomorphic agent on Earth by volume; these ground the engineered surface
(`20`, Group K).

- **Hooke, R.LeB. (2000).** *On the history of humans as geomorphic agents.* Geology 28(9), 843–846.
  — The quantification that humans move more earth than rivers (`20`).
- **Haff, P.K. (2010).** *Hillslopes, rivers, plows, and trucks: mass transport on Earth's surface by
  natural and technological processes.* Earth Surface Processes and Landforms 35(10), 1157–1166. —
  Technology as a sediment-transport process alongside rivers and hillslopes (`20`).
- **Tarolli, P. & Sofia, G. (2016).** *Human topographic signatures and derived geomorphic processes
  across landscapes.* Geomorphology 255, 140–161. — Human topographic signatures in high-resolution
  DEMs; the umbrella review for anthropogeomorphology (`20`).
- **Goudie, A.S. (2013).** *The Human Impact on the Natural Environment: Past, Present, and Future*
  (7th ed.). Wiley-Blackwell. — The standard text; the anthropogeomorphology chapter (`20`).
- **Brune, G.M. (1953).** *Trap efficiency of reservoirs.* Transactions, AGU 34(3), 407–418. — The
  **trap-efficiency** curve keyed to capacity/inflow — how much sediment a reservoir retains (`20`, `12`).
- **Morris, G.L. & Fan, J. (1998).** *Reservoir Sedimentation Handbook.* McGraw-Hill, New York,
  805 pp. — The reference handbook for reservoir delta deposition and drawdown (`20`).
- **Kondolf, G.M. (1997).** *Hungry water: effects of dams and gravel mining on river channels.*
  Environmental Management 21(4), 533–551. — Sediment-starved incision and bed coarsening below a dam
  (`20`, `04`).
- **Ritter, A. (1892).** *Die Fortpflanzung der Wasserwellen.* Zeitschrift des Vereines Deutscher
  Ingenieure 36(33), 947–954. — The **dam-break** dry-bed shallow-water solution; wavefront speed
  `2√(g·h₀)` (`20`).
- **Palmer, M.A., Bernhardt, E.S., Schlesinger, W.H. et al. (2010).** *Mountaintop mining
  consequences.* Science 327(5962), 148–149. — Valley fills bury headwater streams; the spoil side of
  the mining mass budget (`20`).

## Reference implementations

Runnable, pytest-verified Python mirrors of the simulation pseudocode live in
`terrain-architect/reference-impl/` (numpy-only, each checked against its `09` oracle). They are
executable evidence, not an implied code licence; consume the neutral contracts in the references
unless the repository grants reuse permission. The mature libraries below are already distilled
in `22`; they are not required runtime dependencies. The shipped optional cross-validation tests
currently cover RichDEM and pysheds only.

- **Hobley, D.E.J., Adams, J.M., Nudurupati, S.S., Hutton, E.W.H., Gasparini, N.M.,
  Istanbulluoglu, E. & Tucker, G.E. (2017).** *Creative computing with Landlab: an open-source
  toolkit for building, coupling, and exploring two-dimensional numerical models of Earth-surface
  dynamics.* Earth Surface Dynamics 5, 21–46. — The CSDMS toolkit: stream power, flow routing,
  diffusion, priority-flood depression handling — all tested. **MIT**, pinned grounding in `22`.
- **fastscapelib / FastScape** — the maintained implementations of the O(N) stream-power solver of
  **Braun & Willett 2013** (above); `fastscape` is the xarray-based Python package.
  **GPL-3.0-only**, pinned grounding in `22`.
- **Barnes, R. (2016).** *RichDEM: Terrain Analysis Software.* github.com/r-barnes/richdem — the
  canonical priority-flood depression filling and flow accumulation (Barnes et al. 2014, above).
  **GPL-3.0-only**, pinned grounding in `22`.
- **Bartos, M. (2020).** *pysheds: simple and fast watershed delineation in Python.*
  DOI 10.5281/zenodo.3822494 — D8 flow direction, accumulation, catchment delineation.
  **GPL-3.0-only**, pinned grounding in `22`.

## Reading order

For maintainers extending the pre-grounding ledger, verify in this order:

1. **Braun & Willett 2013** — if the map is large. It is the highest-leverage paper here; the
   solver is three lines and it makes the difference between hours and seconds.
2. **Barnes et al. 2014** — because nothing downstream works without depression handling.
3. **Mei et al. 2007** — if the map is small-to-medium and you want water.
4. **Musgrave et al. 1989** — short, and it grounds thermal erosion.
5. **Bridson 2007** — two pages, and you'll need scatter eventually.

Everything else is reference-on-demand.
