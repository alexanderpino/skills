---
type: Technique
title: Sketch-based authoring — a drawn constraint against a solver
description: "Turning a drawn ridge line or river path into terrain: the sparse-to-dense interpolation as a Laplace solve with a gradient term, hard versus soft constraints as one weight, the C1 falloff at the edge of the edited region, and the three-way choice of whether the constraint is imposed before, during or after the erosion pass."
tags: [generation, authoring, constraints, sketching, interpolation, diffusion]
status: draft
generated: { by: process:claude-code, at: 2026-09-03T00:00:00Z }
sources:
  - { id: hnaidi2010, tier: P, locator: "§3.1 for the feature-curve constraint tuple — elevation hi and plateau radius ri, angle constraints ai, bi, θi, ϕi, noise amplitude Ai and roughness Ri, at parameter ui — and for elevation interpolated along the curve by a cubic spline while every other attribute is linear, 'to avoid unnatural piecewise linear ridge lines'; §4.2 for the three equation orders, Laplace ΔF = 0 order 2, gradient ∇F = G order 1, identification F = F order 0, and for the explicit refusal of Poisson — 'we do not use Poisson partial differential equations because this would require the computing of the divergence of the gradient. This operation induces the loose of the gradient direction', plus 'Poisson equation simplifies to a Laplace equation when we set a null gradient constraint and thus forbids the creation of horizontal angle constraints'; §4.1 for the gradient-intersection rule, leave intersecting areas empty and Laplace-diffuse to fill the holes, with fig. 9; §5.2 for the Jacobi blend F = αFL + βFG + one-minus-α-minus-β times FI, with α = β = one half in gradient areas, α = β = 0 in strict elevation areas, and 'If we want to approximate and not interpolate elevation constraints, we can set α > 0 and the solution will be smoother. But this breaks edges on features'; §5.2 for 5 times l−i Jacobi iterations at multigrid level i; §6 Table 2 for computing times of 0.168 to 0.811 s across 512², 1024² and 2048², and §6 for ten n×n 32-bit grids, 40 MB at 1024², and for the canyon of fig. 10 — a first sketch in under 3 minutes and almost 45 minutes of detail editing" }
  - { id: orzan2008, tier: P, locator: "§3.2.2 for the diffusion as a Poisson solve, ΔI = div w with I = C at pixels that store a colour value, and for the multigrid with Jacobi relaxations and 5i iterations at level i on a 512×512 image; §3.2.1 for the constraint band — colour sources are displaced a distance d normal to the curve, d = 3 pixels in their implementation, with the gradient constraint left on the curve itself so the sharp transition survives, and for the stencil test that discards overlapping sources where curves are close or highly curved; §3.2.4 for the statement that a Poisson solution is global, 'any color value can influence any pixel of the final image', and for the fix — solve coarsely over the whole domain first and use that solution as Dirichlet boundary conditions around the window you are refining" }
  - { id: gain2009, tier: P, locator: "§4 eq. (1) for the falloff W_i = d of the ratio of the distance from the shadow to the distance from the boundary, with d(a) = (a²−1)², described as 'This C1 blending function ensures full weighting on the shadow tapering to zero at the boundary'; §4 eq. (3) for the deformation ΔT_i = W_i times the height difference between silhouette and terrain; §4 for the boundary contracted per scale, B_i = φi over φ0 times B_0, and for the silhouette truncated by the filter width at its ends to guarantee C1 where it meets the terrain; §4 Noise Propagation for the calibration experiment — 10 subjects, sketched noise variance in error against the source terrain 'from 5% to 50%', and the decision to fit an exponential decay through the sketched variance rather than use it raw; §5 Efficiency for 512×512 with 6 wavelet levels in under 2.3 s and deformation linear in the number of grid elements deformed; §5 Realism for the admission that the join is visible on inspection because wavelet noise is isotropic and real erosion gullies are not" }
  - { id: genevaux2013, tier: P, locator: "§7 for the construction tree A = C of B of the terrain primitives and B of the river primitives, for weighting functions 'defined on a compact support to limit their influence' with w(p) = 0 wherever d(p)² ≥ r², and for the replace operator h_C = one-minus-w_B times h_A plus w_B h_B; §8 Control for the claim that matters here — the user sketches rivers, river mouths and slope maps, and 'Independently on the quality of the user input, our approach will lead to a hydrographically correct river network', with fig. 19 for two constraint functions sketched in two minutes" }
  - { id: stava2008, tier: P, locator: "§8 for the editing vocabulary, 'add spring, dry, evaporate, rain, add obstacle of easy-to-erode material' — every one of them an input to the simulation, none of them a height; §7 Table 1 and §8 for 20 fps at 2048×1024 with four material layers, and for the 32-bit-float texture budget that caps the grid there" }
  - { id: constraint_timing, tier: F, locator: "no artefact: whether a user constraint is imposed before, during or after the erosion pass. Every paper opened for this document picks one and does not discuss the other two" }
---
# Sketch-based authoring — a drawn constraint against a solver

A user draws a ridge line. Two things now want the heightfield and they want different things:
the drawing, which is a sparse set of exact values on a curve, and the erosion model, which is a
solver with its own opinion about what a hillside looks like. Everything hard about sketch-based
authoring is that conflict, and the decision that resolves it is not *how* to interpolate the
drawing — that part is a linear solve with a known answer — but **when** the constraint is
imposed relative to the simulation.

This document owns the general constraint problem: sparse drawing to dense field, hard against
soft, and the edge of the edited region. The **river carve** is one instance of it and belongs to
`river-networks.md`, which owns the centreline-to-channel operator and the downstream-monotonicity
fix; do not redo either here. Uplift fields are `tectonic-uplift.md`; the distance field it
prescribes is computed by `mask-operators.md`. The solvers a constraint has to survive are
`hydraulic-erosion.md` and `stream-power.md`.

## Use this

**Interpolate the drawing with a Laplace solve carrying a gradient term, and impose the result
*after* the erosion pass as a compactly supported primitive with a C1 falloff — while feeding the
same drawing into the simulation as an *input* (uplift, erodibility, a water source) so the
physics agrees with it rather than fights it.**

Concretely:

- **Rasterise the curve** into three constraint images — elevation, gradient direction and
  magnitude, noise parameters — then solve `ΔF = 0` where you have no gradient information,
  `∇F = G` where you do, and `F = F` on the drawn cells themselves [hnaidi2010] §4.2. One
  multigrid pass, GPU, 0.17–0.81 s over 512² to 2048² in the paper.
- **Blend it in with a C1 weight** `w(a) = (a² − 1)²`, `a` = distance over support radius
  [gain2009] eq. (1), on a support that is exactly zero outside its radius [genevaux2013] §7.
- **Feed the drawing to the sim too**, as [genevaux2013] §8 and [stava2008] §8 both do — the
  user's line becomes a river mouth, a slope map, a spring or a band of soft material, and the
  generator then guarantees the invariant "independently on the quality of the user input".

**What it beats**, each measured below in `scratchpad/w7/constraint_solvers.py`:

- *Impose it before, as an initial condition, and let erosion have it* — a 4-cell ridge keeps
  **18.8% of its visible relief** after 200 diffusion steps. This is the right answer only when
  the feature is wide relative to the run (§2 crossover).
- *Re-project the constraint every solver step* — costs almost nothing (**21% of one diffusion
  step**), and leaves a curvature spike of **88.3** at the edge of the projection mask against
  **0.69** for the unconstrained field: a 128× scar. It also never settles; at step 200 it is
  still putting back 19% of what it put back on step 1.
- *Paste it on afterwards with a hard-edged stamp* — **28 interior pits against a control of 15**.
  The stamp dams the drainage, and every downstream consumer inherits that.
- *Sculpt the heightfield by hand with no falloff* — a 40 m edit at a hard cut is a
  **40 m/cell** slope step at the seam. A linear falloff over 32 cells still leaves 1.25 m/cell.
- *Interpolate with a thin-plate (biharmonic) solve* — smooth, but it passes **through** the
  constraint instead of creasing at it, which is wrong for a ridge and right for a hill (§1).
- *Example-based synthesis from an exemplar DEM* — excluded from this skill by design; see the
  last section.

## The three places a constraint can go

This is the decision, and no source opened for this document states it as a choice
[constraint_timing] — no canonical source; standard practice is for a paper to pick one arm and
not discuss the other two. [hnaidi2010] and [gain2009] impose before and run no erosion at all;
[stava2008] edits during; [genevaux2013] constructs after. So the comparison below is measured
here rather than quoted.

Same terrain (257×257, tilt plus fBm), same drawn crest (Gaussian, σ = 4 cells, 40 m, curved),
same 200 explicit hillslope-diffusion steps:

| | relief kept | interior pits | max `|Δ²h|` in the skirt |
|---|---|---|---|
| **before** — initial condition, then erode | 18.8% | 15 | 0.69 |
| **during** — re-imposed every step | 93.4% | 16 | **88.29** |
| **after** — smooth stamp on the eroded result | 93.0% | 17 | 1.76 |
| **after** — the same stamp, hard-edged | 94.1% | **28** | 6.60 |
| *control* — erosion, no constraint at all | — | 15 | 0.69 |

Read the columns, not the rows. **Fidelity** (column 1) says "before" loses the drawing and the
other three keep it. **Consistency** (column 2) says only the hard-edged paste damages the
drainage, nearly doubling the pit count. **Seam** (column 3) says the per-step projection is by
far the most violent, because a hard-edged mask re-applied 200 times builds a wall at its own
boundary that the solver spends every step trying to smooth away.

That last point is the one that is easy to get backwards. Per-step projection *feels* like the
principled option — it is a constraint that holds at every instant — and it is the worst of the
three on the only metric where it should have won. The mechanism is that a projection is a
discontinuous operator: it is `where(mask, …)`, and the solver's stencil straddles the mask edge.
The projection re-adds height inside; diffusion carries it out; the projection re-adds it again.
Measured, the height re-added per step falls from 4,562 to 867 cell-metres over 200 steps and
then stops falling — 19% of the initial rate, forever. **A per-step projection does not converge
to a fixed point; it converges to a steady flux.**

⚠️ **Cost is not the reason to avoid it.** One whole-grid masked re-projection costs 110 µs
against 532 µs for one diffusion step, and 26 µs if you restrict the write to the mask's bounding
box — 21% and 5% of a step. Per-step projection is cheap. It is *wrong*, and it is wrong in a way
that a profiler will never show you.

**The crossover between "before" and "after"** is the only one of the three with a closed form,
and it is the feature's width against the erosion's diffusion length. Under `∂h/∂t = D∇²h`, a
Gaussian ridge of half-width `σ` keeps peak amplitude `A(t)/A₀ = σ/√(σ² + 2Dt)`, so it is half
gone at `t = 1.5σ²/D`. Impose **before** when

```
sigma >= sqrt(2 * D * T / 3)          # T = total simulated erosion time
```

and **after** otherwise. Measured against theory, exactly (`constraint_solvers.py` §2):

| σ (cells) | predicted half-life (steps) | measured | amplitude kept after 200 |
|---|---|---|---|
| 2 | 30 | 30 | 0.218 |
| 4 | 120 | 120 | 0.408 |
| 8 | 480 | 480 | 0.667 |
| 16 | 1920 | 1920 | 0.873 |

⚠️ **That closed form is in PEAK amplitude, and the table above it reports RELIEF. They are not the
same number and the document owes you the reconciliation.** The same σ = 4 crest over the same 200
steps keeps **0.408 of its peak** and **18.8% of its visible relief**, because diffusion raises the
flanks while it lowers the crest and relief is the difference between them. The measurement script
says it outright: *peak retention flatters the survivor; relief is what a viewer sees.* So a ridge
sitting exactly on `σ = sqrt(2DT/3)` keeps half its peak and appreciably less than half of what a
viewer would call the ridge. Treat the closed form as a **lower bound on the width you need**, not
as the width that works, and check relief on your own field before trusting it. (Curvature is not
the explanation: a curved arc decays within 0.5% of a straight ridge, 0.410 against 0.408.)

At `D = 1`, `Δt = 0.2`, 200 steps, the threshold is `σ ≥ 5.16` cells, and the table crosses
between 4 and 8 as it must. **Half-life goes as width squared**: doubling the width of a drawn
feature buys four times the life. That is why erosion eats drawn creases and spares drawn
mountains, and why a tool that lets the user draw at any scale needs to tell them which side of
the line they are on.

⚠️ **This law is for the diffusion term only.** It was derived and measured against
`∂h/∂t = D∇²h`, the hillslope term `stream-power.md` keeps always on. The corresponding decay for
droplet erosion and for the `K·A^m·S^n` incision term was **not measured here**, and the exponent
is not assumed to carry over. `stream-power.md` states the qualitative version — a carved step in
uniform `K` is something the solver erases — and `river-networks.md` repeats it for channels.

## Sparse drawing to dense field: it is a linear solve

A drawing gives you values on a measure-zero set and you need a value everywhere. That is an
interpolation problem with a classical answer, and [hnaidi2010] §4.2 is the terrain-specific
statement of it. Three equations, by order:

| order | equation | what it says |
|---|---|---|
| 0 | `F = F` (identification) | this cell *is* the drawn value |
| 1 | `∇F = G` (gradient) | the surface leaves the curve at this slope, in this direction |
| 2 | `ΔF = 0` (Laplace) | everywhere else, be as smooth as possible |

Solved together as one over-constrained system by Jacobi relaxation inside a multigrid, at
`5(l − i)` iterations on level `i` [hnaidi2010] §5.2 — the same schedule [orzan2008] uses for
diffusion curves, which is where the method comes from.

**Why not Poisson.** [orzan2008] §3.2.2 solves `ΔI = div w`, and that is the right formulation
for images. [hnaidi2010] §4.2 rejects it for terrain, explicitly and for two reasons worth
repeating because they are not obvious: taking the divergence of the gradient field "induces the
loose of the gradient direction", and a Poisson equation with a null gradient constraint
degenerates to Laplace, "and thus forbids the creation of horizontal angle constraints". A
horizontal angle constraint is how you draw a **hill** — a curve whose neighbourhood is flat.
Poisson cannot express it. That is a real, checkable reason to prefer a first-order gradient
equation over a second-order source term.

**Why not biharmonic.** The other obvious upgrade is a thin plate, `Δ²h = 0`, which is C1 at the
constraint instead of merely C0. Measured on a 65×65 domain with one drawn unit-height line, both
systems assembled densely and solved exactly (`constraint_solvers.py` §1):

| | height lost in the first cell off the line | domain above 1% of the constraint | min over domain |
|---|---|---|---|
| Laplace, membrane | **4.20%** | 92.0% | +0.000000 |
| biharmonic, clamped plate | **0.26%** | 79.9% | −0.000022 |

The membrane sheds **16.5×** as much height in the first cell. That is the crease, and it is the
whole reason to use the lower-order operator: **a ridge line is a crease, and a membrane makes
creases for free.** A plate passes smoothly through the drawn line, which is what you want for a
hilltop and wrong for an arête. [hnaidi2010]'s answer — stay second order, add a *gradient*
equation — gets both, because the gradient constraint sets the slope leaving the curve on each
side independently, and a crease is just two different slopes.

⚠️ **The textbook plate overshoot did not appear.** The clamped plate undershot the lowest
constraint value by 2.2×10⁻⁵ of the constraint height, which is nothing. Do not repeat the folk
claim that biharmonic interpolation rings badly; for this configuration it does not. The reason
to prefer Laplace here is the crease, not stability.

**Both are global.** A single drawn line moved 92% (Laplace) or 80% (plate) of the domain above
1% of its own height. [orzan2008] §3.2.4 names this directly — "any color value can influence any
pixel of the final image" — and gives the practical fix: solve coarsely over the whole domain,
then use that solution as **Dirichlet boundary conditions** around the window you refine at full
resolution. That is the tile-boundary recipe for an authoring tool that edits a planet, and it is
the reason a naive per-tile solve produces visible tile seams.

## Hard and soft is one number, and it costs you the edges

The user wants two different things at different times: "the ridge is *exactly* here" and "the
ridge is *roughly* here, make it look natural". [hnaidi2010] §5.2 makes that a single weight in
the relaxation, `F = αF_L + βF_G + (1 − α − β)F_I`:

| region | α (Laplace) | β (gradient) | effect |
|---|---|---|---|
| strict elevation constraint | 0 | 0 | pure identification — **hard**, interpolating |
| gradient constraint | 0.5 | 0.5 | satisfy both equations at once |
| everywhere else | 1 | 0 | pure smoothing |
| *softened* elevation constraint | > 0 | 0 | **soft**, approximating |

And the paper is candid about the price: setting `α > 0` means "the solution will be smoother.
But this breaks edges on features". **A soft constraint is not a hard constraint with tolerance;
it is a hard constraint with its crease rounded off.** If the drawn thing is a ridge or a cliff,
softening it removes the feature you drew. Soften the *noise* parameters, soften the gradient
magnitude, and keep the elevation hard.

The corresponding move at the raster level is a constraint **band** rather than a constraint
line. [orzan2008] §3.2.1 displaces the value sources a distance `d` normal to the curve —
`d = 3` pixels in their implementation — and leaves only the gradient constraint on the curve
itself, so the two sides do not collide in the rasteriser and the sharp transition survives.
Where curves are close or highly curved the sources still overlap and a stencil test discards
them, leaving the gradient alone to dictate the transition. [hnaidi2010] §4.1 solves the same
collision the other way for gradients, which cannot be averaged because two crossing curves can
demand antagonistic directions: **leave the intersection empty and Laplace-diffuse the hole
shut**. Both are worth knowing; the second generalises better, because it needs no rule about
which constraint wins.

## The boundary of the edited region is where these tools visibly fail

An edit has a support. Outside it the terrain is untouched; inside it the terrain is the user's.
The ring between them is where every sketch-based tool is judged, and it is a two-line fix that
is routinely skipped.

[gain2009] eq. (1) is the canonical form: weight the deformation by

```
W(a) = (a^2 - 1)^2 ,   a = distance from the feature / distance to the boundary
```

described in the paper as "full weighting on the shadow tapering to zero at the boundary", and
claimed C1. Measured on a 40 m edit with a 32-cell support (`constraint_solvers.py` §5):

| falloff | `w` at the boundary | slope step at the seam |
|---|---|---|
| hard cut | 1.000 | **40.000 m/cell** |
| linear, `1 − a` | 0.000 | **1.250 m/cell** |
| smoothstep, `1 − (3a² − 2a³)` | 0.000 | 0.002 m/cell |
| [gain2009] `(a² − 1)²` | 0.000 | 0.002 m/cell |

A hard cut puts the entire 40 m into one cell. A **linear** falloff — the one people reach for
because it obviously goes to zero — leaves a 1.25 m/cell slope discontinuity, which is a visible
ring under any lighting and a spurious break line to every slope-based mask in
`terrain-analysis-masks.md`. The two C1 forms leave 0.002 m/cell, which is the
finite-difference floor of the measurement and not a real step. Note also that the quartic and a
plain smoothstep differ by only 0.0625 at the half-radius: **what matters is that the weight is
C1, not which C1 weight you pick.**

Three further boundary facts worth having, each from a paper that hit the problem:

- **Compact support must be exact.** [genevaux2013] §7 defines `w(p) = 0` wherever
  `d(p)² ≥ r²`. A Gaussian falloff has no such radius; its tail is small but never zero, so an
  edit "here" perturbs the terrain everywhere and no cache in `node-graph-runtime.md` can bound
  the dirty region. Use a polynomial with a real support, not a Gaussian.
- **Contract the support with the frequency.** [gain2009] §4 scales the boundary inward per
  smoothness level, `B_i = (φ_i/φ_0)·B_0`, so coarse shape is blended over a wide ring and fine
  detail over a narrow one. One radius for all frequencies gives you either a smudged silhouette
  or a hard detail edge, and you cannot have neither.
- **The ends of a curve are a boundary too.** [gain2009] §4 truncates the silhouette by the
  filter width at each end and fits a C1 blend into the terrain there, because there is otherwise
  no guarantee the drawn curve's endpoint touches the ground it lands on. A drawn ridge that
  simply stops is the single most common artefact in this class of tool.

## Constrain the inputs, not the output

The reason "impose after" wins the fidelity column and still looks pasted on is that it constrains
the *wrong object*. A height is an output of the erosion model; forcing an output leaves the model
disagreeing with it everywhere. The two papers here that ran an actual simulation both constrain
**inputs** instead:

- [stava2008] §8 lists its entire editing vocabulary: "add spring, dry, evaporate, rain, add
  obstacle of easy-to-erode material". Not one of those is a height. The user edits water and
  material; the erosion produces the height; the result is consistent by construction, at 20 fps
  on 2048×1024 with four layers.
- [genevaux2013] §8 has the user sketch rivers, river mouths and terrain- and river-slope maps —
  two constraint functions in two minutes, per its fig. 19 — and then states the guarantee that
  makes the approach work: "Independently on the quality of the user input, our approach will
  lead to a hydrographically correct river network."

That sentence is the design target. **The user should not be able to draw something physically
impossible, because the drawing is not the answer — it is a term in the equation that produces
the answer.** In this skill's pipeline the terms available to be drawn are named already: uplift
`U` (`tectonic-uplift.md`, which prescribes a distance field from a spline — computed by
`mask-operators.md`), erodibility `K` as a lithology (`stratigraphy-and-lithology.md`), and rain
and water sources (`hydraulic-erosion.md`). A drawn ridge painted into `U` and left to erode is a
ridge with valleys on it. A drawn ridge stamped onto the output is a shape.

The honest limit: none of this reproduces the *exact* line the user drew. If exactness is the
requirement — a river must pass through this village — you are back to imposing after, and
`river-networks.md` owns the carve and the monotonicity pass that makes it survive contact with
flow routing.

## Crossovers

- **Before or after the erosion pass** flips at `σ ≥ √(2DT/3)` for the diffusion term. At
  `D = 1`, `T = 40` that is 5.2 cells; below it the sim eats the feature.
- **Laplace or biharmonic** flips on whether the drawn feature is a *crease*. Ridges, cliffs and
  riverbanks: Laplace, which sheds 16.5× more height in the first cell. Hilltops and domes:
  either, and the plate is smoother.
- **Hard or soft constraint** flips on whether the feature has an edge. Elevation on a ridge:
  hard (`α = 0`). Noise amplitude, roughness, gradient magnitude: soft.
- **Per-step projection or not**: never, on these measurements — not on cost (21% of a step) but
  on the 88.3 curvature spike it builds at its own mask edge.
- **Global solve or windowed solve** flips on domain size. One drawn line moves 92% of a 65×65
  domain; past the size where a full-resolution solve fits, use [orzan2008] §3.2.4's coarse solve
  as Dirichlet data for the window.
- **Curve primitive or painted mask** flips on whether the user needs to re-edit. [hnaidi2010] §6
  notes the difference against [gain2009] plainly: the sketching system's edits are "incrementally
  edited but not stored", while a vector representation survives — 59 curves in 2.89 kB, and a
  canyon that took under 3 minutes to sketch and 45 minutes to refine.

## Where this sits in the pipeline

Authoring time, on both sides of erosion. The interpolation runs before anything else and
produces a heightfield or a set of constraint images; the falloff-weighted composite runs after
the solver. Consumes distance fields from `mask-operators.md`. Feeds `stream-power.md` and
`hydraulic-erosion.md` when the constraint goes in as `U`, `K` or water. Hands the finished
surface to `terrain-analysis-masks.md`, which will faithfully report every seam you left.

**What this document is not.** This skill excludes learned and example-based synthesis, so the
branch that takes a sketched feature map plus an exemplar DEM and stitches patches — Zhou, Sun,
Turk & Rehg (2007), *Terrain synthesis from digital elevation models* — is out of scope here. It
is named because [hnaidi2010] §2 and [gain2009] §2 both position against it and a reader will
meet it immediately; **no openable copy of it was reached for this document**, so nothing is
claimed about its contents beyond the one-line characterisation those two papers give it.
Constraint-based authoring, which is what is above, is not part of that exclusion.

## How this fails, and what it looks like

| Symptom | Mechanism | Fix |
|---|---|---|
| The drawn ridge is gone after the erosion pass | It was an initial condition and its width is under the diffusion length; a 4-cell ridge keeps 18.8% of its relief in 200 steps | Impose after, or widen it: half-life goes as σ², so `σ ≥ √(2DT/3)` |
| A thin drawn crease vanishes but a broad drawn massif survives, on the same terrain | Same law; 2 cells is half gone in 30 steps, 16 cells in 1920 | Not a bug. Report the survival estimate to the user at draw time |
| A wall or trench appears at the edge of the constrained region | A per-step projection through a hard-edged mask; curvature 88.3 against 0.69 for the free field | Do not project per step. If you must, feather the mask and accept the softened edge |
| The constraint is still "costing" simulation after hundreds of steps | Per-step projection reaches a steady flux, not a fixed point — 19% of the step-1 work at step 200 | Constrain an input instead (`U`, `K`, water), which the solver does not fight |
| Pits and standing water appear where a feature was stamped in | A hard-edged stamp dams the drainage: 28 interior pits against a control of 15 | C1 falloff on a compact support, and re-run depression handling (`flow-routing.md`) |
| A visible ring at the edge of every edit | Linear falloff — C0 but not C1, leaving a 1.25 m/cell slope step on a 40 m edit over 32 cells | `w(a) = (a² − 1)²` [gain2009] eq. (1), or any C1 weight |
| A step you can see the cell boundary of | Hard cut: the whole 40 m in one cell | As above |
| Editing "here" invalidates the cache everywhere | Gaussian falloff has no support radius | Polynomial weight with `w = 0` beyond `r` [genevaux2013] §7 |
| Coarse shape smudged, or fine detail with a hard edge, and no radius fixes both | One blend radius used for every frequency | Contract the support per level, `B_i = (φ_i/φ_0)·B_0` [gain2009] §4 |
| A drawn ridge line comes out as a smooth ridge with no crest | Biharmonic or plate interpolation, which passes through the constraint; or a softened elevation constraint, `α > 0`, which "breaks edges on features" | Laplace plus a gradient equation, elevation constraints hard at `α = 0` [hnaidi2010] §5.2 |
| A drawn hilltop comes out with a crease along the curve | Elevation constraint with no angle constraint — the membrane creases by default | Add the horizontal angle constraint; this is the case Poisson cannot express [hnaidi2010] §4.2 |
| Two crossing feature curves produce a spike or a smear at the junction | Antagonistic gradient directions averaged | Leave the intersection empty and Laplace-diffuse the hole [hnaidi2010] §4.1 fig. 9 |
| Sharp features dissolve where two curves run close together | Value sources rasterised onto the curve collide | Offset the sources normal to the curve (`d = 3` px) and keep the gradient on the curve [orzan2008] §3.2.1 |
| Tile seams in a windowed or streamed editor | The solve is global — one line moves 92% of the domain — so a per-tile solve has the wrong boundary data | Coarse global solve, then Dirichlet conditions around the window [orzan2008] §3.2.4 |
| A drawn curve's endpoint floats above or cuts into the terrain | The curve was not blended into the ground at its ends | Truncate by the filter width and fit a C1 join [gain2009] §4 |
| Sketched terrain reads as too rough or too smooth at every scale | Sketched noise variance taken literally; users are 5–50% out against real terrain | Fit an exponential decay through the sketched variance [gain2009] §4 |
| The edit is invisible in a hillshade but obvious in a slope or curvature mask | Analysis runs after the final write and sees every C0 seam | Fix the seam; analysis is not the place to hide it (`terrain-analysis-masks.md`) |
| The user drew a river that runs uphill | Not this document's problem | `river-networks.md`, downstream monotonicity |
