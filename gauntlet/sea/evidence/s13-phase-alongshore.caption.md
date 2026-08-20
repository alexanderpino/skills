# s13-phase-alongshore — the crest field had no alongshore half

Wave 13's largest finding **for the picture**, drawn two waves late because all
three of that wave's builders died at or before the evidence step.

`transform_2d`'s docstring says contours of `S mod 2π` are the crests, and that
this is what the plan-view figure and the render draw. Waves 1–12 set
`S[:, 0] = 0` and integrated only `k_x`. `k = grad(S)` has two components. So
the one field the renderer draws crests with satisfied `dS/dx = k_x` exactly and
**`dS/dy = 0` exactly**, at a sea state whose orthogonal is 20° off
shore-normal.

## The two upper panels — the bay in plan, same bed, same wave field

| | |
|---|---|
| **left** | waves 1–12. Every crest runs **exactly shore-parallel**, edge to edge, at constant orientation, whatever the sea state says. |
| **right** | wave 13. The crests cross the frame at the obliquity the sea state declares, and refract into the embayment where the contours curve. |

Nothing else differs. **The left panel is generated from the right one**, not
from an old checkout: the march's increment does not depend on `S`, so waves
1–12's field is exactly this one with its own boundary column subtracted off
every row. That is an identity, not an imitation, and it is the same
substitution `--bug phase-no-alongshore` uses in the suite.

## The two lower panels — the control whose answer is known in advance

A flat bed in 20 m of water, where refraction has nothing to bend and the answer
is a plane wave (standing ruling 14).

| | waves 1–12 | wave 13 | closed form |
|---|---|---|---|
| `dS/dx` | 0.057264 | 0.057264 | `k cos θ` = 0.057264 |
| `dS/dy` | **0.000000** | 0.016998 | `k sin θ` = 0.016998 |
| alongshore phase run over 1408 m | **0.00 rad** | 23.93 rad | 3.81 wavelengths |
| crest azimuth read off `S` | **0.000°** | 16.533° | θ = 16.533° |

The obliquity was present in `theta`, in the radiation stress, in the longshore
transport and in every suite row that reads them. It was absent from the field
the crests are drawn with. **That is half of what wave 11's critic called
corrugated roofing, and none of it is a spreading problem.**

## What this figure does not show, and it is a degeneracy worth naming

On a **straight** coast `k_y` does not depend on `y`, so `S(y, 0)` is linear and
the march adds the same increment to every row: `dS/dy = k sin θ` then holds for
a reason that has nothing to do with the irrotationality the fix relies on. The
lower-right panel is therefore a test of the **boundary condition** and not of
`curl(k) = 0`. The non-degenerate test is run on the **bay**, where `k_y` varies
alongshore by sd 5.7e-3 rad/m — suite row *"CURVED bay: dS/dy = k sin(theta)
where k_y varies alongshore"*, rms 2.4e-4 clean against 1.7e-2 with the defect
reintroduced, a factor of seventy.

**Blast radius, measured rather than asserted:** `S` feeds no flux term, so the
bed, the height and the angle are bit-identical either side of the fix. Only the
drawn phase moved.

*Provenance: **measured**, scene-linear SI throughout — every field plotted was
computed by `beach.py` and nothing is read back off a PNG. Drawn by
`beach_evidence.fig_phase_alongshore`; the defect is `validate_beach.py`'s
`_bug_phase_no_alongshore`; the fix is `beach.transform_2d`, commit `a5db020`.
Guarded by `_sec_spread` rows S.8.*
