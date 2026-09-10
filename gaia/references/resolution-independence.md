---
type: Technique
title: Resolution independence — the same terrain at two sampling densities
description: "Which parameter of each erosion operator has to rescale with cell size and by what exponent, which invariances are only approximate, and which are not available at all."
tags: [generation, erosion, scaling, resolution, authoring-time]
status: draft
generated: { by: process:claude-code, at: 2026-09-06T00:00:00Z }
sources:
  - { id: ta_ops_filters, tier: F, locator: "§'Placement & masking' — the rule that a placement is authored in metres and never in cells, which is the authoring half of this document's first instruction; the same section's never-ship-a-binary-mask rule is a different claim and is not used here" }
  - { id: lague_erosion, tier: F, locator: "Erosion.cs lines 6-22, the shipped defaults that make up half the census below — erosionRadius 3, maxDropletLifetime 30, evaporateSpeed 0.01, each counted in cells or in steps and none of them in metres or years; lines 155-200 InitializeBrushIndices, where the brush weight 1 − sqrt(sqrDst)/radius is built over a radius measured in cells and normalised by weightSum" }
  - { id: mei2007, tier: P, locator: "§3.2.2, the CFL statement dt*u <= lX and dt*v <= lY; Table 1 with its row labels, where the timestep halves at every doubling of grid resolution — 0.002 s at 256² down to 0.000125 s at 4096²; §3.2 eq. (2) for the flux update whose pipe cross-section A and pipe length l are constants rather than functions of depth" }
  - { id: stava2008, tier: P, locator: "§4 eq. (1), the pipe cross-section fixed at C = l² with l the grid spacing — the one line that ties the scheme's signal speed to the cell size rather than to the water" }
  - { id: courant1928, tier: P, locator: "the hyperbolic case — the requirement that a difference scheme's numerical domain of dependence contain the physical one, which is why an explicit timestep is a function of cell size and an implicit one need not be" }
  - { id: explicit_diffusion_limit, tier: F, locator: "no artefact: the explicit FTCS bound dt <= dx²/(4D) in two dimensions, which is the sub-cycling law for every diffusive pass named here" }
  - { id: cordonnier2016, tier: P, locator: "§3.1 eq. 1, dh(p)/dt = u(p) − k*A(p)^m*s(p)^n with the paper's own sentence adopting n = 1 and m = 0.5; §5 eq. 2, the implicit update, whose unconditional stability is what frees the stream-power timestep from the cell size while the companion diffusion term stays bound to it" }
  - { id: montgomery1992, tier: P, locator: "eqs. (3) and (4), the channel-head criterion A*S² printed as 4000 m² and 500 m² upper and lower bounds — a threshold on a product containing a slope, so the number moves with the sampling density even though it is quoted in m²" }
  - { id: ocallaghan1984, tier: P, locator: "§3, the 8-neighbour steepest-descent rule: one receiver selected by a maximum over eight candidates, which is the operation that makes a drainage network a discontinuous function of the surface" }
  - { id: sauermann2001, tier: P, locator: "eq. 47 and Fig. 5 for the saturation length l_s and its magnitude, and p. 2 for the shear-velocity range 0.18 to 0.6 m/s the paper names as its own regime. Cited here only because l_s is a physical length, which makes it the sharpest resolution FLOOR in this document; the logistic-versus-linear question is thermal-and-aeolian-erosion.md's" }
  - { id: subcell_channel, tier: F, locator: "no artefact: the rule that a channel narrower than about two cells cannot be carved into a heightfield at all, and that below that width a river has to become a texture or a spline" }
  - { id: skinner2023, tier: P, locator: "§2.1 for the resample series — one 2 m DEM taken to every cell size from 2 to 30 m in 2 m steps plus a 50 m grid; §3.1 and Table 3 for which of fifteen metrics hold and the cell size at which each breaks down; §3.3 and Fig. 5 for the drainage-network result and its non-monotonic connectivity; §4.1 and the abstract for the fewer-but-larger-bursts finding; §1 for the three second-hand results quoted here as that paper reports them" }
  - { id: selfaffine_slope, tier: F, locator: "no artefact: a finite-difference slope over a lag dx on a self-affine surface of Hurst exponent H scales as dx^(H−1)" }
  - { id: grid_unit_transfer, tier: F, locator: "no artefact: K_grid = K_SI*dx^(2m−n) for E = K*A^m*S^n with heights in metres and horizontal distances counted in cells, and the observation that the exponent vanishes at n = 2m" }
---
# Resolution independence — the same terrain at two sampling densities

**Tier: authoring-time — the preview is where it is discovered and the build is where it is paid
for.** Change the output resolution and the terrain changes. That is the most common complaint
made against tools in this class, and most of it is not mysterious: a few parameters were stored
in cells, a few timesteps were chosen once, and one quantity — slope — cannot be stored in any
unit at all. This document says which is which, what each simulation family's parameters must do
when the cell size moves, and which invariances are not available at any price.

**Scope.** `node-graph-runtime.md` owns the runtime consequence — resolution belongs in the cache
key, so a preview and a build are different entries; `layering-filters-and-masks.md` owns the
authoring rule for filter radii and placements; `terrain-analysis-masks.md` owns the bare fact
that slope is resolution-dependent. What none of them carries, and this document owns, is the
**per-operator arithmetic** those three assume: which parameter of each family rescales, by what
exponent, and where the rescale stops working.

## Use this

**Store every parameter in world units, derive the grid-valued form at evaluation time, and prove
the result by refinement rather than by eye.** Four rules, in the order they bite:

1. **A parameter with a dimension is stored with it** — metres, metres per year, degrees, seconds
   [ta_ops_filters]. A radius in cells, a lifetime in steps, a pass count, a hop in cells and a
   timestep chosen once are five spellings of one bug.
2. **Derive the cell-valued form where the grid is known**: `radius_cells = radius_m/Δx`,
   `lifetime = reach_m/Δx`, `count = density_per_km² · area`, `passes = ceil(4.5·(r_m/Δx)²)`. The
   table below gives the exponent per family; none of them is 1 for every parameter, and a droplet
   count needs a further `1/Δx²` on top of that conversion for reasons the droplet section
   measures.
3. **A rate per step is not a rate.** Evaporation, erode and deposit fractions, a relaxation
   coefficient — anything applied once per iteration compounds a different number of times at
   every resolution, so re-express it per unit of simulated time or of path length.
4. **Test by refinement, not by preview.** Run at `Δx` and `Δx/2` with identical world-unit
   parameters, decimate the fine result onto the coarse grid, and report the residual **and its
   order under a further halving**. A residual that does not fall is two terrains, not a
   discretisation error. Then publish the **floor**: the smallest feature the pipeline claims to
   resolve, in metres.

⚠️ **Two of the six rows below cannot reach invariance at any price, and none of the other four
reaches it unconditionally** — one is statistical only, one needs a modelling change first, one
holds only if the relaxation runs to its fixed point, one only above a stated floor. State which
verdict you claim per operator: *invariant*, *invariant subject to a named condition*, or *not
available*. A pipeline advertising the first everywhere is making a claim this document shows to
be false.

**What it beats.** *Re-tuning per resolution* — the default, and it does work; it costs the user
the tuning twice and makes every preset resolution-specific, which is the complaint in its
original form. *"Scale every parameter by the cell ratio"* — right for a radius, wrong by a square
for a pass count, wrong in kind for a per-step rate, and wrong in direction for stream power's
`K`, whose exponent is `2m − n` and is exactly zero at the default `m` and `n`
[grid_unit_transfer]. *Normalising the domain to the unit square* — moves the bug rather than
removing it; a slope is still a difference across one cell, whatever the cell is called.
*Supersampling the graph and decimating* — pays the full fine-grid cost and still cannot repair a
node whose radius is stored in cells. *A reduced-resolution preview offered as the proof* — a
preview resembles the build in the band both grids carry and predicts it nowhere else, which is
the distinction two sections below.

## Three kinds of parameter, and only one of them is a parameter

**World units.** A length, a time, a rate, an angle. It transfers unchanged, and the corpus's
model of one written correctly is the thermal pass's per-neighbour limit,
`dLimit = tan(talus)·dist` with `dist` the neighbour's real run in metres
(`thermal-and-aeolian-erosion.md`). The angle of repose is a physical constant; the *drop* it
permits is a length that the grid supplies.

**Cells.** A bug [ta_ops_filters]. The runtime cannot repair it — it can only refuse to have one
(`node-graph-runtime.md`). The census:

| Parameter | Where it lives | As shipped | Invariant form |
|---|---|---|---|
| `erosionRadius = 3` | droplet brush [lague_erosion] | cells | `radius_m/Δx`, and see the floor below |
| `maxDropletLifetime = 30` | droplet [lague_erosion] | steps, ~one cell each | `reach_m/Δx` |
| `evaporateSpeed = 0.01` | droplet [lague_erosion] | per step | `e(Δx) = 1 − (1 − e₀)^(Δx/L₀)`, for `e₀` as authored at cell size `L₀` |
| `minSlope ≈ 0.01` | droplet capacity (`hydraulic-erosion.md`) | compared against a per-step **drop** | `minSlope·Δx` |
| saltation hop ≈ 5 | slab automaton (`thermal-and-aeolian-erosion.md`) | cells | `hop_m/Δx` |
| pass count | thermal, `passes ≈ 4.5·r²` in cells | passes | `ceil(4.5·(r_m/Δx)²)` to budget; stop on a measurement |
| `A = l²` | pipe cross-section [stava2008] | one cell's area | `A ≈ h·lx/2` (`shallow-water.md`) |
| `Δt` chosen once | pipe and shallow water [mei2007] | seconds | recomputed from `Δx` and the state |
| `L_sat` | aeolian continuum [sauermann2001] | **already metres** | none needed — it sets a floor instead |

**The third kind: dimensionless, and still resolution-dependent.** A slope, a curvature, a Froude
number — anything computed as a finite difference — and every threshold built on one, including
the `A·S²` channel head [montgomery1992]. It carries no unit, so the metres-not-cells rule never
reaches it, and there is no unit to move it into. Its value is set by the interval it was
differenced over, and that interval is the cell.

Measured, because the size of the effect is what decides whether it matters. A seeded fBm at
1024² by spectral synthesis with `P(k) ∝ k^−(2H+2)`, domain 10 km, box-averaged down by 2, 4, 8
and 16 so that every level is the *same surface* at a coarser sampling; mean `‖∇h‖` by central
differences in metres at each level:

| Hurst `H` | `Δx` = 9.77 m | 19.53 | 39.06 | 78.12 | 156.25 | fitted exponent | `H − 1` |
|---|---|---|---|---|---|---|---|
| 0.4 | 0.01188 | 0.00744 | 0.00484 | 0.00320 | 0.00210 | −0.622 | −0.60 |
| 0.6 | 0.00522 | 0.00380 | 0.00284 | 0.00213 | 0.00158 | −0.427 | −0.40 |
| 0.8 | 0.00245 | 0.00205 | 0.00173 | 0.00145 | 0.00120 | −0.254 | −0.20 |

Sixteen-fold coarsening reports slopes **5.7×, 3.3× and 2.0× smaller** on one unchanged surface.
The `Δx^(H−1)` law [selfaffine_slope] gets the direction and the rough magnitude; ⚠️ the fitted
exponents run **3.7%, 6.8% and 27% steeper** than predicted, the gap widens with `H`, and this
harness does not separate the box filter's own attenuation near Nyquist from the field's exponent
— so treat the mechanism as certain and the exponent as approximate, and do not compute a
correction factor from it. The published form of the same finding is
second-hand in [skinner2023] §1, which reports Hancock & Evans (2006) finding "a clear drop in the
area–slope relationship with larger grid cells" across 10–50 m grids and Finlayson & Montgomery
(2003) finding a major degradation of mean slope from 30 to 90 to 900 m.

## The scaling law, family by family

`Δx → Δx/2` throughout. "Cost" is the work for the same physical result, not for the same step
count.

| Family | What moves, and by what exponent | Cost of one halving | Verdict |
|---|---|---|---|
| Droplet | radius and lifetime `∝ 1/Δx`; count `∝ 1/Δx²`; the brush `∝ 1/Δx²` cells; per-step rates `∝ Δx`; the capacity floor `·Δx` | ×32 (×8 in steps) | approximate — statistical, never pointwise |
| Pipe / shallow water | `Δt ∝ Δx` at a fixed signal speed; `A = l²` ties that speed to the cell | ×8, or ×5.7 with `A = l²` | invariant only once `A ≈ h·lx/2` |
| Thermal | nothing in the rule; pass count `∝ 1/Δx²` | ×16 | invariant at the fixed point; the cost is quartic |
| Aeolian | hop `∝ 1/Δx`; slabs `∝ 1/Δx²`; `L_sat` is already metres | ×4, ×8 if the hop is marched | invariant above a floor near `L_sat` |
| Stream power | nothing in SI; `K_grid ∝ Δx^(2m−n)`; the `D` sub-cycles `∝ 1/Δx²` | ×4, ×16 for the diffusion half | **not available** — `S` and the network |
| Flow routing | `dist` is already metres; the `A·S²` threshold moves | ×4 | **not available** — the receiver is a discrete choice |

**Droplet.** A droplet's life is a fixed number of steps of about one cell, so its reach is
`lifetime × cellSize` (`hydraulic-erosion.md`) — 30 to 60 cells at every extent. Hold the reach in
metres and the lifetime scales as `1/Δx`. The count is less obvious than the other two: a density
per square kilometre is a *fixed* number of droplets, but the cut per droplet is not fixed. On the
loop of `hydraulic-erosion.md` at 128² and 256², one 2 km domain, every parameter here already in
world units, eroded volume fell **4.1–4.6× per halving at an unchanged count** across three seeds
and came back within ±30% at four times the droplets — so the count that holds the *result* goes
as `1/Δx²`, loosely, and droplet *steps* go as the cube law. ⚠️ **The work does not.** Erosion is
brush-wise [lague_erosion], so every erode step touches a disc of `radius_m/Δx` cells — 25 of them
at 128², 109 at 256² — and the work goes as `1/Δx⁵`: those same runs touched **32.1–33.0× the
brush cells** for 7.8–7.9× the steps. Over a 512² → 4096² span that is 32 768×, not 512×. Two
subtler parameters.
**The per-step rates compound.** `water *= (1 − evaporate)` runs `L/Δx` times
over a path of physical length `L`, so what is invariant is `ln(1 − e)/Δx`, and for small `e` the
fix is simply `e ∝ Δx` — the same argument applies unchanged to `erodeSpeed` and `depositSpeed`.
**And the capacity floor is not a slope.**
`capacity = max(−Δh, minSlope)·speed·water·capacityFactor` compares `minSlope` against `−Δh`, a
drop across one step, which is `S·Δx`; so the effective slope floor is `minSlope/Δx` and it
*rises* as you refine, biting on more of the map at every halving. Write `max(−Δh, minSlope·Δx)`
and the floor becomes the slope it is named for. One term is already invariant and worth knowing
about: `speed² += (−Δh)·gravity` telescopes to `g ×` the total drop along the path, a physical
quantity, so the speed update needs no rescale — exactly, as long as the `max(0, ·)` guarding it
never bites, and only approximately for a droplet that climbs far enough to be clamped.

⚠️ **Droplet paths are chaotic, so pointwise invariance is not on offer even after all of that.**
A path is a sequence of bilinear gradient reads; perturb the surface by one decimation and the
path diverges. What can be made invariant is the *statistics* — eroded volume, hypsometry, the
distribution of channel depths — and that is what the acceptance test must measure.

**Pipe and shallow water.** The explicit timestep is bound to the cell by the domain-of-dependence
requirement [courant1928], but *which* exponent you get is a consequence of a modelling choice
most implementations make without noticing. Three regimes, all from `dt_crit = 0.50·dx/√(g·A/l)`
(`shallow-water.md`'s measured form of the 2-D leapfrog bound):

- **`A` and `l` held as fixed numbers.** The signal speed `√(2gA/l)` does not move, so `Δt ∝ Δx`,
  steps `∝ 1/Δx`, cells `∝ 1/Δx²`, work `∝ 1/Δx³`. This is the regime [mei2007] Table 1 sits in —
  the timestep halves at every doubling of resolution, 0.002 s at 256² to 0.000125 s at 4096².
  The scheme is self-consistent and its wave speed is an authored constant unrelated to the water.
  ⚠️ The cube law is the *structural* expectation, and the one place this corpus has measured a
  refinement cost against it, that same table's 1612× collapse over a 16× range, fits an exponent
  of **2.66 rather than 3** (`hydraulic-erosion.md`). Budget from a measurement where you have
  one; use the exponent to know which way to look when the measurement disagrees.
- **Šťava's `A = l²` with `l` the grid spacing** [stava2008]. Now `A/l = Δx`, so
  `dt_crit = 0.50·√(Δx/g)` — the timestep falls only as `√Δx`, work goes as `1/Δx^2.5`, and, far
  worse, the *effective depth* `2A/l = 2Δx` halves with the cell. The grid sloshes at the speed of
  water two cells deep (`shallow-water.md`), so **refining the grid changes the wave speed**:
  halving `Δx` slows every wave by `√2` on the same scene. Nothing reports an error; the water is
  simply a different fluid.
- **`A ≈ h·lx/2`.** The signal speed becomes `√(g·h)`, the water's own, and the model is
  resolution-independent in its physics. `Δt ∝ Δx` again, work `∝ 1/Δx³`, and the bound must be
  recomputed each step because a filling pool raises `h`.

**Thermal.** The rule is already in world units — `dLimit = tan(talus)·dist` per neighbour, `c`
dimensionless — and its fixed point is exactly *no pair over its limit*
(`thermal-and-aeolian-erosion.md`). ⚠️ **What that makes invariant is the constraint, not the
surface.** "No pair over `tan(talus)·dist`", plus the exact volume conservation that document
measures, is stated entirely in world units and so transfers unchanged — but it admits many
surfaces, and which one a run lands on depends on the path it took there. That document also says
plainly that nothing in it *proves* the fixed point is reached, only that every configuration
tried reached it, and prescribes a measured stopping rule rather than a pass count. So: the
constraint is invariant, the surface is invariant to the extent the relaxation is run to
completion, and the **cost** of completion is not invariant at all. Material moves one cell per
pass, so the measured law is `passes ≈ 4.5·r²` in the feature radius **in cells**; hold the radius
in metres and the pass count goes as `1/Δx²`, on a grid that already grew as `1/Δx²`. That is one
of the two quartics here — the other is stream power's diffusion companion, below, for the same
reason: an explicit scheme whose stable step is bound by `Δx²`. It also converts straight into a
resolution-dependent *result* for anyone stopping on a pass budget: at a fixed pass count the
fraction of the relaxation achieved falls as `Δx²`, so the same "40 passes" leaves a knife-edge at
1 m that it removed at 8 m.

**Aeolian.** The slab automaton's angles and probabilities are dimensionless and transfer; its
saltation hop is quoted in cells (~5) and must become `hop_m/Δx`; a slab is a fixed height over a
cell's area, so the slab count to move a fixed volume goes as `1/Δx²`. The continuum chain is
better placed — law of the wall, cubic flux law and the Exner step are all in SI already — and it
is the one family whose limit is a *floor* rather than an exponent. `L_sat` is a physical length,
running from about 0.46 m upward across the transporting part of the 0.18–0.6 m/s band
[sauermann2001] names as its own regime (the reading `thermal-and-aeolian-erosion.md` establishes
against that paper's eq. 47), and it must span several cells or the relaxation is invisible and
the chain degenerates to `q = q_sat`. That degeneration is silent and not benign: without the
relaxation `‖∇·q⃗‖` grows as `1/λ` without bound, so the shortest wavelength the grid carries
drives the strongest bed change and **refining the grid makes the result worse**. With it, the
response saturates for every wavelength at or below `L_sat` and the model is
resolution-independent above the floor.

## Stream power, where the honest answer is no

`K` is not a dimensionless dial: with `[E] = L·T⁻¹` and `[A] = L²` it carries `L^(1−2m)·T⁻¹`, and
the discharge form is a different coefficient again, `L^(1−3m)·T^(m−1)` (`stream-power.md`,
`driver-fields.md`). ⚠️ **But that `L` is a metre, not a cell** — in SI, `K` has no cell-size
dependence to correct. The defect is narrower and much better hidden: terrain codes routinely mix
units, keeping heights in metres while counting horizontal distance in cells. Under that mixture
`A_grid = A/Δx²` and `S_grid = S·Δx`, so reproducing the same incision needs

```
K_grid = K_SI · Δx^(2m − n)        # heights in metres, horizontal lengths in CELLS
```

[grid_unit_transfer]. **The exponent is zero for any pair with `n = 2m` (`m/n = 0.5`), the defaults
among them** — a ray, not a point. `m = 0.5, n = 1` [cordonnier2016] §3.1 is one point on it;
`m = 0.75, n = 1.5` and `m = 1, n = 2` cancel too, both inside the `n` in 1–2 that `stream-power.md`
calls defensible at that `m/n`. That is why a `K` tuned at 512² appears to transfer to 4k and stops
the moment `m` or `n` leaves the ray. Confirmed at three cell sizes spanning 16×: on the ray the
grid-unit `K` is the same 3.0×10⁻⁵ at 10, 40 and 160 m; at `m = 0.45` it moves 32% over that range;
at `m = 0.35`, 2.30×; at `m = 0.5, n = 2` the exponent is −1 and it moves **16×**. Dimensional
bookkeeping rather than an experiment, worth the arithmetic only because the direction is the one
people get backwards: refining the grid needs a *larger* grid-unit `K` whenever `n > 2m`.

Fix the units and the model still is not resolution-independent, for two reasons that no rescale
reaches. `S` is a finite difference and falls as `Δx` grows on any real surface — the table above.
And `A` comes from a receiver chosen by a maximum over eight candidates [ocallaghan1984] §3, so a
near-tie flips a whole basin from one trunk to another and the drainage area at a point is a
**discontinuous** function of the surface.

**Measured, on a refinement series.** One physical domain, 10 km across; one initial surface — a
seeded `H = 0.6` fBm at 256² scaled to 10 m of relief, box-averaged down to 128² and 64² so that
all three runs start from the same ground; identical SI parameters `U = 5×10⁻⁴ m/yr`,
`K = 3×10⁻⁵ yr⁻¹`, `m = 0.5`, `n = 1`, `Δt = 1000 yr`, 800 steps; the solver of `stream-power.md`
transcribed literally, edge pinned at `h = 0` with `U = 0`, uplift applied to interior minima, the
`max(h[i], h[r])` guard on. Zero interior pits at every resolution.

| | 64², `Δx` = 156.25 m | 128², 78.12 m | 256², 39.06 m |
|---|---|---|---|
| relief | 106.23 m | 134.16 m | 163.19 m |
| mean elevation | 39.35 m | 49.08 m | 59.45 m |
| `log S` vs `log A` slope | −0.500 | −0.500 | −0.500 |
| RMS residual against the next finer grid, decimated | — | 17.14 m | 19.62 m |
| channel cells whose `A` differs from the finer grid's by over 2× | — | 41.5% | 62.0% |

The last two rows compare each grid with the *next finer* one: the residual box-averages the finer
heightfield onto the coarser grid and takes the RMS difference; the drainage-area row takes, for
each coarse cell with `A ≥ 50` cell areas, the **maximum** `A` inside the corresponding fine block
— the channel passing through it — and counts the cells where the two disagree by more than a
factor of two.

Three things to take from it, in ascending order of how uncomfortable they are.

**The residual does not fall.** 17.14 m then 19.62 m — 10.5% and 12.0% of the finest run's own
relief — while mean elevation climbs 25% and then 21% per halving. A converging discretisation
shrinks the residual across a refinement series; a flat one is the signature of two terrains, and
the acceptance test reports it without anybody having to look at a hillshade.

**It is not a transient.** All three columns are settled: taking 64² and 128² from 400 to 800
steps moved their means from 39.89 and 50.89 to 39.35 and 49.08, and carrying 256² on to 1200 and
1600 steps moved its mean 59.45 → 59.18 → 59.00, under a per cent against a 21% gap to the grid
beside it. ⚠️ Read the *mean* row for that, not the relief row: relief is `max − min`, an
extremum, and it wanders a few per cent as the network reorganises even after the mean has
settled — 163.19, 157.62 then 162.35 m across those same three step counts. The disagreement
between columns is the answer; the wander within one is not part of it.

**The check `stream-power.md` offers passes anyway** — −0.500 at all three resolutions. That is no
fault in the check. At steady state `S = (U/K)^(1/n)·A^(−m/n)`, so the regression *slope* is `−m/n`
whatever the cell size, and a uniform bias in `S` moves the intercept alone. It catches exactly
what it was offered for — wrong drainage area, wrong receiver distances, an unhandled depression —
and it cannot see a resolution change, because what it measures is invariant by construction.
⚠️ **Do not report it as evidence of resolution independence**: here it is the one number that
looks perfect at every resolution while the terrain grows a fifth taller at each halving.

The mechanism is that pure stream power carries **no length scale except the cell**:
`S ∝ A^(−m/n)`, so relief accumulates from the divide downward and keeps rising as the smallest
`A` the grid can carry — one cell's area — falls as `Δx²`. The companion term `D·∇²h`
[cordonnier2016] supplies one, and `stream-power.md` already says it is not optional: run it, size
`D` so the hillslope it creates is resolved at the **coarsest** grid shipped, and test that by
refinement rather than by assumption.

⚠️ **This document did not find a `D` that restores convergence, and reports the attempts rather
than a number.** At `D` = 0.5 and 2.0 m²/yr over **400** steps the residual stopped growing and
did not fall — 39.03 then 36.62 m at `D` = 0.5, and 25.13 then 23.05 m at `D` = 2.0, against
18.72 then 41.16 m with no diffusion at the same step count. Carried to **800** steps at
`D` = 2.0 it grew again, 30.39 then 34.98 m, and by then the slope–area exponent had left the
fluvial regime altogether — **−0.224, +0.077 and −0.596** across the three resolutions, against
−0.500 everywhere without diffusion. That configuration is diffusion-dominated and no longer tests
what it was set up to test, so no `D` from these runs is worth quoting: it would be a constant
with no regime attached. What holds without one is the mechanism above and the floor rule below —
size `D` from the hillslope length you want, check the length is resolved at the coarsest grid you
ship, and re-run the series.

⚠️ **The cost of the companion term is quartic where the incision term is quadratic.** The
explicit Laplacian is bound by `Δt ≤ Δx²/(4D)` [explicit_diffusion_limit], so its sub-cycle count
goes as `1/Δx²` while the implicit incision half stays free of `Δx` entirely [cordonnier2016] §5.
At `D` = 2.0 m²/yr, `Δt` = 1000 yr and a 0.9 safety factor, `ceil(D·Δt/(0.225·Δx²))` is 1, 2 and 6
sub-cycles at 156.25, 78.12 and 39.06 m — computed, not measured, and checkable in one line.

## What no rescale reaches

**Slope, and everything keyed on it.** Measured above, so every threshold carrying a slope — a
material selector, a talus mask, the `A·S²` channel head between 500 and 4000 m² [montgomery1992]
— moves with the sampling density. `A·S²` is the sharpest case, because it is quoted in m² and so
reads as a fixed physical quantity. It is not: only `S` carries a cell-size exponent — `A` is an
area in m² on either grid, and its own failure is the discontinuity above rather than a drift with
`Δx` — so with `S ∝ Δx^(H−1)` the *threshold constant* has to scale as `Δx^(2H−2)` to go on
selecting the same ground: at `H = 0.5` that is `1/Δx`, so coarsening by two **halves** it, the
direction nobody guesses. And `H` is a property of the terrain rather than of the tool, so no
coefficient a tool ships can carry it. State the resolution beside the threshold
(`terrain-analysis-masks.md`) and re-tune per level; that is the whole available fix.

**Network topology.** The receiver rule is a maximum over eight [ocallaghan1984], so the map from
heightfield to network is not continuous and no parameter makes it so. The published form is
[skinner2023] §3.3: across resamplings of one DEM, first-order stream counts fall steadily while
connectivity does not — the disparity between Shreve and Strahler counts comes from part of the
channel disconnecting from the main network, and that disconnection "was not consistent through
the resolutions, with some coarser resolutions displaying a better connected network than others."
Non-monotonic, on real ground, from one surface. This is also why the 41.5% and 62.0% drainage-area
figures in the table above are the honest headline and the slope–area check is not.

**The unresolved band.** Below about two cells a channel is not geometry at all [subcell_channel];
below several cells `L_sat` is invisible [sauermann2001]; below one cell a brush is a point and the
droplet's erosion asymmetry (`hydraulic-erosion.md`) is gone. These are not scaling laws but
**floors**, running in the opposite direction from every exponent above: they bound the *coarsest*
grid on which a claim of invariance can be made at all. Publish the floor with the claim.

**Per-realisation detail.** Droplet paths, slab moves, tie-breaks in a fill. [skinner2023] §1
reports Hancock et al. (2016) finding that random perturbations of a DEM left basin sediment yield
alone while strongly changing local patterns of hillslope erosion after 10 000 years — statistical
stability with pointwise divergence, the ceiling on what a stochastic operator can promise.

## A preview that predicts, and a preview that merely resembles

A preview **predicts** the build when every decision made at preview resolution has the same
outcome at build resolution: a threshold lands in the same place, a tuned slider is still tuned, a
mask selects the same ground. Formally, the preview is the build passed through a stated
decimation to a published tolerance. A preview **resembles** the build when it shares its
statistics and its character and nothing else. Both are legitimate products; only one lets a user
stop tuning, and the difference is invisible in a screenshot.

**The test that separates them** is the refinement test above, run at the preview's own
resolution: decimate the build onto the preview grid and subtract. If the residual lives in the
band the preview cannot carry — frequencies above its Nyquist — the preview predicts, and its
tolerance is that residual. If it lives at wavelengths *both* grids carry, the preview only
resembles, however similar it looks.

⚠️ **Prediction is available only for the resolved band, and some operators leak the unresolved
band into it.** A blur, a placement in metres, a slope mask on a feature many cells across: these
predict. A drainage divide does not, because `A` at a resolved point is decided by the finest
scale in the domain — that is the discontinuity above, not a tolerance that shrinks. So
`node-graph-runtime.md` states the requirement correctly and this is what meeting it costs: the
contract is **per operator**, and the operators that cannot meet it are exactly the ones listed
above as unavailable. Say which are which on the page, or the user discovers the boundary by
finding that a mask they placed carefully has moved.

## The acceptance test

What to measure before claiming a pipeline is resolution-independent. Six items; the first two are
what make it a test rather than a demonstration.

1. **A refinement series, at least three levels.** Identical world-unit parameters, one physical
   initial surface decimated down — never a fresh noise field per level, which changes the input
   and hides the effect. Decimate the finer result onto the coarser grid with a stated filter — a
   box average, which preserves mean elevation and therefore volume — and report the residual.
2. **The order, not the residual.** One pair proves nothing, and a small residual is not a pass.
   Report how the residual behaves *across* the series: **falling** is a consistent
   discretisation and the only result that supports the claim; **flat or growing** means the
   pipeline is producing a different terrain per resolution rather than one terrain sampled twice
   — the measurement above is flat, at 10–12% of relief, and that is a failure. ⚠️ The residual
   must be computed between *independent runs*, never between a build and a preview generated
   from it, which is the pipeline agreeing with itself.
3. **A per-quantity report, not a single number.** At minimum: relief and mean elevation;
   hypsometry as a distribution, not a mean; total eroded volume; the slope–area regression slope
   — *with* the note that it is invariant by construction and therefore weak here; and the
   fraction of channel cells whose drainage area disagrees with the finer grid's by more than a
   stated factor. The last one is the one that will fail, and reporting it is what makes the claim
   honest rather than selective.
4. **A parameter round-trip.** Tune a threshold at preview resolution, apply it at build
   resolution, and report the symmetric difference of the two masks as a fraction of area. This is
   the number the user actually experiences, and it is the one a residual in metres does not
   predict.
5. **The declared floor.** The smallest feature the pipeline claims to resolve, in metres, checked
   against every operator's characteristic length at the *coarsest* resolution shipped — brush
   radius, `L_sat`, saltation hop, hillslope length, channel width [subcell_channel]. Below the
   floor the claim is void, and saying so is cheaper than being found out.
6. **The measured cost exponent.** Wall clock against `1/Δx`, fitted, and compared with the
   predicted exponent from the table above. A mismatch is diagnostic: work rising as `1/Δx²` where
   the model predicts `1/Δx³` means a timestep that did not move, `1/Δx⁴` where `1/Δx²` was
   predicted means a pass count that did, and `1/Δx³` from a droplet pipeline where `1/Δx⁵` was
   predicted means a brush radius still counted in cells.

[skinner2023] is the closest thing in this bibliography to that test run in public — one 2 m DEM
resampled to every cell size from 2 to 30 m plus 50 m (§2.1), fifteen metrics each reported with
the cell size at which its pattern breaks down (§3.1, Table 3). Its §4.1 conclusion is the one to
carry into a tool: total sediment yield showed "little change" up to 22 m while the *behaviour*
producing it changed — the same total delivered in fewer, larger bursts. A headline metric that
holds is not evidence that the model is doing the same thing.

## How this fails, and what it looks like

| Symptom | Mechanism | Fix |
|---|---|---|
| Erosion detail is finer and weaker at every increase in resolution | Droplet reach is `lifetime × cellSize`, and the brush radius is in cells | `lifetime = reach_m/Δx`, `radius_cells = radius_m/Δx` |
| Droplets run out of water and dump their load early once the grid is refined | `evaporate` and the erode/deposit fractions are applied per *step*, and a path of the same physical length now takes `L/Δx` more of them | Re-express per unit path length; for small `e`, `e ∝ Δx` |
| Isolated deposit spikes appear on flats when the map is coarsened, and erosion goes slope-blind over much of it when the map is refined | `max(−Δh, minSlope)` floors a per-step **drop**, not a slope, so the effective slope floor is `minSlope/Δx` — nearly inert at coarse spacing, dominant at fine | `max(−Δh, minSlope·Δx)` |
| A droplet pass affordable at 512² misses its 4k wall-clock budget by orders of magnitude, with every parameter correctly in metres | Steps go as `1/Δx³`, but each erode step touches a brush of `radius_m/Δx` cells, so the work goes as `1/Δx⁵` — 32 768× over that span, not 512× | Budget `1/Δx⁵` for the droplet pass. Capping the brush in cells buys the time back and re-introduces the resolution dependence; declare it if you do |
| Halving the cell size makes the water slower and the sloshing period longer | `A = l²` with `l` the cell, so the model's effective depth is `2Δx` and its signal speed `√(2gΔx)` [stava2008] | `A ≈ h·lx/2`, or accept a fixed authored signal speed and say so |
| The pipe solve is stable at one resolution and explodes at the next | `Δt` chosen once; the bound is `0.50·dx/√(g·A/l)`, and `dx` moved — and if `A = l²`, so did `A/l` | Recompute per resolution, and per step wherever the celerity tracks depth [courant1928] |
| Ridges relax fully at 512 and stay knife-edged at 4k on the same pass budget | Thermal pass count goes as `4.5·(r_m/Δx)²` | Stop on a measured over-steep count, never a pass count |
| Dunes turn to noise as the grid is refined | `L_sat` no longer spans several cells, so the chain degenerates to `q = q_sat` and short wavelengths dominate `∇·q⃗` | Resolve `L_sat` [sauermann2001]; it is a floor, not a parameter |
| A `K` that transferred between resolutions stops transferring when `m` or `n` is changed | `K_grid = K_SI·Δx^(2m−n)`, and that exponent is zero for any pair with `n = 2m` (`m/n = 0.5`), the defaults among them | Store `K` in SI with `A` in m² and `dist` in metres [grid_unit_transfer] |
| Relief and mean elevation climb with every refinement, with no parameter changed | Pure stream power has no length scale but the cell, so relief accumulates from the smallest resolved `A` | Add `D·∇²h` [cordonnier2016] and resolve the hillslope it creates at the coarsest grid |
| The slope–area check passes at every resolution while the terrain plainly changes | The regression slope is `−m/n` at steady state whatever the cell size; a uniform `S` bias moves only the intercept | Keep the check for what it catches; test resolution by refinement residual and by `A` disagreement |
| A slope or `A·S²` threshold tuned at 1 m/px selects the wrong ground at 8 | Slope is a finite difference over `Δx`, `∝ Δx^(H−1)` [selfaffine_slope] | State the resolution beside the threshold; re-tune per level. No unit conversion exists |
| A basin drains to a different outlet at the coarser resolution, and a still coarser one agrees with the fine grid again | The receiver is a maximum over eight [ocallaghan1984]; connectivity is non-monotonic in cell size [skinner2023] | Not fixable — report the fraction of area affected, and keep divides away from authored content |
| A river present in the build is missing from the preview | Channel narrower than about two cells [subcell_channel] | Carry discharge as the truth and derive the channel; publish the floor |
| Total eroded volume matches across resolutions and the terrain does not | A headline metric holding while the behaviour changes — the same total in fewer, larger events [skinner2023] | Report a distribution, not a total; add the per-quantity list from the acceptance test |
| The preview matched, and the parameter still had to be re-tuned at build resolution | The preview resembles rather than predicts: the residual lives in a band both grids carry | Run the refinement test at the preview's resolution; publish the tolerance per operator |
