---
type: Technique
title: Atmosphere and aerial perspective
description: "How the sky is drawn and how every terrain pixel gets its distance cue: one fullscreen triangle drawn last and depth-tested, four resolution-independent LUTs costing 0.17 ms with only the on-screen apply scaling with pixels, and the rule that stops three participating media attenuating the same path twice."
tags: [rendering, atmosphere, sky, aerial-perspective, fog]
status: draft
generated: { by: process:claude-code, at: 2026-09-04T00:00:00Z }
sources:
  - { id: hillaire2020, tier: P, locator: "READ IN FULL (the author's copy at sebh.github.io/publications/egsr2020.pdf; p.1 carries 'Eurographics Symposium on Rendering 2020 / Volume 39 (2020), Number 4' and the acknowledgments thank 'the anonymous reviewers' -- both checked, which is what settles the P tier against two same-year course artefacts on the same technique). Section 7 and Table 2 for the four LUTs with resolutions, step counts and per-LUT times on an NVIDIA 1080 and an iPhone 6s, and for the 0.31 ms total at 1280x720; section 7 verbatim for the comparison that matters -- 'the Bruneton model BN08 renders in 0.22ms, but this is without all the LUTs being updated. Updating all the LUTs using the code provided costs 250ms, where 99% of this cost comes from the many iterations required to estimate multiple scattering'; section 7 for volumetric shadows at 32 samples costing 1.0 ms; section 5.3 for the sky-view LUT losing accuracy from space and the switch to on-screen ray marching" }
  - { id: brunetonneyret2008, tier: P, locator: "the precomputed model this pass samples, and the render cost it achieves once its tables exist -- 125 fps at 1024x768 on an 8800 GTS, of which 0.4 ms is the first three terms of eqs. 17-18 and 2.6 ms the remainder including 1 ms for the non-linear parameterisation, in section 6. The tables themselves and the precompute are sky-and-weather-state.md's subject, not this document's. Read in the Inria HAL deposit inria-00288758, paginated 1-8 rather than 1079-1086, so sections are cited and pages are not" }
  - { id: bruneton2017, tier: P, locator: "Table 2 for the accuracy the pass inherits from whichever model was precomputed -- render-time complexity and RMSE in the same rows, the RMSE being against the sky MEASUREMENTS and not against libRadtran, over a 09h30-13h30 window only, Bruneton and Elek at O(1) and 11.3, Hosek at O(1) and 41.5, Preetham at O(1) and 88.1. Cited here only for what the choice of model costs the FRAME; the precompute columns belong to sky-and-weather-state.md. Read in arXiv:1612.04336v1, the author's accepted version" }
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

**0.31 ms total at 1280×720**, updates included — and **do the subtraction before you budget it**.
The four LUTs sum to **0.17 ms**, and every one of them is a fixed size that does not change with
screen resolution. The remaining **0.14 ms** is the on-screen apply, and that is the only part that
scales with pixels. So the shape of the budget is `0.17 + 0.14 × (pixels / 0.92 Mpix)`: about
**0.44 ms at 1080p** and about **1.4 ms at 4K** on the same 2016-era GPU, against 0.31 quoted.

That the LUTs do not scale is a design decision, not an accident. [hillaire2020] §5.3 says so
directly: ray marching the sky per pixel "can be expensive, especially at high resolution such as
4K or 8K", so the distant sky is rendered into a fixed 200×100 latitude/longitude texture and
upsampled. **The sky is resolution-independent by construction; the aerial-perspective apply is
not.**

⚠️ These are one paper's measurements on one GPU at one resolution. They are the right *shape* to
reason with and they are not your budget. The mobile column is the warning: the same transmittance
LUT costs 0.01 ms on a 1080 and **0.53 ms** on an iPhone 6s, 53× more, and that LUT is a pure
function of the medium that need not be rebuilt every frame at all — on a tight platform, updating
it on a cadence is the first saving available, and it is worth **half** of the mobile LUT cost.

Volumetric shadows through the atmosphere, at 32 samples, take the total to **1.0 ms** — roughly
three times the unshadowed pass, and the single largest discretionary number on this page.

## Rebuild on change, not on frame

The table above reads as though all four LUTs are rebuilt every frame. They are not, and the
cadence is the difference between the technique fitting a mobile frame and not:

| LUT | Depends on | Rebuild when |
|---|---|---|
| Transmittance | the medium only | the medium changes — in practice a **load-time bake** |
| Multi-scattering | medium + sun elevation | a material sun move; it varies smoothly, so gate on ~1° |
| Sky-view | view altitude + sun direction | per frame |
| Aerial perspective | camera frustum + sun | per frame, **per view** |

⚠️ **On an iPhone 6s the transmittance LUT is 0.53 ms — 51% of the whole 1.03 ms LUT budget — and it
is a pure function of constants.** Bake it once and the same set costs about **0.38 ms** for a moving
camera under a static sun. An engineer reading the flat table as written spends 3% of a 33 ms mobile
frame rebuilding tables two thirds of which did not change, and may reasonably conclude the technique
does not fit and fall back to an analytic gradient at 88.1 RMSE. It fits; it fits **with the
cadence**.

The implementation is a dirty flag, not a scheduler: hash the atmosphere parameter block and the
quantised sun direction, and rebuild only the LUTs whose inputs moved. A tool viewport nobody is
interacting with rebuilds nothing.

**How wrong it is.** The pass inherits the accuracy of whatever model was precomputed, and
[bruneton2017] Table 2 prices that in RMSE against the sky **measurements** (not against
`libRadtran`, which is a comparison point in that paper rather than the error reference), over a
09h30–13h30 window: a Bruneton-class model 11.3, Hosek
41.5, Preetham 88.1 — all three rendering in O(1). **Accuracy is bought in the bake, not in the
pass.** Once the tables exist, the cheap model and the accurate model cost the frame the same.

**The comparison that is usually stated backwards.** [hillaire2020] §7 does *not* claim to be
faster than its predecessor, and repeating that it does is a misreading: *"the total render time is
0.31 ms … For the same view, the Bruneton model [BN08] renders in **0.22ms**, but this is without
all the LUTs being updated. Updating all the LUTs using the code provided costs **250ms**, where
99% of this cost comes from the many iterations required to estimate multiple scattering."*

Bruneton renders **faster**. What it cannot do is rebuild its state inside a frame. So the real
claim is about *dynamism*, not throughput: if your medium never changes, the older model is cheaper
and you should use it.

⚠️ **And "the medium", not "the sun".** Sun zenith is an axis of the older model's 4D table, so
moving the sun there costs a texture coordinate — see `sky-and-weather-state.md`, which corrects
this at length. What lands 250 ms in your frame is a change of *medium*: turbidity, scale heights,
or ground albedo. The newer method inverts the trade, building a small sun-specific LUT every frame
at 0.05 ms instead of a large sun-general one once, which is why a moving sun is free there too —
by a different mechanism, and one that also makes a changed medium free.

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
no geometry claimed, so *the sky shader's* cost falls as the scene fills — note that the
aerial-perspective apply moves the opposite way, since it is paid on every pixel geometry *did*
claim. A closed interior scene pays almost no sky and almost all apply. **Depth-testing** is what keeps it
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
junction mismatches the land horizon at every sunset.

⚠️ **That sentence is a slogan, and two teams cannot implement it independently and meet in the
middle.** "The atmosphere LUT" is four LUTs; "the view-depth coordinate" is ambiguous in the one
place water has two depths. Stated so it is implementable — this is a contract derived here, not
taken from a source:

> **Exported once, consumed by terrain, water and translucents.**
> - `Transmittance(viewDir, viewAltitude) → RGB` — the sun-path attenuation. **The sun colour every
>   surface lights with comes from here.** A private sun colour is the same class of bug as a
>   private water fog colour, and it is what makes a sunset glint red.
> - `AerialPerspective(screenUV, airDistance) → RGB inscatter + RGB transmittance` — from the froxel
>   volume while `airDistance < volumeFar`, from the sky-view path beyond it, **with the same
>   fallback and the same cross-fade width on both surfaces**. An ocean horizon is 4.8 km from a
>   1.8 m eye and 36 km from a 100 m cliff, so the far field is not an edge case here: if terrain
>   clamps to the last froxel slice and water evaluates analytically, they disagree *exactly at the
>   horizon*, which is the symptom this contract exists to fix.
> - `Sky(dir, viewAltitude) → RGB` — valid for any direction, **including one refracted through a
>   water surface from below**, which is how the sky arrives inside the Snell window when the camera
>   goes under.
>
> **Ordering, which is not derivable from either document.** Aerial perspective is applied **once,
> after the water composite**, on each pixel's own **air** distance. A translucent shader that
> samples scene colour must sample a **pre-aerial-perspective** copy — otherwise the bed's colour
> already carries AP, the water extinguishes it again over the refracted path, and the surface
> applies it a third time. That is three transmittances over one path: the three-media rule above,
> committed across a document boundary where neither side can see it.
>
> **`airDistance` is the camera-to-*surface* distance in air.** `water-rendering.md` is emphatic
> that the in-water path is the refracted distance and never the depth-buffer difference; that
> segment is a different medium and **must not enter the atmosphere lookup at all**. Feed it the bed
> depth and the water goes hazy with bathymetry.

A private water fog colour is the mechanism; one atmosphere source is the fix. The sea, the land and
the sky are three surfaces under one medium, and the horizon is where a disagreement between them is
most visible and least forgivable.

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
| A 40 km vista reads as a miniature | No aerial perspective; fog cards and grading cannot substitute | The froxel volume, 0.04 ms at 32³ [hillaire2020] — but check its depth range covers the vista: a 32-slice volume sized for a few hundred metres leaves the far field to fall back on the sky term alone |
| The scene goes muddy at range and no parameter fixes it | Three media attenuating the same path — aerial perspective, height fog and froxel fog composited as results | Sum coefficients in the shared froxel, integrate once; apply the sky term once at one depth |
| Sea and land disagree in colour exactly at the horizon | A private water fog colour instead of the shared atmosphere path | One atmosphere state, shared — `water-rendering.md` |
| Sky and terrain detach at the horizon when the camera moves | A planet-absolute atmosphere shader jittering against jitter-free terrain | Evaluate in the camera-relative frame — `planetary-precision.md` |
| The sky is fine on the ground and wastes resolution from orbit | The sky-view LUT spends most of itself on empty space | Switch to on-screen ray marching for space views [hillaire2020] §5.3 |
| Mobile spends 3% of the frame rebuilding LUTs | All four rebuilt every frame; the transmittance LUT alone is 0.53 ms on an iPhone 6s and depends only on the medium | Bake transmittance at load; gate multi-scattering on ~1° of sun elevation. Roughly 1.03 ms → 0.38 ms |
| Water and terrain disagree in colour at the horizon *after* both were told to share the atmosphere | They share the LUT and not the **far-field fallback**: one clamps to the last froxel slice, the other evaluates analytically | Same fallback, same cross-fade width, on both surfaces |
| Water is too dark, and worse the further the camera is | Aerial perspective applied to the scene colour the water refracts, then again by the water, then again on the surface | Apply AP once, after the water composite; refract against a pre-AP copy |
| Water hazes with depth of the sea bed rather than distance from the camera | The refracted in-water path fed into the atmosphere lookup | `airDistance` is camera-to-surface, in air, only |
| A time-of-day sweep costs 250 ms a step | The old precompute being rebuilt per step for a sun move it does not need — sun angle is a table AXIS, not a bake input | Move `u_µs`; rebuild nothing. If the medium is what changes, use the in-frame LUT set [hillaire2020] |
| Volumetric shadows triple the sky cost | 32 ray-march samples with jitter and reprojection | Budget the 1.0 ms, or drop the feature. ⚠️ Do **not** simply cut samples and lean harder on TAA: that trades a measured cost for ghosting and crawling shafts, which is an unmeasured one |
