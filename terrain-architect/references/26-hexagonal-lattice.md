# 26 — Hexagonal lattice heightfields

The implementation depth behind `08`'s hexagonal-grids section — `08` owns the grid-system case
(why and when to choose hex, interchange, and the spherical hex-DGGS closure); this chapter owns
building on it — and the **fourth cure** in `09`'s grid-anisotropy family: change the lattice so
no preferred axis exists. Symbol note: `08` writes `s` for the hexagon circumradius and `d` for
the centre-to-centre neighbour spacing in its stencil formulas; here `s` IS that centre-to-centre
spacing (`= 08`'s `d` `= √3 ×` its circumradius) — the `cellSize` contract is the same, the
formulas are not interchangeable without converting symbols.

**What it is for — and the expectation to correct first.** A hexagonal sampling lattice is a real,
citable fix for one specific defect class: **stencil-printed 4-fold anisotropy** and the diagonal
ambiguity of the square grid. It is *not* a route to "more organic shapes" — organic-ness is process
history (`SKILL.md` doctrine), and hex changes the discretisation of the process, not the process.
What a user actually sees is the *absence of a defect*: no plus-shaped thermal cones, no 45°-biased
drainage, no diagonal-choice flicker — and where the lattice does print through, a 6-fold signature
at 15.5% eccentricity instead of a 4-fold one at 41.4% (`C4` lock = √2 ≈ 1.414; `C6` lock =
2/√3 ≈ 1.155 — geometric floors, derivable).

## Provenance spine (tiers per `00`)

- **Sampling optimality** — P. Petersen & Middleton 1962, *Information and Control* 5(4):279–323:
  for a signal band-limited to a **disc**, the hexagonal lattice is the minimum-density
  alias-free sampling lattice. The saving is exact: `1 − √3/2 = 13.4%` fewer samples.
  **Caveat that gets dropped:** disc band-limits only. For square-band-limited content (dune
  fields, foliated strata — `05`, `18`) the square lattice wins. Terrain post-FBM is
  approximately isotropic, so the assumption usually holds.
- **Hexagonal image processing** — P (book). Middleton & Sivaswamy 2005, *Hexagonal Image
  Processing: A Practical Approach*, Springer, ISBN 9781852339142 (cite the ISBN; the series name
  was rebranded). Square↔hex resampling done properly: Van De Ville, Philips & Lemahieu 2002,
  *Signal Processing: Image Communication* 17(5):393–408. Hex FFT with rectangular output:
  Ehrhardt 1993, *IEEE TSP* 41(3):1469–1472. Survey: Magillo 2025, *Computer Science Review* 56.
  (Mersereau 1979, *Proc. IEEE* 67(6):930–949 is the classic restatement — metadata verified, text
  paywalled at verification time; the 13.4% figure above is re-derived, not quoted.)
- **The transport-isotropy precedent** — P for the papers. HPP (square, 4 velocities) fails to
  reproduce isotropic Navier–Stokes; FHP on the triangular lattice succeeds: Hardy, Pomeau &
  de Pazzis 1973 (*J. Math. Phys.* 14:1746); Frisch, Hasslacher & Pomeau 1986 (*PRL* 56:1505);
  Wolfram 1986 (*J. Stat. Phys.* 45:471). Mechanism (standard result, re-derived in §Kernels): C4
  symmetry leaves the 4th-rank moment tensor anisotropic; C6 makes it isotropic. Same lineage as
  the corpus's *randomise* cure (Miyamoto & Sasaki, `19`) — hex is the *lattice* cure. Same effect
  in FD stencils: Hamilton & Bilbao 2013 (POMA 19, ICA — text not independently read).
- **D6 drainage on hex DEMs** — P. Wang & Ai 2018 (ISPRS Archives XLII-4:687–692): D6 introduced by
  analogy with D8; hex DEMs hold drainage-network shape better at coarse resolution. Wang, Ai,
  Shen & Li 2020 (*Transactions in GIS* 24(2):483–507): D8's orthogonal-vs-diagonal distance
  inconsistency is the named cause of anisotropic valley extraction; hex removes it. Production
  hydrology: Liao et al. 2020 (already in `99`); **Landlab** ships first-class hex grids
  (Hobley 2017; Barnhart 2020, *ESurf* 8:379): FlowDirectorSteepest (=D6), MFD, accumulation and
  the grid-agnostic streampower/diffusion components run on hex; **D8 and D∞ do not exist there**
  (raster-specific by their own documentation).
- **Practitioner coordinates** — F, folklore-canonical and say so: Patel, *Hexagonal Grids*
  (redblobgames.com) — the games-industry reference; never dress it as peer-reviewed. Peer-reviewed
  hierarchical hex indexing (Gibson & Lucas 1982 GBT) is **?** — proceedings metadata unverified.
- **CG erosion on hex heightfields** — **? / absent.** No graphics paper doing hydraulic or thermal
  erosion on a hex heightfield could be verified to exist. A hex erosion port is an **F-tier
  engineering translation** grounded on the P-tier hydrology and lattice physics above. Do not
  imply a paper.

## Coordinates and storage

**Store `odd-r` offset; compute in axial; use cube only for distance/rotation.**

```
storage    : h = Float32Array(W*H), h[r*W + q]          # unchanged from a square port
lattice    : pointy-top, odd rows shifted +s/2           # "odd-r"
s          : cellSize = nearest-neighbour spacing (m)    # THE one distance
world(q,r) : x = (q + 0.5*(r & 1)) * s ;  y = r * s * (√3/2)   # PHYSICAL kernels
domain(q,r): u = (q + 0.5*(r & 1)) / W ;  v = r / H             # AUTHORED fields — see §below
cellArea   : (√3/2) s²                                   # for A in m² (SKILL.md invariant)
axial      : q_ax = q − ((r − (r&1)) >> 1)               # shear; store offset, never pay twice
```

Doubled coordinates cost 2× memory (half the array invalid) — for sparse tile maps only. Sizing is
a stated choice (`SKILL.md` "derive the cell size and state it"): equal memory ⇒ nn-spacing 7.46%
coarser; equal spacing ⇒ 15.47% more samples (`H = round(N·2/√3)` for a square world); equal
alias-free disc bandwidth ⇒ 13.4% fewer.

**The seed-contract trap (the loud one).** Never feed raw `(q,r)` to a field function: the half-row
shear lives in the coordinate transform, **never** in the field function, and skipping it gives every
field a half-cell zig-zag — the hex instance of the `01` tile-local defect. But the corpus's
square-grid mandate to *evaluate in world metres*, which earlier revisions of this chapter carried
across unchanged, is **not** the right contract for authored fields on a lattice whose array is not
square: it crops the noise, and the measurement is the next section. Authored fields evaluate in the
**authoring domain**; physical kernels evaluate in **world metres**. Porting corollary: noise / warp /
ops / droplet nodes stay lattice-agnostic in *structure*, but each one's coordinate line gains the
odd-row half-cell term (`+0.5·(r&1)` on hex, `0` on square, so square stays byte-identical) — one
line per generator, **not zero**. Make the lattice a property of the field
(`{data, W, H, cellSize, lattice}`), not a fork of the graph; nodes partition into lattice-agnostic
(no change), stencil (swap iterator + re-derive constants), and raster-specific (D∞, separable
blur, hardware filtering — rewrite or no analogue).

## The authoring domain vs the world metric (F — production experience, no paper)

**Tier first, because this section corrects the one above it.** Everything here is measured
implementation experience from one production build (Terrain Studio, 2026-07), not a published
result. It is **F** by `00`'s table — practice with no canonical source — and it must not acquire a
citation. Oracles: `studio/_verify_hex.js` gates H4a/H4b, and `studio/_verify_hex_parity.js` for the
end-to-end numbers.

**The trap.** Storing an odd-r lattice in the same `W×H` array a square grid would use puts cell
`(q,r)` at world `((q + 0.5·(r&1))·s, r·s·√3/2)`, so the footprint is `W·s × H·s·(√3/2)` — only
0.866 as tall as the square map over the same array. It is then natural to make every generator
sample noise at the **world** point, on the reasoning that the seed contract should be "the same
noise field, sampled where the cells actually are". That reasoning is self-consistent, which is why
it is the attractive mistake rather than a careless one, and it is the wrong *product* contract:
sampling one field down an axis 0.866 as long **crops** it in `v`. Measured on a production terrain
graph, toggling square→hex under the world-point contract gave Pearson `r = 0.574` against the square
build, mean absolute difference 10.9% of range. What the user sees is a grid setting silently
re-rolling terrain they authored; what they report is that the maths is broken.

**The fix — two coordinate systems, and every operator states which one it is in.**

```
domain(q,r) : u = (q + 0.5*(r&1))/W ;  v = r/H            # AUTHORED — dimensionless, [0,1]²
world(q,r)  : x = (q + 0.5*(r&1))*s ;  y = r * s * (√3/2) # PHYSICAL — metres
```

The **authoring domain** holds everything a user authored — noise generators, placement parameters
(Position X/Y), shapes, painted strokes, warp displacement. Note `v = r/H` and **not** `r·(√3/2)/H`:
leaving the row compression out is the whole point. The odd-row half-cell term is **retained**,
because it is a sub-cell offset *within* a row rather than a metric, and dropping it prints the
row-parity zig-zag. The **world metric** holds every physical kernel — erosion, flow routing, wind,
snow, normals, AO, picking, DEM interchange — and must never be "corrected" back to the domain.
Measured after the split: `0.9999` on a single fbm node, `0.992` end to end on the full default graph,
mean difference 2.4% of range against 10.9% before. On a square lattice the two systems differ only
by the uniform factor `s`, which is why the corpus's world-space seed rule (`SKILL.md`, `01`) has
never had to distinguish them; the offset lattice is where they come apart.

**The trade, stated rather than hidden.** A unit square cannot map isotropically onto a non-square
world, so the choice is **squash or crop, and there is no third option**. Domain normalisation
squashes the generated *pattern* by 13.4% in world `y`. That is the cheaper half of the trade: a
squashed FBM is indistinguishable from one at a slightly different frequency — noise has no canonical
aspect ratio — whereas a crop is a genuinely different draw, which is exactly the complaint being
fixed. Critically the **lattice** stays perfectly isotropic under either choice — all six neighbours
remain at exactly one cell spacing — so the D6 erosion, flow and thermal kernels below keep their
correctness either way. Only the pattern's aspect is affected.

**The same defect's quieter symptom, worth recognising by shape.** Under the world-point contract a
placement parameter authored as a `[0,1]` fraction — Position Y — did not reach the last row, because
it was compared against an axis only `0.866·H` tall. Any authored quantity normalised to `[0,1]` and
then measured down the world axis behaves this way: the last 13.4% of the map becomes unreachable
from the UI. If a lattice toggle re-rolls the terrain, expect the placement sliders to be short too.

**The verification lesson: a contract change demotes the negative controls derived from the old
contract.** The existing gate proved the seed contract by comparing the real build against one with
the odd-row half-cell shift removed. Under the domain contract that comparison is a sub-pixel change
and correlation cannot resolve it — the *broken* build reads `0.999` as well, so the control had gone
vacuous and would have passed on the defect it existed to catch. The replacement controls the shift
with the **D6 Laplacian magnitude**, `|Σₖ h[nₖ] − 6h[c]|` averaged over the field, which sees the
row-parity zig-zag directly: the shift-suppressed build's magnitude over the real build's reads
`1.000×` when the shift is dead in the product (the two fields are then the same field) against
`1.313×` when it is alive, so the bound sits at `1.15` between two **measured** endpoints instead of
a guessed one — the first bound tried here was a guessed `1.5`, which the *correct* build failed.
The durable part is not about hex: **when a contract changes, re-derive its negative controls.** A
control inherited from the superseded contract can start silently passing on the defect, and a suite
that still reports green is worse than no suite.

## Kernels (all six neighbours at exactly `s` — the point of the exercise)

Odd-r neighbour table, branchless: `p = r & 1`; same row `(q±1, r)`; rows above/below
`(q+p, r±1)` and `(q+p−1, r±1)`. All six at distance `s` — the `√2` weighting bug class
(`03`/`04`/`05`/`09`) stops existing.

- **D6 steepest descent**: one divisor, no diagonal case. Still **single-receiver** — see Limits.
- **Gradient** (normals, `06`): `∇h ≈ (1/(3s)) Σₖ (h[nₖ]−h[c]) uₖ` — exact for linear fields via
  `Σ uₖuₖᵀ = 3I`; no residual 4-fold term (Horn's 3×3 has one).
- **Laplacian** (thermal/diffusion, `05`/`10`): `∇²h ≈ (2/(3s²)) Σₖ (h[nₖ]−h[c])`, and the
  **leading error term is isotropic** (the FHP result in usable form). ⚠️ The constant is
  `2/(3s²)`, **not** `1/s²`: a port that swaps the neighbour loop and keeps the old coefficient
  runs at the wrong diffusivity. Re-derive every stencil constant; `09`'s resolution-consistency
  test is the detector.
- **Talus** (`05`): `dLimit = tan(α)·s`, one value, six neighbours — the plus-shaped-cone failure
  row becomes *structurally impossible*, not merely fixed.
- **Pipes** (`04`): six pipes, one length; the 4-pipe anisotropy paragraph dissolves.
- **MFD6** (`03`): Freeman weights unchanged; **drop Quinn's contour-length weighting** — all six
  faces have identical length `s/√3`, so Freeman/Quinn collapse into one.

## Canonical triangulation — why edge spinning ceases to exist

Between rows r and r+1: even rows `[(q,r),(q+1,r),(q,r+1)]` + `[(q+1,r),(q+1,r+1),(q,r+1)]`; odd
rows `[(q,r),(q+1,r),(q+1,r+1)]` + `[(q,r),(q+1,r+1),(q,r+1)]`. Every edge is a lattice edge.

- **Unique**: all triangles equilateral (side `s`); the rhombus's short diagonal *is* the lattice
  edge (`s` vs `√3 s`), so Delaunay has nothing to decide. Height-aware edge spinning,
  shortest-diagonal heuristics and checkerboard tie-breaks cease to exist.
- **Topology is height-independent**: the index buffer is a pure function of `(W,H)` — buildable
  once, immune to height/snow/water edits, and assertable (`hash(indexBuffer)` bit-identical under
  any edit — an assertion *impossible to satisfy* on an edge-spun square mesh).
- **Creases are reframed, not solved**: no diagonal aligns with a ridge either; the error becomes
  direction-independent instead of azimuth-lucky. If crease fidelity dominates, the answer is
  resolution or feature-aligned meshing, not a lattice.
- **Mips**: the lattice contains an index-4 hex sublattice at `2s` — keep rows `r ≡ 0 (mod 2)`,
  and within a kept row keep columns `q ≡ (r/2) mod 2`. Clean 4:1 chains, but the column phase
  alternates per kept row: **hardware mip generation and box downsampling are wrong. Build mips
  yourself.**
- **GPU sampling**: upload as a plain `W×H` R32F texture, but **never hardware-bilinear** — the
  taps live in a sheared basis (systematic error + half-texel row shear). Sample barycentrically
  in the containing triangle: 3 fetches, cheaper than bilinear's 4. You lose hardware filtering,
  mips and aniso; budget for it.

## Verification (add to `09`; cone and radial-vent inputs need only hex expected-output lines)

1. **C6 vs C4 cone symmetry** — report BOTH modes on BOTH lattices; the win is the surviving mode
   changing order, not just shrinking. Floors: C4 lock √2; C6 lock 2/√3. Target `C6 ≤ 1.05`,
   `m=4` → noise floor.
2. **Thermal isotropy** — talus-front isoline: `m=4` structurally absent, `m=6 ≤ 1–2%`; repose
   angle recovered from the slope histogram with the **new** constant.
3. **Stencil ratio** — the pipe-vs-droplet anisotropy statistic should collapse most of its excess
   (droplet is the stencil-free reference); predict a large drop, **not zero**.
4. **Routing azimuth sweep** — D6 error is 60°-periodic with peak ≤30° (**worse** than D8's 22.5°
   — see Limits); the pass criterion belongs to **MFD6** (flat, small), not D6.
5. **Resample round-trip** (square→hex→square on a real DEM): gate on **slope RMS** and "the same
   rivers route", never on height RMS (reassuring and wrong).
6. **Topology invariance** — `hash(indexBuffer)` bit-identical under any height/snow/water edit.
7. **Lattice invariance of authored nodes** — same seed, square vs hex, compared at matched
   **domain** `(u,v)`, not matched world `(x,y)`: production build reads `0.9999` on one fbm node and
   `0.992` end to end. Report the world-point correlation beside it (`0.574`) and do **not** gate it —
   agreeing at world points *is* the crop. The half-cell shift needs a separate control that
   correlation cannot provide: D6 Laplacian magnitude, bound `1.15` between the measured `1.000`
   (shift dead) and `1.313` (shift alive). See §The authoring domain for why the old form of this
   check went vacuous.
8. Existing invariants re-based: `cellArea = (√3/2)s²`; mass; determinism; resolution consistency.

## Limits — what does not get better

Single-receiver parallel-line artefacts survive (D6 quantises to 6 azimuths vs D8's 8; hex removes
the *metric* inconsistency, not the discretisation — the cure is still MFD). **D∞ has no published
hex analogue** (a 6-facet version would be F-tier; say so). Noise anisotropy (Perlin creases,
diamond-square axes) is a property of the noise function itself, in whichever space it is
evaluated — untouched. Droplet erosion
gains nothing (already stencil-free) and pays barycentric sampling. Braun–Willett is
lattice-neutral but its stack/donor/fill machinery all need iterator rewrites, and it stays global
and untileable (`08`). Separable blur is lost (iterate the 7-point Laplacian, or pay O(k²));
naive FFT on offset storage is sheared (Ehrhardt 1993 or shear-correct); spectral isostasy (`02`)
is affected. The boundary zig-zags by `s/2` per row and the `(r&1)` parity term is the entire new
bug surface. A W×H array covers a non-square world (`4096 × 3547·s`) — silent aspect drift is the
likely first bug, and its authored-field half is §The authoring domain: the *footprint* stays
truthfully rectangular; what is deliberately squashed is the generated pattern. And the ecosystem
— PNG/R16, SRTM, GeoTIFF, engine importers, RichDEM, pysheds,
this corpus's own reference-impl cross-checks — is square end to end (Landlab the verified
exception), so export always ends in one hex→square resample at exactly the point `08` says
"export last, once": bake normals/AO on the hex field and resample the *maps*, not the other way
around.

**Production measurement (Terrain Studio, 2026-07) — a correction to the thermal expectation.**
On a repose-relaxed world-space cone, the D6 thermal kernel's talus ring is magnitude-isotropic
to 0.3% (max/min 1.003 across azimuth; the distance-corrected D8 square kernel reads 1.005 — both
excellent). But facet-*direction* concentration measured the OTHER way from the naive reading of
this chapter: hex 1.41 vs corrected-D8 1.17 — and the D4 *defect* kernel itself reads 1.23
(36-bin direction histogram, each lattice measured with its own one-ring gradient estimator,
which quantizes directions toward its tap families — 6 at 60° vs 8 at 45°; that estimator
coupling is why facet-direction is reported, never gated, and the gated quantity is ring
magnitude-isotropy: 1.003). The C4-vs-C6 lock comparison in this chapter describes the **uncorrected /
D4 defect class**; against a *well-implemented* distance-corrected D8 thermal, D6's win is
**exactness** — one neighbour distance, one threshold, no √2 correction to forget — not facet
diversity, and a well-corrected D8 actually offers more facet families. Claiming otherwise
overstates. (Oracle: `studio/_verify_hex.js`, gate H3 + its REPORT line.)

Cross-references: `08` (spherical hex-DGGS — the same idea's globe case; do not re-explain),
`09` grid-anisotropy family (this chapter is its fourth cure), `03`/`04`/`05` (stencil rows that
become moot), `07` (Poisson disk is lattice-free; hex is the densest circle packing blue noise
deliberately never reaches), `13` (Tarnita's hexagonal termite spacing is an emergent pattern,
NOT a sampling lattice — do not conflate).
