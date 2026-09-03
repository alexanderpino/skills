---
type: Bibliography
title: Papers — wave 1 additions
description: "Sources added in wave 1 of the generation axis: multi-band scale-space decomposition and volume-preserving surface modification."
tags: [bibliography, provenance, generation]
status: draft
generated: { by: process:claude-code, at: 2026-09-03T00:00:00Z }
---
# Papers — wave 1 additions

A holding file for sources added in wave 1, to be merged into `papers-generation.md`. The
**provenance tier table and the two rules that bind every entry** live in `papers-flow.md` —
never upgrade a tier to satisfy a question, and a constant reconstructed from memory is a `?`
wearing a P's confidence. Entry format is the family's:

```
- **id** `T` — Author (Year). *Title.* Venue. — note
```

## Scale-space decomposition

- **burt1983** `P` — Burt, P.J. & Adelson, E.H. (1983). *The Laplacian Pyramid as a Compact
  Image Code.* IEEE Transactions on Communications COM-31(4), 532–540. — The Gaussian/Laplacian
  pyramid. Read for this document. **§The Generating Kernel, p. 533** gives the separable,
  normalized, symmetric 5-tap kernel and the *equal contribution* constraint `a + 2c = 2b`,
  which fixes `ŵ(0)=a, ŵ(±1)=1/4, ŵ(±2)=1/4 − a/2` — one free parameter, not five.
  **Fig. 3, p. 534**: `a=0.5` is triangular, `a=0.4` Gaussian-like, `a=0.3` broader, and at
  `a=0.6` "the central positive mode is sharply peaked, and is flanked by small negative lobes"
  — the "Gaussian" pyramid is not non-negative at the value the paper itself later prefers
  (p. 537, greatest entropy reduction). **Eq. (3), p. 535** defines the band as
  `L_l = g_l − EXPAND(g_{l+1})`, **eq. (4)** gives exact reconstruction by summing expanded
  levels, and the same page describes the Laplacian levels as "a set of bandpass filtered copies
  of the image". ⚠️ The paper claims **exact reconstruction**; it makes no claim about preserving
  a sum, a mean or a volume, and it must not be cited for one.

- **paris2011** `P` — Paris, S., Hasinoff, S.W. & Kautz, J. (2011). *Local Laplacian Filters:
  Edge-aware Image Processing with a Laplacian Pyramid.* ACM TOG 30(4) (SIGGRAPH 2011), 68:1–68:12.
  — Read for this document. **§2, "Pyramid-based Edge-aware Filtering"** states the failure mode of
  a per-band gain UI in one sentence: "A first approach is to directly rescale the coefficients of a
  Laplacian pyramid, however, this typically produces halos." **§3.2 and Fig. 3** show it — clipping
  large coefficients leaves the signal "somewhat deformed near edges… manifested in images as thin
  but unsightly rim halos", and the caption adds that truncation "smooths the edge". **§4,
  Algorithm 1** is the O(N log N) fix: build the output pyramid coefficient by coefficient from a
  point-wise remapped copy of the input, then collapse. The same section gives the support width of
  one Laplacian coefficient for the standard 5-tap kernel, **K = 3(2^(l0+2) − 1)** — which is
  exactly `2·R(l0+1) + 1` for the halo radius `R(L) = 3·2^L − 2` measured independently in
  `surface-and-scale-space.md`.

## Tool practice — the surface-modification contract

No canonical paper covers how an authoring tool separates silhouette from surface; these are
vendors documenting their own products, cited for **what a shipping tool chose**, which is
evidence about practice and never about correctness.

- **gaea_surface** `F` — QuadSpinner. *Gaea 2 Documentation*, Using Gaea → "Surface Nodes"
  (slug `surface-nodes`). https://docs.gaea.app/ — the site is JS-rendered; the full corpus is
  published as plain text at https://docs.gaea.app/llms-full.txt. — States the motivation
  verbatim: "when you erode a terrain or apply a strong effect filter, the overall terrain shape
  is diminished (sometimes even completely destroyed)", and the contract under the heading
  **Volume Preservation**: the tools "separate the process of designing the overall terrain shape
  (or volume) and designing the superficial shapes on the surface", so the user can "modify the
  surface without altering the overall shape, volume, or silhouette".
- **gaea_bands** `F` — QuadSpinner. *Gaea 2 Documentation*, Node Reference, slugs `filter`,
  `graphiceq`, `deflate`, `transpose` and `shaper` (same llms-full.txt corpus). — Four UIs over
  one mechanism. `filter` is "an audio-inspired parametric filter … useful for isolating or
  suppressing features at specific scales", with LowPass/HighPass/LowShelf/HighShelf/BandPass/
  Notch/Bell modes, Frequency/Gain/Q, and a **Keep DC** toggle that "preserves the overall
  baseline/average height (DC offset) so the filter affects detail without shifting the mean
  elevation". `graphiceq` is seven fixed bands with per-band gain, positive boosting and negative
  suppressing "features at that scale". `deflate` "takes away the bulk of the terrain leaving only
  finer details". `transpose` "takes the character of the Reference terrain and applies [it] to the
  Input terrain… maintains the original volume and shape of the Input terrain so you do not lose
  your silhouette". `shaper` exposes the split's cutoff directly as **Maintain Fine Details**
  ("finer detail is preserved regardless of shape changes") plus **Detail Size** ("the scale of
  details to be preserved or affected during shaping").
