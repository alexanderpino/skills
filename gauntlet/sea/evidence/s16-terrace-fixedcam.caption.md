# s16-terrace-fixedcam

**The controlled frame: the terraced bed through the un-terraced bed's own
camera.** One thing differs from `s12-bathy-frame` — `stands=4` in the coastal
loop. Same camera object, same position, same azimuth, same depression, same
lens, same sun, same exposure key. **No text is burned into the frame.**

| | `s12-bathy-frame` (un-terraced) | this frame (terraced) |
|---|---|---|
| eye | 17.31 m at x = 648 m, y = −672 m | identical |
| azimuth / depression | 312.46° / 25.44° | identical |
| sky / water / land | 32.1 / 16.8 / 51.1 % | **32.1 / 16.9 / 50.9 %** |
| ground under the eye | 15.71 m | **13.89 m** (the merged tread) |
| plateau patch, hf sd scene-linear | `2.75e-04 / 3.29e-04 / 1.40e-04` | **`1.59e-03 / 1.60e-03 / 1.22e-03`** |
| plateau patch, distinct 8-bit levels | 9 / 8 / 8 | **30 / 34 / 30** |

The frame shares are unchanged to a fifth of a per cent, which is what makes
this a measurement: the composition is held and the bed is the variable.

## What it shows

The ground the camera stands on is no longer `initial_coast`'s declared 1:12.5
ramp. It is the **merged tread** — the scene's rungs 2 and 3 are 1.0 m apart,
below the merge threshold the instrument measures at 4–5 m, so the younger stand
re-planed the older into one bench at 13.86–14.05 m (closed-form bracket
[13.189, 14.189]; `validate_beach._sec_terrace` carries that row). The eye is
therefore **3.4 m above its own ground** rather than 1.6 m, the tread runs away
to the old cliff line, and the near field carries a grazing gradient the flat
ramp did not.

That gradient is the whole of the improvement, and it is worth stating as such:
**a factor of 5–9 in high-frequency content and 8–9 → 30–34 distinct display
levels, on ground that is still a plane with one albedo.** It is more relief
than there was; it is not texture, and nothing on the tread reads as a surface.

## The confound this frame exists to expose, and the one it cannot remove

Holding the camera holds the *pixels* but not the *standing height*: the terrace
raises the ground under the eye from 15.71 m to 13.89 m — the eye is 1.60 m
above the brow on the old bed and 3.42 m above the tread here — so part of the
near-field difference is a grazing geometry, not a material. There is no
placement that holds both, because the terrace **is** a change to the ground the
camera stands on. Both ends are published: this frame holds the camera,
`s16-terrace-frame` holds the inference, and the two disagree in direction.
The verdict in `s16-plateau-patch` is written on both.

*Provenance: `beach.run_bay(embay=True, stands=4)` rendered through the camera
built from `beach.run_bay(embay=True)`, in one process so the two cameras cannot
differ by a rebuild. 720 × 960 at SS = 2, WHITE = 3.4826, measured scene-linear.*
