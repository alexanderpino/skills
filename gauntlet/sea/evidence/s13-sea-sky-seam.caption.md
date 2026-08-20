# s13-sea-sky-seam — the sun through zero metres of water

**Top: waves 1–12. Bottom: wave 13.** A 1:1 crop across the horizon of bar
frame K — 720 × 180 render samples per half, one sample per image pixel, no
downsample and no resize, cut from a 720 × 960 buffer whose horizon row is 289.
**No text is burned into the frame**; both halves are tone-mapped through the
same exposure and the same gamma, so a difference in the image is a difference
in the radiance.

## The defect

`through_face` initialised `g_prev` to zero, which asserts that the traced entry
point lies exactly on the free surface. On the first march step the crossing
refinement then evaluated

```
frac = g_prev / (g_prev - g) = 0 / (0 - g) = 0
```

so a ray reported as having exited carried a chord of **exactly zero**.
`exp(-(a + b_b) · 0)` is 1, and the term returned the full solar beam
undiminished — *the sun through no water at all* — added on top of terms 1–3.

**It fired where the trace is ill-conditioned, which is the horizon.** The
water intersection is four Newton steps on `z(t) = η`, whose update divides by
the ray's z-component; at a fraction of a degree below horizontal that component
is ~6e-4, the step is kilometres, and the traced point lands metres *above* the
surface. That is the hard bright band along the top half's waterline, and it is
brightest exactly where the sea should be handing off to the sky.

## Measured, scene-linear, before the tone map

`horizon_seam` compares the two rows below the horizon against the two above,
on the frame columns furthest from the sun's azimuth — **33.9° off-axis**, so
this is the seam and not the glitter.

| | R | G | B | worst |
|---|---|---|---|---|
| sky (rows 286–288) | 1.0974 | 1.2276 | 1.4602 | — |
| **sea, waves 1–12** | 1.2767 | 1.3745 | 1.5396 | |
| ratio sea/sky | **1.1634** | 1.1196 | 1.0543 | **+16.3%** |
| **sea, wave 13** | 1.1306 | 1.2520 | 1.4581 | |
| ratio sea/sky | **1.0302** | 1.0198 | 0.9985 | **+3.0%** |

Bar K2 makes this a criterion: *"the sea's radiance at grazing must approach the
sky's reflected value CONTINUOUSLY, and any seam there is a tell visible at a
glance."* At grazing the Fresnel reflectance goes to 1, so a sea just below the
horizon is a mirror of the sky just above it and the ratio must go to 1.

Wave 13 reported **+19.8% → −2.0%** on its own run. This figure measures
**+16.3% → +3.0%** at 720 × 960 and **+28.1% → +3.1%** at 360 × 480. The
residual and its sign depend on how finely the grazing rows are sampled, which
is what a resolution sweep of an ill-conditioned trace should do; the finding —
a double-counted sun at the horizon, worth one to three tenths of the sky's own
radiance — is the same at every resolution tried.

## The two invariants, which are statements and not epsilons

1. **A ray whose entry point is above the surface never entered the water.**
   `g_prev` is now the real `η − z` at the entry point: zero if the tracer is
   exact, and the truth if it is not.
2. **A path of no length carries no transport.** With no water crossed there is
   nothing to see through, and what the eye receives along that ray is the
   surface — which terms 1–3 already carry in full. Including it double-counts
   the sun. `chord > 0` is the exact statement that the ray was inside the
   medium for a finite length, not a tuned threshold.

Neither is a constant and neither was chosen to make the picture right. Both
restate what `through_face`'s and `shade_water`'s own docstrings already
promised — *"the chord is where it exits"*, *"it is zero when the chord is
zero"* — and which the code did the opposite of.

*Provenance: **measured**, scene-linear, before the tone map; `horizon_seam`
reads the radiance buffer and nothing is read back off a PNG. Both halves are
**one code path and one bed**, rendered back to back in one process by
`beach_render.seam_figure`, with `through_face` swapped for
`_through_face_wave12` between them — a faithful copy of the current function
with exactly two lines changed back. The fix is commit `4e448e6`. **This defect
has no suite row**; `validate_beach.py` contains no reference to `through_face`
or `horizon_seam`, and that gap is recorded in the wave record.*
