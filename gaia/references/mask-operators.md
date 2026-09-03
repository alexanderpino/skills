---
type: Technique
title: Mask operators — distance fields and component filtering
description: "The two utilities the rest of this corpus assumes and never provides: an exact Euclidean distance transform, including distance from a spline, and an area-thresholded component filter that despeckles a mask without eroding it."
tags: [generation, masks, distance-field, morphology, authoring-time]
status: draft
generated: { by: process:claude-code, at: 2026-09-03T00:00:00Z }
sources:
  - { id: felzenszwalb2012, tier: P, locator: "Algorithm 1 p. 420, the O(n) 1D lower-envelope-of-parabolas transform, with the intersection s = ((f(r)+r²) − (f(q)+q²)) / (2r − 2q) on p. 419; §2.2 eqs. (2.2)–(2.3) and Theorem 2.2 for the separable extension to d dimensions in O(dN); §1 p. 416 for the definition D_f(p) = min over q of (d(p,q) + f(q)), and the note that earlier exact linear-time methods 'are quite involved and are not widely used in practice'; §3 Algorithm 2 for the two-pass L1 transform attributed to Rosenfeld & Pfaltz" }
  - { id: meijster2000, tier: P, locator: "§2 The First Phase pp. 332–333, the per-column reduction to G(x,y); §3 The Second Phase pp. 333–336, the lower envelope of the per-column curves F_i and the single algorithm parameterised by f for EDT, MDT and CDT; the introduction p. 331 for the statement that mask-sweep approximations are linear in pixels but 'hard to parallelize' because results propagate sequentially" }
  - { id: hajdu2012, tier: P, locator: "p. 3 — the printed 3×3, 5×5 and 7×7 Borgefors masks with their scale factors 3, 5 and 12, and the sentence giving their maximum relative errors as 0.0572, 0.0198 and 0.0138; the definition of the maximum relative error E as the limsup of |W(v)/|v| − 1| as |v| grows; the optimal-for-size values E1C ≈ 0.0396, E2C ≈ 0.0136, E3C ≈ 0.0065" }
  - { id: rongtan2006, tier: P, locator: "§3 — the log n rounds with step lengths n/2, n/4, …, 1, and the JFA+1 and JFA+2 variants that append rounds of step length 1; Figure 4 and §3 for the rejection of the doubling variant; §5 for errors occurring at and around Voronoi vertices; §6 Efficiency and Figure 9 for the frame rate being flat in seed count" }
  - { id: fiorio1996, tier: P, locator: "§1 Introduction and overview p. 165–166 — general union-find is O(α(n,m)·m) by Tarjan's algorithm, the bound is sharp for pointer machines, and whether a random-access machine can do better 'is not known until now'; the paper's own result that the restricted union sequence of a raster scan is linear" }
  - { id: wu2009, tier: P, locator: "§1 and Figure 1(b) for the four-neighbour forward scan mask; §1.1 item 2 for the three phases of a two-pass labeller; §4.2 Theorem 3 — 'the total time required by a two-pass labeling algorithm using any union-find with path compression is O(p)', p the pixel count; §4.1 Theorem 1 for the decision tree and the factor-of-two reduction in neighbours accessed" }
  - { id: salembier2009, tier: P, locator: "§Size filtering — the area opening removes components below a pixel-count threshold and 'is equal to the supremum of all possible openings by a connected structuring element involving T_A pixels'; the abstract for connected operators that 'cannot create new contours nor modify their position'; Figs. 17–18 for the union-find implementation; Fig. 21(b) vs 21(c) for a disk opening against an area filter on the same image" }
---
# Mask operators — distance fields and component filtering

Two operators that half this corpus already assumes. `tectonic-uplift.md` tells you to author
uplift as "a distance field from a spline" and never says how to compute one.
`terrain-analysis-masks.md` warns that a curvature mask "is speckle" on a quantised field and
stops there. This document is those two holes.

**Boundary.** `terrain-analysis-masks.md` owns how a mask is *derived* from height — slope,
curvature, occlusion, wetness — and the selector stack that turns masks into material weights.
`layering-filters-and-masks.md` owns how a mask is *applied* to a filter. This document owns the
two operators that take a mask and return a better mask.

## Use this

**For a distance field: the separable exact transform of [felzenszwalb2012], one pass down the
columns and one across the rows, on the squared distance, square-rooting only at the end.** It is
about forty lines, it is exact, it is O(N) in the number of cells at any radius, and it needs no
parameter. For a distance *from a spline*, rasterise the curve into the seed mask first and
transform that; for a *signed* field, run it twice and subtract.

Everything else on this axis is a compromise you should be able to name:

- **Chamfer masks** (the 3-4 and 5-7-11 sweeps) — same asymptotic cost, one less array, and a
  **maximum relative error of 5.7% and 2.0% respectively** [hajdu2012], reproduced below. Use
  only where the field feeds something with a soft threshold and never a measurement.
- **Jump flooding** [rongtan2006] — the GPU answer, `log n` passes over the whole field, and
  approximate. Cross over when the field must be rebuilt per frame from moving seeds.
- **Brute force over seed pixels** — correct, trivial, and O(N · seeds); fine below a few
  thousand seed pixels and catastrophic for a rasterised coastline.
- **A blurred mask as a fake distance field** — the commonest substitute and the worst: a
  Gaussian's response falls off exponentially and its reach is fixed by the kernel, so the value
  is not a distance, does not scale with a radius you can author, and is quantisation noise a
  short way out.

**For despeckling a thresholded mask: label the components and delete the ones below an area
threshold** — a two-pass scan with union-find [wu2009], which is O(pixels) [fiorio1996]. **Do not
use a morphological opening for this.** An opening shrinks every surviving feature; a component
filter is size-selective and shape-preserving, and the section below measures the difference at
54% versus 0% of a real feature destroyed.

## The exact transform: a lower envelope of parabolas

The trick that makes it separable is to generalise the transform from a binary mask to an
arbitrary sampled function [felzenszwalb2012]:

```
D_f(p) = min_q [ d(p,q) + f(q) ]
```

With `f(q) = 0` on seeds and `+∞` elsewhere this is the ordinary distance transform. But after
transforming one column, the intermediate result is **no longer an indicator function** — it is a
real-valued cost — and that is exactly why an algorithm that only handles binary input cannot be
run twice. The generalisation is what buys the separability, not a side benefit of it.

Under *squared* Euclidean distance, the one-dimensional problem is the lower envelope of `n`
parabolas of identical shape, rooted at `(q, f(q))`. Two of them cross at exactly one place:

```
s = ((f(r) + r²) − (f(q) + q²)) / (2r − 2q)
```

Because the parabolas arrive already sorted by vertex position, the envelope is built by a stack
that pushes each parabola and pops any it has undercut — every parabola is pushed once and popped
at most once, so the pass is O(n), not O(n log n) [felzenszwalb2012], Algorithm 1. A second walk
samples the envelope at each grid position. Two dimensions is that pass down every column, then
that pass across every row of the result; `d` dimensions is `d` passes, O(dN) total
[felzenszwalb2012], Theorem 2.2.

Three implementation notes that cost an afternoon each if missed:

- **Stay in squared distance until the very end.** The recurrence is exact in integers for an
  integer grid; the square root is one pass at the end, and taking it early destroys the
  separability outright, because the sum of two Euclidean distances is not the distance.
- **`∞` must be big enough and finite.** Use a large float, not `inf` — the intersection formula
  divides differences of `f` values, and `inf − inf` is `NaN`. [meijster2000] makes the same point
  from the other side: `m + n` suffices as the "infinity" of an `m × n` grid.
- **Order does not matter.** Columns-then-rows and rows-then-columns give the same field
  [felzenszwalb2012] §2.2, which is a free unit test.

[meijster2000] reaches the same separable structure from the other direction, and is the better
read if you want three metrics from one code path: its first phase reduces each column to the
distance to the nearest seed *within that column* (§2), and its second phase combines columns via
the same lower envelope, with the metric appearing only as the choice of a single function `f` —
squared difference for Euclidean, absolute difference for Manhattan, max for chessboard (§3).

**Verified here.** Algorithm 1 was transcribed line for line into
`scratchpad/w6/edt_error.py` and compared against brute-force minimisation over all seed
pixels: on a 64×64 field with 40 random seeds and on a 129×129 field with a single centre seed,
the two agree **exactly** — maximum absolute difference 0.000e+00, not merely small. That is the
check to run before trusting any distance field, and it takes ten lines.

## Chamfer and jump flooding, and where each one is right

A chamfer transform propagates integer step costs through a forward raster sweep and a backward
one: the 3×3 mask charges 3 for an orthogonal step and 4 for a diagonal, then divides by 3; the
5×5 mask charges 5, 7 and 11 and divides by 5. The masks are Borgefors', and her 1986 paper could
not be obtained here — it is named rather than cited, and the constants below are transcribed from
[hajdu2012], which prints all three classical masks in order to compute their errors.

Those errors are *not* small, and they are the reason to reach for the exact transform by default:

| Mask | Max relative error, hajdu2012 | Measured here, single centre seed | Measured on a rasterised polyline |
|---|---|---|---|
| 3-4 (3×3) | 0.0572 | **0.0572** | max 0.0572, rms 0.0358 |
| 5-7-11 (5×5) | 0.0198 | **0.0198** | max 0.0198, rms 0.0104 |
| Best possible at 3×3 | 0.0396 | — | — |
| Best possible at 5×5 | 0.0136 | — | — |

The middle column reproduces the paper's published constants to four decimals from an independent
implementation, which validates the transcription and the paper simultaneously.

⚠️ **The error is bipolar, not systematically positive, and the published constant is the
*under*-estimate.** An earlier draft of this document claimed chamfer distances over-estimate
"everywhere", and its own next sentence disproved it. Measured on a 201² field, single centre seed,
cells beyond `r = 20`:

| Mask | most positive | most negative | cells reading short | worst underestimate at |
|---|---|---|---|---|
| 3-4 | +5.41% | **−5.72%** | 25.0% | 45° |
| 5-7-11 | +1.98% | −1.61% | **58.1%** | 63.4° |

For 5-7-11 the *majority* of cells read short. And `E = 0.0572`, the constant the table above
quotes for 3-4, is the error at 45°, where the mask returns `4/3 = 1.333` per step against
`√2 = 1.414` — **short by 5.72%**, not long. The `+0.45%` that motivated "systematically positive"
is a *mean* over one polyline field, and the sign of a mean was attached to a magnitude that is an
absolute value.

So a chamfer field thresholded at a fixed distance selects a **larger** region along the diagonals
and a **smaller** one near 18°, which is the anisotropy stated as a shape rather than as a bias: it
is *anisotropic*, and a radial ramp built on it is visibly an octagon.

**Jump flooding** [rongtan2006] is the GPU form and a genuinely different animal: each cell stores
the coordinates of the best seed it has heard about, and `log n` rounds with step lengths
`n/2, n/4, …, 1` pass that coordinate outward. Because it propagates a *seed position* rather than
a distance, the distance it returns is always the true distance to *some* seed — the error is never
a wrong arithmetic, only a missed neighbour. Measured on the polyline mask at 256², 8 rounds:

| Method | % of cells with the wrong nearest seed | Max relative error | RMS relative error |
|---|---|---|---|
| JFA | 0.0137% | 0.0068 | 0.00003 |
| JFA+1 | 0.0076% | 0.00024 | ~0 |
| JFA with *doubling* step | 25.75% | 0.0534 | 0.0053 |

On 1000 random seeds in a 512² grid — the configuration [rongtan2006] §6 measured — plain JFA got
4 cells of 262144 wrong and JFA+1 got none. The last row is the paper's own warning made concrete:
the step schedule must *halve*, and the intuitive small-to-large order fails catastrophically
(§3, Figure 4).

**The crossover.**

| Situation | Do | Because |
|---|---|---|
| Authoring-time bake, any seed count | Exact separable [felzenszwalb2012] | O(N), exact, no parameter; the CPU is not the bottleneck in a bake |
| Seeds move every frame, GPU already resident | JFA+1 [rongtan2006] | `log n` full-screen passes, error at the fourth decimal, cost flat in seed count |
| Field feeds a hard threshold or a measurement | Exact, always | 5.7% of a 2 km radius is 114 m of misplaced mountain |
| Field feeds a soft mask you will noise-break anyway | 5-7-11 chamfer is defensible | 2.0% is under the noise you are about to add |
| Fewer than ~1000 seed pixels, one-off | Brute force | It is four lines and cannot be wrong |
| You reached for a Gaussian blur | Stop | Blur saturates; it is not a distance and does not scale with radius |

⚠️ **JFA's `log n` passes are over the whole field.** At 4k that is 12 full-screen passes with nine
taps each — comfortably real-time, and comfortably more total work than the exact CPU transform
does. JFA is the right answer because it is *on the GPU where the data already is*, not because it
is cheaper in operations.

## Signed distance, and distance from a spline

`tectonic-uplift.md` asks for "a distance field from a spline". The transform above takes a raster
mask, so the spline has to become one. There is **no canonical source for this pipeline; standard
practice is** to rasterise and then transform, and the three steps below are the practice, not a
published result — only the transform in the middle is:

1. **Rasterise the curve into the seed mask.** Sample the spline at a spacing of at most half a
   cell — undersample and the field acquires a scalloped, beads-on-a-string profile that shows up
   as periodic bumps along the ridge you were building. Conservative rasterisation of the segments
   is the robust form.
2. **Transform, then remap.** The field is in cells; multiply by the cell size to get world units
   before any threshold, exactly as `terrain-analysis-masks.md` demands of every threshold.
3. **Profile the distance, do not threshold it.** `U = U_max · exp(−d²/2σ²)` or a smoothstep over
   a band gives a range with flanks; `d < w` gives a plateau with a cliff edge.

**Sub-cell accuracy, if you need it.** The raster transform quantises the source to cell centres,
so the field is accurate to about half a cell near the curve — fine at 2 km, wrong if the spline is
a river centreline at 1 m/px. Two ways out: supersample the seed mask by 2–4× and downsample the
result, or seed the transform with the *exact* distance from each near-curve cell to the analytic
segment and let the transform propagate from there. The second is the generalisation
[felzenszwalb2012] already provides — a non-binary `f` is exactly what the algorithm takes.

**Signed fields.** Run the transform on the mask and again on its complement, and subtract. ⚠️ The
order is the whole content of this line, and an earlier draft had it backwards:

```
# edt(S) is this document's D_f with f = 0 on S: DISTANCE TO THE NEAREST CELL OF S.
# So edt(inside) is small inside the mask -- which is why it is the term that gets negated.
sdf = edt(inside) − edt(outside)      # positive outside, negative inside
```

Checked on a 7×7 square in a 21² field: as written this gives **−4.00** at the centre and **+9.90**
at a corner. Reversing the two terms gives +4.00 and −9.90 — the same field, negated, with a
comment that reads exactly as plausible. This is the failure the table below calls "a coin flip",
and nothing downstream will tell you: an inverted SDF still looks like a distance field, still has
the right gradient magnitude, and still produces a smooth falloff — it just selects the outside.
Assert the sign at one known interior cell before you use it.
Two cautions. The sign convention is a coin flip and both are in circulation — write it into the
node name, because the failure is a silently inverted mask. And the two transforms are each exact,
but the *combined* field has a one-cell plateau of zeros at the boundary, because a boundary cell
is at distance 0 from itself under both. If the zero crossing matters — it does for anything that
marches the field — offset by half a cell or reconstruct the boundary sub-cell.

**What a distance field gets you beyond a mask.** A falloff whose width is in metres and does not
change with the terrain's height range; a coastline shelf profile; erosion strength that fades from
a fault; and — the one that pays for the operator on its own — **a mask boundary you can move**.
`smoothstep(a, b, sdf)` dilates or erodes the region by an arbitrary real distance in one
instruction, where morphology would need a structuring element per radius.

## Component filtering: size-selective, shape-preserving

A thresholded curvature or slope mask arrives with hundreds of one- and two-cell fragments around
its real features. The fix is to *label* the connected components and delete the small ones.

**The algorithm** [wu2009] §1.1: one raster pass assigns each foreground cell a provisional label,
looking only at the already-scanned neighbours (the four cells above and to the left, §1 Fig. 1b),
and unions the labels wherever two provisional labels meet; an analysis pass resolves each
provisional label to its root; a second raster pass writes the final labels. Union-find with path
compression is the merge structure. Pick 8-connectivity for the foreground unless you have a
reason — 4-connected foreground splits diagonal chains into separate specks.

**The complexity, stated honestly.** General union-find is **O(α(n,m)·m)**, not O(m), and
[fiorio1996] §1 is careful that this bound is *sharp* for pointer machines and that the
random-access case is open. `α` is under 5 for any grid that fits in memory, so the practical claim
is safe — but the reason it is safe here is stronger than "α is small": the union sequence produced
by a raster scan is *restricted*, and [wu2009] §4.2 Theorem 3 proves that a two-pass labeller using
any union-find with path compression runs in **O(p)** for `p` pixels, generalising fiorio1996's
result. So the operator is linear in the field, provably, and you may budget it as one more pass.

Measured on a 256² mask from a thresholded noise field (39.18% coverage, 25676 set cells,
`scratchpad/w6/component_filter.py`): 927 components, of which **921 are smaller than 25 cells —
99.4% of the components and 6.46% of the set cells**. That ratio is the whole case for the
operator: nearly every object in the mask is speckle, and nearly none of the mask is. The
union-find did 2622 pointer hops for 25676 object cells — **0.102 hops per cell**, which is what
"effectively constant" looks like when you count it.

**Why this is not a morphological opening.** An opening erodes then dilates by a structuring
element: it removes anything the element does not fit inside, and it *also* rounds off every
corner, severs every neck thinner than the element, and shrinks features that survive. Same mask,
same target of removing everything under 25 cells:

| Operator | Cells kept | Components left | Largest component | % of the largest component destroyed |
|---|---|---|---|---|
| input | 25676 | 927 | 19887 | — |
| **area filter, min 25 cells** | 24017 | **6** | **19887** | **0.00%** |
| opening, disk r=1 (5 cells) | 18580 | 104 | 4615 | 22.87% |
| opening, disk r=2 (13 cells) | 14346 | 26 | 3721 | 41.76% |
| opening, disk r=3 (29 cells) | 11526 | 14 | 3266 | 54.11% |

The opening needs **r=3** before every sub-25-cell component is gone, and by then it has destroyed
**54.11%** of the largest real feature and shattered what remains into 14 pieces — the disk severs
every neck narrower than 6 cells. The area filter reaches zero small components while touching
**0.00%** of the feature. On a synthetic pair — one 40-cell bar one cell wide, one compact 16-cell
blob — the area filter keeps 40/40 of the bar and 0/16 of the blob, which is the requested
behaviour; an opening with r=1 keeps 0/40 of the bar and 12/16 of the blob, which is the exact
opposite, because an opening selects by *thickness* and the filter selects by *size*.

This is not folklore: [salembier2009] gives the operator its formal name, the **area opening**, and
proves the identity that makes the shape-independence exact — the area opening equals the
*supremum of all possible openings by a connected structuring element of `T_A` cells*. An opening
by one disk imposes that disk's shape; the area opening imposes no shape because it takes the
union over every shape of that size. The same review frames both as **connected operators**, which
"cannot create new contours nor modify their position" — that is the property being bought, stated
as a theorem rather than as a preference. Fig. 21 makes the picture: stars removed by a disk
opening against the same stars removed by an area filter, on the same galaxy.

**Two variants worth having.** Filter the *background* the same way to fill pinholes — components
of the complement below a threshold, which is an area *closing* and is not the same as a
morphological closing for the same reason. And keep the per-component statistics the labelling
already computed (area, bounding box, mean of some other field): a mask that can say "keep the
twelve largest lakes" is a different authoring tool from one that can only say "keep everything
over 400 cells".

⚠️ **Threshold in world area, not cells.** 25 cells is 25 m² at 1 m/px and 1600 m² at 8 m/px. Store
the threshold in m² and divide by the cell area, or every LOD of the same graph despeckles
differently — the same defect `terrain-analysis-masks.md` documents for slope thresholds.

## How this fails, and what it looks like

| Symptom | Mechanism | Fix |
|---|---|---|
| A "distance field" that stops varying a few cells out | A Gaussian blur used as a distance field | Blur saturates; use a real transform |
| Distance ramp is a visible octagon | Chamfer anisotropy — 4/3 per diagonal step against √2 | Exact transform, or 5-7-11 if the error budget allows |
| A thresholded distance region is an octagon, not a circle | Chamfer error is bipolar and direction-dependent: 3-4 runs +5.41% at 18° and **−5.72% at 45°**, so the region bulges on the diagonals and pulls in near 18° | 5-7-11 if approximate is fine (+1.98%/−1.61%); exact separable if the threshold is a specification [felzenszwalb2012] |
| Field is right near seeds, wrong far away | Squared distance square-rooted between the two passes | Stay in squared distance until the end |
| NaNs in the second pass | `inf` used as the empty value; `inf − inf` in the intersection | A large finite float; `m + n` suffices |
| Beads-on-a-string bumps along a spline-driven ridge | Curve rasterised at more than half-cell spacing | Sample at ≤ 0.5 cell, or rasterise conservatively |
| Ridge from a spline has a flat top and cliff sides | Distance thresholded rather than profiled | `exp(−d²/2σ²)` or a smoothstep band |
| Distance mask breaks at a different LOD | Threshold left in cells | Multiply by cell size; threshold in metres |
| Signed field inverted; interior selected instead of exterior | Sign convention is a coin flip and both ship | Write the convention into the node name |
| Marching a signed field snags at the boundary | One-cell plateau of zeros where both transforms give 0 | Offset by half a cell, or reconstruct sub-cell |
| GPU distance field has a few wrong cells near cell corners | JFA misses a seed at a Voronoi vertex [rongtan2006] | JFA+1 — one extra round of step length 1 |
| GPU distance field is wrong nearly everywhere | Step length doubling instead of halving | Halve: `n/2, n/4, …, 1` [rongtan2006] Fig. 4 |
| Mask is 900 specks and 6 real features | Threshold on a second-derivative field | Area-filter the components, not an opening |
| Despeckling ate the features too | Morphological opening used as a despeckler | 54% of the largest feature lost at r=3, measured; use the area filter |
| Despeckling severed a thin ridge into fragments | Opening's structuring element wider than the neck | An area filter has no structuring element |
| A one-cell-wide 40-cell filament vanished, a 16-cell blob survived | Opening selects by thickness, not size | Area filter: it is size-selective by construction |
| Despeckling threshold behaves differently per LOD | Threshold in cells, not m² | Store m²; divide by cell area at use |
| Labelling splits diagonal chains into separate specks | 4-connectivity on the foreground | 8-connectivity for foreground, 4 for background |
