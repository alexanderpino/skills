# s21-hero-reach — does the recent physics reach the pixels?

**Ruling 18, answered in integers off rendered buffers.** Every number here is scene-linear and taken BEFORE the tone map. Each row is ONE branch switched off against the all-on baseline, on the SAME bed, from the SAME camera axis, at 360 x 480 — so the row measures the branch and nothing else. Produced by `gauntlet/sea/scout/s21-hero.py`; no physics was changed and `terrain-renderer/reference-impl/` was not modified.

The three framings: **J** and **K** are the bar's own (`beach_camera.J_CONTENT` / `K_CONTENT`, built by `beach_render.hero_cameras`). **F** is `beach_render.main()`'s backlit-face frame, included as a CONTROL rather than as a hero: it looks seaward over open water, contains neither partition breakpoint and carries almost no foam, so a feature that lives in the surf zone must read ~0 there. Standing ruling 14 — a near-zero measurement is worthless until zero has been shown to be reachable — and `DECK_UNION` reaches it: **3 pixels**.

## The ladder

| branch | frame | px changed | share of frame | share of water | max ΔL | px changed in 8-bit |
|---|---|---:|---:|---:|---:|---:|
| `spectral_on` | J | 27 076 | 15.67 % | 94.30 % | 196.7 | 19 995 |
| `spectral_on` | K | 33 213 | 19.22 % | 94.86 % | 178.7 | 28 534 |
| `spectral_on` | F | 110 478 | 63.93 % | 96.50 % | 3.385 | 109 104 |
| `subgrid_on` | J | 25 993 | 15.04 % | 91.29 % | 184.2 | 15 662 |
| `subgrid_on` | K | 33 002 | 19.10 % | 94.30 % | 160.1 | 23 810 |
| `subgrid_on` | F | 114 323 | 66.16 % | 99.86 % | 0.7851 | 109 520 |
| `foam_realise` | J | 28 113 | 16.27 % | 98.74 % | 53.13 | 13 026 |
| `foam_realise` | K | 34 642 | 20.05 % | 98.99 % | 59.32 | 21 318 |
| `foam_realise` | F | 114 480 | 66.25 % | 100.00 % | 3.335 | 72 434 |
| `foam_population` | J | 19 226 | 11.13 % | 67.52 % | 90.71 | 11 639 |
| `foam_population` | K | 26 012 | 15.05 % | 74.33 % | 92.98 | 19 011 |
| `foam_population` | F | 14 143 | 8.18 % | 12.35 % | 3.384 | 10 795 |
| `DECK_UNION` | J | 7 788 | 4.51 % | 27.35 % | 35.63 | 1 673 |
| `DECK_UNION` | K | 14 329 | 8.29 % | 40.94 % | 22.41 | 1 500 |
| `DECK_UNION` | F | 3 | 0.00 % | 0.00 % | 0.5282 | 3 |

## What each branch is

- **`spectral_on`** — wave 19 -- the transported bundle: the first-order surface becomes a 256-component realisation instead of one carrier phase
- **`subgrid_on`** — wave 18 -- `SlopeRealisation`: the sub-footprint wind sea is DRAWN and subtracted from the Cox & Munk density instead of left in it
- **`foam_realise`** — wave 18 -- `coverage_field`: the foam is a Boolean realisation instead of its own expectation
- **`foam_population`** — wave 19 -- `breaking_indicator` on the drawn envelope, rescaled by `rayleigh_exceedance`: WHICH waves broke, not E[breaking]
- **`DECK_UNION`** — wave 19 -- the foam deck is the union over the two offshore partitions instead of the carrier's alone; this is the second breaker bar

## The verdict, feature by feature

**All five reach pixels in both bar framings.** The smallest is the second breaker bar, and it is the only one whose reach depends on the framing: **8.29 %** of frame K, **4.51 %** of frame J, **0.00 %** of frame F. That ordering is the bed's and not the renderer's — the two partitions break at x = 598 m and x = 676 m on the centre row, frame K's row reaches x = 704 m and contains both, frame J's row reaches only x = 626 m and contains the outer line alone, and frame F looks the other way and reaches neither.

**But the argument that activates it is passed by nothing that draws a picture.** `grep -rn "run_bay(" *.py` finds one caller in the whole repository that passes `climate=`: `validate_beach.py:12254`, inside the suite. Not `beach_render.main`, not `main_wave8/9/10/12`, not any of the seven `*_evidence.py` drivers. The union deck therefore had never reached a rendered frame before this round — which is ruling 18's exact shape with the guard, rather than the module, as the sole caller.

**And `beach_render.py` still does not import `beach_diffract`.** Ruling 18's third case is unchanged at wave 20: zero pixels of any of these three frames carry a diffracted edge.

## Per-frame reach, off the 720 x 960 hero buffers

| | frame J | frame K |
|---|---:|---:|
| water pixels | 454 150 | 559 887 |
| wave population changes the covering measure at | 391 663 px (86.24 % of water) | 521 565 px (93.16 % of water) |
| ...of which move drawn coverage by > 0.02 | 258 353 | 337 182 |
| `SlopeRealisation` writes a non-zero slope at | 454 150 px (16.43 % of frame) | 559 887 px (20.25 % of frame) |
| ...rms of the drawn slope magnitude | 0.1070 | 0.1116 |
| `coverage_field` foam visible at this footprint | 99.81 % | 99.78 % |
| foam deck > 0.25 | 328 652 | 405 374 |
| pixels differing from the BEFORE frame, scene-linear | 130 470 (18.88 %) | 152 733 (22.10 %) |
| ...by more than 8 levels through the shared 8-bit encode | 9.74 % | 16.09 % |
| high-frequency sd, after (17 px box, scene-linear) | 6.84/6.12/4.63 | 4.92/4.40/3.33 |
| high-frequency sd, before | 1.68/1.48/1.08 | 1.41/1.25/0.92 |

Render times, on an otherwise idle 4-core box with nothing else of this project running (100 % of one core throughout — ruling 13 stays withdrawn): frame J after **1518 s**, before **347 s**; frame K after **1679 s**, before **338 s**. The ladder cost 549 s for J, 549 s for K and 1370 s for F.

