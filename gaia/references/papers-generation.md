---
type: Bibliography
title: Papers — generation
description: "Sources for the generation axis: noise and fractal composition, tectonics and isostasy, hydraulic, thermal and aeolian erosion, landscape evolution, layered rock and grain classes, impact cratering, constraint-based authoring, and periodic construction. Terrain analysis and edge-aware filtering moved to papers-masks-and-filtering.md."
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

## What was read, and what was not

Three families were added to this file from documents written separately, and each carries its own
read log. Older sections of this bibliography predate the practice; where a source was never
obtained, its entry carries `[not-opened]`.

### Impact cratering

**`pike1977`** — the ADS scanned page images of the Pergamon volume were read directly. Table 1
(p. 491) and equations (1)–(4) (p. 492) are transcribed from that scan, digit for digit, and the
two stated intersection diameters were then reproduced numerically from the transcribed
coefficients as a check on the transcription.
**`austin2024`** — open access at the publisher; §6.2 and equation (1) read there.
**`minton2019`** — the accepted-manuscript PDF; §1.1 and Figure 1 read there.
**`silber2017`** — the accepted-manuscript PDF of the JGR-Planets paper; §1 and §5 read there.

⚠️ **One source is deliberately absent.** McGetchin, Settle & Head (1973), *Radial thickness
variation in impact crater ejecta*, EPSL 20, 226–236, is the origin of the ejecta falloff
exponent every later paper quotes, and **it could not be obtained** — the publisher's copy is
paywalled and the ADS scan is not retrievable. It is therefore not an entry here, and
`impact-craters.md` cites austin2024 for the exponent instead, which reports both McGetchin's
value and its own measurement. Naming McGetchin in prose, with the paper that reports it as the
citation, is the honest form; adding a bibliography entry for a paper nobody here opened would
not be.

### Constraint and sketch-based authoring

**`hnaidi2010`** — the authors' copy on Éric Galin's LIRIS page. Sections 3 through 6, both
tables and the figure captions read there. Every equation quoted in `sketch-based-authoring.md`
is transcribed from that PDF.
**`orzan2008`** — `diffusion_curves.pdf` from the INRIA Maverick project page for the paper.
Sections 3.2.1, 3.2.2 and 3.2.4 read there.
**`gain2009`** — the author's copy in the University of Cape Town publications archive
(`pubs.cs.uct.ac.za`, `terrsketch.pdf`). Section 4 and section 5 read there; equations (1)–(3)
and the calibration numbers are transcribed from it.

⚠️ **One source is deliberately absent.** Zhou, H., Sun, J., Turk, G. & Rehg, J.M. (2007),
*Terrain synthesis from digital elevation models*, IEEE TVCG 13(4), 834–848, is the
example-based branch that both `hnaidi2010` §2 and `gain2009` §2 position against, and **no
openable copy was reached** — the publisher's copy is paywalled and the two author-side links
found returned HTML, not a PDF. It is therefore not an entry here.
`sketch-based-authoring.md` names it in prose, says it was not reached, and claims nothing about
its contents beyond the one-line characterisation the two papers that *were* opened give it. It
also falls inside this skill's learned-and-example-based exclusion, so nothing rests on it.

### Periodicity and boundaries

**`lagae2010`** — the authors' preprint PDF of the Computer Graphics Forum survey. §2.3, §3.1.1,
§7 and Table 1 with its four footnotes were read there. ⚠️ **That artefact paginates 1–20**, with
the header reading "Volume 0 (1981), Number 0", so it does not carry the CGF 29(8) page numbers;
the locator therefore cites sections and a table, never a page. The published pagination is
2579–2600 and is asserted here only as catalogue metadata, not as a locator.

**`hobley2017`** — the Copernicus open-access PDF of the Earth Surface Dynamics paper. §3.1.4 and
Tables 4a/4b were read there, at the paper's own page numbers 30–31.

**`perlin2002`** — the 2-page SIGGRAPH sketch, read at the author's own copy. ⚠️ **This artefact
carries no appendix listing.** The reference implementation's 8-bit index mask — the line that
actually fixes classic Perlin noise's period at 256 — is *not* in it, so it is not attributed to
this paper anywhere. What the sketch does carry, and what is cited, is the shape of the lookup in
§2 and the statement in §5 that the permutation table is the only remaining random component.

**`mei2007`** — the authors' HAL deposit `inria-00402079`. §3.2.2 and §4 read there.

**`barnes2014`** (defined in `papers-flow.md`) — the arXiv/accepted PDF already in the corpus, re-opened for this document. §1,
§3.1 and §3.3 read there.

⚠️ **One source is named in prose and deliberately absent.** Lagae & Dutré, *Long-period hash
functions for procedural texturing* — the reference `lagae2010` §7 gives for improving a lattice
noise's period — **was not obtained**. `seamless-and-periodic.md` therefore attributes the
period-versus-storage relationship to the survey that reports it, and grades the modular-indexing
construction it recommends as `F`, rather than borrowing authority from a paper nobody here read.
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

- **musgrave1989** `P` [not-opened] — Musgrave, F.K., Kolb, C.E. & Mace, R.S. (1989). *The Synthesis and
  Rendering of Eroded Fractal Terrains.* SIGGRAPH '89, 41–50. — The origin of both thermal
  erosion and grid-based hydraulic erosion in graphics. Everything downstream traces here.
  ⚠️ **Not obtained.** The ACM Digital Library refused the download and no open copy was
  reachable, so no locator into this paper is verified anywhere in this repository. What the
  documents attribute to it was read second-hand in `olsen2004` p. 6, which restates the
  thermal pass and credits Musgrave et al. 1989 for both erosion types.
- **obrien1995** `P` [not-opened] — O'Brien, J.F. & Hodgins, J.K. (1995). *Dynamic Simulation of Splashing
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
- **beyer2015** `F` [not-opened] — Beyer, H.T. (2015). *Implementation of a Method for Hydraulic Erosion.*
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
  full.** Section *Thermal erosion*: the reference implementation on **p. 6** is
  `h_i += c·(d_max − T)·d_i/d_total` with "A reasonable value for c is 0.5", credited to
  Musgrave et al. 1989; the *Optimizations* sub-head on pp. 6–7 is the fast variant, and it is
  four specific changes — Von Neumann rather than Moore, material to the **lowest neighbour
  only**, `Δh = d_max/2`, and **in-place height-map writes instead of a difference map**.
  ⚠️ **This entry used to say "including the sweep-based variant". There is no sweep in Olsen.**
  The correction matters because the fourth change is the deliberate removal of the double
  buffering that `thermal-and-aeolian-erosion.md` requires, so the variant cannot be reached for
  casually. Measured there: 500 iterations in 10 s against 60 s, stabilising sooner but scoring
  5% worse at 500 iterations (p. 7, *Analysis*).
- **montgomery1994** `P` [not-opened] — Montgomery, D.R. & Dietrich, W.E. (1994). *A physically based model
  for the topographic control on shallow landsliding.* Water Resources Research 30(4),
  1153–1171. — The shallow-landslide susceptibility model behind SHALSTAB: wetness from drainage
  area coupled to infinite-slope stability. Failures concentrate in steep, convergent, wet
  hollows. ⚠️ **Not obtained** — paywalled at AGU, no open copy reachable; nothing inside it is
  cited by section or equation anywhere here, and the summary above is repeated from secondary
  descriptions.
- **corominas1996** `P` [not-opened] — Corominas, J. (1996). *The angle of reach as a mobility index for
  small and large landslides.* Canadian Geotechnical Journal 33(2), 260–271. — The runout stop
  rule `L = H/tan(α)`, with the reach angle shrinking as volume grows, across 204 landslides.
  ⚠️ **Not obtained** — paywalled at Canadian Science Publishing, no open copy reachable. The
  204-landslide sample and the reach-angle bands (rockfalls ~30–45°, small slides 20–30°, large
  rock avalanches under 10°) that `thermal-and-aeolian-erosion.md` quotes are repeated from
  secondary descriptions and are **unverified against the paper**.
- **bagnold1941** `F` [not-opened] — Bagnold, R.A. (1941). *The Physics of Blown Sand and Desert Dunes.*
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
  length. Section VI — its actual heading is *A Minimal Model for Geomorphological Applications*,
  not "for the Sand Flux", which both ends of this citation had invented — carries the two
  load-bearing expressions: eq. 46, `∂q/∂x = (q/l_s)(1 − q/q_s)`, which is **logistic and not the
  linear `dq/ds = (q_sat − q)/L_sat` that circulates**, and eq. 47 for `l_s`.
  ⚠️ **The saturation length is about 0.09 m, not 0.4–0.8 m.** This entry read the divergent part
  of Figure 5 and called it the asymptote — the caption says the opposite, that `l_s` "is
  asymptotically constant for high shear velocities, but diverges for shear velocities near the
  threshold". Recomputed from the paper's own eq. 47 with its own fitted constants (α = 0.35,
  γ = 0.2, `z1` = 0.005 m, `zm` = 0.04 m, `u*t` = 0.28 m/s, `d` = 250 µm, `Cd` = 3): the asymptote
  is **0.087 m**, the curve is 0.122 m at `u*/u*t` = 8, and 0.4–0.8 m occurs only over
  `u*/u*t` ≈ 1.7–2.3, inside the near-threshold divergence. Five to nine times too large, on the
  length a reader is told to size grid cells against. The linear form is its
  linearisation about saturation and carries the same `l_s`.
  ⚠️ **This entry used to credit it with setting the minimum dune size. It does not.** Section
  VIII explicitly defers "the question of shape differences between small and large dunes or the
  minimum size for slip-face formation" to the companion paper (Kroy, Sauermann & Herrmann,
  *Minimal Model for Sand Dunes*, PRL 88, 054301), which adds the turbulent wind field this one
  does not carry. Cite Sauermann for the saturation length; cite Kroy et al. for the minimum size.
- **werner1995** `P` [not-opened] — Werner, B.T. (1995). *Eolian dunes: Computer simulations and attractor
  interpretation.* Geology 23(12), 1107–1110. — The implementable dune model. Slab CA with a
  shadow zone and differential deposition probability; produces barchan, transverse, linear and
  star dunes from wind regime alone. Under-cited relative to its usefulness.
  ⚠️ **Not obtained** — paywalled at GeoScienceWorld, no open copy reachable. The shadow-zone
  rule, the `p_sand > p_bare` values and the saltation length that
  `thermal-and-aeolian-erosion.md` attributes to it are **unverified against the paper**.
- **momiji2000** `P` [not-opened] — Momiji, H., Carretero-González, R., Bishop, S.R. & Warren, A. (2000).
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

- **whipple1999** `P` [not-opened] — Whipple, K.X. & Tucker, G.E. (1999). *Dynamics of the stream-power river
  incision model: implications for height limits of mountain ranges, landscape response
  timescales, and research needs.* Journal of Geophysical Research 104(B8), 17661–17674. — The
  reference for stream-power incision dynamics, the roles of `m` and `n`, and knickpoint
  behaviour. ⚠️ **Not obtained** — paywalled at AGU, no open copy reachable. Only the concavity
  claim has been checked, and second-hand: `cordonnier2016` §3.1 states `m/n ≈ 0.5` as constrained
  by stream-profile shape and cites Whipple & Tucker for it. The knickpoint-celerity claim
  `stream-power.md` hangs on this entry is **unverified**.
- **crosby2006** `P` [not-opened] — Crosby, B.T. & Whipple, K.X. (2006). *Knickpoint initiation and
  distribution within fluvial networks: 236 waterfalls in the Waipaoa River, North Island, New
  Zealand.* Geomorphology 82(1–2), 16–38. — Where waterfalls come from and how they propagate
  through a network; the empirical anchor for "a waterfall is a knickpoint". ⚠️ **Not obtained** —
  paywalled at Elsevier, no open copy reachable. Note that "236 waterfalls in the Waipaoa" is the
  paper's title, so quoting it is a citation and not a locator.
- **culling1960** `P` [not-opened] — Culling, W.E.H. (1960). *Analytical Theory of Erosion.* Journal of
  Geology 68(3), 336–344. — Hillslope transport as diffusion, `D·∇²h`. The origin of the
  companion term in the stream-power equation. ⚠️ **Not obtained** — behind JSTOR, no open copy
  reachable, so no section or equation inside it is cited anywhere here.

## Layered rock and stratigraphy


- **benes2001** `P` — Beneš, B. & Forsbach, R. (2001). *Layered Data Representation for Visual Simulation of Terrain Erosion.* Proceedings of the 17th Spring Conference on Computer Graphics (SCCG 2001), 80–86. doi:10.1109/SCCG.2001.945341. — The graphics origin of the per-column layer stack: the landscape as a 2D array of 1D arrays, each entry a layer of one material with its own properties, and thermal erosion run over it. Read in full. Its own demonstration is the differential-erosion one — a hard letter buried under weak mud, which survives being exhumed — and its cost argument (`k·n²`, not `n³`) is why the structure is affordable at all. It is a *representation* paper: the erosion law it carries is thermal, not fluvial, so it grounds the data structure and not the incision.
- **mitchell2021** `P` — Mitchell, N.A. & Yanites, B.J. (2021). *Bedrock river erosion through dipping layered rocks: quantifying erodibility through kinematic wave speed.* Earth Surface Dynamics 9, 723–753. doi:10.5194/esurf-9-723-2021. Open access, CC-BY; read in full. — 1-D stream-power models of rivers cutting layered stratigraphy, with contact dip as the control variable. Carries the two equations this skill needs: kinematic wave speed for horizontal contacts, and the dip-corrected form. ⚠️ It deliberately does **not** run `n = 1` (see its §2.4), so its own numbers are for `n = 0.67` and `n = 1.5`; the `n = 1` reduction quoted in `stratigraphy-and-lithology.md` is arithmetic on its eq. (6), not a result it reports.
- **forte2016** `P` — Forte, A.M., Yanites, B.J. & Whipple, K.X. (2016). *Complexities of landscape evolution during incision through layered stratigraphy with contrasts in rock strength.* Earth Surface Processes and Landforms 41(12), 1736–1757. doi:10.1002/esp.3947. — The landscape-evolution study that established which properties of a two-unit stratigraphy matter: the erodibility contrast, the **order** of the units, and the contact orientation and dip. ⚠️ **Abstract only.** The full text is behind Wiley; the LSU repository record carries metadata and no file. The locator says `Abstract` because that is what was read.
- **barnhart2018** `P` — Barnhart, K.R., Hutton, E., Gasparini, N.M. & Tucker, G.E. (2018). *Lithology: A Landlab submodule for spatially variable rock properties.* Journal of Open Source Software 3(30), 979. doi:10.21105/joss.00979. CC-BY; both pages read. — The shipped implementation of a depth-varying rock column under a landscape-evolution solver: a generic `Lithology` and a parallel-layer `LithoLayers`, each rock type carrying arbitrary attributes, layers removed by erosion and added by deposition. Its load-bearing contribution here is the **choice of two storage schemes** and what each costs. A two-page software paper, peer-reviewed by JOSS's open review as software — named as that, not dressed as a results paper; the claim taken from it is a description of its own data structures, which is the thing a software paper is authoritative about.
- **strat_authoring** `F` — No canonical source. The authoring recipe for a stratigraphic column in a terrain tool — an ordered thickness list, resistant and weak alternating, per-bed erodibility, jittered thicknesses from a seed, and the whole thing sampled as `K(x, y, z)` through a dip plane — is standard practice in landscape-evolution modelling and in every terrain tool that ships a stratification node, and no paper claims it. The published pieces are separable: `benes2001` grounds the layer stack, `mitchell2021` the dip term, `barnhart2018` the attribute lookup. The *recipe that composes them* is folklore. [no-artefact]

## Grain classes in sediment transport


- **parker1982** `P` — Parker, G. & Klingeman, P.C. (1982). *On why gravel bed streams are paved.* Water Resources Research 18(5), 1409–1423. doi:10.1029/WR018i005p01409. — Why a coarse surface layer forms over a finer subsurface, and the equal-mobility argument behind it: coarse grains are intrinsically less mobile, so the pavement must be what equalises mobility, by exposing proportionally more coarse grains to the flow. The prediction that pavement is absent in most sand-bed streams is the falsifiable half. ⚠️ **Abstract only** — AGU paywall; the locator says `Abstract`.
- **gaea_erosion2** `F` — Gaea 2.x documentation, the Erosion2 node. — The shipped multi-class formulation this skill describes: three sediment classes, **Suspended Load**, **Bed Load** and **Coarse Sediments**, ordered by increasing mass and decreasing mobility, each with an amount slider and its own *Discharge Angle*, the angle being the slope at or above which that class comes to rest. ⚠️ This entry used to name the first control *Discharge Amount*. There is no such control: "Discharge Angle" occurs four times in the whole published Gaea documentation corpus and "Discharge Amount" zero times — the docs say only "Each type has its own Discharge Angle" and refer to "sliders". `hydraulic-erosion.md` already had this right and wrote "an amount slider"; the invented name survived in the one entry whose entire stated value is what the controls are called. Tool documentation, cited as tool documentation: it evidences that the practice exists and what its controls are called, and it is not a derivation. No paper covers the heightfield form.

## Impact cratering


- **pike1977** `P` — Pike, R.J. (1977). *Size-dependence in the shape of fresh impact craters on the moon.* In Roddy, D.J., Pepin, R.O. & Merrill, R.B. (eds.), *Impact and Explosion Cratering*, Pergamon Press (New York), 489–509. — The morphometric reference: eleven size-dependent shape changes, seven of them fitted as log-log regressions in Table 1 (p. 491). Depth, rim height, rim flank width, floor diameter, central-peak relief and ray length, each against rim-crest diameter, each in km, each with a separate fit below and above the simple-to-complex transition. **On the venue:** this is a chapter in the proceedings volume of the Symposium on Planetary Cratering Mechanics (Flagstaff, September 1976), published by Pergamon as an edited book — the same class of artefact as the conference proceedings this bibliography grades `P` elsewhere (duchaineau1997, IEEE Visualization; jensen1996, the Eurographics Rendering Workshop), and graded the same way. A reader who thinks proceedings volumes should be `F` should demote all four together, not this one alone.
- **silber2017** `P` — Silber, E.A., Osinski, G.R., Johnson, B.C. & Grieve, R.A.F. (2017). *Effect of impact velocity and acoustic fluidization on the simple-to-complex transition of lunar craters.* Journal of Geophysical Research: Planets, doi:10.1002/2016JE005236 (paper 2016JE005236; the volume number is not on the accepted manuscript read here and is not asserted). — iSALE modelling of the transitional regime. Cited here only for its introduction and discussion, which state the roughly `1/g` dependence of the transition diameter, put the lunar value at about 19–20 km, and — importantly for anyone tempted to hard-code the scaling — record that Mars and Mercury have essentially identical surface gravity (3.72 and 3.70 m/s²) and measurably different transition diameters.
- **austin2024** `P` — Austin, T., Robinson, M. & Mahanti, P. (2024). *Ejecta blankets at small craters on the Moon.* The Planetary Science Journal 5(5), art. 114, doi:10.3847/PSJ/ad3827. — LROC-derived ejecta thickness profiles at small lunar craters. Gives the radial law as `t = T·(r/R)^−B`, measures `B = 2.8 ± 0.1` against the `B = 3.0` McGetchin et al. (1973) inferred for blankets of all sizes, fits rim thickness with coefficient 0.14 ± 0.062 and exponent 0.77 ± 0.080, and places the edge of the continuous blanket at roughly 3–4 crater radii. Open access.
- **minton2019** `P` — Minton, D.A., Fassett, C.I., Hirabayashi, M., Howl, B.A. & Richardson, J.E. (2019). *The equilibrium size-frequency distribution of small craters reveals the effects of distal ejecta on lunar landscape morphology.* Icarus 326, from p. 63 (accepted 19 February 2019; the end page is not confirmed here and is not asserted). — Production and equilibrium crater size-frequency distributions as cumulative power laws, the result that any steep-sloped production population (`η > 2`) reaches an equilibrium slope `β ≈ 2`, Gault's geometric saturation `0.385 r^−2` and the ~2%-of-saturation empirical ceiling, and the finding that steady diffusive degradation driven by distal ejecta — not cookie-cutting or burial — is what sets the equilibrium.
- **melosh1989** `F` — Melosh, H.J. (1989). *Impact Cratering: A Geologic Process.* Oxford Monographs on Geology and Geophysics 11, Oxford University Press. — The standard textbook: ch. 2 Crater Morphology, ch. 6 Ejecta Deposits, ch. 7 Scaling of Crater Dimensions, ch. 8 Cratering Mechanics: Modification Stage. `F` because it is a textbook and `P` asserts peer review; it is cited in `impact-craters.md` as the synthesis behind a recipe that has no canonical paper, not for any number.

## Constraint and sketch-based authoring


- **hnaidi2010** `P` — Hnaidi, H., Guérin, E., Akkouche, S., Peytavie, A. & Galin, E. (2010). *Feature based terrain generation using diffusion equation.* Computer Graphics Forum 29(7) (Pacific Graphics 2010), 2179–2186, doi:10.1111/j.1467-8659.2010.01806.x. — The reference implementation of constraint-based terrain authoring. A terrain is a set of vector feature curves, each carrying elevation, slope-angle and noise constraints; the dense heightfield is the solution of an over-constrained system mixing three equation orders — identification on the drawn cells, a first-order gradient equation where a slope angle is prescribed, and Laplace everywhere else — relaxed by Jacobi inside a GPU multigrid. Contributes the three things nothing else here has: a stated reason to prefer a gradient equation over a Poisson source term (Poisson loses the gradient's direction, and degenerates to Laplace at a null gradient, which forbids the flat-topped hill), the hard-versus-soft constraint expressed as a single relaxation weight with the paper's own admission of what softening costs, and the rule for two feature curves whose gradients disagree — leave the intersection empty and diffuse the hole shut. Runs no erosion at all, which is the gap `sketch-based-authoring.md` measures rather than cites.
- **orzan2008** `P` — Orzan, A., Bousseau, A., Winnemöller, H., Barla, P., Thollot, J. & Salesin, D. (2008). *Diffusion curves: a vector representation for smooth-shaded images.* ACM Transactions on Graphics 27(3) (SIGGRAPH 2008); the article number is not on the copy read here and is not asserted. doi:10.1145/1360612.1360691. — Not a terrain paper; it is the paper `hnaidi2010` §4.2 borrows its solver from, and it states two things about sparse-to-dense interpolation more clearly than any terrain source. First, the constraint band: rasterising values exactly on a curve makes the two sides collide, so the values are displaced a few pixels normal to the curve and only the gradient constraint is left on it. Second, globality: a Poisson or Laplace solution is global, "any color value can influence any pixel", and the fix for a windowed or zoomed view is a coarse whole-domain solve used as Dirichlet data around the window — which is the tile-seam recipe for any editor that cannot solve the whole planet at full resolution. Cited here for the interpolation problem, never for terrain.
- **gain2009** `P` — Gain, J., Marais, P. & Straßer, W. (2009). *Terrain sketching.* I3D '09: Proceedings of the 2009 Symposium on Interactive 3D Graphics and Games, 31–38, doi:10.1145/1507149.1507155. — The deformation-style half of the family: the user draws a silhouette, a shadow and a boundary curve, and the terrain is warped to match through a multi-scale hierarchy, with wavelet noise whose variance is read off the user's own stroke. Its lasting contribution to this document is the falloff — a C1 weight `(a² − 1)²` on the ratio of distance-from-feature to distance-from-boundary, full weight on the drawn feature and zero slope at the edit's edge — plus the two boundary details that go with it: contract the support with the frequency band, and truncate the curve at its ends so the drawn feature actually lands on the ground. Also the only source here with a user measurement: 10 subjects sketching characteristic silhouettes were 5% to 50% out on noise variance against the terrains they were shown, which is why the system fits an exponential decay rather than using the sketched variance raw.
- **constraint_timing** `F` — The choice of *when* a user constraint is imposed relative to an erosion simulation: before it as an initial condition, during it as a per-step projection, or after it as a composite. There is no paper that frames these as alternatives and compares them. Each source opened for this wave silently picks one — `hnaidi2010` and `gain2009` impose before and never run a solver, `stava2008` edits inputs during, `genevaux2013` composites after — and none discusses the other two. `sketch-based-authoring.md` therefore states it as a three-way choice, says plainly that no canonical source exists, and settles it with measurements in `constraint_solvers.py`, recorded in `registers/pseudocode-execution.tsv` rather than by citation. [no-artefact]

## Periodic noise


- **lagae2010** `P` — Lagae, A., Lefebvre, S., Cook, R., DeRose, T., Drettakis, G., Ebert, D.S., Lewis, J.P., Perlin, K. & Zwicker, M. (2010). *A Survey of Procedural Noise Functions.* Computer Graphics Forum 29(8), 2579–2600, doi:10.1111/j.1467-8659.2010.01827.x. — The field's reference classification, into lattice gradient, explicit and sparse convolution noises. Cited here for the two things it says about periodicity, both of which cut against the grain of this topic. First, §2.3's definition of a *good* procedural noise makes non-periodicity a virtue — a noise should cover an arbitrarily large area "without seams and unwanted repetition" — so the whole literature is optimising away from a tiling requirement. Second, Table 1 and its footnote 1 express every noise's storage requirement "in function of the period N", making the period and the memory the same quantity: Perlin noise is O(N) and is not ticked non-periodic; Gabor and sparse convolution noise are O(1) and are. §7 names the two published escapes, noise tiles and long-period hash functions. The survey does **not** describe the modular-index construction this skill recommends, and is not cited for it.
- **periodic_lattice_practice** `F` — No canonical source. The construction that makes a lattice noise wrap — reduce each lattice integer modulo the domain period before hashing it, so that `i0 = floor(x) mod P` and `i1 = (floor(x)+1) mod P` — together with the two consequences it drags in: that the per-octave period `P·lacunarity^k` must remain an integer, so lacunarity becomes a correctness parameter rather than a taste parameter; and that a noise whose lattice is skewed by an irrational constant (simplex, and OpenSimplex after it) cannot be reindexed this way at all, leaving a four-dimensional torus embedding as the only route. Every part of this is standard practice in shipping noise libraries and none of it has a paper; `lagae2010` §7 gets as close as the literature does, and names *different* fixes (noise tiles, long-period hashing). Graded `F` and left there deliberately: the modular construction is verified in this skill by measurement — bit-exact wrap at periods 7, 16, 64 and 300 in `m1_periodic_noise.py`, recorded in `registers/pseudocode-execution.tsv` — not by citation. [no-artefact]

## Periodic boundary conditions in a simulation


- **hobley2017** `P` — Hobley, D.E.J., Adams, J.M., Nudurupati, S.S., Hutton, E.W.H., Gasparini, N.M., Istanbulluoglu, E. & Tucker, G.E. (2017). *Creative computing with Landlab: an open-source toolkit for building, coupling, and exploring two-dimensional numerical models of Earth-surface dynamics.* Earth Surface Dynamics 5, 21–46, doi:10.5194/esurf-5-21-2017. Open access. — The framework paper for the most widely used landscape-evolution toolkit. Cited here for §3.1.4 and Table 4, which are the clearest published statement that a periodic boundary is one *enumerated modelling choice* among four rather than a post-process: a node is fixed-value (Dirichlet), fixed-gradient (Neumann), **looped**, or closed, and the node status determines whether each attached link carries flux at all — core-to-looped is Active, core-to-closed is Inactive. Two further sentences in the same section carry weight for this document: that "the edges of a Landlab grid are always defined by boundary nodes", so periodicity is expressed by *pairing* perimeter nodes rather than by removing them; and the worked description of a basin whose only outlet is a single fixed-value node with the rest of the perimeter closed, which is exactly the authored-sink recipe a torus requires.
- **seam_fake_practice** `F` — No canonical source. The three constructions used to force a field that does not wrap into wrapping — mirroring the tile about its own edge; cross-blending a margin against the field's own translate with a smootherstep weight; and simulating on a larger domain and cropping back inside the boundary's influence. All three are ubiquitous in terrain tools, shader code and texture pipelines, none has a citable origin, and their costs are what `seamless-and-periodic.md` measures rather than asserts — 100.0% of a mirror seam being a local extremum, `a² + (1−a)²` of the detail variance surviving a blend (0.488 measured against 0.500 predicted), and a crop margin that grows from 3 to 13 cells between 100 and 1200 simulated steps. Graded `F` because the alternative is to hang the claims off a tool's release notes, which would be `N`, or off a paper that nearly says it, which the tier rules forbid. [no-artefact]
