---
type: Technique
title: Stratigraphy and lithology — rock as a depth-varying K
description: "Authoring a stratigraphic column, giving it dip and strike, sampling it to K(x, y, z), and handing that to the erosion law you already run — with what layered K measurably does and does not produce."
tags: [generation, stratigraphy, lithology, erodibility, layers, authoring-time]
status: draft
generated: { by: process:claude-code, at: 2026-09-03T00:00:00Z }
sources:
  - { id: cordonnier2016, tier: P, locator: "§3.1 eq. 1 — dh(p)/dt = u(p) - k*A(p)^m*s(p)^n, the term k that this document makes a field; §4.3 Lake Overflow for the in-loop lake handling that stays unchanged" }
  - { id: benes2001, tier: P, locator: "§4 New Terrain Representation — the landscape as a 2D array of 1D layer arrays, a per-column properties array capped at MAX_LEVEL = 10, column height as the sum of layer heights, and the cost argument k*n^2 rather than n^3; §5 for thermal erosion run over that stack and for eroded material changing its own properties; §7 Fig. 3, a hard letter W buried under weak mud and exhumed unchanged" }
  - { id: mitchell2021, tier: P, locator: "§2.1 eq. (1), the stream-power law with K carrying units L^(1-2m) T^-1; §2.4 eq. (6), kinematic wave speed C_H = K*A^m*|dz/dx|^(n-1); §2.5 eq. (12), the dip-corrected C_H = K_W*A^m*|dz/dx|^n / (|dz/dx| - tan(phi)), with phi < 0 dipping upstream; Table 1 for the dips tested, -45 to +15 degrees" }
  - { id: forte2016, tier: P, locator: "Abstract — the three controls on a two-unit stratigraphy: erodibility contrast, the order of the units (hard over soft versus soft over hard), and contact orientation and dip angle; and the finding that steady-state denudation is unlikely to develop in horizontal to moderately tilted layers. Abstract only; the full text was not reached" }
  - { id: barnhart2018, tier: P, locator: "p. 1, Summary — the Lithology and LithoLayers classes, each rock type carrying multiple attributes, layers removed by erosion and added by deposition; and the two storage schemes, `event layers` versus `material layers`, with the memory/history trade stated" }
  - { id: strat_authoring, tier: F, locator: "no artefact: the composed recipe — an ordered bed list, alternating resistant and weak, jittered from a seed, sampled through a dip plane into K(x, y, z) and handed to an existing solver" }
  - { id: stava2008, tier: P, locator: "§5 the material-layer stack, bedrock under regolith with different erodibility Ke — the two-layer case this document generalises" }
---
# Stratigraphy and lithology — rock as a depth-varying K

Gaia already holds the opinion twice. `tectonic-uplift.md` states the mechanism — *"layered `K`
produces caprock, cuestas and mesas as outputs, where a terrace node quantises height and produces
contour lines on a model"* — and `stream-power.md` rejects the alternative in its own words. Neither
says how. This document is the operator: **rock enters every erosion law in this skill through
exactly one channel, the erodibility coefficient, and stratigraphy is that coefficient becoming a
function of depth as well as position.**

Nothing downstream changes. Stream power's `f = K·Δt·A^m/dist` [cordonnier2016] §3.1 eq. 1 already
reads `K` per cell; the pipe model's capacity constant already reads a per-layer erodibility
[stava2008] §5. What is missing is the thing that *supplies* them a value that depends on how deep
the surface has cut.

## Use this

**Author an ordered stratigraphic column, sample it to `K(x, y, z)` through a dip plane, and hand
the result to the erosion law you are already running** [strat_authoring]. The column is a list of
beds, each a thickness and an erodibility; the sample is one dot product, one floor and one table
lookup per cell per step:

```
# once, at authoring time
beds = [(thickness_0, K_0), (thickness_1, K_1), ...]      # resistant and weak alternating
period = sum(t for t, _ in beds)                          # the column repeats
d      = (cos(psi), sin(psi))                             # dip direction, psi = strike + 90 deg

# per cell, per erosion step, from the CURRENT surface height
s   = h[y][x] + tan(delta) * (d.x * x * cellSize + d.y * y * cellSize)   # stratigraphic height
u   = fmod(s - datum, period);  if u < 0: u += period
K   = lookup(beds, u)                                     # walk or prefix-sum table
```

Alternatives, and why each is worse:

- **A terrace or height-quantise node** — steps at absolute elevations, so they cut across valleys
  instead of following bed geometry; already rejected in `stream-power.md`.
- **A painted 2-D `K` mask** — right for faults and plutons (`tectonic-uplift.md`), useless for
  strata: it has no depth, so exhuming a bed changes nothing.
- **An explicit per-column layer stack** [benes2001] §4 — the correct structure, and more than you
  need while material is only being removed.
- **A voxel field** — `n³` memory for a problem that is `k·n²` [benes2001] §4.
- **Two layers, bedrock under regolith** [stava2008] §5 — the special case; generalising it to `k`
  beds is this document.

⚠️ **The crossover is deposition, not size.** Use the **implicit column** — the function above,
which stores nothing and is evaluated from `h` — for as long as the simulation only *removes*
rock. Switch to an **explicit per-column layer stack** [benes2001] §4 the moment material is put
**back**: deposited sediment is a new bed with its own erodibility, it exists only where it landed,
and no closed-form function of `(x, y, z)` describes it. That is the same boundary
`hydraulic-erosion.md` draws between droplet and pipe, for the same reason — the moment state has
to persist, a formula stops being enough.

## The column

A bed is a thickness and an erodibility. Everything else it might carry — a talus angle for the
thermal pass, a colour, a roughness — rides along and is looked up the same way; [barnhart2018]
p. 1 makes the point structurally, with each rock type holding arbitrary attributes.

| Knob | What it sets | Sane range |
|---|---|---|
| Bed thickness | The vertical spacing of scarps; the tread width of a cuesta, with dip | 1–200 m; below about one vertical cell it is invisible |
| Erodibility contrast `K_weak / K_hard` | How hard the scarp reads | 3–10×; past ~20× the weak bed stops holding any slope at all |
| Number of distinct beds | Whether the section reads as banded or as noise | 2–6, repeated; ten different beds read as one texture |
| Thickness jitter, from a seed | Whether the banding looks authored | ±20–30% of nominal |
| Dip, strike | See below | 0–30°; past ~45° beds read as vertical structure, not stratigraphy |

⚠️ **`K` is not a dimensionless dial and its units depend on `m`.** In the stream-power law
`K` carries units `L^(1−2m)·T^(−1)` [mitchell2021] §2.1 eq. (1). Change `m` from 0.5 to 0.45 and
every per-bed `K` in the column silently means something different, so a column tuned at one `m`
does not transfer to another. Author the **contrast** — a dimensionless ratio against a reference
`K` — and multiply, rather than typing absolute numbers per bed.

Order matters as much as contrast. [forte2016] finds hard-over-soft and soft-over-hard to be
genuinely different regimes rather than reflections of each other, alongside contrast and dip, and
reports that a landscape cutting horizontal-to-moderately-tilted layers of contrasting strength is
unlikely to reach steady-state denudation at all. Practically: **do not expect a layered run to
converge the way a uniform-`K` run does**, and do not tune it by waiting for erosion rates to
flatten out.

## Dip and strike

Give the column a plane and the beds tilt. With dip angle `δ` and dip direction azimuth `ψ` (the
strike is the horizontal line perpendicular to it), the stratigraphic height of a point is

```
s(x, y, z) = z + tan(delta) * (x*cos(psi) + y*sin(psi))
```

and everything else is unchanged: the bed index is `floor((s − datum) / period)` into the same
list. **This is the whole of dip.** Two multiplies, an add, a floor and a lookup — it costs
nothing next to the flow routing in the same step, and it is the single highest-value knob in the
column, because horizontal beds give concentric bands on every hill and a dipping column gives
cuestas, strike valleys and hogbacks.

⚠️ **Dip has a resolution constraint, and it is the one that bites.** A bed of thickness `T` dipping
at `δ` crops out across a map-plane width

```
w = T / sin(delta)
```

and if `w` is not several cells wide the bed cannot be expressed at all — it aliases into a
one-cell stripe that erosion cannot organise around. Measured (see below, same rig): 25 m beds at
10° give `w = 144 m` = **1.4 cells** on a 100 m grid and produce the **weakest** layered signal of
any run in the set; 100 m beds at the same 10° give `w = 576 m` = **5.8 cells** and produce the
**strongest**. The rule is `T ≥ 4·cellSize·sin(δ)` — steepen the dip and the beds must get thicker
in proportion, and a nearly vertical column needs beds as thick as the outcrop pattern you want to
see. This is the first thing to check when a dipped column looks like noise.

Dip is not only cosmetic; it changes the *rate* at which the pattern moves. A lithologic contact
migrates upstream at the kinematic wave speed [mitchell2021] §2.4 eq. (6),
`C_H = K·A^m·|dz/dx|^(n−1)`, which at `n = 1` is exactly `K·A^m` — **the same expression
`stream-power.md` gives for knickpoint celerity.** That is not a coincidence and it is worth
carrying: a contact and a knickpoint are the same kinematic object, so a resistant bed is a
knickpoint generator that never runs out. With dip, the contact's migration acquires a geometric
term [mitchell2021] §2.5 eq. (12):

```
C_H = K_W * A^m * |dz/dx|^n / ( |dz/dx| - tan(phi) )        # phi < 0 dips upstream
```

Beds dipping **upstream** (`φ < 0`) enlarge the denominator and **slow** contact migration; beds
dipping **downstream** speed it up. [mitchell2021] Table 1 works dips from −45° to +15°. The
authoring consequence is direct: dip the column *into* the drainage and the resistant beds hold
their scarps for longer, which is what a long-lived cliff band wants.

## Sampling: the two data structures

| | Implicit column | Explicit layer stack [benes2001] §4 |
|---|---|---|
| Storage | none — a function of `(x, y, h)` | `k` layers per column, `k·n²` total |
| Deposition | cannot represent it | a new layer, per column |
| Voids, caves, overhangs | no | yes — a layer with zero density [benes2001] §4 |
| Cost per lookup | one dot product, one floor | walk the column, or keep a running cursor |
| Rebuild on graph change | free | the stack is state; invalidation is real |

[benes2001] §4 is the graphics origin of the second column and states its own cost argument: the
structure has voxel expressiveness at `k·n²` rather than `n³`, "where `k` is the number of the
layers — this is usually much smaller". Their implementation caps `MAX_LEVEL` at ten. At 4096²
with ten layers of two 4-byte attributes that is about 1.3 GB, so the cap is not decoration; a
tool that lets a user deposit freely needs either a cap or a variable-length representation, and
[barnhart2018] p. 1 names the resulting choice exactly:

- **event layers** — one entry per time step, even when nothing was deposited. Keeps the transient
  history of erosion and deposition; grows without bound in the step count.
- **material layers** — one entry per contiguous run of the same material, regardless of age.
  "More memory efficient but does not record the transient dynamics of erosion and deposition."

**Take material layers unless something downstream reads the history.** In a terrain tool nothing
does: the mask stage wants what the rock *is*, not when it arrived.

One detail from [benes2001] §5 is easy to miss and worth stealing: when their model moves
material, it changes that material's properties — dense in place, loose once transported. In a
heightfield tool that is one line, and it is what stops a deposited apron behaving like the cliff
it fell off.

## What layered K measurably produces

Gaia asserts caprock, cuestas and mesas. Measured, **the assertion is half right, and the half
that fails is worth knowing.**

The model is the one `stream-power.md` prescribes — the implicit `O(N)` stack solve with `D·∇²h`
sub-cycled at `c = 0.225` — on a 128² grid at 100 m/cell, `U = 5·10⁻⁴ m/yr` with the domain edge
pinned, `D = 0.02 m²/yr`, `Δt = 2000 yr`, 1000 steps (2 Myr). Horizontal beds 25 m thick alternate
`K_hard = 5·10⁻⁶` and `K_soft = 2·10⁻⁵` — a 4× contrast. The **control is the same run with `K`
uniform at the geometric mean** `10⁻⁵`, and the bands scored anyway; without that control the
elevation–slope correlation alone produces a fake signal.

| Measure | Uniform control | Layered, 4× contrast |
|---|---|---|
| Mean slope, cells in resistant bands ÷ cells in weak bands | **1.010** | **1.597** |
| Slope by phase through one bed pair (resistant half first) | 0.290 0.295 0.293 0.299 0.292 · 0.290 0.291 0.292 0.285 0.296 | 0.340 0.376 0.353 0.377 0.315 · 0.220 0.153 0.189 0.216 0.197 |
| Trunk channel: share of total drop carried by resistant beds | 45.7% | **49.6%** |
| Trunk channel: share of channel length they occupy | 52.8% | **31.3%** |
| Relief concentration (drop share ÷ length share) | 0.86× | **1.58×** |
| Channel slope ratio, resistant ÷ weak | 0.75 | **2.16** |
| Surface area sitting in resistant beds | 0.499 | **0.497** |

Read the rows in order. The control is flat — the phase profile varies by 5% with no structure,
and relief concentration is 0.86×, i.e. nothing. The layered run puts **half the trunk's descent
into under a third of its length**, with a step in the phase profile that lands on the contact.
**Scarps are real, and they are an output.** So is the first half of Gaia's claim.

Two results cut against the naive reading, though:

⚠️ **The slope contrast under-reads the erodibility contrast, badly.** Equilibrium says
`S ∝ (U/K)^(1/n)`, so a 4× contrast in `K` at `n = 1` should give a 4× contrast in slope. Measured:
**2.16×**, and it does not improve with time — the same run to 4 Myr gives 2.12×, so this is the
converged answer, not a transient. The mechanism is [mitchell2021]'s premise: contacts migrate, and
erosion rates on either side adjust so that the two sides retreat *horizontally* together, which
means neither unit is at local equilibrium with its own `K`. If you tune a column by looking at
the result, **you will author roughly twice the contrast you think you did.** Start from the
contrast you want to see and expect to double it.

⚠️ **Stream power plus linear diffusion gives the riser and not the tread.** Surface area sitting
in resistant beds is **0.497** against the 0.5 the bed thicknesses alone predict — the resistant
beds do **not** hold more of the landscape's area. A mesa is a *flat top* held up by a caprock, and
producing one needs the scarp to retreat laterally while the top stays level, which is mass wasting
— the slope-limited pass and the failure model of `thermal-and-aeolian-erosion.md`, not incision.
So Gaia's sentence is right about cuestas and caprock scarps and **overstated about mesas**: layered
`K` is necessary for a mesa and does not produce one on its own. Run thermal after the layered
hydraulic pass with a **per-bed talus angle** — that is the second attribute the column carries,
and it is what turns a steep reach into a cliff with a scree apron.

[benes2001] §7 Fig. 3 is the same result from the other end: a hard letter buried under weak
material, exhumed by thermal erosion alone and left "unchanged". Differential erosion needs no
fluvial machinery. What it needs is a `K` that varies with depth.

## K moves under the solver, and the solver does not care

Layered `K` makes the incision coefficient **state-dependent**: `K` is read from the current
surface, so a cell that erodes through a contact changes its own coefficient mid-run. That is
exactly the shape of thing that breaks an implicit scheme's stability proof, and here it does not.

The reason is in the update itself. `stream-power.md`'s line is

```
h[i] = (h[i] + U[i]*Δt + f * h[r]) / (1 + f)
```

which for any `f ≥ 0` is a **convex combination** of `h[i] + U[i]·Δt` and `h[r]` — weights
`1/(1+f)` and `f/(1+f)`, summing to one. So the new height is bracketed by those two values
whatever `f` is, and `f` is where `K` lives. No value of `K`, however large, and no jump in `K`
between steps can push a cell outside that bracket. **Unconditional stability survives a
state-dependent `K` because it never depended on `K` being constant.** Measured: the same solver
with a **1000× contrast** at `Δt = 20 000 yr` and no diffusion stays finite and bounded, which no
explicit form would.

What does degrade is **accuracy at contacts**, and it degrades quietly:

| | `Δt = 2000`, 1000 steps | `Δt = 500`, 4000 steps |
|---|---|---|
| Simulated time | 2 Myr | 2 Myr |
| Contact crossings | see the run register | |
| Depth cut past a contact using the bed above's `K` | | |
| Channel slope ratio, resistant ÷ weak | | |

A cell that starts a step in a resistant bed erodes the **whole step** at the resistant `K`, even
if it cut through the contact halfway. The error is one-sided — it always over-resists — and it
scales with how deep a cell can cut in one step against the bed thickness.

**The rule that follows is a ratio, not a timestep.** Keep the typical per-step incision below
roughly a fifth of the thinnest bed:

```
Δt_max ≈ 0.2 * min(bed thickness) / max(K * A^m * S^n)
```

At the parameters above that is comfortably satisfied and the two timesteps agree; halve the bed
thickness or double `K` and it is not. The diagnostic is cheap and belongs in the loop: count the
cells whose step crossed a contact, and the depth they cut on the far side. If that depth is a
noticeable fraction of the erosion budget, the column is finer than the timestep can resolve —
**thicken the beds or shorten the step; do not raise the contrast to compensate**, which is the
tempting move and makes the artefact worse.

**What it beats.** *A terrace node* — quantises absolute elevation, so its steps ignore the
drainage and cross valleys horizontally; it is a contour map, not a stratigraphy
(`stream-power.md`). *Displacing height at the contact* — the same failure `tectonic-uplift.md`
records for faults: a step nothing pins, relaxed away by the next pass. *A 2-D `K` mask* — correct
for faults and intrusions, blind to exhumation. *Noise added after erosion to fake banding* — has
no relationship to the drainage that would have exploited it. *A full voxel lithology* — `n³` for a
`k·n²` problem [benes2001] §4, and the extra expressiveness is caves, which a heightfield cannot
render anyway.

**Time budget.** Authoring-time, and effectively free. The sampling is a handful of arithmetic ops
per cell per step against a flow-routing pass that is orders of magnitude more expensive; adding
strata to an existing stream-power or pipe run is not measurably slower. The explicit layer stack
costs memory rather than time — `k·n²` [benes2001] §4 — and costs invalidation: the stack is
state, so a node-graph rebuild upstream of it cannot be cached the way a pure function can
(`node-graph-runtime.md`). Nothing here runs per frame; a runtime consumes the baked `K` field as
a material mask, not as a simulation input.

## How this fails, and what it looks like

| Symptom | Mechanism | Fix |
|---|---|---|
| Steps that cross valleys horizontally and follow no structure | A terrace or quantise node on absolute elevation | Layered `K` fed to the erosion law; the steps then follow bed geometry |
| Layers authored, and the result looks uniform | `K` sampled from a 2-D mask, so exhumation never changes it | Sample from `(x, y, h)`; `K` must depend on the current surface height |
| Bands visible on hillshade but no scarps in the channels | The `K` field built but never handed to the solver — painted as a colour map instead | It is the same `K` in `f = K·Δt·A^m/dist` [cordonnier2016] §3.1 eq. 1 |
| The scarps read far weaker than the authored contrast | Contact migration keeps neither unit at local equilibrium; measured slope contrast was 2.16× for a 4× `K` contrast | Author roughly twice the contrast you want to see [mitchell2021] |
| Concentric bands on every hill, like a contour map | Zero dip | Give the column dip and strike; even 5° breaks the concentricity |
| Cuestas that vanish after a long run | Beds dipping downstream, so contacts migrate fast | Dip into the drainage: `φ < 0` slows contact migration [mitchell2021] §2.5 eq. (12) |
| Cliff bands but no flat-topped mesas | Incision plus linear diffusion makes the riser, not the tread; measured area in resistant beds 0.497 versus 0.5 expected | Mass wasting after the hydraulic pass, with a per-bed talus angle (`thermal-and-aeolian-erosion.md`) |
| Thin beds erased entirely | Per-step incision comparable to bed thickness, so the bed is skipped in one update | `Δt ≤ 0.2·min(bed thickness) / max(K·A^m·S^n)`, or thicker beds |
| Resistant beds look thicker than authored | One-sided contact error: a cell cutting through a contact erodes the whole step at the bed above's `K` | Same ratio; instrument the crossing depth as a diagnostic |
| Erosion rates never settle, so the run never looks finished | Expected: layered stratigraphy is not steady-state in the way uniform `K` is [forte2016] | Stop on a morphology target, not on rate convergence |
| A column that looked right at `m = 0.5` is wrong at `m = 0.45` | `K` has units `L^(1−2m)·T^(−1)` [mitchell2021] §2.1 eq. (1) | Author dimensionless contrasts against a reference `K` |
| Deposited sediment erodes like bedrock | The implicit column is a function of `z` and knows nothing about what was put back | Explicit layer stack [benes2001] §4; deposit as a bed with its own `K`, and change its properties on transport [benes2001] §5 |
| Memory blows up after a long deposition run | `event layers` storage, one entry per step | `material layers` [barnhart2018] p. 1 — merge contiguous same-material runs |
