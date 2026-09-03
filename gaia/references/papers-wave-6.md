---
type: Bibliography
title: Papers — mask operators and mask-to-material
description: "Sources for the two documents added in the sixth wave: distance transforms and connected-component filtering on the mask axis, and the path from a mask weight to a rendered albedo on the material axis."
tags: [bibliography, provenance, generation, rendering, materials]
status: draft
generated: { by: process:claude-code, at: 2026-09-03T00:00:00Z }
---
# Papers — mask operators and mask-to-material

Two families that did not fit an existing bibliography file. Entry format, tier definitions and
the two non-negotiable rules live in `papers-flow.md`; they are not restated here.

Note for editors: entry ids are written **without** square brackets in this file, for the reason
`papers-rendering.md` gives — a bracketed id in a bibliography body reads as an uncited inline
citation.

## What was read, and what was not

Every `P` below was opened. The specific artefact each grade rests on:

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

## Distance transforms and component labelling

- **felzenszwalb2012** `P` — Felzenszwalb, P.F. & Huttenlocher, D.P. (2012). *Distance transforms of sampled functions.* Theory of Computing 8(19), 415–428, doi:10.4086/toc.2012.v008a019. — The separable exact algorithm. The distance transform of a sampled function is defined as `D_f(p) = min_q [ d(p,q) + f(q) ]`, which reduces to the classical binary transform when `f` is the 0/∞ indicator of the seed set. Under the *squared* Euclidean distance the one-dimensional problem is the lower envelope of `n` equal parabolas rooted at `(q, f(q))`, computable in O(n) because the parabolas arrive already sorted by vertex; the multi-dimensional case is a composition of one-dimensional transforms along each axis, O(dN) overall. The paper is explicit that it is not the first linear-time exact EDT — it cites Karzanov 1992, Breu et al. 1995 and Maurer et al. 2003 — and that its contribution is that the others "are quite involved and are not widely used in practice". Open access.
- **meijster2000** `P` — Meijster, A., Roerdink, J.B.T.M. & Hesselink, W.H. (2000). *A general algorithm for computing distance transforms in linear time.* In Goutsias, J., Vincent, L. & Bloomberg, D.S. (eds.), *Mathematical Morphology and its Applications to Image and Signal Processing* (ISMM 2000), Computational Imaging and Vision 18, Kluwer, 331–340. — The other standard separable exact EDT, and the one worth reading second because it derives the same row-column factorisation from a different direction: a first phase that reduces each column to the distance to the nearest seed *in that column*, and a second phase that combines columns via a lower envelope. Written for three metrics at once — Euclidean, Manhattan and chessboard — differing only in the per-metric function `f`, which is the cleanest available statement of what the separable structure actually buys.
- **hajdu2012** `P` — Hajdu, A., Hajdu, L. & Tijdeman, R. (2012). *Approximation of the Euclidean distance by chamfer distances.* Acta Cybernetica 20(3), 399–417. Read as arXiv:1201.0876v1. — Determines the *best possible* maximum relative error of a chamfer mask at each neighbourhood size, under three different boundary conditions, and prints the classical Borgefors masks and their errors for comparison. The comparison table is the useful part for a tool builder: the 3×3 `<3,4>` mask, the 5×5 `<5,7,11>` mask and the 7×7 mask have maximum relative errors of 0.0572, 0.0198 and 0.0138, against optimal-for-their-size values of 0.0396, 0.0136 and 0.0065.
- **rongtan2006** `P` — Rong, G. & Tan, T.-S. (2006). *Jump flooding in GPU with applications to Voronoi diagram and distance transform.* Proc. ACM Symposium on Interactive 3D Graphics and Games (I3D '06), 109–116, doi:10.1145/1111411.1111431. — The GPU method: each grid point carries its best-known seed, and `log n` rounds of flooding with step lengths `n/2, n/4, …, 1` propagate every seed to every point. The paper is unusually honest about being an approximation — §5 analyses where errors occur (at and around Voronoi vertices), §6 measures them on 10000 random runs per configuration, and §3 gives the JFA+1 and JFA+2 variants that add rounds of step length 1 to clean them up. It also rejects the obvious alternative of *doubling* the step length, with a figure showing the error explosion.
- **fiorio1996** `P` — Fiorio, C. & Gustedt, J. (1996). *Two linear time Union-Find strategies for image processing.* Theoretical Computer Science 154(2), 165–181, doi:10.1016/0304-3975(94)00262-2. — The honest complexity statement for label merging. §1 records that general union-find is O(α(n,m)·m) by Tarjan's algorithm, that this bound is *sharp* for pointer machines, and that whether a RAM can do better is open — then shows that the restricted sequence of unions produced by a raster scan is linear, because the trees can be kept flat. This is the paper that makes "union-find is basically constant time" a theorem for this use rather than a folk belief.
- **wu2009** `P` — Wu, K., Otoo, E. & Suzuki, K. (2009). *Optimizing two-pass connected-component labeling algorithms.* Pattern Analysis and Applications 12(2), 117–135, doi:10.1007/s10044-008-0109-y. — The practical two-pass labeller. §1.1 lays out the three phases — scan with provisional labels, analyse equivalences, relabel — and the taxonomy of multi-pass, two-pass and one-pass approaches. §3 gives the array-based union-find; §4.1 the decision tree that cuts the average number of neighbours examined by about half; §4.2 Theorem 3 proves that a two-pass labeller using *any* union-find with path compression runs in O(p) for `p` pixels, generalising fiorio1996.
- **salembier2009** `P` — Salembier, P. & Wilkinson, M.H.F. (2009). *Connected operators: A review of region-based morphological image processing techniques.* IEEE Signal Processing Magazine 26(6), 136–157, doi:10.1109/MSP.2009.934154. — Why a component filter is not an opening. Connected operators act by merging flat zones, so they "cannot create new contours nor modify their position"; the area opening removes every connected component below a pixel-count threshold and is shown to equal the *supremum of all possible openings by a connected structuring element of that many pixels*, which is exactly the sense in which it is shape-agnostic where a disk opening is not. §"Size filtering" and Fig. 11 for the operator, Figs. 17–18 for the union-find implementation, Fig. 21 for the side-by-side against a disk opening. **On the venue:** a review article in a peer-reviewed IEEE magazine. A reader who thinks magazine reviews should be `F` should say so and demote it; nothing here rests on it alone.

## Mask to material

- **sharma2005** `P` — Sharma, G., Wu, W. & Dalal, E.N. (2005). *The CIEDE2000 color-difference formula: Implementation notes, supplementary test data, and mathematical observations.* Color Research & Application 30(1), 21–30, doi:10.1002/col.20070. — The colour-difference metric, plus the thing that makes it usable: 34 supplementary CIELAB pairs with published ΔE00 values, designed to catch the implementation errors — signed chroma and hue differences, the arctangent quadrant, the mean-hue boundary cases — that the CIE's own worked examples do not. The paper's own account is that several widely distributed implementations, including the authors' early ones, passed the CIE examples and were still wrong.
- **moreland2009** `P` — Moreland, K. (2009). *Diverging color maps for scientific visualization.* Proc. 5th International Symposium on Visual Computing (ISVC 2009), LNCS 5876, 92–103. Read as the author's expanded version, `ColorMapsExpanded.pdf`. — Mapping a scalar to a colour, done deliberately. §2 is the case against the rainbow map: no perceptual ordering, non-uniform perceptual rate, and sensitivity to colour-vision deficiency. §3 gives the sRGB → linear → XYZ → CIELAB chain, eqs. (1)–(3), and states the operative distinction for a terrain palette — physical light effects belong in a linear space, perception of a colour belongs in CIELAB.
- **icc_srgb** `F` — International Color Consortium. *How to interpret the sRGB color space (specified in IEC 61966-2-1) for ICC profiles*, color.org. — The sRGB transfer function and primaries, restated from the standard by the body that maintains ICC profiles. §A.7 gives the XYZ(D65) → linear sRGB matrix; §B gives the encoding and decoding equations with the 0.0031308 / 0.04045 thresholds, the 12.92 slope, the 0.055 offset and the 2.4 exponent. `F` because it is a standards-body technical note, not peer review, and because the normative document it restates — IEC 61966-2-1 — is paywalled and was not opened.
- **srgb1996** `F` — Stokes, M., Anderson, M., Chandrasekar, S. & Motta, R. (1996). *A Standard Default Color Space for the Internet — sRGB*, version 1.10, W3C Note. — The original proposal. Cited here only for the warning W3C now prints at the top of it: the document is obsolete, sRGB was standardised as IEC 61966-2-1, and "during standardization, a small numerical error caused by rounding error was corrected". That is the provenance of every slightly-different set of sRGB constants in circulation. The equations themselves are images in the HTML and were not read as text, which is why icc_srgb is cited for the numbers instead.
