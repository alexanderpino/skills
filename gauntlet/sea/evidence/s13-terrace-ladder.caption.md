# s13-terrace-ladder — the plateau is an output of a sea-level history

Wave 12 measured the coastal plateau at 45.4% of the hero frame and called it
*"one declared albedo on a declared ramp that no process in this file has ever
run on"*. Wave 13 replaced the ramp with chapter 12's own sea-level-history
loop. **Nobody has looked at the result until now.**

## Why the elevation distribution is the figure

The ladder is a statement about **where land elevation piles up**. The treads
this loop cuts slope at 1:919 and 1:1274 — a shaded relief of them shows
nothing at all, and a hillshade would be an honest picture of an invisible
thing. In the histogram a tread is a spike and a riser is the empty ground
between spikes, which is the whole ladder in one panel.

**The control is the same coast with `stands=None`** — the declared ramp waves
1–12 carried, drawn as the grey line. One field changed. Its distribution is
featureless by construction, and that contrast is the evidence.

## Measured, on `run_coast(stands=5)`, dx = 4 m

| rung | measured level | width | rows | closed form `terrace_ladder()` |
|---|---|---|---|---|
| oldest / highest | — *(off the domain)* | — | — | 46.189 m |
| | **30.063 m** | 47.1 m | 26 of 89 | 30.189 m |
| | **13.959 m** | 304.7 m | **89 of 89** | 13.189 / 14.189 m |
| present bench | **−1.904 m** | 290.1 m | 89 of 89 | −1.811 m |
| | −3.571 m | 56.0 m | 89 of 89 | — |

The main tread spans **x = 636–956 m** on the mid-domain row and its level
varies alongshore with a standard deviation of **0.0401 m** over all 89 rows —
lower-right panel. The two closed-form rungs at 13.189 and 14.189 m are the
`-5.0` and `+6.0` eustatic stands, whose uplift-corrected levels straddle the
one tread the domain resolves; the loop plans them into a single bench, which
is why one measured level answers to two rungs.

**The round trip is the lower-left panel**: the closed form is
`uplift × age + the stand's own eustatic level`, and the measured treads come
back off the *built surface* by a slope threshold that knows nothing about it.

## The re-measurement this figure was asked for, and the answer is: NOT CLOSED

Wave 11's critic scored the plateau **3/10** on a high-frequency standard
deviation of **0.00092 / 0.00091 / 0.00081 of 255** on rows 620–720, cols
60–360 of the hero frame, and wave 12 re-measured it **unmoved**. Wave 13
changed the bed underneath it and never re-measured.

**It is still not re-measured in the frame, and this round did not reach it.**
What this round can say, from the surface itself rather than from a render:

- the terrace is **correct in the elevation distribution** — three rungs, a
  round trip against the closed form, an alongshore level sd of 4 cm;
- the tread's own high-frequency relief, alongshore-detrended over 17 cells,
  is **1.52 m** — which sounds large and is not a texture: it is dominated by
  the tread's *edges* and by the 30 m riser inside the sampled band, not by
  relief on the tread;
- the tread interior remains a plane at 1:1274 carrying **one declared albedo**.

So on the evidence here the honest verdict is the one the round was told to
watch for: **the physics gap is closed and the visual gap is not.** A terrace
that is right in the histogram and still one flat albedo in the frame has moved
the process and not the pixels. The frame measurement that would settle it
needs a hero render on the terraced bed and is named, unreached, in the wave
record.

*Provenance: **measured**, scene-linear SI. Drawn by
`beach_evidence.fig_terrace_ladder` from `beach.run_coast(stands=5)` and
`beach.run_coast()`; levels by `beach.terrace_levels`, closed form by
`beach.terrace_ladder`. No render is involved and nothing is read off a PNG.
`?` carried by the input: `UPLIFT_RATE = 1.0e-4 m/yr`, `HIGHSTAND_DURATION =
1.0e4 yr` and the five eustatic highstands `(8, 2, -5, 6, 0) m`.*
