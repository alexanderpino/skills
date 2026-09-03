---
type: Technique
title: Coastal erosion — the shore profile, and why a coast smooths
description: "What waves do to the land: the equilibrium profile h = A·x^(2/3) and the one parameter it has, the Bruun rule together with the published case for abandoning it, the one-line shoreline model as a literal diffusion equation, the 42° angle at which that diffusion runs backwards, and cliff retreat as a threshold rather than a rate."
tags: [generation, coastal, erosion, shoreline, waves, sediment, authoring-time]
status: draft
generated: { by: process:claude-code, at: 2026-09-03T00:00:00Z }
sources:
  - { id: dean1991, tier: P, locator: "eq. (1) p. 54, h(y) = A·y^(2/3), attributed to Bruun (1954) on Danish North Sea and Mission Bay profiles; eq. (3) p. 54, Dean (1977) least-squares fit of h = A·y^n to the 504 Atlantic and Gulf profiles of Hayden et al. (1975) giving a central n = 2/3; eq. (4) p. 54 for the physical reading, uniform wave energy dissipation per unit volume D* = (1/h)·∂(E·C_G)/∂y, and eq. (5) p. 54 for A in terms of it; Figure 1 p. 55 for the fitted A = 0.067·w^0.44 with A in m^(1/3) and settling velocity w in cm/s; Figure 9 caption p. 59 for A(D = 0.2 mm) = 0.10 m^(1/3) and A(D = 0.6 mm) = 0.20 m^(1/3); eq. (8) p. 58 for the gravity-corrected profile whose beach face is planar, h = m·y, where eq. (1) has infinite slope; eq. (12) p. 59 for W* = (H_b/(κ·A))^(3/2) and κ ≈ 0.78; eq. (15) p. 59 for the Bruun Rule itself, Δy = −S·W*/(h* + B)" }
  - { id: cooper2004, tier: P, locator: "§3 pp. 159–160 — the claimed field verifications reviewed one at a time, the SCOR Working Group (1991) finding of predicted-versus-measured errors from +224% to −68% at Chesapeake Bay, and the statement that there has not been 'a single field verification that the Bruun Rule actually operates as Bruun (1962) envisioned it'; §4.1 p. 161 for the assumption list — no net longshore transport, no aeolian or overwash exchange, a closed 2D material balance, retreat always and accretion never — and for Zhang et al. (2004) finding no eastern-US site that conclusively meets them; p. 159 for the closure depth being put at 18 m by Bruun and at 4 m in later nourishment design, and for the US east coast shoreface reaching 10–12 m" }
  - { id: ashton2006b, tier: P, locator: "Table 1 p. 2 — five alongshore transport formulations with their maximising angles, including CERC's H_b^(5/2)·cos(φ_b−θ)·sin(φ_b−θ) peaking at 45° in breaking angle and 42° in deepwater angle, with K ≈ 0.7, ρ_s = 2.65 g/cm³, porosity 0.4; §2.3 p. 4 for the one-line derivation from mass conservation, attributed to Pelnard-Considère (1956), giving eq. (3), a diffusion equation for shoreline position, and eq. (4), μ = −(1/D)·∂Q_s/∂θ with D the shoreface depth, positive μ smoothing and negative μ growing perturbations; §3.2 p. 5 for the deepwater recast eq. (7) with K_2 = 0.34 m^(3/5)·s^(−6/5) for r.m.s. wave height and 0.15 for significant height, and eq. (8) for the diffusivity with its angle factor eq. (10); abstract p. 1 for the 35°–50° span of the deepwater maximum across formulae and for the landform list it produces, 'capes, flying spits, and alongshore sand waves'; Figure 3 p. 3 for breaking wave height and transport varying along an undulating shoreline under refraction" }
  - { id: shadrick2022, tier: P, locator: "Methods, 'Modelling' subsection p. 9 — wave attack expressed as an assailing force from wave height with an exponential decay across the platform, on a gridded cell framework, where a cell erodes only once that force exceeds a per-cell material resistance F_R, and intertidal weathering acts by lowering F_R rather than by eroding; the same passage for cliff retreat being driven exclusively at the cliff foot with subaerial weathering unrepresented. P. 3 for ~130-year mean retreat of 5.8 ± 4.0 cm/yr at Bideford and 5.9 ± 4.3 cm/yr at Scalby against a 2–25 cm/yr range along ~2 km of the same coast, 'caused by the stochastic pattern of erosion in space and time'; p. 2 for cliff erosion being intrinsically episodic" }
---
# Coastal erosion — the shore profile, and why a coast smooths

Everything else in this skill's erosion axis **roughens**. Stream power cuts valleys into a
surface and makes the divides between them sharper; thermal relaxation smooths, but only locally,
and only to a repose angle. The coast is the one process in the corpus whose governing equation is
the **heat equation** — the one-line shoreline model is a diffusion equation, literally, in the
form its authors write it [ashton2006b]. A coastline is the place where the terrain gets *simpler*.

And then there is the twist that makes the subject worth a document: **that diffusivity changes
sign.** Above a deepwater wave approach angle of about 42° it is negative, the equation runs
backwards, and the same coast that was smoothing starts growing capes and spits out of nothing
[ashton2006b]. Both behaviours come from one formula. Which one you get is a property of the wave
climate, not of the rock.

## Use this

**Three fields in — sea level, a wave-direction field, and a fetch/exposure field — and two
operators out.** Cross-shore, relax the submerged heightfield toward Dean's equilibrium profile
`h = A·x^(2/3)` measured from the waterline, with `A` set from grain size [dean1991]. In plan
view, extract the sea-level contour and run **one-line diffusion** along it with the CERC
diffusivity, whose sign flips at 42° [ashton2006b]. Where the shore is rock rather than sand,
replace the second operator with a **threshold**: erode a cell only when wave force exceeds its
resistance [shadrick2022].

**There is no canonical source for any of this as a heightfield operator; standard practice is**
to author the cross-shore shape and let the plan-view model move the contour, then rasterise. The
coastal-engineering literature models a *profile* and a *line*; nobody has published the pass that
turns either into a raster edit. What is published — and what this document is for — is every
number and every sign that pass has to get right.

**The exposure field is the input you will be tempted to skip, and it is the one that matters.**
`driver-fields.md` computes a horizon sweep and reuses it for insolation and wind shelter; fetch
is the same sweep over water, and it decides which shores get waves at all — see
`water-closed-vs-open.md` for why a closed body has none of its own. A coastline operator with a
global wave height erodes the sheltered side of an island exactly as hard as the exposed side, and
that single error is more visible than any profile constant.

**What it beats.** *A blur of the coastline mask* — the right qualitative idea, and it has no
scale: real shoreline diffusivity is a physical number with units of m²/s, so features decay at a
rate set by `L²` and by wave height to the power 12/5, and a blur radius encodes neither. *The
Bruun rule as an operator* — see below; it is one line of arithmetic with a published refutation
attached [cooper2004], and using it to *drive* a coastline rather than to estimate one number is
worse than the thing it is criticised for. *Painting sand below a height threshold* — produces a
uniform apron with no dependence on exposure, grain size, or wave angle, and therefore the same
beach on the lee shore as on the windward one. *A shallow-water or hydraulic-erosion solve at the
shore* — `shallow-water.md` and `hydraulic-erosion.md` both own real processes, and neither one is
this one: SWE at authoring resolution cannot resolve a surf zone, and fluvial transport has no
alongshore term at all. *Any tool's sea, coast or beach node* — these are UI branding
over a sea-level fill plus a distance-field apron, and the node name is not an algorithm; the
question to ask of one is which of the numbers below it hits. The diagnostic is cheap and it is
the same in every tool: **if the node has no wave-direction input, it cannot produce any result
in this document**, because every mechanism here is signed by an angle.

⚠️ **A cape, a flying spit and an alongshore sand wave are landforms, not algorithms.** There is
no spit operator. Those three are named in [ashton2006b]'s own abstract as what emerges from the
high-angle instability — one mechanism, three landforms, depending on the wave climate and how
long it runs. If you find yourself writing a `Spit` node, you have mistaken an output for a
mechanism.

## The cross-shore profile, and the one parameter it has

The shore profile is not a slope. It is concave, and it has been fitted as a power law
[dean1991]:

```
h(x) = A * x ** (2.0/3.0)     # h = depth below still water, x = distance offshore
```

Bruun (1954) found the 2/3 exponent on Danish North Sea and Mission Bay profiles; Dean (1977)
recovered it as the least-squares central value of `n` in `h = A·x^n` over **504 profiles** from
the US Atlantic and Gulf coasts [dean1991]. It is not a curve fit with no story: `n = 2/3` is
exactly the exponent for which wave energy dissipation per unit water volume,
`D* = (1/h)·∂(E·C_G)/∂x`, is **uniform across the surf zone** [dean1991]. The profile is the shape
that spreads the breaking evenly.

`A` is the entire parameterisation, and it is a property of the **sediment**, not of the waves —
which is the single most useful fact here, because it means the same wave climate builds a
different beach out of different sand. Dean's two published anchors [dean1991]:

| Grain size | `A` (m^(1/3)) |
|---|---|
| 0.2 mm (fine sand) | 0.10 |
| 0.6 mm (coarse sand) | 0.20 |

and the fitted relation to settling velocity `w` in cm/s, `A = 0.067·w^0.44` [dean1991]. Inverting
that at Dean's own two anchors gives `w = 2.49 cm/s` and `w = 12.0 cm/s`; running it forward,
`A` moves only **3.74×** across a 20× range of settling velocity, because the exponent 0.44 is a
strong damper. **So `A` is a narrow knob.** Expose it as grain size, give it a 0.05–0.25 range,
and do not expect it to be the control that makes two coasts look different — that is the wave
climate's job, not the sand's.

What `A` *does* control is width, and width is what a heightfield sees. With `x` measured from the
waterline out to a closure depth `h*`, the seaward limit is `W* = (h*/A)^(3/2)` [dean1991]:

| `A` | `h*` = 4 m | 6 m | 10 m | 18 m |
|---|---|---|---|---|
| 0.10 (0.2 mm) | 253 m | 465 m | 1000 m | 2415 m |
| 0.20 (0.6 mm) | 89 m | 164 m | 354 m | 854 m |

All computed from the two published equations; the mean slope over that width runs from about
1 in 22 for the coarse, shallow case to 1 in 134 for the fine, deep one. **Halving `A` widens the shoreface by 2^(3/2) = 2.83× at the same
closure depth**, and that is the visible difference between a Gulf barrier beach and a shingle
one.

⚠️ **`h = A·x^(2/3)` has infinite slope at the waterline, and Dean says so.** At `x = 1 cm` with
`A = 0.10` the local gradient is 0.31 — one in 3.2 — which is a cliff, not a beach face.
[dean1991] eq. (8) adds gravity to the force balance and integrates to a form that is **planar**,
`h = m·x`, in shallow water and reduces to `A·x^(2/3)` in deeper water. Use it, or splice a linear
face onto the power law over the first few cells. The pure power law drawn straight into a
heightfield puts a step at the shoreline, and it is the first thing anyone notices.

**Resolution decides whether you have a beach at all.** For `A = 0.10`, `h* = 6 m`, `W*` is 465 m:

| Domain across 4096 cells | cell size | cells from shoreline to closure |
|---|---|---|
| 10 km | 2.44 m | 190 |
| 50 km | 12.2 m | 38 |
| 200 km | 48.8 m | 9.5 |
| 500 km | 122 m | 3.8 |

At map scale the entire shoreface is **four cells**, and no profile law survives that. Above about
50 km of domain, stop authoring the profile as geometry and start authoring it as a shading and
material boundary; below it, the profile is a real feature and worth the pass.

## Retreat under sea-level rise: the rule, and the paper that says not to use it

Push the equilibrium profile up by a sea-level rise `S` and conserve sediment, and the shoreline
must move landward by [dean1991]:

```
R = S * W_star / (h_star + B)   # W* = (h*/A)^(3/2), B = berm height, h* = closure depth
```

That is the **Bruun rule** [dean1991]. It is geometry, not physics: the whole content is that a
profile translating up and back sweeps out equal cut and fill. The reason it is famous is the
amplification — with `S = 0.30 m`, `B = 2 m`, `A = 0.10` and `h* = 8 m`, the retreat is **21.5 m**,
about 72× the rise.

⚠️ **The Bruun rule has a published refutation and it must travel with the rule.** [cooper2004]
is titled *time to abandon the Bruun Rule* and concludes it "has no power for predicting shoreline
behaviour under rising sea level". The case, from the paper: the assumptions — no net longshore
transport, no aeolian or overwash exchange, a closed two-dimensional material balance, and retreat
always with accretion never — are so restrictive that Zhang et al. (2004), searching the entire
eastern US coast for a site that met them, found none conclusively; the SCOR Working Group's
review of the claimed verifications found predicted-versus-measured errors running from **+224%
to −68%**; and there has not been "a single field verification that the Bruun Rule actually
operates as Bruun (1962) envisioned it" [cooper2004].

The most useful part of the criticism for a tool builder is mechanical rather than rhetorical.
**Nearly all of the answer is `h*`, and `h*` is a convention.** [cooper2004] p. 159 records that
Bruun put the closure depth off east Florida at 18 m, while nourishment design has since used
values as shallow as 4 m. Holding everything else fixed and sweeping `h*` across exactly that
published range:

| `h*` | 4 m | 6 m | 8 m | 10 m | 12 m | 18 m |
|---|---|---|---|---|---|---|
| retreat `R` | 12.6 m | 17.4 m | 21.5 m | 25.0 m | 28.2 m | 36.2 m |

A **2.86× spread** from one unmeasured parameter, on the same rise, the same sand and the same
equation. Grain size does the same thing in the other direction: at `h* = 8 m`, moving `A` from
0.10 to 0.20 takes the retreat from 21.5 m to 7.6 m.

**So: use the Bruun rule as a scale hint and never as an operator.** It tells you that a shoreline
responds to sea level by tens of metres per decimetre, which is genuinely useful when you are
deciding whether sea level is a slider worth having. It does not tell you where the shoreline
goes, it cannot produce a shape, and a coastline node built on it will translate every coast
uniformly — which is precisely the behaviour [cooper2004] says does not happen in nature.

## Plan view: the one-line model is a diffusion equation

This is the part that generalises, and the part a heightfield tool actually wants. Track the
shoreline as a single contour `y(x)`, assume the cross-shore profile keeps its shape, and conserve
sediment. With `D` the shoreface depth, [ashton2006b] §2.3 gets

```
dy/dt = -(1/D) * dQs/dx  =  mu * d2y/dx2      # a diffusion equation
mu    = -(1/D) * dQs/dtheta                   # theta = local shoreline orientation
```

— the one-line model, whose single-contour idea goes back to Pelnard-Considère (1956)
[ashton2006b]. **Positive `μ` smooths the shoreline; negative `μ` grows perturbations**
[ashton2006b].

`Q_s` is alongshore sediment transport. The CERC form depends on the waves as
`H_b^(5/2)·cos(ψ_b)·sin(ψ_b)` where `ψ_b` is the breaking wave angle relative to the shore
[ashton2006b] — which, since `cos·sin = ½·sin(2ψ)`, is the familiar `Q ∝ H^2.5·sin(2θ)`. That form
peaks at exactly **45°** in breaking angle, reproduced numerically. But breaking angles are small,
because refraction turns waves toward the shore; the useful version is the deepwater recast
[ashton2006b] eq. (7):

```
Qs = K2 * T**0.2 * H0**2.4 * cos(psi)**1.2 * sin(psi)
K2 = 0.34            # m^(3/5) s^(-6/5), for root-mean-square wave height
K2 = 0.15            # the same constant for SIGNIFICANT wave height
```

⚠️ **Two constants, two wave-height conventions, a factor of 2.3 between them.** [ashton2006b]
gives both because `H_s ≈ 1.4·H_rms`; feed significant heights into the r.m.s. constant and every
transport rate is out by that factor. `wave-models.md` owns which height your spectrum produces —
go and check before wiring this up.

Note the exponents. Transport goes as `H0^(12/5)` and as `T^(1/5)`: **wave height is nearly
everything and period is nearly nothing.** A wave field with the right period and the wrong height
is wrong; the reverse barely matters. That is a real simplification and worth taking.

### How fast does a coast actually smooth?

Because eq. (3) is a diffusion equation, a sinusoidal shoreline undulation of alongshore
wavelength `L` decays as `exp(−t/τ)` with `τ = L²/(4π²·μ)` — the standard mode solution, which is
this document's arithmetic and not the paper's. Evaluating `μ` from [ashton2006b] eq. (8) with the
r.m.s. constant, `T = 10 s`, `H0 = 1 m`, waves straight on, and a 10 m shoreface gives
**|μ| = 0.0539 m²/s** (eq. (4)'s units, m³/s per radian divided by a depth, are m²/s):

| Alongshore wavelength | e-folding time, `H0` = 1 m | at `H0` = 0.5 m |
|---|---|---|
| 100 m | 1.3 hours | 6.9 hours |
| 1 km | 5.4 days | 29 days |
| 10 km | 1.5 yr | 7.9 yr |
| 100 km | 149 yr | 786 yr |

Those are upper-bound rates — real climates spend most of their time at angles that reduce `|μ|`,
and the net over a wave record is what [ashton2006b] eq. (5) computes. But the **`L²` scaling is
the design fact**, and it is the reason a coastline reads the way it does: metre-scale wiggles are
erased within a day, kilometre-scale ones within a month, and only the hundred-kilometre features
survive long enough to record anything else. Halving the wave height costs a factor of 5.3 in
rate, because `H^(12/5)`.

**This is the exact opposite of the fluvial axis, and the contrast is the point.** `stream-power.md`
describes an *advective* process: knickpoints propagate upstream, a signal travels and is
preserved, and small features are created rather than destroyed. The coast is *diffusive*: signals
do not travel, they decay, fastest at the smallest scale. Put both in one pipeline and the seam
between them — a river mouth — is where a preserved fluvial signal meets a process that erases it,
which is why deltas and estuaries are the hardest thing on any generated coast and why the honest
move is to give the river mouth a fixed sediment input and let the shoreline model spread it.

## The 42° switch, where smoothing becomes roughening

Differentiate the deepwater transport with respect to shoreline orientation and the diffusivity's
angle dependence is [ashton2006b] eq. (10), whose sign is carried by

```
(6.0/5.0) * sin(psi)**2 - cos(psi)**2
```

That expression is zero at `arctan(sqrt(5/6))`, which is **42.392°** — and the same angle is where
eq. (7)'s transport is maximised, recomputed here by two independent routes that agree to four
decimals against the paper's stated "approximately 42°" [ashton2006b]. Reproducing it is the
cheapest possible check that you transcribed four exponents correctly; get one wrong and the
crossing moves several degrees.

Below 42°, `μ` is positive and the coast smooths. **Above 42°, `μ` is negative, the diffusion
equation runs backwards, and perturbations grow** — this is the high-angle wave instability, and
it is what builds capes, flying spits and alongshore sand waves [ashton2006b]. The mechanism is
refraction, and it is worth understanding because it is counter-intuitive: at high deepwater
angles, turning the shore *toward* the waves increases the breaking angle but also stretches the
crests and lowers the breaking height, and past 42° the height loss wins [ashton2006b].

Three consequences a tool must respect:

- **A single wave direction is a modelling decision with a visible outcome.** 42.4° of the 0–90°
  range is stable and the remaining **52.9%** is unstable, so a coast forced by one direction is
  overwhelmingly likely to be in one regime or the other, permanently. Real coasts are marginal:
  [ashton2006b] §3.3 computes an instability index of 0.02 — essentially balanced — for the Outer
  Banks. **Drive the model with a wave-angle distribution, not a vector**, and the balance between
  smooth and cuspate becomes a knob.
- **It is not unique to CERC.** [ashton2006b] compares five transport formulations and every one
  has a deepwater maximum, between 35° and 50°; the threshold is a consequence of energy
  conservation and Snell's law, not of one empirical fit. So the instability is not an artefact
  you can tune away.
- **Refraction makes wave height vary along an undulating shore** [ashton2006b] Figure 3 — energy
  converges on headlands and spreads in bays. That is the classical straightening mechanism, and
  in this framework it is not a separate rule: it is where the diffusivity comes from.

`wave-models.md` already owns the machinery you need to evaluate this — the travel-time/eikonal
field whose iso-lines are refracted wavefronts, and the `H ≈ 0.78·h` breaking criterion. Do not
rebuild it here; sample the shore-normal and the local wave direction out of it and feed `ψ`.

## Cliff coasts are a threshold, not a rate

Everything above assumes a sediment budget. A rock coast has none, and the model changes shape
entirely. In the coupled rock-coast model of [shadrick2022], wave attack is expressed as an
**assailing force** — wave height with an exponential decay across the platform — on a grid of
cells, and **a cell erodes only once that force exceeds a per-cell material resistance `F_R`**;
weathering does not erode, it lowers `F_R` until waves can [shadrick2022].

Three things follow, and each is a modelling instruction:

- **It is a threshold, so the output is episodic.** [shadrick2022] p. 2 states that cliff erosion
  is intrinsically episodic; p. 3 reports a ~130-year mean retreat of 5.8 ± 4.0 cm/yr at one site
  and 5.9 ± 4.3 cm/yr at another, against a **2–25 cm/yr range along ~2 km of the same coast**,
  attributed to "the stochastic pattern of erosion in space and time". A cliff operator that
  retreats every cell by the mean rate produces a smooth wall and is wrong by more than an order
  of magnitude locally. Retreat in blocks, at intervals, or not at all.
- **The forcing is concentrated at one elevation.** Retreat in that model is driven exclusively at
  the **cliff foot**, with subaerial weathering and groundwater unrepresented [shadrick2022]. So
  the operator is a *notch* cut in a band around sea level, and the face above it fails by
  collapse — which is `thermal-and-aeolian-erosion.md`'s repose-angle relaxation, run on the
  material the notch undercut, not a second coastal process.
- **`F_R` is where lithology enters, and it is one number per cell.** [shadrick2022] is explicit
  that a single resistance value is a heavy simplification folding mechanical, geological and
  structural controls together — but that is exactly the interface a heightfield tool has:
  `stratigraphy-and-lithology.md` already turns a bed stack into a per-cell erodibility `K`, and
  `F_R` is that same field read by a different operator. Hard bands make headlands and stacks; soft bands make bays. That is the whole of it.

**The crossover between the two operators is the sediment supply, not the rock type.** A cliff
with a wide beach in front of it is protected — the waves never reach the foot — and a cliff with
no beach is attacked at every high tide. So the two operators are coupled through the same
sediment the one-line model is moving, and a tool that runs them independently will put bare
cliffs behind wide beaches.

## Where this sits in the pipeline

**After tectonics and fluvial erosion, before the material pass, and it needs sea level to exist
first.** The coast is defined by a contour, so nothing here can run until a sea level has been
chosen; and it is the *last* geometric process, because it consumes what the river network
delivered.

Read it as a **driver-field consumer**, in `driver-fields.md`'s sense: three fields in, and each
one is a bake rather than a per-cell query.

| Field | What it is | Where it comes from |
|---|---|---|
| Sea level | one scalar | authored; everything below is a contour of it |
| Exposure / fetch | per-cell, over water | the same sweep `driver-fields.md` uses for wind shelter |
| Wave angle `ψ` | per-shoreline-cell | shore normal from the contour, wave direction from `wave-models.md` |

⚠️ **Run the coastal pass after erosion, not before.** A coastline cut into a pre-erosion surface
gets re-cut by every subsequent hydraulic pass, and the rivers then drain into a shoreline that no
longer exists. The reverse of `impact-craters.md`'s instruction, and for the same reason: a crater
is a landform that later processes should modify, while a shoreline is a boundary condition that
later processes would destroy.

## The crossover that changes the answer

| Situation | Do | Because |
|---|---|---|
| Domain under ~50 km across | Author the cross-shore profile as geometry | The shoreface is tens of cells wide and reads as a landform |
| Domain over ~50 km | Profile becomes a material boundary, not geometry | Four cells cannot hold a power law |
| You need one number for "how far back does the sea come" | The Bruun rule, stated as an estimate | It is the right order and it is honest about being geometry [dean1991] |
| You need a coastline *shape* | One-line diffusion, never Bruun | Bruun translates uniformly; [cooper2004] is the reason not to trust that |
| Sandy coast, waves mostly shore-normal | Positive `μ` — the coast smooths, fast at small `L` | `τ = L²/(4π²μ)`; metre-scale wiggles die in hours |
| Sandy coast, waves mostly oblique | Negative `μ` — capes and spits grow | Past 42.392° the diffusion runs backwards [ashton2006b] |
| You want both on one map | Give the wave climate an angular distribution | Real coasts sit near the balance point [ashton2006b] |
| Rock coast | Threshold on `F_R`, notch at the foot, repose collapse above | A cliff has no sediment budget to diffuse [shadrick2022] |
| Cliff with a wide beach | Suppress the notch | The waves do not reach the foot |
| A river mouth | Fixed sediment input, then let the shoreline model spread it | Advective process meeting a diffusive one; see `stream-power.md` |

## How this fails, and what it looks like

| Symptom | Mechanism | Fix |
|---|---|---|
| A step or wall at the waterline | `h = A·x^(2/3)` drawn to `x = 0`, where its slope is infinite | Splice a planar face — [dean1991] eq. (8) is the gravity-corrected form |
| Every beach the same width regardless of sand | `A` not exposed, or exposed and ignored | `W* = (h*/A)^(3/2)`: halving `A` widens the shoreface by 2^(3/2) = 2.83× |
| Beaches invisible at map scale, and tuning does nothing | Shoreface is under ~5 cells wide | Above ~50 km of domain, express the profile as material, not height |
| Sheltered lee shores eroded like exposed ones | No fetch/exposure field; one global wave height | Bake exposure with `driver-fields.md`'s sweep; `H0^(12/5)` makes the difference enormous |
| Transport rates out by ~2.3× | Significant wave height fed into the r.m.s. constant | `K_2` = 0.34 for `H_rms`, 0.15 for `H_s` [ashton2006b] |
| The whole coast retreats by the same distance | Bruun applied per-cell as an operator | Bruun is a one-number estimate; use one-line diffusion for shape [cooper2004] |
| Sea-level retreat numbers feel arbitrary | They are — `h*` is a convention | 4 m to 18 m of assumed closure depth spans 2.86× in retreat [cooper2004] |
| Coastline is uniformly smooth, everywhere, always | Diffusivity forced positive; one wave direction, shore-normal | 52.9% of the angle range is unstable — drive with a distribution |
| Grid-scale noise on the shoreline explodes | Negative `μ` with no regularisation: backward diffusion amplifies the smallest `L` fastest | Cap the instability with wave shadowing, or clamp `ψ` below 42.392° |
| Capes and spits never appear at any setting | Wave angles never exceed 42° | The instability threshold is a deepwater angle, not a breaking angle — refraction has already reduced the latter |
| Headlands and bays do not track the geology | `F_R` is a global constant | One resistance per cell, from `stratigraphy-and-lithology.md` |
| Cliffs are smooth vertical walls | Mean retreat rate applied uniformly | Erosion is threshold-crossing and episodic: 2–25 cm/yr across 2 km of one coast [shadrick2022] |
| Bare cliffs standing behind wide beaches | Cliff and beach operators run independently | The beach is the cliff's armour; couple them through the sediment |
| Rivers drain to a shoreline that is not there | Coastal pass run before hydraulic erosion | Sea level and the coastal pass come last |
