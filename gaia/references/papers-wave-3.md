---
type: Bibliography
title: Papers — craters and offline meshing
description: "Sources for the two documents added in the third wave: impact-crater morphometry, ejecta and size-frequency statistics on the generation axis, and offline mesh extraction and simplification on the rendering axis."
tags: [bibliography, provenance, generation, rendering]
status: draft
generated: { by: process:claude-code, at: 2026-09-03T00:00:00Z }
---
# Papers — craters and offline meshing

Two families that did not fit an existing bibliography file. Entry format, tier definitions and
the two non-negotiable rules live in `papers-flow.md`; they are not restated here.

Note for editors: entry ids are written **without** square brackets in this file, for the reason
`papers-rendering.md` gives — a bracketed id in a bibliography body reads as an uncited inline
citation.

## What was read, and what was not

Every `P` below was opened. The specific artefact each grade rests on:

**`pike1977`** — the ADS scanned page images of the Pergamon volume were read directly. Table 1
(p. 491) and equations (1)–(4) (p. 492) are transcribed from that scan, digit for digit, and the
two stated intersection diameters were then reproduced numerically from the transcribed
coefficients as a check on the transcription.
**`austin2024`** — open access at the publisher; §6.2 and equation (1) read there.
**`minton2019`** — the accepted-manuscript PDF; §1.1 and Figure 1 read there.
**`silber2017`** — the accepted-manuscript PDF of the JGR-Planets paper; §1 and §5 read there.
**`garland1997`** — the authors' own PDF of the SIGGRAPH '97 paper; §3–§5 read there.

⚠️ **One source is deliberately absent.** McGetchin, Settle & Head (1973), *Radial thickness
variation in impact crater ejecta*, EPSL 20, 226–236, is the origin of the ejecta falloff
exponent every later paper quotes, and **it could not be obtained** — the publisher's copy is
paywalled and the ADS scan is not retrievable. It is therefore not an entry here, and
`impact-craters.md` cites austin2024 for the exponent instead, which reports both McGetchin's
value and its own measurement. Naming McGetchin in prose, with the paper that reports it as the
citation, is the honest form; adding a bibliography entry for a paper nobody here opened would
not be.

## Impact craters

- **pike1977** `P` — Pike, R.J. (1977). *Size-dependence in the shape of fresh impact craters on the moon.* In Roddy, D.J., Pepin, R.O. & Merrill, R.B. (eds.), *Impact and Explosion Cratering*, Pergamon Press (New York), 489–509. — The morphometric reference: eleven size-dependent shape changes, seven of them fitted as log-log regressions in Table 1 (p. 491). Depth, rim height, rim flank width, floor diameter, central-peak relief and ray length, each against rim-crest diameter, each in km, each with a separate fit below and above the simple-to-complex transition. **On the venue:** this is a chapter in the proceedings volume of the Symposium on Planetary Cratering Mechanics (Flagstaff, September 1976), published by Pergamon as an edited book — the same class of artefact as the conference proceedings this bibliography grades `P` elsewhere (duchaineau1997, IEEE Visualization; jensen1996, the Eurographics Rendering Workshop), and graded the same way. A reader who thinks proceedings volumes should be `F` should demote all four together, not this one alone.
- **silber2017** `P` — Silber, E.A., Osinski, G.R., Johnson, B.C. & Grieve, R.A.F. (2017). *Effect of impact velocity and acoustic fluidization on the simple-to-complex transition of lunar craters.* Journal of Geophysical Research: Planets, doi:10.1002/2016JE005236 (paper 2016JE005236; the volume number is not on the accepted manuscript read here and is not asserted). — iSALE modelling of the transitional regime. Cited here only for its introduction and discussion, which state the roughly `1/g` dependence of the transition diameter, put the lunar value at about 19–20 km, and — importantly for anyone tempted to hard-code the scaling — record that Mars and Mercury have essentially identical surface gravity (3.72 and 3.70 m/s²) and measurably different transition diameters.
- **austin2024** `P` — Austin, T., Robinson, M. & Mahanti, P. (2024). *Ejecta blankets at small craters on the Moon.* The Planetary Science Journal 5(5), art. 114, doi:10.3847/PSJ/ad3827. — LROC-derived ejecta thickness profiles at small lunar craters. Gives the radial law as `t = T·(r/R)^−B`, measures `B = 2.8 ± 0.1` against the `B = 3.0` McGetchin et al. (1973) inferred for blankets of all sizes, fits rim thickness with coefficient 0.14 ± 0.062 and exponent 0.77 ± 0.080, and places the edge of the continuous blanket at roughly 3–4 crater radii. Open access.
- **minton2019** `P` — Minton, D.A., Fassett, C.I., Hirabayashi, M., Howl, B.A. & Richardson, J.E. (2019). *The equilibrium size-frequency distribution of small craters reveals the effects of distal ejecta on lunar landscape morphology.* Icarus 326, from p. 63 (accepted 19 February 2019; the end page is not confirmed here and is not asserted). — Production and equilibrium crater size-frequency distributions as cumulative power laws, the result that any steep-sloped production population (`η > 2`) reaches an equilibrium slope `β ≈ 2`, Gault's geometric saturation `0.385 r^−2` and the ~2%-of-saturation empirical ceiling, and the finding that steady diffusive degradation driven by distal ejecta — not cookie-cutting or burial — is what sets the equilibrium.
- **melosh1989** `F` — Melosh, H.J. (1989). *Impact Cratering: A Geologic Process.* Oxford Monographs on Geology and Geophysics 11, Oxford University Press. — The standard textbook: ch. 2 Crater Morphology, ch. 6 Ejecta Deposits, ch. 7 Scaling of Crater Dimensions, ch. 8 Cratering Mechanics: Modification Stage. `F` because it is a textbook and `P` asserts peer review; it is cited in `impact-craters.md` as the synthesis behind a recipe that has no canonical paper, not for any number.

## Offline mesh extraction and simplification

- **garland1997** `P` — Garland, M. & Heckbert, P.S. (1997). *Surface simplification using quadric error metrics.* SIGGRAPH '97, 209–216, doi:10.1145/258734.258849. — The canonical error-driven simplifier. Iterative contraction of vertex *pairs* (not only edges, so disconnected regions can be joined), with the error at a vertex defined as the sum of squared distances to the planes of its incident triangles and stored as a single symmetric 4×4 quadric; the additive rule for merging two vertices' plane sets, the 4×4 linear solve for the optimal contraction target, and the cost heap that orders the whole run. §6 adds the boundary and discontinuity constraint planes, naming terrain height fields as the case that needs them. Note that the paper is careful about what its metric *is*: a sum of squared distances to a plane set, deliberately double-counting shared planes up to three times, whose absolute value has no intrinsic meaning outside the ranking it produces.
- **garland1995** `F` — Garland, M. & Heckbert, P.S. (1995). *Fast polygonal approximation of terrains and height fields.* Technical report CMU-CS-95-181, School of Computer Science, Carnegie Mellon University; C++ implementation released as `scape`. — The refinement family: greedy insertion of the highest-error grid point into a Delaunay TIN, four progressively optimised variants, the empirical comparison of importance measures that settles on plain vertical error against the current approximation, and the error-versus-vertex-count behaviour. `F` because it is a technical report and never went through peer review; the report itself records that greedy insertion "has been reinvented many times", so there is no canonical paper to promote to, and the honest form is to say so. Still the most useful single treatment of simplification aimed specifically at a heightfield.
- **hoppe1996** `P` — Hoppe, H. (1996). *Progressive meshes.* SIGGRAPH '96, 99–108, doi:10.1145/237170.237216. — The nested multiresolution representation: a base mesh plus a stream of vertex-split records, built by edge collapses alone, from which every intermediate mesh in the chain is recoverable. Cited here for the structural consequence rather than the construction — because consecutive levels share vertices by construction, a geomorph between them is definable at all, which is the property an exported LOD chain either has or does not.
