---
type: Technique
title: Mask to material — from weights to albedo
description: "The step terrain-analysis-masks.md stops before: turning a set of material weights into a colour. Palettes driven by a scalar, the partition of unity, the splatmap channel budget, height-blended against alpha-blended transitions, and the colour space each of those has to happen in."
tags: [generation, materials, masks, colour, splatmap, real-time]
status: draft
generated: { by: process:claude-code, at: 2026-09-03T00:00:00Z }
sources:
  - { id: sharma2005, tier: P, locator: "the 34-pair supplementary test data (Table I and the file ciede2000testdata.txt from the first author's site), used here to validate an implementation; the Introduction, for the finding that several independently distributed CIEDE2000 implementations — including the authors' own early ones — passed the CIE's worked examples and were still wrong; the implementation notes on signed ΔC′ and ΔH′, the arctangent quadrant in eq. (7) and the mean-hue boundary cases in eq. (14)" }
  - { id: moreland2009, tier: P, locator: "read in the author's expanded version, ColorMapsExpanded.pdf. §2.2 Color Spaces, eqs. (1)-(3) (NOT §3, which is Color Map Requirements and contains no equations) — the sRGB→linear transfer function, the linear-RGB→XYZ matrix and the XYZ→CIELAB conversion, with the statement that physical light effects belong in a linear space while perception of a colour belongs in CIELAB; §2 for the case against the rainbow map — no perceptual ordering, non-uniform perceptual rate, and sensitivity to colour-vision deficiency" }
  - { id: icc_srgb, tier: F, locator: "§A.8 Color component transfer function for the ENCODING equations and Part B Hints for profile makers for the DECODING inverse (NOT §B for both, as this said) — linear <= 0.0031308 scaled by 12.92, otherwise 1.055·L^(1/2.4) − 0.055; encoded ≤ 0.04045 divided by 12.92, otherwise ((E+0.055)/1.055)^2.4; §A.7 for the XYZ(D65)→linear-sRGB matrix used to build the CIELAB conversion here; §A.1–A.3 for the BT.709 primaries and the D65 white point" }
  - { id: srgb1996, tier: F, locator: "the W3C obsolescence notice at the head of the document — the 1996 proposal was superseded by IEC 61966-2-1 and 'during standardization, a small numerical error caused by rounding error was corrected'" }
  - { id: mishkinis2013, tier: F, locator: "the height-based splat blend — per-layer height maps biased by the layer weights, with a depth or contrast term deciding how much of the runner-up survives near the boundary" }
---
# Mask to material — from weights to albedo

`terrain-analysis-masks.md` ends at a set of material weights summing to ≤ 1. Nothing on the
generation axis says what a material *is*. This document is the rest of that sentence: weights in,
a colour out, and the four places where the arithmetic between them is routinely wrong.

**Boundary.** `terrain-analysis-masks.md` owns computing the weights. `virtual-texturing.md` owns
caching and streaming the *result* — if the composite below is too expensive per frame, that is
where the answer is, and it is not restated here. `layering-filters-and-masks.md` owns where in the
graph the masks are applied.

## Use this

**Composite materials as a weighted sum of linear-light albedos, with the weights normalised to
sum to exactly 1 at the point of use, and let the weights come from a height-aware blend rather
than a straight cross-fade.** In one expression, for `n` materials with weights `w_i`, albedo
textures `A_i` and height channels `h_i`:

```
b_i  = w_i + h_i                                 # height-biased weight [mishkinis2013]
m    = max_i(b_i) − depth                        # keep only what is within `depth` of the winner
w'_i = max(b_i − m, 0)
A    = Σ w'_i · linear(A_i) / Σ w'_i             # linear light, normalised at the last moment
```

Four decisions are packed into that, and each is dismissible in a line:

- **Weighted sum, not an ordered over-composite.** An over-composite hides an over-subscribed
  weight set completely (`terrain-analysis-masks.md` makes the same point at the producer end); a
  normalised sum makes the bug visible and the result order-independent.
- **Linear albedo, not sRGB.** Blending in the encoded space is measurably wrong — up to
  **ΔE00 = 16.4** and **48% of the luminance** on the pairs measured below.
- **Height-aware weights, not a linear cross-fade.** A cross-fade makes every texel at the
  boundary a 50/50 average, which is a third material that exists nowhere. Measured below: alpha
  blending leaves **100%** of texels a mix at the midpoint against **4.9%** for a height blend, and
  costs **29% of the texture's contrast**.
- **Normalise at the point of use.** Not at the producer, not per layer — see the partition of
  unity below, where an unnormalised sum is exactly a brightness multiplier until it clips.

**What it beats.** *A colour ramp on height alone* — the "topographic map" look; height is the one
input that guarantees horizontal banding. *An ID map with no blending* — hard boundaries at texel
resolution, which reads as a jigsaw at any distance. *Per-material forward passes* — correct and
`n×` the fill rate, which is the problem `virtual-texturing.md` exists to solve.

## The palette: a colour lookup driven by a scalar

The cheapest material system is a 1D lookup table indexed by a scalar — height, slope, wetness,
deposition depth — and it is a legitimate one for distant terrain, macro colour variation, and
anything that must fit in a single texture fetch. Three rules make it not look like a chart:

- **Drive it with something other than height wherever possible.** Height is monotone in one
  direction, so a height palette produces contour bands. Wetness, deposition and occlusion are
  spatially irregular, so they read as material rather than as elevation.
- **Do not use a rainbow.** [moreland2009] §2 gives the reasons in the visualisation setting — no
  perceptual ordering, a perceptual rate that varies wildly along the ramp, and colours that
  collapse under common colour-vision deficiencies. Terrain inherits all three.
- **Break the index with noise before the lookup**, exactly as `terrain-analysis-masks.md` requires
  of a threshold. A LUT indexed by a smooth field has the same perfect contour problem a hard
  threshold does.

**Which space to interpolate the palette in, measured.** [moreland2009] §3 draws the distinction
this document is built on: physical light effects belong in a linear space, perceptual ones in
CIELAB. A palette *ramp* is perceptual — you want even-looking steps — and this is the one place
where interpolating in linear light is the wrong answer. Stepping a 32-entry ramp between two
terrain colours three ways and measuring the perceptual size of each step with ΔE00
(`colour_blend.py`, recorded in `registers/pseudocode-execution.tsv`):

| Ramp | largest / smallest step | coefficient of variation |
|---|---|---|
| forest → snow, interpolated in **linear** | **10.62×** | 78.3% |
| forest → snow, interpolated in sRGB | 1.79× | 17.3% |
| forest → snow, interpolated in **CIELAB** | **1.54×** | 12.6% |
| wet rock → sand, linear / sRGB / CIELAB | 5.29× / 1.37× / **1.28×** | 48.7% / 8.3% / **7.1%** |

A linear-light ramp between a dark and a light colour spends most of its entries in a range the eye
cannot separate and then jumps. **Author and interpolate the palette in CIELAB; convert the result
to linear light once, at bake time, and store the LUT linear.** That is not a contradiction of the
rule below — the palette is authored perceptually and *consumed* linearly.

## Weight normalisation: the partition of unity

A material set is a partition of unity: `Σ w_i = 1` everywhere, so every point is fully described
and the composite is an average rather than an accumulation. `terrain-analysis-masks.md` builds the
weights to satisfy `Σ ≤ 1` by construction with a priority stack. This is what happens when that
guarantee is broken, measured on a three-material composite:

| `Σ w` | resulting luminance | channels clipped |
|---|---|---|
| 0.70 | 70.0% of correct | 0 |
| 0.90 | 90.0% | 0 |
| 1.00 | 100.0% | 0 |
| 1.30 | 130.0% | 0 |
| 1.60 | 158.3% | 1 |
| 2.00 | 159.9% | 3 |

Two regimes, and the second is why this is hard to diagnose. **Below clipping, an unnormalised
weight set is exactly a brightness multiplier** — 0.7 gives 70.0%, 1.3 gives 130.0%, linear and
uniform, so the terrain simply looks mis-exposed and everyone reaches for the exposure control.
**Above clipping it becomes a hue shift**: at `Σ = 1.6` one channel has saturated, so luminance
tracks at 158.3% instead of 160% and the ratio between channels has changed; at 2.0 all three are
pinned and the surface is white regardless of what material is under it. The transition between
those two regimes is a function of the *albedo*, so a bug that is invisible on dark rock appears on
snow, in one part of the map.

**Normalise by the sum at the point of use — `A = Σ w_i A_i / Σ w_i` — and assert.** Dividing by
the sum is one extra reciprocal and makes the whole class of failure impossible. Assert
`|Σ w − 1| < 1e-3` in a debug build, and render `Σ w` to a debug view mapped so that 1.0 is grey:
over-subscription is then a bright region and under-subscription a dark one, which is the fastest
diagnosis available.

⚠️ **`Σ w = 1` must hold after interpolation, not just at the texel centres.** A splatmap is
bilinearly filtered, and a weighted sum of partitions of unity is a partition of unity, so
interpolation is safe — *unless* the weights were normalised per-texel after quantisation to 8 bits
and the sum is 254/255 in one texel and 256/255 in the next. Normalise in the shader after the
fetch, not in the texture.

## The splatmap and its channel budget

The standard representation is an RGBA texture whose channels *are* the weights: four materials per
splatmap, at a resolution independent of both the heightfield and the albedo textures. There is **no
canonical source for this representation; standard practice is** an RGBA control texture plus an
array of tiling material textures, and every engine's terrain system is a variation on it.

The arithmetic that decides the design:

- **Four weights per texture.** `n` materials need `ceil(n/4)` splatmaps, and each one is another
  texture fetch per pixel *and* another set of albedo/normal/roughness fetches for the materials it
  addresses. Eight materials is two splatmaps and up to eight material sets: 8 × 3 = 24 texture
  fetches per pixel before lighting.
- **The cheap escape is a bound on simultaneous materials, not on total materials.** A world can
  have forty materials as long as no *pixel* mixes more than four. The two representations are the
  weight vector (fixed cost, `n` materials wide) and the ID+weight pair (fixed cost, `k` materials
  deep, `n` unbounded): store, say, four `(material_id, weight)` pairs per texel, indexing into a
  **texture array** so every material is one array slice and the fetch count is bounded by `k` no
  matter how many materials exist.
- **A texture array requires every slice to share dimensions, format and mip count.** That is the
  actual constraint that bites — not the slice count. Budget it as one decision at the start of the
  project, because retrofitting a 2048² array onto a library authored at mixed resolutions is a
  re-export of every material.
- **The splatmap does not need the albedo's resolution.** Material boundaries are low-frequency;
  the detail comes from the tiling textures. A splatmap at 1/4 of the albedo resolution is normal,
  and the height blend below is what keeps the boundary crisp despite it.

Beyond that budget, the answer is to composite once and cache — which is `virtual-texturing.md`'s
subject, and it owns both the page cache and the crossover into streaming.

## Height blending versus alpha blending

Given two materials and a weight `t`, a linear cross-fade computes `A = (1−t)A₁ + tA₂`. Every texel
in the transition band is then a genuine average of gravel and grass, which is a material that does
not exist. Height blending instead uses each material's own height channel to decide, per texel, which one is
on top. There is **no canonical source for it; standard practice is** the recipe in an article
[mishkinis2013] — graded `F`, not peer-reviewed — reimplemented in every engine since: bias each layer's height by its weight, take the maximum,
and keep only the layers within `depth` of it.

Measured (`colour_blend.py`, recorded in `registers/pseudocode-execution.tsv`, 4096 texels, uniform height channels):

| | alpha blend | height blend, depth 0.02 | depth 0.1 | depth 0.3 |
|---|---|---|---|---|
| 10–90% transition width, per texel, in weight units | 0.800 | **0.018** | 0.089 | 0.259 |
| ...as a multiple of `depth` | — | 0.90× | 0.89× | 0.86× |
| texels that are a *mix* at `t = 0.5` | **100%** | 4.9% | 18.4% | 48.6% |
| composited contrast, two textures of equal σ | **71% of σ** | — | **96% of σ** | — |

Three things fall out of that table.

**`depth` is the *per-texel* transition width, in weight units, to within 14% — and it is not the
width of the boundary you see.** ⚠️ There are two widths here and an earlier draft reported one of
them as both. Per texel, the flip from 10% to 90% takes `0.89 × depth` at every depth measured
(0.018, 0.089, 0.259 at depth 0.02, 0.10, 0.30). But every texel flips at a *different* `t`,
because each carries a different height, so the **ensemble** band — the range of `t` over which the
surface is a visible mixture — measures **0.56, 0.56, 0.61**: essentially independent of `depth`,
and 30× wider than the per-texel figure at `depth = 0.02`.

So `depth` sets **how dithered the boundary is, not how wide it is**. That is still the parameter
worth authoring, and the table's own strongest row says why: at `t = 0.5` alpha blending has
**100%** of texels in a mixed state and height blending has **4.9%** at `depth = 0.02`. The
boundary occupies a similar span of weight either way; what changes is whether it resolves into
interlocking grains or smears. A reader sizing a transition band from `depth` alone would ask for
0.018 and get 0.56.

**Alpha blending destroys texture contrast, by an amount you can predict.** Averaging two
independent textures of equal standard deviation gives `σ/√2 = 70.7%` of the original — measured at
**71%**. That 29% loss is precisely the "muddy band" look at every material boundary in a naive
terrain shader, and no amount of sharpening the albedos fixes it, because the loss happens after
they are sampled. Height blending keeps **96%**.

**The transition width no longer depends on the splatmap resolution.** With a cross-fade, the band
is as wide as the splatmap's bilinear ramp — so a low-resolution control texture gives a wide,
obviously blurry boundary. With a height blend, the width is `depth` in weight space and the
*shape* comes from the height channel, which is at albedo resolution. A 512² splatmap over a 2048²
albedo produces a crisp interlocking edge. This is why height blending is worth its cost on a
memory-constrained target specifically.

⚠️ **The height channels have to be authored, and they have to be comparable.** `depth` compares
`h₁` and `h₂` directly, so if one material's height channel occupies 0.2–0.4 and another's occupies
0.0–1.0, the second wins nearly everywhere regardless of the weights. Normalise every material's
height channel to the same range at import, or the blend is a material-authoring lottery. And
height-blend the *normals and roughness with the same weights* — blending albedo one way and
normals another produces a boundary whose lighting disagrees with its colour.

⚠️ **A height blend is not differentiable across the boundary and must not drive geometry.** The
`max` makes it piecewise; used as a displacement weight it creases. Use the smooth normalised form
for anything geometric, and reserve the height blend for surface appearance.

## Colour space: where linear is required, and where it is wrong

sRGB is not a gamma-2.2 curve; it is piecewise — a linear segment near black and a 2.4 power
elsewhere — `encode` is [icc_srgb] §A.8, `decode` is its Part B:

```
encode(L) = 12.92·L                       for L ≤ 0.0031308
          = 1.055·L^(1/2.4) − 0.055       otherwise
decode(E) = E / 12.92                     for E ≤ 0.04045
          = ((E + 0.055) / 1.055)^2.4     otherwise
```

Those constants are not quite self-consistent, and it is worth knowing why before you are hunting a
one-LSB seam: `12.92 × 0.0031308 = 0.040449936`, against the decode threshold of `0.04045` — a gap
of **6.4e-8**, or 0.00002 of an 8-bit code value. That is the residue of the rounding error
[srgb1996] records being corrected during standardisation, and it is far below quantisation, so it
matters only if you are testing exact continuity. The round trip itself is clean: decode∘encode
over 10001 samples of [0,1] is accurate to **4.4e-16** — but ⚠️ that is a **sampling artefact**, not
exactness: a coarse grid steps over the knot. Resampling 300001 points across [0.0030, 0.0033],
where the two branches actually disagree, the round-trip error is **2.3e-09**. Still far below any
8-bit or even 16-bit quantisation, so the conclusion is unchanged and the reason for it is not:
the curve is not float64-exact, it is exact everywhere you are unlikely to sample.

**Blending in the encoded space is a real, large error, not a purist's complaint.** Measured
(`colour_blend.py`, recorded in `registers/pseudocode-execution.tsv`) as the difference between lerping the *encoded* values and
lerping the *linear* ones, for chosen 8-bit terrain albedos, reported as CIEDE2000 and as the error
in linear luminance:

| pair, at `t = 0.5` | ΔE00 | luminance error | worst channel, linear |
|---|---|---|---|
| snow / forest | **11.68** | −36.2% | 44.1% |
| wet rock / snow | 9.96 | −35.9% | 38.0% |
| snow / red rock | 9.18 | −19.6% | 39.5% |
| sand / forest | 7.96 | −26.7% | 33.7% |
| wet rock / sand | 7.22 | −26.2% | 28.3% |
| dry grass / snow | 6.32 | −10.3% | 26.3% |
| dry grass / sand | 1.00 | −1.8% | 4.4% |
| wet rock / forest | 0.42 | −0.5% | 3.3% |

Across the whole blend for the worst pair: ΔE00 2.31 at `t = 0.1`, 11.68 at 0.5, and a maximum of
**16.35 at `t = 0.75`**, where the luminance is **48.2% too dark**. For scale, a ΔE00 of 1 is
roughly a just-noticeable difference, so 16 is not subtle — it is the difference between a snow
line and a mud line. **Every luminance error is negative**, because the encoding curve is concave:
an sRGB-space blend is *always* the darker one, which is why the artefact reads as a dark seam
along every material boundary and around every alpha-blended decal edge.

The last two rows are the reason the bug survives review: between two colours that are already
close (wet rock and forest, ΔE00 0.42), the error is invisible. It appears only where the contrast
is high, which is where the terrain is most likely to be looked at.

**So:** sample albedo textures through an sRGB-decoding sampler (`*_SRGB` formats decode in
hardware, for free, with correct filtering), keep every weight, blend and lighting computation in
linear light, and encode once at the end of the frame. Height, roughness, metalness, AO, masks and
splatmaps are **not colours** and must be stored in linear/UNORM formats — decoding a roughness map
through an sRGB sampler is the mirror-image bug and produces surfaces that are too smooth in the
mid-range.

**Measuring it yourself.** ΔE00 is the right metric and a famously easy formula to get wrong.
[sharma2005] exists because several independently published implementations passed the CIE's own
worked examples and were still incorrect; the paper ships 34 supplementary CIELAB pairs chosen to
catch exactly those errors. The implementation used for every number above was validated against
all 34: worst disagreement **4.95e-5** against a table printed to four decimals. Do not trust a
colour-difference number, including the ones in this document, from an implementation that has not
been run against that file.

## How this fails, and what it looks like

| Symptom | Mechanism | Fix |
|---|---|---|
| A dark seam along every material boundary | Albedo blended in sRGB; the encoding curve is concave, so the midpoint is always darker | Decode to linear before blending; up to 48% luminance, ΔE00 16 |
| The seam is invisible in the grey blockout and obvious on snow | The sRGB blend error scales with the contrast of the pair | Same fix; test on the highest-contrast pair, not the average one |
| Whole terrain looks mis-exposed, uniformly | `Σ w ≠ 1` below the clipping point — an exact brightness multiplier | Normalise by `Σ w` at the point of use; assert |
| Bright patches wash out to white and shift hue | `Σ w > 1` and channels clipping — luminance stops tracking | Same fix; render `Σ w` to a debug view with 1.0 as grey |
| Surfaces too smooth in the mid-range | Roughness map sampled through an sRGB decoder | Roughness, height, AO and masks are linear/UNORM data, not colour |
| A muddy 50/50 band at every material boundary | Linear cross-fade; every texel is a genuine average | Height blend [mishkinis2013] |
| Material textures look softer where they meet | Averaging two textures of equal σ gives σ/√2 — 29% of contrast lost | Height blend keeps 96% |
| Boundaries blurry in exact proportion to the splatmap resolution | Alpha blend width is the splatmap's bilinear ramp | Height blend: width is `depth`, shape is the height channel |
| One material wins every boundary regardless of weights | Height channels authored at incomparable ranges | Normalise every height channel to the same range at import |
| Lighting at a boundary disagrees with the colour | Albedo height-blended, normals cross-faded | One weight set for albedo, normal, roughness |
| Displacement creases at material boundaries | Height blend's `max` is not differentiable | Smooth normalised weights for anything geometric |
| Height blend behaves like an expensive cross-fade | `depth` set large; it *is* the transition width | `depth ≈ 0.02–0.1` in weight units |
| Splat weights change discontinuously across a texel edge | Weights normalised per-texel before quantisation, then interpolated | Normalise in the shader after the fetch |
| Horizontal colour banding across the whole terrain | Palette driven by height alone | Drive from wetness, deposition or occlusion; noise-break the index |
| A palette ramp that crawls then jumps | Ramp interpolated in linear light — 10.6× step-size ratio measured | Interpolate in CIELAB; store the baked LUT linear |
| The palette obscures the very feature it was made to show | Rainbow map: no perceptual order, uneven rate | [moreland2009] §2; a monotone or diverging ramp |
| 24 texture fetches per pixel and falling frame rate | One splatmap channel per material, all fetched everywhere | Bound *simultaneous* materials with ID+weight pairs into a texture array |
| A new material cannot be added without re-exporting the library | Texture array requires identical dimensions, format and mip count per slice | Fix the array format at project start |
| Composite is correct but too expensive per frame | Recomposited every frame from scratch | Cache the composite — `virtual-texturing.md` |
