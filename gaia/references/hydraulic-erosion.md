---
type: Technique
title: Hydraulic erosion — droplet and pipe
description: "The two detail-scale water models: which one to run, the transcription details that decide whether each works, and the standing-water crossover between them."
tags: [generation, erosion, hydraulic, droplet, pipe, authoring-time]
status: draft
generated: { by: process:claude-code, at: 2026-09-02T00:00:00Z }
sources:
  - { id: mei2007, tier: P, locator: "READ IN FULL, and every reference below re-checked against the PDF. Section 3 opens 'The proposed hydraulic erosion model is decomposed into five steps' — 3.1 Water Increment, 3.2 Flow Simulation, 3.3 Erosion and Deposition, 3.4 Sediment Transportation, 3.5 Evaporation; section 3.2.1 eq. 2 is the flux update with pipe cross-section A and pipe length lX, eq. 4 the outflow scaling factor K = min(1, d1*lX*lY/(sum of fluxes)*dt); section 3.3 eq. 10 is the transport capacity C = Kc*sin(alpha)*|v|; the CFL statement dt*u <= lX and dt*v <= lY closes section 3.2.2" }
  - { id: stava2008, tier: P, locator: "§4 eq. (1), pipe cross-section fixed at C = l² and the outflow scale-down written as a guarded branch rather than Mei's min; §5 sediment slippage and the material-layer stack" }
  - { id: jako2011, tier: P, locator: "eq. (10) as numbered in the CESCG 2011 printing, which is the copy that was read: the capacity term scaled by the depth ramp lmax(d1), and the ramp definition (0 below zero depth, linear to 1 at Kdmax). Numbering may differ in the Eurographics Short Papers printing" }
  - { id: obrien1995, tier: P, locator: "the height-column fluid surface coupled by pipes on the head difference. NOT OPENED — the Computer Animation 1995 proceedings are not online free and the Berkeley author copy was unreachable from here, so no section, equation or page inside it is named" }
  - { id: beyer2015, tier: F, locator: "the per-droplet transport-capacity formulation, and the erosion-brush radius. NOT OPENED — the TUM mediatum copy did not serve the PDF and no other copy was reachable, so no section inside the thesis is named. A bachelor thesis and not peer review, hence F. What this document actually verified is the implementation that follows it, lague_erosion" }
  - { id: musgrave1989, tier: P, locator: "the original grid hydraulic and thermal erosion passes. NOT OPENED — SIGGRAPH 1989 sits behind the ACM paywall, which refused the download, so nothing inside it is named. The lineage claim was read instead in olsen2004 p. 5, which opens its erosion chapter with the sentence that thermal and hydraulic erosion 'were first described by Ken Musgrave et al in 1989' and cites this paper for both" }
  - { id: lague_erosion, tier: F, locator: "READ IN FULL, Assets/Scripts/Erosion.cs at github.com/SebLague/Hydraulic-Erosion. Defaults, lines 6-22: erosionRadius 3, inertia 0.05, sedimentCapacityFactor 4, minSedimentCapacity 0.01, erodeSpeed and depositSpeed 0.3, evaporateSpeed 0.01, gravity 4, maxDropletLifetime 30. Erode, lines 47-128: capacity at line 93, deposition at lines 98-106 with the source's own comment 'Deposition is not distributed over a radius (like erosion) so that it can fill small pits', brush-weighted erosion at lines 111-120. InitializeBrushIndices, lines 155-200: weight = 1 − sqrt(sqrDst)/radius inside a circular radius, normalised by weightSum. CAUTION line 124, speed = sqrt(speed^2 + deltaHeight*gravity), has the sign this document warns against — deltaHeight is negative downhill, so as published the droplets accelerate UPHILL. Cross-check defaults and brush weights against this file; do not copy line 124" }
  - { id: parker1982, tier: P, locator: "Abstract — coarse grains are intrinsically less mobile, so the pavement must be the mechanism that equalises mobility, by exposing proportionally more coarse grains to the flow; and the prediction that pavement is absent in most sand-bed streams. Abstract only; the full text was not reached" }
  - { id: gaea_erosion2, tier: F, locator: "READ, the Gaea documentation page Using Gaea, Erosion_2, at docs.gaea.app. §Sedimentary Control names the three classes in the docs' own words, 'Suspended Load, Bed Load and Coarse Sediments. These types represent increasing sediment mass and decreasing mobility', and states 'Each type has its own Discharge Angle, which controls the slope angle at which sediment begins to settle'; the sub-head §Coarse Sediments carries the sentence this document quotes, 'A discharge angle of 24 degrees for coarse sediments means they will be deposited only on or near such steep inclines; you will not see them on flat areas'. NOTE the page read gives each class an amount slider and a Discharge Angle but never uses the phrase 'Discharge Amount', and says nothing about the shipped presets, so this document's claim about preset ordering is NOT supported by the page read" }
---
# Hydraulic erosion — droplet and pipe

Two families, one lineage, and a taxonomy that is wrong in most reference tables. The virtual-pipe
abstraction — a fluid surface as height columns coupled by pipes driven by head difference —
is [obrien1995]; [mei2007] is where it becomes an *erosion* model, and [stava2008] extends the same
model. **Neither is a particle method.** The particle method everyone means has no canonical paper:
it descends from [musgrave1989] and reaches its modern form in [beyer2015], popularised through
[lague_erosion]. Citing Mei for "particle erosion" sends the implementer to the wrong algorithm.

For maps past roughly 50 km, neither belongs here at all — see `stream-power.md`.

## Use this

**Droplet erosion [beyer2015] for detail work**: cheap, art-directable, tunable by eye, and the
easiest to get looking good on a small map.

**The pipe model [mei2007] with Šťava's slippage and layers [stava2008] the moment water has to
persist** — lakes, ponding, deltas, standing water of any kind. Droplet erosion has no water; it
has droplets, and they leave.

## The crossover, which is cells, standing water and simulated time

⚠️ **The governing quantity is cells, not kilometres.** A droplet's life is a fixed number of
steps — ~30–60 in the usual implementations — each advancing about one cell, so its reach is
`lifetime × cellSize`: **30–60 cells, at every extent**. Kilometre thresholds only work once you
say what a cell measures. At 1024 cells across 2 km (≈2 m/cell) that reach is 60–120 m — a small
valley. On the same grid across 100 km (≈100 m/cell) it is 3–6 km, which sounds large and is not:
it is still 3–6% of a domain whose trunk network spans the whole thing, so the droplet scratches
rather than carves.

The km bands below assume **1024–4096 cells across the domain** — ≈0.5–2 m/cell at the small end,
≈12–100 m/cell at the crossover. Re-derive them if your cell size is elsewhere; the cell column is
the one that transfers.

| Droplet reach vs domain | Map extent at 1024–4096 cells | Backbone | Because |
|---|---|---|---|
| Reach is valley-scale — tens of metres of terrain per droplet | < ~2 km | **Droplet** | The feature a droplet cuts is the feature you want at this cell size. |
| Reach still cuts real features, but water has to persist | ~2–50 km | **Pipe** | Standing water, deltas, lakes; GPU-native by design [mei2007]. |
| Reach is a few percent of a network spanning thousands of cells | > ~50 km | Stream power | The only one stable over geological time; see `stream-power.md`. |

The failure mode of choosing wrong is diagnostic, not subtle: droplet erosion on a large map
produces **scratches instead of valleys**, and stream power on a 500 m map produces **nothing**,
because there is no drainage area worth speaking of.

## Droplet: the asymmetry that is the whole method

One droplet carries `pos`, `dir`, `speed`, `water`, `sediment` across its whole life; the loop
below is one step of it, and it dies at `lifetime` steps, off the map, or on `|dir| → 0`.
Heights are sampled bilinearly, so `pos` is continuous and `h(p)` interpolates four cells.

```
grad     = bilinearGradient(map, pos)              # ∂h/∂x, ∂h/∂y at pos
dir      = normalise(dir * inertia - grad * (1 - inertia))
pos_new  = pos + dir                               # |dir| = 1, so one cell per step
Δh       = h(pos_new) - h(pos)                     # negative downhill; THE sign that matters
capacity = max(-Δh, minSlope) * speed * water * capacityFactor
if sediment > capacity or Δh > 0:
    amount    = (Δh > 0) ? min(Δh, sediment) : (sediment - capacity) * depositSpeed
    sediment -= amount
    depositBilinear(map, pos, amount)              # 4 cells under the droplet
else:
    amount    = min((capacity - sediment) * erodeSpeed, -Δh)
    sediment += amount
    erodeWithBrush(map, pos, radius, amount)       # a disc of radius 2-4 cells
speed = sqrt(max(0, speed*speed + (-Δh) * gravity))
water *= (1 - evaporate)
pos    = pos_new
```

- **The two `sediment` lines are the state, and the commonest transcription error is to omit
  them.** Without them `sediment` is pinned at 0: `sediment > capacity` is never true and
  `min(Δh, sediment)` deposits nothing, so the droplet erodes on every step of every life and
  the speed update feeds that straight back into `capacity`. It does not sit there doing
  nothing — it diverges. Transcribed without them onto a 128² noise field of unit relief,
  20k droplets took the relief to ~10⁶⁸; with them, to 0.91.
- **Erosion is brush-wise; deposition is point-wise.** This asymmetry is the method. Erode through
  a single cell and you get one-pixel scratches instead of valleys; deposit through a brush and
  your rivers silt into mush. Getting it backwards is the commonest droplet bug there is. The
  reference implementation says so in its own comment: "Deposition is not distributed over a
  radius (like erosion) so that it can fill small pits" ([lague_erosion], `Erosion.cs` line 102),
  with deposit spread bilinearly over the four corners of the current cell and erosion spread over
  a circular brush weighted `1 − sqrt(d²)/radius` and normalised to sum to 1.
- **`min(Δh, sediment)` going uphill.** Deposit only enough to fill the pit just hit, never the
  whole load, or droplets bury the terrain in front of every rise.
- **`minSlope ≈ 0.01`** stops capacity collapsing to zero on flats, which would dump the entire
  load into one cell as a spike.
- **The sign in the speed update.** `Δh` is negative downhill, so speed rises with `+(-Δh)·gravity`.
  Written the other way, droplets accelerate uphill and the terrain grows tumours. ⚠️ **The most-read
  droplet implementation has it the other way.** [lague_erosion] `Erosion.cs` line 124 is
  `speed = sqrt(speed*speed + deltaHeight*gravity)`, and `deltaHeight` there is `newHeight −
  oldHeight`, negative downhill — so as published, that line slows a droplet falling and speeds up
  one climbing, and goes `NaN` once `deltaHeight·gravity < −speed²`. Take the defaults and the
  brush from that file; do not take line 124.
- **Inertia** blends gradient-following against going straight: high gives straighter, wider
  valleys; low gives gradient-hugging scratches.
- **Count** is the honest cost: roughly 0.5–2× the cell count for a visible effect, 4× for a mature
  look. A 4k map wants tens of millions of droplets.
- **On GPU, droplets race.** Overlapping brush footprints make naive parallelism
  non-deterministic and lose deposits. Accumulate `Δh` into a separate buffer with atomics and
  apply in a second pass; contention is low because droplets spread out fast.

## Pipe: the scaling step, which makes NaN twice

Every symbol, before the block. Grid: `lx`, `ly` are the spacings in x and y, `b` the bed
height, `d1` the water depth after the water-increment stage (Mei's subscripts number the
intermediate depths within one step), `_D` a neighbour in `D ∈ {L,R,T,B}`, `f_D` the outflow
flux through that pipe, `|v|` the flow speed reconstructed from the fluxes. Pipe: `A` its
cross-sectional area and `l` its length — **both constants**, not functions of depth; Šťava
fixes `A = l²` with `l` the cell spacing [stava2008], and the choice is a stability parameter,
not a free one (see **Time budget**). Erosion: `Kc` the sediment-capacity constant, `α` the
local tilt angle **in radians**, `α_min ≈ 0.05` its floor — ⚠️ radians too, and the mistake is quiet because `sin(0.05 rad) = 0.04998`, so a floor read as degrees is 57× too small and still looks like a small number — `lmax(d)` a ramp from 0 at zero depth to 1 at a
depth `Kdmax` [jako2011].

```
Δh_D = (b + d1) - (b_D + d1_D)                      # flow stage: head difference per pipe
f_D  = max(0, f_D + Δt * A * g * Δh_D / l)
Σf   = fL + fR + fT + fB
K    = (Σf > 0) ? min(1, (d1 * lx * ly) / (Σf * Δt)) : 1     # flow stage: THE scaling step
f_D *= K
C    = Kc * sin(max(α, α_min)) * |v| * lmax(d1)     # erosion-deposition: transport capacity
```

- **The outflow scaling is not optional, and the clamp as printed in the paper is itself the
  second NaN.** Both halves are real, and this document used to claim only the first.
  *Missing clamp*: a cell outputs more water than it contains in one step; depth goes negative,
  the velocity term divides by it, and the field is NaN within a few steps of the first
  offending cell. *Present but unguarded*: Mei's eq. (4) is `K = min(1, d1·lx·ly / (Σf·Δt))`
  [mei2007], and on a **dry cell** — `d1 = 0`, every flux 0 — that is `0/0`. On an 8×8 grid dry
  but for one wet cell, transcribed straight, `K` is NaN in 63 of 64 cells at step 0 and the
  depth field is entirely NaN after one step. ⚠️ **This one hides in a CPU prototype**, which is
  why it survives to the port: Python's `min(1, NaN)` returns `1` (it keeps the first argument,
  because `NaN < 1` is false) — but `min(NaN, 1)` returns `NaN`, `np.minimum` propagates either
  way, and GLSL and HLSL leave `min` on NaN undefined. Argument order, not semantics. Guard the
  denominator instead of trusting `min`: the branch form above is Šťava's own [stava2008], which
  scales down only *if* the outflow volume exceeds the water in the column and so never divides
  by zero. With the guard, the same transcription runs at every `Δt` tested from `C = 0.2` to
  `C = 20` with no NaN, `min depth = -0.000000` and mass drift ≤ 1.1e-16 — which is the
  positivity property, and it really is unconditional. [mei2007] motivates `K` as a positivity
  requirement and reports no failure-iteration count — the "about twenty iterations" figure that
  circulates (and that this document used to carry) is folklore, so do not plan a test around it.
- **`lmax(d1)`**, a soft ramp on shallow water, scales capacity down in a thin film. Without it
  a millimetre of water on a steep slope carves like a river. ⚠️ **It is Jákó's, eq. (10)**
  [jako2011], not Šťava's — Šťava's capacity (eq. 2) is `|v|·Kc·sin α`, unramped, and this
  document previously misattributed it. Mei's original omits it too, and it shows.
- **`α_min`** guards `sin α → 0` on flats. With capacity exactly zero all sediment dumps at once
  and you get a hard rim around every flat.
- **The 4-pipe stencil is anisotropic**, more so than D8, which at least has diagonals. Flow down a
  diagonal staircases and channels drift toward the axes over long runs. The fix is 8 pipes with a
  per-pipe length (`cellSize` cardinal, `cellSize·√2` diagonal) in the `Δh/l` term, and a velocity
  field summing all eight fluxes componentwise.
- **Sediment advection is semi-Lagrangian**: unconditionally stable, diffusive, so sediment smears.
  Usually acceptable; MacCormack or BFECC costs one extra advection if it is not.
- **Double-buffer everything**, or the result depends on traversal order and stops being
  deterministic under threading.

**Šťava's three additions over Mei, in value order** [stava2008]: sediment slippage — a thermal
pass restricted to the deposited layer (`thermal-and-aeolian-erosion.md`), which is the single
biggest visual improvement, because plain Mei builds vertical sediment walls no material would
support; **material layers**, bedrock under regolith with different **erodibility** `Ke` — spelled out
because `K` in the pipe code above is Mei's outflow clamp, a different quantity entirely, and
`K` elsewhere in this skill is stream power's erodibility — which buys the
rock-outcrop-above-scree look for free; and **ghost-cell boundaries** — a boundary cell holds a
copy of its neighbour, giving free-slip `v·n = 0` — where Mei zeroes the outflow flux on edge
cells instead. Both are explicit; they are not the same wall.

**What it beats.** *Mei alone* [mei2007] — correct and GPU-native, but the sediment walls and the
full-capacity thin film are visible, and the fixes are one pass [stava2008] and one factor on
capacity [jako2011] respectively. *Musgrave's original grid
model* [musgrave1989] — the ancestor of both families and the origin of the thermal pass; superseded
as an erosion model, still the correct citation for the lineage. *Lague's implementation*
[lague_erosion] — no canonical paper; it follows [beyer2015] and is the code most people have
actually read, which makes it the useful cross-check on brush weights and defaults, not a source
for the method — and not on the speed update, whose sign it gets wrong (above). It is also the only
member of the droplet lineage this repository has actually been able to open: Beyer's thesis and
Musgrave's paper both defeated it. *Thermal erosion alone* — relaxes what is there; it cuts nothing and moves no water.

**Time budget.** Both are authoring-time. Droplet cost is droplet count × lifetime, decoupled from
resolution, so it is the one you can dial down to interact with; pipe cost is a fixed number of
full-grid passes per step with `Δt` bounded by `Δt·|v| < cellSize` — Mei's own stated CFL
[mei2007] — **and by the pipe stencil's own signal speed `sqrt(g·A/l)`**, which with `A` and `l`
constant does not move with depth at all: `shallow-water.md` owns that bound and the reason the
familiar `sqrt(g·h)` is not it here. So it is the one that maps onto
a compute shader and the one to pick if the tool must show the erosion progressing. Neither is a
per-frame operation at authoring resolution. If velocity spikes, clamp it rather than reducing
`Δt` globally — the spike is almost always one bad cell.

**Order in the graph: hydraulic first, thermal after.** Hydraulic over-steepens and thermal
relaxes; reversed, the hydraulic pass re-steepens what thermal fixed and the thermal pass was
wasted work.

## Grain classes: one capacity, one talus angle, and why that is not enough

Everything above carries **one** sediment field and **one** transport capacity, and the thermal
pass that follows it carries **one** angle of repose. Real transport does not work that way: silt,
gravel and boulders move by different mechanisms, start moving at different thresholds, and stop in
different places. Two landforms follow directly from that difference and cannot be produced by any
tuning of a single-class model.

⚠️ **No canonical source; standard practice is** to split the load into three classes ordered by
increasing mass and decreasing mobility, give each its own capacity constant and its own settling
threshold, and give each its own repose angle. The shipped example is Gaea's Erosion2
[gaea_erosion2]: *Suspended Load*, *Bed Load* and *Coarse Sediments* — the documentation's own
phrasing is that these "represent increasing sediment mass and decreasing mobility" — each with an
amount slider and its own **Discharge Angle**, "which controls the slope angle at which sediment
begins to settle". There is no paper for the heightfield formulation — it is a
practice, cited here from a tool's documentation and graded accordingly. The geomorphology
underneath it is not folklore, and one part of it is [parker1982].

**Armouring, which one class cannot do.** With a single class the bed never changes character:
erosion removes an undifferentiated material and the next step erodes it the same way. With
classes, the mobile fines leave first and a coarse lag concentrates at the surface, and that lag
then protects what is beneath it. [parker1982] is the canonical statement of why the coarse surface
exists at all: coarse grains are intrinsically less mobile than fine ones, so *something* must
nearly equalise mobility, and the pavement is that mechanism — it works by exposing proportionally
more coarse grains to the flow. Its falsifiable half is that pavement should be absent in most
sand-bed streams, which is also the authoring rule: **armouring is a gravel-bed phenomenon, so a
scene with no coarse class should not show it.** Visually this is the difference between a gully
that deepens without limit and one that stabilises on a stony floor.

**Fining downstream** falls out for free, the moment the settling thresholds differ: coarse drops
first, so a fan grades from blocks at its head to silt at its toe. ⚠️ The model earns that pattern
by *selective deposition only*. Real fining is also abrasion — grains wearing down as they travel —
which no heightfield model represents, so read the grading as a placement, not as a grain size.

**Per-class capacity.** The classes share one flow and not one budget. Compute the velocity field
once, then give each class its own capacity of the same shape as the single-class one — [mei2007]
eq. (10) with [jako2011]'s depth ramp — differing only in its constant:

```
for each class i:                       # |v|, alpha and d1 computed ONCE, outside this loop
    C_i = Kc_i * sin(max(alpha, alpha_min)) * |v| * lmax(d1)
    if s_i > C_i:  deposit (s_i - C_i) * depositSpeed_i    into layer i
    else:          erode   min((C_i - s_i) * erodeSpeed_i, available_i)
```

- **Order the `Kc_i`, do not tune them independently.** `Kc_susp > Kc_bed > Kc_coarse` is the whole
  content of "increasing mass, decreasing mobility"; three constants tuned freely will cross over
  somewhere in the domain and the classes stop meaning anything.
- **Erosion has to draw from a source that can run out.** A class can only be picked up if that
  grain size is present. Without an `available_i` term the coarse class manufactures boulders out
  of bedrock everywhere and armouring never happens — it is the same omission as the droplet loop
  never writing `sediment`, in a different place.
- **Settling is a threshold on slope, not a rate**, and its direction is the counter-intuitive
  part. Gaea documents a coarse discharge angle of 24° as meaning coarse material "will be
  deposited only on or near such steep inclines; you will not see them on flat areas"
  [gaea_erosion2]. That is not steep ground catching boulders — it is boulders never leaving the
  steep ground they started on, while the fines ride the flow out onto the flats. So the coarse
  class's angle is high *because* it is immobile, and reading it as "coarse settles last" gets the
  sign backwards and puts scree in the valley floor.
- **Do not assume the three angles are ordered.** They are independent authored controls, so
  nothing in the model forces `angle_susp < angle_bed < angle_coarse`; author each against the
  landform it is meant to place. ⚠️ This document used to add that Gaea's shipped presets do not
  order them monotonically, citing [gaea_erosion2]; the Erosion_2 documentation page says nothing
  about presets, so that half is **withdrawn as unsourced** rather than left looking checked.
- **Advect each class separately**, through the same semi-Lagrangian step. The diffusion that step
  already introduces now applies `k` times over, and it is what blurs a sharp fining gradient into
  a smooth one.

**Per-class repose is the payoff, and it is nearly free.** Šťava's sediment slippage [stava2008] is
a thermal pass restricted to the deposited layer; with classes it becomes `k` passes, each moving
only its **own** deposit layer against its **own** limit. ⚠️ They are **not** independent: each
pass measures slope on the *composite* surface, so a coarse layer that moves changes the slope the
fine pass then sees, and the order is a real choice. Run **coarse first** — the coarse layer is the
one that stops nearest where it started, so letting it settle before the mobile classes relax over
it matches the order the material actually arrives in, and it stops a fine apron being built on a
slope that the next pass removes.

Measured on co-located piles, sand at 32° under scree at 38°, flat bedrock, 64²: reading the
composite, the surface relaxes to **38.00°** and the two orders differ by **0.25 m**. The tempting
fix is to let each pass read only its own layer over bedrock — which does make the result exactly
order-independent, **0.000e+00 m** between orders — and the composite surface then stands at
**54.6°**, sixteen degrees steeper than any repose angle in the scene. There is no third option: a
pass that cannot see the other layers cannot respect their combined slope, and a pass that can is a
pass whose result depends on when it ran. Take the order dependence, fix the order, and put it in
the cache key. The exception is a stack that is **a splatmap rather than geometry** — nothing there
is rendered as a slope, so the exactness is free and worth having. Separated piles are unaffected
once their **runouts** stop overlapping, which is the condition, not the separation of their peaks:
at 32° and 38° with 12 m cones, centres 12 cells apart still differ by 0.38 m between orders, 16
cells by 0.016 m, and 24 cells or more by exactly 0.000. Beyond that each relaxes to exactly its
own limit (32.00° and 38.00° measured), and the trade
appears only where two classes overlap — which, since selective deposition is what puts them in the
same place, is wherever the feature you wanted is. `thermal-and-aeolian-erosion.md`'s calibration ranges are the numbers to
start from: dry sand 30–35°, gravel and scree 35–40°, unsourced there and unsourced here. The
visible consequence is that **a sand apron slumps to a gentle cone while a scree apron beside it
stands steeper, in the same frame, out of the same pass** — which is the single thing a one-angle
model cannot fake, because one angle means every deposit in the scene has the same profile.

This is the material-layer stack again: grain classes are layers distinguished by property
[stava2008] §5, and `stratigraphy-and-lithology.md` is the same idea applied to rock rather than to
sediment. The cost is honest and linear — `k` sediment fields, `k` advections, `k` capacity
evaluations, `k` slippage passes — against a flow solve that dominates the step, so three classes
cost far less than three times a single-class run. **Three is where the returns stop**: two gives
you armouring and a fining gradient, three gives you scree that behaves unlike sand, and a fourth
is a constant nobody can tune by eye.

## How this fails, and what it looks like

| Symptom | Mechanism | Fix |
|---|---|---|
| NaN spikes a few steps into the run | Pipe outflow exceeds the water in the cell; depth goes negative | The outflow scaling factor `K` in the flow stage [mei2007] |
| The *whole* field is NaN after one step, worst on a dry map | `K` transcribed as `min(1, d1·lx·ly/(Σf·Δt))`: on a dry cell that is `0/0` | Guard the denominator — scale only when `Σf > 0` [stava2008] |
| It ran in the Python prototype and NaNs on the GPU | Scalar `min(1, NaN)` returns 1; `np.minimum`, and `min` on NaN in GLSL/HLSL, do not | Same guard; never rely on `min` to absorb a NaN |
| Droplets erode forever and the terrain explodes | The droplet loop never writes `sediment`, so it can never reach the deposit branch | `sediment -= amount` on deposit, `+= amount` on erode |
| One-pixel scratches instead of valleys | Droplet erosion applied per-cell instead of through a brush | Erode through a disc of 2–4 cells |
| Rivers silted into mush | Deposition spread through a brush | Deposit bilinearly, 4 cells |
| The terrain grows tumours on the uphill side | Sign error in the speed update; droplets accelerate uphill | `speed² += (-Δh)·gravity` |
| An isolated spike where a droplet stopped | Capacity collapsed to zero on a flat | `minSlope ≈ 0.01` |
| Vertical walls of deposited sediment | No sediment slippage | A repose-angle pass on the deposit layer [stava2008] |
| A thin film carving like a river | Capacity not ramped by depth | The `lmax(d1)` ramp [jako2011] — not in Šťava, despite the usual attribution |
| A hard rim around every flat area | `sin α → 0`, so capacity is exactly zero | Clamp `sin α ≥ ~0.05` |
| Channels drifting toward the grid axes | 4-pipe cardinal-only stencil | 8 pipes with per-pipe length |
| Different result with threading enabled | In-place neighbour updates | Double-buffer |
| Deposits missing on GPU, non-repeatably | Droplet brush footprints racing | Accumulate with atomics, apply in a second pass |
| Scratches instead of valleys on a large map | A droplet reaches 30–60 cells whatever the cell measures; the network spans thousands | Change backbone: pipe, or stream power |
| The brief mentions lakes and there are none | Droplet erosion has no standing water | Pipe model |
