---
type: Technique
title: Surface modification and scale space — changing the skin without moving the mountain
description: "Band-splitting a heightfield so an operator can rework the surface without destroying the silhouette: what the split does and does not conserve, and what it costs a tiled build."
tags: [generation, scale-space, surface, filtering, authoring-time]
status: draft
generated: { by: process:claude-code, at: 2026-09-03T00:00:00Z }
sources:
  - { id: burt1983, tier: P, locator: "§The Generating Kernel, p. 533 — the normalized symmetric 5-tap kernel and the equal-contribution constraint a + 2c = 2b; Fig. 3, p. 534 for the kernel shape against a, including the negative lobes at a = 0.6; eq. (3) and eq. (4), p. 535 for the band definition and exact reconstruction; p. 537 for the a = 0.6 entropy result" }
  - { id: paris2011, tier: P, locator: "§2 Pyramid-based Edge-aware Filtering for the one-sentence statement that rescaling Laplacian coefficients directly typically produces halos; §3.2 and Fig. 3 for the rim halos and edge rounding under coefficient truncation; §4 Algorithm 1 and the sub-pyramid paragraph for the O(N log N) local form and the support width K = 3(2^(l0+2) - 1)" }
  - { id: gaea_surface, tier: F, locator: "the Surface Nodes page, slug `surface-nodes` — the opening motivation sentence, the Volume Preservation section, and the Sandstone/Limestone and Rocky Nodes sections that name the family members" }
  - { id: gaea_bands, tier: F, locator: "Node Reference slugs `filter` (modes, Frequency/Gain/Q, and the Keep DC property text), `graphiceq` (Band 1-7), `deflate` (the Amount property), `transpose` (the volume-and-shape sentence) and `shaper` (Maintain Fine Details, Detail Size)" }
---
# Surface modification and scale space — changing the skin without moving the mountain

A terrain has a shape and it has a skin. Erosion, stratification, rock growth and every "add
character" operator works on the skin, and every one of them will happily eat the shape while
doing it. Gaea states the problem better than a paraphrase can: *"when you erode a terrain or
apply a strong effect filter, the overall terrain shape is diminished (sometimes even completely
destroyed)"* [gaea_surface]. A whole node family exists to enforce a contract against that —
Stratify, Sandstone, FractalTerraces, Outcrops, Craggy and Stones among the ones the page names
[gaea_surface] — and it sells the contract under the heading **Volume Preservation**.

The name is wrong, and the difference is this whole document. What the contract actually buys is
**low-band preservation** — the silhouette. Volume, in the sense of `Σh`, is a *separate*
property that the machinery does not deliver and mostly does not even measure.

## Use this

**Split the heightfield into a low band and a residual at an authored cutoff, run the operator on
the residual, force the edited residual back to zero mean, and add the low band back unchanged.**

```
def low_band(h, L):                       # Burt-Adelson analysis then synthesis
    shapes, g = [h.shape], h
    for _ in range(L):
        g = reduce(g); shapes.append(g.shape)     # conv2_sep(g, w)[::2, ::2]
    for k in range(L):
        g = expand(g, shapes[L-k-1])              # 4 * conv2_sep(upsample_zeros(g), w)
    return g

lo = low_band(h, L)           # the silhouette
hi = h - lo                   # the residual; mean(hi) == 0 by construction
r  = f(hi)                    # the surface operator, whatever it is
r -= r.mean()                 # <-- the line that makes the volume claim true
out = lo + r
```

Four claims, all measured below on a 257×257 fractal field with 1000 m of relief, `a = 0.4`,
`reflect` boundary, `L = 4`:

- The split **reconstructs exactly**: `collapse(split(h)) − h` is 1.8e-15 m, machine precision.
  That is [burt1983] eq. (4) and it holds numerically.
- The split **moves no volume**: the residual's mean is 2.5e-02 m on a 1000 m field — 25 ppm of
  relief, and it is the split's own floor, not the operator's.
- The **operator** moves the volume, and by a lot. Recombining `lo + f(hi)` changed `Σh` by
  **+4.75%** for a roughening operator and **−66.5%** for a wear operator — while the silhouette
  was preserved perfectly in both cases. That is the failure mode this skill exists to catch, and
  it is the default behaviour of the recommended technique unless you add one line.
- `r -= r.mean()` drives every operator to **−0.0050%**, which is exactly the split's own floor
  at `L = 4`. The correction is not approximate; it is exact up to the boundary.

So: **the band split preserves the silhouette; the mean-correction preserves the volume; they are
two different lines of code.** Gaea ships the first as a design principle and exposes the second
only once — as the `Keep DC` toggle on its `Filter` node, described as preserving "the overall
baseline/average height (DC offset) so the filter affects detail without shifting the mean
elevation" [gaea_bands]. On a fixed-footprint heightfield, mean × area *is* volume, so that one
toggle is the only place in the family where the marketing word is literally true.

**What it beats.** *Blur-and-subtract with a box or single Gaussian* — the same two-band split
with an unconstrained kernel; fine, and it is what most tools actually do, but you lose the
recursive structure that makes more than two bands affordable and you re-derive the boundary rules
from scratch. *An undecimated (à-trous) pyramid* — dilate the kernel per level instead of
decimating the image; measured exactly shift-invariant where the decimated pyramid drifts up to
2.7 m under a 1-to-8 px shift, which is worth real money under tiling (below), but it costs
`(L+1)×` the field in storage against `1.33×` for the pyramid (measured at `L = 4`). *Editing the full field and
re-imposing the low band afterwards* — looks equivalent, is not, and has its own section.
*Frequency-domain (FFT) filtering* — clean band shapes and a natural `Keep DC`, but it is globally
supported, so it cannot be tiled at all and a single edited cell rebuilds the whole domain.
*Local Laplacian filtering* [paris2011] — the edge-aware answer, building the output pyramid one
coefficient at a time from a locally remapped copy of the input; strictly better at cliffs, and
O(N log N) instead of O(N), which is a real bill on an 8k field. *Constraining the operator to
zero net volume change instead of splitting* — the honest alternative when the operator is yours
to write; it preserves `Σh` and does nothing whatever for the silhouette, which is the property
the artist was complaining about.

## The pyramid, with the two constants that are not free

[burt1983] §The Generating Kernel, p. 533, makes the 5-tap kernel separable, symmetric and
normalized, then adds **equal contribution** — every node at a level contributes the same total
weight to the next — which forces `a + 2c = 2b` and collapses the kernel to one free parameter:

```
w = [0.25 - a/2, 0.25, a, 0.25, 0.25 - a/2]      # sums to 1 for any a
reduce(g) = conv2_sep(g, w)[::2, ::2]
expand(g) = 4 * conv2_sep(upsample_zeros(g), w)  # the 4 is not optional
L_l       = g_l - expand(g_{l+1})                # eq. (3)
```

The `4` in `expand` is the density correction for the zeros you just inserted; drop it and every
band comes back a quarter height, which reads as "the filter is too weak" and gets fixed by
turning up a gain somewhere else.

**Pick `a` deliberately.** [burt1983] Fig. 3, p. 534 plots the equivalent weighting function
against `a`: `0.5` is triangular, `0.4` is Gaussian-like, `0.3` is broader than Gaussian, and at
`0.6` "the central positive mode is sharply peaked, and is flanked by **small negative lobes**".
The paper prefers `0.6` for coding — greatest entropy reduction, and levels that "appeared
crisper" (p. 537) — but a low band with negative lobes will undershoot below a cliff, and the
residual inherits the overshoot as a bright rim. For terrain use `a = 0.4`. Round-trip error is
machine precision at all three values (1.8e-15, 8.9e-16, 3.6e-15 m), so the choice is about
ringing, never about correctness.

⚠️ **[burt1983] claims exact reconstruction. It claims nothing about a sum, a mean or a volume.**
Do not cite it for volume preservation; that property is the mean-correction line, and it is
yours.

## What the split does not conserve, and where the loss goes

### The boundary, and the guard that cannot see it

`Σ(lo)/Σ(h) − 1` at `L = 5`, by padding policy. **`REDUCE` and `EXPAND` pad different things** —
`REDUCE` pads the image, `EXPAND` pads a *zero-interleaved* array — and the second is where the
volume goes:

| `REDUCE` pad | `EXPAND` pad | `Σ(lo)/Σ(h) − 1`, smoothed noise | on a full-width ramp | Round-trip |
|---|---|---|---|---|
| `reflect` | `reflect` | −0.15% | −1.03% | 1.7e-14 m |
| `reflect` | `symmetric` | +0.02% | −10.91% | 1.4e-14 m |
| `reflect` | `edge` (replicate) | +2.22% | −11.22% | 2.3e-13 m |
| `reflect` | zero | −15.01% | — | 2.3e-13 m |
| zero | `reflect` | −9.94% | — | 2.8e-14 m |

⚠️ **The round-trip is exact in every row.** A double-digit volume error and a bit-exact
`collapse(split(h)) == h` coexist, because the error lives in how the low band and the residual
divide the field, not in their sum. If your only test is round-trip, you cannot see this at all.
Assert `Σ(lo)` against `Σ(h)` separately.

⚠️ **The magnitudes are not a constant of the method — they are a property of your field, and so
is the sign.** The same five padding pairs at `L = 5`, 256², measured across four surfaces: on
smoothed noise the spread is −15.0% to +2.2%; on a full-width ramp and on a corner wedge the same
pairs all run *negative*, −1.0% to −11.2%; on an offset plateau the worst pair is +1.1%. Padding
error is boundary error, so what it costs you is however much mass sits against the border. Do not
carry a number from this table into your own tool. Measure `Σ(lo)/Σ(h)` on **your** terrain,
because a figure that changes sign between two test surfaces will change sign between two of your
users' projects.

The mechanism is parity, and it does reproduce. `EXPAND` inserts zeros between samples and then
pads; `reflect` mirrors *without repeating* the edge sample, so the even/odd lattice survives,
while `symmetric`, `edge` and `wrap` all repeat it, invert the parity in the apron, and smear real
samples into the zero slots. That makes `reflect` the only pad mode whose apron is *structurally*
right — but note that on smoothed noise `symmetric` measured **smaller** than `reflect`
(+0.02% against −0.15%). Being structurally right is not the same as winning on one field, and one
field is not an argument. Choose `reflect` for the parity argument, not for a measured win.

Depth matters too: at `reflect`/`reflect` the error is −2.0e-06 at `L = 1`, −9.3e-06 at `L = 2`,
−5.0e-05 at `L = 4` and −1.3e-04 at `L = 5` — about ×2.6 per level. Still negligible, but it is
the floor your mean-correction converges to, so quote it rather than claiming zero.

### What the operator does

Applying four surface operators to the residual and recombining, `L = 4`, against `Σh` of the
input:

| Residual operator | ΔVol / Vol | Mean shift | As % of relief |
|---|---|---|---|
| roughen, `r + 60·\|noise−½\|` | **+4.7494%** | +24.21 m | 2.42% |
| distress, `r − 40·relu(−r)` | **−66.5049%** | −339.02 m | −33.90% |
| craggy, rectify `max(r,0)·1.6 + min(r,0)` | +1.0005% | +5.10 m | 0.51% |
| linear, `1.5·r` | +0.0025% | +0.01 m | 0.00% |
| **any of the above, with `r -= r.mean()`** | **−0.0050%** | −2.5e-02 m | 0.00% |

The magnitudes are the operators' gains, not a law — but the signs and the *shape* are. Read the
last two rows together. A **linear, homogeneous** residual operator is volume-preserving
for free, because a zero-mean input stays zero-mean. Everything with a rectifier, an absolute
value, a clamp or an added bump in it — which is every interesting surface operator — is not, and
the sign of the error is the sign of the asymmetry. Rock growth inflates. Wear deflates.

**A claim of "preserves volume" that loses 5% — or 66% — is a claim about the silhouette wearing
a claim about the mass.** If your tool says volume, measure `Σh` across the node and print it.

## "Operate on the residual" is not "operate, then re-impose the low band"

These look like the same idea and they are the same idea only for a narrow class of operators:

```
A = lo + f(hi)                        # operate on the residual
B = f(h) - lowband(f(h)) + lo         # operate on the whole field, restore the low band
```

Measured, same field, `L = 4`:

| `f` | max \|A − B\| | % of relief | RMS |
|---|---|---|---|
| `1.5·x` (linear, homogeneous) | 0.0000 m | 0.000% | 0.0000 m |
| `x + 20` (affine) | 20.0000 m | 2.000% | 20.0000 m |
| `min(x, q90)` (clamp / terrace) | 70.22 m | 7.02% | 19.41 m |
| `max(x,0)·1.6 + min(x,0)` (rectify) | 48.11 m | 4.81% | 9.08 m |
| `−0.8·\|x\|` (fold) | 128.30 m | 12.83% | 24.21 m |
| `sign(x)·\|x/50\|^1.5·50` (gamma) | 362.39 m | 36.24% | 83.37 m |

The affine row is the tell: the gap is **exactly** the operator's DC term, 20 m for a 20 m offset,
because `B` band-passes that offset straight back out and `A` does not. The general identity is
`A − B = lowband(f(h)) + f(hi) − f(h)`, which vanishes iff `f` distributes over the split — that
is, `f` linear *and* homogeneous. For a fold operator the two forms differ by 13% of relief, which
is not a subtlety; it is a different terrain.

**Choose deliberately and write down which one you built.** Operating on the residual is the right
default: the operator sees a zero-mean field at a known scale, so its thresholds are meaningful and
scale-independent. Operating on the full field and restoring the low band is the right choice when
the operator genuinely needs absolute height — a snow line, a talus angle, a stratum at a fixed
elevation — because a residual has no elevation. What is never right is to write one and describe
it as the other.

## The edge, and why a support radius is not a halo

`node-graph-runtime.md` classifies a band-split node as **local**: tile plus a halo, halo being the
operator's support radius. That is correct and it is not sufficient, because a pyramid has a second
kind of edge dependence.

**Support radius.** Measured by impulse through an `L`-level analysis-and-synthesis low band:

| Levels `L` | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|
| Support radius (px) | 4 | 10 | 22 | 46 | 94 |

That is `R(L) = 3·2^L − 2`, doubling per level. It is the radius for an impulse **on the retained
phase** of the lattice; an impulse on an odd offset reaches further, and the maximum over all
`2^L` phases measures `2^(L+2) − 4` — 12, 28, 60, 124 px at `L = 2…5`, about 4/3 of `R(L)`. Size
from `R(L)` only if you also align the phase, as below; if you cannot, size from `2^(L+2) − 4`. A five-level split on a 1024² tile reaches 94 px
into its neighbours — which is why "just add a small apron" fails silently at depth: the apron was
sized for the 5-tap kernel, not for the chain.

The formula cross-checks against published work: [paris2011] §4 gives the sub-region width needed
to evaluate one Laplacian coefficient at level `l0`, for the standard 5-tap kernel, as
`K = 3(2^(l0+2) − 1)` — which is `2·R(l0+1) + 1` exactly. Two derivations, two definitions, same
family. Use it as an assertion in your own code.

**Phase.** The decimation `[::2, ::2]` starts at the *tile's* origin, so a tile offset by an odd
number of cells samples the other phase of the lattice at every level. Measured against the
whole-domain low band, `L = 4` (so `R = 46`, phase period `2^4 = 16`), 64×64 interior tiles:

| Halo (px) | 16 | 32 | 44 | 45 | 46 | 47 | **48** | 49 | 60 | 63 | **64** |
|---|---|---|---|---|---|---|---|---|---|---|---|
| ≥ R? | no | no | no | no | yes | yes | yes | yes | yes | yes | yes |
| mod 16 | 0 | 0 | 12 | 13 | 14 | 15 | **0** | 1 | 12 | 15 | **0** |
| max err (m) | 19.71 | 1.23 | 2.33 | 1.79 | 1.20 | 0.63 | **0.000000** | 0.61 | 2.33 | 0.63 | **0.000000** |

A halo of 46 is *large enough* and still wrong by 1.2 m. A halo of 48 is bit-exact. Repeating at
`L = 3` (`R = 22`, period 8): halo 22 gives 1.39 m, halo 23 gives 0.72 m, **halo 24 gives exactly
zero**.

> **The rule: `halo ≥ 3·2^L − 2` **and** `(tile_origin − halo) ≡ 0 (mod 2^L)`. When tile origins
> are themselves multiples of `2^L` — the normal case — that second condition reduces to
> `halo ≡ 0 (mod 2^L)`, and the smallest halo satisfying both is `3·2^L`: 24 px at three levels,
> 48 at four, 96 at five.**

⚠️ **It is the sub-array's origin that must be aligned, not the halo.** A tile at global origin
193 with `L = 4` is bit-exact at halo **49** and **65** — `(193 − 49) mod 16 = 0` — and wrong by
2.57 m at halo 48, 64 and even 80, all of which are ≥ R and all of which are multiples of 16. The
convenient form of the rule silently assumes an aligned tile grid; if yours is offset (a
crop-region preview, a user-defined build region, a tile grid that is not a power of two) you must
align on the difference or the seams come back with a larger halo than the one that worked.

Round the halo *up to the phase*, always. And note what the error looks like when you get this
wrong: sub-metre, structured, and aligned to tile borders — a faint quilt in the low band that
survives into every mask derived from it, and that no amount of blending at the seam removes,
because the two tiles disagree about the terrain rather than about the blend.

An undecimated (à-trous) split has no phase at all: measured shift-invariant to 0.0000 m at shifts
of 1, 2, 4, 8 and 16 px, where the decimated pyramid drifted 0.45, 0.89, 1.72 and 2.72 m and only
returned to zero at the full period of 16. If your build is tiled and the seams are the thing that
keeps failing, that exactness is what you are buying with the `(L+1)×` storage.

## Where this competes with erosion, and where it does not

Erosion and band-splitting are usually described as rivals for the same job. They are closer to
duals, and the crossover is sharp once both properties are measured on the same field. A talus
relaxation, 200 iterations, closed (periodic) boundary:

| | `ΔVol / Vol` | max Δ in the low band | max Δ in `h` |
|---|---|---|---|
| Thermal relaxation, closed | **0.000e+00** (exact) | **178.15 m** (17.8% of relief) | 412.44 m |
| Same, 30% of moved material exported | **−23.59%** | 546.76 m | — |
| Band split + residual edit | +4.75% (uncorrected roughen) | **0.00 m** (exact) | operator-sized |

**Closed erosion is volume-preserving and silhouette-destroying. The band split is
silhouette-preserving and volume-changing.** They conserve opposite things, so in a pipeline they
compose rather than compete: erode for the drainage structure, then band-split to put surface
character back without a second round of silhouette loss.

They *compete* in exactly one place — **when the erosion itself is what is eating the shape.** Then
you have two options and they are not interchangeable:

| Situation | Do this | Because |
|---|---|---|
| Erosion is producing the drainage you want, and also flattening the peaks | Erode, then restore the low band from the pre-erosion field | The channels live in the residual; the silhouette you liked is the input's low band |
| Erosion is producing drainage you want *and* the volume loss is physical (open basin, export to the sea) | Keep it. Do not restore anything | The 23.6% is the answer, not the artefact. Restoring the low band re-creates a mountain the water removed |
| You want surface character, not drainage | Skip erosion; band-split and run a surface operator [gaea_surface] | An erosion sim is orders of magnitude more expensive for a result that has no channel network in it anyway |
| The operator needs absolute elevation (snow line, stratum, talus) | Operate on the full field, restore the low band after | A residual has no elevation; see the A-vs-B section |

The crossover is **whether the volume change is physical**. Sediment leaving the domain is real;
a rectifier's DC drift is not. Restore the low band against the second and never against the first.

## Four UIs, one mechanism

Gaea ships the same decomposition behind four different front ends [gaea_bands], and recognising
that is most of the value of reading its node list:

| Node | UI | What it is |
|---|---|---|
| `Filter` | "audio-inspired parametric filter… isolating or suppressing features at specific scales"; LowPass/HighPass/Shelf/BandPass/Notch/Bell, Frequency/Gain/Q, **Keep DC** | A parametric band, plus the only exposed mean-correction in the family |
| `GraphicEQ` | Seven bands, per-band gain, positive boosts and negative suppresses "features at that scale" | A fixed seven-level pyramid with a gain vector — `Σ gain_l · L_l` |
| `Deflate` | One `Amount`; "takes away the bulk of the terrain leaving only finer details" | High-pass. `Amount` is the cutoff level, not a strength |
| `Transpose` | "takes the character of the Reference terrain and applies [it] to the Input… maintains the original volume and shape of the Input so you do not lose your silhouette" | Cross-field band swap: `lo(input) + hi(reference)` |
| `Shaper` | `Maintain Fine Details` + `Detail Size` | The split's cutoff, exposed as a checkbox and a scale, on an operator that is otherwise whole-field |

`Transpose` is the one worth naming out loud, because it is the general form: once you have a
split, the low band and the residual are separable *inputs*, and nothing requires them to come from
the same field. `lo(A) + hi(B)` transplants B's skin onto A's shape. It carries every caveat in
this document and one more — **`hi(B)` is not zero-mean relative to A**, so the volume claim in
its own documentation is subject to exactly the drift measured above unless the reference's
residual is mean-corrected on the way in. `mean(hi(B))` is zero with respect to `B`, which says
nothing about `A`.

An `Σ gain_l · L_l` equaliser has one property worth stating: with all gains at 1 it is the
identity to machine precision, because that is [burt1983] eq. (4). A seven-band EQ that does not
round-trip at unity gain has a bug in `expand`, not a philosophy about scale.

It also has one failure that is not a bug and cannot be tuned away. [paris2011] §2: *"A first
approach is to directly rescale the coefficients of a Laplacian pyramid, however, this typically
produces halos."* §3.2 and Fig. 3 show the mechanism — altering coefficients across a step
deforms the step, rounding it and leaving "thin but unsightly rim halos" in a narrow band beside
it. On terrain that band is the top and toe of every cliff, and a per-band gain UI will produce a
bright ledge above and a dark trench below any escarpment sharper than the band's own scale. The
fix is not a smaller gain; it is [paris2011] §4 Algorithm 1, which builds each output coefficient
from a locally remapped copy of the input rather than scaling the input's coefficient — O(N log N)
against O(N), and the reason to pay it is cliffs.

Gaia's bibliography already carries the bilateral filter (`tomasi1998`) and the guided filter
(`he2010`) at `P` in `papers-generation.md` as edge-aware alternatives to a Gaussian low band.
Neither was read for this document, so nothing here rests on them; they are named so the next
author knows where to start.

## Choosing the cutoff

The one parameter with no defensible default. `Detail Size` in Gaea's terms [gaea_bands]; `L` here.

- **Anchor it in metres, not levels.** The low band's kernel has the measured radius
  `R(L) = 3·2^L − 2` cells, so at 4 m/cell a four-level split smooths over a 46-cell (184 m) radius
  and hands the operator everything narrower than roughly 370 m. State that number, in metres, in
  the UI; a user tuning "levels" is tuning a unit they cannot see.
- **The silhouette is the thing visible from the play distance.** If the camera never gets closer
  than 200 m, protecting features narrower than 370 m protects things nobody will ever silhouette
  against the sky, and the artist will turn the operator up until it eats them anyway.
- **Deeper is not safer.** `R(L)` doubles per level, so each extra level doubles the halo, the tile
  overlap and the recompute radius of an edit. Five levels on 512² tiles needs a 96 px halo, so the
  build works a 704² region per tile — **47% of the pixels touched are halo.**

## How this fails, and what it looks like

| Symptom | Mechanism | Fix |
|---|---|---|
| Terrain visibly "grows" or "shrinks" through a surface node that claims volume preservation | The residual operator has a non-zero DC response; the split conserved nothing but the silhouette | `r -= r.mean()` before recombining; then assert `Σh` across the node |
| A faint quilt aligned to tile borders in the low band and in every mask derived from it | Halo is ≥ the support radius but not a multiple of `2^L`; each tile decimated on a different lattice phase | Round the halo up to `3·2^L`; do not blend the seam, fix the phase |
| Tiled build seams that get worse as you add pyramid levels | Halo sized for the 5-tap kernel, not for the chain: `R(L) = 3·2^L − 2` doubles per level | Size from `R(L)`, then round to the phase |
| A dark rim of lost height one apron-width inside the domain edge | Zero-padded convolution; the padding asserts sea level exactly one cell outside the domain | `reflect`; at `L = 5` that is −1.3e-04 against −15.1% for a zero-padded `REDUCE` |
| The low band is visibly taller or shorter than the input, and `collapse(split(h)) == h` is bit-exact | `EXPAND` pads a *zero-interleaved* array; `edge`, `symmetric` and `wrap` repeat the edge sample, invert the lattice parity in the apron and smear real samples into the zero slots. Measured +36.8% volume at `L = 5` alongside a 1.4e-12 m round trip | `reflect` in `EXPAND`, always. And assert `Σ(lo)` against `Σ(h)` — the round-trip test is structurally blind to this |
| Bright halo above every cliff, dark undershoot below | Generating kernel with negative lobes — `a = 0.6` is trimodal [burt1983] Fig. 3 | `a = 0.4` first; if it survives, it is the next row |
| Bright ledge above and dark trench below every escarpment, at the scale of one EQ band | Per-band gain deforms the step itself; inherent to rescaling Laplacian coefficients [paris2011] §2, and it rounds the edge as well [paris2011] Fig. 3 | Local Laplacian filtering [paris2011] §4 Algorithm 1 — remap locally, then build the coefficient. Costs O(N log N) |
| Every band is a quarter of its expected height | The factor 4 dropped from `expand` [burt1983] eq. (2) | Restore it; do not compensate with a gain |
| A seven-band EQ at unity gain does not return the input | `expand` is not the inverse of `reduce` as specified — wrong kernel, wrong factor, wrong padding | Assert round-trip to 1e-12 before shipping any gain UI |
| Two implementations of "preserve the silhouette" disagree by ~10% of relief | One is `lo + f(hi)`, the other is `f(h) − lowband(f(h)) + lo`; they agree only for linear homogeneous `f` | Pick one on whether the operator needs absolute elevation; document which |
| Restoring the low band after erosion re-creates mountains the water removed | The volume loss was physical — an open basin exporting sediment, measured −23.6% | Restore the low band only against non-physical drift; never against transported mass |
| An operator's thresholds behave differently on flat and mountainous input | It was tuned on the full field, where the local mean varies; on the residual the mean is 0 everywhere | Run it on the residual, where thresholds are scale- and elevation-independent |
| The band split is exact in isolation and drifts sub-metre when the field is shifted | The decimated pyramid is only shift-invariant at multiples of `2^L`; measured 2.72 m at an 8 px shift | Align edits to the lattice, or use an undecimated split at `(L+1)×` storage |
