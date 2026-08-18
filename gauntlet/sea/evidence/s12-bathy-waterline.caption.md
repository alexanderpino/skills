# s12-bathy-waterline — the beach face across the waterline, 1:1

**One render sample per image pixel.** 320 x 200, cut straight out of the
supersampled buffer of `s12-bathy-frame` (rows 660–860, cols 1120–1440 of the
1440 x 1920 render) with no downsample and no resize, so an edge that is here
is visible and an edge that is not cannot be smoothed into existence.

Sea top-left, then the swash sheet, then the damp band, then dry sand. **Two
boundaries, and the wave-10 frame had neither.**

## The measurement, on the exact 48 px wave 11's critic measured

Column 620 of the delivered 720 x 960 frame, rows 370 to 418 — the critic's own
patch, on which the verdict was *"a smooth ramp with no edge anywhere across
48 px of beach"*:

| | largest one-row step, green | the pair, 8-bit |
|---|---|---|
| **s10 (what the critic judged)** | **4 / 255** — a monotone ramp 165 → 168 | seaward `194,182,169` **brighter** than landward `183,169,148` |
| **s12 (this frame)** | **36 / 255**, at rows 404 → 406 | damp `153,138,116` **darker** than dry `189,174,150` |

Scene-linear, over the whole frame's sand: damp `[1.1417 0.9144 0.6251]`
against dry `[1.9551 1.6191 1.1557]`, **ratio 0.584 / 0.565 / 0.541**. Bar H3's
direction — *"wet sand darkens"* — in the TOTAL and not only in the diffuse
half, which is what waves 8–11 could report and could not draw.

## Where the edge comes from

`optics.wet_albedo` is unchanged and was never the defect. Two things were:

1. **The Rayleigh scale was Hunt's R itself.** `runup_hunt` marks the
   coefficient `?` — *"depends on which run-up level (mean, 2%, maximum)"*.
   Read as the rms the instantaneous damp limit lands at 1.433 m on a beach
   whose own closed forms top out at 1.029 m, so this coast could carry no dry
   sand at any instant. Read as R_2% it lands at 0.725 m, just under the berm.
   The `?` is closed by consequence, not by a citation.
2. **A distribution is not a surface.** The shader blended by the share of
   swash cycles reaching a level. That is the beach's time-average. It now
   draws a sample of it, and the alongshore cusping in this crop is the
   realisation's own — correlation length = the swash excursion
   `sqrt(H_0 L_0) = 13.77 m`, which the file already owned.

And the specular lobe moved off the damp band onto the swash sheet: pore water
darkens, free water reflects, and they are not the same mask. That is what
inverted the rung.

*Provenance: `beach_render.waterline_crop`, one code path with the hero frame.
The `?` this adds is `SWASH_TAU_DRY = 300 s`, bracketed 60–1800 s, which moves
the damp limit by 1.56x against the 1.98x error it removes.*
