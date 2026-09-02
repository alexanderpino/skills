---
type: Technique
title: Wave models — spectra, trochoids, and what dispersion forbids
description: "Which wave field to synthesise for open water, which for a stylised or gameplay sea, and what the dispersion relation constrains in every one of them."
tags: [simulation, water, waves, spectra, runtime]
status: draft
generated: { by: process:claude-code, at: 2026-09-02T00:00:00Z }
sources:
  - { id: tessendorf_ocean, tier: F, locator: "the spectrum sampling and inverse-FFT displacement construction" }
  - { id: gerstner_trochoid, tier: F, locator: "the per-wave trochoid with horizontal and vertical displacement" }
  - { id: capillary_gravity, tier: F, locator: "the capillary-gravity dispersion relation and its minimum phase speed" }
  - { id: airy_coastal, tier: F, locator: "the linear dispersion relation, Green's law, the breaker index and the surf-similarity parameter" }
  - { id: coxmunk1954, tier: P, locator: "the wind-speed regressions for the sea-surface slope variance" }
  - { id: bruneton2010, tier: P, locator: "the slope-variance treatment of wave detail below the geometry band, and the solar-disc variance clamp" }
  - { id: dupuy2012, tier: P, locator: "the statistical whitecap coverage from the Jacobian's footprint mean and variance" }
  - { id: monahan1980, tier: P, locator: "the whitecap-coverage power law in wind speed at 10 m" }
  - { id: yuksel2007, tier: P, locator: "the wave-particle carrier and its subdivision rule" }
---
# Wave models — spectra, trochoids, and what dispersion forbids

A wave field is not a simulation. It is a **closed form evaluated at time `t`**, which is why an
ocean fits in a frame when a fluid solver does not, and why the same evaluator can run on the CPU
for physics and the GPU for rendering. Choosing which closed form is most of the work.

This document owns the *field*: what it is, what it may contain, and what motion it produces. How
it is shaded, filtered and drawn is the rendering axis; where a body is closed rather than open,
read the taxonomy first.

## Use this

**Open sea: a spectral FFT field in 2–4 cascades** [tessendorf_ocean]. Sample an oceanographic
spectrum into a frequency grid, inverse-FFT to a displacement map per frame, sum cascades at
different world-space patch sizes (order 400 m / 60 m / 10 m). It is the AAA default because it is
the only family that is statistically ocean-like across the whole band.

**Stylised, hero, gameplay-authored or tight-budget: a Gerstner (trochoidal) sum**
[gerstner_trochoid]. 4–16 analytic waves, each with horizontal and vertical displacement, sharp
tunable crests, direct per-wave authoring, and an analytic normal.

**Surf zone: neither.** Both above are *deep-water* models — they assume the bottom is infinitely
far away. The moment the depth field says otherwise, a separate shore-wave band owns the water; see
[the shore](#the-shore-is-a-different-field-not-a-modulation).

## What the dispersion relation actually constrains

One equation governs every model here [capillary_gravity] [airy_coastal]:

```
omega^2 = ( g*k + (sigma/rho)*k^3 ) * tanh(k*h)      # k = 2*pi/lambda, h = depth
```

It is not decoration. Four hard constraints fall out of it, and each one is a bug if you ignore it.

**1. There is a smallest possible wave.** The `k^3` term means phase speed *rises* again for very
short waves, so `c(k)` has a minimum:

```
c_min   = (4 g sigma / rho)^(1/4)    = 0.2312 m/s      # sigma = 0.0728 N/m
lam_min = 2 pi sqrt(sigma/(rho g))   = 0.01712 m       # 1.712 cm
```

Below `lam_min` ripples are damped rather than supported. **A renderer that keeps adding finer
normal-map octaves to "sharpen" calm water is fabricating detail the physics forbids**, and will
alias for it. Cut the spectrum there. (⚠️ Derive both numbers from one `sigma`; the widely-quoted
pair `23.1 cm/s at 1.73 cm` implies two surface tensions 2.5% apart.)

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

⚠️ **Elfouhaily et al. (1997)** is the unified wind- *and* fetch-parameterised spectrum spanning
gravity and capillary wavenumbers continuously, and it is the right target if you need one curve
across the whole band. Gaia does not cite it: the fullest treatment in this repo
(`water-physics/references/12b-water-provenance.md`) records that the paper is paywalled and **was
not read**, and that its equations there are an agreed intersection of four independent
restatements. Use it, and take the provenance from that file rather than from here.

**The field's slope statistics are the part the renderer actually reads.** Below the wavelength a
displacement grid can resolve, waves stop being geometry and become **variance** — and the crossover
must be handled deliberately or far water turns to plastic [bruneton2010]. Cox & Munk's photographic
regressions are the ground truth for how much slope a given wind produces [coxmunk1954]. Two limits
on quoting them: wind speed is referenced at **12.5 m**, not the 10 m of standard wind data, and the
fit is calibrated only over **1–14 m/s** — do not extrapolate to storm winds.

## The Jacobian is a free product; use it

A displacement field carries horizontal motion, so it has a Jacobian:

```
J = (1 + dDx/dx) * (1 + dDy/dy) - (dDx/dy) * (dDy/dx)
```

`J <= 0` means the surface has folded through itself — a breaking crest. Threshold slightly above
zero (practice: 0.5–0.9) for a whitecap mask, accumulated with decay so foam persists behind the
crest. **This is *the* whitecap signal**; painting whitecaps any other way fights the displacement
that produced them. The prefilterable form — coverage as a statistical function of the Jacobian's
mean and variance over a footprint — is what keeps it stable at distance [dupuy2012].

Two checks that the coverage is physical rather than tuned. Whitecap coverage from wind follows a
power law with **no offset** [monahan1980], so at zero wind the sea must carry exactly zero foam
pixels; and that law puts coverage near zero around 5 m/s and conspicuous by 15 m/s, which agrees
with the Beaufort observation that whitecaps begin at Force 3. An empirical formula and a
19th-century observational scale agreeing on where foam starts is a strong argument for driving foam
from wind rather than from a constant.

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

- **Gerstner for the open sea** [gerstner_trochoid] — its loop artefact (the whole surface visibly
  repeating its motion) is inherent; irrational frequency ratios and per-wave phase mitigate, never
  remove.
- **A single FFT tile** [tessendorf_ocean] — visibly repeats from any altitude; cascades at
  near-co-prime sizes push the repeat beyond notice, but verify from maximum gameplay altitude,
  because tiling *returns* at height as the small cascades mip away.
- **Shallow-water simulation as an ocean** — no dispersion, so no groups, no swell and no correct
  deep-water motion. It is the right tool for a bounded interactive body and the wrong one for a sea.
- **Wave particles and packets** [yuksel2007] — Lagrangian carriers of wave energy advected over the
  bathymetry and rasterised into a displacement field. Refraction, dispersion and shoaling emerge
  instead of being painted; the cost is research-grade machinery and tens of thousands of carriers,
  so in production it is *targeted* (a wake, a hero cove) while the tiers above still carry the sea.
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
| Fine ripple octaves alias and never sharpen | Detail below `lam_min`, which the physics damps out | Cut the spectrum at the capillary minimum [capillary_gravity] |
| The sea reads as a metronome | One period | Superpose 2–3 periods with a slow group envelope |
| Slope variance too high at storm wind | Cox & Munk extrapolated past 14 m/s, or fed 10 m wind | Respect the calibration range and the 12.5 m reference [coxmunk1954] |
| A crisp wave shadow behind an isolated rock | Ray model with no diffraction term | State the limit; a shadow at `W/lambda ≈ 1` is wrong across its whole extent |
