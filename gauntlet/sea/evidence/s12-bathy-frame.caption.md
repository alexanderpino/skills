# s12-bathy-frame

Bar section J, the embayment overview. Same bed, same camera, same lens and
same sun as `s10-bathy-frame`: upright 720 x 960, 106.18° tall x 89.91° wide (an
iPhone 16 Pro 0.5x held portrait), eye 17.31 m on this bed's own cliff brow at
x = 648 m, y = -672 m, azimuth 312.46°, depressed 25.44°. Nothing about the
framing moved this wave. **No text is burned into the frame.**

Scene-linear, measured on the buffer before the tone map:

| | |
|---|---|
| frame | 32.1% sky, 16.8% water, 51.1% land, 7.4% of pixels clip the derived white point |
| land | 45.4% coastal plain, 3.8% beach sand, 1.9% rock (of the whole frame) |
| bar J's five-rung ladder | 5 of 5 rungs present: deep 2.47%, teal 0.05%, surf 12.70%, wet sand 3.51%, dry sand 0.26% |
| **wet/dry pair, TOTAL** | damp `[1.1417 0.9144 0.6251]`, dry `[1.9551 1.6191 1.1557]`, **ratio 0.584 / 0.565 / 0.541** |
| the same pair at wave 10 | ratio **1.558 / 1.604 / 1.628** — wet *brighter*, bar H3 backwards |

## What changed in this frame, and what did not

**Changed.** The wet/dry boundary. It is no longer a blend by the share of
swash cycles that reach a level — that is the *time-average* of the beach and
an average has no edge — but a realisation of it: `beach.damp_limit`, the
maximum of the last `tau_dry/T = 33` Rayleigh run-ups, sharp in elevation and
cusped alongshore at the swash excursion. And the specular lobe moved off the
damp band onto the swash sheet, because damp sand is not a mirror.

**Not changed, and it is the largest thing in frame.** The coastal plain is
45.4% of these pixels and is still one declared albedo `[0.17 0.19 0.12]` with
a normal whose tilt spread across the whole frame is 3.72°. Its
high-frequency standard deviation on the patch wave 11's critic measured
(rows 620–720, cols 60–360) is **0.00092 / 0.00091 / 0.00081 of 255, against
0.00092 / 0.00095 / 0.00081 at wave 10** — unmoved, and this lane says so
rather than claiming it. See `gauntlet/sea/workbench.md`: the plateau's relief
is a missing *process* (a marine terrace cut at a former stand, chapter 12's
own sea-level-history loop), not a missing constant, and the arithmetic for
why no plausible weathering coefficient reaches it is in
`beach_render.plain_relief`.

**Not changed, and not this lane's.** The surf's blown white band and the
sea's resolved striping.

## The illuminant is the wrong half of the sky, and it is out of this lane

Drawn under 21.02° elevation at azimuth 273.75° — a west sun straight out to
sea on a west-facing coast — against bar J's own timed class at 56.22° /
123.13°, which is front-lit and eclipse-clean. That is why the swash sheet
glints toward the camera here. `atmosphere.py` is shared with the pool and
standing ruling 6 binds it; moving the sun is a wave of its own.

*Provenance: one code path, `beach_render.main_wave12()`. Frame to match: bar
section J. No placeholder is claimed absent — the coastal plain is one, it is
45.4% of the frame, and it is named here.*
