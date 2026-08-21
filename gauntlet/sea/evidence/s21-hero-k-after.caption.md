# s21-hero-k-after

Bar frame K -- open water and the glitter path. `beach_camera.K_CONTENT`: the same cliff, aimed straight down the sun's azimuth so the path runs from the horizon into the near field. Built by `beach_render.hero_cameras`, unmoved since wave 7.

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
| water | 559 887 | 20.25 % |
| land | 1 369 713 | 49.54 % |
| sky | 835 200 | 30.21 % |
| **frame** | **2 764 800** | |

Foam deck above 0.25: **405 374 px** (14.66 % of frame). Drawn coverage above 0.5: **133 844 px** (4.84 %).

## Does each recent feature reach these pixels?

Ruling 18, as integers off this frame's own rendered buffer.

- **Wave 19, the wave population** (`breaking_indicator` on the drawn envelope, rescaled by `rayleigh_exceedance`): **RAN**. It changes the covering measure at **521 565 px**, 18.86 % of frame and 93.16 % of the water, between x = 55 and 704 m; **337 182 px** (12.196 % of frame) move by more than 0.02 in drawn coverage. Mean chi 0.5983, mean p 0.5253; the cap touches 0.64 % of the break measure.
- **Wave 18, the sub-footprint slope realisation** (`beach_optics.SlopeRealisation`): **RAN**. It writes a non-zero slope at **559 887 px**, 20.25 % of frame -- every water pixel -- with rms |grad| 0.1116 and 99th percentile 0.2637; **543 111 px** (19.64 % of frame) carry more than 0.01 of drawn slope.
- **Wave 18, the Boolean foam realisation** (`beach_foam.coverage_field`): **RAN**. Drawn mean 0.23972 against field mean 0.24016, 99.78 % of the frame's foam visible at this footprint, p_max 0.7695.
- **Wave 19, the second breaker bar**: the two offshore partitions break at x = 598 m and x = 676 m on the centre row (x increases SHOREWARD, so the larger x is the inner line). In a +-15 m window round each, on this frame: x = 598 m -> 32 149 px in frame, 13 856 of them with deck > 0.25; x = 676 m -> 161 632 px in frame, 161 632 of them with deck > 0.25.
- Glitter, scene-linear: mean 4.8976, 99.9th percentile 232.73, **57 543 px** above the exposure key.

## The pair, measured

Scene-linear, max over the three channels: **152 733 of 691 200 pixels (22.10 %)** differ at all; rms difference 5.2180, max 229.9115 (the exposure key is 3.4826).

Through the same 8-bit encode both PNGs went through -- stated because this is the visual comparison and not a physical one: **19.92 % of pixels change by at least one level**, **16.09 % by more than eight**, mean change 7.39 levels, max 182.

Frame statistics, scene-linear: mean radiance 1.8532 after against 1.8506 before; high-frequency sd (17 px box, `hf_sd`) 4.9241/4.4002/3.3285 after against 1.4089/1.2454/0.9206 before.

## One branch at a time, at 360 x 480 on the same camera axis

The pair above moves the bed AND five flags at once. This ladder moves one branch at a time against the all-on baseline, on the same bed, so each row answers ruling 18 for one feature. Scene-linear; the 8-bit column is the same encode the PNGs use.

| branch removed | px changed | share of frame | share of water | max dL | px changed in 8-bit | where (x) |
|---|---:|---:|---:|---:|---:|---|
| `spectral_on=False` (wave 19 bundle) | 33 213 | 19.22 % | 94.86 % | 178.7 | 28 534 | -10-704 m |
| `subgrid_on=False` (wave 18 glitter) | 33 002 | 19.10 % | 94.30 % | 160.1 | 23 810 | -7664-704 m |
| `foam_population=False` (wave 19 population) | 26 012 | 15.05 % | 74.33 % | 92.98 | 19 011 | 62-704 m |
| `foam_realise=False` (wave 18 foam) | 34 642 | 20.05 % | 98.99 % | 59.32 | 21 318 | -6417-704 m |
| `DECK_UNION=False` (wave 19 second bar) | 14 329 | 8.29 % | 40.94 % | 22.41 | 1 500 | 597-704 m |

Render time 1679 s on an otherwise idle 4-core box (100 % of one core; nothing else of this project was running).
