---
type: Technique
title: Caustics — light focused by the water surface
description: "Underwater and surface caustics on terrain: the caustic-map path for a rasterizer, the ray-traced path for studio quality, and why the scrolling texture everyone ships is not a caustic."
tags: [rendering, rasterizer, ray-traced, water, caustics]
status: draft
generated: { by: process:claude-code, at: 2026-09-02T00:00:00Z }
sources:
  - { id: shah2007, tier: P, locator: "the light-space receiver estimation loop against a depth map" }
  - { id: wyman2006, tier: P, locator: "photon emission per texel of the light-space surface image, and the image-space gather" }
  - { id: guardado2004, tier: F, locator: "the projected-texture and per-vertex intensity forms" }
  - { id: jensen1996, tier: P, locator: "§4, the separate caustic photon map along specular paths" }
  - { id: zeltner2020, tier: P, locator: "§4, the manifold walk that solves for specular chains" }
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
a bed touching the surface is evenly lit. Contrast builds with separation as neighbouring rays get
room to converge, and then the water's own scattering erases the fold structure over a few metres
of path. A renderer that brightens the pattern monotonically as the bed rises has the near end of
that band inverted.

Three consequences worth fixing in mind before choosing a technique:

- **Caustics redistribute light; they do not add it.** Averaged over the bed, the caustic pattern
  must integrate back to the transmitted irradiance. A caustic layer added on top of an already
  fully-lit bed double-counts, and the bed reads washed out and flat-bright between the filaments.
- **They exist only inside that depth band, and only where the water is clear.** Scattering
  destroys the fold structure over a few metres of path, so deep or turbid water has no caustics,
  only a diffuse column — and water shallow enough that the refracted map is near the identity has
  none either.
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
5. Project that texture onto the bed in the main pass, attenuated by the same extinction the water
   column already applies, gated by the sun's shadow term, and normalized so the mean returns to
   the transmitted irradiance.

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
| A rasterizer, stylized art direction, no bathymetry | Projected animated texture [guardado2004] | Cheap and legible — label it as an effect, not as light |
| A path tracer, and caustics are part of the shot | **Caustic photon map** [jensen1996] | Robust, handles any surface, blurs the fold |
| A path tracer, and the filaments are the shot | **Specular manifold sampling** [zeltner2020] | Keeps the high-frequency structure photon gathering smooths away |
| Real-time ray tracing, terrain as a proxy | Caustic map still, projected in the raster pass | The ray budget is spent on shadows and reflections; see `heightfield-raymarching.md` for the proxy contract |

⚠️ **One of those rows rests on an `F` source.** There is no peer-reviewed paper behind the
stylized projected-texture tier; the standard exposition is a GPU Gems book chapter
[guardado2004], and it is listed here as the honest name for what the industry actually ships, not
as a result. Every other row above cites a peer-reviewed paper.

The crossover is not "how much GPU do I have" but **whether the surface is available as a field the
light pass can rasterize**. If it is, the caustic map is nearly free relative to what it buys. If
the surface only exists per-pixel in a fullscreen analytic pass, you have no light-space surface
image and must either build one for the light or drop to the stylized tier.

## Details that decide whether it looks right

- **Attenuate along the *light's* path, not the camera's.** The photon travelled from the surface
  down to the bed; that distance, not the view distance, sets how much of it survives. Getting
  this backwards makes caustics brightest where the camera is closest instead of where the water
  is shallowest.
- **Prefilter, or the filaments alias.** Caustic structure is high-frequency by construction and
  goes sub-pixel with distance, giving crawling sparkle. Widen the splat kernel with the receiver's
  screen footprint — the same "move the variance rather than lose it" discipline that governs the
  water surface itself in `water-rendering.md`. Temporal accumulation over a few frames is the
  cheap complement, and it is safe here because the pattern is already animating.
- **Fade with depth on the bathymetry field**, not on view distance, and let the fade reach zero
  before the depth at which the water's own scattering would have destroyed the pattern.
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
| The bed is uniformly bright between filaments | The caustic layer was added on top of full lighting | Normalize so the mean returns to the transmitted irradiance |
| Caustics in the shadow of a rock, a boat or a bridge | The sun's shadow term was not applied to the caustic layer | Gate by the same shadow term the rest of the direct light uses |
| Bright where the camera is near rather than where the water is shallow | Attenuated along the view ray instead of the light path | Attenuate over the light's path length through the water |
| Crawling sparkle on distant shallows | Sub-pixel filaments, unfiltered | Widen the splat kernel with the receiver footprint; add a short temporal accumulation |
| Caustics visible in deep or turbid water | Fade driven by view distance, or not at all | Fade on the bathymetry depth, to zero before scattering would have erased the pattern |
| The pattern is blocky and follows the bed's triangles | Per-vertex intensity on a coarse receiver | Move to a light-space texture; per-vertex ties the effect to tessellation |
| Path-traced water renders black caustics | The specular chain is never found by chance | A caustic photon map, or manifold sampling |
| Ray-traced caustics are correct but mushy | Photon gathering smooths the fold set | Manifold sampling for the filaments, photons for the base |
| The pattern appears on the water surface itself | The caustic texture was applied to the wrong material | It belongs to what the light reached through the surface |
| Caustics stop existing when the fullscreen water pass is enabled | There is no light-space surface image to rasterize | Build one for the light pass, or accept the stylized tier |
