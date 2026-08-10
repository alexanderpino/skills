# Liquids: Optical & Rheological Identity

The property-bundle chapter for **fluids**, the sibling of `18`'s bundle for solids. `18` answers
"what *is* this rock"; this file answers "what *is* this water" — and, past water, what makes mud,
lava, brine and tar different classes of liquid rather than differently-tinted water.

It exists because of a hole in the handoff. The engine's water shader needs a per-body extinction
`sigma` and a scatter colour, and states plainly that ocean, clear lake and turbid river must not
share one global constant (terrain-renderer `12`). Nothing in this skill produced that descriptor:
lava got a full property chapter (`19`), while water existed only as geometry and routing (`03`,
`12`). This chapter is the producer.

The doctrine boundary is unchanged: **this file decides what a liquid *is*, never how it moves.**
Waves, foam, spray and flowing surfaces are the engine's (`SKILL.md`, Cross-skill routing).

Contents: [A liquid is a property bundle](#a-liquid-is-a-property-bundle) ·
[Water's optical identity](#waters-optical-identity) ·
[The three constituents](#the-three-constituents) ·
[From terrain to optics](#from-terrain-to-optics-the-causal-chain) ·
[Water archetypes](#water-archetypes) ·
[Beyond water: the rheological axis](#beyond-water-the-rheological-axis) ·
[The liquid roster](#the-liquid-roster) · [What to export](#what-to-export) ·
[Verification](#verification) · [Sources & provenance](#sources--provenance)

## A liquid is a property bundle

The same trap as `18`, one phase over: treating a liquid as *a colour with transparency*. A liquid
is a bundle of coupled properties, and six axes separate every liquid in this chapter:

| Axis | Water | What varying it changes |
|---|---|---|
| **Dynamic viscosity** `μ` | 10⁻³ Pa·s | Wave speed and persistence, ripple cutoff, splash breakup, how fast a surface returns to level |
| **Yield stress** `τ_y` | **0** | Whether it holds a shape at all: deposit thickness, levées, plug flow, abrupt arrest |
| **Shear index** `n` | 1 (Newtonian) | The character of the arrest — sluggish-then-sudden vs smooth |
| **Emission** | none | Self-luminance (blackbody); makes the liquid a light *source*, not a lit surface |
| **Absorption / scattering / IOR** | weak, blue-biased, n≈1.33 | Whether and how far you see *into* it; the entire colour question below |
| **Surface skin** | none (surface tension only) | Crust, ice lid, oil film, foam raft — often the dominant visual, and a *different material* |

**The load-bearing one is yield stress, and it is a generation concern, not a shading detail.**
Water has `τ_y = 0`: it spreads until level and leaves no deposit of its own. Every other liquid
here has `τ_y > 0`, which means it stops at a **finite thickness on a slope**:

```
h_c = τ_y / (ρ · g · sinθ)        # critical deposit thickness on an incline θ
                                  # water: τ_y = 0 → h_c = 0 → no deposit, ever
```

That single relation is why lava and mud **build terrain** and water does not, why their deposits
have steep margins and lobate snouts, and why an unconfined flow spontaneously grows static
**levées** that channelise it (Hulme 1974, who inverts the relation to recover yield strength from
observed flow dimensions — so a landform measurement gives you the rheology parameter). If a
liquid in your world leaves a deposit, `τ_y` is the knob; if it leaves none, it is water.

## Water's optical identity

Water's colour is not a swatch. It is two measurable coefficients per wavelength — absorption
`a(λ)` and scattering `b(λ)`, with backscatter `b_b` the fraction that returns to a viewer — and
picking them from oceanography rather than a colour picker is the difference between "blue-tinted
glass" and *this specific water*.

**Why water is blue at all.** Its visible absorption is the high-order overtone band of the O–H
stretch — **vibrational, not electronic** (Braun & Smirnov 1993). Water is one of very few
substances whose visible colour comes from vibrational spectroscopy. There is nothing to absorb in
the blue until the UV, and the overtones pile up in the red:

```
a_pure(418 nm) = 0.0044 m^-1     # the minimum (Pope & Fry 1997)
a_pure(700 nm) = 0.62   m^-1     # ~140x higher
# 1/e depths: ~227 m at 418 nm, ~17.7 m at 550 nm, ~1.6 m at 700 nm
# practical: red gone by ~5 m, orange ~10 m, yellow ~20 m, green ~40 m
```

That ratio **is** the shallow→deep colour ramp. It is not sky reflection, and a generator that
ships a flat "water colour" has thrown away the strongest realism cue water has.

⚠️ **Do not source blue absorption from Smith & Baker (1981).** That era's measurements were
scattering-contaminated and give `a(420)` about **3.4×** too high, which desaturates clear water.
Use Pope & Fry above 380 nm; Smith & Baker remains correct for UV and for `K_d`.

**Two attenuation coefficients, not one.** `c = a + b` (beam attenuation) governs a *sharp
sightline* — how fast a submerged object's own radiance is lost. `K_d` (diffuse attenuation)
governs the *ambient light column* with depth. Because forward scattering dominates
(`b_f` ≳ 50·`b_b`), `c` is typically **5–20× larger** than `K_d`. Export both and label them;
collapsing them into one "extinction" makes water look far murkier than it is.

**Scattering has a direction, and engines ask for it.** `a` and `b` say *how much*; the **phase
function** says *where the scattered light goes*, and natural water is strongly forward-scattering —
the Petzold measurements that everyone's water model descends from show a phase function peaked hard
in the forward direction, which is the same fact as `b_f ≳ 50·b_b` above, expressed as an angle
rather than a ratio. Real-time renderers do not evaluate a measured phase function; they take a
single asymmetry parameter `g` and feed it to a Henyey-Greenstein-style lobe (Unreal's Single Layer
Water documents a Schlick phase function, the standard cheap HG approximation). That shader's inputs
are **scattering coefficients, absorption coefficients and a phase `g`** — plus a colour-scale term
for what is seen through the water — which is useful confirmation that the split this chapter exports
is the one the engine side wants (terrain-renderer `12`). So ship `phase_g` alongside `a` and `b_b`:
positive and large for turbid, particle-loaded water (mineral suspensions scatter forward
hardest), lower for
water whose scattering is molecular. Two failure modes it prevents: pre-summing `a + b_b` into one
"extinction" — which discards the difference between bright-and-murky (sediment) and
dark-and-clear (CDOM) — and leaving `g` at zero, which makes every water body isotropic and kills
the forward glow through a sunlit wave crest.

**The authoring handle.** Lee et al. (2015) showed the classical Secchi relation is not derivable
from radiative transfer and replaced it with a strikingly clean result:

```
Z_SD ~= 1 / min_over_lambda( K_d(lambda) )
```

Secchi depth is the reciprocal of the *minimum* of the diffuse attenuation spectrum — and **which
wavelength that minimum sits at is the water's hue**. So "you can see four metres down" plus a
water class fully determines the optical export. (The classical `K_PAR = 1.44/Z_SD` constant is
Holmes 1970, the best-performing of ~13 published constants spanning 1.27–1.86.)

## The three constituents

Everything that moves water off pure blue is one of three things, and they are **not**
interchangeable murkiness sliders:

```
a(λ) = a_w(λ) + a_ph(λ) + a_CDOM(λ) + a_NAP(λ)
b(λ) = b_w(λ) + b_p(λ)
```

| Constituent | Optical effect | Reads as |
|---|---|---|
| **Phytoplankton / chlorophyll** | Absorbs blue (~440 nm) **and** red (~675 nm), leaving a transmission window at 550–570 nm | **Green.** Productive lakes, blooms; opaque pea-soup at high load |
| **CDOM / gelbstoff / tannins** | `a(λ) = a₄₄₀·exp[−S(λ−440)]`, `S ≈ 0.012–0.022 nm⁻¹`; rises steeply into the blue. **Scatters not at all** | **Transparent but dark.** Tea/amber shallow, near-black deep |
| **Suspended mineral sediment** | Scattering, near spectrally **flat** (`b_b ∝ λ^−0.5…−1`, vs λ^−4.3 for water molecules) | **Brightens.** Turquoise → green → ochre as load climbs |

**The rule that prevents most mistakes: CDOM darkens, sediment brightens.** They are opposite
controls. Blackwater is *transparent and dark*; turbid water is *opaque and pale*. Reaching for a
turbidity slider to make a tannin-stained river gives you mud.

**Concentration → optics bridge** (Babin et al. 2003): mineral-dominated suspended matter
contributes `b_p(555)/SPM ≈ 0.5 m²/g` — and since 1 mg/L = 1 g/m³, **each mg/L of mineral load
adds ≈0.5 m⁻¹ to `b` at 555 nm**. (Dimension-check it: a coastal few-mg/L water then has `b` of
order 1 m⁻¹, and a 1000 mg/L silt river has `b ≈ 500 m⁻¹` — a millimetre-scale photon path, i.e.
opaque mud. Both are right.) Organic-dominated matter is roughly double that per unit mass,
because mineral grains are denser.

**Glacial turquoise is not Rayleigh scattering.** The popular explanation is physically impossible:
rock flour is 2–65 µm, **10–100× the wavelength**, squarely Mie/geometric where scattering is
nearly wavelength-*independent*. The defensible mechanism is two-step — flat-spectrum backscatter
shortens the mean photon path to order a metre, and over that short path `a_w` still removes red
efficiently while barely touching blue-green. Concentration is therefore the **hue** knob: more
flour → paler and greener, less → deeper blue. This is why a proglacial lake chain gets bluer
downstream as flour settles, and why one lake drifts in hue across the melt season.

## From terrain to optics: the causal chain

The point of putting this in the *generator*: every constituent has a driver this skill already
computes. Carry three scalars per water body plus depth, and derive the rest.

| Driver already in the graph | Sets | Mechanism |
|---|---|---|
| Upstream erosional yield ÷ discharge, minus settling (`04`) | **SPM** | Sediment supply and residence |
| Glacier presence and subglacial abrasion (`12`) | **SPM**, very fine, slow-settling | Rock flour |
| Catchment lithology = chalk/limestone (`11`) | SPM ≈ 0, CDOM ≈ 0 | Aquifer filtration, base-flow dominance |
| Catchment lithology = karst + CO₂-rich springs (`11`) | SPM as authigenic CaCO₃ | Dissolution → degassing → in-situ precipitation |
| Catchment lithology = shield/granite, low relief (`11`) | All three low | Resistant rock, low denudation |
| Young orogen, high relief + high precipitation (`02`, `13`) | SPM high | Intense mechanical erosion of immature rock |
| Peat / bog / wetland cover, podzolic soils (`13`) | **CDOM**, 5–19 m⁻¹ | Humic and fulvic leaching; peat is the top DOC-exporting biome |
| Lake residence time × depth × temperature × nutrient load (`03`, `13`) | **Chl** | Eutrophication |
| Discharge and season (`03`, `13`) | Modulates SPM **and** CDOM | Both are discharge-driven and flashy |
| Water-body depth (`03`, `12`) | Perceived saturation | Longer path → more red removed → bluer, then darker |

**Seven rules that fall out, and are worth stating as doctrine:**

1. **Sediment is a supply-and-residence problem, not a slope problem.** `SPM ≈ (upstream yield) /
   discharge × (1 − settled)`, with settling rising with residence time and grain size. This single
   rule generates the whole proglacial lake chain — milky at the snout, progressively bluer
   downstream — for free.
2. **Lithology sets the particle's optical *character*, not just its amount.** Carbonate → bright,
   low-absorption → turquoise. Quartz flour → bright neutral → cyan-white. Iron-rich mafic or
   lateritic → strongly blue-absorbing → ochre at the *same* SPM. Volcanic ash → very low density,
   very high mass-specific scattering → intensely milky at low mass loading.
3. **A glacier does not automatically mean turquoise.** Turquoise needs fine SPM *and* low CDOM
   *and* depth. A glacier draining a peaty forefield gives murky olive-brown. Gate turquoise on
   `a_CDOM(440) < ~0.5 m⁻¹`.
4. **Peat is a step function, not a gradient.** Past roughly 3–5 m⁻¹ the blue channel is dead
   within 30 cm and the body reads black-from-above regardless of anything else. Below ~1 m⁻¹ it
   merely tints. Model the sharp perceptual transition.
5. **Turbidity and CDOM are antagonistic.** Sediment brightens, CDOM darkens — so a
   blackwater–whitewater confluence is one of the highest-contrast features in nature. Treat
   confluences of contrasting water types as a first-class visual event (`03`).
6. **Eutrophication is residence-gated.** Rivers rarely go green because flushing beats growth;
   long-residence, shallow, warm, nutrient-rich lakes do. Drive `Chl` from
   `min(residence, growth_timescale) × nutrients × temperature × light(1/K_d)` — note the
   self-limiting feedback, which is physically correct.
7. **Season moves all three.** Melt → SPM up; storms → SPM and CDOM up; summer stratification →
   Chl up and SPM down; autumn/winter high flow → CDOM up in forested and peat catchments.

## Water archetypes

Named presets, each a point in the three-scalar space with a distinct cause chain:

| Archetype | Cause | Optical signature |
|---|---|---|
| **Clear oceanic** | Open ocean, low productivity | Chl <0.05; deep blue, near-black at depth |
| **Glacial / proglacial** | Rock flour from subglacial abrasion (`12`) | High flat-spectrum `b_b`, low CDOM → milky turquoise; hue drifts with season |
| **Karst / travertine** | CaCO₃ precipitated in situ from CO₂-rich springs (`11`) | Same physics as glacial, cleaner and more saturated; tufa dams and cascade pools |
| **Blackwater** | Peat/podzol catchment, leached humics (`13`) | `a_CDOM(440)` 5–19 m⁻¹, no backscatter → amber shallow, near-black deep, mirror-like |
| **Whitewater (silty)** | Young orogen, high mechanical erosion | High SPM → opaque café-au-lait / ochre |
| **Clearwater** | Cratonic shield, low denudation | Low in everything; transparent, faintly green |
| **Chalk stream** | Carbonate aquifer, base-flow >75% (`11`) | Gin-clear, gravel visible; colour comes from weed, not water |
| **Eutrophic lake** | Long residence + nutrients (`03`, `13`) | Chl-driven green; opaque at high load |

Amazon terminology (Sioli's whitewater / blackwater / clearwater) maps directly onto catchment
geology, which is why it is a *generation* classification and not just a description.

### Jerlov presets, with numbers

The oceanic and coastal Jerlov types are the standard classification, and Solonenko & Mobley
(2015) publish a matched `K_d`/constituent set per type — a directly usable `{type → constants}`
lookup (values `K_d` at 490 nm, m⁻¹; Chl in mg/m³):

| Type | `K_d(490)` | Chl | Character |
|---|---|---|---|
| I | 0.029 | 0.010 | Clearest ocean — deep blue, near-black at depth |
| IA | 0.032 | 0.027 | Clear tropical blue |
| IB | 0.039 | 0.037 | Blue, slight green cast |
| II | 0.064 | 0.044 | Blue-green |
| III | 0.109 | 0.177 | Green, productive |
| 1C | 0.120 | 1.00 | Coastal green |
| 3C | 0.197 | 1.28 | Turbid green |
| 5C | 0.319 | 3.95 | Green-brown |
| 7C | 0.560 | 8.4 | Brown-green, murky |
| 9C | 1.00 | 9.1 | Very turbid inland/coastal |

`Z_SD ≈ 1/min_λ K_d`, so a type-I sea sees ~30 m down and a 9C harbour under a metre — the range
this whole system has to span. These are the *presets*; the causal chain above is how a generated
body lands between them.

## Refraction is a per-liquid property

Index of refraction is one of the six defining axes, and it is the one most often wrongly treated
as a universal constant. The engine's surface Fresnel term and its refraction bending both key off
`ior` (`F0 = ((n−1)/(n+1))²`), and across natural liquids `n` varies enough to matter:

| Liquid | `n` (≈589 nm) | Fresnel `F0` | Source |
|---|---|---|---|
| Ice | 1.31 | 0.018 | standard optics |
| Pure / fresh water | 1.33 | 0.020 | standard optics |
| Seawater (35 ‰) | 1.34 | 0.021 | Maykut & Light (Appl. Opt. 34, 1995) |
| Saturated brine (≈240 ‰) | ~1.40 | 0.028 | Maykut & Light 1995 (freezing-brine series) |
| Oil / hydrocarbon | ~1.47 | 0.036 | commonly cited; verify per fluid |

That is a **~2× spread in surface reflectance** (F0 0.018→0.036) — a brine pool visibly reflects
more than the fresh lake beside it, and an oil slick more still. So `ior` ships per body; the
engine must not hardcode 1.33. Two special cases: **emissive liquids** (lava) are dominated by
their own blackbody radiance, so surface Fresnel is a minor term and IOR is low-priority there;
and a **surface film** (oil on water) is optically a thin high-IOR layer over a low-IOR body,
which is what produces thin-film iridescence — a layered-Fresnel effect the engine renders, flagged
here by the film's presence, not a single-IOR value. Wave *refraction* (crests bending over
bathymetry) is unrelated — that is the depth-driven process of `12`, not this optical constant.

## Beyond water: the rheological axis

Water is **Newtonian**: `τ = μ·γ̇`, no threshold, no memory. Two departures matter:

```
Bingham plastic:     τ = τ_y + μ_p·γ̇      for |τ| > τ_y ;  γ̇ = 0 otherwise
Herschel-Bulkley:    τ = τ_y + K·γ̇^n      n < 1 shear-thinning (most natural suspensions)
```

Herschel-Bulkley beats Bingham for real mud because Bingham's straight line misfits the
low-shear-rate region — which is exactly where deposition and arrest happen, i.e. where the
landform is decided.

**Implementation warning.** Both laws are *discontinuous* at `γ̇ = 0` (infinite apparent viscosity),
so a naive solver either explodes or must explicitly track yield surfaces. Use **Papanastasiou
(1987) regularization** — an exponential continuation that makes the relation valid everywhere and
removes the need to track yield surfaces. This is the single most-cited practical fix and belongs
in any yield-stress flow this skill runs (`19`'s lava sim included).

What yield stress produces, visually and geomorphically:

- **Finite deposit thickness** — `h_c = τ_y/(ρ g sinθ)`, the arrest condition.
- **Levées** — unconfined flow grows static margins that channelise it. *The* diagnostic
  morphology, and why lava and debris-flow deposits look nothing like river channels.
- **Plug flow** — a rigid unsheared core riding a sheared boundary layer.
- **Abrupt arrest** — the flow stops as a body rather than thinning asymptotically.
- **Lobate snout** — steep, coarse, and often unsaturated at the front.

## The liquid roster

| Liquid | Rheology | Distinguishing property | Route |
|---|---|---|---|
| **Water** | Newtonian, μ ≈ 10⁻³ | `τ_y = 0` — the only one that leaves no deposit | this file |
| **Lava** | Bingham / HB; viscosity spans ~10¹–10¹² Pa·s by composition and temperature (VFT, Giordano et al. 2008) | **Emission** — a light source, not a lit surface; crust with cracks exposing hot core at only 0.001–0.1 area fraction (Crisp & Baloga 1990) | `19`, `11` |
| **Mudflow** (fine, cohesive) | Herschel-Bulkley; μ and `τ_y` rise **exponentially** with sediment concentration (O'Brien & Julien 1988) | Opaque, near-Lambertian, keeps its shape after stopping | `05` |
| **Debris flow** (coarse) | *Not* single-phase — governed by solid–fluid interaction and pore pressure (Iverson 1997) | Coarse unsaturated snout, grain segregation, levées | `05` |
| **Glacier ice** | Power-law creep, `n ≈ 3` (Glen 1955) — a third class: shear-thinning, no yield stress | Flows on geological timescales; parabolic profile, crevasses | `12` |
| **Slush / frazil** | Granular suspension; apparent yield stress at high packing | Strongly forward-scattering translucent medium — needs SSS, not a BRDF | `17` |
| **Tar / bitumen** | Newtonian but ~10⁸ Pa·s | Near-black, low albedo; surface relaxes over hours — a *frozen* wave field | `11` |
| **Oil film on water** | — | Damps capillary waves, cutting mean-square slope 2–3× — renders as a **smooth mirror patch**, not a stain; thin-film iridescence | export as a slope-variance modifier |
| **Hypersaline brine** | Newtonian, ρ ≈ 1.2–1.3 | Sharp visible interface *with water itself*; halite crust at margins | `16` |
| **Hot spring / geothermal** | Near-water | Mineral precipitates and thermophile mats; **builds terrace geometry** (travertine/sinter) | `11` |
| **Acid crater lake / AMD** | Near-water | Ochre ferric or milky colloidal-sulfur suspension — volumetric, not a tint | `11`, `19` |

## What to export

Per water body — both the **causal state** (what this skill decided) and the **derived optics**
(what the engine consumes), so a renderer can take whichever it supports and a human can check the
result is physical:

```
liquid_body:
  class                       # water | lava | mud | brine | ...  (the SUBSTANCE — rheology bundle)
  bodyType                    # sea | lake | pond | river | stream | estuary | wetland (03)
                              #   the HYDROLOGICAL type — selects the engine's surface/animation
                              #   model: lake = wind waves only, river = flow, sea = swell+tide
                              #   This enum is exhaustive for GENERATED water and deliberately so:
                              #   it is classified from the fill mask and flow accumulation (03),
                              #   and no classifier will ever emit a swimming pool, a tank or a
                              #   canal. Man-made bodies are AUTHORED render-side, where the enum
                              #   extends (pool | basin | tank | canal | reservoir) and most of
                              #   the natural bands gate off — terrain-renderer 12, "Man-made
                              #   water". Do not add them here; nothing upstream can produce them.
  fetchField                  # per-shoreline wave-exposure (12 sweep); the wind-wave driver for
                              #   lakes and enclosed water — NOT a flow field
  # causal state
  chl_mg_m3, cdom_a440, spm_mg_L, spm_lithology_class, mean_depth_m
  # rheology (non-water, and 0/1/none for water)
  viscosity_Pa_s, yield_stress_Pa, shear_index_n, emission_temperature_K
  # derived optics — the renderer's per-body descriptor
  ior                         # index of refraction — drives the surface Fresnel F0 and
                              #   refraction bending; do NOT let the engine hardcode 1.33
  a_RGB, b_b_RGB              # or full a(λ), b(λ) if the engine takes spectra
                              #   ship SEPARATELY, never pre-summed: engines take absorption and
                              #   scattering as distinct shader inputs (terrain-renderer 12)
  phase_g                     # scattering asymmetry, [-1,1]; forward-peaked in natural water and
                              #   strongest in particle-loaded water. The engine's phase-function
                              #   input; 0 (isotropic) is a visible wrong default
  c_RGB                       # beam attenuation: sharp sightlines
  K_d_RGB                     # diffuse attenuation: the depth-tinted column
  scatter_colour              # the multiple-scattering body colour
  # legibility / QA
  secchi_depth_m              # = 1 / min_λ K_d
  jerlov_type, forel_ule_index
```

`sigma` on the engine side is built from these — see terrain-renderer `12`. This closes the
producer gap named at the top of this file; register the fields in `08` and `27`.

## Verification

- **The depth ramp exists.** Sample one body at increasing depth: red must die first, then orange,
  then yellow, then green. A body whose hue is constant with depth has a flat colour, not optics.
- **Clear is not bright.** Deep clear water must read *near-black*; bright cyan is shallow water
  over a bright bottom. If the drop-off edge on a reef does not darken sharply, `b_b` is wrong.
- **CDOM and SPM move in opposite directions.** Raise CDOM → darker and *more* transparent; raise
  SPM → paler and *less* transparent. If both make it "murkier", they are wired to one slider.
- **Confluence contrast.** A blackwater tributary meeting a silty main stem must produce a visible
  mixing line (`03`).
- **Secchi round-trip.** `1/min_λ K_d` must reproduce the authored Secchi depth.
- **Yield stress does what it claims.** A `τ_y > 0` liquid on a slope must arrest at
  `h_c = τ_y/(ρ g sinθ)` and grow levées; if it spreads to level, the yield term is not being
  applied (`09`).
- **Water leaves no deposit.** If the water class produces a standing deposit, `τ_y` has leaked
  into it.

## Sources & provenance

- **P** — Pope & Fry, "Absorption spectrum (380–700 nm) of pure water. II" (*Applied Optics* 36(33),
  8710–8723, 1997): the modern pure-water absorption spectrum; minimum 0.0044 m⁻¹ at 418 nm.
- **P** — Smith & Baker, "Optical properties of the clearest natural waters" (*Applied Optics* 20(2),
  177–184, 1981): `K_w` reference. ⚠️ Its `a_w` in the blue is ~3.4× too high (scattering
  contamination) — superseded by Pope & Fry above 380 nm.
- **P** — Braun & Smirnov, "Why is water blue?" (*J. Chem. Educ.* 70(8), 612, 1993): vibrational
  overtone origin of water's colour.
- **P** — Lee et al., "Secchi disk depth: a new theory and mechanistic model for underwater
  visibility" (*Remote Sensing of Environment* 169, 139–149, 2015): `Z_SD ≈ 1/min_λ K_d`.
- **P** — Jerlov, *Marine Optics* 2nd ed. (Elsevier, 1976), Tables XXVI–XXVII; Solonenko & Mobley,
  "Inherent optical properties of Jerlov water types" (*Applied Optics* 54(17), 5392–5401, 2015);
  Morel (1988) for the Jerlov↔chlorophyll ladder. The per-type `K_d(490)` and Chl values in the
  preset table were **extracted from Solonenko & Mobley 2015 (Tables 3–8), fetched 2026-08**;
  their `M`/`α` CDOM parameters and small/large particle concentrations are in the same tables if
  a fuller reconstruction is needed. Williamson et al. (*L&O Letters* 8(5), 2023) give depth
  profiles for all ten types (paywalled, not obtained).
- **P** — Babin, Morel, Fournier-Sicre, Fell & Stramski (*Limnology & Oceanography* 48(2), 843–859,
  2003): mass-specific scattering ≈0.5 m²/g for mineral-dominated SPM at 555 nm.
- **P** — Carlson, "A trophic state index for lakes" (*L&O* 22(2), 361–369, 1977): the
  oligotrophic→hypereutrophic ladder tying Secchi, chlorophyll and phosphorus.
- **P** — Pitarch, van der Woerd, Brewin & Zielinski (*Earth System Science Data* 13, 481–490, 2021)
  and van der Woerd & Wernand (*Sensors* 15(10), 25663–25680, 2015): the Forel-Ule index and hue
  angle — a validated 21-class colour output. ⚠️ The numeric FU↔hue-angle boundary table was not
  retrieved; fetch before implementing the discretisation.
- **P** — Sioli, *The Amazon* (Junk, 1984): whitewater / blackwater / clearwater keyed to catchment
  geology. Consulted via Ríos-Villamizar et al.'s review, not the original.
- **P** — Hulme, "The interpretation of lava flow morphology" (*Geophys. J. R. Astron. Soc.* 39(2),
  361–383, 1974): Bingham flow on an incline; predicts levées; inverts flow dimensions to yield
  strength.
- **P** — Herschel & Bulkley (*Kolloid-Zeitschrift* 39, 291–300, 1926); Bingham, *Fluidity and
  Plasticity* (McGraw-Hill, 1922) — the latter verified only via secondary citation.
- **P** — Papanastasiou, "Flows of materials with yield" (*Journal of Rheology* 31(5), 385–404,
  1987): the exponential regularization that removes yield-surface tracking.
- **P** — O'Brien & Julien, "Laboratory analysis of mudflow properties" (*J. Hydraulic Engineering*
  114(8), 877–887, 1988): viscosity and yield stress rise **exponentially** with sediment
  concentration. Iverson, "The physics of debris flows" (*Reviews of Geophysics* 35(3), 245–296,
  1997): coarse debris flows are pore-pressure governed, not single-phase.
- **P** — Giordano, Russell & Dingwell, "Viscosity of magmatic liquids: a model" (*EPSL* 271,
  123–134, 2008); Crisp & Baloga, "A model for lava flows with two thermal components" (*JGR* 95(B2),
  1255–1270, 1990) — exposed-core area fraction 0.001–0.1. Glen, "The creep of polycrystalline ice"
  (*Proc. R. Soc. A* 228, 519–538, 1955) — `n ≈ 3`.
- **P / synthesis** — **Glacial-flour turquoise.** The popular Rayleigh/Tyndall explanation is
  physically wrong at 2–65 µm particle size (that is the Mie/geometric regime, near
  wavelength-independent scattering). The scattering-plus-red-absorption mechanism given above is
  now grounded in measured-reflectance limnology: in-situ and satellite reflectance studies of
  glacial lakes relate colour to suspended-sediment load and grain size, and report the diagnostic
  relationship that **decreasing grain size at fixed concentration shifts the reflectance peak to
  shorter wavelengths and brightens the water** — which is the concentration/particle→hue knob this
  chapter uses. Sources: Everest-region in-situ + satellite reflectance study (*Mountain Research
  and Development* 37(1), 2017); high-elevation U.S. Rocky Mountain lake-colour study
  (*Environmental Research Letters* 17, 2022). What remains unlocated is a *single* study combining
  measured reflectance, particle-size distribution and a full IOP decomposition for one proglacial
  lake; the mechanism is sound and now corroborated, the complete first-principles chain is still
  assembled here rather than quoted.
- **P/?** — Forward-peaked volume scattering in natural water: the canonical measurements are
  Petzold, *Volume Scattering Functions for Selected Ocean Waters* (Scripps Institution of
  Oceanography ref. 72-78, 1972), whose "average particle" phase function underlies most ocean-optics
  models. Cited from model knowledge and **not web-verified**; the load-bearing claim in this chapter
  is only the direction (forward-peaked, more so with particle load), which is the same fact as the
  `b_f ≳ 50·b_b` ratio taken from the sources above. The single-`g` Henyey-Greenstein reduction is
  the real-time approximation, not the measurement.
- **D** — That engine water shaders take **absorption, scattering and a phase `g` as three separate
  inputs**: Epic's Single Layer Water shading-model documentation (fetched 2026-08) — the reason
  this chapter exports them unsummed. See terrain-renderer `12`.
- **L** — The driver→constituent table, the seven doctrine rules, the archetype presets and the
  export schema are this skill's composition over the P-tier relations above.
