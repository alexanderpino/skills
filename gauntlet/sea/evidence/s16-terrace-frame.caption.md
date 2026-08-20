# s16-terrace-frame

**The frame the terraced bed actually implies, and it is the round's worst
result.** Bar section J's viewpoint re-inferred on `run_bay(embay=True,
stands=4)` — the same lens, the same sun, the same exposure and the same
inference procedure as `s12-bathy-frame`, with the sea-level history switched
on underneath. Upright 720 × 960 at SS = 2, 106.18° tall × 89.91° wide (an
iPhone 16 Pro 0.5x held portrait). **No text is burned into the frame.**

| | un-terraced (`s12-bathy-frame`) | **terraced (this frame)** |
|---|---|---|
| eye | 17.31 m at x = 648 m | **31.68 m at x = 1000 m** |
| ground under the eye | 15.71 m (cliff brow) | **30.08 m (the oldest tread)** |
| azimuth / depression | 312.46° / 25.44° | 312.46° / **25.49°** |
| sky | 32.1 % | 32.1 % |
| **water** | 16.8 % | **1.6 %** |
| **land** | 51.1 % | **66.4 %** |
| plateau patch, distinct 8-bit levels | 9 / 8 / 8 | **1 / 1 / 1** |

## Read this before reading the frame

`beach_camera` stands the eye on the **highest ground the bed supplies**, and
that is not a composition choice — it is bar J's own constraint ("the whole
embayment from its own rim"). On the un-terraced bed the highest ground is a
17 m cliff brow 352 m from the landward boundary. On the terraced bed the
oldest tread of the flight stands at **30.19 m** (closed form) and reaches the
landward edge of the domain, so the inference walks the camera onto it — and
from a plane at 1:1274, three centimetres of relief per metre travelled, the
frame is a plane.

**Two thirds of these pixels are the tread, and the 300 × 100 patch that samples
it is a single RGB triple.** The sea has been reduced from a sixth of the frame
to a sixtieth. This is the terrace succeeding at its physics — the flight is
real, its rungs land on the closed form, the guard rows in
`validate_beach._sec_terrace` say so at 29 rows — and destroying the picture at
the same time.

## Why it is kept rather than reframed

Because moving the camera back to wave 12's position is a *choice*, and the
project's own ruling is that the framing is the landform's. `s16-terrace-fixedcam`
holds the wave-12 camera on this same bed, which is the controlled comparison
and the one the plateau numbers are taken at; this frame is what the inference
returns when it is allowed to run. Both are published because the honest
statement needs both: **at a fixed camera the terrace multiplies the plateau's
high-frequency content by about five; at the camera it implies, it removes it
entirely.**

The remedy is not another placement. It is that 66 % of the frame is one
declared albedo `[0.17 0.19 0.12]` on a plane — the same gap 2 that
`beach_render.plain_relief` has been naming since wave 8, now larger rather than
smaller. See `s16-plateau-patch` for the numbers and the estimator.

*Provenance: one code path. `beach.run_bay(embay=True, stands=4)` →
`beach_render.Water` → `hero_cameras` → `render`, exposure key WHITE = 3.4826.
All shares measured on the scene-linear buffer before the tone map.*
