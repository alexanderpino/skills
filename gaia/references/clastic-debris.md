---
type: Technique
title: Clastic debris — boulders, cobbles and pebbles as scattered objects
description: "Scattering rock onto a finished heightfield: the size classes are powers of two, Poisson-disk sampling has one parameter and it is a separation rather than a density, so the classes are placed largest-first with rejection against everything already down — and the smallest class never becomes an instance at all."
tags: [generation, placement, scattering, clasts, poisson-disk, blue-noise, instancing, authoring-time]
status: draft
generated: { by: process:claude-code, at: 2026-09-10T00:00:00Z }
sources:
  - { id: bridson2007b, tier: F, locator: "§2 The Algorithm — the three inputs, 'the extent of the sample domain in R^n, the minimum distance r between samples, and a constant k as the limit of samples to choose before rejection in the algorithm (typically k=30)'; step 0's background grid, 'We pick the cell size to be bounded by r/sqrt(n), so that each grid cell will contain at most one sample', stored as 'a simple n-dimensional array of integers: the default -1 indicates no sample'; step 2's candidate draw, 'up to k points chosen uniformly from the spherical annulus between radius r and 2r around x_i'. §3 Analysis — 'Step 2 is executed exactly 2N-1 times to produce N samples' and 'each iteration of step 2 takes O(k) time, and since k is held constant (typically quite small) the algorithm is linear'. Read in full in the author's own PDF, which carries no article number, no DOI and no page numbers, so no page is cited. Graded F, not P: it is a two-page SIGGRAPH Sketch, not a papers-track publication, and the tier table's criterion is peer review alone. All four of its claims are verified here by measurement, not taken on the venue's authority" }
  - { id: wentworth1922, tier: P, locator: "NOT OPENED -- the grade scale this document names its classes against. journals.uchicago.edu returned HTTP 403 and no other copy was reached, so nothing is quoted from it and no reading is claimed. The class edges printed here rest on arithmetic instead — the scale is geometric with ratio 2 and phi = -log2(d/mm), so integer phi puts every edge on a power of two" }
  - { id: clast_scatter_practice, tier: F, locator: "no artefact: placing size classes largest-first with each pass rejecting against everything already down, and the packed per-instance transform an engine carries for a scattered rock. Standard practice with no canonical paper; every figure attached to it here is measured in this skill rather than cited" }
---
# Clastic debris — boulders, cobbles and pebbles as scattered objects

**Tier: authoring-time; the runtime consumes the baked instance list.** The heightfield is
finished before this document starts. What is left is where the loose rock goes — and the
decisive fact is not aesthetic. A pebble bed is **133 million instances per square kilometre**,
3.20 GB of transforms, and no amount of culling makes that a list you ship. The boulder class is
0.67 per square metre and 16.1 MB per square kilometre, which is nothing. The whole engineering
content of scattering rock is knowing where between those two numbers the instance path ends.

## Use this

**Name the classes on the Wentworth grade scale, place them largest-first with a separate
Poisson-disk pass per class, reject each candidate against everything already placed, and stop
instancing below the class where the count stops being affordable.**

```
# Wentworth grades: phi = -log2(d/mm) at integer phi, so every edge is a power of two.
# The top class is open above and the scale gives it no d_max: you AUTHOR one, and every
# figure on this page uses 1024 mm. Without it r_cls below is undefined.
classes  boulder  d 256..1024 mm      # d_max AUTHORED, not from the scale
         cobble   d  64..256 mm
         pebble   d   4..64 mm        # <- the instance path ends at or above here;
#        granule  d   2..4 mm            granule is a MATERIAL, never a loop iteration

for cls in classes, LARGEST FIRST:          # the order is the algorithm
    if instances_per_m2(cls) > budget: BREAK # the stop rule, and it binds before granule:
                                            # granule at r = 4 mm is ~930 GB/km2 of transforms
    r_cls = d_max(cls)                      # = 2 * a_max: a class cannot overlap itself
    for p in poisson_disk(domain, r_cls, k=30):     # [bridson2007b] §2
        a = radius drawn from the class' size law
        if clear(p, a): place(p, a, cls)    # clear() tests d_ij >= a_i + a_j against
                                            # every clast already down, not just this class
                                            # -- one grid PER CLASS, or this costs 42x more
```

Four numbers, all measured below on a 10 m × 10 m patch. The largest-first pass places **13,338
clasts with 0 interpenetrating pairs** and covers 17.60% of the ground; a single Poisson pass at
the pebble spacing places 15,153 and leaves **31 interpenetrating pairs, the worst of them buried
63% of the way into its neighbour**. Placement costs **214 µs per clast** in CPython — an
algorithmic figure, not a shipping one, and read as such below. And a per-class count planned off
independent passes overshoots: **multiply it by 0.828**, because rejection against the earlier
classes takes 17.2% of the candidates and is not a rounding error.

**What it beats.** *One Poisson pass sized for the largest clast* — correct, and it spends the
whole domain: 67 clasts on the patch and **0.01% of the ground covered**, because a separation
that keeps two boulders apart keeps two pebbles a metre apart as well. *One pass sized for the
smallest* — the count is right and the geometry is not, at the rate above. *A jittered grid* —
cheaper than either and it has a pitch, which a scatter of rock must not have.

**What this does not cover.** Vegetation, which shares the sampler and nothing else: a tree's
constraint is a canopy radius and a species mask, not an interpenetration test against a rock.
That is `coverage.md`'s `procedural-placement` row and it is still unwritten. Nor does this
document generate the clasts' *shapes*, or place them by simulating rockfall — both are
mechanisms this skill has no source for, and neither is needed to put rock on the ground.

## The classes are powers of two, and that is the whole point

Clast sizes are named on the Wentworth grade scale [wentworth1922], and the scale is geometric
with ratio 2. Krumbein's φ = −log₂(d/mm) turns it into arithmetic: **at integer φ every class edge
lands on a power of two**.

| φ | d | edge |
|---|---|---|
| −8 | 256 mm | boulder / cobble |
| −6 | 64 mm | cobble / pebble |
| −2 | 4 mm | pebble / granule |
| −1 | 2 mm | granule / sand |

So **boulder > 256 mm, cobble 64–256 mm, pebble 4–64 mm, granule 2–4 mm**, and a φ value converts
to millimetres exactly. That exactness is not pedantry — it is the only reason the scale is worth
using in a tool. A size law written in φ is a uniform draw over an interval; the same law written
in millimetres is a power law with a fitted exponent. Bin edges on powers of two also mean an
implementation can select a class with a shift.

⚠️ **The artefact was not obtained.** `journals.uchicago.edu` returned HTTP 403 and no
author-side copy was reached, so the entry carries `[not-opened]` and nothing above is quoted
from Wentworth. The table is the φ arithmetic, which anyone can redo in a line.

⚠️ **And the nearest openable secondary is wrong.** A table captioned "adapted from the Wentworth
scale" prints boulders as **"250–100"** — the range reversed, and 250 where the scale says 256 —
cobbles "65–250", pebbles "4–65", and coarse silt "0.031–0.625", the last off by a factor of ten.
Rounding 64 to 65 and 256 to 250 destroys the one property that makes the scale usable. If your
class edges are not powers of two, you copied them from something like that.

## Bridson in one page, and the parameter it does not have

[bridson2007b] replaces dart-throwing with an O(N) algorithm, and it is short enough to state
completely. §2 gives it three inputs: the domain extent, **the minimum distance `r` between
samples**, and a rejection limit `k`, "typically k=30".

- **Step 0.** A background grid with cell size "bounded by `r/sqrt(n)`, so that each grid cell
  will contain at most one sample". The grid is then "a simple n-dimensional array of integers",
  `-1` for empty — so the neighbour test is a fixed 5×5 scan of integers, not a spatial query.
- **Step 1.** One uniform seed sample, inserted into the grid and into an *active list*.
- **Step 2.** While the active list is non-empty, pick a random active index `i` and generate up
  to `k` candidates "uniformly from the spherical annulus between radius `r` and `2r` around
  `x_i`". Emit the first candidate at least `r` from every existing sample; if `k` attempts all
  fail, remove `i` from the active list.

§3 prices it exactly: step 2 "is executed exactly 2N−1 times to produce N samples", each
iteration is O(k), "and since k is held constant … the algorithm is linear".

**All four claims reproduce.** Five runs, seed 7, `k = 30`, domains from 100² to 400²:

| domain | `r` | N | step-2 iterations | 2N−1 | max samples per cell | min separation / `r` |
|---|---|---|---|---|---|---|
| 100×100 | 4.0 | 404 | 807 | 807 | 1 | 1.000328 |
| 100×100 | 2.0 | 1,564 | 3,127 | 3,127 | 1 | 1.000286 |
| 200×200 | 2.0 | 6,203 | 12,405 | 12,405 | 1 | 1.000008 |
| 400×400 | 2.0 | 24,714 | 49,427 | 49,427 | 1 | 1.000006 |
| 100×100 | 1.0 | 6,203 | 12,405 | 12,405 | 1 | 1.000008 |

The iteration count is not approximately `2N−1`; it is `2N−1`, in every run. Cost held between
**107 and 134 µs per sample** across a 61× range in N — linear, with the spread being CPython's
dictionary and list overhead rather than the algorithm. The last two rows are the same run:
**N depends only on `L/r`**, so `r` is a scale, and a scatter authored at one cell size transfers
to another by scaling `r` alone. (`resolution-independence.md` is the general statement of that
property; here it falls out of the sampler for free.)

### Two details that are easy to get wrong

**The annulus is an annulus.** "Uniformly from the spherical annulus between `r` and `2r`" means
uniform *on the annulus*, whose area element is `ρ dρ`, so `ρ = sqrt(U(r², 4r²))`. Drawing
`ρ = U(r, 2r)` instead is the common shortcut and it is not the same distribution: measured over
400,000 draws the correct mean radius is **1.5559 r** against the exact 14/9 = 1.5556, and the
shortcut gives **1.5000 r** — it runs **3.6% low**, pulling every candidate inward and raising
the rejection rate for no benefit.

**The achieved density is about half the packing bound.** A Poisson-disk set is not a packing.
Against the hexagonal bound `2A/(√3 r²)` the sampler achieved 60.9%, 54.7% and 53.8% at
`r` = 1.024, 0.256 and 0.064 on the patch below. **A clast count planned off the packing bound
comes out 39–46% low.** Size `r` from the measured ~0.54 factor, or place a target count by
bisecting on `r` — never from the bound.

## One `r` cannot hold two classes

Two clasts of radii `a_i` and `a_j` interpenetrate when `d_ij < a_i + a_j`. Bridson's `r` is a
**single minimum separation**, so it expresses that constraint for exactly one pair of radii. A
clast field spans 4 mm to 1024 mm — `a_i + a_j` varies over a factor of 256 — and one number
cannot bound it. Measured on a 10 m × 10 m patch, seed 11, sizes drawn from a truncated power law
`N(>d) ∝ d^−2.5` over the whole range:

| construction | `r` | clasts | interpenetrating pairs | ground covered |
|---|---|---|---|---|
| one pass, sized for the largest | 1.024 m | 67 | 0 | **0.01%** |
| one pass, sized mid-range | 0.256 m | 964 | 0 | — |
| one pass, sized mid-range | 0.128 m | 3,785 | 0 | — |
| one pass, sized for the smallest | 0.064 m | 15,153 | **31** (0.2 per 100) | — |
| **largest-first, per class** | per class | **13,338** | **0** | **17.60%** |

Both single-pass failures are the same failure seen from opposite ends. Sized for the largest,
every constraint is satisfied and the patch is empty — 67 objects, almost all of them pebbles
because the size law is pebble-dominated, each holding a metre of ground it does not need.
Sized for the smallest, the count is right and the geometry is wrong: 31 pairs interpenetrate and
**the worst is buried 63% of the way into its neighbour**, which is not a subtle artefact.

Note what the 0.2-per-100 rate does *not* mean. It is low because the size law is
pebble-dominated, so large-large encounters are rare; flatten the exponent and the rate climbs,
because the *condition* — `a_i + a_j > r` — is met by any two clasts averaging more than `r/2` in
radius. The rate is a property of your size law, not of the sampler.

### Largest-first, and what each pass costs the next

The fix is not a cleverer sampler. It is an ordering: run one Poisson pass per class at that
class' own `r = d_max` — which is `2·a_max`, so a class cannot overlap **itself** by
construction — and test each candidate against every clast already placed, using that pair's own
`a_i + a_j`. Largest first, because a boulder rejected by a pebble is a boulder lost, and the
table below has **225 pebble candidates for every boulder candidate** (15,075 against 67) — so
losing pebbles is cheap and losing boulders is not.

| class | `r` | candidates | kept | survive the earlier classes |
|---|---|---|---|---|
| boulder | 1.024 m | 67 | 67 | 100.0% |
| cobble | 0.256 m | 961 | 840 | 87.4% |
| pebble | 0.064 m | 15,075 | 12,431 | 82.5% |
| **total** | | **16,103** | **13,338** | **82.8%** |

Zero interpenetrating pairs over 13,338 clasts, and the cross-class rejection is **17.2%** of the
candidates. So a budget planned from independent per-class passes — the natural thing to do, since
each pass is independent until it is not — overshoots, and the safe form of that is a
multiplier: **plan × 0.828**. Stated as a percentage it is ambiguous, and the ambiguity is not
academic — 16,103 candidates exceed the 13,338 achieved by 20.7% *of the achieved count* while
being 17.2% *of the plan*. Plan from the kept counts and the question does not arise.

### The grid the cross-class test runs on is not free

One uniform grid at cell size `d_max` of the largest class does make a 3×3 scan sufficient for
every pair — no clast's radius exceeds half a cell — and it is the wrong structure, because that
scan sweeps `9 × 1.024²` = 9.44 m² of ground, and at the final 133.38 clasts/m² there are ~1,259
clasts inside it. **Measured over the whole run: 451.3 pairwise distance tests per candidate.**

Give each class its own grid at its own `d_max`, and scan each one out to `a + a_max(class)`
instead. Same result, same guarantees, **10.8 tests per candidate — 41.8× fewer**, because the
dense classes have small radii and the class with the large radius is sparse.

⚠️ So **the rejection test is not O(1) per candidate**, which this document asserted in an earlier
revision and which is false in a way that matters at scale. It is O(*density* × `a_max²`) for the
class being scanned, summed over classes — so widening the size range makes it worse twice over,
once through the candidate count and once through the reach. Drop the pebble floor from 4 mm to
2 mm and the candidates roughly quadruple while each candidate's pebble scan also quadruples in
population: the rejection work goes up about 16×, not 4×. That is the term to watch, not the
sampler.

## The exponent, and the two constructions it means different things in

The size law within and across classes is a parameter, not a fact this skill has a source for.
Its consequences are arithmetic — but **they depend on which construction you are in, and the two
answers are almost opposite.** Getting this backwards was a real defect in an earlier revision of
this page, so both are stated.

### If you draw one global law and place what you drew

Sampling 200,000 diameters from a truncated power law `N(>d) ∝ d^−b` over 4–1024 mm:

| `b` | boulders | cobbles | pebbles | | boulder area | cobble area | pebble area |
|---|---|---|---|---|---|---|---|
| 1.0 | 1.18% | 4.78% | 94.03% | | **75.38%** | 18.90% | 5.72% |
| 1.5 | 0.18% | 1.39% | 98.43% | | 55.36% | 25.46% | 19.18% |
| 2.0 | 0.025% | 0.37% | 99.60% | | 27.54% | 24.77% | **47.69%** |
| 2.5 | 0.0035% | 0.10% | 99.89% | | 8.87% | 14.02% | 77.10% |
| 3.0 | 0.0005% | 0.026% | 99.97% | | 1.55% | 5.24% | 93.21% |

Left half: **the count is pebbles at every exponent** — 94% at `b = 1` and 99.97% at `b = 3`.
Right half: the *visible* ground flips. Area per clast goes as `d²` and the number density as
`d^(−b−1)`, so the covered area per size goes as `d^(1−b)` — and at **`b = 2`** that exponent is
`−1`, which is **equal area per octave of size**. The classes span 2, 2 and 4 octaves
(256–1024 mm, 64–256, 4–64), so `b = 2` should split the ground 25 : 25 : 50, and the measured row
reads 27.54 : 24.77 : 47.69. Below `b = 2` the weight moves to the largest class, above it to the
smallest.

### If you use the largest-first construction this page recommends — and you should

**None of the above governs your counts.** In the recommended scheme the *count* of each class is
set by that class' Poisson `r`, and `b` only picks a radius *within* a class it has already been
assigned to. Re-running the same stratified placement at five exponents, seed 11:

| `b` | boulders | cobbles | pebbles | total | ground covered | transforms / km² |
|---|---|---|---|---|---|---|
| 1.0 | **67** | 776 | 11,209 | 12,052 | **26.48%** | 2.89 GB |
| 1.5 | **67** | 800 | 11,682 | 12,549 | 22.81% | 3.01 GB |
| 2.0 | **67** | 824 | 12,092 | 12,983 | 19.97% | 3.12 GB |
| 2.5 | **67** | 840 | 12,431 | 13,338 | 17.60% | 3.20 GB |
| 3.0 | **67** | 850 | 12,709 | 13,626 | 15.72% | 3.27 GB |

The boulder count is **67 at every exponent**, because 67 is what `r = 1.024 m` yields on a
10 m × 10 m patch and `b` never enters. The total moves 13% across the entire range, and the
instance budget moves from 2.89 to 3.27 GB/km² — so **you cannot buy your way out of the memory
problem by flattening the size law.** Choosing `b = 1` still lands at 90% of the figure the next
section calls a category error.

What `b` *does* control here is **coverage and rejection**: the ground under clasts falls
monotonically from 26.48% to 15.72% as `b` rises, because a steeper law makes the clasts within
each class smaller. A low `b` gives a coarse, blocky field with more of the ground hidden; a high
`b` gives a finer one with more ground showing. That is a look, and it is priced in area, not in
instances.

⚠️ **The two tables answer different questions and the first one is not about this algorithm.**
Read the global table to understand what a size law is; read the second one to plan.

## What it costs, and where the instance path ends

Placement cost, from the run above: **2,853 ms for 13,338 clasts, or 214 µs per clast**, CPython
3, single-threaded, on a 10 m × 10 m patch. ⚠️ Read that as an *algorithmic* figure and never as a
shipping one — it is an interpreted reference implementation, and the useful content of it is the
`2N−1` iterations of O(k) work underneath, which is what survives a port. Against the same rig's
107–134 µs per sample for a bare Poisson pass, the three passes' 16,103 candidates account for
roughly 1.85 s of the 2.85 s, so **the cross-class rejection is about a third of the total** — a
subtraction of two separately-timed things, so treat it as a ratio and not as a measurement.
Composition costs about 1.5× a bare pass, and neither half disappears when you rewrite it in C.
⚠️ Nor is the rejection half O(1) per candidate — see the grid section above, where it measures
451.3 distance tests per candidate on one grid and 10.8 on per-class grids. The 214 µs figure is
the **one-grid** number; the per-class arrangement is the one to port.

The memory is the number that decides the design. Take the smallest honest per-instance
transform — position 3×`float32`, rotation one packed quaternion `uint32`, uniform scale
`float32`, mesh id `uint16` and two bytes of padding — at **24 bytes per instance**, and
extrapolate the measured densities:

| carried down to | instances / m² | instances / km² | transforms / km² |
|---|---|---|---|
| boulder | 0.67 | 670,000 | **16.1 MB** |
| cobble | 9.07 | 9,070,000 | **217.7 MB** |
| pebble | 133.38 | 133,380,000 | **3.20 GB** |

**Boulders are free. Cobbles are a streaming problem. Pebbles are not instances at all.** 3.20 GB
of transforms per square kilometre is not a culling problem, an LOD problem or a compression
problem — it is a category error, and the fix is not to store the pebble class. Two ways out, and
they compose:

- **Make the smallest class a material.** Below the class where the count stops being affordable,
  the ground is not covered in objects; it *is* gravel. That is a surface: an albedo and normal
  variation authored once and tiled, which is `mask-to-material.md`'s subject, and it costs the
  same whether the view holds one square metre or one square kilometre.
- **Regenerate the near field instead of storing it.** The sampler is seeded and the grid is
  local, so a patch can be re-placed on demand from `(tile, class, seed)` and thrown away behind
  the camera; `tiled-streaming.md` gives the residency machinery and `node-graph-runtime.md` the
  per-tile determinism contract. Regeneration converts 3.20 GB of storage into 214 µs per clast of
  compute, which is only a good trade for the classes you can afford to pay it on.

⚠️ **Where the boundary sits is unpriced here.** Choosing between "store it" and "regenerate it"
needs the cost of a ported sampler on the target hardware and the streaming budget it competes
with, and neither was measured for this document. What is measured is the size of the problem —
the three rows above — which is enough to tell you the boundary is between cobble and pebble on
any budget, and not which side of the cobble row it falls on. `simulation-time-budget.md` is where
a measured answer would belong.

## Where they go

Density is a field, not a constant: rock accumulates below cliffs and in channel beds, and thins
on smooth interfluves. The sampler takes one `r` for the whole domain, so a varying density is
imposed by **rejection** — place at the finest `r` the densest region needs, then keep a candidate
with probability `w(x)` read from a mask. `terrain-analysis-masks.md` produces the fields (slope,
curvature, flow accumulation, occlusion) and `mask-operators.md` composes them; nothing in this
document changes how they are built.

⚠️ **Two things about this are not priced, and one is a trap.** The trap: varying `r` *inside* the
sampler instead — a natural-looking optimisation — breaks the grid invariant. Step 0's cell size
is `r/sqrt(n)` for the `r` the grid was built with, so a neighbour scan sized from a *local* `r`
stops covering the clasts a larger neighbour excludes, and the min-separation guarantee is gone
silently. If you vary `r`, the grid and the scan radius must both be sized from `r_min` and
`r_max` respectively, which costs the fixed-size scan that made step 2 O(k). The unpriced part:
what rejection sampling costs in throughput at a given mask contrast, and what `w(x)` should be
for any real lithology — this skill measured neither, and a number for either would be invented.

## How this fails, and what it looks like

| Symptom | Mechanism | Fix |
|---|---|---|
| Rocks interpenetrate, worst of them half-buried in each other | One Poisson pass for every class: `r` is a single separation and the constraint is `a_i + a_j`, which spans a factor of 256 over the Wentworth range. Measured 31 pairs in 15,153, worst buried 63% of the contact radius | One pass per class, largest first, each candidate tested against everything already placed [clast_scatter_practice] |
| Correct spacing, and the ground looks empty | `r` sized for the largest clast, so every pebble holds a boulder's worth of ground: 67 clasts and 0.01% of the patch covered against 17.60% for the largest-first pass | Per-class `r = d_max` of that class, not of the field |
| The scatter has a visible pitch | A jittered grid, or a Poisson pass whose `r` is so close to the packing bound that the result is a lattice with noise on it. Bridson achieved 53.8-60.9% of the hexagonal bound in the runs above | Keep `r` where the sampler is free to reject; check the achieved count against ~0.54 × the bound |
| You asked for N clasts and got about half | The count was planned from the packing bound `2A/(√3 r²)`. Measured achievement 60.9% / 54.7% / 53.8% at three `r`, so the plan runs **39–46% low** | Bisect on `r` against a measured count, or plan off the ~0.54 factor |
| The per-class budget is right and the total is short | Independent per-class passes were summed. Cross-class rejection removes **17.2%** of candidates — 100% of boulders survive, 87.4% of cobbles, 82.5% of pebbles | Plan from kept counts, not candidate counts |
| Candidates cluster inward and the rejection rate is higher than the paper's | The annulus draw is `U(r, 2r)` on the radius instead of `sqrt(U(r², 4r²))`. Mean candidate radius 1.5000 r against the correct 1.5556 r — **3.6% low** | `rho = sqrt(uniform(r*r, 4*r*r))`; the angle stays uniform [bridson2007b] §2 |
| Min separation is violated after adding a per-cell density mask that varies `r` | The background grid's cell size is `r/sqrt(n)` for one `r`; a scan sized from a *local* `r` no longer reaches the neighbours a larger `r` excludes, and the guarantee fails silently rather than loudly | Build the grid from `r_min` and scan from `r_max`, and accept that step 2 is no longer O(k); or keep `r` fixed and vary the *acceptance probability* instead |
| The instance buffer is gigabytes and no LOD scheme helps | The smallest class was instanced. 133.38 clasts/m² is 133 million per km², **3.20 GB** of 24-byte transforms | Stop instancing below the affordable class: the ground is gravel, not objects — `mask-to-material.md`. Boulders alone are 16.1 MB/km², cobbles bring it to 217.7 MB |
| Class edges disagree with every geology reference you check | The edges were copied from a rounded secondary — 65 for 64, 250 for 256 — which destroys the exact φ ↔ mm conversion | φ = −log₂(d/mm); the edges are 2, 4, 64, 256 mm and nothing else |
| The scatter changes when the terrain is re-authored at a different cell size | `r` was expressed in cells rather than in world units. N depends only on `L/r` — measured identical at `r = 2` on 200² and `r = 1` on 100² | Keep `r` in metres; see `resolution-independence.md` |
