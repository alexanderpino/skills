# s16-plateau-patch

**The measurement that was owed and had been deferred twice.** Wave 11's critic
scored the coastal plateau **3/10** on the high-frequency standard deviation of
rows 620–720, cols 60–360 of the hero frame — **0.00092 / 0.00091 / 0.00081 of
255**. Wave 12 re-measured it *unmoved*. Wave 13 changed the bed underneath it
into an emerged marine terrace and **never re-measured**. Wave 15 said so and
did not reach it either. This is it, and the answer is not the one the terrace
was built to give.

Three panels, top to bottom, 1:1 (no resampling), the same 300 × 100 pixels of
each frame, tone-mapped through the **same** exposure key so a difference in
the image is a difference in the radiance. **No text is burned into the
figure.**

1. **un-terraced bed, wave-12 camera** — `run_bay(embay=True)`, the bed and the
   frame the 3/10 was scored on.
2. **terraced bed, the same camera** — `run_bay(embay=True, stands=4)`, rendered
   through the *un-terraced* bed's own camera object. One thing changed: the
   bed.
3. **terraced bed, its own inferred camera** — the camera re-inferred from the
   terraced landform, which is what ships.

## The estimator, and how it was recovered

The record does not carry wave 11's filter, so it was reconstructed by
calibration: on the un-terraced buffer, **the standard deviation of the 8-bit
display frame minus its own 17-px box mean, as a fraction of 255**, gives
`0.000901 / 0.000880 / 0.000779` against the published `0.00092 / 0.00091 /
0.00081` — **within 2–4 % in every channel, with the channel ordering
reproduced**. Box 19 brackets it from the other side (+1.6 to +3.6 %). That
estimator is then run unchanged on all three buffers.

Nothing here is read off a PNG. The 8-bit frame is formed in memory from the
scene-linear buffer by the renderer's own `_save` curve, so the historical
number can be reproduced without breaking the ruling.

## The numbers

Scene-linear first, because that is the quantity; the 8-bit column exists only
to connect to the published figure.

| | hf sd, **scene-linear** | robust (1.4826 · MAD) | hf sd, 8-bit **/255** | distinct 8-bit levels |
|---|---|---|---|---|
| **1. un-terraced, wave-12 camera** | `2.752e-04 / 3.292e-04 / 1.400e-04` | `2.20e-05 / 1.91e-05 / 1.02e-05` | **0.000901 / 0.000880 / 0.000779** | 9 / 8 / 8 |
| **2. terraced, same camera** (plateau px only) | `1.592e-03 / 1.599e-03 / 1.221e-03` | `1.05e-04 / 1.04e-04 / 4.92e-05` | 0.001160 / 0.001178 / 0.001156 | 30 / 34 / 30 |
| **3. terraced, its own camera** | `1.706e-06 / 1.700e-06 / 8.105e-07` | `1.71e-07 / 1.67e-07 / 6.58e-08` | **0.000000 / 0.000000 / 0.000000** | **1 / 1 / 1** |

Panel 2 is quoted over the 98.91 % of the patch the renderer's own plateau
criterion accepts; over all pixels its scene-linear sd is `9.79e-03 / 8.24e-03 /
6.76e-03`, carried by a small bright tail on ground 29 m away where the tread
runs over its own lip. The robust column is there so that the tail cannot be
what the verdict rests on — it does not change the direction of either
comparison.

## The verdict, and it is two things at once

**Held at the same camera, the terrace works.** Panel 2 against panel 1 is a
factor of **5.8 / 4.9 / 8.7** in scene-linear high-frequency content, **4.8 /
5.5 / 4.8** on the robust statistic, and the 8-bit frame goes from **8–9
distinct levels to 30–34**. The relief is an output of the sea-level history
and it is real.

**The camera is not held, and cannot be.** The frame is an *inference from the
landform* — `beach_camera` stands the eye on the highest ground the bed
supplies — and the terrace moves that ground: the wave-12 camera stood at
**x = 648 m, eye 17.31 m** on a cliff brow, and the terraced bed's own camera
stands at **x = 1000 m, eye 31.68 m** on the oldest tread at the domain's
landward edge. From there the near field is that tread, at **2–3 m range**, and
it is **one RGB value across all 30 000 pixels of the patch**: high-frequency sd
exactly zero on the 8-bit frame, `1.7e-06` scene-linear, **161–194× flatter
than the bed the 3/10 was scored on**. See `s16-terrace-frame`, which is 66.4 %
land against 51.1 % before and **1.6 % water against 16.9 %**.

So, plainly: **the terrace closed the physics and left the picture flat.** It
did not merely fail to help — at the camera its own landform implies, it made
the frame flatter and emptier than the one that scored 3/10. The gap is not
"the plateau has no relief"; the relief is there and measurable. The gap is that
the relief is a *plane at 1:1274 with one declared albedo*, and a camera
standing on it sees a plane whatever the elevation histogram says.

## One thing the reconstruction found on the way

The published `0.00092` is **mostly the quantiser**. The same 17-px estimator
run on the un-quantised display image of the same patch gives `7.1e-05 / 8.3e-05
/ 4.8e-05` — **twelve times smaller**. On a patch spanning 8 grey levels, the
statistic a critic scored 3/10 on was dominated by the 8-bit display of a
surface that was already flat, not by anything in the surface. It is the exact
failure the "measure scene-linear, never read a PNG" ruling exists to prevent,
and it is recorded here rather than used to argue the score away — the
scene-linear numbers above tell the same story and are the ones the verdict
rests on.

*Provenance: `beach.run_bay(embay=True[, stands=4])`, `beach_render.render` at
720 × 960 with SS = 2, camera `J`, one exposure key (`WHITE = 3.4826`) for all
three panels. Measured on the radiance buffer before the tone map.*
