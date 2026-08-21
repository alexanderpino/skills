# s18-land-hero-before

**The frame the project shipped at wave 17, and the largest thing in it is not
water.** Bar J's hero frame on the terraced bed (`run_bay(embay=True,
stands=4)`), 720 × 960, SS = 2, exposure key `WHITE = 3.4826` — the same key as
`s18-land-hero-after`, so a difference between the two images is a difference in
the radiance and not in the grade. **No text is burned into the figure.**

This is **not an archived PNG**. It is re-rendered from the current tree by
`beach_view_evidence.py`, which carries the wave-7..17 brow search as
`brow_legacy` for exactly this purpose: the before-frame has to come from the
same code as the after-frame or the comparison is between two eras rather than
between two searches.

## Where the camera is, and why it is there

**x = 1000 m, ground 30.08 m, eye 31.68 m.** x = 1000 m is the **landward
boundary of the domain** — the last cell there is. The camera is standing on
the oldest terrace tread with its back to the wall of the world, and the ground
2–3 m in front of it fills the bottom of the frame.

It was put there by `beach_render.viewpoint`, whose docstring calls itself *"the
seaward-most standing point at the top of the cliff face"*. Two clauses in it
fail on a terraced bed, and both fail *because* the terrace exists:

1. **The threshold was `3 × median(land slope)`.** A tread is flat and large:
   here it is 63 % of the land, and the median land slope falls from **0.0800**
   (which is `beach.S_PLAIN`, the plain's declared gradient) to **0.0007**. The
   threshold falls with it to 0.0021, and the tread's own microrelief —
   **0.0019 to 0.0027**, the relief the terrace was built to produce — clears
   it. The search fires two cells in from the boundary.
2. **It stopped at the first break in slope walking seaward.** A terrace flight
   has a riser per rung by construction. This profile carries a riser at
   x = 934–954 m and the sea cliff at x = 632–644 m, with 286 m of tread
   between them.

## What the frame contains

| | this frame | after the repair | wave 15, un-terraced |
|---|---|---|---|
| water | **1.6 %** | 16.2 % | 16.8 % |
| land | **66.4 %** | 51.6 % | 51.1 % |

## The patch

Rows 620–720, cols 60–360, **scene-linear and un-quantised**:

`4.841e-06 / 4.866e-06 / 2.608e-06` — and **one distinct 8-bit value across all
30 000 pixels, in every channel.** 115–135× flatter than the un-terraced bed
wave 11 scored 3/10 on, and 160–172× flatter than the same bed seen from the
repaired brow. (Wave 16 published `1.706e-06` for this panel from an estimator
it did not commit; the display-level count `1 / 1 / 1` reproduces exactly and
the sd does not. `s18-land-patch` carries both columns and the reason.)

**The relief is not missing.** Held at a fixed camera, the terrace raises the
same statistic from `2.75e-04` to `1.59e-03`, a factor of 5–9 (wave 16,
`s16-plateau-patch`). The relief is real, it is an output of the sea-level
history, and this camera is standing on it — at 2–3 m range on a 2 m grid, so
the whole patch is the interior of a single bilinear cell and is a plane by
construction.

*Provenance: measured. `terrain-renderer/reference-impl/beach_view_evidence.py`.
Statistic: `beach_render.hf_sd` over `beach_render.PLATEAU_PATCH`, on the
scene-linear buffer before the tone map.*
