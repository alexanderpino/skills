---
type: Bibliography
title: Papers — seamless output and periodic boundaries
description: "Sources for the eighth-wave document on tiling without a seam: the noise survey that grades periodicity as a defect, and the landscape-evolution framework that names a periodic boundary as one of four."
tags: [bibliography, provenance, generation, noise, erosion, boundary-conditions]
status: draft
generated: { by: process:claude-code, at: 2026-09-03T00:00:00Z }
---
# Papers — seamless output and periodic boundaries

Entries new to the corpus for `seamless-and-periodic.md`. Entry format, tier definitions and the
two non-negotiable rules live in `papers-flow.md`; they are not restated here. That document also
cites `perlin2002` (papers-generation.md), `mei2007` (papers-generation.md) and `barnes2014`
(papers-flow.md), which already exist and are deliberately **not** duplicated here.

Note for editors: entry ids are written **without** square brackets in this file, for the reason
`papers-rendering.md` gives — a bracketed id in a bibliography body reads as an uncited inline
citation.

## What was read, and what was not

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

**`barnes2014`** — the arXiv/accepted PDF already in the corpus, re-opened for this document. §1,
§3.1 and §3.3 read there.

⚠️ **One source is named in prose and deliberately absent.** Lagae & Dutré, *Long-period hash
functions for procedural texturing* — the reference `lagae2010` §7 gives for improving a lattice
noise's period — **was not obtained**. `seamless-and-periodic.md` therefore attributes the
period-versus-storage relationship to the survey that reports it, and grades the modular-indexing
construction it recommends as `F`, rather than borrowing authority from a paper nobody here read.

## Periodic noise

- **lagae2010** `P` — Lagae, A., Lefebvre, S., Cook, R., DeRose, T., Drettakis, G., Ebert, D.S., Lewis, J.P., Perlin, K. & Zwicker, M. (2010). *A Survey of Procedural Noise Functions.* Computer Graphics Forum 29(8), 2579–2600, doi:10.1111/j.1467-8659.2010.01827.x. — The field's reference classification, into lattice gradient, explicit and sparse convolution noises. Cited here for the two things it says about periodicity, both of which cut against the grain of this topic. First, §2.3's definition of a *good* procedural noise makes non-periodicity a virtue — a noise should cover an arbitrarily large area "without seams and unwanted repetition" — so the whole literature is optimising away from a tiling requirement. Second, Table 1 and its footnote 1 express every noise's storage requirement "in function of the period N", making the period and the memory the same quantity: Perlin noise is O(N) and is not ticked non-periodic; Gabor and sparse convolution noise are O(1) and are. §7 names the two published escapes, noise tiles and long-period hash functions. The survey does **not** describe the modular-index construction this skill recommends, and is not cited for it.
- **periodic_lattice_practice** `F` — No canonical source. The construction that makes a lattice noise wrap — reduce each lattice integer modulo the domain period before hashing it, so that `i0 = floor(x) mod P` and `i1 = (floor(x)+1) mod P` — together with the two consequences it drags in: that the per-octave period `P·lacunarity^k` must remain an integer, so lacunarity becomes a correctness parameter rather than a taste parameter; and that a noise whose lattice is skewed by an irrational constant (simplex, and OpenSimplex after it) cannot be reindexed this way at all, leaving a four-dimensional torus embedding as the only route. Every part of this is standard practice in shipping noise libraries and none of it has a paper; `lagae2010` §7 gets as close as the literature does, and names *different* fixes (noise tiles, long-period hashing). Graded `F` and left there deliberately: the modular construction is verified in this skill by measurement — bit-exact wrap at periods 7, 16, 64 and 300 in `w8/m1_periodic_noise.py` — not by citation. [no-artefact]

## Periodic boundary conditions in a simulation

- **hobley2017** `P` — Hobley, D.E.J., Adams, J.M., Nudurupati, S.S., Hutton, E.W.H., Gasparini, N.M., Istanbulluoglu, E. & Tucker, G.E. (2017). *Creative computing with Landlab: an open-source toolkit for building, coupling, and exploring two-dimensional numerical models of Earth-surface dynamics.* Earth Surface Dynamics 5, 21–46, doi:10.5194/esurf-5-21-2017. Open access. — The framework paper for the most widely used landscape-evolution toolkit. Cited here for §3.1.4 and Table 4, which are the clearest published statement that a periodic boundary is one *enumerated modelling choice* among four rather than a post-process: a node is fixed-value (Dirichlet), fixed-gradient (Neumann), **looped**, or closed, and the node status determines whether each attached link carries flux at all — core-to-looped is Active, core-to-closed is Inactive. Two further sentences in the same section carry weight for this document: that "the edges of a Landlab grid are always defined by boundary nodes", so periodicity is expressed by *pairing* perimeter nodes rather than by removing them; and the worked description of a basin whose only outlet is a single fixed-value node with the rest of the perimeter closed, which is exactly the authored-sink recipe a torus requires.
- **seam_fake_practice** `F` — No canonical source. The three constructions used to force a field that does not wrap into wrapping — mirroring the tile about its own edge; cross-blending a margin against the field's own translate with a smootherstep weight; and simulating on a larger domain and cropping back inside the boundary's influence. All three are ubiquitous in terrain tools, shader code and texture pipelines, none has a citable origin, and their costs are what `seamless-and-periodic.md` measures rather than asserts — 100.0% of a mirror seam being a local extremum, `a² + (1−a)²` of the detail variance surviving a blend (0.488 measured against 0.500 predicted), and a crop margin that grows from 3 to 13 cells between 100 and 1200 simulated steps. Graded `F` because the alternative is to hang the claims off a tool's release notes, which would be `N`, or off a paper that nearly says it, which the tier rules forbid. [no-artefact]
