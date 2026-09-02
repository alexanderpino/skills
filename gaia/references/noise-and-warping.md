---
type: Technique
title: Noise and domain warping — the initial condition
description: "The base layer erosion runs on: which gradient noise, which fractal composition, and the warp that costs three evaluations."
tags: [generation, noise, fbm, domain-warp, authoring-time, real-time]
status: draft
generated: { by: process:claude-code, at: 2026-09-02T00:00:00Z }
sources:
  - { id: perlin2002, tier: P, locator: "§3 Modifications, p. 682 — the quintic fade 6t^5 - 15t^4 + 10t^3 replacing 3t^2 - 2t^3, and the 12 cube-edge gradient vectors listed there, padded to 16" }
  - { id: perlin1985, tier: P, locator: "§ Noise(), p. 289 — a hashed gradient-and-value per lattice point and only 'a smooth (eg. cubic polynomial) interpolation'; the paper never writes 3t^2 - 2t^3 down" }
  - { id: opensimplex2, tier: F, locator: "README §3D Noise (ImproveXY Orientation), and the noise3_ImproveXY body in java/OpenSimplex2.java — the XY planes are rotated 'far out of alignment with the cube faces'" }
  - { id: gustavson2005, tier: F, locator: "§Example code, p. 11 — the 2D noise() listing with F2 = 0.5*(sqrt(3)-1) and G2 = (3-sqrt(3))/6; the isotropy claim is the third advantage bullet on p. 1" }
  - { id: worley1996, tier: P, locator: "§Computation of Fn(x) — a Poisson feature-point count per cube, mean about 4, clamped to 1..9; §Application to texturing — F2-F1 vanishes on the Voronoi boundaries and gives the vein-like ridge tracery" }
  - { id: musgrave_tm, tier: F, locator: "the RidgedMultifractal() listing, weight = signal*gain clamped to 0..1, and the HybridMultifractal() listing, whose 'prevent divergence' clamp is if weight > 1.0 then weight = 1.0" }
  - { id: quilez_warp, tier: F, locator: "§The idea — the two nested listings, q then r, both with K = 4.0; §The experiments — q and r exposed as extra outputs for colouring" }
  - { id: fournier1982, tier: P, locator: "§3.2.3 A Recursive Subdivision Algorithm, pp. 375–376; §4.1.2.1 Polygon Subdivision, p. 379 — side midpoints first, then the centre from the opposed midpoints" }
  - { id: lagae2009, tier: P, locator: "§2.3 eq. 6, the Gabor kernel; §2.4 — the kernel's magnitude, orientation, principal frequency and bandwidth are the noise's; §4 for procedural evaluation" }
  - { id: cook2005, tier: P, locator: "§2 Overview, steps 1–4 — N is R minus the downsampled-then-upsampled R; §4.3 Noise tiles for the precomputed tile" }
  - { id: bridson2007, tier: P, locator: "§2.1 Curl, eq. 1 in 3D and eq. 2 in 2D — v is the curl of a potential, divergence-free because the divergence of a curl is identically zero" }
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

**Fade.** Use the quintic `6t^5 - 15t^4 + 10t^3` [perlin2002], never the cubic `3t^2 - 2t^3`.
The cubic's second derivative `6 - 12t` is non-zero at the lattice points, so the grid prints
through anything that reads curvature — normal maps and every curvature-driven mask in
`terrain-analysis-masks.md`. The difference is two multiplies. ⚠️ **Both the cubic and that
second derivative are written down in [perlin2002] §2, not in the 1985 paper.** [perlin1985]
introduces Noise but specifies only "a smooth (eg. cubic polynomial) interpolation" and never
gives the polynomial, so attributing `3t^2 - 2t^3` to it — as this document did, and as the
bibliography entry still does — reads a constant into a source that does not carry it.

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

⚠️ **Per-octave offsets fix this too — and the recommended fBm above already has them.** The
offset was introduced for a different problem (octave correlation), but with a non-lattice `O_i`
octave *i* is evaluated off-lattice and is generically non-zero at the coarse lattice points, so
only octave 0 still vanishes there. Measured on an 8-octave improved-Perlin stack — mean |value|
at lattice points over mean |value| at generic points, a measurement of an implementation and not
a cited result:

| configuration | lattice / generic |
|---|---|
| lacunarity 2, no offsets | 0.00 |
| lacunarity 2, **with** per-octave offsets (`O_0 = 0`) | 0.44 |
| lacunarity 2.03, no offsets | 0.44 |

Offsets recover the pinch grid at least as well as detuning does, and the residual — 0.44 in both
columns, and around half the generic level in every stack measured — is **octave 0's own zeros**,
which neither fix removes. A mitigation, not a cure. Apply both
anyway: only the offsets decorrelate the octaves. And do not expect a detune to visibly change a
stack that already offsets; it will not, and reading that as "the detune worked" is the trap this
note exists to close.

**Gain** ≈ 0.5. Tying it to a Hurst exponent — `gain = lacunarity^(−H)`, i.e. `2^(-H)` at
lacunarity 2 — is the standard fBm parameterisation and is stated here as common practice, with
no source in this bibliography cited for the identity: H = 1 is the standard smooth-ish terrain,
H = 0.5 (gain ≈ 0.707) is closer to real eroded topography at small scales.

**Octave count** is not a taste parameter: stop when an octave's wavelength falls below ~2 cells.
With base wavelength `W` cells and lacunarity 2, octave *k* has wavelength `W / 2^k`, so
requiring it to stay above ~2 cells gives

    octaves ≈ log2(baseWavelengthInCells) − 1

and the grid's resolution does not enter it — the cutoff is a property of the base wavelength and
the cell, not of the domain's extent. (`log2(resolution / baseWavelengthInCells)`, which
circulates widely, is a different quantity: at 4096 cells with `W = 1024` it returns 2 where this
returns 9, discarding seven octaves of legitimate detail.) Octaves past the Nyquist limit add
aliasing that shimmers under LOD, not detail.

## Ridged and hybrid multifractal

The naive ridged form — `1 - abs(noise)`, squared — gives crumpled paper. What makes it read as
mountains is **weight feedback**: each octave is multiplied by a clamped function of the previous
octave's value, so detail concentrates on the ridges and the valleys stay smooth [musgrave_tm].
Hybrid multifractal multiplies each octave by a running product of the previous octaves' values
instead — seeded with octave 0's own value — so low ground stays smooth and high ground gets rough — the height-roughness correlation real topography has and plain
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
paper's Poisson count — its own implementation uses a mean of about 4 per cube, clamped to 1–9 —
and makes cells too regular. *Gabor noise* [lagae2009] — the only one with
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
| A regular grid of pinch points in the height, and in everything derived from it | Lacunarity exactly 2 *and* no per-octave offsets; all octaves zero at the shared lattice points | Either fix lifts them equally — detune to 2.03, add offsets, or both; octave 0's own zeros remain either way |
| Faint creases along the grid axes under lighting or curvature masks | The cubic fade `3t^2 - 2t^3`, whose second derivative `6 - 12t` is non-zero at lattice points | Quintic fade [perlin2002] |
| Diagonal banding in a field sampled from 3D noise on a flat plane | The simplex lattice has a face parallel to the sampling plane | A lattice-rotated variant [opensimplex2] |
| A mask thresholded near zero outlines the lattice grid | Gradient noise is identically zero at lattice points | Threshold fBm output, or offset the threshold away from 0 |
| Isolated spikes to absurd heights | `min(weight, 1)` dropped from hybrid multifractal | Restore the clamp [musgrave_tm] |
| Normals wrong along every ridgeline | Analytic derivatives of `abs()` at its crease | Finite differences on the final field |
| Terracing far from the world origin | fp32 has ~8 mm of resolution at 100 km; high-frequency octaves compute on garbage low bits | Subtract a per-region offset that is an exact multiple of the noise period, or transform in double |
| Seams at tile boundaries | `noise(uv)` per tile | `noise(worldPos * frequency)`, always |
| A remap curve does nothing to the tails and everything to the middle | The distribution is Gaussian, not uniform, so the knee lands elsewhere | Histogram-match, or apply the curve to the measured range |
| Shimmering under LOD | Octaves below ~2 cells' wavelength | Cut the octave count to `log2(baseWavelengthInCells) − 1` — resolution does not enter it |
| Rivers run uphill after a warp node | The warp moved geometry the drainage was solved on | Move every warp upstream of routing |
