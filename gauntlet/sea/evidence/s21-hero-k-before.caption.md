# s21-hero-k-before

Bar frame K -- open water and the glitter path. `beach_camera.K_CONTENT`: the same cliff, aimed straight down the sun's azimuth so the path runs from the horizon into the near field. Built by `beach_render.hero_cameras`, unmoved since wave 7.

**BEFORE.** The recent work is OFF -- the waves 5-18 surface. Same camera, same exposure, same sun, same instant. `run_bay(embay=True)` with `climate=None`, so one offshore partition and one bar; then `spectral_on=False` (one carrier phase, one height per cell), `subgrid_on=False` (Cox & Munk's full density, no drawn sub-footprint slope), `foam_realise=False` (the foam is alpha-blended by `coverage(m) = 1 - exp(-m)`, the EXPECTATION), `foam_population=False` (no per-wave breaking indicator -- it cannot run anyway without a bundle to take an envelope of).

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
| water | 575 043 | 20.80 % |
| land | 1 354 557 | 48.99 % |
| sky | 835 200 | 30.21 % |
| **frame** | **2 764 800** | |

Foam deck above 0.25: **433 862 px** (15.69 % of frame). Drawn coverage above 0.5: **40 506 px** (1.47 %).

## Does each recent feature reach these pixels?

Ruling 18, as integers off this frame's own rendered buffer.

- **Wave 19, the wave population**: **did not run** (`m_pop` is None -- there is no bundle to take an envelope of).
- **Wave 18, the sub-footprint slope realisation**: **did not run** (`subgrid_on=False`; every pixel is shaded with the ensemble mean of the whole slope distribution).
- **Wave 18, the Boolean foam realisation**: **did not run** -- the frame draws `coverage(m)`, the expectation.
- **Wave 19, the second breaker bar**: the two offshore partitions break at x = 598 m and x = 676 m on the centre row (x increases SHOREWARD, so the larger x is the inner line). In a +-15 m window round each, on this frame: x = 598 m -> 28 862 px in frame, 25 982 of them with deck > 0.25; x = 676 m -> 154 166 px in frame, 154 166 of them with deck > 0.25.
- Glitter, scene-linear: mean 4.7513, 99.9th percentile 165.74, **98 714 px** above the exposure key.

## The pair, measured

Scene-linear, max over the three channels: **152 733 of 691 200 pixels (22.10 %)** differ at all; rms difference 5.2180, max 229.9115 (the exposure key is 3.4826).

Through the same 8-bit encode both PNGs went through -- stated because this is the visual comparison and not a physical one: **19.92 % of pixels change by at least one level**, **16.09 % by more than eight**, mean change 7.39 levels, max 182.

Frame statistics, scene-linear: mean radiance 1.8532 after against 1.8506 before; high-frequency sd (17 px box, `hf_sd`) 4.9241/4.4002/3.3285 after against 1.4089/1.2454/0.9206 before.

Render time 338 s on an otherwise idle 4-core box (100 % of one core; nothing else of this project was running).
