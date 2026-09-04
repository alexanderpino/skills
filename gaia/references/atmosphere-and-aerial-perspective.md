---
type: Technique
title: Atmosphere and aerial perspective
description: "How the sky is drawn and how every terrain pixel gets its distance cue: one fullscreen triangle drawn last and depth-tested, four LUTs that fit in a third of a millisecond, and the rule that stops three participating media attenuating the same path twice."
tags: [rendering, atmosphere, sky, aerial-perspective, fog]
status: draft
generated: { by: process:claude-code, at: 2026-09-04T00:00:00Z }
sources:
  - { id: hillaire2020, tier: P, locator: "READ IN FULL (the author's copy at sebh.github.io/publications/egsr2020.pdf; p.1 carries 'Eurographics Symposium on Rendering 2020 / Volume 39 (2020), Number 4' and the acknowledgments thank 'the anonymous reviewers' -- both checked, which is what settles the P tier against two same-year course artefacts on the same technique). Section 7 and Table 2 for the four LUTs with resolutions, step counts and per-LUT times on an NVIDIA 1080 and an iPhone 6s, and for the 0.31 ms total at 1280x720; section 7 verbatim for the comparison that matters -- 'the Bruneton model BN08 renders in 0.22ms, but this is without all the LUTs being updated. Updating all the LUTs using the code provided costs 250ms, where 99% of this cost comes from the many iterations required to estimate multiple scattering'; section 7 for volumetric shadows at 32 samples costing 1.0 ms; section 5.3 for the sky-view LUT losing accuracy from space and the switch to on-screen ray marching" }
  - { id: brunetonneyret2008, tier: P, locator: "the precomputed model this pass samples, and the render cost it achieves once its tables exist -- 125 fps at 1024x768 on an 8800 GTS, of which 0.4 ms is the first three terms of eqs. 17-18 and 2.6 ms the remainder including 1 ms for the non-linear parameterisation, in section 6. The tables themselves and the precompute are sky-and-weather-state.md's subject, not this document's. Read in the Inria HAL deposit inria-00288758, paginated 1-8 rather than 1079-1086, so sections are cited and pages are not" }
  - { id: bruneton2017, tier: P, locator: "Table 2 for the accuracy the pass inherits from whichever model was precomputed -- render-time complexity and RMSE in the same rows, Bruneton and Elek at O(1) and 11.3, Hosek at O(1) and 41.5, Preetham at O(1) and 88.1. Cited here only for what the choice of model costs the FRAME; the precompute columns belong to sky-and-weather-state.md. Read in arXiv:1612.04336v1, the author's accepted version" }
  - { id: bilodeau2014, tier: F, locator: "slide 12 only, verbatim 'Triangle has better performance than quad'. A GDC talk, not peer review. The quad-utilisation and diagonal-seam explanation usually attributed to this deck is NOT in it -- all 33 slides and their speaker notes were read and slide 12 carries no notes; that reasoning exists only in personal blogs, which measure the effect at about 0.2% at 1080p" }
  - { id: tr_lighting_shadows, tier: F, locator: "section 'Atmospheric integration' for the fullscreen-triangle sky idiom, verbatim 'The skybox is the same fullscreen triangle. Modern sky rendering is neither a dome mesh nor a box: draw the sky last as one fullscreen triangle, depth-test', for the failure it prevents -- 'a disk drawn over terrain' is sky composited without a depth test -- for the vertex-fog-to-height-fog-to-physical-atmosphere history, for aerial perspective as a core terrain feature rather than a post effect, and for the double-attenuation rule extended to three media. A practitioner chapter in a sibling skill, not peer review" }
---
# Atmosphere and aerial perspective

## Use this

**Draw the sky as one fullscreen triangle, last, depth-tested, and give every terrain pixel its
transmittance and in-scatter from the same atmosphere state** [tr_lighting_shadows] [hillaire2020].

The tables come from `sky-and-weather-state.md`, which owns the precompute. This document owns what
happens in the frame.

**What it costs.** [hillaire2020] Table 2, measured on an NVIDIA 1080 at 1280×720 and on an
iPhone 6s:

| LUT | Resolution | Steps | PC | Mobile |
|---|---|---|---|---|
| Transmittance | 256 × 64 | 40 | 0.01 ms | 0.53 ms |
| Sky-view | 200 × 100 (96 × 50 mobile) | 30 / 8 | 0.05 ms | 0.27 ms |
| Aerial perspective | 32³ (32²×16 mobile) | 30 / 8 | 0.04 ms | 0.11 ms |
| Multi-scattering | 32² | 20 | 0.07 ms | 0.12 ms |

**0.31 ms total at 1280×720**, updates included. Volumetric shadows through the atmosphere, at 32
samples, take it to **1.0 ms** — so the shadowed variant costs roughly three times the unshadowed
one, and that is the single largest discretionary number on this page.

**How wrong it is.** The pass inherits the accuracy of whatever model was precomputed, and
[bruneton2017] Table 2 prices that in RMSE against `libRadtran`: a Bruneton-class model 11.3, Hosek
41.5, Preetham 88.1 — all three rendering in O(1). **Accuracy is bought in the bake, not in the
pass.** Once the tables exist, the cheap model and the accurate model cost the frame the same.

**The comparison that is usually stated backwards.** [hillaire2020] §7 does *not* claim to be
faster than its predecessor, and repeating that it does is a misreading: *"the total render time is
0.31 ms … For the same view, the Bruneton model [BN08] renders in **0.22ms**, but this is without
all the LUTs being updated. Updating all the LUTs using the code provided costs **250ms**, where
99% of this cost comes from the many iterations required to estimate multiple scattering."*

Bruneton renders **faster**. What it cannot do is rebuild its state inside a frame. So the real
claim is about *dynamism*, not throughput: if your sky never changes, the older model is cheaper and
you should use it. The moment the sun moves, 250 ms lands in your frame and the newer method is the
only one of the two that survives it.

**Alternatives, dismissed in a line each.**

- **A skybox cube or a sky dome mesh** — geometry to cull, animate and seam, for a signal that is a
  function of view direction. Superseded; see the crossover below.
- **Vertex or per-pixel Z-fog toward one colour** — hid the far clip plane, and made a 40 km
  mountain read as a small model behind grey glass [tr_lighting_shadows].
- **Exponential height fog as the distance model** — a bounded, art-directed local medium. Keep it;
  do not let it do aerial perspective's job.
- **Ray march the atmosphere per pixel with no LUTs** — what [hillaire2020] §5.3 falls back to for
  space views, where the sky-view LUT wastes most of its resolution on empty space. Right there,
  wrong everywhere else.

## One fullscreen triangle, drawn last

[tr_lighting_shadows] states the idiom: *"The skybox is the same fullscreen triangle. Modern sky
rendering is neither a dome mesh nor a box: draw the sky **last** as one fullscreen triangle,
depth-test."*

Three properties, and each removes a class of bug. Drawing **last** means the sky only shades pixels
no geometry claimed, so its cost falls as the scene fills. **Depth-testing** is what keeps it
behind the terrain — the named failure is *"a disk drawn over terrain"*, which is what compositing
without a depth test looks like the first time a mountain reaches the horizon. And **one triangle**
rather than a quad avoids a seam along the diagonal where two triangles meet.

⚠️ **This is folklore, and the corpus convention is to say so.** There is no canonical source for
the composite idiom — sky as a fullscreen triangle, drawn last, depth-tested. Standard practice is
what is described above, and the artefacts that state it are a practitioner chapter and a
scattering of tutorials that contradict each other on depth-write and compare function. Decide
those two yourself and write them down.

⚠️ **The reason usually given for the triangle is not in the source it is attributed to, and it is
small.** [bilodeau2014] slide 12 says only *"Triangle has better performance than quad"* — the
quad-utilisation and diagonal-seam explanation everybody repeats appears nowhere in that deck, and
the blogs that do carry it measure about **0.2% at 1080p**. Use one triangle; it is free and it
removes the seam. Do not budget a saving for it.

## Aerial perspective is the distance cue, not a post effect

The load-bearing claim of this document, and the reason the axis exists at all.

Without atmosphere a 40 km vista reads as a miniature. Nothing else communicates scale —
not fog cards, not desaturation grading — because nothing else accumulates wavelength-dependent
in-scatter over kilometres [tr_lighting_shadows]. **Budget it as a core terrain feature.** At
0.04 ms for the aerial-perspective volume on a 2016-era desktop GPU, the argument that it is too
expensive has not been true for a decade.

The froxel volume is the mechanism: a low-resolution 3D texture over the camera frustum, 32³ at 30
steps, holding in-scatter and transmittance per depth slice. Every terrain pixel samples it at its
own depth and composites. That is the entire terrain-side contract, and it is why the sea and the
land must share it — see below.

**Height fog is a different system with a different job.** Aerial perspective is the planet-scale
physical medium and owns the distance cue; exponential height fog is a local, art-directed layer
that sells valley mist. Both can exist. Only one is allowed to be the distance model.

## The three-media rule

⚠️ **Aerial perspective, height fog and camera-frustum froxel fog can attenuate the same path
twice**, and the result is a scene that goes muddy at range in a way no single parameter fixes.

The rule, as the practitioner literature converges on it: **media sharing a volume are combined as
coefficients, not composited as results.** Sum the extinction and in-scatter of every medium
occupying the same froxel, average the phase functions, and integrate once. Compositing three
finished attenuations multiplies three transmittances that each already accounted for the same path.

The world-scale sky term is the exception, and it is applied **once**, at a single representative
depth, rather than being integrated alongside the local media. That is a documented compromise
rather than a derivation — the practitioners who describe it say in their own words that it is not
physically correct, and they ship it anyway because the error is small and the alternative is a
second full integration.

## The camera-relative frame

At planetary scale the atmosphere must be evaluated in **the same camera-relative frame as
everything else**. A planet-absolute-position atmosphere shader jitters independently of
jitter-free terrain, and the two visibly detach at the horizon [tr_lighting_shadows]. This is not
an atmosphere problem; it is `planetary-precision.md`'s problem arriving in a pass that people
forget to convert. Route there for the frame construction; this document only records that the sky
is subject to it.

## One atmosphere, shared with the water

`water-rendering.md` already prescribes this and, until this document existed, had nothing to point
at: **share the atmosphere LUT and the view-depth coordinate with the terrain**, or the sea/sky
junction mismatches the land horizon at every sunset. A private water fog colour is the mechanism;
one atmosphere source is the fix. The sea, the land and the sky are three surfaces under one
medium, and the horizon is where a disagreement between them is most visible and least forgivable.

## The crossover, with a date and a direction

- **Before the 2000s** — vertex or pixel Z-fog toward one colour. Every wavelength and altitude
  behaved identically [tr_lighting_shadows].
- **Then** — exponential height fog. Altitude structure, still an art-directed local medium.
- **2008** [brunetonneyret2008] — precompute scattering into tables; the pass becomes a few texture
  fetches, and renders at 125 fps at 1024×768 on an 8800 GTS. The sky is now physical and static.
- **2020** [hillaire2020] — the tables themselves become cheap enough to rebuild in-frame: 0.31 ms
  at 1280×720 including all four updates, against 250 ms for the older bake. The sky becomes
  physical *and* dynamic.

**Which way it is still moving.** Each step moved work off the critical path and then made the
off-frame work cheap enough to bring back on. The direction is toward **fully dynamic state at
frame rate**, and the number to watch is the shadowed-atmosphere figure — 1.0 ms at 32 samples
today, which is where the remaining discretionary cost sits.

## When it fails

| Symptom | Mechanism | Fix |
|---|---|---|
| A disk of sky drawn over a mountain | Sky composited without a depth test [tr_lighting_shadows] | Draw last, depth-test |
| A seam along the screen diagonal | Two triangles instead of one | One fullscreen triangle [bilodeau2014] |
| A 40 km vista reads as a miniature | No aerial perspective; fog cards and grading cannot substitute | The froxel volume, 0.04 ms at 32³ [hillaire2020] |
| The scene goes muddy at range and no parameter fixes it | Three media attenuating the same path — aerial perspective, height fog and froxel fog composited as results | Sum coefficients in the shared froxel, integrate once; apply the sky term once at one depth |
| Sea and land disagree in colour exactly at the horizon | A private water fog colour instead of the shared atmosphere path | One atmosphere state, shared — `water-rendering.md` |
| Sky and terrain detach at the horizon when the camera moves | A planet-absolute atmosphere shader jittering against jitter-free terrain | Evaluate in the camera-relative frame — `planetary-precision.md` |
| The sky is fine on the ground and wastes resolution from orbit | The sky-view LUT spends most of itself on empty space | Switch to on-screen ray marching for space views [hillaire2020] §5.3 |
| A time-of-day sweep costs 250 ms a step | The old precompute rebuilt per step | Rebuild only the sun-dependent table, or use the in-frame LUT set [hillaire2020] |
| Volumetric shadows triple the sky cost | 32 ray-march samples with jitter and reprojection | Budget 1.0 ms, or reduce samples and lean harder on TAA [hillaire2020] |
