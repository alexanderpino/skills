---
type: Technique
title: Caustics — light focused by the water surface
description: "Underwater and surface caustics on terrain: the caustic-map path for a rasterizer, the ray-traced path for studio quality, and why the scrolling texture everyone ships is not a caustic."
tags: [rendering, rasterizer, ray-traced, water, caustics]
status: draft
generated: { by: process:claude-code, at: 2026-09-02T00:00:00Z }
sources:
  - { id: shah2007, tier: P, locator: "the light-space receiver estimation loop against a depth map" }
  - { id: wyman2006, tier: P, locator: "§3.1 Photon Emission — one photon per texel of a light-space image of the refractor; §3.2 Photon Gathering, with §3.2.1 and §3.2.2 the two gather forms and §3.2.3 the noise filter" }
  - { id: guardado2004, tier: F, locator: "§2.3 Our Approach — the per-vertex backward ray trace and the 0.53° sun-disc angle — and §2.4 for the OpenGL pass structure. The projected caustic texture is §2.2, where the chapter credits it to Stam 1996 rather than presenting it" }
  - { id: jensen1996, tier: P, locator: "§3 Pass 1: Constructing the Photon Maps — the caustics photon map is built by emitting photons towards the specular objects; §4.3 Caustics is where that map is used at render time, and §5 the radiance estimate" }
  - { id: zeltner2020, tier: P, locator: "§4.1 Finding all solutions — seeded Newton walks and the convergence-basin probability — and §4.2 Unbiased SMS; the manifold walk itself is set up in §3.1" }
---
# Caustics — light focused by the water surface

**Boundary.** The refraction law, absorption and total internal reflection are established in
`water-optics.md`; the wave field that does the focusing is `wave-models.md`; surface shading,
reflection and depth colour are `water-rendering.md`. **This document owns the focused light on
the bed** — and the same machinery pointed upward at a hull or a cave roof.

## What a caustic actually is, in one paragraph

The wavy surface refracts every incoming ray, so the map from a point on the surface to the point
it illuminates on the bed is a smooth but **non-area-preserving** transformation. Irradiance on the
bed scales as the reciprocal of that map's Jacobian determinant: where neighbouring rays converge,
the Jacobian shrinks and the bed brightens. The bright *filaments* are where it passes through
zero — the fold set of the projection — which is why real caustics are sharp cusped lines rather
than soft blobs. Everything below is an approximation to that one statement, and the approximations
are graded by which part of it they keep.

⚠️ **Depth does not simply sharpen them; there is a band, with nothing at either end.** At zero
separation the refracted map is the identity, `J = 1` everywhere, and there is no caustic at all —
a bed lying *on* the surface carries the surface's own slope shading and no focusing whatever.
Contrast builds with separation as neighbouring rays get room to converge, and then the water's own
scattering erases the fold structure over a few metres of path. A renderer that brightens the
pattern monotonically as the bed rises has the near end of that band inverted. **The two ends are
two different factors, and a renderer needs both**: a geometric gain `G` that goes to 1 as the
separation goes to zero, and a coherent fraction `f` that goes to zero as scattering takes the beam
apart. `## Use this` writes them out.

Three consequences worth fixing in mind before choosing a technique:

- **Caustics redistribute light; they do not add it — so the caustic layer *replaces* the bed's
  direct sun term rather than sitting on top of one.** It is a dimensionless **gain** with mean 1
  over the *light-space texture that carries it*, never over bed area — the measure the energy
  argument conserves is the bed's **horizontal footprint**, which is exactly the factor the block
  below already applies — and it **multiplies**. Normalizing the layer's mean and then adding it to
  a bed that is already fully sun-lit does not cure the double-count: a layer normalized to the
  transmitted irradiance `E_sun` — the symbol the block below defines — plus a direct term of the
  same mean is exactly `2·E_sun`, one stop too bright everywhere, and *that* is what reads as
  washed-out flat-bright water between the filaments. Normalizing sets the scale; multiplying is
  the composition; they are two different fixes and only the second one removes the double-count.
  Only the *direct* term is modulated: the sky is a hemisphere-wide source, so the patterns its
  many directions cast superimpose and average their own fold structure away. Filaments are a
  near-point-source effect, which is why the sun makes them and an overcast sky does not.
- **They exist only inside that depth band, and only where the water is clear.** The pattern is
  carried by the *unscattered* beam, so its contrast decays over roughly one scattering length of
  path, `1/(b − b_b)` — metres in clear water, centimetres in turbid, tabulated under *Details*
  below. Deep or turbid water therefore has no caustics, only a diffuse column, and water shallow
  enough that the refracted map is near the identity has none either.
- **They require unshadowed direct sun.** Bed in shadow, no caustics. This is the cheapest
  correctness win available and it is skipped constantly.

## Use this

**Rasteriser tier: a caustic map — render the surface from the light, refract, find where each ray
lands, splat into a light-space texture, and project that texture onto the receiver**
[wyman2006] [shah2007].

1. Rasterize the water surface *from the light*, giving a light-space image whose texels are
   surface points with normals.
2. Per texel, refract the light direction through the surface normal — one photon per texel.
3. **Find the receiver by iterating against a light-space depth map of the terrain** [shah2007],
   not by assuming a plane. This is the step that makes the technique work over real bathymetry
   instead of over a flat pool floor, and it is the step the cheap implementations drop.
4. Splat each photon with a small kernel into a light-space caustic texture, additively.
5. Project that texture onto the bed in the main pass as a **gain on the direct sun term** — not as
   a layer laid over one — gated by the sun's shadow term, with the pattern attenuated on the
   **beam** coefficient `c` along the refracted solar path and the mean on `K_d` with depth.

**Which extinction, and on which term.** `water-optics.md` exports two attenuation coefficients
precisely so that this choice is made rather than lumped: `c = a + b`, the *beam* coefficient, for a
sharp ray bundle; `K_d`, the *diffuse* one, for the ambient column. A caustic is the beam — the fold
structure lives in light that has not been scattered — while the sun's *total* contribution to the
bed is the column, because forward-scattered light still arrives, only smeared. Both appear, on
different terms and never interchangeably:

```
mu_w  = sqrt(1 - (sin(theta_sun)/n)^2)     # Snell cosine of the SUN below the surface
L     = z / mu_w                           # refracted solar path to a bed at depth z
G     = splat density / the density a flat WATER surface deposits  # mean 1 in LIGHT SPACE
f     = exp(-max(0, c - mu_w*K_d) * L)     # the coherent beam's SHARE of the irradiance at z
E_sun = (1 - R_ext(theta_sun)) * E_n * cos(theta_sun) * exp(-K_d * z)
E_bed = shadow * (dot(N_bed, l_w) / mu_w) * E_sun * (1 + (G - 1) * f)
#  l_w  is the refracted direction TO the sun below the surface, so the bed factor is 1 when flat
#  c    is NOT an exported field. water-optics.md exports a, b_b, K_d, phase_g and ior; c is
#       reconstructed from them as a + b_b/B(phase_g), which at phase_g = 0.924 is a + 58.9*b_b
#  E_n  is direct NORMAL irradiance above the water, and R_ext is the exact unpolarised Fresnel at
#       the SUN's incidence, n = 1.335: 2.06% at 0 deg, 2.17% at 30, 2.82% at 45, 6.01% at 60.
#       NOT the 6.67% cosine-weighted hemispherical figure, which is a Lambertian average over the
#       whole hemisphere and is the reflectance at no single angle at all
#  E_sun*f is (1 - R_ext)*E_n*cos(theta_sun)*exp(-c*L) -- the beam law, intact -- EXACTLY WHILE
#       c >= mu_w*K_d. Where the max(0, ..) above clamps, f = 1 identically and the beam law is
#       gone: the pattern then never fades with depth at all, which is the failure row "The
#       filaments keep their contrast all the way down". The clamp is a floor, not a repair --
#       where it fires, take the exponent water-only instead: b - b_b = b_b*(1/B(phase_g) - 1),
#       positive by construction, needing no clamp and carrying no sun angle
#  G has mean 1 BY CONSTRUCTION over the LIGHT-SPACE texture -- equivalently over the bed weighted
#       by dot(N_bed, l_w)/mu_w, its horizontal footprint, which is the factor the E_bed line
#       already carries, and NEVER by bed area. And only while every emitted photon is deposited.
#       One that leaves the light-space texture, or whose receiver search fails, is lost energy:
#       the bed goes dim at the map's edges and no amount of later normalizing puts it back
```

`f` is the far end of the depth band, and the bracket it sits in is the whole story: `(1 + (G−1)·f)`
is `G` in the shallows, the pure caustic, and 1 in deep or turbid water, a smooth column with no
pattern left in it. `K_d` carries `mu_d`, the mean cosine of the *whole* downwelling field; with the
sun dominating that field — the only condition under which caustics exist at all — `mu_d = mu_w` and
the exponent collapses to `b − b_b`, **one scattering length of path, with no sun angle left in
it**. ⚠️ The `max(0, …)` is not decoration: a `K_d` exported for a more diffuse field than the one
being rendered drives the exponent negative — pure water at 610 nm with `K_d` taken at
`mu_d = 0.75` against a zenith sun gives `−0.088 /m` — and a negative exponent *grows* the pattern
with depth.

⚠️ **The error this accepts, and why `K_d` is the wrong end of a real bracket rather than simply
wrong.** `exp(-c·L)` counts *every* scattering event as destroying that photon's contribution to
the fold. Under the Henyey–Greenstein function the descriptor exports (`water-optics.md`), at
`phase_g = 0.924`, that is close to true: the mean deflection is **14.4°** and the median **7.5°**,
throwing a photon 26 cm and 13 cm off course over a remaining metre of path — enough to decorrelate
it from its own filament wherever the filaments are spaced at that scale or finer. Filament spacing
is set by the surface rather than chosen: the refracted ray map is periodic in the surface's own
period, so the fold set is periodic in it too, and the filaments land at a *fraction of the
wavelength that made them* (`wave-models.md` owns those wavelengths). A 26 cm scramble therefore
erases what short wind ripple writes on the bed and leaves a long swell's metres-apart structure
partly intact. The opposite extreme is `a + b_b`, which is exactly `mu_d·K_d`: only backscatter
counts, near-forward scattering is assumed to preserve the fold perfectly, and the fade vanishes
entirely. *That* is what a renderer picks when it attenuates the pattern on `K_d` — less a
coefficient confusion than the assumption that forward scattering is free. The truth is inside that
bracket, and under the phase function the descriptor actually exports it sits near the short end,
`1/(b − b_b)`.

The whole thing is one extra light-space pass at modest resolution, and its cost is independent of
screen resolution and of how much bed is visible. It is the cheapest thing that is genuinely a
caustic: it moves with the waves because it is *computed from* the waves, it converges and diverges
correctly with depth, and it produces cusps because the splat density is the **reciprocal** of the
Jacobian — the same quantity the irradiance statement above is written in. Getting that the wrong
way up inverts the image: the folds come out as dark seams and the flat regions as the bright ones.

**Near-real-time / ray-traced tier: solve the specular chain rather than sampling toward it.** Path
tracing finds a light→water→bed→eye path only by chance, and the chance is essentially zero for a
smooth surface — which is why naively ray-traced water renders black caustics. The two production
answers are a **caustic photon map**, shot along specular paths from the light and gathered on the
bed [jensen1996], and **specular manifold sampling**, which walks the surface to *solve* for the
refraction point connecting a shading point to the light [zeltner2020]. Photon mapping is the
robust workhorse and biases toward blur at the fold; manifold sampling keeps the high-frequency
filaments that make water read as water, at the cost of a solver per sample. For a studio-quality
still or a near-real-time preview, that is the tier.

**What it beats.** *A scrolling authored caustic texture projected down the light direction* — the
overwhelming industry default, and it is not a caustic at all: it is an animation with no
dependence on the surface that supposedly focused it. It does not respond to wind, wave height,
water depth or the shape of the bed; it cannot converge into cusps; it slides rather than shimmers;
and projected naively it appears on vertical faces and on surfaces the water cannot reach. It is
defensible only as an art-directed stylized effect, and it should be labelled that way in the
material so nobody debugs it as physics. *Per-vertex caustic intensity from the surface normal*
[guardado2004] — the same era, tied to mesh density, and it dies wherever the bed is coarsely
tessellated. *Screen-space caustics from the G-buffer* — cheap, and it has SSR's disease: the
photon's landing point is often off-screen exactly when the effect matters, at grazing angles over
a shelving bed. *Analytic caustics from a summed wave field* — attractive and only valid while the
wave model is a small sum of analytic terms; it stops being available the moment the surface comes
from a spectrum or a simulation.

## The crossover, stated as a budget

| You have | Use | Because |
|---|---|---|
| A rasterizer, a real bathymetry field, sun-lit shallows | **Caustic map** with depth-map receiver estimation [shah2007] | One light-space pass, cost independent of screen coverage; correct response to wave state and depth |
| A rasterizer, stylized art direction, no bathymetry | Projected animated texture — nearest published relative [guardado2004] | Cheap and legible — label it as an effect, not as light |
| A path tracer, and caustics are part of the shot | **Caustic photon map** [jensen1996] | Robust, handles any surface, blurs the fold |
| A path tracer, and the filaments are the shot | **Specular manifold sampling** [zeltner2020] | Keeps the high-frequency structure photon gathering smooths away |
| Real-time ray tracing, terrain as a proxy | Caustic map still, projected in the raster pass | The ray budget is spent on shadows and reflections; see `heightfield-raymarching.md` for the proxy contract |

⚠️ **One of those rows rests on an `F` source, and thinly.** There is no peer-reviewed paper
behind the stylized projected-texture tier — and, checked against the source, there is no book
chapter either. The GPU Gems chapter usually cited for it [guardado2004] raises the projected
caustic texture in §2.2 only to attribute it to Stam 1996 and then replace it: the chapter's own
method, §2.3–2.4, is the per-vertex backward ray trace this document credits it with above. The
row is listed as the honest name for what the industry actually ships, not as a result. Every
other row above cites a peer-reviewed paper.

The crossover is not "how much GPU do I have" but **whether the surface is available as a field the
light pass can rasterize**. If it is, the caustic map is nearly free relative to what it buys. If
the surface only exists per-pixel in a fullscreen analytic pass, you have no light-space surface
image and must either build one for the light or drop to the stylized tier.

## Details that decide whether it looks right

- **Attenuate along the *light's* path, not the camera's.** The photon travelled from the surface
  down to the bed; that distance, not the view distance, sets how much of it survives. Getting
  this backwards makes caustics brightest where the camera is closest instead of where the water
  is shallowest. That distance is the **refracted** solar path `z/mu_w` — not the vertical depth,
  which understates it by up to 1.51x at `n = 1.335` (`water-optics.md`), and not the straight line
  to the sun above the water. And it is `c` that attenuates it: `K_d` belongs to the column, which
  carries no pattern.
- **Prefilter, or the filaments alias.** Caustic structure is high-frequency by construction and
  goes sub-pixel with distance, giving crawling sparkle. Widen the splat kernel with the receiver's
  screen footprint — the same "move the variance rather than lose it" discipline that governs the
  water surface itself in `water-rendering.md` — but not across a receiver discontinuity; see the
  next bullet. Temporal accumulation over a few frames is the cheap complement, and it is safe here
  because the pattern is already animating.
- **Never filter across a light-space depth discontinuity — not when splatting, not when
  projecting.** Both ends of the caustic map filter blind by default. A splat kernel widened over a
  ledge deposits energy on a face the photon never reached; a bilinear tap at projection time reads
  four texels whose receivers are metres apart in depth and bleeds the ledge top onto the shadowed
  side. It is the same defect as compositing a reduced-resolution volumetric buffer against
  full-resolution depth, and it takes the same fix: weight or reject each tap by the agreement
  between its stored receiver depth and the shaded point's, and clamp the kernel where they
  disagree. The light-space depth map from step 3 is already built and already registered; the
  comparison costs one extra tap.
- **Fade with depth on the bathymetry field**, not on view distance, and fade it on the water's own
  scattering rather than on a hand-tuned depth. The scale is one scattering length of path,
  `1/(b − b_b)`, out of the body's own descriptor:

| Water | `b` [1/m] | `1/(b − b_b)` | `f` after 3 m of path |
|---|---|---|---|
| pure water, 450 nm | 0.0046 | 437 m | 0.993 |
| clear oceanic | 0.15 | 6.8 m | 0.64 |
| coastal | 1.0 | 1.02 m | 0.053 |
| turbid | 5.0 | 0.20 m | 4.0e-7 |
| very turbid | 20 | 0.051 m | 2.6e-26 |

  `b` is what `b_b/B(phase_g)` reconstructs. The four particle-laden rows are `water-optics.md`'s
  own water types at the particulate `B = 0.018`; pure water's is molecular scattering, where the
  Rayleigh phase function is symmetric and `B = 1/2`. **This is also why the familiar "5–20x"
  `c`/`K_d` range is the wrong end of the table to reason about caustics from**: that range is
  turbid water, where `f` is gone inside a metre and there is no pattern left to attenuate. Where
  caustics actually exist the two coefficients are close — `c/K_d = mu_d·(a+b)/(a+b_b)` is 0.75 to
  1.20 in pure water, *crossing one*, and about 2.8 in clear oceanic water at `mu_d = 0.75`
  (`water-optics.md`) — and their difference is precisely this fade, not a brightness offset.
- **Point the machinery upward too.** The same light-space splat run on rays reflected *off* the
  surface gives the dancing light on a hull, a jetty underside, or a sea-cave roof — a strong and
  almost free cue, and one that is almost always missing.
- **Volumetric shafts are a different effect.** Light scattered *within* the water column between
  the surface and the bed is participating-medium marching, not caustic mapping; the caustic
  texture can modulate it, but stamping the bed pattern onto a fog volume is not the same thing and
  reads as a decal in mid-water.
- **Do not caustic-light the water surface itself.** The pattern belongs on what the light reached
  *through* the surface. Applying it to the surface material is a common copy-paste error and shows
  as a texture that ignores the viewing angle entirely.

## How this fails, and what it looks like

| Symptom | Mechanism | Fix |
|---|---|---|
| The pattern slides across the bed instead of shimmering, and ignores wind | A scrolling texture, not a caustic | Compute it from the surface; or keep the texture and stop calling it physics |
| Caustics on vertical cliff faces and under overhangs | The projection has no receiver test | Find the receiver by iterating the light-space depth map |
| The bed is uniformly bright between filaments, one stop hot | The caustic layer was added on top of a full direct term. Normalizing its mean does not fix this: mean `E_sun` plus mean `E_sun` is exactly `2·E_sun` | Make it a gain of mean 1 **in light space** and **multiply** the direct term by it — `E_sun·(1 + (G−1)·f)`, never `E_sun + layer` |
| Caustics in the shadow of a rock, a boat or a bridge | The sun's shadow term was not applied to the caustic layer | Gate by the same shadow term the rest of the direct light uses |
| Bright where the camera is near rather than where the water is shallow | Attenuated along the view ray instead of the light path | Attenuate over the **refracted** solar path `z/mu_w`, with `c` |
| The filaments keep their contrast all the way down, and murky water still shows them | The pattern was attenuated on `K_d`, or on nothing. `K_d` is the column's coefficient and carries no fade for a beam | The pattern rides `exp(-c·L)` and the mean rides `exp(-K_d·z)`; their ratio `f = exp(-max(0, c − mu_w·K_d)·L)` is the fade, and it is one scattering length of path |
| The whole bed goes several times too dark with depth | `c` applied to *everything*, so the forward-scattered light that still reaches the bed was thrown away | `c` attenuates the pattern only; the mean is `K_d` on the vertical depth. The gap is `1/f` — 4.4x at 7.5 m of depth in clear oceanic water at `mu_w = 0.75` |
| Crawling sparkle on distant shallows | Sub-pixel filaments, unfiltered | Widen the splat kernel with the receiver footprint; add a short temporal accumulation |
| Caustics visible in deep or turbid water | Fade driven by view distance, or not at all | Fade on the bathymetry depth, at the water's own scattering length of path `1/(b − b_b)` — tabulated under *Details* |
| Caustics bleed off a ledge onto the face beneath it | A splat kernel or a projection tap filtered across a light-space depth discontinuity | Compare each tap against the light-space depth map already built for step 3; clamp the kernel where the receivers disagree |
| The pattern is blocky and follows the bed's triangles | Per-vertex intensity on a coarse receiver | Move to a light-space texture; per-vertex ties the effect to tessellation |
| Path-traced water renders black caustics | The specular chain is never found by chance | A caustic photon map, or manifold sampling |
| Ray-traced caustics are correct but mushy | Photon gathering smooths the fold set | Manifold sampling for the filaments, photons for the base |
| The pattern appears on the water surface itself | The caustic texture was applied to the wrong material | It belongs to what the light reached through the surface |
| Caustics stop existing when the fullscreen water pass is enabled | There is no light-space surface image to rasterize | Build one for the light pass, or accept the stylized tier |
