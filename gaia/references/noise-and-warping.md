---
type: Technique
title: Noise and domain warping — the initial condition
description: "The base layer erosion runs on: which gradient noise, which fractal composition, and the warp that costs three evaluations."
tags: [generation, noise, fbm, domain-warp, authoring-time, real-time]
status: draft
generated: { by: process:claude-code, at: 2026-09-02T00:00:00Z }
sources:
  - { id: perlin2002, tier: P, locator: "the quintic fade 6t^5 - 15t^4 + 10t^3, and the 12-vector cube-edge gradient set" }
  - { id: perlin1985, tier: P, locator: "the original cubic fade 3t^2 - 2t^3" }
  - { id: opensimplex2, tier: F, locator: "the noise3_ImproveXY lattice-rotated variants in the reference source" }
  - { id: gustavson2005, tier: F, locator: "the skew/unskew constants F2 and G2 and the 2D reference code" }
  - { id: worley1996, tier: P, locator: "the F1/F2 cellular basis, and the Poisson feature-point count per cell" }
  - { id: musgrave_tm, tier: F, locator: "the ridged and hybrid multifractal formulations, including the weight-feedback terms" }
  - { id: quilez_warp, tier: F, locator: "the fbm of fbm of fbm construction" }
  - { id: fournier1982, tier: P, locator: "the midpoint-displacement subdivision" }
  - { id: lagae2009, tier: P, locator: "the Gabor kernel, and the setup/evaluate split" }
  - { id: cook2005, tier: P, locator: "the band-limited tile construction by downsample-upsample difference" }
  - { id: bridson2007, tier: P, locator: "the curl-of-a-potential construction, divergence-free by definition" }
---
# Noise and domain warping — the initial condition

Noise is the **initial condition** the rest of the pipeline runs on, and nothing more. It has no
memory of water, so it cannot produce a drainage network: ridged fBm makes ridges that read as
mountains in a hillshade and fail a flow-accumulation check immediately, because the valleys do
not connect. Everything here exists to hand erosion a surface worth eroding.

## Use this

**fBm over improved Perlin or OpenSimplex2, lacunarity detuned off 2, then one domain warp**
[perlin2002] [opensimplex2] [quilez_warp]. For mountain relief, swap plain fBm for Musgrave's
**ridged multifractal with weight feedback** [musgrave_tm]; for plains-next-to-mountains, hybrid
multifractal from the same source.

Three constants carry most of the quality: the quintic fade, a lacunarity that is not exactly 2,
and a warp amplitude near the largest octave's wavelength.

## The lattice, and the constants that decide the look

Gradient noise is zero at every lattice point by construction. Two consequences follow, and both
are constants, not code.

**Fade.** Use the quintic `6t^5 - 15t^4 + 10t^3` [perlin2002], never the original cubic
`3t^2 - 2t^3` [perlin1985]. The cubic's second derivative is non-zero at the lattice points, so
the grid prints through anything that reads curvature — normal maps and every curvature-driven
mask in `terrain-analysis-masks.md`. The difference is two multiplies.

**Gradient set.** The 12 cube-edge vectors of [perlin2002] remove the directional bias of random
gradients and reduce `grad()` to adds. The 2D reduction most heightfields actually call uses the
8-vector set (4 axes + 4 diagonals), which mixes magnitude 1 and magnitude √2, so its practical
range reaches ≈±1 rather than the ±0.707 of a unit-gradient set. **Measure the range of your
octave stack and remap against the measurement**; normalising by a theoretical maximum gives a
washed-out field, because the distribution is roughly Gaussian and never fills its bound.

**Seeding.** Shuffle the permutation table with the seed. Seeding by adding an offset to the
input coordinate gives "seeds" that are translations of one pattern, and any two of them will
line up somewhere in a large world.

**Lattice rotation.** If you sample 3D noise on an axis-aligned plane — the usual way to get an
animatable or layered 2D field — the naive simplex lattice has a face parallel to your sampling
plane and you get diagonal banding. Use a lattice-rotated variant [opensimplex2]. This catches
people constantly, and the artefact looks like a filtering bug rather than a lattice choice.

## fBm, and why lacunarity is never exactly 2

```
fbm(p, octaves, lacunarity = 2.03, gain = 0.5):
    sum = 0;  amp = 1;  freq = 1;  norm = 0
    for i in 0..octaves-1:
        sum  += amp * noise(p * freq + octaveOffset[i])
        norm += amp
        freq *= lacunarity
        amp  *= gain
    return sum / norm
```

At lacunarity exactly 2, every octave's lattice coincides with the coarsest one's, so at those
shared points **every octave is zero at once** and so is the sum — not small, exactly zero. The
result is a regular grid of hard pinch points that prints through every field derived from the
height. Detuning to 2.03 lifts those points to roughly half the generic level; it is a mitigation,
not a cure, and it costs nothing.

⚠️ The per-octave offset is a **different** fix for a **different** problem (octave correlation).
It does not touch the pinch grid, because those zeros come from lattice geometry. Apply both.

**Gain** ≈ 0.5, and `gain = 2^(-H)` ties it to the Hurst exponent: H = 1 is the standard
smooth-ish terrain, H = 0.5 (gain ≈ 0.707) is closer to real eroded topography at small scales.

**Octave count** is not a taste parameter: stop when an octave's wavelength falls below ~2 cells,
i.e. `octaves = log2(resolution / baseWavelengthInCells)`. Octaves past the Nyquist limit add
aliasing that shimmers under LOD, not detail.

## Ridged and hybrid multifractal

The naive ridged form — `1 - abs(noise)`, squared — gives crumpled paper. What makes it read as
mountains is **weight feedback**: each octave is multiplied by a clamped function of the previous
octave's value, so detail concentrates on the ridges and the valleys stay smooth [musgrave_tm].
Hybrid multifractal multiplies each octave by the accumulated value instead, so low ground stays
smooth and high ground gets rough — the height-roughness correlation real topography has and plain
fBm does not.

Two traps, both in the same source and both routinely dropped in online versions:

- **`min(weight, 1)` in hybrid multifractal is not optional.** Without the clamp the product
  diverges and you get isolated spikes to absurd heights.
- **Ridged noise is not differentiable at the ridgeline.** `abs()` has a discontinuous derivative
  at zero — that crease *is* the ridge. Analytic normals are wrong there; take finite differences
  on the final heightfield.

## Domain warp

```
warp1(p) = fbm(p + K * vec2(fbm(p + O1), fbm(p + O2)))                    # 3 fBm evaluations
warp2(p): q = vec2(fbm(p + O1), fbm(p + O2))
          r = vec2(fbm(p + K1*q + O3), fbm(p + K1*q + O4))
          return fbm(p + K2*r)                                            # 5 fBm evaluations
```

The highest ratio of visual improvement to implementation cost in the whole noise section
[quilez_warp]. `K` is an amplitude in the units of `p`: start at roughly the wavelength of the
largest octave. Much smaller does nothing visible; much larger dissolves the structure into soup.
Return `q` and `r` alongside the height — they are free masks that correlate with the warp
structure, so materials placed by them follow the terrain's apparent flow direction.

⚠️ **Warping is not erosion, and a warp after erosion is a bug.** Warp produces the *appearance*
of flow-aligned structure with none of the connectivity. And because the drainage network was
computed on the pre-warp geometry, a warp applied downstream of erosion leaves rivers that no
longer run downhill — a change that looks excellent in a hillshade and fails flow accumulation
instantly. Every warp belongs upstream of routing.

**What it beats.** *Diamond-square / midpoint displacement* [fournier1982] — the 1982 original
and a real paper, but it is a grid rather than a function: you cannot sample it at an arbitrary
point, evaluate a tile lazily, change resolution, or tile it, and its two passes have different
neighbour sets so the axes print through. *Value noise* — no canonical source; cheaper, but the
extrema sit on the lattice so the grid is far more visible; usable only as one octave inside a
stack. *Simplex* [gustavson2005] — 3 corners instead of 4 in 2D, which is no meaningful win for a
heightfield; the reason to use it is isotropy, and in 3D/4D the corner count is the win.
*Worley F2−F1* [worley1996] — cell and crack structure for rock, mud flats and boulder fields, not
a base layer; note the one-point-per-cell simplification everyone ships is a deviation from the
paper's Poisson count and makes cells too regular. *Gabor noise* [lagae2009] — the only one with
local control of frequency, bandwidth and **orientation**, so the only one that can do anisotropy
honestly; far too expensive for base terrain, correct for aligned detail layers. *Wavelet noise*
[cook2005] — genuinely band-limited, which matters only if you synthesise per-frame at varying
LOD; for a baked heightfield the export resolution has already band-limited everything.
*Curl noise* [bridson2007] — divergence-free, so it swirls a warp without pinching or tearing;
a warp field, not a height source.

**Time budget.** An fBm octave is a lattice fetch plus a handful of dots, so the whole stack is a
per-frame operation — this is the one part of terrain generation that genuinely is. Budget in
evaluations, not octaves: `warp1` is 3 fBm calls and `warp2` is 5, so a warped 8-octave field is
24 or 40 noise evaluations per sample. Offline, take `warp2` and as many octaves as Nyquist
allows. Per frame, take `warp1` and drop octaves by distance — the far LOD does not need the
octaves it cannot resolve anyway, and dropping them is also the poor-man's band-limiting.

## How this fails, and what it looks like

| Symptom | Mechanism | Fix |
|---|---|---|
| A regular grid of pinch points in the height, and in everything derived from it | Lacunarity exactly 2; all octaves zero at the shared lattice points | Detune to 2.03; add per-octave offsets as well, for the other artefact |
| Faint creases along the grid axes under lighting or curvature masks | The 1985 cubic fade, whose second derivative is non-zero at lattice points | Quintic fade [perlin2002] |
| Diagonal banding in a field sampled from 3D noise on a flat plane | The simplex lattice has a face parallel to the sampling plane | A lattice-rotated variant [opensimplex2] |
| A mask thresholded near zero outlines the lattice grid | Gradient noise is identically zero at lattice points | Threshold fBm output, or offset the threshold away from 0 |
| Isolated spikes to absurd heights | `min(weight, 1)` dropped from hybrid multifractal | Restore the clamp [musgrave_tm] |
| Normals wrong along every ridgeline | Analytic derivatives of `abs()` at its crease | Finite differences on the final field |
| Terracing far from the world origin | fp32 has ~8 mm of resolution at 100 km; high-frequency octaves compute on garbage low bits | Subtract a per-region offset that is an exact multiple of the noise period, or transform in double |
| Seams at tile boundaries | `noise(uv)` per tile | `noise(worldPos * frequency)`, always |
| A remap curve does nothing to the tails and everything to the middle | The distribution is Gaussian, not uniform, so the knee lands elsewhere | Histogram-match, or apply the curve to the measured range |
| Shimmering under LOD | Octaves below ~2 cells' wavelength | Cut the octave count to `log2(res / baseWavelengthInCells)` |
| Rivers run uphill after a warp node | The warp moved geometry the drainage was solved on | Move every warp upstream of routing |
