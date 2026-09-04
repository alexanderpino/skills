---
type: Technique
title: Wave models — spectra, trochoids, and what dispersion actually settles
description: "Which wave field to synthesise for open water, which for a stylised or gameplay sea, and what the dispersion relation constrains in every one of them."
tags: [simulation, water, waves, spectra, runtime]
status: draft
generated: { by: process:claude-code, at: 2026-09-02T00:00:00Z }
sources:
  - { id: tessendorf_ocean, tier: F, locator: "2004 course notes, §4.3 eq. 40 the Phillips spectrum and §4.4 eq. 42-43 the Fourier amplitudes inverse-FFT'd to a height field; §4.6 eq. 44 the choppy horizontal displacement and eq. 45 the folding Jacobian" }
  - { id: gerstner_trochoid, tier: F, locator: "Finch, GPU Gems ch. 1 §1.2.3 'Geometric Waves', sub-head 'Gerstner Waves' — eq. 9 is the trochoid with lateral displacement, eq. 10-12 the analytic tangent-space basis" }
  - { id: capillary_gravity, tier: F, locator: "no artefact: the capillary-gravity dispersion relation and its minimum phase speed. Classical fluid mechanics with no single canonical paper" }
  - { id: lamb_damping, tier: F, locator: "6th ed. 1932, ch. XI Viscosity, Art. 348, pp. 623-624 — eq. 7 da/dt = -2*nu*k^2*a, eq. 8 its exponential decay, eq. 9 the decay modulus tau = 1/2*nu*k^2 = lambda^2/8*pi^2*nu" }
  - { id: airy_coastal, tier: F, locator: "no artefact: the linear (Airy) dispersion relation, Green's law, the breaker index and the surf-similarity parameter. Coastal-engineering canon with no single citable paper for the set" }
  - { id: coxmunk1954, tier: P, locator: "§6.3 'Mean Square Slopes', p. 847 — the clean- and slick-surface least-squares regressions, with W recorded at 41 ft, i.e. 12.5 m; the 1-14 m/s range and the factor two-or-three slick reduction are in the abstract, p. 838" }
  - { id: bruneton2010, tier: P, locator: "§3.2 'Model hierarchy' eq. 4, the slope variance summed over the trochoids filtered out of the geometry; §5.1 'Sun light', which clamps sigma_x^2 and sigma_y^2 to a minimum in eq. 15 so the Sun keeps a finite disc" }
  - { id: dupuy2012, tier: P, locator: "the statistical whitecap coverage from the Jacobian's footprint mean and variance" }
  - { id: monahan1980, tier: P, locator: "§5 'Conclusions', p. 2097 eq. 5 — the robust-biweight fit W = 3.84e-6 U^3.41 of Table 3, combined data set; the paper's ordinary-least-squares fit is eq. 4, W = 2.95e-6 U^3.52. U at 10 m in both" }
  - { id: yuksel2007, tier: P, locator: "§3.2 'Wave Particles' — eq. 7, the radial local deviation function, and the subdivision rule that splits one particle into three when neighbour spacing exceeds half the particle radius" }
---
# Wave models — spectra, trochoids, and what dispersion actually settles

A wave field is not a simulation. It is a **closed form evaluated at time `t`**, which is why an
ocean fits in a frame when a fluid solver does not. Choosing which closed form is most of the work
— and part of that choice is whether physics can ask the field a question cheaply, which is **not**
the same answer for every model here; see [querying the
field](#querying-the-field-is-a-per-model-question).

This document owns the *field*: what it is, what it may contain, what motion it produces, and the
**spectrum and slope statistics** that describe it. How those statistics are consumed — the
variance tensor, the roughness-aware Fresnel fit, prefiltering, the glitter BRDF — is the rendering
axis; where a body is closed rather than open, read the taxonomy first.

## Use this

**Open sea: a spectral FFT field in 2–4 cascades** [tessendorf_ocean]. Sample an oceanographic
spectrum into a frequency grid, inverse-FFT to a displacement map per frame, sum cascades at
different world-space patch sizes (order 400 m / 60 m / 10 m). It is the AAA default because it is
the only family that is statistically ocean-like across the whole band. (The spectrum, the
transform and the choppy displacement are the cited notes. **The cascade stack is not**: the notes
describe one patch, 10 m to 2 km on a side, and warn that tiling it makes the field periodic.
Layering several patch sizes is later production practice, and is credited here to nobody.)

**Stylised, hero, gameplay-authored or tight-budget: a Gerstner (trochoidal) sum**
[gerstner_trochoid]. 4–16 analytic waves, each with horizontal and vertical displacement, sharp
tunable crests, direct per-wave authoring, and an analytic normal. It is also the only family here
with a genuine **per-point evaluator**, which is what makes gameplay and physics queries cheap —
again, see [querying the field](#querying-the-field-is-a-per-model-question) before assuming the
spectral option gives you that too.

**Surf zone: neither.** Both above are *deep-water* models — they assume the bottom is infinitely
far away. The moment the depth field says otherwise, a separate shore-wave band owns the water; see
[the shore](#the-shore-is-a-different-field-not-a-modulation).

## Querying the field is a per-model question

"A wave field can be evaluated identically on the CPU for physics and on the GPU for rendering" is
true of one family here and **false of the one this document recommends**. The difference decides
how boats float, so it is a selection criterion, not an implementation detail.

- **Gerstner** [gerstner_trochoid] is a closed form with a per-point evaluator: sum 4–16 waves at
  any `(x, z, t)`, on any thread, with no GPU involved. This is the model the claim is true of.
- **A spectral FFT cascade** [tessendorf_ocean] has **no per-point evaluator at all.** The inverse
  FFT produces a whole tile or nothing. A single CPU query therefore costs either the entire
  transform run again CPU-side (the work the GPU was doing to avoid it) or a **readback** of the
  displacement texture — a pipeline stall, and at least a frame of latency, so physics is querying
  last frame's sea. Neither is "the same evaluator on both sides". Budget the usual shipped answer
  instead: a **cheap CPU proxy** — the largest cascade alone, or a few Gerstner waves fitted to the
  same spectrum — driving buoyancy and gameplay, with the understanding that physics and pixels
  agree only down to the proxy's band.

⚠️ **With choppiness on, a displacement field is not a height field.** The field displaces
horizontally as well as vertically, so the surface point that ends up above world `(x, z)` did not
start there: sampling the displacement at `(x, z)` returns the motion of the particle whose *rest*
position is `(x, z)`, which is now somewhere else. Getting the height above a given world point
requires **inverting the horizontal displacement** — two or three fixed-point iterations of
`p <- (x,z) - D_xy(p)` is the standard fix, cheap and usually sufficient — and it must happen on
whichever side asks the question. Skipping it is the boat that floats a metre beside its own wave,
worst exactly where choppiness is strongest, at the crests, where it is most visible.

## What the dispersion relation actually constrains

One equation governs every model here [capillary_gravity] [airy_coastal]:

```
omega^2 = ( g*k + (sigma/rho)*k^3 ) * tanh(k*h)      # k = 2*pi/lambda, h = depth
```

It is not decoration. Four hard constraints fall out of it, and each one is a bug if you ignore it.

**1. There is a slowest possible wave.** The `k^3` term means phase speed *rises* again for very
short waves, so `c(k)` has a **minimum**. `lam_min` is the wavelength at which that minimum occurs
— not a floor on wavelength:

```
c_min   = (4 g sigma / rho)^(1/4)    = 0.2312 m/s      # sigma = 0.0728 N/m
lam_min = 2 pi sqrt(sigma/(rho g))   = 0.01712 m       # 1.712 cm
```

⚠️ **The dispersion relation forbids no wavelength.** `omega^2 = (g k + (sigma/rho) k^3) tanh(k h)`
is positive for *every* `k`, so a real wave with a real frequency exists at every wavelength;
shorter than `lam_min` you are simply on the **capillary branch**, where `c` climbs again as the
wave shortens. Those waves are real, wind makes them, and they are the cat's-paw sparkle this skill
elsewhere asks a renderer to reproduce. What `c_min` gates is **forcing**: wind cannot raise a wave
until it can push past the slowest phase speed the surface offers, which is why a light breeze
gives patches of ripple on otherwise glassy water rather than uniform texture.

What actually removes sub-centimetre ripples is **viscous damping** — a different mechanism, at a
different scale. Deep-water amplitude decays at `alpha = 2 nu k^2` [lamb_damping] (`nu ≈ 1e-6 m²/s`),
so both the lifetime and the e-folding distance against the group speed collapse as the wavelength
falls:

```
lam = 16.5 cm  ->  e-folds over ~90 m,   ~345 s     # rings an 8 m basin many times over
lam =  3   cm  ->  ~2.1 m,               ~11 s
lam =  5   mm  ->  ~0.14 m,              ~0.3 s     # gone within centimetres of whatever forced it
```

So **cut the spectrum where viscous damping or your own aliasing budget says to, and say which one
you used.** A renderer stacking ever-finer normal-map octaves onto calm water is not fabricating
detail the physics forbids — it is adding sub-pixel detail that will alias, and that in the real
surface would have died centimetres from its source. Both are good reasons to stop; the dispersion
relation is not one of them. (⚠️ Derive `c_min` and `lam_min` from a single declared `sigma`; the
widely-quoted pair `23.1 cm/s at 1.73 cm` implies two surface tensions 2.5% apart.)

**2. Long waves outrun short ones, so a sea has groups.** In deep water `c = sqrt(g/k)`, so period
is the ordering parameter and energy travels at half the phase speed. A single period reads as a
metronome; superposing two or three in a band (7–14 s for ocean swell) with a slow envelope is what
produces sets.

**3. Period is conserved across a depth change; wavelength is not.** A train entering shallow water
keeps `omega`, so `k` must rise: **crests bunch and slow** toward shore. Solve `k(omega, h)` with a
few Newton iterations into a small 2-D lookup table offline — never per frame [airy_coastal].

**4. In shallow water celerity depends on depth alone.** `c ≈ sqrt(g*h)` for `h < lambda/20`. Two
consequences: crests rotate toward alignment with the depth contours (refraction, the strongest
single shore cue), and a shallow-water solver has **no dispersion at all** — every wavelength
travels at one speed. That is why the shallow-water equations are the wrong tool for an open sea.

## The spectrum, and how much of it is yours to choose

A spectral field is only as good as the spectrum. The standard family: **Pierson–Moskowitz** for a
fully developed sea, **JONSWAP** for a fetch-limited one with a sharpened peak, and the simplified
**Phillips** form that Tessendorf's notes popularised and most implementations still ship
[tessendorf_ocean]. Drive them from wind speed and fetch, not from an amplitude dial, so every
consumer of the sea state agrees.

⚠️ **Elfouhaily et al. (1997)**, *A unified directional spectrum for long and short wind-driven
waves* (J. Geophys. Res. 102(C7), 15781–15796; DOI 10.1029/97JC00467), is the wind- *and*
fetch-parameterised spectrum spanning gravity and capillary wavenumbers continuously, and it is the
right target if you need one curve across the whole band. **Gaia does not cite it — but the reason is that nobody
here has read it yet, not that it cannot be graded.** It is **open access**: Unpaywall reports
`is_oa: true, bronze`, and the publisher-typeset article is free at
`archimer.ifremer.fr/doc/00091/20226/17877.pdf`, hosted by Ifremer, where three of the four authors
worked. Reading it and citing it as `P [not-opened]` → `P` is outstanding work, not a closed
question.

⚠️ **This paragraph carried two wrong rounds of reasoning, in opposite directions. Both are
corrected here, and the second was the worse of the two.**

- The first round attached a **fabricated provenance chain** to a sibling skill — plausible detail
  invented around a real file.
- The second round, written as a verified audit ("checked against every ref in this repository"),
  declared that file **nonexistent** and its Elfouhaily record **imaginary**. That denial was itself
  false in every part. Checked here with `git show` against
  `origin/claude/swimming-pool-voronoi-render-m22g6r` @ `92bc35f3`:
  `water-physics/` **does** exist, `water-physics/references/12b-water-provenance.md` **is** 1299
  lines, and its lines 95–107 **do** carry the Elfouhaily entry — graded `P (attribution)` with
  DOI 10.1029/97JC00467, declaring "**The paper is NOT held in this repository and was not read**",
  and naming the equations as "the agreed **intersection of four independent restatements**":
  Mobley's *Ocean Optics Web Book*, Wang et al. 2025, Zhang et al., and Hwang & Fois.
- **The mechanism, because it will recur.** That "audit" ran against stale remote-tracking refs. Every
  negative claim in it was true of the commit the clone happened to hold and false of the branch. **A
  negative claim about a repository is only as good as the last fetch**, and a sweeping negative —
  "nowhere on any branch" — is the form most likely to be asserted without one. Fetch before you
  deny, and prefer naming the commit you checked to naming the absence.

⚠️ **This third statement also misread Gaia's own tier rule.** It said an unread source "cannot be
graded `P`". `P [not-opened]` is exactly the sanctioned form for a peer-reviewed paper nobody here
opened, and the corpus's bibliographies carry twenty entries graded exactly that way. The tier bar is peer review; `[not-opened]`
records the reading separately. A rule invented to justify an omission is worse than the omission.

**The field's slope statistics are the part the renderer actually reads.** Below the wavelength a
displacement grid can resolve, waves stop being geometry and become **variance** — and the crossover
must be handled deliberately or far water turns to plastic [bruneton2010]. Cox & Munk's photographic
regressions are the ground truth for how much slope a given wind produces [coxmunk1954]: for a clean
sea, mean-square slope rises **linearly** in wind speed and is **anisotropic**, rougher along the
wind than across it.

```
sigma_up^2    = 0.000 + 3.16e-3 * U        # along wind
sigma_cross^2 = 0.003 + 1.92e-3 * U        # across wind
sigma_total^2 = 0.003 + 5.12e-3 * U        # U in m/s
```

(The two components do not sum exactly to the total — `5.08e-3` against `5.12e-3` — because the
three regressions are fitted separately in the paper. Quote whichever you need; do not derive one
from the other two and expect the published number.)

Two limits on quoting them: wind speed is referenced at **12.5 m** — the paper says 41 feet — not
the 10 m of standard wind data, and the fit is calibrated only over **1–14 m/s** — do not
extrapolate to storm winds. A third
is worth knowing because it is usually implemented as the wrong mechanism: a **surfactant film damps
the short waves that carry most of the slope**, and slicked water measures a factor of 2–3 lower
total mean-square slope [coxmunk1954] — so an oil slick, a wind shadow or a convergence line is a
*local reduction of this variance*, not a dark decal.

That is where this document's job ends and the rendering axis begins: the variance tensor, the
solar-disc clamp on it, and the roughness-aware Fresnel fit that consumes it are how a shader spends
these numbers [bruneton2010], not what they are.

## The Jacobian is a free product; use it

A displacement field carries horizontal motion, so it has a Jacobian [tessendorf_ocean]:

```
J = (1 + dDx/dx) * (1 + dDy/dy) - (dDx/dy) * (dDy/dx)
```

`J <= 0` means the surface has folded through itself — a breaking crest. Foam is masked from a
threshold on `J` **well before** the fold, not at it: shipped values sit around **0.5–0.9**, i.e.
foam appears where the surface has compressed to roughly half to nine-tenths of its rest area, long
before `J` reaches zero. ⚠️ Do not read that as "a hair above zero" and dial in 0.05 — that
thresholds only true folds, and gives a sea with almost no foam on it. Accumulate the mask with
decay so foam persists behind the crest. **This is *the* whitecap signal**; painting whitecaps any
other way fights the displacement that produced them. The prefilterable form — coverage as a statistical function of the Jacobian's
mean and variance over a footprint — is what keeps it stable at distance [dupuy2012].

Two checks that the coverage is physical rather than tuned. Whitecap coverage from wind follows a
power law with **no offset** — `W = 3.84e-6 * U^3.41`, with `U` at 10 m [monahan1980] — so at zero
wind the sea must carry exactly zero foam pixels; and that law puts coverage near zero around
5 m/s and conspicuous by 15 m/s, which agrees
with the Beaufort observation that whitecaps begin at Force 3. An empirical formula and a
19th-century observational scale agreeing on where foam starts is a strong argument for driving foam
from wind rather than from a constant.

⚠️ **That paper publishes two fits and they are not the same curve.** `3.84e-6 * U^3.41` is its
**robust-biweight** fit; its **ordinary-least-squares** fit is `2.95e-6 * U^3.52`. They cross near
11 m/s, so whichever you did not pick is the one your foam reads wrong against at the other end of
the wind range. Name the fit beside the constant, exactly as this skill asks absorption to be
quoted beside its sample wavelengths.

⚠️ **Choppiness is the horizontal-displacement scale, and past about 1.0 it drives `J` negative over
large areas** — which reads as geometry self-intersection shimmer rather than as foam. Clamp it so
folding stays rare and foamed.

## The shore is a different field, not a modulation

Where the bed matters, the deep-water field stops being valid and a **separate shore-wave band**
takes over, cross-faded with the ambient sea over a blend band offshore [airy_coastal]:

- **Phase from travel time, not from wind.** Precompute a wave-travel-time field `tau(x)` by
  propagating a front shoreward at `c(h) = sqrt(g*h)` (an eikonal / fast-marching solve seeded from
  deep water). Iso-lines of `tau` *are* refracted wavefronts: crests wrap headlands, focus on
  points and align to every shore for free. Animate `phase = tau/T - t/T`.
- **Shoaling.** Energy-flux conservation through the slowdown pumps amplitude up; the shallow
  asymptote is Green's law, `a ∝ h^(-1/4)`. The visual is a monotonic **rise then a cut** — never a
  plain fade.
- **Breaking.** A wave breaks at roughly `H ≈ 0.78 h`. *How* it breaks is the surf-similarity
  (Iribarren) number `xi = tan(beta) / sqrt(H/L0)`: low → **spilling**, mid → **plunging**, high →
  **surging**. Beach slope and depth are both in the handoff, so breaker character per shore is
  data-driven, not a global setting.
- **Cross-fade energy down as the shore band comes up — never add them.** Added energy doubles wave
  height exactly where shoaling is already boosting it, and the blend band becomes a wall of water.

⚠️ **Refraction is not diffraction, and no ray, eikonal or travel-time model contains any
diffraction at all.** Not approximated badly — absent: a ray carries energy along a path and there
is no path into a geometric shadow. Behind an obstacle of width `W` the lee fills in over a distance
of order `W^2/lambda`, and at `W/lambda ≈ 1` — an isolated rock in ordinary swell — the shadow a ray
model carves is wrong across the whole of it. The test is one object and it is cheap: put an
isolated obstacle a wavelength across in the scene and look behind it.

## What it beats

- **Gerstner for the open sea** [gerstner_trochoid] — a finite sum of sinusoids repeats, so the
  whole surface visibly cycles through its motion; that is inherent, and irrational frequency
  ratios and per-wave phase mitigate it, never remove it. ⚠️ Do not confuse this with the *loops*
  the cited chapter names: those are vertex loops that form over a crest once the steepness sum
  `Q_i*w_i*A_i` passes 1, they are avoidable, and the chapter says how. The temporal repeat is
  not.
- **A single FFT tile** [tessendorf_ocean] — visibly repeats from any altitude; cascades at
  near-co-prime sizes push the repeat beyond notice, but verify from maximum gameplay altitude,
  because tiling *returns* at height as the small cascades mip away.
- **Shallow-water simulation as an ocean** — no dispersion, so no groups, no swell and no correct
  deep-water motion. It is the right tool for a bounded interactive body and the wrong one for a sea.
- **Wave particles** [yuksel2007] — Lagrangian carriers of wave energy, each holding a radial
  deviation function that is rasterised into a height field and subdivides into three as its
  wavefront spreads. Its real strength is *interaction*: waves raised by floating objects, and
  forces returned to them.
  ⚠️ **Do not credit this paper with refraction, dispersion or shoaling.** It solves the plain
  second-order wave equation at a **constant** wave speed, so it contains no dispersion at all —
  the "dispersion angle" a particle carries is wavefront-spreading geometry, not frequency
  dispersion. It has no bathymetry; its boundaries are container walls that reflect, and it names
  diffraction as future work. Nor is it research-grade in cost: it reports 170 fps at 100 000
  particles on 2007 hardware and says fewer than 10 000 give nearly identical results. Emergent
  refraction and shoaling over a varying bed belong to the later **wave-packet** line, which Gaia
  has not read and therefore does not cite.
- **A depth-modulated ambient field as the whole shore solution** — acceptable only where the camera
  never lingers on a beach: phases stay wind-aligned, so diagonal surf marching through knee-deep
  water survives, and nothing breaks.

## How this fails, and what it looks like

| Symptom | Mechanism | Fix |
|---|---|---|
| Surf marches diagonally onto the sand | Deep-water field modulated by depth; no refraction | Travel-time phase field [airy_coastal] |
| The whole sea visibly repeats its motion | Gerstner loop, or a single FFT tile | More cascades at near-co-prime sizes; verify from max altitude |
| Waves fade out toward shore instead of growing then breaking | Amplitude faded by depth with no shoaling gain | Green's-law rise, clamped, then cut at the break |
| A wall of water in the blend band | Ambient and shore bands added rather than cross-faded | Fade one down as the other comes up |
| Crests shimmer and self-intersect | Choppiness past ~1.0 driving `J` negative over large areas | Clamp choppiness; keep folding rare and foamed |
| Foam on a dead-calm sea | Coverage not driven by wind, or driven by a law with an offset | The power law has no offset [monahan1980] |
| Far water turns to plastic | Wave detail below the geometry band dropped instead of becoming variance | Carry it as slope variance [bruneton2010] |
| Fine ripple octaves alias and never sharpen | Sub-pixel detail added past the aliasing budget — and at those wavelengths the real surface damps within centimetres | Cut on viscous damping or on footprint, not on `lam_min`: it is a phase-speed minimum, not a shortest wave [lamb_damping] |
| A boat, buoy or splash sits a metre beside the wave it should be riding | Displacement field sampled as if it were a height field, with choppiness on | Invert the horizontal displacement — two or three iterations of `p <- (x,z) - D_xy(p)` |
| CPU physics disagrees with the rendered sea, or a readback stalls the frame | An FFT cascade queried per point; it has no per-point evaluator | A cheap CPU proxy fitted to the same spectrum, and state the band where they agree |
| The sea reads as a metronome | One period | Superpose 2–3 periods with a slow group envelope |
| Slope variance too high at storm wind | Cox & Munk extrapolated past 14 m/s, or fed 10 m wind | Respect the calibration range and the 12.5 m reference [coxmunk1954] |
| A crisp wave shadow behind an isolated rock | Ray model with no diffraction term | State the limit; a shadow at `W/lambda ≈ 1` is wrong across its whole extent |
