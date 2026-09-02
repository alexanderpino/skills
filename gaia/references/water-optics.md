---
type: Technique
title: Water optics — absorption, refraction, and the two-sided interface
description: "The physical quantities that make water look like water: per-channel absorption with depth, the two attenuation coefficients, and the interface read from both of its sides."
tags: [simulation, water, optics, absorption, refraction, physics]
status: draft
generated: { by: process:claude-code, at: 2026-09-02T00:00:00Z }
sources:
  - { id: popefry1997, tier: P, locator: "the tabulated pure-water absorption spectrum, 380-700 nm, and its minimum at 417.5 nm" }
  - { id: braun1993, tier: P, locator: "the identification of visible water absorption as O-H vibrational overtones" }
  - { id: lee2015, tier: P, locator: "the replacement Secchi relation, Z_SD as the reciprocal of the minimum diffuse attenuation" }
  - { id: nicodemus1963, tier: P, locator: "the invariance of L over n-squared along a ray and across a smooth boundary" }
  - { id: solonenko2015, tier: P, locator: "the inherent optical properties tabulated per Jerlov water type" }
  - { id: schlick1994, tier: P, locator: "the Fresnel approximation and its stated accuracy for common dielectrics" }
  - { id: bornwolf_optics, tier: F, locator: "the exact unpolarised Fresnel reflectance for a dielectric interface" }
  - { id: iop_split, tier: F, locator: "the beam-versus-diffuse attenuation split" }
---
# Water optics — absorption, refraction, and the two-sided interface

Water's colour is not a swatch and its transparency is not an alpha value. Both are consequences of
a handful of measured coefficients and one refracting boundary, and picking them from physics
rather than a colour picker is the difference between "blue-tinted glass" and *this specific water*.

**Scope.** This document owns the *quantities*: what they are, where they come from, and which of
them a body must carry. How they are gathered into pixels — caustics, glints, screen-space
reflection and refraction, underwater passes — belongs to the rendering axis. Where a technique
appears below, it appears only to name the quantity it consumes.

## Use this

**Ship a per-body optical descriptor, never a global water constant.** Ocean, clear lake and turbid
river must not share one extinction. The minimum set:

```
a(lambda)     absorption coefficient        [1/m]   per channel
b_b(lambda)   backscatter coefficient       [1/m]   per channel
K_d(lambda)   diffuse attenuation           [1/m]   per channel   <-- NOT the same as a + b
phase_g       scattering asymmetry          [-]     forward-peaked for natural water
ior           index of refraction           [-]     1.31 - 1.47 across natural liquids
```

**Take pure-water absorption from Pope & Fry above 380 nm** [popefry1997]. It is the modern
measurement, and the shape is the entire shallow-to-deep colour ramp:

```
a(417.5 nm) = 0.0044 m^-1      # the minimum
a(700   nm) = 0.624  m^-1      # 141x higher
# a three-channel sample at 610 / 550 / 450 nm: 0.2644, 0.0565, 0.00922 m^-1
```

⚠️ **Do not source blue absorption from Smith & Baker (1981).** That era's measurements were
scattering-contaminated and put `a(420)` about **3.4x too high**, which desaturates clear water.
Smith & Baker remains correct for UV below 380 nm and for `K_d`.

⚠️ **The sample wavelengths are part of the constant.** Absorption climbs about 4% per 10 nm on the
red shoulder, so the same water sampled at 620/545/460 nm gives `(0.2755, 0.0511, 0.00979)` instead.
Two triples that disagree may be disagreeing about *where they were sampled*, not about the water.
Quote the sample points with the numbers, always.

**Why water is blue at all**: its visible absorption is the high-order overtone band of the O–H
stretch — **vibrational, not electronic** [braun1993]. Water is one of very few substances whose
visible colour comes from vibrational spectroscopy. It is not sky reflection, and a renderer that
ships a flat "water colour" has thrown away the strongest cue water has.

## Two attenuation coefficients, not one

The trap that survives longest because a single lumped extinction looks reasonable until someone
measures it [iop_split]:

- **`c = a + b`** — **beam** attenuation. It governs a *sharp sightline*: how fast a submerged
  object's own radiance is lost on the way to the eye.
- **`K_d`** — **diffuse** attenuation. It governs the *ambient light column* with depth.

Because natural water scatters strongly forward, `c` typically runs **5–20x larger than `K_d`**.
Whichever of the two a single constant was fitted to, the other term is wrong by that factor.
Export both, label both, and apply each to its own path:

```
T_beam = exp(-c   * rayDistance)      # the bed's own radiance, along the refracted path
T_diff = exp(-K_d * verticalDepth)    # the light column, straight down
L      = bedRadiance * T_beam + L_scatter * (1 - T_diff)
```

**Those two terms are not a lerp and their weights do not sum to one.** They are two transport
paths. `L_scatter` — the radiance the column itself returns — is computed from `b_b`, `K_d` and the
incident irradiance; it is never an authored swatch.

**Use the refracted path length, not the straight one.** The distance travelled in water is the
vertical depth divided by the **Snell** cosine, and that is bounded:

```
mu_w        = sqrt(1 - (sin(theta_air) / n)^2)     # Snell cosine below the surface
rayDistance = verticalDepth / mu_w                 # <= 1.33 * verticalDepth for fresh water
```

The straight-ray length from a depth-buffer difference is *not* bounded — it diverges at grazing
incidence where the refracted one cannot. Measured on a reference frame, substituting it costs a
median of **12.1%** and **46.5%** at the 95th percentile.

## One interface, two reflectances, differing by 7.14x

"Fresnel", "surface reflection" and "reflectance" name **two** numbers. They are the same interface
read from its two sides, and they push a body's interior in opposite directions [bornwolf_optics].

| | From **above** — `R_ext` | From **below** — `R_int` |
|---|---|---|
| What it is | light from the air that **never enters** the water | light from the water **turned back into** it |
| It behaves as | a **loss**: subtract once, on the way in | a **trap**: it multiplies, `1/(1 - rho*R_int)` |
| Diffuse (hemispherical) value at `n = 1.335` | **6.67%** | **47.6%** |
| At normal incidence | 2.06% | — the whole cone is sub-critical |
| Past the critical angle | no critical angle exists from the thin side | **exactly 1** — total internal reflection |

The ratio is **7.14x**, and a reader who takes the wrong one is out by that factor in the direction
that makes the water too dark. The whole difference is one discontinuity, and the symmetric-looking
formula `R = (r_s + r_p)/2` does not show it.

**Total internal reflection and Snell's window.** For water to air:

```
theta_c   = arcsin(1/n)  = 48.5 deg  at n = 1.335      # ~48.6 deg at n = 1.33
cos^2(theta_c) = 1 - 1/n^2 = 0.4387                    # pure geometry, no Fresnel evaluation
```

So the entire above-water world compresses into a bright circle roughly **97° wide** overhead, and
everything outside it mirrors the bottom. That single fact is the cheapest, highest-value
underwater cue there is, and `1 - 1/n^2` is why it is worth 43.9% of a submerged upward hemisphere
before any Fresnel term is evaluated at all.

**`F0` is per body, and the engine default is wrong for water.**

```
F0 = ((n - 1) / (n + 1))^2       # fresh water, n = 1.33  ->  0.020
                                 # the generic dielectric default 0.04 is n = 1.5 (glass)
```

Ship the default and calm water reads too reflective and faintly plastic. Natural liquids span
`n ≈ 1.31–1.47` (ice → fresh → seawater → brine → oil), i.e. `F0` from about **0.018 to 0.036** — a
2x reflectance spread, so a brine pool visibly out-reflects the lake beside it. Take `ior` from the
body descriptor.

⚠️ **Radiance is not conserved across the interface.** The conserved quantity is `L/n^2`
[nicodemus1963], because étendue carries an `n^2`. For fresh water `n^2 ≈ 1.78`, so radiance
crossing from water to air is reduced by that factor. Drop the divisor and a lossless body with a
white Lambertian bed returns **more light than it received** — an energy audit that a Fresnel test
suite cannot see, because it never crosses the boundary.

**What it beats.** *Schlick's Fresnel approximation* [schlick1994] — quoted in the original as about
1% of `R` for common dielectrics, and at water's low IOR it is not: measured against the exact
equations at `n = 1.335` it runs **+11.4% at 83.8°** and **+14.3%** across the 38–79° range, and at
the Brewster angle it is **22% low**. Use the exact unpolarised form; water is the dielectric where
the fit is worst. *One lumped extinction coefficient* — see above; it is wrong by the `c`/`K_d`
ratio whichever way it was fitted. *A flat authored water colour* — discards the depth ramp, which
is the strongest realism cue water has and is entirely a function of the bathymetry. *A global water
constant for every body* — the descriptor above exists because ocean, lake and river genuinely
differ by more than a tint.

## What actually moves water off pure blue

Three constituents, and they are **not** interchangeable murkiness sliders:

| Constituent | Optical effect | Reads as |
|---|---|---|
| **Phytoplankton / chlorophyll** | absorbs blue (~440 nm) and red (~675 nm) | **Green.** Productive lakes and blooms |
| **CDOM / gelbstoff / tannins** | absorption rising steeply into the blue; **scatters not at all** | **Transparent but dark.** Tea-coloured shallow, near-black deep |
| **Suspended mineral sediment** | scattering, near spectrally **flat** | **Brightens.** Turquoise to green to ochre as load climbs |

**The rule that prevents most mistakes: CDOM darkens, sediment brightens.** They are opposite
controls. Blackwater is transparent and dark; turbid water is opaque and pale. Reaching for a
turbidity slider to make a tannin-stained river gives you mud.

**The authoring handle.** Secchi depth is the reciprocal of the *minimum* of the diffuse attenuation
spectrum, `Z_SD ≈ 1 / min(K_d)` [lee2015] — and which wavelength that minimum sits at is the water's
hue. So "you can see four metres down" plus a water class fully determines the optical export, which
is the bridge from an artist dial to the coefficients above.

⚠️ **Water-type presets are a real system with an untraced supply chain.** The Jerlov types have
published inherent optical properties [solonenko2015], but the numeric `K_d(lambda)` tables
circulating in blog posts and asset packs are largely untraceable to any of them. Either extract
from source, or generate the oceanic series from a published `K_d(a,b)` relation — and say in the
descriptor which you did.

## The handoff

The rendering axis owns light transport. What it needs from here, and nothing more:

| The renderer wants | Give it |
|---|---|
| Surface blend between reflection and refraction | `ior`, and the exact Fresnel form, not the fit |
| Refracted colour with depth | `c` per channel, and the **refracted** path length |
| The column's own glow | `b_b`, `K_d`, `phase_g` |
| Caustics on the bed | the surface's normals and the same `ior`; brightness is the inverse Jacobian of the refracted-ray map — **the caustic pass is theirs** |
| The underwater state | `theta_c`, and the `n^2` divisor on radiance leaving the water |
| The shallow-to-deep ramp | the bathymetry depth field — flat-coloured water is almost always a missing depth field |

## How this fails, and what it looks like

| Symptom | Mechanism | Fix |
|---|---|---|
| Water is one flat colour at every depth | The depth field is missing or ignored | The ramp is `exp(-c*L)`; feed it bathymetry |
| Clear water looks washed out and grey-blue | Blue absorption from Smith & Baker (1981) | Pope & Fry above 380 nm [popefry1997] |
| Two "correct" absorption triples disagree | They were sampled at different wavelengths | Quote the sample points with the constant |
| Water reads faintly plastic even when calm | `F0 = 0.04`, the glass default | `F0 ≈ 0.020` from the body's own `ior` |
| Every body reflects identically | A global IOR | `ior` is per body; 1.31–1.47 is a 2x `F0` spread |
| Interior is far too dark | `R_ext` used where `R_int` belonged — a factor of 7.14 | Two names, two numbers, one interface |
| A lossless pool returns more light than it received | The `n^2` divisor on radiance leaving the water is missing | `L/n^2` is the invariant [nicodemus1963] |
| Grazing reflections are too bright | Schlick's fit at water's low IOR | Exact unpolarised Fresnel [bornwolf_optics] |
| Water looks far murkier than it is | One extinction coefficient fitted to `c`, applied to the light column | `c` and `K_d` are two coefficients, 5–20x apart |
| Extinction blows up toward the horizon | Straight-ray depth difference used as the in-water path | Divide vertical depth by the Snell cosine |
| A tannin river renders as mud | Turbidity raised to darken it | CDOM darkens without scattering; sediment brightens |
| Nothing above the surface is visible from below | Snell's window not modelled | Above `theta_c` the surface mirrors the bottom; below it is a ~97° bright circle |
