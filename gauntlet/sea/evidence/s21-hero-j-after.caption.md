# s21-hero-j-after

Bar frame J -- the embayment overview. `beach_camera.J_CONTENT`: headland to headland with the backing cliff, the horizon in the upper third, the lens inferred from the standoff-over-chord ratio and the eye standing on the bay's own rim. Built by `beach_render.hero_cameras`, unmoved since wave 7.

**AFTER.** Everything the recent waves added is ON. `run_bay(embay=True, climate=beach.CLIMATE_SCENE)` -- the embayed plan-form (wave 9, off by default) and the two-partition offshore climate (wave 19, off by default, and **no render entry point in the repository passes it**). `Water` then builds, at its own defaults: `spectral_on=True` (wave 19's transported bundle, 256 components), `subgrid_on=True` (wave 18's `SlopeRealisation`), `foam_realise=True` (wave 18's Boolean foam), `foam_population=True` (wave 19's per-wave breaking realisation), `DECK_UNION=True` (wave 19's union deck over the two partitions).

**Provenance: measured (`M`).** Rendered by
`gauntlet/sea/scout/s21-hero.py`, captioned by
`gauntlet/sea/scout/s21-captions.py`. The driver imports `beach_render` and
moves only flags that file already carries as control panels; **no physics was
changed and `terrain-renderer/reference-impl/` was not modified.** 720 x 960 output pixels, box-averaged **in scene-linear**
from a 1440 x 1920 buffer, then a single exposure key (`beach_render.WHITE`
= 3.4826) and gamma 2.2. **Both frames of the pair use the identical
camera object and the identical exposure key**, so a difference in the PNG is
a difference in the scene and not in the mapping. Every quantity below is read
from the scene-linear buffer BEFORE the tone map, except where it says 8-bit,
which is stated because a visual comparison goes through the encode.

**No text is burned into the frame.**

## What is in the frame, in integers

| | pixels | share of frame |
|---|---:|---:|
| water | 454 150 | 16.43 % |
| land | 1 422 170 | 51.44 % |
| sky | 888 480 | 32.14 % |
| **frame** | **2 764 800** | |

Foam deck above 0.25: **328 652 px** (11.89 % of frame). Drawn coverage above 0.5: **93 244 px** (3.37 %).

## Does each recent feature reach these pixels?

Ruling 18, as integers off this frame's own rendered buffer.

- **Wave 19, the wave population** (`breaking_indicator` on the drawn envelope, rescaled by `rayleigh_exceedance`): **RAN**. It changes the covering measure at **391 663 px**, 14.17 % of frame and 86.24 % of the water, between x = 55 and 626 m; **258 353 px** (9.344 % of frame) move by more than 0.02 in drawn coverage. Mean chi 0.5369, mean p 0.5412; the cap touches 0.21 % of the break measure.
- **Wave 18, the sub-footprint slope realisation** (`beach_optics.SlopeRealisation`): **RAN**. It writes a non-zero slope at **454 150 px**, 16.43 % of frame -- every water pixel -- with rms |grad| 0.1070 and 99th percentile 0.2569; **437 488 px** (15.82 % of frame) carry more than 0.01 of drawn slope.
- **Wave 18, the Boolean foam realisation** (`beach_foam.coverage_field`): **RAN**. Drawn mean 0.20741 against field mean 0.20823, 99.81 % of the frame's foam visible at this footprint, p_max 0.7768.
- **Wave 19, the second breaker bar**: the two offshore partitions break at x = 598 m and x = 676 m on the centre row (x increases SHOREWARD, so the larger x is the inner line). In a +-15 m window round each, on this frame: x = 598 m -> 168 773 px in frame, 168 347 of them with deck > 0.25; x = 676 m -> 0 px in frame, 0 of them with deck > 0.25.
- Glitter, scene-linear: mean 12.1918, 99.9th percentile 252.06, **116 548 px** above the exposure key.

## The pair, measured

Scene-linear, max over the three channels: **130 470 of 691 200 pixels (18.88 %)** differ at all; rms difference 7.3572, max 209.6165 (the exposure key is 3.4826).

Through the same 8-bit encode both PNGs went through -- stated because this is the visual comparison and not a physical one: **14.03 % of pixels change by at least one level**, **9.74 % by more than eight**, mean change 4.14 levels, max 188.

Frame statistics, scene-linear: mean radiance 2.7291 after against 2.4616 before; high-frequency sd (17 px box, `hf_sd`) 6.8450/6.1183/4.6289 after against 1.6769/1.4783/1.0833 before.

## One branch at a time, at 360 x 480 on the same camera axis

The pair above moves the bed AND five flags at once. This ladder moves one branch at a time against the all-on baseline, on the same bed, so each row answers ruling 18 for one feature. Scene-linear; the 8-bit column is the same encode the PNGs use.

| branch removed | px changed | share of frame | share of water | max dL | px changed in 8-bit | where (x) |
|---|---:|---:|---:|---:|---:|---|
| `spectral_on=False` (wave 19 bundle) | 27 076 | 15.67 % | 94.30 % | 196.7 | 19 995 | -43-626 m |
| `subgrid_on=False` (wave 18 glitter) | 25 993 | 15.04 % | 91.29 % | 184.2 | 15 662 | -19726-626 m |
| `foam_population=False` (wave 19 population) | 19 226 | 11.13 % | 67.52 % | 90.71 | 11 639 | 74-626 m |
| `foam_realise=False` (wave 18 foam) | 28 113 | 16.27 % | 98.74 % | 53.13 | 13 026 | -3652-626 m |
| `DECK_UNION=False` (wave 19 second bar) | 7 788 | 4.51 % | 27.35 % | 35.63 | 1 673 | 567-621 m |

Render time 1518 s on an otherwise idle 4-core box (100 % of one core; nothing else of this project was running).
