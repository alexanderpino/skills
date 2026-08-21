# s18-land-patch

**The 3/10 rectangle, at 1:1, on three frames.** Rows 620–720, cols 60–360 —
wave 11's own patch — shown at **300 × 100 pixels each, no resampling**, under
**one exposure key** (`WHITE = 3.4826`) so a difference in the image is a
difference in the radiance. **No text is burned into the figure.** Panels top to
bottom, separated by a plain white rule:

1. **un-terraced bed, its own camera** — `run_bay(embay=True)`. The bed wave 11
   scored **3/10**, and the reference this round is measured against.
2. **terraced bed, the legacy brow search** — `run_bay(embay=True, stands=4)`
   through the camera the project shipped at wave 17. This is
   `s18-land-hero-before`'s near ground.
3. **terraced bed, the repaired brow search** — the same bed, the same shading
   code, the same constants. This is `s18-land-hero-after`'s.

**READ THE FIGURE BEFORE THE TABLE, because the figure is the harder result.**
All three panels look like flat green. Panel 2 is *literally* one 8-bit triple
in all 30 000 of its pixels; panels 1 and 3 are not, but at 1:1 and at this size
a human eye cannot tell them apart from panel 2. That is the honest state of the
coastal plain and it is what the owner was looking at when he said the frame
does not look like water.

So this figure documents **texture ABSENT in all three cases**. The ×164 in the
table below is a real recovery of a real collapse — 1 distinct level to 14 is
the difference between a painted surface and a lit one — and it is **not** a
texture, and this round does not claim it is. What the repair actually buys is
visible in `s18-land-hero-after` and not here: the sea, the surf lines, the
beach and the wet-sand edge come back into frame. The plain stays flat.

## The numbers, scene-linear and un-quantised

The estimator is `beach_render.hf_sd`: the buffer minus its own 17-px box mean,
standard deviation per channel, taken on the **radiance before the tone map**.
The 8-bit column is display-referred and is here only to say plainly whether the
patch is a surface or a colour.

| panel | hf sd, **scene-linear** | distinct 8-bit levels |
|---|---|---|
| 1. un-terraced (the 3/10 bed) | `5.558e-04 / 6.349e-04 / 3.519e-04` | 9 / 8 / 8 |
| 2. terraced, legacy brow | `4.841e-06 / 4.866e-06 / 2.608e-06` | **1 / 1 / 1** |
| 3. terraced, repaired brow | `7.958e-04 / 7.768e-04 / 4.495e-04` | 14 / 11 / 10 |

- **3 against 2 — what the camera repair recovers: ×164 / ×160 / ×172.**
- **3 against 1 — against the frame that scored 3/10: ×1.43 / ×1.22 / ×1.28**,
  with the display-level count going 9 / 8 / 8 → 14 / 11 / 10.

All three rows come from **one estimator in one run** (`beach_render.hf_sd`,
`beach_view_evidence.py`). That matters more than usual here — see below.

## Two things that did NOT reproduce, and why the estimator is now in code

**Wave 11's `0.00092` is mostly the quantiser.** It was measured on the 8-bit
display frame; wave 16 found the same statistic on the same patch un-quantised
reads `7.1e-05`, twelve times smaller. That result stands and is why every
figure above is scene-linear.

**Wave 16's own scene-linear column does not reproduce.** Re-rendered here on
the same beds through the same cameras — panel 1's camera lands at
`x = 648.0 m, ground 15.715 m, eye 17.315 m`, matching wave 16's stated
`x = 648 m, eye 17.31 m` — the *display-level* counts come back **exactly**
(9 / 8 / 8 and 1 / 1 / 1, both channels-for-channel), so the frames are the
same frames. The scene-linear standard deviations do not:

| | wave 16 published | measured here | ratio |
|---|---|---|---|
| un-terraced | `2.752e-04 / 3.292e-04 / 1.400e-04` | `5.558e-04 / 6.349e-04 / 3.519e-04` | 2.02 / 1.93 / 2.51 |
| terraced, legacy brow | `1.706e-06 / 1.700e-06 / 8.105e-07` | `4.841e-06 / 4.866e-06 / 2.608e-06` | 2.84 / 2.86 / 3.22 |

The two ratios are not the same number, so it is not a scale factor — the two
estimators differ in shape (a box width, a padding rule, or a masked subset).
**Wave 16 shipped no script**, and its caption reconstructs the estimator in
prose, so there is nothing to diff against. This round therefore puts the
estimator in `beach_render.hf_sd` and the rectangle in
`beach_render.PLATEAU_PATCH`, where a later wave can read them instead of
re-deriving them for the fifth time.

**Nothing in this round's verdict depends on the discrepancy**, because every
comparison above is made against this round's own panels with this round's own
estimator. Wave 16's *conclusion* — that the terrace built real relief and the
camera then stood on it — reproduces completely: 1 / 1 / 1 display levels, a
frame 1.6 % water, and a patch two orders of magnitude flatter than either
alternative.

## What is actually varying in panel 3

Measured, not asserted — the patch re-rendered with every driver field read out
beside it:

| driver | mean | range |
|---|---|---|
| ground height `h` | 13.44 m | **0.643 m** (panel 2: **0.0047 m**) |
| `N · sun` | 0.571 | 0.186 (panel 2: ~0) |
| slope-clause `rock` mask | 0.0061 | 0.290 |
| `cover` | **1.000000** | **0** |
| `bare` — sub-grid rock pockets | **0** | **0** |

The variance is **the bed's own normal and the slope-classified material edge at
the cliff brow**, both computed from `w.h`, which is the output of
`beach.coastal_step` run over the sea-level history. **No new material, texture,
constant or noise field was added by this round** — the whole renderer diff is
four deleted lines in `beach_render.viewpoint` plus a measuring instrument.

And the two zero rows are the limit. `cover` saturates at exactly 1.000000
because 300 kyr of denudation puts 9 m of regolith over a 0.25 m rock roughness,
so `rock_bare_mask` — the only sub-grid process in the material path — returns
identically zero on this ground. **A soil-mantled tread has no sub-grid surface
process in this project**, and that is recorded in
`terrain-architect/references/12-glacial-coastal.md` rather than filled in with
a texture.

## The residual, stated

**Closed by derivation:** the whole of the ×164 collapse, and the frame's
composition — water back to 16.2% from 1.6%, land down to 51.6% from 66.4%.
Both follow from two clauses of a landform search, with no new constant.

**Not closed, and visible in the figure above:** the coastal plain is still a
flat green plane. It is roughly a quarter of `s18-land-hero-after`, it reads as
one colour at 1:1, and ×1.2–1.4 over the bed that scored 3/10 is not the order
of magnitude that would change that. The reason it cannot go further from this
lane is measured —
**97–99% of land pixels in this frame sample the bed below half a grid cell**,
so no field computed on the 2 m grid can vary across the near ground at all.
Against the 3/10 bed the gain is ×1.2–1.4 in the statistic and 9 / 8 / 8 →
14 / 11 / 10 in display levels: real, measured, and **not** the order of
magnitude a photograph would need.

*Provenance: measured. `terrain-renderer/reference-impl/beach_view_evidence.py`
regenerates this figure and both hero frames. Guarded by `_sec_view` in
`validate_beach.py`, whose floor row sits between a measured value 4–9x over
it and a legacy camera 225–510x under it.*
