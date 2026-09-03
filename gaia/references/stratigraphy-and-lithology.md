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
# ANGLES ARE IN RADIANS FROM HERE DOWN. psi and delta are authored in degrees, so convert
# once at the boundary -- tan(30) is -6.405 and inverts the dip; tan(radians(30)) is 0.5774.
psi, delta = radians(strike + 90), radians(dip_degrees)
dx, dy = cos(psi), sin(psi)                               # dip direction

# per cell, per erosion step, from the CURRENT surface height
s   = h[y][x] + tan(delta) * (dx * x * cellSize + dy * y * cellSize)     # stratigraphic height
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
| Bed thickness | The vertical spacing of scarps; the outcrop width of a cuesta tread, with dip | 25–200 m measured below; the binding constraint is the outcrop width, not the thickness |
| Erodibility contrast `K_weak / K_hard` | How hard the scarp reads | 4× and 16× both measured below and both work; the rendered contrast comes out far below the authored one, so author high |
| Number of distinct beds | Whether the section reads as banded or as noise | 2–6, repeated; ten different beds read as one texture |
| Thickness jitter, from a seed | Whether the banding looks authored | ±20–30% of nominal |
| Dip, strike | See below | 0–30°; past ~45° beds read as vertical structure, not stratigraphy |

These ranges are calibration figures of the same kind as `tectonic-uplift.md`'s uplift rates — the
thickness and contrast columns are measured below, the rest are what works. No source is cited for
the table and none should be [strat_authoring].

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
w = T / tan(delta)        # T is the VERTICAL span the sampler above uses, not perpendicular thickness
```

⚠️ **`T` here is the *vertical* span the sampler uses, not the bed's perpendicular thickness, and
the two give different formulas.** The block above builds `s` by adding `tan δ · horizontal` to a
height, so a bed's `thickness` is a vertical interval of `s`. A vertical span `T` crops out over
`T/tan δ`; a perpendicular thickness `T⊥ = T·cos δ` crops out over `T⊥/sin δ` — the same distance,
written two ways, and mixing them costs a factor of `1/cos δ`. Measured against the sampler's own
output on a flat surface at 1 m cells: at 2° the two differ by 0.06%, at 10° by 1.5%, at 30° by
**15%** and at 60° by **2×**. An earlier draft used `T/sin δ` with the vertical `T`, which is why
this note exists — invisible at the shallow dips the results table quotes, and wrong at the top of
its own stated range.

and if `w` is not several cells wide the bed cannot be expressed at all — it aliases into a
one-cell stripe that erosion cannot organise around. Measured (see below, same rig): 25 m beds at
10° give `w = 144 m` = **1.4 cells** on a 100 m grid and produce the **weakest** layered signal of
any run in the set; 100 m beds at the same 10° give `w = 576 m` = **5.8 cells** and produce the
**strongest**. The rule is `T ≥ 4·cellSize·tan(δ)` — steepen the dip and the beds must get thicker
in proportion, and a nearly vertical column needs beds as thick as the outcrop pattern you want to
see. This is the first thing to check when a dipped column looks like noise.

⚠️ **That rule is scoped to dip and goes vacuous at `δ = 0`, where the same aliasing is at its
worst.** Horizontal beds do not escape it — they crop out across a *hillside*, and the width is
`T / tan(surface slope)`, which is the same expression with the surface's slope in place of the
dip. Measured for 25 m beds on a 100 m grid: **2.86 cells** on a 5° hillside, 1.42 on 10°, 0.69 on
20° and **0.43 on 30°** — well under the 1.4 cells that made the dipped case the weakest run in the
set. So the general statement is that a bed's visibility is set by the angle between the bedding
and the **surface**, not by the dip alone: `w = T / tan(angle between bedding and surface)`, and
`T ≥ 4·cellSize·tan(that angle)`. Dip is the case where the surface is flat and the bedding is not;
a hillside with horizontal beds is the same problem with the roles swapped, and it is the case a
mountainous scene actually hits.

Dip is not only cosmetic; it changes the *rate* at which the pattern moves. A lithologic contact
migrates upstream at the kinematic wave speed [mitchell2021] §2.4 eq. (6),
`C_H = K·A^m·|dz/dx|^(n−1)`, which at `n = 1` is exactly `K·A^m` — **the same expression
`stream-power.md` gives for knickpoint celerity.** That is not a coincidence and it is worth
carrying: a contact and a knickpoint are the same kinematic object, so a resistant bed is a
knickpoint generator that never runs out. With dip, the contact's migration acquires a geometric
term [mitchell2021] §2.5 eq. (12):

```
C_H = K_W * A^m * |dz/dx|^n / ( |dz/dx| - tan(phi) )        # phi < 0 dips upstream
# VALID ONLY FOR |dz/dx| > tan(phi). See the warning below: for phi > 0 this is
# singular at S = tan(phi) and NEGATIVE below it, which is most channel slopes.
```

⚠️ **The dip-corrected form has a pole, and downstream dip walks straight into it.** For `φ > 0`
(beds dipping downstream) the denominator `S − tan φ` vanishes at `S = tan φ` and goes negative
below it. At `φ = +15°`, `tan φ = 0.268` — steeper than almost every channel in a real domain — so
the expression returns a **negative celerity** at `S = 0.10`, `0.05` and `0.02`, and blows up near
0.268. [mitchell2021] Table 1 tests −45° to **+15°**, so the published range stops exactly where
this bites, and the prose above ("beds dipping downstream speed it up") describes only the
`S > tan φ` branch. Clamp the denominator away from zero and fall back to the undipped `C_H` below
`S = tan φ`, or restrict `φ` to the upstream-dipping case, where `S + |tan φ|` is unconditionally
positive and the formula behaves as described.

Beds dipping **upstream** (`φ < 0`) enlarge the denominator and **slow** contact migration; beds
dipping **downstream** speed it up. [mitchell2021] Table 1 works dips from −45° to +15°. The
authoring consequence is direct: dip the column **upstream**, toward the headwaters, and its
resistant beds hold their scarps for longer — which is what a long-lived cliff band wants. Dip it
downstream and the same column's contacts sweep through the catchment and the banding washes out.

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

Three numbers per run. `S_area` is the mean slope of cells whose stratigraphic height falls in a
resistant bed, divided by the same for weak beds. `conc` takes the trunk channel and divides the
share of its total descent carried by resistant reaches by the share of its *length* they
occupy — 1.0 is no scarp, and above 1.0 is relief packed into short reaches, which is what a
scarp *is*. `area_hard` is the fraction of the map whose surface sits in a resistant bed; 0.5 is
what the bed thicknesses alone predict.

| Run | Outcrop width | `S_area` | `conc` | `area_hard` |
|---|---|---|---|---|
| **Uniform `K`, control**, 25 m bands scored | — | **1.010** | **0.86×** | 0.499 |
| **Uniform `K`, control**, 100 m bands scored | — | **0.944** | **0.89×** | 0.464 |
| Horizontal, 25 m beds, 4× | ∞ | 1.597 | 1.58× | 0.497 |
| Horizontal, 25 m beds, 4×, run to 4 Myr | ∞ | 1.597 | 1.57× | 0.502 |
| Horizontal, 25 m beds, **16×** | ∞ | 1.323 | **2.29×** | **0.300** |
| Horizontal, 100 m beds, 4× | ∞ | **2.131** | 1.45× | 0.308 |
| Dip 10°, 100 m beds, 4× | 576 m — 5.8 cells | 1.705 | **1.85×** | 0.287 |
| Dip 2°, 25 m beds, 4× | 716 m — 7.2 cells | 1.408 | 0.92× | 0.476 |
| Dip 10°, 25 m beds, 4× | 144 m — **1.4 cells** | **1.322** | 1.21× | 0.378 |

The two control rows are what make the rest mean anything: with `K` uniform, scoring the same
bands gives `S_area` 0.94–1.01 and `conc` 0.86–0.89× — no signal, in fact very slightly negative,
which is the elevation–slope correlation showing up and being cancelled. **Every layered run beats
both controls on `S_area`**, by 1.3× to 2.1×; every one but the 2° run beats them decisively on
`conc` too, and the best packs **more than twice** the share of the trunk's descent into its
resistant reaches as those reaches occupy of its length. **Scarps are real and they are an
output.** So is the first half of Gaia's claim, and the 4 Myr row says it is converged rather than
transient.

Three results cut against the naive reading:

⚠️ **The slope contrast under-reads the erodibility contrast, badly.** Equilibrium says
`S ∝ (U/K)^(1/n)`, so 4× in `K` at `n = 1` ought to give 4× in slope. It gives about **2×** (and
16× in `K` gives about 3.7× — see the timestep table below, which shows part even of that is a
discretisation artefact). The mechanism is [mitchell2021]'s premise: contacts migrate, and the
erosion rates on the two sides adjust so that both retreat *horizontally* together, which means
neither unit is ever at local equilibrium with its own `K`. Practically: **author more contrast
than you want to see, not less**, and never read an authored `K` ratio off the rendered slope.

⚠️ **Outcrop width dominates dip angle.** Dipping 100 m beds at 10° gives the strongest scarp in
the set (`conc` 1.85× against 1.45× for the same beds horizontal) — dip *helps*. Dipping 25 m beds
at the same 10° gives the weakest (`S_area` 1.322), because their outcrop is 1.4 cells wide. It is
not the dip that broke it; it is `T / tan δ` falling below the grid.

⚠️ **Stream power plus linear diffusion gives the riser and never the tread.** `area_hard` runs
0.287 to 0.502 across every run and **never meaningfully exceeds 0.5** — resistant beds hold no more of the landscape's
area than their thickness predicts, and at high contrast they hold conspicuously *less* (0.300 at
16×). The area concentrates in the **weak** beds: those are the gentle stretches wide enough to
occupy map, which is a strike valley, not a mesa top. A mesa is a flat top *held up* by a caprock,
and producing one needs the scarp to retreat laterally while the top stays level. So Gaia's sentence
is right about cuestas and caprock scarps and **overstated about mesas**: layered `K` is necessary
for a mesa and does not produce one on its own.

### The obvious fix does not work, and the per-bed quantity is not the talus angle

A slope-limited pass with a **per-bed talus angle** is the natural thing to reach for, and it was
measured. On a synthetic butte — a 400 m escarpment, 100 m beds, resistant standing at 60° and weak
at 32°, 50 m cells — relaxing to those limits moved the escarpment **from 1.998 km to 1.996 km**.
Two metres, on a two-kilometre butte. `area_hard` went 49.61% → 48.91%, against single-angle
controls at 49.46%, 49.52% and 49.62% — the per-bed angles are **indistinguishable from one angle**
on this measure. A slope limit only moves material where the slope exceeds it; once the face is at
60° the pass converges and stops, and nothing has undermined anything.

**Retreat needs a removal term, and the removal is what has to be per-bed.** Adding weathering on
steep faces and controlling for total mass removed:

| Pass | Scarp radius | Tread std | Tread mean | Verdict |
|---|---|---|---|---|
| Talus limit alone | 1.998 → **1.996 km** | 1.01 m | 500.02 m | Nothing happens |
| Talus + **uniform** weathering | — | 1.01 → **7.21 m** | 500.02 → **151.01 m** | The mesa is destroyed |
| Talus + **bed-selective** weathering | 1.998 → **1.360 km** | **1.01 m** | **500.02 m** | Parallel retreat |

That third row is the mesa: the top stays at full height and bit-for-bit as flat as it started,
while the cliff comes in by 640 m. The caprock survives because it is *not weathered*; the weak beds
beneath it are, and the slope-limited pass then drops the unsupported cap. **The talus angle is what
makes the debris apron; the per-bed weathering rate is what makes the landform.** Carry both
attributes on the column, and if you carry only one, carry the rate. `thermal-and-aeolian-erosion.md`
owns the slope-limited pass and the failure-and-runout model; the bed-selective removal term is not
in it, and adding it is the work.

⚠️ **And `area_hard` cannot see a mesa even when there is one.** In the run that produced textbook
parallel retreat it *fell*, 49.61% → 44.66%, because retreat shrinks the cap and the metric counts
map area. The metric is right for the question it was built for — does a bed hold more landscape
than its thickness predicts — and it is the wrong instrument for "is this a mesa", which is a
statement about **shape**: a flat top, a steep side, and a break of slope between them. Measure the
tread's standard deviation and the scarp's position, as the table above does. A metric that is
insensitive to the landform you are chasing will report failure just as confidently when you
succeed.

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

What does degrade is **accuracy at contacts**, and it degrades in the direction that flatters the
result. A cell that starts a step in a resistant bed erodes the **whole step** at the resistant
`K`, even if it cut through the contact a tenth of the way in. The error is one-sided — it always
over-resists — so a coarse `Δt` makes resistant beds look more resistant than they are:

| Same 2 Myr, same column, 4× contrast | `Δt = 2000`, 1000 steps | `Δt = 500`, 4000 steps |
|---|---|---|
| Relief concentration `conc`, layered | 1.58× | **1.23×** |
| Relief concentration `conc`, uniform control | 0.86× | 0.87× |
| Channel slope ratio, resistant ÷ weak | 2.16 | **1.35** |
| RMS difference between the two heightfields | 24.8 m on 494 m of relief — **5.0%** | |

The control barely moves (0.89× → 0.87×) and the layered run moves a lot: **the timestep is
inflating the very feature the column exists to produce.** The scarp survives at both — 1.23× still
clears the control decisively — but its *strength* is a discretisation parameter until you check,
and the check is cheap: halve `Δt` and see whether the scarp holds.

**The rule that follows is a ratio, not a timestep.** Keep the typical per-step incision below
roughly a fifth of the thinnest bed:

```
Δt_max ≈ 0.2 * min(bed thickness) / max(K * A^m * S^n)
```

and it predicts the measurement above. In the trunk of that run, `K·A^m·S` reaches about
`10⁻² m/yr`, so `Δt_max ≈ 0.2 × 25 / 10⁻² ≈ 500 yr`. **`Δt = 2000` violates it by 4× and `Δt = 500`
sits on it** — which is exactly the pair that disagreed, and exactly which of the two moved. The
rule was derived before the runs and the runs land on it, so use it rather than picking a step by
eye.

The diagnostic is cheap and belongs in the loop: count the cells whose update crossed a contact,
per step. If that count is a large fraction of the actively eroding cells, the column is finer than
the timestep can resolve — **thicken the beds or shorten the step; do not raise the contrast to
compensate**, which is the tempting move, and which makes a coarse-`Δt` artefact look like a
successful edit.

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
| The scarps read far weaker than the authored contrast | Contact migration keeps neither unit at local equilibrium; a 4× `K` contrast measured 1.35–2.16× in slope | Author more contrast than you want to see, and never read `K` back off the slope [mitchell2021] |
| Concentric bands on every hill, like a contour map | Zero dip | Give the column dip and strike; even 5° breaks the concentricity |
| A dipped column that reads as noise or as stripes one cell wide | Outcrop width `T/tan δ` below the grid — 25 m beds at 10° are 1.4 cells on a 100 m grid, and measured the weakest of any layered run | Thicken the beds with the dip: `T ≥ 4·cellSize·tan δ` |
| The scarp weakened when the timestep was refined | The coarse step was inflating it: one-sided over-resistance at contacts | Believe the finer step; `Δt ≤ 0.2·min(bed thickness)/max(K·A^m·S^n)` |
| Cuestas that vanish after a long run | Beds dipping downstream, so contacts migrate fast | Dip into the drainage: `φ < 0` slows contact migration [mitchell2021] §2.5 eq. (12) |
| Cliff bands but no flat-topped mesas | Incision plus linear diffusion makes the riser, not the tread | A **per-bed weathering rate**, not a per-bed talus angle: measured, the talus limit alone retreats a 2 km butte by 2 m, and bed-selective removal retreats it by 640 m with the tread bit-preserved |
| A per-bed talus angle changed nothing | A slope limit only moves material where slope exceeds it; once the face sits at the limit the pass converges | Add a removal term. The angle makes the debris apron; the rate makes the landform |
| Weathering was added and the mesa dissolved | The removal was uniform, so the caprock weathered too — tread mean fell 500 → 151 m at equal mass removed | Gate the removal on the bed: the resistant unit must not be weathered, or nothing holds the top up |
| The metric says no mesa but the render clearly has one | `area_hard` counts map area, and parallel retreat *shrinks* the cap — it fell 49.61% → 44.66% in the run that produced textbook retreat | Measure shape, not area: the tread's standard deviation and the scarp's position |
| Thin beds erased entirely | Per-step incision comparable to bed thickness, so the bed is skipped in one update | `Δt ≤ 0.2·min(bed thickness) / max(K·A^m·S^n)`, or thicker beds |
| Resistant beds look thicker than authored | One-sided contact error: a cell cutting through a contact erodes the whole step at the bed above's `K` | Same ratio; count contact crossings per step as a diagnostic |
| Erosion rates never settle, so the run never looks finished | Expected: layered stratigraphy is not steady-state in the way uniform `K` is [forte2016] | Stop on a morphology target, not on rate convergence |
| A column that looked right at `m = 0.5` is wrong at `m = 0.45` | `K` has units `L^(1−2m)·T^(−1)` [mitchell2021] §2.1 eq. (1) | Author dimensionless contrasts against a reference `K` |
| Deposited sediment erodes like bedrock | The implicit column is a function of `z` and knows nothing about what was put back | Explicit layer stack [benes2001] §4; deposit as a bed with its own `K`, and change its properties on transport [benes2001] §5 |
| Memory blows up after a long deposition run | `event layers` storage, one entry per step | `material layers` [barnhart2018] p. 1 — merge contiguous same-material runs |
