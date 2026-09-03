---
type: Bibliography
title: Papers — generation
description: "Sources for the generation axis: noise, tectonics, erosion and terrain analysis, each graded by provenance tier."
tags: [bibliography, provenance, generation]
status: draft
generated: { by: process:claude-code, at: 2026-09-02T00:00:00Z }
---
# Papers — generation

The generation family of Gaia's bibliography. `papers-flow.md` carries the **provenance tier
table and the two rules that bind every entry here** — never upgrade a tier to satisfy a
question, and a constant reconstructed from memory is a `?` wearing a P's confidence. Read them
there; they are not repeated.

Entry format, as in the flow family:

```
- **id** `T` — Author (Year). *Title.* Venue. — note
```

## Attribution corrections that bind this family

The general table is in `papers-flow.md`. These four decide where an implementer of the erosion
axis is sent, so they are restated:

| Common claim | Reality |
|---|---|
| "Hydraulic (particle) — Mei et al. 2007" | **Mei et al. 2007 is a grid/pipe model.** The pipe abstraction itself is O'Brien & Hodgins 1995; Mei is where it becomes erosion. |
| "Hydraulic (grid/pipe) — Šťava et al. 2008" | **Šťava is also a pipe model**, extending Mei. One family, not two. |
| "Droplet erosion has a canonical paper" | It does not. Musgrave et al. 1989 → Beyer's 2015 TU München thesis. Tier `F`, not `P`. |
| "Tectonic plates — Cordonnier 2015" | The paper is **Cordonnier et al. 2016**, and it is the same paper as the stream-power citation. The O(N) solver under it is **Braun & Willett 2013**, listed in `papers-flow.md`. |

## Noise

- **perlin1985** `P` — Perlin, K. (1985). *An Image Synthesizer.* SIGGRAPH '85, 287–296. —
  The original gradient noise: a hashed gradient and value per lattice point, interpolated.
  It does **not** contain `3t² − 2t³`. The Noise() section (p. 289) says only "a smooth (eg.
  cubic polynomial) interpolation", and no polynomial appears anywhere in the paper. The
  cubic, and the `6 − 12t` second derivative the continuity argument turns on, are written
  down in **perlin2002 §2**, which attributes the description to Ebert et al. 1998. Cite 1985
  for the construction, 2002 for either fade.
- **perlin2002** `P` — Perlin, K. (2002). *Improving Noise.* ACM TOG 21(3), SIGGRAPH '02,
  681–682. — The quintic fade `6t⁵ − 15t⁴ + 10t³` and the 12 cube-edge gradients (padded to 16
  so the index is a mask, not a modulo), §3 Modifications, p. 682. It also carries the cubic
  `3t² − 2t³` it replaces, in §2 — the 1985 paper does not. Use this, not the 1985 version.
- **opensimplex2** `F` — KdotJPG. *OpenSimplex2.* github.com/KdotJPG/OpenSimplex2 (public
  domain). — No canonical paper; standard practice is to take this reference implementation
  whole, including the lattice-rotated `noise3_ImproveXY` variants. Do not reconstruct its
  constants from memory.
- **gustavson2005** `F` — Gustavson, S. (2005). *Simplex noise demystified.* Linköping
  University technical note. — Not peer-reviewed; the readable derivation of the skew/unskew
  constants and the reference 2D/3D/4D code.
- **worley1996** `P` — Worley, S. (1996). *A Cellular Texture Basis Function.* SIGGRAPH '96,
  291–294. — F1/F2 cellular noise. The paper specifies a Poisson-distributed feature-point count
  per cell; the one-point-per-cell simplification everyone ships is a deviation.
- **musgrave_tm** `F` — Musgrave, F.K. Chapters in Ebert, Musgrave, Peachey, Perlin & Worley,
  *Texturing and Modeling: A Procedural Approach* (3rd ed., 2002); also Musgrave, F.K. (1993),
  *Methods for Realistic Landscape Imaging*, PhD thesis, Yale. — No peer-reviewed paper for
  ridged and hybrid multifractal; these are the authoritative formulations, including the
  weight-feedback terms most online versions omit.
- **quilez_warp** `F` — Quilez, I. *Domain warping.* iquilezles.org/articles/warp — An article,
  not a paper. The `fbm(p + fbm(p + fbm(p)))` construction, and the source everyone's warp node
  descends from.
- **fournier1982** `P` — Fournier, A., Fussell, D. & Carpenter, L. (1982). *Computer Rendering
  of Stochastic Models.* CACM 25(6), 371–384. — Midpoint displacement / diamond-square.
  Historically important, obsolete in practice.
- **lagae2009** `P` — Lagae, A., Lefebvre, S., Drettakis, G. & Dutré, P. (2009). *Procedural
  Noise using Sparse Gabor Convolution.* ACM TOG 28(3), SIGGRAPH '09. — Gabor noise: spatially
  varying spectrum and orientation, the only common noise with honest anisotropy.
- **cook2005** `P` — Cook, R.L. & DeRose, T. (2005). *Wavelet Noise.* ACM TOG 24(3), SIGGRAPH
  '05, 803–811. — Genuinely band-limited noise, and the anti-aliasing argument for it.
- **bridson2007** `P` — Bridson, R., Hourihan, J. & Nordenstam, M. (2007). *Curl-Noise for
  Procedural Fluid Flow.* ACM TOG 26(3), SIGGRAPH '07. — Divergence-free noise from the curl of
  a potential; for terrain, a warp field rather than a height source.

## Tectonics, uplift and isostasy

- **cordonnier2016** `P` — Cordonnier, G., Braun, J., Cani, M.-P., Benes, B., Galin, E.,
  Peytavie, A. & Guérin, E. (2016). *Large Scale Terrain Generation from Tectonic Uplift and
  Fluvial Erosion.* Computer Graphics Forum 35(2), 165–175 (Eurographics 2016). — Tectonic
  uplift coupled to stream power, with lake-graph handling of local minima inside the loop.
  This is both the "2015 tectonics" paper and the "2016 stream power" paper; they are one.
- **cortial2019** `P` — Cortial, Y., Peytavie, A., Galin, E. & Guérin, E. (2019). *Procedural
  Tectonic Planets.* Computer Graphics Forum 38(2) (Eurographics 2019). — Whole-planet terrain
  from approximated plate subduction and collision under user-controlled plate motion. The
  graphics anchor for spherical tectonics.
- **turcotte2014** `F` — Turcotte, D.L. & Schubert, G. (2014). *Geodynamics* (3rd ed.).
  Cambridge University Press. — A **textbook, not peer review**, and graded on the same rule
  that makes every book in this bibliography `F`. It is nonetheless the standard reference for
  Airy isostasy and thin-elastic-plate flexure, including flexural rigidity and the flexural
  parameter; there is no canonical paper for either, and standard practice is to take the
  textbook derivation whole.
- **molnar1990** `P` — Molnar, P. & England, P. (1990). *Late Cenozoic uplift of mountain ranges
  and global climate change: chicken or egg?* Nature 346(6279), 29–34. — Erosional isostasy:
  incision unloads a range and the summits rebound, so peak uplift is not by itself proof of
  tectonic uplift.

## Hydraulic erosion

- **musgrave1989** `P` — Musgrave, F.K., Kolb, C.E. & Mace, R.S. (1989). *The Synthesis and
  Rendering of Eroded Fractal Terrains.* SIGGRAPH '89, 41–50. — The origin of both thermal
  erosion and grid-based hydraulic erosion in graphics. Everything downstream traces here.
  ⚠️ **Not obtained.** The ACM Digital Library refused the download and no open copy was
  reachable, so no locator into this paper is verified anywhere in this repository. What the
  documents attribute to it was read second-hand in `olsen2004` p. 5, which restates the
  thermal pass and credits Musgrave et al. 1989 for both erosion types.
- **obrien1995** `P` — O'Brien, J.F. & Hodgins, J.K. (1995). *Dynamic Simulation of Splashing
  Fluids.* Proc. Computer Animation '95, 198–205. — The virtual-pipe height-field water model:
  a fluid surface as height columns coupled by pipes on the head difference. Not an erosion
  paper; the lineage runs O'Brien & Hodgins → Mei → Šťava. ⚠️ **Not obtained** — the proceedings
  are not online free and the Berkeley author copy was unreachable, so no locator into it is
  verified here.
- **mei2007** `P` — Mei, X., Decaudin, P. & Hu, B.-G. (2007). *Fast Hydraulic Erosion
  Simulation and Visualization on GPU.* Pacific Graphics 2007, 47–56. — The virtual pipe model
  applied to erosion. Grid-based, **not** particle-based. §3 enumerates **five** stages — water
  increment, flow, erosion–deposition, sediment transport, evaporation — including the outflow
  scaling factor in the flow stage. The "eight-step" enumeration that circulates is a community
  re-split of the flow stage and is not a locator anyone can follow into the paper.
- **stava2008** `P` — Šťava, O., Beneš, B., Brisbin, M. & Křivánek, J. (2008). *Interactive
  Terrain Modeling Using Hydraulic Erosion.* SCA 2008, 201–210. — Extends Mei with sediment
  slippage, material layers and ghost-cell boundaries. Also a pipe model. §4 fixes the pipe
  cross-section at `C = l²`, **constant**, and writes the outflow scale-down as a guarded
  branch rather than Mei's `min`. It does **not** contain the `lmax` depth ramp often
  attributed to it — that is `jako2011`; its capacity (eq. 2) is `|v|·C_k·sin α`, unramped.
- **jako2011** `P` — Jákó, B. & Tóth, B. (2011). *Fast Hydraulic and Thermal Erosion on the
  GPU.* Eurographics 2011 Short Papers. — Adds the `lmax(d)` depth ramp on transport capacity
  to the Mei pipe model, plus a thermal pass. Eq. (10) and the ramp definition were read in
  Jákó's CESCG 2011 copy of the same work (old.cescg.org), not in the Eurographics printing.
- **beyer2015** `F` — Beyer, H.T. (2015). *Implementation of a Method for Hydraulic Erosion.*
  Bachelor thesis, Technische Universität München. — A thesis, not peer review. There is no
  canonical droplet-erosion paper; this is the modern formulation, borrowing Mei's transport
  capacity and applying it per droplet. ⚠️ **Not obtained** — the TUM mediatum copy did not serve
  the PDF, so no locator into the thesis is verified here; what has been read is the
  implementation that follows it, `lague_erosion`.
- **lague_erosion** `F` — Lague, S. *Hydraulic Erosion.* github.com/SebLague/Hydraulic-Erosion —
  Not a paper. The droplet implementation most people have actually read; follows Beyer. **Read
  in full** — `Assets/Scripts/Erosion.cs`, 207 lines. Useful as a cross-check on brush weights
  (`1 − sqrt(d²)/radius`, normalised, lines 155–200) and on the defaults (lines 6–22), not as a
  source for the method. ⚠️ **Line 124 is wrong and is widely copied**:
  `speed = sqrt(speed*speed + deltaHeight*gravity)` with `deltaHeight = newHeight − oldHeight`
  accelerates droplets *uphill* and can take the square root of a negative number. Cite this file
  for what it is — the code people read — and flag that line wherever it is recommended.

## Thermal, mass wasting and aeolian

- **olsen2004** `F` — Olsen, J. (2004). *Realtime Procedural Terrain Generation.* Technical
  report, University of Southern Denmark. — A technical report, not peer review. **Read in
  full.** Section *Thermal erosion*: the reference implementation on p. 5 is
  `h_i += c·(d_max − T)·d_i/d_total` with "A reasonable value for c is 0.5", credited to
  Musgrave et al. 1989; the *Optimizations* sub-head on pp. 6–7 is the fast variant, and it is
  four specific changes — Von Neumann rather than Moore, material to the **lowest neighbour
  only**, `Δh = d_max/2`, and **in-place height-map writes instead of a difference map**.
  ⚠️ **This entry used to say "including the sweep-based variant". There is no sweep in Olsen.**
  The correction matters because the fourth change is the deliberate removal of the double
  buffering that `thermal-and-aeolian-erosion.md` requires, so the variant cannot be reached for
  casually. Measured there: 500 iterations in 10 s against 60 s, stabilising sooner but scoring
  5% worse at 500 iterations (p. 7, *Analysis*).
- **montgomery1994** `P` — Montgomery, D.R. & Dietrich, W.E. (1994). *A physically based model
  for the topographic control on shallow landsliding.* Water Resources Research 30(4),
  1153–1171. — The shallow-landslide susceptibility model behind SHALSTAB: wetness from drainage
  area coupled to infinite-slope stability. Failures concentrate in steep, convergent, wet
  hollows. ⚠️ **Not obtained** — paywalled at AGU, no open copy reachable; nothing inside it is
  cited by section or equation anywhere here, and the summary above is repeated from secondary
  descriptions.
- **corominas1996** `P` — Corominas, J. (1996). *The angle of reach as a mobility index for
  small and large landslides.* Canadian Geotechnical Journal 33(2), 260–271. — The runout stop
  rule `L = H/tan(α)`, with the reach angle shrinking as volume grows, across 204 landslides.
  ⚠️ **Not obtained** — paywalled at Canadian Science Publishing, no open copy reachable. The
  204-landslide sample and the reach-angle bands (rockfalls ~30–45°, small slides 20–30°, large
  rock avalanches under 10°) that `thermal-and-aeolian-erosion.md` quotes are repeated from
  secondary descriptions and are **unverified against the paper**.
- **bagnold1941** `F` — Bagnold, R.A. (1941). *The Physics of Blown Sand and Desert Dunes.*
  Methuen, London. — A **monograph, not a peer-reviewed paper**; `F` on the same rule as every
  other book here, and the demotion costs nothing because the physics is canonical either way.
  The origin of the threshold friction velocity and the `u*³` saltation law. Cite it for
  *why*, not *how*: the saltation-cloud physics is not a heightfield operation, but those two
  results are one expression each per cell. ⚠️ **Not obtained** — the 1941 monograph was not
  reachable here, so no chapter is cited and the numeric constants attributed to it in
  `thermal-and-aeolian-erosion.md` (`A ≈ 0.1`, the 0.25 mm reference grain) are conventional
  working values, not read out of Bagnold.
- **sauermann2001** `P` — Sauermann, G., Kroy, K. & Herrmann, H.J. (2001). *A continuum
  saltation model for sand dunes.* Physical Review E 64, 031305. — **Read in full** (arXiv
  cond-mat/0101377v2). The continuum branch: flux relaxes toward saturation over a saturation
  length. Section VI *A Minimal Model for the Sand Flux* carries the two load-bearing
  expressions — eq. 46, `∂q/∂x = (q/l_s)(1 − q/q_s)`, which is **logistic and not the linear
  `dq/ds = (q_sat − q)/L_sat` that circulates**, and eq. 47 for `l_s`, plotted in Figure 5 as
  0.4–0.8 m asymptotically and diverging as `u*` nears the threshold. The linear form is its
  linearisation about saturation and carries the same `l_s`.
  ⚠️ **This entry used to credit it with setting the minimum dune size. It does not.** Section
  VIII explicitly defers "the question of shape differences between small and large dunes or the
  minimum size for slip-face formation" to the companion paper (Kroy, Sauermann & Herrmann,
  *Minimal Model for Sand Dunes*, PRL 88, 054301), which adds the turbulent wind field this one
  does not carry. Cite Sauermann for the saturation length; cite Kroy et al. for the minimum size.
- **werner1995** `P` — Werner, B.T. (1995). *Eolian dunes: Computer simulations and attractor
  interpretation.* Geology 23(12), 1107–1110. — The implementable dune model. Slab CA with a
  shadow zone and differential deposition probability; produces barchan, transverse, linear and
  star dunes from wind regime alone. Under-cited relative to its usefulness.
  ⚠️ **Not obtained** — paywalled at GeoScienceWorld, no open copy reachable. The shadow-zone
  rule, the `p_sand > p_bare` values and the saltation length that
  `thermal-and-aeolian-erosion.md` attributes to it are **unverified against the paper**.
- **momiji2000** `P` — Momiji, H., Carretero-González, R., Bishop, S.R. & Warren, A. (2000).
  *Simulation of the effect of wind speedup in the formation of transverse dune fields.* Earth
  Surface Processes and Landforms 25, 905–918. — Refines Werner with a **height-dependent
  saltation length**: wind speeds up over a dune's windward profile, so a slab launched from
  high on the dune is carried further than one launched from the flat. That is what bounds
  runaway growth in the slab model. It is **not** the source for shadow-zone non-erosion —
  that rule is Werner's own (slabs in shadow are not eroded and deposit with probability 1),
  and crediting it here sent the reader to the wrong paper.
  ⚠️ **Not obtained** — paywalled at Wiley, no open copy reachable; the correction above rests on
  secondary descriptions of both papers, not on either full text.

## Landscape evolution

- **whipple1999** `P` — Whipple, K.X. & Tucker, G.E. (1999). *Dynamics of the stream-power river
  incision model: implications for height limits of mountain ranges, landscape response
  timescales, and research needs.* Journal of Geophysical Research 104(B8), 17661–17674. — The
  reference for stream-power incision dynamics, the roles of `m` and `n`, and knickpoint
  behaviour. ⚠️ **Not obtained** — paywalled at AGU, no open copy reachable. Only the concavity
  claim has been checked, and second-hand: `cordonnier2016` §3.1 states `m/n ≈ 0.5` as constrained
  by stream-profile shape and cites Whipple & Tucker for it. The knickpoint-celerity claim
  `stream-power.md` hangs on this entry is **unverified**.
- **crosby2006** `P` — Crosby, B.T. & Whipple, K.X. (2006). *Knickpoint initiation and
  distribution within fluvial networks: 236 waterfalls in the Waipaoa River, North Island, New
  Zealand.* Geomorphology 82(1–2), 16–38. — Where waterfalls come from and how they propagate
  through a network; the empirical anchor for "a waterfall is a knickpoint". ⚠️ **Not obtained** —
  paywalled at Elsevier, no open copy reachable. Note that "236 waterfalls in the Waipaoa" is the
  paper's title, so quoting it is a citation and not a locator.
- **culling1960** `P` — Culling, W.E.H. (1960). *Analytical Theory of Erosion.* Journal of
  Geology 68(3), 336–344. — Hillslope transport as diffusion, `D·∇²h`. The origin of the
  companion term in the stream-power equation. ⚠️ **Not obtained** — behind JSTOR, no open copy
  reachable, so no section or equation inside it is cited anywhere here.

## Analysis and filtering

- **horn1981** `P` — Horn, B.K.P. (1981). *Hill shading and the reflectance map.* Proceedings of
  the IEEE 69(1), 14–47. — The Sobel-weighted slope and aspect estimator GIS tools use.
  ⚠️ **Not obtained** — paywalled at IEEE and the MIT author copies now 404, so no locator into it
  is verified here.
- **zevenbergen1987** `P` — Zevenbergen, L.W. & Thorne, C.R. (1987). *Quantitative analysis of
  land surface topography.* Earth Surface Processes and Landforms 12(1), 47–56. — The 3×3
  partial-quartic fit; profile and plan curvature. ⚠️ **Not obtained** — paywalled at Wiley, no
  open copy reachable, so the coefficient and curvature expressions `terrain-analysis-masks.md`
  writes out are the standard published form and have **not** been checked against Zevenbergen &
  Thorne's own numbering.
- **beven1979** `P` — Beven, K.J. & Kirkby, M.J. (1979). *A physically based, variable
  contributing area model of basin hydrology.* Hydrological Sciences Bulletin 24(1), 43–69. —
  TOPMODEL, and the topographic wetness index. ⚠️ **Not obtained** — paywalled at Taylor &
  Francis, and the White Rose repository record for it states that no full text is held there, so
  no locator into it is verified here.
- **timonen2010** `P` — Timonen, V. & Westerholm, J. (2010). *Scalable Height Field
  Self-Shadowing.* Computer Graphics Forum 29(2) (Eurographics 2010), 723–731. — O(1)-per-cell
  horizon computation by sweep plus incremental convex hull. **Read in full** (author copy at
  wili.cc). §4 states the O(n)-per-line complexity and the absence of approximation; §5 and
  Algorithm 1 are the convex-hull stack. ⚠️ §4 also claims the authors are "not aware of this
  method having been introduced in a field outside computer graphics before" — which `dozier2022`
  §I contradicts, attributing the order-N sweep to Dozier, Bruno & Downey (1981). Cite Timonen for
  the GPU formulation, not for the idea.
- **bavoil2008** `F` — Bavoil, L., Sainz, M. & Dimitrov, R. (2008). *Image-space horizon-based
  ambient occlusion.* SIGGRAPH '08 talks. — HBAO. A **talk, not a paper**, and graded like every
  other talk in this bibliography. Its `sin h − sin t` form is a screen-space weighting, not the
  cosine-weighted hemisphere integral a baked terrain map needs. **Read in full**: slide 12
  defines `h` and `t` as `atan(z/||xy||)` of the horizon and tangent vectors and gives
  `AO = sin h − sin t`; slide 16 averages `AO(θ)` over 2D directions.
- **weiss2001** `F` — Weiss, A. (2001). *Topographic Position and Landforms Analysis.* Poster,
  ESRI User Conference, San Diego. — The topographic position index. Widely used, **not
  peer-reviewed**; an F-tier convenience, cited as such. **Read in full**: Fig. 2a is the
  definition, Figs. 2b–2c the two worked annulus scales on a 30 m DEM (`tpi300` at radii 5/10
  cells, `tpi2000` at 62/67), Figs. 3b–3c the standard-deviation thresholding, and Fig. 4a–4b the
  two-scale combination into ten landform classes.
- **tomasi1998** `P` — Tomasi, C. & Manduchi, R. (1998). *Bilateral Filtering for Gray and Color
  Images.* ICCV '98, 839–846. — Edge-preserving smoothing by the product of a spatial and a
  range weight.
- **he2010** `P` — He, K., Sun, J. & Tang, X. (2010). *Guided Image Filtering.* ECCV 2010;
  extended in IEEE PAMI 35(6), 2013, 1397–1409. — O(1) per cell at any radius, no gradient
  reversal, and it accepts a separate guide image. Better than bilateral for terrain.
  ⚠️ **Not obtained** — the SpringerLink chapter PDF served an HTML shell and both author copies
  404, so no locator into it is verified here.
