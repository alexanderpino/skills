# Overturning — the price

**Wave 20, scout round.** What it would cost to render an overturning wave in
this project. Nothing was built. Every number below was measured on the shipped
code this round, and the scripts that produced them are named at the end.

This document answers the re-opened sections A and F of `bar/bar.md`. It does
**not** re-close them, and it does not recommend closing them.

**Evidence:** `evidence/s20-overturning.png`, caption in
`evidence/s20-overturning.caption.md`.

---

## 0 · The one-paragraph answer

The shipped scene **wants to plunge, on every alongshore row, and the model
already says so in its own numbers.** The wave breaks on the seaward flank of
its own Exner bar, where the local bed slope is **1 : 4.4** and the local
surf-similarity number is **ξ = 1.11 (range 0.97–1.20 over 89 rows)** — squarely
inside Battjes' plunging band on both published threshold sets. What refuses the
overturn is not the sea state, not the bed and not the steepness: it is that
`η(x, y)` admits one height per point. **Exactly one candidate representation
survives standing ruling 4**, and it is the analytic one — the parametric cubic
free surface of Longuet-Higgins (1982), which is an *exact solution of the
free-surface equations* rather than a sculpted mesh. Priced at **2 waves for the
geometry-and-measurement half and 2–4 more for the renderer half**, with a hard
provenance gate in front of both. The cheapest thing that would confirm or refute
it costs about a minute and is described in §6.

---

## 1 · The boundary, by measurement

### 1.0 The instrument, and what else was running

Everything in this section comes from two read-only scripts driving the shipped
modules — `beach.py`, `beach_render.py` — through their own entry points. No
file in `terrain-renderer/reference-impl/` was modified. Measurements are on the
free surface itself, before any tone map; no PNG was read for physics.

`nproc` is **4**. Two other `python3` processes (other builders) were running at
100 % and 124 % CPU for the whole of this round, and the load average at the
start was 2.09. Every wall-clock figure quoted below is therefore an **upper**
bound on the same work run alone. Standing ruling 13's surviving half applies:
these totals are not comparable with totals taken on an idle box.

Costs, for anyone reproducing: `beach.run_bay()` **117.8 s**,
`beach_render.Water(bay)` **35.6–38.4 s**, one `surface_slope` call over 90 000
world points **≈ 20 s**.

### 1.1 The breaker class — and a correction, because the slope window is the instrument

The first measurement this round took said **spilling on 89 of 89 rows**, and it
was wrong in the way this project keeps finding: *a number measured once under
conditions nobody recorded.* The condition was the width of the window the bed
slope was differenced over.

| slope window at the breakpoint | median &#124;m&#124; | median ξ_b | rows plunging (ξ ≥ 0.4) |
|---|---|---|---|
| ± 10 cells (40 m) | 0.0290 → 1 : 34.5 | 0.142 | 0 / 89 |
| ± 5 cells (20 m) | 0.0510 → 1 : 19.6 | 0.247 | 0 / 89 |
| ± 2 cells (8 m) | 0.0639 → 1 : 15.7 | 0.307 | 22 / 89 |
| ± 1 cell (4 m) | 0.0486 → 1 : 20.6 | 0.230 | 22 / 89 |
| **steepest cell of the bar flank** | **0.2268 → 1 : 4.4** | **1.110** | **89 / 89** |

The bar's seaward flank is about **16 m wide on a 2 m grid**. A slope averaged
over 20 m reports the Dean ramp the bar sits on; a slope taken at the flank
reports the face the wave actually meets. The transform is not averaging: its
own depth filter is set at the **grid-noise scale, 1.5 cells = 3 m**, and
`smooth_depth`'s docstring says in its own words why it is not at the wavelength
scale. So the wave in this model sees the 1 : 4.4 flank.

The cross-shore profile at the middle row, from the shipped bay:

| x (m) | d (m) | H/d | &#124;m&#124; | ξ | q_b |
|---|---|---|---|---|---|
| 480 | 3.516 | 0.467 | 0.0469 (1 : 21) | 0.262 | 0.076 |
| 486 | 3.054 | 0.554 | 0.1206 (1 : 8.3) | 0.643 | 0.207 |
| 490 | 2.684 | 0.647 | 0.1754 (1 : 5.7) | 0.895 | 0.448 |
| 494 | 2.333 | 0.766 | 0.2232 (1 : 4.5) | **1.085** | 0.929 |
| 496 | 2.216 | **0.815** | 0.0312 | 0.149 | **1.000** |

**The wave crosses `H/d = γ_b = 0.78` at the steepest point of the bar flank.**
That is not a coincidence and it is not tuned: the bar is where it is *because*
the flux converges at the break point, and the break point is where it is
because the bar is there. The Iribarren number of that coincidence is 1.1, and
1.1 is a plunging breaker.

Over the whole domain, of 9 490 breaking cells, **50.9 % have local ξ ≥ 0.4**
(plunging) and 5.1 % have ξ ≥ 2.0 (surging). Of the 9 651 cells in the 0.5–5 m
band, **11.9 % are steeper than the derived reflective limit `2K/5 = 0.060`**
that `beach.saturation_slope_limit` already carries, at x = 468–648 m and depths
0.50–3.90 m.

**Which bar.** The shipped hero bay is single-partition (`run_bay()` defaults
`climate=None`, and that default is what keeps 562 published rows comparable).
Wave 19's second breaker bar lives on a two-partition bed that the hero frames
do not use. Evaluating `climate_breakpoints` with `CLIMATE_SCENE` on the shipped
bed gives **three lines at x = 491.8 / 587.2 / 604.2 m in 2.34 / 1.18 / 0.59 m**
of water — so the plunging flank measured above is under the **seaward** line,
the swell's own, at x ≈ 490 m; the wind sea's lines are inshore of it, in
shallower water, on the gentler bed behind the bar.

### 1.2 The face angle of the shipped surface

`surface_slope` over 90 000 world points, 8 instants across one period, both
branches of the `SPECTRAL_ON` control panel, `eps = 0.5 m` (the shipped operator):

| | carrier only (waves 5–18) | shipped (wave 19 bundle) |
|---|---|---|
| median | 0.98° | 1.69° |
| p99 | 8.13° | 13.37° |
| p99.9 | 11.66° | 18.09° |
| p99.99 | 13.79° | 22.09° |
| max | **16.02°** | **43.53°** |
| share of wet samples over 30° | 0.000e+00 | 8.68e-06 |
| share over 41.48° | 0.000e+00 | 1.45e-06 |
| surf zone, per-point max: median | 1.03° | 2.01° |
| surf zone, per-point max: p99.9 | 14.26° | 23.48° |

A fine zoom — 80 × 80 m at 0.2 m spacing around the steepest sample, 24 instants
— reads **46.89°**, so the coarse grid was undersampling the extreme and the
tail is real rather than an interpolation artefact.

**Three things follow, and the third is the one that matters.**

1. **The carrier's 16.02° is its closed form.** `slope_gain` at the shipped
   `(r, ψ)` maxes at exactly **2.000** (the pure-asymmetry limit), `a·k` maxes at
   **0.1481 = 8.42°**, and the product is **0.2945 = 16.41°**. The measured
   16.02° is that number minus the difference operator's own attenuation. So the
   waves 5–18 surface had a ceiling in closed form and sat on it.
   ⚠️ Chapter 12 currently quotes **15.78°** for this scene. That figure is the
   carrier's and is now one wave out of date.

2. **The shipped surface is past Stokes' corner already.** 30° is exceeded by
   about one wet sample in 115 000, and 41.48° by about one in 690 000. It is
   *not* a defect: 30° caps a wave of **permanent form**, and a linear sum of 256
   components is not one. But it disposes of the framing the closure used —
   **the shipped surface does not fail section A for want of a steep enough
   face.** It has faces past 41.48° and section A is still unreachable.

3. **So the boundary is topological, not angular.** `through_face` — the
   instrument already in `beach_render.py` — marches the refracted view ray until
   the free surface comes back down to meet it, and the fraction of rays that
   leave the far side of a crest is **0.0000** on the linear surface and
   **0.0000** on the second-order one. Chapter 12's own two-cone derivation says
   why: the criterion is on the **sum** of the entry and exit inclinations,
   `α₁ + α₂ ≥ 2(90° − θ_c) = 82.96°`, and a face is only half of it. A
   single-valued surface with a 47° face still has to bring its partner face up
   to 36°, on the *same crest*, on the *same ray*. That is what folding buys and
   steepening does not.

⚠️ **The `eps` sensitivity is confounded and is reported that way.** A second
census at `eps = 0.125 m` returned p99.9 = **18.19°** against 18.09° and
p99.99 = **22.05°** against 22.09° — the two agree to a tenth of a degree, so
the shipped difference operator is *not* the limiter at the percentiles. Its
*max* came out lower (34.36°) only because that census ran 4 instants and not 8;
a max over a random field is an extreme-value statistic and is not comparable
across sample counts. **Quote the percentiles, not the max.**

### 1.3 The surface's own statement that it has run out

The strongest single number in this round is not an angle.

`surface_state` clamps the bound second harmonic's amplitude ratio `r` to
`stokes2_crest_limit(ψ)` — the largest `r` for which the shape is still **one
crest and one trough per cycle**. Past that limit a second-order Stokes surface
grows a false crest in its own trough; it is the exact point at which the
representation stops describing one wave.

| | |
|---|---|
| Ursell number over the wet bay | median **0.550**, p99 15.2, max 38.4 |
| the Stokes/cnoidal boundary, in this file's normalisation | Ur = 0.500 |
| fraction of the wet bay past it | **0.5027** |
| `r` that second-order Stokes asks for | median **1.220**, max **77.2** |
| the secondary-crest limit | 0.2500 … 0.5000 |
| **fraction of the wet bay where the clamp bites** | **0.7478** |
| `r_raw / r_limit` over the clamped set | median **50.5×**, max **154×** |

**Three quarters of the wet bay is being held at the limit of a theory that
asked for fifty times more harmonic than the shape can carry.** That is where
the surface wants to go multivalued, stated by the implementation about itself,
and it is not a marginal region — it spans x = 214 m to the shoreline and depths
of 0.10 m to 7.14 m. The clamp is the representation change's *pre-image*: every
clamped cell is a cell where a single-valued shape is standing in for something
the physics no longer describes.

### 1.4 The kinematic criterion, and why it does not fire

Overturning is `u_crest ≥ c`. This model can state that without a new constant:
in shallow water a long wave carries `u = η√(g/d)` (stated in
`beach.ur_half_derived`'s own derivation) and `c = √(gd)` (`beach.celerity`'s
shallow limit), so `u/c = η/d`, and the solitary form is `η/(d+η)`.

Measured on the drawn surface — `η_crest` is the per-point maximum of
`free_surface` over one period, 24 instants, over the 33 611 surf-zone samples
(`q_b > 0.01`):

| | median | p99.9 | max |
|---|---|---|---|
| `η_crest / d` (linear shallow-water form) | 0.241 | **0.977** | **1.161** |
| `η_crest / (d + η_crest)` (solitary form) | 0.194 | 0.494 | 0.537 |
| share with `u/c ≥ 1`, solitary form | | | **0.000e+00** |

**The two conventions disagree by a factor of two and this document does not pick
one**, because the disagreement is itself the answer. On the linear shallow-water
relation the drawn crest reaches **98 % of the phase speed at p99.9 and 116 % at
the extreme** — i.e. the fluid at the crest is overtaking the crest, which *is*
overturning. On the solitary form the same surface reaches **0.537**, and the
criterion never fires.

The solitary form is the one consistent with how this model saturates: the
transform holds the wave at `H/d = γ_b = 0.78` by dissipation, and at the McCowan
limit the solitary form gives `u/c = 0.78/1.78 = 0.438`. Measured, `H/d` over the
wet bay is median 0.326, p99 0.790, max 1.535, with **1.11 % of the wet bay at or
past γ_b**.

**What to take from it.** `u/c` is a *sharp* criterion in a model that resolves
the crest kinematics, and this model does not — it carries a height, a phase and
a bound harmonic, not a velocity field at the surface. The p99.9 = 0.977 says the
drawn surface is standing at the threshold on the more permissive reading; the
0.537 says the dissipation model will never let it cross on the stricter one. So
`u/c` should **not** be the lip's trigger. The triggers this scene *does* supply,
all computed and all unambiguous, are ξ_b (1.11 at the flank, plunging on 89/89
rows), the `H/d` crossing of γ_b (at x ≈ 494 m, on the steepest cell of the bar
flank) and the validity clamp (74.8 % of the wet bay).

### 1.5 Ruling 18, still live, in the place this work would land

`beach.surface_moments` computes the asymmetry `As` in closed form. `grep` this
round: outside `beach.py` the function is called **only** from
`validate_beach.py`, at four sites. Nothing in `beach_render.py`,
`beach_foam.py`, `beach_optics.py` or `field.py` reads it, and `sediment_flux`
has no asymmetry term. Over the wet bay `As` runs 0.000 … **0.759**, with |As|
median 0.008 and p99 **0.759**.

That matters here specifically: **asymmetry is the moment an overturning wave
is made of.** `Sk² + As² = g(r)` — breaking rotates the third moment out of the
skewness and into the asymmetry, and the asymmetry is the pitched-forward front
that becomes the lip. The one quantity the shipped model computes that *is* the
overturn's precursor is the one nothing reads. Any lip built later must be
driven by it or by something equally computed, and the row that proves it is
reached must be paired with the row that tests it (ruling 18).

---

## 2 · What the skill already says — and where it is silent

**Consulted first, per the brief.** `terrain-renderer/references/`.

### `12-water-rendering.md` — has the diagnosis and half the price

- The **structural obstacle is already written**, in the surf-zone section: *"A
  plunging breaker throws its lip forward over an air tube, so for the duration
  of the overturn the free surface is **multivalued** … That is the moment
  `z = f(x, y)` stops existing, and with it goes the height field, the caustic
  pass's Jacobian, the surface-intersection route and every LOD scheme."* It
  names three candidate representations — *"a parametric sheet, a
  particle/level-set hybrid, or a genuinely volumetric surface"* — and says the
  honest move is to **price it as a representation change**, marked `?`.
- **`00-index.md` records the gap in the same words**: *"the multivalued free
  surface under a plunging lip is stated as a representation change with **no
  route proposed**."* This document is the first attempt at that route.
- The **30° ceiling** section is sharper than the closure that cited it, and its
  correction is the one this round confirms: the criterion is **not** 41.48° per
  face, it is `α₁ + α₂ ≥ 82.96°` — a sum over two crossings of the same ray.
  Verified there two ways (a hemisphere shot at a wedge; `through_face` on this
  bay). It also carries the practical half: at `α₁ = α₂ = 41.6°` the best
  two-crossing transmittance is 0.098 and the share of intercepted flux that
  gets through is **1.5 × 10⁻⁴**; it takes **≈ 50°** faces to pass a tenth and
  **≈ 55°** to pass a fifth. **The phenomenon lives well above the geometric
  floor**, which raises the bar on any lip that claims section A.
- The **real-time prescription is authoring**, and this is where the chapter and
  this project collide: *"plunging = an authored curl — flipbook, skinned mesh,
  or particle sheet — placed along the break line (hero-tier, budget it)"*, and
  *"A renderer that wants the green face must **author** it … and say so."*
  That is correct advice for a game and is **exactly what standing ruling 4
  forbids here**. See §4.
- `12a` (derivations) and `12b` (provenance) carry no overturning derivation.
  `12b` marks the multivalued free surface `?` explicitly.

### `19-fluid-simulation.md` — has the decision procedure and the tiers

Question 1 of its representation procedure is literally *"Must the surface
overturn?"*, and its answer is unambiguous: heightfield waves that break are
*"unrepresentable — not expensive, impossible"*, and Tier 1 *"structurally
cannot … overturn, splash, separate, or represent more than one water surface
per column."* Tiers 2 (PBF/SPH), 3 (FLIP/APIC) and 4 (MPM) are laid out with
citations and trade-offs; **Position Based Fluids is named as the games default**
and **APIC over raw FLIP** if choosing today. Drawing a particle fluid is its own
section: screen-space fluid rendering (van der Laan et al. 2009) or isosurface
meshing via `05`'s machinery, plus the spray/foam/bubble diffuse-particle split.

Two sentences from it are load-bearing for the price below:

> *"A particle fluid has no surface — you have to invent one, and the choice
> matters as much as the solver."*

> *"FLIP/APIC … is viable in real time for **bounded** domains … rather than open
> worlds."*

**What it does not contain:** any parametric or analytic overturning surface. Its
whole answer to question 1 is *change tier*, and every tier it offers is a
solver. It does not consider that an exact closed-form overturning free surface
exists.

### `18-heightfield-raymarching.md` — silent, and the silence is structural

The chapter is about marching a ray against a **height texture**. Its decision
table's "Silhouettes" column is about screen-space accuracy, not about surfaces
that fold; nothing in it, including the pitfalls list, contemplates a
multivalued field. That is not an omission to be fixed — the whole family it
documents is defined by single-valuedness — but it means **no LOD, no
acceleration structure and no pyramid in `18` transfers to a lip.** A second
representation gets no help from this chapter.

### `05-voxel-smooth-isosurface.md` — the only chapter with machinery that can hold a fold

An SDF/density field on a grid, extracted by Marching Cubes / Surface Nets /
Dual Contouring, **can** represent a folded sheet — that is what makes it the
`19` isosurface-meshing option. What `05` supplies that is directly usable:
narrow-band storage, the apron doctrine, the quantisation-terracing analysis, and
hermite data for sharp features. What it costs is also there: *"Pay for it in
grid resolution and temporal popping of the mesh."* And its own decision table
says the honest thing for our case — *"No caves/overhangs, no digging →
heightfield LOD, full stop"* — i.e. **a voxel field is what you adopt when the
fold is everywhere, not when it is a 16 m band in a 1 km bay.**

### The silence worth recording

Across all twenty-two chapters there is **no derivation of an overturning free
surface**, and no mention of the exact parametric solutions that exist for one.
The skill's only route to a plunging lip is *author it* (`12`) or *simulate it*
(`19`). That is a real hole in a skill that claims authority on sea and open
water, and it is independent of whether this project ever renders one.

---

## 3 · The candidates, priced

Costs are in **waves**, calibrated on this project's own record: wave 5 (the
nonlinear surface — shape change, same representation, same tracer) was one lane
for one wave; wave 19 (the spectral bundle replacing the first-order term, plus a
suite section and the foam realisation) was one lane for one wave and left one
`FAIL` and one open residual. **Neither touched the tracer.** In nineteen waves
nothing has.

### 3.0 The null — do not do it

**What it can represent:** the wave up to the instant of overturning, which is
what it represents now, and which is genuinely good physics.

**What it cannot:** section F at all; section A at all, at any steepness, for the
two-cone reason in §1.2.3.

**Cost:** 0 waves.

**What the render loses.** Less than it looks, and more than it looks, in two
different places.

- *In the hero frames*: little. The frames are shot from a cliff top at 618 m
  standoff with water at 16.2 % of frame; a lip is metres across and would be a
  handful of pixels. Nobody has ever scored a hero frame down for a missing
  barrel — the standing visual gaps are the clipped glitter slab (6.4 % of frame
  at 254+), the one-valued foam white (sd 0.31 DN against 8–21 measured) and the
  land (30–400× short on high-frequency sd).
- *In the model*: everything the owner actually said. *"Het oppervlak van de zee
  … bestaat ook uit golven … En golven die omslaan."* A model of open water that
  structurally cannot overturn is incomplete, and this round has measured that
  the incompleteness is **not** justified by the scene: the scene's own bar flank
  is a plunging breaker on 89 of 89 rows.

**What it breaks:** nothing. **How it is verified:** it already is — the
measurements in §1 are the evidence for the null as much as against it.

### 3.1 A parametric breaker lip, stitched to the heightfield — **the only ruling-4 survivor**

**The route, and it is not the one the chapters name.** Not an authored curl and
not a flipbook. **Longuet-Higgins (1982), "Parametric solutions for breaking
waves", J. Fluid Mech. 121, 403–424**: an exact family of time-dependent
free-surface flows written parametrically, `z(ω, t)` and `χ(ω, t)`, whose members
include Stokes' 120° corner flow and the 45° rotating wedge, and whose **cubic**
class has a free surface that *"corresponds with remarkable accuracy to the
forward face of an overturning, or plunging, breaker."* (Web-verified this round;
the abstract and the secondary literature agree on the statement, and see the
provenance gate below.) New (1983) supplies the companion result that the tube's
inner surface is close to an ellipse of axis ratio √3.

**What it can represent:** the forward face and the throwing jet of a plunging
breaker, i.e. section F, and with it section A at the earlier instant. The air
tube. The lip's own optics — its thin wedge is exactly the variable-path cuvette
section A describes.

**What it cannot:** the impact, the splash-up, the second jet, the entrained-air
plume's geometry, droplets. Everything after the lip touches down is out of the
solution's validity, which ends where the surface self-intersects.

**Cost in code.** Three pieces, and only the third is large.

| piece | size | note |
|---|---|---|
| `beach_lip.py` — the parametric surface, its own suite section | ~400–700 lines | comparable to `beach_diffract.py` (709 lines, one wave) |
| onset + matching: where the lip attaches, at what scale, at what phase | ~150 lines in `beach.py` | must come from ξ_b, `broken_fraction`, `breaking_indicator`, `As` — **no new constant** |
| `trace` and `shade_water`: an ordered, multi-hit intersection | **the expensive one** | `trace` currently solves `z(t) = η` by 4 Newton steps from the analytic plane hit; a fold has 1 or 3 hits and they must come back ordered |

**Cost in run time.** Bounded and small. The lip exists only where the breaking
criterion fires — the 16 m-wide flank band, ~11.9 % of the 0.5–5 m band, a few
percent of water pixels in the hero frames. A parametric sheet is intersected
analytically (a cubic in the parameter), so the per-pixel cost is a root solve,
not a march. Expect **single-digit percent** on frame time, dominated by the
branch, not the arithmetic.

**What it breaks.**

- **`trace`'s central assumption**, which is stated in its own docstring: *"a ray
  with `d_z < 0` meets the plane `z = 0` at a known `t`, and `|η| ≤ 1 m`, so
  three Newton steps against `η` land on the real surface."* A fold makes that
  false in the band. The fix is a *local* one — Newton for the heightfield, an
  analytic root solve for the lip, `min` over the hits — but it is a change to
  the routine every pixel of every frame goes through.
- **The one-code-path criterion**, unless the handoff is a genuine seam. Chapter
  12's own rule for the analogous blend is the right one: *"Cross-fade … never
  add them."* The lip must **take over** the surface in its band, not be drawn on
  top of it, or the frame has two surfaces where it should have one.
- **Byte-identical frame checks** — but only where the lip fires, and here the
  project's own defaults give a free control. The shipped bay's frames stay
  byte-identical wherever the onset criterion is false, which is 88 % of the
  surf band and 100 % of the offshore water. *That is the cheapest possible
  regression proof and it should be a row.*
- **The deterministic suite:** survives. A parametric surface is a closed form;
  there is nothing stochastic to seed.
- **Standing ruling 6 (the pool):** untouched. `optics.py` is not involved.

**How it is verified — and this is why it is ranked first.**

1. **The surface satisfies its own free-surface conditions to machine
   precision.** A closed-form solution can be substituted back into the kinematic
   and dynamic boundary conditions. That is a row with a known answer, not a
   tolerance.
2. **Stokes' 120° corner is a limiting member of the same family.** So the
   control whose answer is known in advance (standing ruling 14) is *already
   published* — the lip's own machinery must reproduce 120° in the limit, and if
   it does not, the implementation is wrong and the row says so. This project has
   never had a cheaper ruling-14 control available.
3. **The two-cone criterion, measured on the lip's own geometry.**
   `through_face` exists and reads **0.0000** today. Run it against the lip and
   report `α₁ + α₂` against 82.96°, and the transmitted-flux share against the
   chapter's `1.5 × 10⁻⁴ @ 41.6° / 0.126 @ 50° / 0.228 @ 55°` table. **If that
   number is still ~0, the lip did not buy section A and the build is refused on
   its own evidence.**
4. **Reach rows (ruling 18):** integers off the rendered buffer — how many pixels
   carry a lip hit, what share of the surf band, and where; paired with the
   function rows, and with a `grep` that finds the new symbols outside the module
   that defines them.

⚠️ **The provenance gate, and it is a hard one.** *Longuet-Higgins (1982) is not
in this container.* The abstract and the secondary literature are reachable; the
explicit `z(ω, t)` is not, and web search this round did not surface it.
**Standing ruling 9 forbids reconstructing it from memory**, and the precedent is
already on the backlog — Hsu & Evans' bay-shape equation is parked *on provenance,
not difficulty*, with the note *"unpark only when someone can put the paper in
front of it — never by reconstruction."* The same rule binds this. **If the paper
cannot be obtained, this candidate becomes the null and should be parked in the
same words.**

**Price: 2 waves for the geometry-and-measurement half; 2–4 more for the
renderer half.** Detail in §5.

### 3.2 A local mesh strip or level set carrying the plunging region

**What it can represent:** everything 3.1 does, plus the impact, splash-up,
reconnection and the tube's collapse — the whole plunge rather than its forward
face.

**What it cannot:** droplets and spray, which are sub-grid to any level set you
can afford.

**Ruling 4 — and this is the sentence the brief asked for.** *A mesh strip whose
shape is authored fails ruling 4 outright and ends the project's central claim.*
A level set whose motion is **solved** — a boundary-integral / mixed
Eulerian–Lagrangian free-surface solve of the Longuet-Higgins & Cokelet (1976)
kind, or `19`'s Tier 3 — does **not** fail ruling 4, because the geometry is then
an output of the equations rather than a sculpt. **But nothing in between passes.**
There is no version of "a mesh strip we shape to look right" that survives
ruling 4, and the moment a smoothing radius, a curl profile or a lip thickness is
chosen to make the picture right, ruling 3 has gone too.

**Cost in code:** a free-surface solver, its stability, its re-gridding, its
own suite. `19` puts this tier at film/bounded-domain scale. **8+ waves**, and
the suite would have to verify a *solver* rather than a formula — a different
and much harder verification problem than anything this project has done.

**What it breaks:** the same tracer assumptions as 3.1, plus mesh extraction and
its temporal popping (`05`), plus every byte-identical check the moment the
solver's output differs anywhere. Determinism is preservable in principle (fixed
grid, fixed timestep, no RNG) and would have to be a row.

**How it is verified:** against `12a`-style closed forms in the limits, and
against 3.1's parametric solution as the analytic control — which is an argument
for doing 3.1 **first** regardless.

**Price: 8+ waves. Refused at this budget.**

### 3.3 Particles for the lip and the resulting splash

**What it can represent:** spray, splash, entrained air, droplets — the aerated
debris.

**What it cannot: the lip.** A plunging lip is a **thin coherent sheet**, which
is the single hardest thing for a particle method to hold; and `19` states the
disqualifying fact in its own words — *"A particle fluid has no surface — you
have to invent one."* Screen-space fluid rendering's load-bearing step is a
**smoothing** of the depth buffer, and the chapter names both failure modes:
*"under-smooth and it is blobby, over-smooth and it shrink-wraps and loses splash
detail."*

**Ruling 4: fails.** The rendered surface is a smoothing kernel's output, not
analytic geometry. **Ruling 3: fails too**, and worse — the smoothing radius is
precisely *a constant chosen to make the picture right*, and there is no physical
effect that sets it.

**And the project already has the honest version of what particles would be
for.** `beach_foam.py` carries the entrained-air void fraction from Lamarre &
Melville's energy budget, and the plume's diffuse transmittance is measured
(`0.152` at 1.5–3 m). That is a **statistical** treatment of the same aerated
water, derived from the dissipation the transform computes. Replacing a derived
statistic with an undriven particle set would be a step backwards.

**Where particles might legitimately return:** as `19`'s *classified debris* —
spray/foam/bubbles seeded from a solver's own curvature and relative velocity.
They are a **consequence** of 3.2, not a substitute for 3.1. With no solver there
is nothing to classify from.

**Price: not applicable to section F.** If wanted for section E (the cloud after
a break on rock), that is a different item and should be priced there.

### The table

| | represents F | represents A | ruling 4 | ruling 3 | code | run time | breaks | verifiable |
|---|---|---|---|---|---|---|---|---|
| **0 · null** | no | no | ✅ n/a | ✅ | 0 | 0 | nothing | already is |
| **1 · analytic parametric lip** | forward face + jet + tube | yes, if `α₁+α₂` clears 82.96° | ✅ **passes** — exact solution, not a sculpt | ✅ if onset comes from ξ_b / `f_brk` / `As` | ~700 lines + tracer rewire | few % of frame | `trace`, one-code-path, byte-identical *in band only* | ✅ closed form, 120° control, `through_face`, reach rows |
| **2a · authored mesh strip** | yes | yes | ❌ **fails** | ❌ | medium | low | the central claim | ❌ |
| **2b · solved level set** | whole plunge | yes | ✅ passes | ✅ | solver + suite | large | tracer, extraction, all frame checks | hard — verifying a solver |
| **3 · particles** | ❌ not the sheet | ❌ | ❌ **fails** | ❌ smoothing radius | large | large | determinism, the derived foam | ❌ |

---

## 4 · What would have to be true

**Ruling 3 — physics from physical effects, never a constant chosen to make the
picture right.** The lip's *onset*, *scale*, *phase* and *duration* must each be
a function of something the model already computes. The candidates are on the
table and none of them is new: ξ_b = 1.11 at the flank; the `H/d` crossing of
γ_b; `broken_fraction`; `breaking_indicator` on the drawn envelope (which wave 19
already realises per wave rather than in expectation); and `As`, the asymmetry
that *is* the pitched-forward front. **The failure mode is a "lip size" constant.
If one appears, the round has failed whatever the frame looks like.**

**Ruling 4 — the geometry stays analytic.** *Stated plainly, because the brief
asked for it:*

> **A sculpted or authored breaker lip cannot satisfy ruling 4, and no amount of
> care in the authoring changes that.** The chapters' own real-time prescription
> — flipbook, skinned mesh, particle sheet — is unavailable to this project. A
> particle representation is likewise unavailable, because its surface is
> invented by a smoothing kernel. **Exactly one route survives: an exact
> parametric solution of the free-surface equations.** If that solution cannot be
> obtained from its source, then section F is not buildable under ruling 4 and
> the honest outcome is a park on provenance — *not* a relaxation of ruling 4,
> and *not* a lip drawn anyway. That is a scope decision and it belongs to the
> owner.

**Ruling 17 — every visible structure names the number it came from.** For a lip
this is unusually tractable: the parametric solution has a scale and a time
origin and nothing else, so the chain reads *"lip scale from the breaking wave's
own height at the flank, out of `transform_2d`; onset from the `H/d` crossing;
orientation from the crest normal; asymmetry from `surface_moments`."* Four
links, all computed. A lip that cannot write that sentence is not drawn — it is
named (17.2), and the residual is stated (17.3).

**Ruling 18 — a reach row for every function row.** This is the ruling most
likely to be violated by this work, because the lip lives in a narrow band and
the frames are wide. Required: integers off the rendered buffer for lip-hit
pixels and their share of the surf band; a `grep` that finds every new symbol
outside its defining module; and a `git log` on `validate_beach.py` showing the
round's own entry. This project has four recorded instances of the opposite
(foam, glitter, diffraction, wave 13) and the fifth would be free here.

**Ruling 9 — consult the source.** Binding on Longuet-Higgins (1982) and New
(1983). See the gate in §3.1.

**Ruling 14 — build the control whose answer is known.** Available for free:
Stokes' 120° corner is a limiting member of the same parametric family. Build it
first; if the implementation cannot reproduce 120°, nothing after it is worth
running.

**Ruling 6 — the pool does not disappear.** Unaffected. `optics.py` is shared and
none of this touches it; the lip's optics reuse the same Fresnel, critical angle
and Beer–Lambert the cuvette already uses.

---

## 5 · The recommendation, with a number

**Ranked.**

**1 · Buy the geometry-and-measurement half of the analytic lip. Two waves.**
Not the renderer. The deliverable is `beach_lip.py` plus a suite section plus a
figure, and it answers section A's real question **without drawing anything**:

- *Wave A (1 wave):* obtain Longuet-Higgins (1982); implement the parametric
  cubic; verify it satisfies the free-surface conditions to machine precision;
  reproduce Stokes' 120° corner as its limiting member (the ruling-14 control);
  measure `α₁ + α₂` on the lip's own geometry against 82.96° and the transmitted
  flux against chapter 12's table. **Output: a verdict on whether the overturn
  reaches section A at all.**
- *Wave B (1 wave):* the onset and matching — where the lip attaches to `η`, at
  what scale and phase, driven by ξ_b, the `H/d` crossing and `As`, with the
  no-new-constant property as a row. Plus the figure into
  `references/12-water-rendering.md` (the chapter describes an overturn and has
  never shown one), and the chapter correction from §1.2 (its 15.78° is the
  carrier's and the shipped surface now reaches 46.89°).

At the end of two waves, section F is **priced, half-built and verified in
geometry**, the chapter is better, and *nothing in the render has changed* — so
every hero frame is still byte-identical and no visual score has moved. If the
renderer half is never bought, this is still a result rather than a stub.

**2 · Then, only on an owner ruling, the renderer half. Two to four more waves.**
Multi-hit `trace`, the seam in `shade_water`, the lip's own foam and chord, the
reach rows, the byte-identical proof outside the band. Two waves if the tracer
rewire goes cleanly; four if it goes the way this project's last three rewires
went. **Ask before starting**: at wave 20 of 26 budgeted this is 2–4 of the six
remaining
waves, spent on one bar section, while the largest measured tell in every frame
(the land, 30–400× short) has no owner and the glitter slab is 6.4 % of frame.

**3 · The null**, if the paper cannot be obtained. Park on provenance in the
Hsu & Evans words, keep sections A and F open with this document as the price,
and record that the scene's own bar flank is a plunging breaker so nobody
re-closes it on a physics argument.

**4 · Solved level set — refuse at this budget.** 8+ waves and a solver to
verify. Revisit only if this project ever needs the whole plunge rather than the
lip.

**5 · Particles — refuse for section F outright.** Fails rulings 3 and 4, and
would replace a derived statistic with an undriven one.

**The number, in one line: 2 waves to buy the answer, 2–4 more to buy the
picture, and the second half should not start without an owner ruling on the
budget.**

---

## 6 · The one cheap measurement

**Instrument `through_face` to report `α₁ + α₂` for every ray that *enters* the
water, not only for the ones that exit, and render one hero frame at 240 × 320.**

Cost: no new physics, about twenty lines in a copy of the function, one
low-resolution render — **of order a minute** once `Water` is built.

What it decides:

- `through_face` already computes the entry normal (via `Nn`) and the far-side
  normal (`Nf`, after the march). It currently throws away everything about rays
  that never exit — and *every* ray in this scene is one of those, which is why
  the reported number has been **0.0000** for six waves. A zero with no
  distribution behind it cannot tell "close" from "nowhere near".
- Report the distribution of `α₁ + α₂` over entered rays against the
  **82.96°** floor. Two outcomes, and they point opposite ways:
  - **If the tail sits at 25–50°** — which §1.2's per-face percentiles predict —
    then the deficit is 30–58° of *summed* inclination, no single-valued surface
    closes it, and **the lip is the only route**. Rank 1 is confirmed and the
    two waves are worth buying.
  - **If the tail is already brushing 80°+**, then a steeper single-valued
    surface can reach section A, the whole representation change is unnecessary
    for A, and rank 1 should be spent on steepness instead. **Refuted for one
    minute.**

It is the cheapest decisive measurement in the set because it uses an instrument
that already exists, on a frame that already renders, and because it converts
this project's longest-standing `0.0000` into a distance.

---

## 7 · Reproducing this

Three read-only scripts in `gauntlet/sea/scout/`, kept out of `reference-impl/`
on purpose, with their logs beside them:

- `measure-overturning.py` — the scene's breaker class, the nonlinear surface
  state and its clamp, the closed-form ceiling, the face-angle census (both
  branches of `SPECTRAL_ON`, two `eps`, a fine zoom) and the kinematic
  criterion. **585 s** under the contention described in §1.0.
- `measure-breaker-class.py` — the breaker class and the derived slope limits
  over the whole domain, the slope-window ladder of §1.1, and the cross-shore
  profile across the bar flank. **Seconds**, once the bay is cached.
- `figure-overturning.py` — the evidence figure,
  `evidence/s20-overturning.png`, with its caption in the sidecar
  `evidence/s20-overturning.caption.md`.

All three import `beach`, `beach_render`, `beach_foam` and `beach_plot` from
`terrain-renderer/reference-impl/` and write nothing into it. The bay is cached
to a pickle **outside the repository** (`$SCOUT_CACHE`, default `/tmp`) because
`run_bay()` costs 117.8 s and every number here needs it.

⚠️ **One defect found in the scout's own instrument and fixed in place**, because
it is the same class as §1.1's: `-∇h` is *negative* on a shoaling bed, so taking
`argmax` of the signed array found the trough's landward wall instead of the
bar's seaward flank and reported ξ = 0.509 instead of 1.110. The magnitude is
what the Iribarren number wants; the comment in the script says so.

**Nothing in this round was built, and nothing in `reference-impl/` was
modified.** `git status` was clean at the start and the only file added is this
one and its evidence figure.
