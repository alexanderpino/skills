# s18-land-hero-after

**The same bed, the same shading code, the same constants — one landform search
repaired.** Bar J's hero frame on the terraced bed (`run_bay(embay=True,
stands=4)`), 720 × 960, SS = 2, exposure key `WHITE = 3.4826`, the same key as
`s18-land-hero-before`. **No text is burned into the figure.**

The camera stands at **x = 646 m, ground 13.76 m, eye 15.36 m** — the brow of
the present sea cliff. Its pair, `s18-land-hero-before`, stands at **x = 1000 m,
ground 30.08 m, eye 31.68 m**, which is the landward boundary of the domain,
on the oldest terrace tread.

## What is different, and what is not

**Nothing in the material path changed.** The whole renderer diff for this round
is four deleted lines in `beach_render.viewpoint` plus a measurement instrument
that draws nothing. No albedo was added, no texture, no noise field, no new
constant. Every structure visible here was being computed before and was
outside the frame or under the camera's feet:

| what you can see | the number it comes from | where it is computed |
|---|---|---|
| the surf zone and its lines | `tr['brk']`, `H`, `S` from the 2-D transform | `beach.transform_2d` |
| the cliff face reading as rock | slope clause `(\|h_x\|+\|h_y\| − 0.35)/0.5` | `beach_render.shade_land` |
| pocketed bare rock on the present bench | `rock_bare_mask` on `sand_cover_fraction(regolith)` | `beach.rock_bare_mask` |
| the wet/dry edge on the beach | `damp_limit`, `sheet_front` — run-up realisations | `beach.damp_limit` |
| the ground's shading in the patch | the bed normal `N` from `run_coast(stands=4)` | `beach.coastal_step` |

### Which of them carries the patch, measured rather than asserted

The patch was re-rendered with every driver field read out beside it. Ruling 17
asks for the chain, so here it is, and one row of it is a **negative** result
that matters more than the positive ones:

| driver over the patch | mean | range | hf sd |
|---|---|---|---|
| ground height `h` | 13.44 m | **0.643 m** | 0.004 |
| `\|∇h\|` | 0.249 | 0.257 | — |
| `N · sun` | 0.571 | **0.186** | 0.001 |
| slope-clause `rock` mask | 0.0061 | 0.290 | 0.003 |
| `plain` mask | 0.9939 | 0.290 | 0.003 |
| `cover` | **1.000000** | **0.0** | 0.000 |
| `bare` (sub-grid pockets) | **0.0** | **0.0** | 0.000 |

**The variance is the bed's own normal and the slope-classified material edge
at the brow, and nothing else.** `h` ranges over 0.643 m across the patch here
against **4.7 mm** at the legacy camera — a factor of 137 in the *ground*, which
is what the factor of ~165 in the radiance is made of.

**And the negative row is the round's honest limit.** `cover` is exactly
1.000000 and `bare` is exactly zero, so `rock_bare_mask` — the one sub-grid
process the material path has — contributes **nothing at all** on this surface,
and cannot: 300 kyr of denudation puts 9 m of regolith over a 0.25 m rock
roughness, so `sand_cover_fraction` saturates by construction. A soil-mantled
tread has no sub-grid model in this project. That is the gap, and it is named
in `12-glacial-coastal.md` rather than filled with a texture.

## The frame, measured on the radiance buffer

| | before (legacy brow) | after | wave 15, un-terraced |
|---|---|---|---|
| water | **1.6 %** | **16.2 %** | 16.8 % |
| land | 66.4 % | 51.6 % | 51.1 % |

The composition returns to the wave-15 share. That is a *consequence* and not a
target: nothing in the repaired search knows what ends up in frame. It stops at
a break in slope whose threshold is the plain's own declared gradient
(`beach.S_PLAIN`), and it takes the seaward-most such break rather than the
first one it meets.

## The one number this round is scored on

Rows 620–720, cols 60–360 — wave 11's rectangle — **scene-linear and
un-quantised**, which is the standing ruling and is *not* how the 3/10 was
published:

| | hf sd, scene-linear | distinct 8-bit levels |
|---|---|---|
| before (legacy brow) | `4.841e-06 / 4.866e-06 / 2.608e-06` | **1 / 1 / 1** |
| **after** | `7.958e-04 / 7.768e-04 / 4.495e-04` | **14 / 11 / 10** |
| un-terraced, the 3/10 bed | `5.558e-04 / 6.349e-04 / 3.519e-04` | 9 / 8 / 8 |

**×164 / ×160 / ×172** against the frame this replaces, and **×1.43 / ×1.22 /
×1.28** against the un-terraced frame wave 11 scored 3/10 on, whose 9 / 8 / 8
display levels become 14 / 11 / 10. All three measured in one run by one
estimator; `s18-land-patch` records where that estimator disagrees with wave
16's, and why the disagreement changes no conclusion here.

## What this frame is still not, and it is the owner's own complaint

**The coastal plain is still a flat green plane.** It is smaller — 51.6 % of the
frame against 66.4 % — and it no longer fills the foreground, but nothing about
its *surface* changed and `s18-land-patch` shows that plainly: at 1:1 the plain
is one colour in this frame just as it is in the one before it. This round moved
the camera off it and put the sea back; it did not give the plain a surface, and
it does not claim to have.

Two other things in this frame belong to other lanes and are not this round's:
the blown-out white wedge at the left edge is the glitter path, and the foam is
a placeholder (bar section C, an open row).

The reason the plain cannot be fixed from *this* lane is measured rather than
asserted. A
median land pixel here covers about **4 mm of ground against a 2 m grid**, and
**99 % of land pixels fall below half a cell** — so the near field is a
bilinear interpolant of four corners, and no field the generator computes on
that grid (slope, aspect, regolith, cover, the planed mask) can vary across it.
The remaining texture would have to come from a sub-grid surface process for a
soil-mantled tread, which `terrain-architect/references/12-glacial-coastal.md`
does not have. It is named there and not drawn here.

*Provenance: measured. `terrain-renderer/reference-impl/beach_view_evidence.py`,
which regenerates this figure and both of its siblings. Statistic:
`beach_render.hf_sd` over `beach_render.PLATEAU_PATCH`, on the scene-linear
buffer before the tone map. Guarded by `_sec_view` in `validate_beach.py`.*
