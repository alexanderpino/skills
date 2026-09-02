---
type: Technique
title: Water rendering — drawing the surface, not simulating it
description: "Surface geometry, reflection, refraction, depth colour, foam compositing and the underwater view for water on terrain, spined on the slope-variance transition from geometry to BRDF."
tags: [rendering, rasterizer, water, shading, real-time]
status: draft
generated: { by: process:claude-code, at: 2026-09-02T00:00:00Z }
sources:
  - { id: bruneton2010, tier: P, locator: "§3-4, the slope-variance tensor and the roughness-aware Fresnel fit" }
  - { id: coxmunk1954, tier: P, locator: "the slicked-water mean-square-slope reduction, and the along-wind anisotropy of the slope distribution" }
  - { id: ross2005, tier: P, locator: "the Gaussian-slope BRDF with Smith masking" }
  - { id: dupuy2012, tier: P, locator: "the erf-form whitecap coverage over the Jacobian footprint statistics" }
  - { id: deliot2023, tier: P, locator: "the binomial-law glint counting on anisotropic grids" }
  - { id: johanson2004, tier: F, locator: "the projected-grid construction and its horizon behaviour" }
  - { id: vlachos2010, tier: F, locator: "the dual phase-offset flow-map sampling with triangle-wave blend" }
  - { id: unrealwater, tier: F, locator: "the water mesh quadtree and the single-layer-water shading interface" }
---
# Water rendering — drawing the surface, not simulating it

**Tier: real-time rasteriser**, with one near-real-time crossover named at the end.

**Boundary, stated once.** The wave field, the dispersion relation, shoaling and breaking, and the
absorption law are physics and belong elsewhere: `wave-models.md` for the spectrum, its slope
statistics and the Jacobian that signals a breaking crest, `shallow-water.md` for depth-dependent
wave behaviour, `water-optics.md` for Beer–Lambert absorption, the two attenuation coefficients,
refraction and total internal reflection, and `water-closed-vs-open.md` for what a pool is allowed
to do that a sea is not. Caustics are `caustics.md`. **This document owns what happens after those
fields exist**: geometry, reflection, refraction sampling, depth colour, foam compositing, the
shoreline — and, because it owns the surface from *both* of its sides, the underwater view. If you
arrived looking for why water is blue, you want `water-optics.md`.

**One owner per quantity, where this document and `water-optics.md` touch.** Three numbers used to
be answered twice, differently. They are answered once now, there, and consumed here: the in-water
path length is the **refracted** one and never a depth-buffer difference; the volume term is **two
transport paths**, not a lerp toward an authored swatch; and the Fresnel form below is a
**sanctioned approximation** — `water-optics.md` grants it for the real-time tier, names the error
it accepts, and holds the exact unpolarised equations for offline work.

## Use this

**A world-space displaced grid on the water datum, shaded through a slope-variance pipeline**
[bruneton2010]. Two halves, and the second is the one that separates good water from plastic:

1. **Geometry**: reuse the terrain's LOD machinery, flattened onto the water datum — concentric
   rings or an error-refined quadtree, world-anchored. It clips to body extents, matches the
   terrain's error currency at the shoreline, streams with the tiles, and inherits the crack and
   morph contracts already paid for. The engine-native water systems have converged on exactly
   this shape — a convergence documented only in engine documentation, with no peer-reviewed
   source behind it; standard practice is what the shipped systems do [unrealwater].
2. **Shading**: as waves shrink below what geometry and then normals can resolve, **do not
   discard the detail — move it into a slope-variance tensor that widens the BRDF lobe**
   [bruneton2010]. Because it is the same quantity moved between representations, displaced
   geometry near, normal detail mid, and statistical BRDF far join without a pop or a seam.

**What it beats.** *A projected grid* — no canonical paper; the standard exposition is an MSc
thesis [johanson2004] — a screen-space grid projected onto the water
plane, giving near-perfect vertex distribution for free and one mesh for an infinite ocean; it
loses because vertices swim at the horizon edge as the camera turns, which a temporal resolve
punishes, and because per-body clipping and art direction are both awkward. Still defensible for a
single infinite ocean with a camera that never looks straight down. *Ad-hoc distance fade of wave
detail* — the thing the variance tensor replaces; it throws the variance away instead of moving it,
which is the direct cause of the plastic horizon. *Per-pixel raymarched displacement* — the right
answer for a hero close-up with no mesh budget, and the wrong one the moment displacement must read
across the whole screen; see `heightfield-raymarching.md` for the traversal.

**Crossover — the fullscreen-triangle analytic plane.** Draw no water geometry: one fullscreen
triangle, a per-pixel view ray, `t = (h_water - camPos.y) / rayDir.y`, reject against the depth
buffer, shade at the hit. The entire geometry problem — LOD, cracks, skirts, horizon — evaporates
and the horizon becomes pixel-exact. Take it for a single flat datum, for indie budgets, and for
tool viewports that need "sea level" visualized without buying the LOD apparatus. It costs you
displacement (normals only, unless you march), rasterized motion vectors (derive them analytically
or the frame ghosts), and cheap handling of many bodies at many elevations.

## The variance spine, and the four ways distance kills water

Water that reads beautifully at 50 m reads as shrink-wrapped perspex at 5 km. This is a filtering
failure, not an art problem, and it has four separable causes.

**One: thrown-away slope variance.** As distance grows, the waves inside one pixel footprint grow
without bound, per-pixel normals converge to the mean — vertical — and every bit of slope variance
those waves carried is silently discarded. Near-zero variance collapses the specular lobe toward a
Dirac, and energy conservation makes what survives *brighter* as it narrows: fireflies at best,
mirror-flat plastic everywhere else. MSAA does not help; the highlight is smaller than the geometry
it sits on. The fix is the tensor above: accumulate what geometry and normals did not resolve, in
the wind frame, and feed it to the BRDF [bruneton2010].

Two details worth taking verbatim. Nyquist argues for a two-grid-cell geometry cutoff and it
over-blurs in practice; a smoothstep between roughly one and two-and-a-half cells is the shipped
compromise. And **clamp the variance to a minimum matching the solar disc** (0.53°), or dead-calm
water still produces a Dirac. That clamp is what makes a mirror-still lake render a sun of the
right angular size instead of one blown-out pixel.

**Two: Fresnel that ignores roughness.** Plain Schlick assumes a smooth surface, so it gives one
curve no matter how rough the water is. A real rough surface departs from it in *both* directions:
microfacet masking pulls grazing reflectance well below Schlick — which is why a low-variance
distant ocean goes to near-total mirror at the horizon, the chrome-dome look — while the spread of
facet orientations pushes reflectance *above* Schlick through the middle of the range. The
roughness-aware fit captures both, and it is one line [bruneton2010]:

```hlsl
float sigma_v = sqrt(sigma_x2*cos2Phi + sigma_y2*sin2Phi);   // slope variance toward the viewer
float m = pow(1.0 - cosThetaV, 5.0*exp(-2.69*sigma_v))       // roughness rides in the EXPONENT
        / (1.0 + 22.7*pow(sigma_v, 1.5));
float F = R + (1.0 - R) * m;                                 // R = F0 from the body's own ior
```

⚠️ **`exp(-2.69*sigma_v)` scales the exponent; it is not a factor on the result.** The
transcription that multiplies Schlick's fifth power by it is a different function: it can only ever
*lower* reflectance, so it loses the mid-range lift entirely. At `sigma_v = 0.2` and a 70° view the
two differ by 2.6x, and both collapse to Schlick at `sigma_v = 0` — so a calm-water unit test
passes and the error shows up only on rough water at grazing angles, which is the case the whole
section exists to fix.

⚠️ **This is a fit, not the Fresnel equations.** `water-optics.md` sanctions it at the real-time
tier — it is calibrated *as a unit* against the slope distribution, which is why it beats an exact
per-facet evaluation fed a mean normal that no longer describes the surface — and it names the
error that approximation accepts. Use the exact unpolarised form for offline renders, reference
images, and anywhere a single flat facet is what is being evaluated.

Keep the Smith masking term in the sun lobe as well — that is what stops grazing-angle
over-brightening, and with a statistical BRDF [ross2005] it also gives wave self-shadowing free
rather than needing a shadow map.

**Three: binary whitecaps.** The displacement Jacobian is `wave-models.md`'s signal and its
breaking threshold is set there; what fails *here* is the filtering. A per-pixel threshold on it is
correct up close and disintegrates at distance — sub-pixel foam either aliases into shimmer or
vanishes, and the far sea loses the speckle that tells the eye it is rough. Assume the Jacobian is normally distributed
within the footprint and integrate coverage in closed form [dupuy2012]:

```
W ~= 0.5 + 0.5 * erf( (sqrt(2)/(2*sigma_A)) * (eps - mu_A) )
#  mu_A, sigma_A^2 = footprint mean and variance of the Jacobian
#  both are linearly prefilterable -> free hardware mipmapping and aniso
```

Ground-truth the *amount* against the oceanographic wind→coverage power law, which `wave-models.md`
states with its no-offset property and its Beaufort cross-check: essentially no foam at 5 m/s,
conspicuous by 15 m/s. The rendering stake in it is one sentence — the exponent is steep enough
that coverage must be driven by the wind, never by a tuned constant — and the law itself is not
restated here.

**Four: everything else that flattens the far field.** Missing aerial perspective (share the
atmosphere LUT and the view-depth coordinate with terrain, or the sea/sky junction mismatches the
land horizon at every sunset); a constant sky tint instead of a variance-filtered environment
fetch, which discards the gradient the reflection should carry; and missing water-leaving radiance,
without which the surface only reflects and never transmits and therefore has no volume at all.

**The unifying idea, worth internalizing over any single formula**: carry a *prefilterable
statistic* of unresolved sub-pixel surface variation alongside the resolved geometry, and let the
shading model consume it. Correct glitter, correct distant roughness, correct foam coverage and
freedom from specular aliasing all fall out of that one move.

## Sun glitter is the sparkle path, not a specular highlight

The sun subtends 0.53°; the sea-surface slope distribution is tens of degrees wide, anisotropic and
elongated along the wind [coxmunk1954], and `wave-models.md` owns the wind regression that sets its
width. A tight specular lobe is therefore not "glitter needing
more contrast" — it is the wrong *shape* of function, and the inverted physics is the most common
reason ocean renders read as vinyl.

| Tier | Mechanism | Use |
|---|---|---|
| Statistical BRDF | A microfacet BRDF whose normal distribution *is* the anisotropic Gaussian slope distribution, with Smith masking [ross2005] | **The base. Always.** Correct energy and lobe width at every distance |
| Discrete glints | Count the facets in the footprint that reflect toward the eye [deliot2023] | Near to mid field, where individual sparkles resolve |
| Noise-perturbed specular | Scroll noise through the specular term | Indie tier; reads acceptably, physically unfounded |

The first two are not alternatives: tier 1 gives correct statistics, tier 2 gives correct
granularity. Ship tier 1 everywhere and tier 2 inside a fade radius.

⚠️ **The limits on that regression — a 12.5 m wind reference, not the 10 m of standard wind data,
and a 1–14 m/s calibration range — are stated in `wave-models.md` and are not restated here.** They
bind every consumer of the variance field, and this is one.

⚠️ **Slicks are a variance effect, not an albedo effect.** Films damp capillary and short gravity
waves; slicked water measures a factor of 2–3 lower total mean-square slope [coxmunk1954]. An oil
slick, a wind shadow behind an island, or a current-convergence line renders as a **smooth mirror
patch against rougher water**. Modulate the local variance field; a dark decal is the wrong
mechanism and looks it.

**One wind, every consumer.** The same wind speed drives the spectrum, the whitecap coverage, the
glitter variance and the foam streak direction. Wiring them separately produces a mirror-calm sea
covered in foam, or a gale with a needle-sharp sun — both instantly wrong, and both common.

## Composition: reflection, refraction, depth colour, foam

```
color = lerp(refracted_underwater, reflected_environment, F(NdotV, sigma_v)) + foam + sun_glint
```

- **Fresnel `F0` is per-body, from the body's index of refraction** — not the generic dielectric
  0.04, which is glass. `water-optics.md` establishes the values; the rendering consequence is that
  shipping the default makes calm water read too reflective and faintly plastic before any of the
  distance problems compound it.
- **Reflection is a fallback hierarchy, never one source.** Screen-space reflection first, planar
  reflection for a hero body when budget allows, distant probe or sky capture last. Blend by SSR
  confidence, and match the fallback's *brightness* to the SSR result or the dropout draws a
  visible line. SSR fails at grazing angles and screen edges — exactly where water is most
  reflective — which makes water the most brutal SSR-consistency test in the frame. Calm water
  audits every reflection error at full strength; rough water hides them all, which is why a still
  lake is the case where planar reflection is often the honest choice.
- **Refraction is a screen-space approximation of Snell bending**, offsetting the scene-colour
  lookup by the surface normal rather than tracing the bent ray. It cannot see around an obstacle,
  and its canonical artefact is a distorted sample landing on something *above* the water — a dock
  post smeared into the surface. The fix is a depth reject:

```hlsl
float2 uvR = uv + n.xz * distortStrength / viewDepth;
if (LinearEyeDepth(SceneDepth.Sample(s, uvR)) < waterViewDepth) uvR = uv;   // sample was above water
```

- **Depth colour is the single strongest realism cue water has**, and it is entirely a function of
  the bathymetry the generator exported. It is **not a lerp toward an authored water colour.**
  `water-optics.md` owns the form and both coefficients; the renderer evaluates two transport paths
  whose weights do not sum to one:

```
L = bedRadiance * exp(-c * rayDistance) + L_scatter * (1 - exp(-K_d * verticalDepth))
#  c is beam attenuation along the sightline; K_d is diffuse attenuation down the light column
#  L_scatter is computed from b_b, K_d and the incident irradiance -- never an authored swatch
```

- **Two distances, and the first one is refracted.** The **ray distance** through water is the
  vertical depth divided by the Snell cosine, `verticalDepth / mu_w`, bounded by about 1.51x at
  `n = 1.335`. The depth-buffer difference is the *unrefracted* ray and overstates the path by
  `cos(theta_water)/cos(theta_air)` — about 7% at 30° from vertical, 20% at 45°, 52% at 60°, and
  without bound at grazing incidence, which is exactly where a shoreline is viewed. The **vertical
  depth** from the bathymetry field drives the shore regime and caustic survival. Flat-coloured
  water is almost always an ignored depth field.
- **Foam is three masks and one compositor**: whitecaps from the Jacobian, shoreline foam from
  shore distance and depth, flow foam on rivers. Composite it as an opaque-ish albedo layer that
  **kills the Fresnel reflection underneath** — foam is scattering froth, not glossy water, and
  reflective foam is an instant fake tell.
- **River surfaces advect by flow mapping** — no canonical paper; standard practice is the course
  talk that introduced it [vlachos2010] — two phase-offset samples of the same texture cross-faded
  on a triangle wave, so distortion resets instead of accumulating without bound. Everything above still applies; only the UV motion changes.

## The shoreline, where water is actually judged

The waterline is where the water surface meets terrain at a shallow grazing angle — the worst case
for every artefact class. A hard intersection ribbon hidden by a foam strip is not a shoreline
architecture.

- **Depth fade** over the first centimetres to metres of water depth removes the polygonal
  intersection line. It is *cosmetic*: the swim volume still starts at the datum, and gameplay must
  not read the faded visual edge.
- **The wet-sand band must move.** Drive it from the run-up envelope plus the exported wetness map,
  darkened albedo and raised specular, lagging and drying. A static band reads as painted.
- **Shoreline foam phase must agree with the wave cadence** that drives it, or foam and waves
  visibly disagree at the one place everyone is looking.
- **LOD co-discipline.** The water mesh's level at the shoreline must be matched to, or biased
  finer than, the terrain tile beneath it, and both must refine together, or the intersection line
  *crawls* on LOD transitions. The fix is contract — shared error currency and a shoreline
  bias — not more blending. Terrain skirts must stay below the water surface minus the deepest
  wave trough, or skirt walls surface at low tide.

## The camera goes under: the surface read from below

`water-optics.md` establishes this physics and hands the *pass* to the rendering axis; this
document owns the surface from both of its sides, so the pass is here rather than in the gap
between them. It is not an optional extra: `water-closed-vs-open.md` puts the bed at the centre of
the frame for closed bodies, and the bed is mostly seen from in the water. Every number below is
`water-optics.md`'s and is sourced there; what follows is only how a frame spends them.

- **Total internal reflection is the dominant term, not an edge case.** The same interface reflects
  about **6.67%** of a diffuse hemisphere from above and **47.6%** from below — a factor of 7.14 —
  and past the critical angle it reflects *exactly all* of it. Reusing the above-water Fresnel curve
  unchanged, or sampling the sky across the whole upward hemisphere, is the single biggest
  underwater error, and it makes the volume read as faintly tinted air.
- **Snell's window is the cheapest strong cue there is.** The whole above-water world compresses
  into a bright circle about **97°** wide overhead; outside it the surface is a mirror showing the
  bed. Implement it as a branch on the refracted ray rather than as a vignette texture: past
  `theta_c` there is no transmitted ray to sample at all, so the reflection is the only
  contribution and the boundary is a hard, physical edge that a radial fade cannot imitate.
- **Divide radiance by `n^2` on the way out.** `L/n^2` is the invariant across the boundary, not
  `L`; for fresh water the divisor is about **1.78**. Drop it and a lossless body with a white bed
  returns more light than it received — an energy bug no Fresnel test can catch, because a Fresnel
  test never crosses the interface.
- **Underwater fog is the depth-colour pair, re-aimed.** The same `c` and `K_d` — but the camera is
  now *inside* the medium, so `c` runs along the whole camera ray with no refracted segment and no
  surface to start it at, with the column's own glow added exactly as above.
  A grey distance fog with a blue tint is the wrong mechanism and shows it immediately: it has no
  per-channel ramp, so red does not die within the first metres and the shot reads as a colour
  filter over air rather than as water.
- **The crossing frame is the hard one, and the honest answer is a compromise.** A camera on the
  surface needs the water drawn from below (winding, backface culling and the normal all flip), a
  meniscus or wet-lens band that is *cosmetic* and must not gate any physics, and one shared state
  so that crossing is a change of which side each term applies to rather than two materials
  swapping. Production practice is a fully-above and a fully-submerged path with a short blend
  across the straddle; say that in the material instead of implying the partial frame is solved.
- **Reflection budget inverts.** The fallback hierarchy is the same, but screen-space reflection is
  *worse* from below: the mirror region past `theta_c` is precisely where the geometry it would
  need is off-screen. This is another reason closed bodies buy planar reflection — they are small,
  flat, and the shot is looking at the bed through the mirror band.

## How this fails, and what it looks like

| Symptom | Mechanism | Fix |
|---|---|---|
| The horizon reads as a glossy plastic dome with one hot highlight | Sub-pixel slope variance discarded instead of moved into the BRDF | The variance tensor, with the solar-disc minimum clamp |
| A near-total mirror band at the horizon | Plain Schlick on a low-variance surface at grazing incidence | The roughness-aware Fresnel fit, plus Smith masking in the sun lobe |
| Rough water is uniformly darker than Schlick at every angle, and calm water still looks right | `exp(-2.69*sigma_v)` applied as a factor on the fifth power instead of inside the exponent | It scales the exponent; the published fit lifts reflectance mid-range and only cuts it at grazing |
| Far sea loses its speckle, or foam shimmers into aliasing | Binary Jacobian threshold, unfilterable below a pixel | Prefiltered coverage as an erf over the footprint statistics |
| Mirror-calm sea covered in foam, or a gale with a needle-sharp sun | Wind wired separately into spectrum, coverage and glitter | One wind, every consumer |
| One blown-out highlight instead of a glitter path | A tight specular lobe — the wrong shape of function | A statistical BRDF whose distribution is the slope distribution |
| A dark decal where an oil slick or wind shadow should be | Slicks modelled as albedo | Reduce the local slope variance instead |
| A dock post or a character's torso smeared into the water | Refraction sample landed above the water surface | Depth-reject the refracted sample; fall back to the undistorted UV |
| Water is one flat colour regardless of depth | The exported bathymetry is unused, or the colour lerps toward an authored swatch | Two transport paths: extinguish the bed over the refracted path, add the column's own glow |
| Depth colour crushes to black toward the horizon and over distant shallows | The depth-buffer difference used as the in-water path length | Divide vertical depth by the Snell cosine; the refracted path is bounded, the straight one is not |
| A visible line where screen-space reflection stops | Fallback brightness does not match the SSR result | Blend by confidence and match the fallback's level |
| Foam reflects the sky | Foam composited without suppressing Fresnel beneath it | Foam kills the reflection under it |
| The waterline crawls when terrain LOD changes | Water and terrain LOD selected on different cadences | Shared error currency; bias the shoreline band finer; refine together |
| Skirt walls appear at low tide | Terrain skirts extend above the lowest wave trough | Size skirts against the trough, not the datum |
| Water ghosts and smears under a temporal upscaler | An analytic or fullscreen water pass rasterizes no motion vectors | Reproject the plane or ray hit through last frame's matrices |
| Sea and land disagree in colour exactly at the horizon | A private water fog colour instead of the shared atmosphere path | One atmosphere state and one view-depth coordinate for both |
| Wave-displaced tiles pop in at the screen edge | Culling bounds not inflated by wave amplitude and horizontal chop | Inflate per cascade; register the term with the culling system |
| From below the water reads as tinted air, with sky everywhere overhead | The above-water Fresnel curve reused from below, so total internal reflection never happens | Past the critical angle the surface is a perfect mirror; the sky arrives only inside the ~97° window |
| A submerged white floor makes a pool brighter than the light entering it | The `n^2` radiance divisor missing at the interface | `L/n^2` is the invariant crossing the boundary |
| Underwater distance is grey haze and red survives to the far wall | One tinted fog instead of per-channel extinction | The same `c` and `K_d` as the depth ramp, aimed along the camera ray |
