---
type: Bibliography
title: Papers — masks and filtering
description: "Sources for the operators that turn a heightfield into a mask and a mask into something usable: exact and approximate distance transforms, connected-component labelling and area filtering, multi-band scale-space decomposition, and the edge-aware filters that smooth a mask without moving its edges."
tags: [bibliography, provenance, generation, rendering, masks]
status: draft
generated: { by: process:claude-code, at: 2026-09-03T00:00:00Z }
---
# Papers — masks and filtering

The family that several other documents assume and none of them owns. A distance field, a
despeckled mask, a band-split surface and a slope or curvature map are all the same kind of
object — a scalar derived from the heightfield and then consumed by something else — and their
sources belong together rather than scattered across the axis they happen to serve.

**The tier table, the `[not-opened]` rule and the two non-negotiable rules live in
`papers-flow.md`** and are not repeated here. Read them before citing anything below.

Entry ids are written **without** square brackets in this file, for the reason
`papers-rendering.md` gives — a bracketed id in a bibliography body reads as an uncited inline
citation.

## What was read, and what was not

**felzenszwalb2012** — the journal's own open-access PDF at theoryofcomputing.org. Algorithm 1,
Theorems 2.1–3.2 and §2.2 read there; Algorithm 1 was then transcribed into
`scratchpad/w6/edt_error.py` and its output checked against brute force.
**meijster2000** — a course-hosted scan of the Kluwer chapter, complete with the printed page
numbers 331–340 used in the locators.
**hajdu2012** — **the arXiv preprint 1201.0876v1 was read, not the journal version.** The
preprint's own footer says "Preprint submitted to Acta Cybernetica"; the published record is
Acta Cybernetica 20(3), 399–417 (2012), which was located but not opened. The three error
constants quoted from it were independently reproduced numerically, which is the only reason
the citation is worth anything here.
**rongtan2006** — the authors' submitted version at comp.nus.edu.sg. It has no ACM pagination,
so the page range below comes from the ACM record rather than from the artefact read, and the
locators cite sections and figures instead of pages.
**fiorio1996** — the HAL deposit of the published Theoretical Computer Science article, printed
pagination intact. The OCR is poor (it renders "can" as "tan" throughout) but legible.
**wu2009** — the authors' accepted manuscript at sdm.lbl.gov. No journal pagination, so the
locators cite numbered sections and theorems.
**salembier2009** — the authors' PDF at imatge.upc.edu, figure numbering intact.
**sharma2005** — the author's PDF at hajim.rochester.edu, plus the 34-pair supplementary test
file `ciede2000testdata.txt` from the same site, which was used to validate the implementation
in `scratchpad/w6/colour_blend.py`.
**moreland2009** — **the author's "Expanded" version was read, not the ISVC proceedings paper.**
Section and equation numbers in the locator refer to that expanded PDF, and the proceedings
pagination is not asserted.

⚠️ **Four sources are deliberately absent.** **Rosenfeld & Pfaltz (1966)**, *Sequential
operations in digital picture processing*, JACM 13(4), 471–494, is the origin of both the
two-pass raster labelling scan and the two-pass L1 distance transform; **Borgefors (1986)**,
*Distance transformations in digital images*, CVGIP 34(3), 344–371, is the origin of the 3-4 and
5-7-11 chamfer masks; **Danielsson (1980)**, *Euclidean distance mapping*, CVGIP 14, 227–248, is
the origin of the vector-propagation family; and **IEC 61966-2-1** is the sRGB standard itself.
All four are paywalled or unobtainable here. They are named in prose in the documents, with an
opened paper that reports their content cited in their place — felzenszwalb2012 for
Rosenfeld & Pfaltz, hajdu2012 for the Borgefors masks, meijster2000 for Danielsson, icc_srgb for
the sRGB constants. Adding bibliography entries for papers nobody here opened would not be
honest.

⚠️ **The entries in `## Terrain analysis and edge-aware filtering` came from `papers-generation.md`
and predate this practice.** Several were never obtained and now say so with `[not-opened]`;
that tag, not this section, is where their status is recorded.
## Distance transforms and component labelling


- **felzenszwalb2012** `P` — Felzenszwalb, P.F. & Huttenlocher, D.P. (2012). *Distance transforms of sampled functions.* Theory of Computing 8(19), 415–428, doi:10.4086/toc.2012.v008a019. — The separable exact algorithm. The distance transform of a sampled function is defined as `D_f(p) = min_q [ d(p,q) + f(q) ]`, which reduces to the classical binary transform when `f` is the 0/∞ indicator of the seed set. Under the *squared* Euclidean distance the one-dimensional problem is the lower envelope of `n` equal parabolas rooted at `(q, f(q))`, computable in O(n) because the parabolas arrive already sorted by vertex; the multi-dimensional case is a composition of one-dimensional transforms along each axis, O(dN) overall. The paper is explicit that it is not the first linear-time exact EDT — it cites Karzanov 1992, Breu et al. 1995 and Maurer et al. 2003 — and that its contribution is that the others "are quite involved and are not widely used in practice". Open access.
- **meijster2000** `P` — Meijster, A., Roerdink, J.B.T.M. & Hesselink, W.H. (2000). *A general algorithm for computing distance transforms in linear time.* In Goutsias, J., Vincent, L. & Bloomberg, D.S. (eds.), *Mathematical Morphology and its Applications to Image and Signal Processing* (ISMM 2000), Computational Imaging and Vision 18, Kluwer, 331–340. — The other standard separable exact EDT, and the one worth reading second because it derives the same row-column factorisation from a different direction: a first phase that reduces each column to the distance to the nearest seed *in that column*, and a second phase that combines columns via a lower envelope. Written for three metrics at once — Euclidean, Manhattan and chessboard — differing only in the per-metric function `f`, which is the cleanest available statement of what the separable structure actually buys.
- **hajdu2012** `P` — Hajdu, A., Hajdu, L. & Tijdeman, R. (2012). *Approximation of the Euclidean distance by chamfer distances.* Acta Cybernetica 20(3), 399–417. Read as arXiv:1201.0876v1. — Determines the *best possible* maximum relative error of a chamfer mask at each neighbourhood size, under three different boundary conditions, and prints the classical Borgefors masks and their errors for comparison. The comparison table is the useful part for a tool builder: the 3×3 `<3,4>` mask, the 5×5 `<5,7,11>` mask and the 7×7 mask have maximum relative errors of 0.0572, 0.0198 and 0.0138, against optimal-for-their-size values of 0.0396, 0.0136 and 0.0065.
- **rongtan2006** `P` — Rong, G. & Tan, T.-S. (2006). *Jump flooding in GPU with applications to Voronoi diagram and distance transform.* Proc. ACM Symposium on Interactive 3D Graphics and Games (I3D '06), 109–116, doi:10.1145/1111411.1111431. — The GPU method: each grid point carries its best-known seed, and `log n` rounds of flooding with step lengths `n/2, n/4, …, 1` propagate every seed to every point. The paper is unusually honest about being an approximation — §5 analyses where errors occur (at and around Voronoi vertices), §6 measures them on 10000 random runs per configuration, and §3 gives the JFA+1 and JFA+2 variants that add rounds of step length 1 to clean them up. It also rejects the obvious alternative of *doubling* the step length, with a figure showing the error explosion.
- **fiorio1996** `P` — Fiorio, C. & Gustedt, J. (1996). *Two linear time Union-Find strategies for image processing.* Theoretical Computer Science 154(2), 165–181, doi:10.1016/0304-3975(94)00262-2. — The honest complexity statement for label merging. §1 records that general union-find is O(α(n,m)·m) by Tarjan's algorithm, that this bound is *sharp* for pointer machines, and that whether a RAM can do better is open — then shows that the restricted sequence of unions produced by a raster scan is linear, because the trees can be kept flat. This is the paper that makes "union-find is basically constant time" a theorem for this use rather than a folk belief.
- **wu2009** `P` — Wu, K., Otoo, E. & Suzuki, K. (2009). *Optimizing two-pass connected-component labeling algorithms.* Pattern Analysis and Applications 12(2), 117–135, doi:10.1007/s10044-008-0109-y. — The practical two-pass labeller. §1.1 lays out the three phases — scan with provisional labels, analyse equivalences, relabel — and the taxonomy of multi-pass, two-pass and one-pass approaches. §3 gives the array-based union-find; §4.1 the decision tree that cuts the average number of neighbours examined by about half; §4.2 Theorem 3 proves that a two-pass labeller using *any* union-find with path compression runs in O(p) for `p` pixels, generalising fiorio1996.
- **salembier2009** `P` — Salembier, P. & Wilkinson, M.H.F. (2009). *Connected operators: A review of region-based morphological image processing techniques.* IEEE Signal Processing Magazine 26(6), 136–157, doi:10.1109/MSP.2009.934154. — Why a component filter is not an opening. Connected operators act by merging flat zones, so they "cannot create new contours nor modify their position"; the area opening removes every connected component below a pixel-count threshold and is shown to equal the *supremum of all possible openings by a connected structuring element of that many pixels*, which is exactly the sense in which it is shape-agnostic where a disk opening is not. §"Size filtering" and Fig. 11 for the operator, Figs. 17–18 for the union-find implementation, Fig. 21 for the side-by-side against a disk opening. **On the venue:** a review article in a peer-reviewed IEEE magazine. A reader who thinks magazine reviews should be `F` should say so and demote it; nothing here rests on it alone.

## Scale-space decomposition


- **burt1983** `P` — Burt, P.J. & Adelson, E.H. (1983). *The Laplacian Pyramid as a Compact
  Image Code.* IEEE Transactions on Communications COM-31(4), 532–540. — The Gaussian/Laplacian
  pyramid. Read for this document. **§The Generating Kernel, p. 533** gives the separable,
  normalized, symmetric 5-tap kernel and the *equal contribution* constraint `a + 2c = 2b`,
  which fixes `ŵ(0)=a, ŵ(±1)=1/4, ŵ(±2)=1/4 − a/2` — one free parameter, not five.
  **Fig. 3, p. 534**: `a=0.5` is triangular, `a=0.4` Gaussian-like, `a=0.3` broader, and at
  `a=0.6` "the central positive mode is sharply peaked, and is flanked by small negative lobes"
  — the "Gaussian" pyramid is not non-negative at the value the paper itself later prefers
  (p. 537, greatest entropy reduction). **Eq. (3), p. 535** defines the band as
  `L_l = g_l − EXPAND(g_{l+1})`, **eq. (4)** gives exact reconstruction by summing expanded
  levels, and the same page describes the Laplacian levels as "a set of bandpass filtered copies
  of the image". ⚠️ The paper claims **exact reconstruction**; it makes no claim about preserving
  a sum, a mean or a volume, and it must not be cited for one.

- **paris2011** `P` — Paris, S., Hasinoff, S.W. & Kautz, J. (2011). *Local Laplacian Filters:
  Edge-aware Image Processing with a Laplacian Pyramid.* ACM TOG 30(4) (SIGGRAPH 2011), 68:1–68:12.
  — Read for this document. **§2, "Pyramid-based Edge-aware Filtering"** states the failure mode of
  a per-band gain UI in one sentence: "A first approach is to directly rescale the coefficients of a
  Laplacian pyramid, however, this typically produces halos." **§3.2 and Fig. 3** show it — clipping
  large coefficients leaves the signal "somewhat deformed near edges… manifested in images as thin
  but unsightly rim halos", and the caption adds that truncation "smooths the edge". **§4,
  Algorithm 1** is the O(N log N) fix: build the output pyramid coefficient by coefficient from a
  point-wise remapped copy of the input, then collapse. The same section gives the support width of
  one Laplacian coefficient for the standard 5-tap kernel, **K = 3(2^(l0+2) − 1)** — which is
  exactly `2·R(l0+1) + 1` for the halo radius `R(L) = 3·2^L − 2` measured independently in
  `surface-and-scale-space.md`.

## Tool practice — the surface-modification contract


No canonical paper covers how an authoring tool separates silhouette from surface; these are
vendors documenting their own products, cited for **what a shipping tool chose**, which is
evidence about practice and never about correctness.

- **gaea_surface** `F` — QuadSpinner. *Gaea 2 Documentation*, Using Gaea → "Surface Nodes"
  (slug `surface-nodes`). https://docs.gaea.app/ — the site is JS-rendered; the full corpus is
  published as plain text at https://docs.gaea.app/llms-full.txt. — States the motivation
  verbatim: "when you erode a terrain or apply a strong effect filter, the overall terrain shape
  is diminished (sometimes even completely destroyed)", and the contract under the heading
  **Volume Preservation**: the tools "separate the process of designing the overall terrain shape
  (or volume) and designing the superficial shapes on the surface", so the user can "modify the
  surface without altering the overall shape, volume, or silhouette".
- **gaea_bands** `F` — QuadSpinner. *Gaea 2 Documentation*, Node Reference, slugs `filter`,
  `graphiceq`, `deflate`, `transpose` and `shaper` (same llms-full.txt corpus). — Four UIs over
  one mechanism. `filter` is "an audio-inspired parametric filter … useful for isolating or
  suppressing features at specific scales", with LowPass/HighPass/LowShelf/HighShelf/BandPass/
  Notch/Bell modes, Frequency/Gain/Q, and a **Keep DC** toggle that "preserves the overall
  baseline/average height (DC offset) so the filter affects detail without shifting the mean
  elevation". `graphiceq` is seven fixed bands with per-band gain, positive boosting and negative
  suppressing "features at that scale". `deflate` "takes away the bulk of the terrain leaving only
  finer details". `transpose` "takes the character of the Reference terrain and applies [it] to the
  Input terrain… maintains the original volume and shape of the Input terrain so you do not lose
  your silhouette". `shaper` exposes the split's cutoff directly as **Maintain Fine Details**
  ("finer detail is preserved regardless of shape changes") plus **Detail Size** ("the scale of
  details to be preserved or affected during shaping").

## Terrain analysis and edge-aware filtering


- **horn1981** `P` [not-opened] — Horn, B.K.P. (1981). *Hill shading and the reflectance map.* Proceedings of
  the IEEE 69(1), 14–47. — The Sobel-weighted slope and aspect estimator GIS tools use.
  ⚠️ **Not obtained** — paywalled at IEEE and the MIT author copies now 404, so no locator into it
  is verified here.
- **zevenbergen1987** `P` [not-opened] — Zevenbergen, L.W. & Thorne, C.R. (1987). *Quantitative analysis of
  land surface topography.* Earth Surface Processes and Landforms 12(1), 47–56. — The 3×3
  partial-quartic fit; profile and plan curvature. ⚠️ **Not obtained** — paywalled at Wiley, no
  open copy reachable, so the coefficient and curvature expressions `terrain-analysis-masks.md`
  writes out are the standard published form and have **not** been checked against Zevenbergen &
  Thorne's own numbering.
- **beven1979** `P` [not-opened] — Beven, K.J. & Kirkby, M.J. (1979). *A physically based, variable
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
- **he2010** `P` [not-opened] — He, K., Sun, J. & Tang, X. (2010). *Guided Image Filtering.* ECCV 2010;
  extended in IEEE PAMI 35(6), 2013, 1397–1409. — O(1) per cell at any radius, no gradient
  reversal, and it accepts a separate guide image. Better than bilateral for terrain.
  ⚠️ **Not obtained** — the SpringerLink chapter PDF served an HTML shell and both author copies
  404, so no locator into it is verified here.
