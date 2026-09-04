---
type: Technique
title: Sky and weather state
description: "The atmospheric state a world carries: precomputing a scattering model as a solve rather than a lookup, and the one coverage field that clouds, their shadows and the rain they imply must all read."
tags: [simulation, atmosphere, sky, weather, precomputation, driver-fields]
status: draft
generated: { by: process:claude-code, at: 2026-09-04T00:00:00Z }
sources:
  - { id: bruneton2017, tier: P, locator: "READ IN FULL (arXiv:1612.04336v1, the author's accepted version, which says so on its own p.1; paginated 1-15 and dated 2016, NOT the record's 2641-2655 in the 2017 issue, so sections and tables are cited and pages are not). Table 2 for the eight-model comparison, which carries RMSE in mW/(m2.sr.nm) AND precompute time, precompute memory and render time as complexities, in the same rows -- with two caveats in the caption and section 3.1 that the table alone does not show: the Haber and Nishita96 precompute columns are PER SINGLE SUN ZENITH ANGLE while Bruneton and Elek are for n angles, and the measurement window is 09h30-13h30 with the 06h00 cell n/a: Preetham 88.1, O'Neal 49.5, Hosek 41.5, Nishita93 26.6, Nishita96 18.3, Haber 14.7, Bruneton 11.3, Elek 11.3. Section 14.1 for the same ranking in prose. The RMSE reference is the sky MEASUREMENTS themselves; libRadtran is a physically-based comparison point in the paper, not the error reference" }
  - { id: brunetonneyret2008, tier: P, locator: "READ IN FULL (the publisher-typeset EGSR/CGF version in the Inria HAL deposit inria-00288758, paginated 1-8 as an article rather than 1079-1086, so sections and equations are cited and pages are not). Section 4 Algorithm 4.1 PRECOMPUTE(norders) for the multiple-scattering iteration, verbatim `for i <- 1 to i < norders` -- a FIXED order count with no stopping criterion, tolerance or residual anywhere in the paper; section 2.1 for Rg = 6360 km, Rt = 6420 km, HR = 8 km, HM approx 1.2 km and beta_s_R = (5.8, 13.5, 33.1)e-6 m^-1 at 680/550/440 nm; eq. 2 Rayleigh phase and eq. 4 Cornette-Shanks; section 6 for the three tables 64x256, 16x64 and 32x128x32x8 packed as 32x128x256 RGBA at 8 MB in half precision, and for 125 fps at 1024x768 on an 8800 GTS with 0.4 ms and 2.6 ms term costs. The string ozone does not occur in the paper" }
  - { id: hosekwilkie2012, tier: P, locator: "the analytic tier -- zero precompute, O(1) render -- and its RMSE of 41.5 as scored by bruneton2017 Table 2. Read in the authors' lowres preprint, every page stamped 'To appear in ACM TOG 31(4).' (nine of nine, checked), so it carries no article pagination against the record's 95:1-95:9. Its supplemental material, holding the fitted matrices, was not obtained here, so no coefficient from it is quoted anywhere in this corpus -- the paper itself WAS read" }
  - { id: preethamshirleysmits1999, tier: P, locator: "the analytic baseline, and bruneton2017 Table 2's worst performer at RMSE 88.1. Read in the ACM proceedings copy with folios 91-99 present. Cited for the ozone treatment -- a 0.0035 m NTP column absorber applied to the direct solar beam only, the sole ozone model among these five -- and for being the model everything since is measured against" }
  - { id: nishita1993, tier: P, locator: "the origin of the scale-height atmosphere in graphics and of the constants inherited since; scored 26.6 by bruneton2017 Table 2, ahead of two later models. READ AS PAGE IMAGES, not machine-readable: the author's raster scan at nishitalab.org has no text layer and its pages are stored vertically flipped, so it was read as page images and quotations are transcriptions; no proceedings folios were visible, so pp. 175-182 comes from the record and not from the artefact" }
  - { id: hillaire2020, tier: P, locator: "cited here ONLY for the contrast in what a sun move costs: its Sky-View LUT is a 2D latitude/longitude texture built for the CURRENT sun -- Fig. 4 caption, 'The Sky-View LUT during daytime. The sun direction can be seen on the left side, where Mie scattering happens' -- so a sun move forces a rebuild there, at 0.05 ms per Table 2, where brunetonneyret2008 bakes every sun angle into a table axis and rebuilds nothing. Section 5.3 for why the LUT is resolution-independent. The pass itself is atmosphere-and-aerial-perspective.md's subject" }
  - { id: tr_lighting_shadows, tier: F, locator: "the volumetric-cloud bullets for the ONE SKY STATE rule, verbatim: 'the coverage field that shapes the clouds is the *same* map that drives the cloud-shadow term below and, where a weather system exists, `13`'s weather intensity', and for the cloud scroll vector being the wind vector. A practitioner chapter in a sibling skill, not peer review; cited for what a shipping renderer chose" }
---
# Sky and weather state

## Use this

**Precompute a Bruneton-class scattering model into three tables once per sky state, and carry
exactly one coverage field that the clouds, the cloud shadows and the weather all read**
[brunetonneyret2008] [tr_lighting_shadows].

Two decisions, and they fail differently. Getting the model wrong costs accuracy you can measure.
Getting the *state* wrong costs coherence: clouds that do not match their own shadows, and rain
falling where there is no cloud. The second is the one a player notices.

**What it costs, and how wrong it is.** [bruneton2017] Table 2 is the rare artefact that states
both halves in the same rows — measured error alongside precompute time, precompute memory and
render time. Ranked by error, in mW/(m²·sr·nm):

| Model | Precompute time | Precompute memory | Render | RMSE |
|---|---|---|---|---|
| Preetham | 0 | 0 | O(1) | **88.1** |
| O'Neal | 0 | 0 | O(n) | 49.5 |
| Hosek | 0 | 0 | O(1) | 41.5 |
| Nishita93 | O(n³) | O(n²) | O(n) | 26.6 |
| Nishita96 | O(n³) | O(n³) | O(n) | 18.3 |
| Haber | O(n⁶) | O(n³) | O(n²) | 14.7 |
| **Bruneton** | O(n⁶) | O(n⁴) | **O(1)** | **11.3** |
| Elek | O(n⁶) | O(n⁴) | O(1) | 11.3 |

⚠️ **Three caveats, and each one changes how the table may be used.**

**It is measured against sky measurements, not against a model.** §3.1: the RMSE is between each
model and the ground-truth measurements, summed over daytimes, directions and 360–720 nm.
`libRadtran` appears as a physically-based comparison point, not as the error reference. This
document said "against libRadtran" and was wrong; so did the bibliography entry.

**The window is midday only.** §3.1, verbatim: the measurements are "81 samples over the sky dome,
for **17 daytimes between 9h30 and 13h30**". There is **no sunset in this column**, and the paper's
own 06h00 / 87° cell reads `n/a`. So 88.1 is a statement about how a model performs *near noon* and
may not be cited as evidence about sunsets — which is exactly what an earlier revision of this
document did in its failure table.

**The cost columns are not comparable as printed.** The caption's footnote, which this document
previously dropped: the precompute complexities for **Haber and Nishita96 are for a single sun
zenith angle**, while **Bruneton's and Elek's are for `n` such angles**, and Nishita93's are
independent of sun angle altogether. Haber's O(n⁶) buys one sun position; Bruneton's O(n⁶) buys the
whole sky's worth. Comparing those two columns directly, as the ranking invites you to, understates
Bruneton by a factor of `n`.

Read the *shape* of the table with those caveats in hand. Bruneton and Elek buy the lowest error at
the highest precompute and then render in **O(1)** — and that precompute covers every sun angle,
which is what makes them the ones that ship. Hosek is free to precompute and free to render and
carries 3.7× the error. Haber renders in O(n²), which is the one row not to choose for real time.

⚠️ [bruneton2017] gives **complexities, not wall-clock**. An RMSE from this table must never be
paired with a frame time from another paper and presented as one measurement.

**Alternatives, dismissed in a line each.**

- **Preetham** [preethamshirleysmits1999] — the analytic baseline everything is measured against,
  and the worst of the eight at 88.1. Use it to understand the lineage, not to ship.
- **Hosek & Wilkie** [hosekwilkie2012] — the honest zero-precompute choice at 41.5 when you cannot
  afford a bake at all. ⚠️ But read the whole row before reaching for it: Table 2 marks it
  ground-viewpoint only, **`no` for aerial perspective and `no` for sunrise/sunset**. It is a sky
  dome, not an atmosphere — so it cannot do the job the last bullet dismisses a hand-authored
  gradient for failing at, and an earlier revision of this document recommended it two bullets
  later without noticing.
- **Nishita 93/96** [nishita1993] — the origin, and still ahead of two later models at 26.6 and
  18.3. Cite it for the constants, which everything since inherited.
- **Skip the model, author a gradient** — the pre-2000 answer. It cannot produce aerial
  perspective, and aerial perspective is the whole reason the state exists.

## The precompute is a solve, and it is not a convergence test

This is the part that makes the sky a simulation document rather than a shader one, and it is also
the part most often described wrongly.

[brunetonneyret2008] §4 Algorithm 4.1 accumulates **orders of scattering**: single scattering is
computed first, then each further order is gathered from the previous one and added to the running
total. Multiple scattering has no closed form, so it is built up term by term — a Neumann series
evaluated numerically.

⚠️ **It does not iterate to convergence, and writing that it does would be a fabrication.** The
algorithm reads `for i ← 1 to i < norders`. That is a **fixed count set by the caller**. There is
no stopping criterion, no tolerance, no residual and no convergence rate anywhere in the paper. The
implementation uses **five orders**. So the honest instruction is *choose an order count and state
it*, not *iterate until it settles* — and if you need to know what the fifth order is worth, that
is a measurement this literature does not give you and you will have to make.

**What comes out**, and what it occupies [brunetonneyret2008] §6:

| Table | Dimensions | What it holds |
|---|---|---|
| Transmittance | 64 × 256 | attenuation to the top of the atmosphere |
| Ground irradiance | 16 × 64 | light reaching the surface |
| Inscattering | 32 × 128 × 32 × 8 | the four-dimensional scattering table |

The inscattering table is four-dimensional and no hardware samples 4D, so it ships as eight 3D
slices packed into one **32 × 128 × 256 RGBA** texture with the fourth coordinate interpolated by
hand — **8 MB at half precision**. That is the entire memory cost of the sky, and it is why the
O(n⁴) column in the table above is affordable in practice rather than merely asymptotically.

**The medium, so you can reproduce it** [brunetonneyret2008] §2.1: ground radius 6360 km, top of
atmosphere 6420 km, Rayleigh scale height 8 km, aerosol scale height ≈1.2 km, and Rayleigh
scattering coefficients (5.8, 13.5, 33.1)·10⁻⁶ m⁻¹ at 680, 550 and 440 nm. Rayleigh phase is eq. 2;
the aerosol phase is Cornette–Shanks, eq. 4.

⚠️ **Two traps in the constants.** First, **ozone is not in this model at all** — checked, the
string does not occur in the paper, which treats air molecules and aerosols only. Of the five
sources here only [preethamshirleysmits1999] models ozone, and only as a 0.0035 m NTP column
absorber on the direct solar beam, never in the sky radiance itself. If your sunsets are too
yellow, this is the first thing to suspect and these five will not fix it for you — though [hillaire2020], cited here for a different reason, does carry ozone coefficients and a tent profile in its Table 1.
Second, the paper's two validation figures against the CIE clear sky model use **different aerosol
fits** — Fig. 6 uses `g` = 0.76 with `βs_M` = 2·10⁻⁵ m⁻¹, Fig. 7 uses `g` = 0.73 with 2.2·10⁻⁵.
There is no single "the" value; quote a figure with its number.

## The crossover, with a date and a direction

A threshold stated without a year has a hidden expiry. This one has moved twice and is still
moving, always the same way: **toward paying more up front and less per pixel.**

- **Before 1993** — an authored gradient or vertex fog. No physical state at all.
- **1993** [nishita1993] — the scale-height atmosphere arrives, integrated per ray. Accurate for
  its time and O(n) to render; the constants it chose are still in use.
- **1999** [preethamshirleysmits1999] — the analytic fit. Zero precompute, O(1) render, and
  [bruneton2017] later measures the price at 88.1 RMSE. This is the trade that defined a decade.
- **2008** [brunetonneyret2008] — precompute the hard part into tables. Error drops to 11.3 and
  render becomes O(1); the cost moves to an O(n⁶) bake and 8 MB. On 2008 hardware that bake was
  **5 seconds** and the result ran at 125 fps at 1024×768.
- **2012** [hosekwilkie2012] — the analytic branch answers back, fitted to a brute-force reference
  rather than to a simpler model, and lands at 41.5 with no bake.
- **2017** [bruneton2017] — the branches are measured against each other and against physical
  ground truth for the first time, which is what makes the choice a calculation instead of a taste.
- **2020** [hillaire2020] — and then the direction **reverses at the far end**. An O(1)
  multiple-scattering approximation is run *every frame* rather than baked, so the whole LUT set
  rebuilds in 0.31 ms where the 2008 bake costs 250 ms on a 2016 GPU. Note that figure against
  2008's own "5 orders in 5 seconds": the bake did not get slower, the standard for what may sit
  off-frame got stricter.

**Which way it is still moving.** From 1993 to 2017 the direction was steady — push work off the
frame, because bake time is spent once and pixels are paid 60 times a second. Since 2020 it has
turned: the bake itself became cheap enough to bring *back* on-frame, which is what buys a sky that
can change. The stable statement across both halves is that **the affordable place to be wrong
keeps moving**, and the unstable one is which side of the frame boundary it sits on. If you are
reading this after 2026 and a full per-frame solve has become free, the row to re-examine is
Haber's O(n²) render, not Bruneton's precompute.

## One sky state

The load-bearing idea of this document, and the one that has nothing to do with scattering.

A world with weather has several systems that each want to know what the sky is doing: the cloud
renderer needs a density field, the sun-visibility term needs a shadow factor, the snow and
wetness systems need a precipitation intensity, and the vegetation and particle systems need a
wind vector. The failure is to give each of them its own.

[tr_lighting_shadows] states the rule directly: the coverage field that shapes the clouds is *the
same map* that drives the cloud-shadow term and, where a weather system exists, the weather
intensity. **One field, many readers.** When it is one field, a cloud passing overhead darkens the
ground beneath it and wets the same ground, because those are three reads of one number. When it is
three fields, they drift, and the drift is not subtle — shadows arrive where there is no cloud.

The same source ties the motion together: the scroll vector of the coverage field **is** the wind
vector. Gaia already produces one — `driver-fields.md` computes a wind field from the horizon
sweep — so the coverage field should be advected by that field and not by a private constant.
Clouds, blowing snow and bending grass then agree about the weather because they are reading one
answer to one question.

**A sun move does not invalidate a 4D table, and believing it does is expensive.** The sun
direction is a scene parameter owned by `driver-fields.md`. What belongs here is what has to be
*rebuilt* when something changes — and for [brunetonneyret2008] the answer is: **not the sun.**

Sun zenith is an **axis** of the inscattering table, not a constant baked into it. The table is
`S(u_r, u_µ, u_µs, u_ν)` — §4 Fig. 4 and eq. for `u_µs = (1 − e^(−3µs−0.6))/(1 − e^(−3.6))` — where
`µs = s·x/r` is the sun zenith cosine, given its own 32 samples with a mapping chosen for
"precision … for sun zenith angles near 90°". The 32×128×**32**×8 shape prints that axis on the
page. **Moving the sun changes a texture coordinate and costs nothing.**

⚠️ An earlier revision of this document said the opposite, and put "rebuild only the sun-dependent
table" in its failure table — which would have had a reader rebuild the expensive table and skip
the free one.

**What actually invalidates the bake is the medium**: the scattering coefficients, the scale
heights, the asymmetry `g`, and the ground reflectance `ᾱ`, which is not a rendering constant but a
term **inside Algorithm 4.1 itself** — it appears in the `∆J ← J[T·ᾱ/π·∆E + ∆S]` and
`∆E ← Ē[T·ᾱ/π·∆E + ∆S]` lines, so the ground's brightness participates in the multiple-scattering
solve.

**That is a coupling this corpus had not noticed.** Ground albedo in a terrain tool is **snow
cover**. A snow line that advances or retreats changes `ᾱ`, and a changed `ᾱ` invalidates the
scattering bake. Nothing else in Gaia connects `snow-and-weather-state` to the sky, and this does —
weakly, since the effect is a second-order brightening rather than a visible colour shift, but it is
the difference between a bake you can schedule and one that surprises you.

⚠️ **This is model-specific and does not carry to [hillaire2020].** Its sky-view LUT is a 2D
latitude/longitude texture built *for the current sun* — Fig. 4's caption is "The Sky-View LUT
during daytime. The sun direction can be seen on the left side" — so there a sun move **does**
force a rebuild, and that is precisely why it costs 0.05 ms instead of 250 ms. The two designs
answer the same question in opposite directions: bake every sun angle once and pay 8 MB, or bake
one sun angle every frame and pay almost nothing. `atmosphere-and-aerial-perspective.md` uses the
second.

## What this hands to the rest of the corpus

- **Cloud shadow is a driver field.** The sun-visibility term multiplied by cloud coverage is an
  input to insolation, and insolation drives snow line and thermal weathering — see
  `driver-fields.md`, which owns shadow as a physical input and already couples insolation to those
  processes. A cloud deck that darkens the ground should also slow the melt.
- **The tables are what the renderer samples.** `atmosphere-and-aerial-perspective.md` owns the
  pass; it consumes the three tables produced here and must not rebuild them.
- **The coverage field is what the cloud march reads.** ⚠️ `volumetric-clouds.md` is `planned` and
  **not yet written** — the coverage row exists, the document does not. This is a contract stated in
  advance, deliberately, so that whoever writes it inherits the one-sky-state rule rather than
  authoring a second coverage field. Until then the obligation is on the reader, not on a link.

This document does **not** own the sun position or direction (`driver-fields.md`), the occlusion
integral (`terrain-analysis-masks.md`), or surface snow state, which is the separate
`snow-and-weather-state` topic — that row is surface state and this one is atmospheric state.

## When it fails

| Symptom | Mechanism | Fix |
|---|---|---|
| Sky is plausible at noon and wrong at sunset | An analytic model fitted mainly to high sun. ⚠️ [bruneton2017]'s 88.1 does **not** evidence this: its measurement window is 09h30–13h30 and its 06h00 cell is `n/a`, so the number describes midday. Table 2's `sunset sunrise` column does — Preetham and Hosek are both marked `no` | Move to a model whose row says `yes`, and do not cite an RMSE measured at noon for a sunset defect |
| Sunsets are too yellow and no parameter fixes it | Ozone is absent from the model — it is absent from [brunetonneyret2008] entirely and appears in [preethamshirleysmits1999] only on the direct beam | Add an ozone absorption term — [hillaire2020] Table 1 supplies coefficients and a tent-shaped profile, crediting [bruneton2017]; the other four sources here will not |
| The multiple-scattering bake never "converges" | There is no convergence test in [brunetonneyret2008] Algorithm 4.1 — it runs a fixed `norders` | Choose an order count, state it, and measure what the last order was worth |
| Shadows fall where there is no cloud | Two coverage fields, one for shading and one for the cloud pass [tr_lighting_shadows] | One field, many readers |
| Rain falls in clear sky | Weather intensity authored independently of coverage | Derive intensity from the same field |
| Clouds and blowing snow drift apart | The cloud scroll vector is a private constant instead of the wind field [tr_lighting_shadows] | Advect coverage with `driver-fields.md`'s wind field |
| A time-of-day sweep rebuilds the scattering bake every step | Treating sun angle as a baked constant when it is an **axis** of the 4D table [brunetonneyret2008] §4 | Move the sun by changing `u_µs`; rebuild nothing. Only a change of medium — coefficients, scale heights, `g`, ground albedo `ᾱ` — invalidates the bake |
| The sky bake re-runs when the snow line moves, and nobody knows why | `ᾱ` is ground reflectance and sits **inside** Algorithm 4.1's iteration, so surface albedo is a bake input | Expected, not a bug. Decide whether the second-order brightening is worth a rebake, and schedule it |
| The sky bake blows the memory budget | The 4D inscattering table stored naively | Pack as eight 3D slices in one 32×128×256 RGBA texture, 8 MB at fp16 [brunetonneyret2008] §6 |
