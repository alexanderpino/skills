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
- **obrien1995** `P` — O'Brien, J.F. & Hodgins, J.K. (1995). *Dynamic Simulation of Splashing
  Fluids.* Proc. Computer Animation '95, 198–205. — The virtual-pipe height-field water model:
  a fluid surface as height columns coupled by pipes on the head difference. Not an erosion
  paper; the lineage runs O'Brien & Hodgins → Mei → Šťava.
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
  capacity and applying it per droplet.
- **lague_erosion** `F` — Lague, S. *Hydraulic Erosion.* github.com/SebLague/Hydraulic-Erosion —
  Not a paper. The droplet implementation most people have actually read; follows Beyer. Useful
  as a cross-check on brush weights and defaults, not as a source for the method.

## Thermal, mass wasting and aeolian

- **olsen2004** `F` — Olsen, J. (2004). *Realtime Procedural Terrain Generation.* Technical
  report, University of Southern Denmark. — A technical report, not peer review. Fast
  approximations for thermal/talus, including the sweep-based variant.
- **montgomery1994** `P` — Montgomery, D.R. & Dietrich, W.E. (1994). *A physically based model
  for the topographic control on shallow landsliding.* Water Resources Research 30(4),
  1153–1171. — The shallow-landslide susceptibility model behind SHALSTAB: wetness from drainage
  area coupled to infinite-slope stability. Failures concentrate in steep, convergent, wet
  hollows.
- **corominas1996** `P` — Corominas, J. (1996). *The angle of reach as a mobility index for
  small and large landslides.* Canadian Geotechnical Journal 33(2), 260–271. — The runout stop
  rule `L = H/tan(α)`, with the reach angle shrinking as volume grows, across 204 landslides.
- **bagnold1941** `F` — Bagnold, R.A. (1941). *The Physics of Blown Sand and Desert Dunes.*
  Methuen, London. — A **monograph, not a peer-reviewed paper**; `F` on the same rule as every
  other book here, and the demotion costs nothing because the physics is canonical either way.
  The origin of the threshold friction velocity and the `u*³` saltation law. Cite it for
  *why*, not *how*: the saltation-cloud physics is not a heightfield operation, but those two
  results are one expression each per cell.
- **sauermann2001** `P` — Sauermann, G., Kroy, K. & Herrmann, H.J. (2001). *A continuum
  saltation model for sand dunes.* Physical Review E 64, 031305. — The continuum branch: flux
  relaxes toward saturation over a saturation length, which sets the minimum dune size and
  shifts deposition downwind of the crest.
- **werner1995** `P` — Werner, B.T. (1995). *Eolian dunes: Computer simulations and attractor
  interpretation.* Geology 23(12), 1107–1110. — The implementable dune model. Slab CA with a
  shadow zone and differential deposition probability; produces barchan, transverse, linear and
  star dunes from wind regime alone. Under-cited relative to its usefulness.
- **momiji2000** `P` — Momiji, H., Carretero-González, R., Bishop, S.R. & Warren, A. (2000).
  *Simulation of the effect of wind speedup in the formation of transverse dune fields.* Earth
  Surface Processes and Landforms 25, 905–918. — Refines Werner with a **height-dependent
  saltation length**: wind speeds up over a dune's windward profile, so a slab launched from
  high on the dune is carried further than one launched from the flat. That is what bounds
  runaway growth in the slab model. It is **not** the source for shadow-zone non-erosion —
  that rule is Werner's own (slabs in shadow are not eroded and deposit with probability 1),
  and crediting it here sent the reader to the wrong paper.

## Landscape evolution

- **whipple1999** `P` — Whipple, K.X. & Tucker, G.E. (1999). *Dynamics of the stream-power river
  incision model: implications for height limits of mountain ranges, landscape response
  timescales, and research needs.* Journal of Geophysical Research 104(B8), 17661–17674. — The
  reference for stream-power incision dynamics, the roles of `m` and `n`, and knickpoint
  behaviour.
- **crosby2006** `P` — Crosby, B.T. & Whipple, K.X. (2006). *Knickpoint initiation and
  distribution within fluvial networks: 236 waterfalls in the Waipaoa River, North Island, New
  Zealand.* Geomorphology 82(1–2), 16–38. — Where waterfalls come from and how they propagate
  through a network; the empirical anchor for "a waterfall is a knickpoint".
- **culling1960** `P` — Culling, W.E.H. (1960). *Analytical Theory of Erosion.* Journal of
  Geology 68(3), 336–344. — Hillslope transport as diffusion, `D·∇²h`. The origin of the
  companion term in the stream-power equation.

## Analysis and filtering

- **horn1981** `P` — Horn, B.K.P. (1981). *Hill shading and the reflectance map.* Proceedings of
  the IEEE 69(1), 14–47. — The Sobel-weighted slope and aspect estimator GIS tools use.
- **zevenbergen1987** `P` — Zevenbergen, L.W. & Thorne, C.R. (1987). *Quantitative analysis of
  land surface topography.* Earth Surface Processes and Landforms 12(1), 47–56. — The 3×3
  partial-quartic fit; profile and plan curvature.
- **beven1979** `P` — Beven, K.J. & Kirkby, M.J. (1979). *A physically based, variable
  contributing area model of basin hydrology.* Hydrological Sciences Bulletin 24(1), 43–69. —
  TOPMODEL, and the topographic wetness index.
- **timonen2010** `P` — Timonen, V. & Westerholm, J. (2010). *Scalable Height Field
  Self-Shadowing.* Computer Graphics Forum 29(2) (Eurographics 2010), 723–731. — O(1)-per-cell
  horizon computation by sweep plus incremental convex hull. The one to use for large-radius
  terrain occlusion.
- **bavoil2008** `F` — Bavoil, L., Sainz, M. & Dimitrov, R. (2008). *Image-space horizon-based
  ambient occlusion.* SIGGRAPH '08 talks. — HBAO. A **talk, not a paper**, and graded like every
  other talk in this bibliography. Its `sin h − sin t` form is a screen-space weighting, not the
  cosine-weighted hemisphere integral a baked terrain map needs.
- **weiss2001** `F` — Weiss, A. (2001). *Topographic Position and Landforms Analysis.* Poster,
  ESRI User Conference, San Diego. — The topographic position index. Widely used, **not
  peer-reviewed**; an F-tier convenience, cited as such.
- **tomasi1998** `P` — Tomasi, C. & Manduchi, R. (1998). *Bilateral Filtering for Gray and Color
  Images.* ICCV '98, 839–846. — Edge-preserving smoothing by the product of a spatial and a
  range weight.
- **he2010** `P` — He, K., Sun, J. & Tang, X. (2010). *Guided Image Filtering.* ECCV 2010;
  extended in IEEE PAMI 35(6), 2013, 1397–1409. — O(1) per cell at any radius, no gradient
  reversal, and it accepts a separate guide image. Better than bilateral for terrain.
