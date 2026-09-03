---
type: Technique
title: Water optics — absorption, refraction, and the two-sided interface
description: "The physical quantities that make water look like water: per-channel absorption with depth, the two attenuation coefficients, and the interface read from both of its sides."
tags: [simulation, water, optics, absorption, refraction, physics]
status: draft
generated: { by: process:claude-code, at: 2026-09-02T00:00:00Z }
sources:
  - { id: popefry1997, tier: P, locator: "the tabulated pure-water absorption spectrum, 380-700 nm, its minimum of 0.0044 per metre at 417.5 nm and its rise to 0.624 per metre at 700 nm. NOT OPENED — Applied Optics is paywalled at Optica, which served only a loading shell, and no open copy was reachable from here, so no table or figure inside it is named and the two numeric values above are repeated from the bibliography entry rather than read out of the paper" }
  - { id: braun1993, tier: P, locator: "Fig. 1, the H2O against D2O spectra in the same 10 cm cell, and Table I, the gas- and liquid-phase overtone assignments that put v1+3*v3 at 698 nm; the claim that this is the only colour in nature of vibrational origin is the second paragraph, p. 612" }
  - { id: lee2015, tier: P, locator: "READ IN FULL. Section 3.2, eq. 29 — Z_SD = 1/(2.5*K_d_tr) * ln((r_T − r_w_pc)/C_t), the replacement Secchi relation, with eq. 28 the exact form before the K_T ≈ 1.5*K_d approximation; section 4, eq. 33, is the operational version, whose denominator is literally 2.5*Min(K_d(443, 488, 532, 555, 665)) and whose threshold contrast C_t = 0.013 per steradian is fixed on p. 147 from Blackwell 1946. NOTE the paper never writes Z_SD = 1/min(K_d): that shorthand is eq. 33 with the log term collapsed, and it happens to land within about 10 percent only because ln(0.135/0.013)/2.5 ≈ 0.94. Section 4 also carries the validation, N = 338, 18.2 percent mean absolute difference, R^2 = 0.96" }
  - { id: nicodemus1963, tier: P, locator: "the invariance of L over n-squared along a ray and across a smooth boundary. NOT OPENED — American Journal of Physics is paywalled at AIP and no open copy was reachable from here, so no section, equation or page inside it is named" }
  - { id: solonenko2015, tier: P, locator: "the inherent optical properties tabulated per Jerlov water type. NOT OPENED — Applied Optics is paywalled at Optica and the GEOMAR OceanRep copy that OpenAlex lists as open access served an HTML shell rather than the PDF, so no table inside it is named. This matters more than usual here, because the warning this document attaches to the entry is precisely that the circulating K_d tables cannot be traced back to it — and that trace has still not been made" }
  - { id: schlick1994, tier: P, locator: "the Fresnel approximation R(theta) = R0 + (1 − R0)*(1 − cos theta)^5, and the accuracy the original claims for it. NOT OPENED — Computer Graphics Forum is paywalled at Wiley, the Eurographics digital library copy was not reachable, and every mirror tried returned 403 or 404, so no section or equation inside it is named. The 'about 1 percent of R for common dielectrics' figure in the bibliography entry is therefore UNVERIFIED against the paper; the counter-measurement beside it, +11 percent at grazing and 22 percent low at Brewster, is this repository's own arithmetic against the exact Fresnel equations and does not depend on Schlick's text" }
  - { id: bruneton2010, tier: P, locator: "§5.2 'Sky light', sub-head 'Average Fresnel reflectance' — eq. 26 is the roughness-aware mean-Fresnel fit, plotted against the exact integral in Fig. 7; the view-direction slope variance it takes is eq. 25. Not §3, which is the ocean model" }
  - { id: bornwolf_optics, tier: F, locator: "the exact unpolarised Fresnel reflectance for a dielectric interface, and the Snell relation behind the critical angle. NO LOCATOR — not obtained, and deliberately not guessed. The section number this entry used to carry was withdrawn as unchecked and no edition was ever named; three attempts across two agents have failed on Cambridge, on cambridge.org/core and on five lending-restricted archive.org scans. The physics is canonical; the pointer is not" }
  - { id: iop_split, tier: F, locator: "no artefact: the beam-versus-diffuse attenuation split, c = a + b against K_d. Ocean-optics canon with no single canonical source" }
---
# Water optics — absorption, refraction, and the two-sided interface

Water's colour is not a swatch and its transparency is not an alpha value. Both are consequences of
a handful of measured coefficients and one refracting boundary, and picking them from physics
rather than a colour picker is the difference between "blue-tinted glass" and *this specific water*.

**Scope.** This document owns the *quantities*: what they are, where they come from, and which of
them a body must carry. How they are gathered into pixels belongs to the rendering axis, and every
consumer is **named**, never left in the gap: caustics are `caustics.md`; glints, screen-space
reflection and refraction, and **the underwater view — total internal reflection, Snell's window,
the `n^2` divisor and underwater extinction — are `water-rendering.md`**, which owns the surface
from both of its sides. Where a technique appears below, it appears only to name the quantity it
consumes.

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

**Take pure-water absorption from Pope & Fry above 380 nm** [popefry1997] — a table this
repository has not been able to open, so the values below are carried from secondary sources and
should be re-derived from the paper before anyone ships them. It is the modern
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

The trap that survives longest, because a single lumped extinction looks reasonable until someone
measures it. No canonical paper states the split as such — it is standard ocean-optics practice and
is graded accordingly [iop_split] — but the coefficients on either side of it are measured and
peer-reviewed [solonenko2015]. This is a bookkeeping rule, not a contested physical claim:

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
rayDistance = verticalDepth / mu_w                 # <= 1.5094 * verticalDepth at n = 1.335
#  the bound is 1/cos(theta_c) = n / sqrt(n^2 - 1), and it is reached only at grazing incidence
```

The straight-ray length a depth-buffer difference gives you is the **unrefracted** ray, and it is
*not* bounded. It overstates the path by exactly `cos(theta_water) / cos(theta_air)`, which
diverges as `1/cos(theta_air)`:

```
theta_air     15     30      45      60      75      85       89   deg
overstated   1.6%   7.1%   20.0%   52.2%    167%    664%    3700%        # n = 1.335
```

⚠️ **Those percentages are geometry, not a measurement.** They follow from the two cosines above
and nothing else — no frame, no scene, no harness. A figure quoted in this file as *measured* would
have to name the harness that produced it the way `steadystate_discharge` names `hydrology.py`, and
this claim has none; the identity is the stronger argument anyway. What matters is the shape: the
error is negligible looking down and unbounded looking along, which is precisely how a shoreline
and a horizon are viewed.

## One interface, two reflectances, differing by 7.14x

"Fresnel", "surface reflection" and "reflectance" name **two** numbers. They are the same interface
read from its two sides, and they push a body's interior in opposite directions [bornwolf_optics].

| | From **above** — `R_ext` | From **below** — `R_int` |
|---|---|---|
| What it is | light from the air that **never enters** the water | light from the water **turned back into** it |
| It behaves as | a **loss**: subtract once, on the way in | a **trap**: it multiplies, `1/(1 - rho*R_int)` |
| Cosine-weighted hemispherical value at `n = 1.335` | **6.67%** | **47.63%** |
| At normal incidence | 2.06% | — the whole cone is sub-critical |
| Past the critical angle | no critical angle exists from the thin side | **exactly 1** — total internal reflection |

The ratio is **7.14x**, and a reader who takes the wrong one is out by that factor in the direction
that makes the water too dark. The whole difference is one discontinuity, and the symmetric-looking
formula `R = (r_s + r_p)/2` does not show it.

⚠️ **Those two are integrals, not angles — say which weighting, as with Snell's window below.**
6.67% and 47.63% are `R` integrated over the hemisphere **weighted by cosine**, i.e. what a
Lambertian body above or below the interface actually loses. They are not values at any single
incidence: at 60° the external figure is 6.01% and the internal one is *exactly 1*, because 60°
is past `theta_c`. Reproduce by cosine-weighted sampling (`theta = arcsin(sqrt(u))`, `u` uniform)
of the unpolarised `R` at `n = 1.335`. Quoting either number as "the Fresnel value at grazing" is
the error this table exists to prevent.

**Total internal reflection and Snell's window.** For water to air, at the one `n` this document
uses throughout, `n = 1.335`:

```
theta_c        = arcsin(1/n)    = 48.51 deg
cos^2(theta_c) = 1 - 1/n^2      = 0.4389           # pure geometry, no Fresnel evaluation
1/cos(theta_c) = n/sqrt(n^2-1)  = 1.5094           # the refracted-path bound above, same number
```

⚠️ **One `n` per document, and derive the rest from it.** `n = 1.33` gives `theta_c = 48.75°`,
`n = 1.333` gives `48.61°`, `n = 1.335` gives `48.51°`. A line quoting 48.6° beside `n = 1.33` has
mixed two waters — the same defect this file names for absorption sample points, in a file that
insists on exactly that discipline. The spread is real (index moves with temperature, salinity and
wavelength), so pick one, say which, and recompute rather than transplant.

So the entire above-water world compresses into a bright circle roughly **97° wide** overhead, and
everything outside it mirrors the bottom. That single fact is the cheapest, highest-value
underwater cue there is.

⚠️ **Say which fraction you mean.** The window's share of a submerged upward hemisphere is two
different numbers and they are constantly conflated:

```
solid angle      inside = 1 - cos(theta_c) = 0.3375     outside = cos(theta_c)  = 0.6625
cosine-weighted  inside = sin^2(theta_c)   = 1/n^2      outside = cos^2(theta_c) = 1 - 1/n^2
                                           = 0.5611                              = 0.4389
```

By **solid angle** — what fraction of directions — the window is **33.8%**. By **cosine-weighted**
(projected) solid angle — what fraction of irradiance arriving at a flat upward-facing surface — it
is **56.1%**, because the window sits overhead where the cosine is largest. The familiar `1 - 1/n^2`
= **43.9%** is neither of those: it is the cosine-weighted share *outside* the window, the part that
mirrors the bed. Quote the projected figure when you are reasoning about light budget, the plain
solid angle when you are reasoning about screen coverage, and never the third for either. All of
this is before any Fresnel term is evaluated.

**`F0` is per body, and the engine default is wrong for water.**

```
F0 = ((n - 1) / (n + 1))^2       # n = 1.335  ->  0.0206
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

**What it beats.** *Schlick's Fresnel approximation* [schlick1994] — reputed to be within about
1% of `R` for common dielectrics, and at water's low IOR it is not. (That 1% figure is attributed
to Schlick throughout the literature, but the paper could not be obtained here, so treat it as
**unverified**: what follows does not depend on it.) Recomputed against the exact
equations at `n = 1.335`, the signed error over 38–79° has a **maximum of +14.3%** at 78.9°, a
**minimum of −22.8%** at 51.3° beside the 53.2° Brewster angle, and a **mean of −8.9%**; at 83.8°
it is **+11.4%**. Read the statistic, not just the number: it is **not** a uniform +14.3% bias
across the range but a curve that runs low through the middle and high only at the top, so no
exposure or `F0` tweak absorbs it. Use the exact unpolarised form for offline and reference work;
water is the dielectric where the fit is worst. Note the tier: there is no peer-reviewed paper to
cite for the exact equations, because they are textbook physics and Gaia grades the textbook `F`
[bornwolf_optics] — the grade is about the venue, not about the physics.
*One lumped extinction coefficient* — see above; it is wrong by the `c`/`K_d`
ratio whichever way it was fitted. *A flat authored water colour* — discards the depth ramp, which
is the strongest realism cue water has and is entirely a function of the bathymetry. *A global water
constant for every body* — the descriptor above exists because ocean, lake and river genuinely
differ by more than a tint.

⚠️ **The real-time tier is sanctioned to use a different approximation, and it is not Schlick.**
Bruneton, Neyret and Holzschuch fit a **roughness-aware** mean Fresnel [bruneton2010] that replaces
the fixed fifth power with `pow(1 - cos(theta_v), 5*exp(-2.69*sigma_v)) / (1 + 22.7*sigma_v^1.5)`,
where `sigma_v` is the surface's slope variance toward the viewer. ⚠️ **The paper is not
self-consistent about whether that symbol carries the square**, and the two readings differ by a
square root: its eq. 25 defines `sigma_v^2` as the view-direction variance, its eq. 26 then writes
`sigma_v`, and the caption of Fig. 7 labels the fitted axis `sigma_v^2` again. Whichever you feed
it, feed it deliberately and write down which — `water-rendering.md` owns the shader form and the
transcription trap in it.

This document sanctions the fit at the rendering tier, and the reason is that it is calibrated **as a unit** against the slope distribution
rather than against a single smooth facet: at any roughness a real sea carries, the roughness term
dominates the Fresnel term at exactly the grazing angles where an exact evaluation would otherwise
be fed a mean normal that no longer describes the surface. The error it accepts, stated: it returns
a *rough-surface average*, so it is not the exact curve for any individual facet; it degenerates to
Schlick — with all of Schlick's errors above — as `sigma_v` goes to zero; and it is only as good as
the `R` handed to it, so feed it `F0` from the body's own `ior` and never 0.04. Offline, reference,
and single-facet work still take the exact unpolarised form.

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

**The authoring handle.** Secchi depth is set by the *minimum* of the diffuse attenuation spectrum
— and which wavelength that minimum sits at is the water's hue. [lee2015] eq. 33 is the operational
form, and it is worth writing out because the shorthand everyone quotes drops two of its three
parts:

```
Z_SD = ln((0.14 - R_rs_pc) / C_t) / (2.5 * min(K_d))      # Lee 2015 eq. 33
                                                          #   C_t = 0.013 /sr, from Blackwell 1946
                                                          #   R_rs_pc = R_rs at the min-K_d band
```

⚠️ **This document used to state it as `Z_SD ≈ 1/min(K_d)`, which is not what the paper says.** The
paper's denominator is `2.5·min(K_d)` and the numerator is a log contrast term, not 1. The shorthand
survives only because the two nearly cancel: the whole prefactor `ln((0.14 − R_rs)/C_t)/2.5` runs
**0.95 down to 0.85** as water goes from very clear (`R_rs ≈ 0.001`) to moderately turbid
(`R_rs ≈ 0.03`), and 0.77 by `R_rs = 0.05`. So the reciprocal is a good approximation in clear
water and progressively optimistic in murky water — use eq. 33 if the dial has to hold across water
types. Either way, "you can see four metres down" plus a water class determines the optical export,
which is the bridge from an artist dial to the coefficients above. Lee validates eq. 33 against
N = 338 measurements from `<1 m` to `>30 m`, 18.2% mean absolute difference, `R² = 0.96`, with no
regional tuning (§4).

⚠️ **Water-type presets are a real system with an untraced supply chain.** The Jerlov types have
published inherent optical properties [solonenko2015], but the numeric `K_d(lambda)` tables
circulating in blog posts and asset packs are largely untraceable to any of them. Either extract
from source, or generate the oceanic series from a published `K_d(a,b)` relation — and say in the
descriptor which you did.

## The handoff

The rendering axis owns light transport. What it needs from here, and nothing more:

| The renderer wants | Give it |
|---|---|
| Surface blend between reflection and refraction | `ior` — the exact unpolarised form offline, the sanctioned roughness-aware fit in real time |
| Refracted colour with depth | `c` per channel, and the **refracted** path length |
| The column's own glow | `b_b`, `K_d`, `phase_g` |
| Caustics on the bed | the surface's normals and the same `ior`; brightness is the inverse Jacobian of the refracted-ray map — **the caustic pass is theirs** |
| The underwater state | `theta_c`, the 47.6% hemispherical `R_int`, and the `n^2` divisor on radiance leaving the water — spent by `water-rendering.md` |
| The shallow-to-deep ramp | the bathymetry depth field — flat-coloured water is almost always a missing depth field |

## How this fails, and what it looks like

| Symptom | Mechanism | Fix |
|---|---|---|
| Water is one flat colour at every depth | The depth field is missing or ignored | The ramp is `exp(-c*L)`; feed it bathymetry |
| Clear water looks washed out and grey-blue | Blue absorption from Smith & Baker (1981) | Pope & Fry above 380 nm [popefry1997] |
| Two "correct" absorption triples disagree | They were sampled at different wavelengths | Quote the sample points with the constant |
| Water reads faintly plastic even when calm | `F0 = 0.04`, the glass default | `F0 ≈ 0.021` from the body's own `ior` |
| Every body reflects identically | A global IOR | `ior` is per body; 1.31–1.47 is a 2x `F0` spread |
| Interior is far too dark | `R_ext` used where `R_int` belonged — a factor of 7.14 | Two names, two numbers, one interface |
| A lossless pool returns more light than it received | The `n^2` divisor on radiance leaving the water is missing | `L/n^2` is the invariant [nicodemus1963] |
| Grazing reflections are too bright | Schlick's fit at water's low IOR | Exact unpolarised Fresnel offline [bornwolf_optics]; the sanctioned roughness-aware fit in real time [bruneton2010] |
| Water looks far murkier than it is | One extinction coefficient fitted to `c`, applied to the light column | `c` and `K_d` are two coefficients, 5–20x apart |
| Extinction blows up toward the horizon | Straight-ray depth difference used as the in-water path | Divide vertical depth by the Snell cosine |
| A tannin river renders as mud | Turbidity raised to darken it | CDOM darkens without scattering; sediment brightens |
| Nothing above the surface is visible from below | Snell's window not modelled | Above `theta_c` the surface mirrors the bottom; below it is a ~97° bright circle |
