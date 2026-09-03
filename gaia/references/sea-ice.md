---
type: Technique
title: Sea ice — floes as a partition, and the two metres of relief that justify it
description: "What a floe field actually is for a terrain tool: a mask partitioned into cells, whose size distribution is a genuinely contested power law, advected rigidly by a wind-driven free-drift balance, and carrying one to five metres of ridge relief — the only part of the subject that touches height at all."
tags: [generation, water, masks, sea-ice, authoring-time]
status: draft
generated: { by: process:claude-code, at: 2026-09-03T00:00:00Z }
sources:
  - { id: rothrock1984, tier: P, locator: "§3 Power law distributions and §6 Conclusions of the submitted manuscript — N(p) behaving like p^α with −1.7 < α < −2.5 across the data sets examined, together with 'we see no reason to expect a power law or any other simple analytical form to be valid for all p'; §3 for the finiteness constraints, α > −2 for the small floes to occupy finite area and α > −1 for finite perimeter, and for the Poisson field whose inscribed-circle diameters are distributed exponentially as N(p) = N(0)·exp(−p/λ), with 'We do not expect to observe exponential distributions in nature'; Table 1 for the shape ratios measured over 782 digitised summer floes, and the paragraph introducing it for the sample of 782. ⚠️ The artefact read is Appendix I of NASA final report NAG-5-160, the SUBMITTED manuscript; section, table and figure numbers are the manuscript's and not the JGR paper's" }
  - { id: denton2022, tier: P, locator: "Sect. 1 pp. 1563–1564 for the single-versus-two-power-law disagreement, the study lists on each side, and 'it remains an open question as to whether a single power law holds across all floe scales and in all settings, or whether there may be two distinct power-law regimes'; Sect. 3.1 for least-squares slopes m from −2.03 to −1.65 with a mean of −1.79 ± 0.08 over 78 images, an MLE mean of −1.77 ± 0.11, and 76% of fits passing the goodness-of-fit test at p ≥ 0.1; Sect. 2.3 for the noncumulative construction n(a) = c·a^m and for a finite upper bound making the cumulative form concave-down; Sect. 3.4 for the 2m+1 conversion between area-based and diameter-based noncumulative slopes and for the area-to-diameter relation a = 0.66·x²" }
  - { id: brunette2022, tier: P, locator: "Sect. 3.1 eqs. (1)–(6) — the sea-ice momentum equation, the quadratic air and water drag laws, the steady-state balance τ_a = τ_w that defines free drift, and its closed form U_i = α·e^(−iθ)·U_a + U_w with α = sqrt(ρ_a·C_a / ρ_w·C_w); Sect. 3.1 for that one-line relation explaining roughly 70% of sea-ice velocity variance in the central Arctic; Sect. 1 for the reviewed wind factors and turning angles — Nansen about 2% at 20–40° to the right of the near-surface wind, Thorndike and Colony 0.8% at 5° for fall, winter and spring and 1.1% at 18° for summer against the geostrophic wind, Polar Pathfinder's constant 1% at 20°, and Uotila's 1.3–3.3% at 23–25°; the abstract for this paper's own least-squares optimal turning angle of 25°" }
  - { id: duncan2018, tier: P, locator: "Abstract p. 137 — mean sail height 0.99 to 2.16 m and maximum sail height 2.1 to 4.8 m across the 12 pressure ridges mapped; eq. (10) and the paragraph following it for the sail-height definition H_s = ℓ·tan a and the 0.6 m minimum adopted there, after Tan and others 2012's 0.62 m optimal cutoff separating pressure ridges from other sea-ice surface undulations; Introduction p. 137 for ridges forming where separate floes converge and collide" }
---
# Sea ice — floes as a partition, and the two metres of relief that justify it

⚠️ **Read the grade before the document.** This is the lowest-value topic in Gaia's coverage map,
and nothing below changes that. A floe field is almost entirely a **mask** problem — a region cut
into cells — and the mask operators it needs are already written down elsewhere. Its total
vertical signal is **one to five metres** on floes hundreds of metres to tens of kilometres
across [duncan2018], which is a relief-to-extent ratio of order `10⁻³`: for a heightfield tool
this landform is flat. It is here because Gaea ships an `IceFloe` node and because the coverage
map is supposed to record what was looked at, not only what was worth building.

What *is* worth the read is the size distribution, because it is the cleanest example in this
corpus of a number everyone quotes and nobody agrees on.

## Use this

**Author the floe field as a mask, not a simulation. Sample floe sizes from a truncated power law
with an explicitly chosen exponent, place them, and use a partition — Voronoi or Laguerre — only
to generate the crack network between them. Advect the whole mask rigidly by a free-drift
velocity `U = α·e^(−iθ)·U_wind + U_current`, and add height only where floes converge, as ridge
lines carrying one to two metres of sail.** The four clauses are in order of how much they matter.

**Do not derive the floe sizes from the partition.** This is the one measured result in this
document that changes a design, and it is negative: a Poisson-Voronoi tessellation produces cells
that are all nearly the same size, and the observed distribution is not remotely that. The
numbers are in the next-but-one section.

**There is no canonical source for the procedural recipe**; no paper states floe generation as a
heightfield operator. Standard practice is to scatter points, tessellate, and call the cells
floes — and the measurement below is that standard practice reproduces none of the published
statistics. Grade the recipe `F` and treat everything in it as taste except the numbers that
carry a citation.

**What it beats.** *A discrete-element floe simulation* — the right tool for asking how a floe
field evolves, and it is a rigid-body contact solver, which is a different program from a terrain
tool and does not become one by being embedded in a node graph. *A fracture simulation of the ice
sheet* — you would be solving for a crack network whose statistics you already know and can draw
directly. *Noise thresholded into blobs* — no size distribution, no leads, no convergence, and
the blobs have curved boundaries where floe edges are straight fracture traces. *Gaea's
`IceFloe`* — UI branding over a partition-plus-mask operation; the node name is not an algorithm,
and the question to ask of it is which of the numbers below it hits.

## The exponent is contested, and the contest is the content

Almost every treatment of floe size says "power law" and then quotes a number. The founding paper
does not. [rothrock1984] measures the cumulative number distribution `N(p)` — floes per unit area
with mean caliper diameter no smaller than `p` — across an aerial mosaic, a LANDSAT scene and
four U-2 photographs, and concludes:

> In some of the data sets we have examined, `N` behaves approximately like `p^α` with
> **−1.7 < α < −2.5**, but **we see no reason to expect a power law or any other simple
> analytical form to be valid for all `p`.** We find changes in the distribution from year to
> year and from one region to another. — [rothrock1984] §6

Thirty-eight years later the question is still open, and [denton2022] Sect. 1 states it as such:
the FSD "resembles a single power law … or two distinct power laws depending on floe scales", and
"it remains an open question as to whether a single power law holds across all floe scales and in
all settings". Studies are named on both sides — Gherardi & Lagomarsino, Hwang, and Stern for one
power law; Steer, Toyota, and Geise for two — **and this document has opened none of them.** It
reports that the disagreement exists and where the list comes from; it quotes no exponent from
any of them, and the bibliography records that refusal.

The one modern number here that was read in its own paper: [denton2022] segmented 78
high-resolution optical images of the Canada Basin spanning 1999–2014 and fitted the
**noncumulative area** density `n(a) = c·a^m` over 50 m² to 5 km², getting **m from −2.03 to
−1.65, mean −1.79 ± 0.08**, with a maximum-likelihood mean of −1.77 ± 0.11 that differs from the
least-squares value by about 3%.

⚠️ **And 76% of those fits pass the goodness-of-fit test.** [denton2022] Sect. 3.1 reports it
plainly: 76% at `p ≥ 0.1`, meaning the power-law model is *rejected* for roughly a quarter of the
images in the paper that concludes the FSD is a single power law. That is the correct
calibration to carry into a tool. The distribution is a good default and a bad law.

### Why the published exponents disagree more than the ice does

A large part of the apparent spread is bookkeeping, and [denton2022] Sect. 3.4 gives the
conversion. A slope fitted to the noncumulative density of floe **areas** and a slope fitted to
the noncumulative density of floe **diameters** are not the same number: with `a ∼ x²`, a
diameter-based slope equals **`2m+1`**. Inverting that for Stern's reported −2.81 to −1.90 puts
them at −1.91 to −1.45 in the area convention, which overlaps Denton's own −2.03 to −1.65
closely. **Two papers that very nearly agree can look a full unit of exponent apart if you read
the numbers off the abstracts.**

The cumulative form adds a second trap. [denton2022] Sect. 2.3: when the population has a finite
largest floe — which it always does, because the domain is finite — a straight noncumulative
log-log line becomes a **concave-down** cumulative curve, with a flattened small end and a steep
tail, "neither of which can be discerned as purely physical". A tool that fits a cumulative curve
and reports a break in slope has probably just measured its own domain size.

**So before you compare any two exponents, including two of your own, settle three things:
cumulative or noncumulative, area or diameter, and what the upper truncation is.** Most of the
literature's disagreement lives in those three choices, and all three are free parameters in your
generator.

### The one hard constraint on the exponent

[rothrock1984] §3 derives what an exponent is not allowed to be, by integrating the distribution.
For `N ∼ p^α` at small `p`:

| Range | Consequence |
|---|---|
| `α = 0` | finite number of floes |
| `−1 < α < 0` | infinite number of floes, finite total perimeter |
| `−2 < α < −1` | infinite number of floes, **infinite total perimeter** |
| `α ≤ −2` | **infinite total area** — impossible |

This is worth having because it is not a fit, it is arithmetic: an exponent at or past −2 in the
cumulative diameter form makes the small floes cover infinite area, so any generator quoting one
is relying entirely on its lower truncation to stay finite. **And note where that puts the
measurements**: [rothrock1984]'s own reported range, −1.7 to −2.5, straddles the limit. Half of
the observed slopes are steeper than a single power law is allowed to be down to `p = 0`, which
is the arithmetic behind the paper's refusal to assert one. That is legitimate and it must be
deliberate: **`p_min` is not a performance setting, it is the parameter holding the distribution
together**, exactly as `D_min` is for a crater field in `impact-craters.md`.

And [rothrock1984] §3 notes the visual consequence of a power law with no natural length scale:
"it is a common experience to confuse sea ice images with quite different scales". A scale-free
floe field is one you cannot judge the size of. If your render needs to read as *ten kilometres
of ice*, something in it must break the self-similarity — a shore, a ship, a lead of known width.

## What a partition actually produces (measured, and it is not this)

The obvious recipe is to scatter points and tessellate. It does not work, and the failure is
large enough to see without measuring — but measuring it says by how much.
`floe_partition.py`, recorded in `registers/pseudocode-execution.tsv` builds each partition on a 1024² periodic grid by jump flooding
(the operator `mask-operators.md` describes), takes exact cell areas as pixel counts, and fits
the **same** noncumulative log-log density [denton2022] fits, with the same minimum-two-per-bin
rule. Target: `m = −1.79 ± 0.08` over about five decades of area.

| Construction | fitted `m` | CV of area | area in the largest 10% of cells |
|---|---|---|---|
| **Poisson-Voronoi, N = 300 / 1000 / 3000** | **−0.20 / −0.53 / −0.07** | **0.52–0.53** | **0.21** |
| clustered (Thomas) seeds | −1.16 | 2.01 | 0.60 |
| Laguerre, radii drawn from `r^−2` | −0.92 | 2.62 | 0.68 |
| Laguerre, radii drawn from `r^−3` | −0.76 | 1.16 | 0.30 |
| recursive fracture, split prob. 0.65 / 0.75 / 0.85 † | −1.20 / −1.21 / −1.36 | — | — |
| Voronoi(4000) + random merge to 1000 / 300 / 120 † | −1.21 / −1.18 / −0.80 | 3.2–15.3 | 0.68–0.98 |
| *control: a true `a^−1.8` sample, same fitter* | ***−1.80*** | *13.1* | *0.88* |
| *control: a true `a^−2.0` sample, same fitter* | ***−1.99*** | *8.8* | *0.74* |

† mean of 5 seeded realisations. The controls recover −1.80 and −1.99 from true −1.8 and −2.0, so
the fitter is not the problem.

**Plain Poisson-Voronoi is off by the entire exponent.** Its fitted slope is near *zero*: cell
areas have a coefficient of variation of about 0.5, span under two decades, and the largest tenth
of the cells holds a fifth of the ice. In a **synthetic power law** at the observed exponent the largest tenth holds **0.88** of the ice
at −1.8 and **0.74** at −2.0 — ⚠️ both ends of that pair sit inside Denton's own measured range, so
this is a property of the fitted law, not a field observation, and it moves by a seventh across the
published spread. No source read here reports the statistic directly.
A real field is a few enormous floes among a scatter of chips; a Poisson-Voronoi field is
interchangeable pebbles, which is what every naive floe node looks like. The CV barely moves
across N = 300, 1000 and 3000 — 0.52, 0.52, 0.53 — so this is the construction's own statistic
and not a sampling artefact of one run.

[rothrock1984] §3 got there first, with the neighbouring construction: a **Poisson line field**
has inscribed-circle diameters distributed *exponentially*, `N(p) = N(0)·exp(−p/λ)`, and the
paper's verdict on it is "The Poisson field bears only a slight resemblance to winter ice, and
none to summer ice… **We do not expect to observe exponential distributions in nature.**" An
exponential and a near-constant cell size are the same failure: a tessellation of a
homogeneous point process has a characteristic scale, and a floe field does not.

**Every cheap fix tested gets closer and none arrives.** Clustered seeding, Laguerre weights drawn
from a power law, recursive fracture and random coalescence all land between −0.76 and −1.36 on
average — half to three-quarters of the way, and none of them inside the observed −2.03 to −1.65.

⚠️ **And they are wildly seed-dependent, which is why the means above are over five realisations
and not one.** Voronoi-plus-merge to 300 cells ranges from −1.49 to −0.92 across five seeds; a
single run of it produced −1.63 during drafting, which looked like a near-match and was luck.
Recursive fracture is worse: with a per-node continue probability, the very first split can fail,
and two of the fifteen realisations here terminated at one or three pieces. **Any claim that a
construction "matches the power law" that rests on one realisation is measuring its seed.**

**Hence the recommendation.** Draw the sizes from the distribution you want, by inverse transform
from a truncated power law between an explicit `p_min` and `p_max`, and then place them. Use the
partition for what it is genuinely good at — producing a **space-filling network of straight
shared edges**, which is what leads between packed floes look like — and not for what it is bad
at, which is deciding how big anything is.

## Floe shape is measured, and it is nearly a disc

[rothrock1984] Table 1 digitised 782 summer floes over about 1 km across and reports the
ratios between floe properties. In terms of mean caliper diameter `p`:

| Ratio | Floes | A disc | sd |
|---|---|---|---|
| area / `p²` | **0.66** | 0.785 | 0.05 |
| perimeter / `p` | **3.17** | π = 3.14 | 0.04 |
| inscribed circle diameter / `p` | 0.77 | 1 | 0.09 |
| area / perimeter² | **0.065** | 1/4π = 0.080 | 0.005 |

Two things fall out. **`perimeter = π·p` holds to 1%** — [rothrock1984] notes this is exact for
any convex shape, so floes are convex to within measurement error. And the isoperimetric ratio
`4πA/P²` is `4π × 0.065 = 0.817` against a disc's 1.0: **floes are compact, not ragged.** A
generator producing long thin shards or fractal coastlines is producing something else.

⚠️ **One transcription trap, recorded because it nearly propagated.** The manuscript's prose gives
area as `0.56 p²` and its own Table 1 gives `0.66`. `floe_numbers.py`, recorded in `registers/pseudocode-execution.tsv` resolves it
two ways: `0.065 × 3.17² = 0.653`, and the table's sd/mean column of 0.08 against sd = 0.05
implies 0.66 rather than 0.56. [denton2022] Sect. 3.4, reading the published paper, also uses
`a = 0.66·x²`. **Use 0.66.** This is what "a constant reconstructed from memory is a `?` wearing
a `P`'s confidence" looks like when the memory is a scanned page.

## Segmentation and the lead network are somebody else's operators

Once you have a floe mask, everything you want from it is already written down, and this document
adds nothing to it. `mask-operators.md` owns the whole toolchain:

- **Which pixels are one floe** is connected-component labelling — a two-pass union-find,
  provably linear in the pixel count, and `mask-operators.md` gives the algorithm and the
  complexity argument.
- **Removing speckle without deforming floes** is the **area opening**, not a morphological
  opening; `mask-operators.md` measures the difference and it is the difference between losing
  0% and 54% of the largest real feature.
- **Lead width, distance to the nearest floe edge, and the inscribed-circle diameter**
  [rothrock1984] uses as a floe size proxy are all readings of the **exact Euclidean distance
  transform**; the raster partition itself is a **jump flood**. Both operators are
  `mask-operators.md`'s, with its measured cost.
- **Where the ice ends and open water begins** is `water-closed-vs-open.md`'s boundary, not a new
  one. The waves that break the ice are `wave-models.md`'s spectra, and what waves do to a
  *shore* is `coastal-erosion.md`'s; a floe is neither.

The one thing worth saying here is a threshold: express floe and lead size thresholds in **world
units**, m or m², and divide by cell area, or the same graph despeckles differently at every LOD.
That is `mask-operators.md`'s rule and it bites hard here, because the distribution spans five
decades and the smallest floes are always near the cell size.

## What moves them

Free drift is the motion of ice under wind and current **with the internal ice stress dropped**,
and it is one line. [brunette2022] Sect. 3.1 starts from the momentum equation, eq. (1), with
wind stress, ocean drag, Coriolis, internal stress `∇·σ` and sea-surface tilt; assumes steady
state, thin ice, and no internal stress; and is left with `τ_a = τ_w` — the two quadratic drag
laws of eqs. (2)–(3) balancing. The solution, eqs. (5)–(6):

```
U_ice = α · exp(-i·θ) · U_wind  +  U_current
α     = sqrt( (ρ_a · C_a) / (ρ_w · C_w) )
```

`α` is a wind factor and `θ` a turning angle, applied as a complex rotation of the wind vector.
**That is the whole model, and [brunette2022] Sect. 3.1 records that it explains roughly 70% of
sea-ice velocity variance in the central Arctic.** For an authoring tool, 70% of the variance for
two scalars is an excellent trade.

The two scalars, as [brunette2022] Sect. 1 reviews them:

| Source | wind factor, magnitude of `α` | turning angle `θ` | against which wind |
|---|---|---|---|
| Nansen (1902), the Fram drift | ≈ 2% | 20–40° right | near-surface |
| Thorndike & Colony (1982), winter | 0.8% | 5° | geostrophic |
| Thorndike & Colony (1982), summer | 1.1% | 18° | geostrophic |
| Polar Pathfinder, as used | 1% | 20° | geostrophic |
| Uotila (2001), Baltic buoys | 1.3–3.3% | 23–25° | 10 m |
| [brunette2022]'s own least-squares fit | thickness-dependent | 25° | — |

⚠️ **The turning angle depends on which wind you are turning.** Surface friction veers the wind
left in the boundary layer while the ice goes right of the surface wind, so the same physics gives
a *smaller* angle against a geostrophic wind than against a 10 m wind [brunette2022] Sect. 1. A
tool with one wind field and one angle has silently picked a convention; say which.

Evaluating `α = sqrt(ρ_a C_a / ρ_w C_w)` over the usual drag-coefficient ranges
(`ρ_a = 1.3`, `ρ_w = 1026`, `C_a` 1.2–2.5 × 10⁻³, `C_w` 3.0–8.0 × 10⁻³) gives **1.4% to 3.3%**
which brackets the values referenced to a **near-surface or 10 m** wind — Nansen's ≈2% and Uotila's
1.3–3.3% — and sits **above** the geostrophic-referenced rows (0.8%, 1.0%, 1.1%). ⚠️ That is the
same convention split the warning above makes about the turning angle, and it applies to the
magnitude for the same reason: a geostrophic wind is the stronger one, so the same ice speed
divided by it gives a smaller factor. An earlier revision of this line claimed the bracket covered
*every* row, which it does not — four of the five sit outside it, and the fix is to compare like
with like rather than to widen the bracket. The formula is not a fit; it is a ratio of drag
coefficients, and against the winds it is derived for it lands in the right place.

**The authoring consequence is that a floe field is advected, not simulated.** One vector per
frame, applied to the whole mask as a rigid translation plus a slow rotation, reproduces the
dominant motion. `driver-fields.md` owns wind fields — but note that its wind is *terrain-derived*
shelter, `Sx` and `Sb` computed from upwind slope, and over an ocean there is no upwind slope.
The wind a floe field needs is the unsheltered synoptic field, which that document explicitly
does not model. Take the vector from your weather authoring and the two coefficients from here.

## Ridging is the only part that touches height

Everything above is a mask. Ridging is not: it is the one mechanism that puts a floe field into
a heightfield at all. Ridges form where floes converge and collide [duncan2018] — the ice has
nowhere to go, so it goes up and down, rubble piling into a **sail** above the waterline and a
**keel** below it. Only the sail is in your heightfield, and only the sail is measured here — keel
depth is the larger number in the literature and **no source opened for this document reports
one**, so none is asserted.

The numbers, from 12 Arctic ridges mapped in Operation IceBridge imagery [duncan2018]:

- **mean sail height 0.99 to 2.16 m** per ridge,
- **maximum sail height 2.1 to 4.8 m**,
- and a **0.6 m lower cutoff**, below which a bump is sastrugi and not a ridge.

Put that against floe sizes. A 1.5 m sail on a 1 km floe is a relief-to-extent ratio of
`1.5 × 10⁻³` and a mean slope of **0.17°**; on a 10 km floe it is `1.5 × 10⁻⁴`. The most extreme
combination in [duncan2018] — a 4.8 m sail on a 1 km floe — reaches 0.55°. A mountain range is
`10⁻¹`. **The entire vertical content of a sea-ice landform is two orders of magnitude below the
smallest thing a terrain heightfield is usually asked to carry**, which is the whole reason this
topic is graded the way it is.

So: **do not simulate convergence.** Take the lead network the partition already gave you, choose
the edges where your drift field is convergent — the divergence of `U` is one finite difference
away and it is negative there — and paint a ridge line along them with a sail height drawn near
1–2 m and clipped below at 0.6 m. That is a mask-to-height operation of the kind
`mask-to-material.md` and `thermal-and-aeolian-erosion.md` already cover; the talus relaxation of
a rubble pile is repose behaviour and belongs to the latter. **There is no canonical source for
that recipe; standard practice is to paint ridges onto lead edges by hand**, and nothing found
here states it as a published operator.

## The crossover that changes the answer

| Situation | Do | Because |
|---|---|---|
| A still frame, ice as ground cover | Mask only; no drift, no ridging | The relief is `10⁻³`; nothing else is visible |
| You need the published size statistic | Sample sizes from the power law and place them | Every partition tested fits `m` shallower than −1.65 |
| You need leads that look right | Voronoi or Laguerre partition, edges as leads | Straight shared edges are what packed-floe cracks are |
| You need both | Partition for edges, sampled sizes for cells | Merging a fine partition averaged only −1.2, with a −0.9 to −1.5 seed spread |
| Motion over hours to days | Free drift, `α ≈ 1–2%`, `θ ≈ 20°` | One line, ~70% of the variance [brunette2022] |
| Motion in a converging field | Free drift plus ridge lines on convergent edges | Convergence is the only source of vertical relief |
| Marginal ice zone, wave-broken | Smaller `p_max`, steeper `m` — but do not quote a break | The two-regime claim is contested and unread here |
| An ice field that must interact mechanically | Not this document; a DEM contact solver | Rigid-body contact is a different program |

## How this fails, and what it looks like

| Symptom | Mechanism | Fix |
|---|---|---|
| Every floe is the same size | Cell sizes taken from a Poisson-Voronoi partition | Measured CV 0.52 and a fitted slope near zero; sample sizes from the distribution instead |
| A few huge floes and nothing between | Power law sampled with no `p_min`, or `p_min` set from cell size | `p_min` sets what the field looks like, not just its cost |
| Total floe area diverges as you refine | Cumulative diameter exponent at or past −2 | `α > −2` is required for finite area [rothrock1984] §3 |
| Your fitted exponent disagrees with a paper's by ~2× | Comparing area-based to diameter-based, or cumulative to noncumulative | Diameter slope = `2m+1` [denton2022] Sect. 3.4; settle the convention first |
| A "break in slope" appears in your cumulative fit | Finite largest floe makes any bounded power law concave-down | Fit the noncumulative form [denton2022] Sect. 2.3 |
| The power law is asserted as a law | Reading one paper's headline exponent | 24% of [denton2022]'s own fits are rejected by its goodness-of-fit test |
| Floe outlines are ragged or fractal | Boundary noise applied after segmentation | `4πA/P² = 0.817`, and `perimeter = π·p` to 1% — floes are convex and compact [rothrock1984] |
| Floe edges are curved, leads have no width | Blobs from a thresholded noise field, not a partition | Partition edges are straight and shared; widen them into leads with a distance transform |
| Small speckle survives despeckling, or floes get eaten | Morphological opening used as the size filter | Area opening, `mask-operators.md` |
| Despeckling changes with resolution | Threshold stored in cells | Store in m², divide by cell area |
| The ice drifts straight downwind | Turning angle omitted | `U = α·e^(−iθ)·U_wind + U_current` [brunette2022] eq. (5) |
| Drift speed is wrong by 2× | `α` taken for the wrong wind, or a 10 m angle used with a geostrophic wind | 0.8–1.1% at 5–18° geostrophic; ~2% at 20–40° near-surface [brunette2022] Sect. 1 |
| Ridges look like mountains | Sail height authored by eye | Mean sail 0.99–2.16 m, max 4.8 m [duncan2018] |
| Ridges appear everywhere | Ridge placement uncoupled from the drift field | Ridge only on convergent edges; `∇·U < 0` is one finite difference |
| Sea ice reads as terrain and disappoints | Expecting height from a `10⁻³` landform | Spend the effort on the mask and the material, not the heightfield |
