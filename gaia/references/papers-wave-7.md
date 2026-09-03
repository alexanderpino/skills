---
type: Bibliography
title: Papers — sketch and constraint-based terrain authoring
description: "Sources for the seventh wave: constraint-based terrain authoring — feature curves solved as a diffusion problem, the diffusion-curve literature the method is borrowed from, and deformation-style terrain sketching."
tags: [bibliography, provenance, generation, authoring]
status: draft
generated: { by: process:claude-code, at: 2026-09-03T00:00:00Z }
---
# Papers — sketch and constraint-based terrain authoring

One family: a user draws a sparse set of curves, and something has to turn that into a dense
field a physical solver will not immediately destroy. Entry format, tier definitions and the two
non-negotiable rules live in `papers-flow.md`; they are not restated here.

Note for editors: entry ids are written **without** square brackets in this file, for the reason
`papers-rendering.md` gives — a bracketed id in a bibliography body reads as an uncited inline
citation.

## What was read, and what was not

Every `P` below was opened as a full PDF and the cited sections were read in it:

**`hnaidi2010`** — the authors' copy on Éric Galin's LIRIS page. Sections 3 through 6, both
tables and the figure captions read there. Every equation quoted in `sketch-based-authoring.md`
is transcribed from that PDF.
**`orzan2008`** — `diffusion_curves.pdf` from the INRIA Maverick project page for the paper.
Sections 3.2.1, 3.2.2 and 3.2.4 read there.
**`gain2009`** — the author's copy in the University of Cape Town publications archive
(`pubs.cs.uct.ac.za`, `terrsketch.pdf`). Section 4 and section 5 read there; equations (1)–(3)
and the calibration numbers are transcribed from it.

**Two entries this wave's document cites live elsewhere.** `genevaux2013` is defined in
`papers-wave-4.md` and `stava2008` in `papers-generation.md`; both PDFs were opened again for
this document (Purdue CGVLab copies) and the sections newly cited here — `genevaux2013` §7 and
§8, `stava2008` §7 Table 1 and §8 — were read there. They are not redefined below, because a
second entry for the same id is a duplicate, not a citation.

⚠️ **One source is deliberately absent.** Zhou, H., Sun, J., Turk, G. & Rehg, J.M. (2007),
*Terrain synthesis from digital elevation models*, IEEE TVCG 13(4), 834–848, is the
example-based branch that both `hnaidi2010` §2 and `gain2009` §2 position against, and **no
openable copy was reached** — the publisher's copy is paywalled and the two author-side links
found returned HTML, not a PDF. It is therefore not an entry here.
`sketch-based-authoring.md` names it in prose, says it was not reached, and claims nothing about
its contents beyond the one-line characterisation the two papers that *were* opened give it. It
also falls inside this skill's learned-and-example-based exclusion, so nothing rests on it.

## Constraint and sketch-based terrain authoring

- **hnaidi2010** `P` — Hnaidi, H., Guérin, E., Akkouche, S., Peytavie, A. & Galin, E. (2010). *Feature based terrain generation using diffusion equation.* Computer Graphics Forum 29(7) (Pacific Graphics 2010), 2179–2186, doi:10.1111/j.1467-8659.2010.01806.x. — The reference implementation of constraint-based terrain authoring. A terrain is a set of vector feature curves, each carrying elevation, slope-angle and noise constraints; the dense heightfield is the solution of an over-constrained system mixing three equation orders — identification on the drawn cells, a first-order gradient equation where a slope angle is prescribed, and Laplace everywhere else — relaxed by Jacobi inside a GPU multigrid. Contributes the three things nothing else here has: a stated reason to prefer a gradient equation over a Poisson source term (Poisson loses the gradient's direction, and degenerates to Laplace at a null gradient, which forbids the flat-topped hill), the hard-versus-soft constraint expressed as a single relaxation weight with the paper's own admission of what softening costs, and the rule for two feature curves whose gradients disagree — leave the intersection empty and diffuse the hole shut. Runs no erosion at all, which is the gap `sketch-based-authoring.md` measures rather than cites.
- **orzan2008** `P` — Orzan, A., Bousseau, A., Winnemöller, H., Barla, P., Thollot, J. & Salesin, D. (2008). *Diffusion curves: a vector representation for smooth-shaded images.* ACM Transactions on Graphics 27(3) (SIGGRAPH 2008); the article number is not on the copy read here and is not asserted. doi:10.1145/1360612.1360691. — Not a terrain paper; it is the paper `hnaidi2010` §4.2 borrows its solver from, and it states two things about sparse-to-dense interpolation more clearly than any terrain source. First, the constraint band: rasterising values exactly on a curve makes the two sides collide, so the values are displaced a few pixels normal to the curve and only the gradient constraint is left on it. Second, globality: a Poisson or Laplace solution is global, "any color value can influence any pixel", and the fix for a windowed or zoomed view is a coarse whole-domain solve used as Dirichlet data around the window — which is the tile-seam recipe for any editor that cannot solve the whole planet at full resolution. Cited here for the interpolation problem, never for terrain.
- **gain2009** `P` — Gain, J., Marais, P. & Straßer, W. (2009). *Terrain sketching.* I3D '09: Proceedings of the 2009 Symposium on Interactive 3D Graphics and Games, 31–38, doi:10.1145/1507149.1507155. — The deformation-style half of the family: the user draws a silhouette, a shadow and a boundary curve, and the terrain is warped to match through a multi-scale hierarchy, with wavelet noise whose variance is read off the user's own stroke. Its lasting contribution to this document is the falloff — a C1 weight `(a² − 1)²` on the ratio of distance-from-feature to distance-from-boundary, full weight on the drawn feature and zero slope at the edit's edge — plus the two boundary details that go with it: contract the support with the frequency band, and truncate the curve at its ends so the drawn feature actually lands on the ground. Also the only source here with a user measurement: 10 subjects sketching characteristic silhouettes were 5% to 50% out on noise variance against the terrains they were shown, which is why the system fits an exponential decay rather than using the sketched variance raw.
- **constraint_timing** `F` — The choice of *when* a user constraint is imposed relative to an erosion simulation: before it as an initial condition, during it as a per-step projection, or after it as a composite. There is no paper that frames these as alternatives and compares them. Each source opened for this wave silently picks one — `hnaidi2010` and `gain2009` impose before and never run a solver, `stava2008` edits inputs during, `genevaux2013` composites after — and none discusses the other two. `sketch-based-authoring.md` therefore states it as a three-way choice, says plainly that no canonical source exists, and settles it with measurements in `scratchpad/w7/constraint_solvers.py` rather than by citation. [no-artefact]
