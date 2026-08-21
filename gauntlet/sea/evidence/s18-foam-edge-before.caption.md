# s18-foam-edge-before

**1:1 crop of the foam edge, the field waves 6 to 17 drew.** Full-resolution
render buffer, columns (223, 685, 783, 1045) of a 1440 x 1920 buffer, one render sample per
image pixel -- the 2 x 2 downsample is not applied, so this edge is not
smoothed into or out of existence by resampling.

**Provenance: measured.** Rendered by `foam_evidence.py` from this build with
`foam_realise = False` and `foam_roller = False`, which are the control-panel
branches `beach_render.shade_water` already carries. It is therefore the same
code path as the AFTER half with two flags moved, not a remembered checkout.
`foam_realise = False` alpha-blends by `coverage(m) = 1 - exp(-m)`, the
EXPECTATION of the Boolean model; `foam_roller = False` lays the deck from
Battjes & Janssen's `Q_b` instead of the roller.

**Display-referred, and it has to be.** Encoded through
`beach_render._save`'s curve -- exposure `WHITE`, gamma 2.2 -- because the
numbers below are compared against 8-bit JPEG photographs and a run-length
statistic above a half-max threshold does not survive a change of tone curve.
Every physical quantity in this project is measured scene-linear; this one is
not, deliberately.

**Measured on this crop, leftmost 500 px:** correlation length
`l/W` = 2.25 % of the box width, acf 1/e = 11.26 px, run q90 =
328 px, gap median = 209 px. The photographs in
`gauntlet/sea/bar/generic/` give 0.3-0.8 % and 8-52 px.
