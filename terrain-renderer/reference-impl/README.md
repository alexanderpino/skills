# Pool reference implementation

A physically-motivated renderer for a 1.40 m domestic pool, written to check the
claims in `../references/12-water-rendering.md` against photographs. Every
doctrine statement in that chapter that carries a number was either derived here
or falsified here.

    python3 render.py          # writes pool_final.png, pool_final_dispersion.png,
                               #        pool_final_zoom.png
    POOL_UNDERWATER=1 python3 render.py       # the same frames, plus
                               #        pool_under.png -- the camera under the
                               #        water. The hero frame is bit-identical
                               #        either way; see the section below.
    POOL_WIDE=1 python3 render.py             # the whole basin from a high
                               #        oblique: pool_wide.png and its two
                               #        companions. Same physics, same
                               #        constants, only the camera moves --
                               #        it is the frame the water/stone ratio
                               #        was first measured on, and it is a
                               #        switch rather than a scratch copy so
                               #        that number can be re-run.

| File | Owns |
|---|---|
| `field.py` | The water surface: wind, reverberant tail, wall reflections, jet boil, jet wake. Answers "what is the slope at (x,y)". Knows nothing about light. |
| `wake.py`  | Eikonal ray tracing of the jet's stationary wake through its own drift field. |
| `render.py`| Light: the caustic pass, liner and tile materials, Fresnel — the **exact equations at every water interface**, not Schlick, because an approximation justified only by speed does not belong in a reference and the far water's specular term is the brightest thing in the frame — sky, camera, tone map. |

Sun position is the measured one for the reference photograph (Aljezur, 37.319N
8.803W, 2026-08-10 18:41 WEST): elevation 21.0 deg, azimuth 273.75 deg.

## Validating it — `validate.py`

    python3 validate.py          # runs everything, exits non-zero on any FAIL
    python3 validate.py -v       # also prints every tolerance's justification

`render.py` prints ~90 diagnostics per run and almost all of them check the
implementation against itself. `validate.py` checks it against things that were
not written here, in three tiers, in about 100 seconds — no render, no PNG.

| Tier | Strength of evidence | Covers |
|---|---|---|
| 1 · closed form | a disagreement is a bug in one of the two | exact Fresnel (F0, grazing, Brewster, s/p) — including the renderer's own `fresnel` against the closed-form Brewster value — Snell and the critical angles, TIR and the null return past it, Beer–Lambert, the sun-disc penumbra compression, **a single sinusoid's caustic against its analytic Jacobian**, a flat surface, the sun lobes' flux, the riser gather's closure and `tir_vert(0) = ½` and `WALL_SKY` as the other half of that same hemisphere, the meniscus's force balance and projected-area identity and its two collapse limits, the sign that refutes the fillet's internal-reflection term, **Walsh's relation, `2E_3(0) = 1`, the diffuse path being longer than the vertical one, and a lossless white-bedded pool composed through the shipped `rho_water` coming to exactly 1**, the four wall planes against `pool_sdf`, the analytic ceiling on the fillet's transmitted column, the near-wall fold guard fired both ways, a shadow march of the coping, and — new this round — **the Snell window's half-angle measured off the underwater frame's own ray directions**, the mirror regime's reflectance being exactly 1, Stokes reversibility, **the `n²` radiance gain closed against the air-side transmitted flux**, and — new this round — **the Snell window's share of a HORIZONTAL face against `1/n²` and of a VERTICAL one against `½ − tir_vert(t_c)(1 − 1/n²)`, the same ratio driven to exactly `WALL_SKY = ½` in the `n → 1` limit, `r_int_at` against the water→air equations written from the two indices, `r_int_at ≡ 1` past the critical angle with no tolerance at all, and the upgoing gather closing on 1 over a horizontal face's hemisphere and on exactly ½ over a vertical face's upper half — the same ½ the downgoing gather leaves**, and — new in the illuminant round — **a uniform sky integrating to exactly `L` on a horizontal face and exactly `L/2` on a vertical one, the sky gradient being uniform in BLUE and therefore forcing a vertical face's share of it to the same number to double round-off, the Rayleigh phase function's `cos²Θ` half carrying exactly ¼ of the scattered light — the ceiling that falsifies the old `SKY_DECK` with no photograph in it — `sky() = env_diffuse + the disc` over 4096 directions, `slab_esc(0) = T_OUT_DIFFUSE`, and the ledge form at both of its limits** |
| 2 · published measurement | a disagreement may be a bug or a different water | pure-water absorption vs Pope & Fry 1997 and Smith & Baker 1981, slope statistics vs Cox & Munk 1954, the round-jet constants S and B, capillary-gravity dispersion and c_min, and — new in the illuminant round — **the derived deck illuminant's diffuse fraction of global horizontal against the 0.10–0.35 a clear sky gives at air mass 2.8** |
| 3 · independent method | a disagreement localises to one of the two methods | Monte-Carlo vs the reflected-slope ellipse, a 0.2 mm march vs the analytic cylinder, the separable GEMM vs the direct plane-wave sum, MC vs the exact rectangle view factor, **the bed ↔ wall transfer closed by reciprocity — the shipped gather's lattice against that same rectangle view factor**, the shipped 960-direction lattice against its own closed form over the wall's height range, MC vs TIR_FRAC and TIR_VERT, the empirical diffuse-Fresnel fit vs the file's quadrature, the eikonal solve against its own conserved Hamiltonian, an RK4 march of Young–Laplace vs the meniscus profile, a 4000-ray fan vs its projected area, a 1 mm march of the bed height field vs `scene_hit`'s five-plane solve, a 128 000-hit march of the fillet's transmitted fan vs the wall map's extent, the pool's apparent albedo integrated ray by ray vs `wet_albedo`'s trapped series, **`rho_water` at the file's own absorption against a 400 000-photon random walk, and `2E_3` by Gauss-Legendre against the exponential-integral recurrence**, a 0.5 mm march of the water body vs `scene_hit_under`'s any-direction solve, and — new this round — **`axial_share`'s 2-D quadrature reproducing `tir_vert(t_c)`'s closed form, the upgoing lattice's mirror coefficient against `R_INT` reached by Walsh's reciprocity rather than by any integral, and the solve run for exactly `NSOLVE` passes from black against `trap_gain`'s closed geometric series**, and — new in the illuminant round — **the deck illuminant against a 400 000-sample cosine Monte-Carlo and against its own lattice at 16× the directions, the aureole term against its lobe integrated in `validate.py` from `L_AURE` and `N_AURE` alone, `slab_esc` against a 300 000-photon walk of the same slab, and the band's occlusion march against a direct angular quadrature of the same blocking rule** |

The highest-value single test is the **sinusoid caustic**: for `h = a sin(kx)`
under a vertical sun the whole pass is a 1-D map with an exact Jacobian, so the
caustic pass — the least checkable thing in the renderer — gets a right answer to
compare against. It matches to **0.086%** pointwise below focus and locates folds
to **0.38 mm**. It also pins `F = 0.25·d·s·k`: the 0.25 is `1 − 1/n`, and fold
onset for one sinusoid is `0.25/((1−1/n)√2) = 0.7048`.

**It does not render a pixel.** The camera pass, the shadow map, the coping march,
the material tables, the tone map and the individual band levels are all outside
it; the file ends with a section naming every gap, and that list is as much the
deliverable as the tests are.

**Reading a failure.** Every row prints expected, measured and tolerance, and every
tolerance is justified in a comment beside it — chosen from the *estimator's* own
error (binning, Monte-Carlo variance, float32 accumulation) or from a published
uncertainty, never from the measured disagreement. So a FAIL means the number is
outside what the measurement itself can explain, and the next question is *which
of the two sides is wrong*, never *can the tolerance move*. Rows marked INFO carry
no assertion and never affect the exit code.

**It loads `render.py` by slicing.** `render.py` has no `__main__` guard, so
importing it would run the full render. `load_render()` parses the source and
executes only the nodes that define things. The guard against that silently losing
something is the `REQUIRED` list: the loader raises if any name the suite tests is
missing, so a restructured `render.py` produces a loud error rather than a quietly
absent test.

**It is green, and that took work rather than tolerance.** The suite exited 1 on
eight rows for several rounds — three absorption, two Schlick-vs-exact-Fresnel, one
missing total-internal-reflection branch, and two on `TIR_VERT`. All eight are now
closed with no tolerance widened; four tolerances were *tightened* to double
round-off because the quantity they cover became an identity rather than an
approximation.

**It is now 268 rows and 0 FAIL, up from 240.** The 28 newest are the two
illuminants above the water — the deck's and the freeboard band's, both derived
from the file's own `sky()`, plus the closures around `WBOUNCE` and the coping's
occlusion march — and their bug-reintroduction table is with their section below.
The 15 before them are the underside
of the surface — the window's two shares, the mirror's own reflectance, the
upgoing gather's closures and the solve's fixed point — and every one of them was
fired at the bug it was written for by putting the bug back:

| bug reintroduced | rows that FAIL |
|---|---|
| `SKY_VERT` back to `WALL_SKY = 0.5` on the submerged wall | 1 |
| the solve truncated to **one** pass | 2 |
| the solve truncated to **three** passes | 1 — and it is the high-albedo one, which is the right way round |
| the window's vertical share written as a flat partition | 1 |
| the mirror not total past the critical angle | 4 |

**And one of them is blind, found the same way and recorded rather than papered
over.** Every row tests `window_shares(profile=False)`, and the identity row
compares `SKY_VERT` with `WIN_VERT/WIN_BED` — which come from the *same call*. So
a wrong sky **profile** inside the window moves both and no row moves. An INFO row
now prints both numbers side by side (0.2141/0.2032/0.1916 profiled against
0.1995/0.1988/0.1976 flat), which bounds what that blindness can cost at 2%.

The 10 before them are the pool's
closed-form albedo and the photon walk that guards it, and why the audit they
replace was blind is written up in the first section below. The 19 before them are
the underwater camera's, and they are listed with the section further down. The 27 before them are the
guards on the six defects closed below plus the four on the wall gather, and each
was checked the only way a guard can be: by putting the defect back. Reverting the
`1/n²` fails 6 rows, writing `1/n` instead of `1/n²` fails the same 6, putting
the wall planes back on the plan rectangle fails 4, shortening the wall map fails
2, neutering the fold guard fails 2, handing stone `sun_vis` again fails 1, and
setting `WALL_SKY` back to 1 — the double count the bed-onto-wall round exists to
avoid — fails 2. A guard that does not fire on the bug it was written for is a
comment with a `check()` around it.

**One of the four is deliberately narrower than it looks, and the file says so.**
The reciprocity row proves the bed → wall transfer is the right *size*; it does
not prove `render.py` *applies* it, because no row here builds a wall map (that
costs a caustic pass). A wall left dark would still pass every row in this file.
What catches that is `render.py`'s own `wall bounce:` print and the ordering
verdict in the colour regression — and the epilogue names the gap rather than
letting the green count imply otherwise.

Two of those eight are worth knowing about even if you never read the code, because
they are the reason the tolerance column is not the interesting one:

- **`TIR_VERT` — a green test would have installed a second wrong number.** The
  constant shipped 0.563; the derivation in the comment beside it evaluates to
  0.635; the physics gives 0.885. The suite's two rows — a 2M-point quadrature and
  a 4M-sample Monte-Carlo, filed as independent methods — had both been written
  from that comment's sentence rather than from the interface, so they agreed with
  each other and were both wrong. **Two methods that read the same premise are one
  method.** What closed it was a check with nothing to transcribe: as `θ_c → 0` the
  ratio is forced to exactly ½, which both wrong forms miss (0.239 and 0.318), and
  that same ½ is now cross-checked against the riser gather's closure — unrelated
  code, same number.
- **Schlick was in a reference, and its error changes sign inside one frame.**
  `_fresnel_rough` at zero variance was plain Schlick. Over the 38–79° of incidence
  this camera spans, `Schlick/exact − 1` runs **−22.8% at 51.3°** and **+14.3% at
  79°**, crossing zero at 67.1° — so the far water read too much like a mirror while
  the mid water read too little, on the brightest term in the picture, and no single
  multiplier could have fixed both. The renderer now evaluates `R_s` and `R_p`; the
  guard is the closed-form Brewster value, which an approximation cannot reach
  (Schlick misses it by 22%). Cost: **+1.1% of render time.**

The general rule those two produced, now doctrine in `11`: **a test and the code it
checks must not share a premise.** Derive the value from physics, write the
derivation down, and then guard it with something that could not have been written
from it — a limit, a conservation identity, an analytic special case, or the same
quantity reached by unrelated code.

## Measured — two illuminants derived from one atmosphere, and the ordering still does **not** emerge

The previous round located the remaining factor of 1.9 on the **band** rather
than the wall, named three candidates, and moved none of them. They are moved
here — not by calibration, which the standing ruling forbids, but by deriving
them, and the first thing the derivation does is **falsify the previous round's
own counterfactual**.

| north wall (averted, `cau` = 0.000), scene-linear luminance / dry band | wave 14 | wave 15 | wave 16 |
|---|---|---|---|
| wall, 0–100 mm below the line | 0.470 | 0.518 | **0.513** |
| wall, 100–250 mm | 0.581 | 0.616 | **0.621** |
| the dry band itself, absolute | 0.5724 | 0.5721 | **0.5524** |
| what the observation requires | > 1 | > 1 | > 1 |

**The ordering did not emerge, and this round says so plainly rather than
reaching for it.** What it does deliver is that the gap is now attributed to one
place: with the band's illuminant derived and the wall's hemisphere untouched,
the remaining factor of **1.95** is not a missing band term and not a missing
wall term.

**The control is the mirror image of the last round's.** Wave 15 moved
everything under the water and nothing over it. This round moves everything over
the water and nothing under it: the solve's convergence table is *identical* to
wave 15's, line for line, seed to pass 6. The submerged pixels do move by a
little — 83.4 → 80.5 in encoded luminance on the first 100 mm of wall — and that
is entirely the **reflected** column, because what the water reflects at the
wall is the band and the coping and both of those changed. The transmitted
column is unchanged to the digit (0.190 and 0.239, before and after).

### `SKY_DECK`, and it was two errors that cancelled in green

`SKY_DECK = SKY_AMB × 0.30 + SUN_COL × 0.075` was the longest-standing underived
constant in the file — 1.74 stops written by hand, filed as open for the whole
project, and applied to a horizontal deck and a vertical band alike. There is
nothing left to choose in it. An illuminant for a diffuse receiver is one
number,

```
E(N)/pi = (1/pi) INT_hemisphere L(w) (w.N)+ dw
```

and the file already owns `L(w)`: `sky()` is a complete environment whose two
lobes were derived, the round before, from the same Rayleigh atmosphere that
reddens `SUN_COL`. The only judgement is **which lobes belong**, and that is
settled by the audit already in the file: the disc lobe carries the beam
*exactly* (its flux is `π·SUN_COL` to a part in a thousand), and every diffuse
receiver already gets that beam as an explicit `SUN_COL·(N·L)·vis` term, so
integrating the disc as well would light the frame with two suns. The aureole is
not the beam — it is light scattered *out* of the beam, arriving from directions
the beam does not — and it is skylight.

|  | red | green | blue |
|---|---|---|---|
| the gradient's own cosine integral | 0.4478 | 0.6381 | 1.1270 |
| the Rayleigh aureole | 0.0616 | 0.0928 | 0.1405 |
| **derived `SKY_DECK`** | **0.5094** | **0.7310** | **1.2675** |
| what shipped | 0.8127 | 0.8462 | 0.8604 |
| shipped / derived | **1.60** | **1.16** | **0.68** |

**The level was 16% high in green and the colour was wrong in both directions,
because the two hand terms were each wrong by more than their sum was.**
`SKY_AMB × 0.30` is **0.42×** the gradient's own cosine integral; `SUN_COL ×
0.075` is **6.2×** the aureole's. They very nearly cancel in green — which is
how a constant this wrong survived every green-channel comparison this project
ever made.

**And the aureole's share has a ceiling that needs no quadrature at all.** The
Rayleigh phase function is `P(Θ) = (3/4)(1 + cos²Θ)`. Over the sphere `∫P dω/4π
= 1`, and its `cos²Θ` half contributes exactly `(3/4)(1/3) = 1/4` — for **any**
optical depth and **any** sun elevation. So a singly-scattered Rayleigh sky
cannot put more than a quarter of its diffuse light in the forward lobe — and
higher orders only add to the isotropic side, so the ceiling on the *total*
diffuse sky is if anything lower. The derived aureole is **12.7%** of the deck illuminant in green. The constant it
replaced put it at **68%**. That is a falsification from the atmosphere the file
already recovered from `SUN_COL`, and it needs no photograph.

**`?` What is still not derived, and exactly what is missing.** The two lobes
come from the Rayleigh atmosphere; the **gradient** — `SKY_HOR`, `SKY_TOP` and
the 0.55 exponent between them — does not, and never did. What the atmosphere
can say about it is a **lower bound**, and the bound is computed rather than
asserted: single-scattered Rayleigh radiance for a ground observer,

```
L = (F0 P(Theta)/4pi) mu_s (e^{-tau/mu_v} - e^{-tau/mu_s}) / (mu_v - mu_s)
```

with `F0 = E_SUN·e^{+τ·m}` the top-of-atmosphere beam this file's own `SUN_COL`
implies, gives a deck illuminant of `(0.246, 0.367, 0.557)` against the
gradient's `(0.448, 0.638, 1.127)` — **0.55 / 0.58 / 0.49** of it. That is a
bound and not a disagreement: it has no multiple scattering and no ground
return, and at `τ_R(blue) = 0.202` neither is small. **What is missing is
named** — orders two and up of the sky's own radiative transfer, and the albedo
of the ground under it — which is the honest form of an open constant rather
than a `0.30`.

### The band's own hemisphere, and the term that was absent from it

`liner_band` lit a **vertical, sun-averted** strip with `SKY_DECK × 0.50`. The
halving is right for a uniform sky and for nothing else: a vertical face's
cosine weight is `sin²θ dθ`, heaviest at the **horizon**, which is the brightest
part of this sky in red and green and the part the aureole sits 21° above at
*one* azimuth. One number cannot be both. So the band gets its own integral, at
its own azimuth, with three sources:

| the band's irradiance / π, north wall (averted) | red | green | blue |
|---|---|---|---|
| its own sky, upper half | 0.3139 | 0.4016 | 0.6124 |
| the sky the **water reflects** into the lower half | 0.0838 | 0.0975 | 0.1291 |
| the pool's upwelling, `WBOUNCE × 0.50` | 0.0484 | 0.3242 | 0.4749 |
| direct sun (`N·L = −0.061`, clipped) | 0 | 0 | 0 |
| **total** (over the rays that land on it) | **0.4761** | **0.9220** | **1.3568** |
| what it was | 0.5205 | 0.9449 | 1.0660 |

**And here is the finding the previous round could not have made.** Its
counterfactual — *drop the aureole the band cannot see and the ratio goes 0.518
→ 0.78* — was arithmetic on top of a wrong decomposition. Against the derived
integral the band's sky half goes to **0.77 / 0.95 / 1.42** of `SKY_DECK ×
0.50`: it *barely moves in green* and moves a great deal in colour. The
category error was real; its size was not what subtracting one hand constant
from another suggested.

**The azimuth dependence is now real and it is 1.24×.** The east wall's band,
facing the sun, collects `(0.377, 0.497, 0.756)` against the north wall's
`(0.314, 0.402, 0.612)`. "On **every** side" is the load-bearing word in the
observation this line of work is about, and a single halved deck illuminant
cannot be both numbers. A `validate.py` row asserts the ratio is above 1.10 —
a constant wearing an integral's name reads exactly 1.00 and fails it.

**The one term this round ADDS to the band, and it works against the ordering.**
A poolward-facing strip 0–100 mm over the water sees, in its lower half, the
water — and the water returns two different things. The pool's own upwelling was
there; the **sky reflected in that surface** was not. It is not small: the lower
half's weight is heaviest at the horizon and so is the water's external Fresnel,
so the radiance-weighted mean `R_ext` over that half is **0.243**, not the 0.02
of normal incidence. It is 23% of what the band's lower half now gets, and it
makes the band brighter. It is in because it is there, not because of which way
it pushes.

### The coping's overhang, marched instead of asserted

The shader's `0.50` for the sky half was right, and it was right for a reason it
did not state. The bullnose's poolward extreme is at `SBUL − BULR = SLIP`, the
band's **own plane**, and the stone recedes from the pool going up, so every
direction the coping occupies has `(ω·N) ≤ 0` and carries zero weight. The stone
overhangs the **water** by 20 mm and the **liner** by nothing.

That is now **traced**: `band_sky_vis` marches one ray per direction over 8192
directions at 12 heights against this file's own `edge_z`, and returns
**1.0000**. The closed form for a strip under an infinite ledge of width `w` at
height `D` — `(α + sin α cos α)/π`, `α = atan(D/w)` — is the second route, and
it is exactly 0.50 (i.e. the whole upper half) at `w = 0`. The 30 mm
counterfactual costs the strip 6% of its sky on average and 0.6% at its foot;
that is what a *different section* would cost and it is a section question, not
a lighting one.

**A real overhang is not a height field, and saying so is the point.** `edge_z`
is a section `z(s)`; the only thing it can put over the band is stone the band
stands on. So the shipped answer is an identity, not a coincidence — and the
marcher is fired at the thing a height field *can* put in front of the band, a
wall, at the limit (a 3 m wall 10 mm out takes everything) and in between
(against a direct angular quadrature that shares no step and no height field).

### `WBOUNCE`, against the converged floor

It shipped as a closed-form guess with three defects at once, and the previous
round measured it at `(0.53, 0.77, 0.93)` of the truth:

- the **escape was factorised out of the attenuation** — `exp(−a·DEPTH)` for a
  vertical up leg times a mean escape, when a steep ray escapes *and* crosses
  less water. This file has already been caught making exactly this mistake
  once; it costs 19.4 / 5.1 / 1.1% per band;
- an undeclared `0.8` on an ambient that was not attenuated at all;
- **one bounce**, where the solve has six.

It is now `wbounce_of(L) = L × slab_esc()` — one integral, both factors inside —
evaluated on the **converged deep floor**. The definition stays where it always
was, six hundred lines up beside the `1 − R_int` it used to lead with; only the
evaluation moved past the solve, and a closed-form seed stands in its place
until then so the two routes can be printed against each other.

| | red | green | blue |
|---|---|---|---|
| `slab_esc()` | 0.3403 | 0.4795 | 0.5106 |
| × the converged deep floor `(0.285, 1.352, 1.860)` | **0.0969** | **0.6484** | **0.9498** |
| the closed-form seed (same escape, `shade`'s own deep floor) | 0.1465 | 0.8360 | 1.1043 |
| what shipped | 0.1836 | 0.8404 | 1.0249 |
| shipped / converged | **1.90** | **1.30** | 1.08 |

The gap between the seed and the converged value is the trap and the walls,
i.e. exactly what six passes add — the second route this number now has. And
note the **sign**: the band was over-lit by its own upwelling, so the wall/band
ratio used to *understate* the wall and now does not.

### What this did to the water/stone ratio, and it is the honest answer

| water / sunlit stone, hero frame, transmitted column, scene-linear | wave 15 | wave 16 |
|---|---|---|
| the render | 0.836 | **0.908** |
| the closed form beside it | 0.772 | **0.839** |
| apart | +8.3% | **+8.2%** |

**Both sides moved by the same factor and the disagreement did not move at
all**, which is exactly what should happen: the closed form's water is unchanged
(nothing under the water moved) and its *denominator* is the render's own
sunlit stone, which fell 8% when the deck's illuminant was derived. So this
round adds no information about the 8.2% — and that is itself information,
because it means the overshoot is **not** in the deck term. It is in the bed's.

**Bar section J2b's headline measurement is water against sunlit sandstone, and
it moves the right way — in the units the bar actually read it in.** The bar
records the render "near 0.40 where all three frames read at or above 1". That
0.40 was a *display-referred* reading of a PNG, which this project has already
refuted as an instrument (see the section below: 0.395 against a true 0.735).
Both numbers moved this round and both moved up: scene-linear **0.836 → 0.908**,
and the display-linear median-over-median off the sRGB frame — the number a
reader with the PNG would get — **0.779 → 0.849**. From a denominator that was
derived rather than dialled, with the water untouched.

**The wide frame moves the same way, and by the same mechanism.** `POOL_WIDE=1`,
same code, same constants, only the camera: water / sunlit stone goes **0.796 →
0.863** against a closed form that moves **0.677 → 0.735** on that geometry —
+17.6% apart before, **+17.4%** after. Two cameras, one denominator, and the
disagreement is the same one in both. **77.4% of the wide frame's pixels moved,
mean |Δ| 17.9, worst 34, luminance 169.35 → 165.46** — more of that frame is deck
than of the hero's, which is the whole of why.

### And the third illuminant, priced and **not** moved

The same integral prices `SKY_AMB`, because the Snell window is a change of
variables and nothing else: `n² cos t_w sin t_w dt_w = cos t_a sin t_a dt_a`
maps the window integral of the `n²`-gained sky exactly onto the air-side
hemisphere, so a submerged horizontal face's sky irradiance is the **deck's**,
less what the surface reflects away.

| | red | green | blue |
|---|---|---|---|
| `SKY_DECK × (1 − R̄)`, `R̄ = (0.086, 0.077, 0.068)` | 0.4655 | 0.6745 | 1.1812 |
| shipped `SKY_AMB` | 0.559 | 0.903 | 1.419 |
| shipped / derived | 1.20 | **1.34** | 1.20 |

**It is left alone on purpose, and the reason is attribution, not timidity.**
`SKY_AMB` is the wall's illuminant *and* the bed's, so it is the numerator and
the denominator of the wall/band ratio at once; moving it in the same round as
the band would make the one number this work exists to report unreadable. It is
also the arithmetic that closes the water/stone overshoot: the sky is **20.3%**
of what lights this floor in luminance (beam `(1.469, 1.974, 1.624)` against sky
`(0.219, 0.505, 0.861)`, both printed every run), a 34% over-supply of it is
worth **5.2%** on the bed directly, and the trap and the wall return amplify
that by a further 1.2–1.3× — against the **8.2%** measured. Same order, same
sign, and not arranged. **That is the next round, and it is now a number rather
than a suspicion.**

### What the derivation exposes, which is not a new defect

The comment that used to sit over `SKY_DECK` justified its warmth as *"a warm
albedo times a blue illuminant is grey"*. It was **right about the mechanism and
wrong about which constant causes it.** With the illuminant derived, the deck's
sky is the blue sky it actually is — and the warm beam standing beside it is
still multiplied by `0.30`, the last factor above the water with no derivation
anywhere in this file. Under-weight the beam by 3.33 and the blue term wins:

| a horizontal coping facet in full sun | `E/π` | × `COP_ALB` | linear saturation | sky's share |
|---|---|---|---|---|
| at the shipped `0.30` | (1.435, 1.557, 1.891) | (1.026, 0.890, 0.828) | 0.193 | 47% |
| at `1.00` | (3.595, 3.483, 3.347) | (2.570, 1.992, 1.466) | **0.430** | 21% |

In the frame the coping's sRGB median goes **(180, 164, 139) sat 0.23 → (166,
158, 157) sat 0.05**. That is a legible regression in the picture and it is
reported as one. It is **not moved**, for the reason it has never been moved:
`0.30` is the exposure of the entire above-water half, its blast radius is
coping, paving, band and the `WBOUNCE`/`SKY_DECK` balance between them, and
raising it to 1 more than doubles the deck. What has changed is that it is no
longer hiding behind a warm illuminant — the symptom is now on the picture and
in a printed counterfactual, which is a sharper handle than "two receivers get
the same beam at a ratio of 3.33".


Also worth recording, because a `?` that is written down is worth more than one
that is not: the band's **grazing sheen** still takes `WBOUNCE` as its source,
and after this round that is demonstrably the wrong half of what the water
returns — at the angle the band is seen at, the water in front of it is mostly
reflected sky. `emir` is exactly that quantity, but averaged over a half-space,
and the sheen is a *per-direction* term, so closing it means a per-ray lookup
rather than a swapped constant. Marked in `liner_band`, not moved.

### The observation this whole line of work is chasing, against the bar's own reading

Worth stating, because it changes what "the ordering" means. Bar section J,
written from the seventh and eighth photographs of the same pool:

> **The submerged wall reads darker than the freeboard above it, in both
> frames** — the opposite ordering to the low-angle sunlit photographs that
> drove the wall work. **Both orderings are real and the render must produce
> both** … This is a prediction to test, not a target to dial.

The hero frame's wall is the **north** one, averted, `cau = 0.000` — a shaded
wall seen against a directly-lit band. It reads 0.513, i.e. **the J ordering**.
The other ordering is a *sunlit* wall, and the file prints `cau = 0.920` on the
east wall and its radiance at 2.63 / 1.63 / 1.39 × the deep floor. So the render
produces both, from geometry, with no constant between them — which is what J
asks for. What it does **not** produce is the low-angle ordering *on an averted
wall*, and after two rounds of building the receiver and one of deriving the
source, the honest reading is that either `SKY_AMB` above is the whole of the
remainder, or that observation and this physics disagree.

### What moved in the picture

Above the waterline, everything; below it, only what the water reflects. **43.0%
of the hero's pixels moved, mean |Δ| 16.6 levels over those, worst 35**, mean
encoded luminance **140.96 → 138.74**.

**And the underwater frame is bit-identical to wave 15's — every pixel, all
960 000 of them.** `w16-underwater.png` and `w15-underwater.png` differ by zero,
which is worth stating precisely: that frame sees the submerged wall *directly*,
with no reflected column over it, so it is the cleanest available check that the
wall's own radiance did not move. What it does **not** check is the band or the
coping, because it cannot see either — the window's outer rim is filled by
`sky()` and nothing else, which is section G's standing `?`. The two controls
together — this frame and the solve's convergence table, identical line for line
— are what let the hero frame's 0.518 → 0.513 be attributed entirely to the
band.

| sRGB median, encoded luminance | wave 15 | wave 16 | why |
|---|---|---|---|
| **riser face** | **(16, 122, 162) · 102.4** | **(16, 122, 162) · 102.4** | **the control** |
| **tread top** | **(73, 169, 193) · 150.3** | **(73, 169, 193) · 150.3** | **the control** |
| **floor, sunlit** | **(53, 161, 184) · 139.7** | **(53, 161, 184) · 139.7** | **the control** |
| **floor, in shadow** | **(42, 109, 156) · 98.1** | **(42, 109, 156) · 98.1** | **the control** |
| **water in front of the wall** | **(66, 157, 182) · 139.5** | **(66, 157, 182) · 139.5** | **the control** |
| coping stone | (180, 164, 139) · 165.6 · sat 0.23 | **(166, 158, 157) · 159.6 · sat 0.05** | the deck illuminant, derived — and the `0.30` beside it |
| freeboard, dry blue band | (45, 153, 173) · 131.5 · sat 0.74 | **(39, 148, 188) · 127.7 · sat 0.79** | its own hemisphere, `WBOUNCE` closed |
| wall, 0–100 mm | (20, 97, 136) · 83.4 | **(15, 94, 139) · 80.5** | the reflected column only |
| wall, 100–250 mm | (30, 109, 152) · 95.3 | **(27, 107, 153) · 93.3** | the same |

**Five rows are the control and they did not move at all** — same triple, same
luminance to the decimal. Nothing this round touches can reach into the water,
and the frame says so rather than the commit message. The band went **more
saturated and slightly darker** (0.74 → 0.79), which is the derived illuminant
doing what a derived illuminant does: the old constant's fake warmth was
desaturating a blue liner.

### Suite

**268 rows, 0 FAIL, up from 240.** The 28 new ones are the two illuminants and
the closures around them, and every one was fired at the bug it was written for
by putting the bug back:

| bug reintroduced | rows that FAIL |
|---|---|
| `SKY_DECK` back to `SKY_AMB*0.30 + SUN_COL*0.075` | 3 — the identity, the aureole cross-check, and the Monte-Carlo |
| the `1/π` dropped from `env_irradiance` | 9 |
| the sun's **disc** let into the diffuse lobes | 8 — including the ¼ ceiling and the blue/red bounds |
| the **aureole** dropped from them | 3 |
| `band_illum` returned `SKY_DECK × 0.50` flat | 3 — including the azimuth-dependence row |
| `band_sky_vis` neutered to "nothing is ever blocked" | 3 |
| `wbounce_of` re-factorised as `T_DIFF_UP × T_OUT_DIFFUSE` | 1 |
| `slab_esc` re-factorised the same way | 1 — the 300k-photon walk |
| the band's mirror term flattened to `R_ext = 0.02` | 2 |

Two routes to every number that has two: the deck illuminant against a
400k-sample cosine Monte-Carlo *and* against its own lattice at 16× the
directions; the aureole term against a lobe integrated in `validate.py` from
`L_AURE` and `N_AURE` with none of `render.py`'s weights; `slab_esc` against a
300k-photon walk *and* against `T_OUT_DIFFUSE` in the zero-depth limit; the
band's occlusion march against a direct angular quadrature *and* against the
ledge closed form at both limits.

**And the sharpest row in the section needs no tolerance from the quadrature at
all.** `SKY_HOR` and `SKY_TOP` are **equal in blue** (0.98 both), so the
gradient is exactly uniform in that channel — and therefore a vertical face's
share of it must be the *same* number the uniform-sky row produces, whatever
that number's own error is. In red and green the horizon is brighter and a
vertical face weights the horizon, so the share must be strictly **larger**. One
row proves the integrator weights by `sin²θ` and not by a constant, and it does
it to double round-off.

**Runtime, priced.** `validate.py` goes **83.0 s → 92.2 s** (+11%, both measured
on an otherwise idle box): the `load_render`
slice gains ~5 s building the 131 072-direction environment lattice, the
121-azimuth band tables and the twelve occlusion marches, and the new tier costs
~4 s, most of it the two Monte-Carlos. `render.py` is unchanged in its
passes — the solve reads **272.7 s → 281.8 s**, which is scheduling noise on the
same 6 × (200 × 100 × 576) gather — and the illuminant block itself is
milliseconds against twelve minutes.

Archived: `gauntlet/evidence/w16-hero-above.png`, `w16-wall-waterline.png` — the
**same crop of the north waterline in both renders, wave 15 above and wave 16
below**, which is the picture this round is about: coping, grey bead, dry blue
band, meniscus line, submerged liner, water, with the *bottom* three now the
unchanged ones and the top three moved — plus `w16-underwater.png`,
`w16-underwater-risers.png` and `w16-wide.png`. All are re-rendered from the
shipped file; the wide one is reproducible with `POOL_WIDE=1` and is comparable
with `w12-wide.png`, `w14-wide.png` and `w15-wide.png`.

## Refuted — the water is **not** dark by a factor of two, and the two errors that made it look that way

This round was handed a finding: *the render's water is too dark against its own
physics, by a factor of 1.5–2.5*, from a closed form predicting a
water-to-sunlit-stone luminance ratio of **0.61–1.00** against **0.401** measured
off `gauntlet/evidence/w12-wide.png`. It was to be recomputed before being acted
on. It was, and it does not survive: **the prediction is 13% high and the
measurement is 1.8× low, and between them they are the whole of the factor.**
The render's water agrees with a corrected closed form to **−4.8%**.

Both halves are now computed every run, in `render.py` under *the pool's apparent
albedo*, so neither can be re-derived by hand again.

> **Read this section with the wave-15 numbers beside it.** The agreement it
> reports — the render's water within −4.8% of the corrected form — was *"not
> innocent"*, and it said so: two ~25% errors of opposite sign, a truncated trap
> and an unmodelled sky. Wave 15 closed the trap, the cancellation broke, and the
> same measurement now reads **0.836 against the form's 0.772, +8.3%**. Every
> number below still holds for the frame it was taken on; the section further up
> carries the new pair.

### The prediction, corrected twice

The chain's shape was right and two of its factors were not. The form as handed:

```
rho_eff = T_slant · rho_bed · (1 − R_int) / (1 − rho_bed · T_round · R_int)
```

- **The up leg is missing from the numerator.** The bed's light has to *cross the
  column* before it can escape; the form has a round trip in its denominator and
  no one-way transmission at all in its numerator. Worth **1/T_up** — 13% in
  luminance at 1.40 m, 85% in red.
- **The two integrals do not factorise, and the error changes sign between them.**
  `T_up · (1 − R_int)` treats attenuation and escape as independent. They are
  strongly correlated: a steep ray escapes *and* crosses less water, a grazing one
  is totally reflected *and* crosses more. The product of the means understates
  the mean of the product by **19.4% in red, 5.1% in green, 1.1% in blue**; the
  round trip is correlated the other way and the factorised form *over*states it
  by **30% in red**. So the file now writes one integral each, over the water-side
  cosine, with the exact internal Fresnel inside them:

```
T_esc = ∫ 2μ exp(−a d/μ) (1 − R_int(μ)) dμ      = 0.3403 / 0.4795 / 0.5106
G_rt  = ∫ 2μ exp(−2a d/μ)    R_int(μ)  dμ      = 0.0965 / 0.3277 / 0.4445
rho_w = (1 − R_ext(sun)) · T_slant · rho_bed · T_esc / (1 − rho_bed · G_rt)
```

The interface constants themselves were checked and they hold: `R_int_diff =
0.47617`, `R_ext_diff = 0.06669`, Walsh exact to float64 — nothing there moved.

| writing | rho_water (lum) | against the corrected form |
|---|---|---|
| as handed, no up leg | **0.2550** | **+12.9%** |
| with the up leg, factorised | 0.2197 | −2.7% |
| **joint integrals** | **0.2259** | — |
| **the render, measured** | **0.2151** | **−4.8%** |

### The measurement, corrected twice

`0.401` is reproducible — this round measured **0.395** off the same PNG — and it
is not the quantity the closed form predicts. **Three** distortions sit between
them, two of which the bar already names for *photographs* and neither of those
had ever been applied to the render's own output:

- **It is a median on a right-skewed field.** A caustic net is bright folds over
  dim cells, so its distribution has a long right tail and its median sits well
  under its mean — measured on the transmitted column over the sunlit floor, the
  median is **0.786** of the mean. A median over water therefore reads the caustic
  *cell* while the same median over smooth stone reads the stone. Worth **−4.7%**
  on the wide frame (0.706 → 0.673) and −4.6% on the hero (0.735 → 0.701).
- **It is display-referred.** `colour_table` reads sRGB code values, which have
  been through the ACES curve *and* a display-side S. Inverting the sRGB EOTF
  recovers display-linear, not scene-linear — which is precisely the failure bar
  section **J2c** pins on the reference photographs, here committed by the
  render's own pipeline. Worth a further **−0.4%** on the wide frame
  (0.673 → 0.670) and −3.4% on the hero (0.701 → 0.677), and the two surfaces are
  far apart in level, which J2c says is the regime the curve hurts worst.

- **And it is taken over a different surface.** The closed form is about *sunlit
  bed under water*. `0.401` was taken over **all** the water in the frame — which
  on that camera includes the sail's shadow and the 1.37 m strip along the far
  wall that the refracted beam never reaches, because the beam walks east and the
  west wall shadows the bed behind it. That is the dark band in the frame, and it
  is physics, not a deficit. Worth **×0.590**, and it is the largest of the three.

`0.706 × 0.953 × 0.996 × 0.590 = 0.395`, which is the number the round opened on,
with every link measured rather than argued.

The wide camera is now a switch on the shipped file (`POOL_WIDE=1`, writing
`pool_wide.png`) rather than a scratch copy nobody can re-run, and it reports the
same statistics. It reproduces the archived frame: the same crude
all-water-vs-all-stone segmentation gives **0.395 on both**, to three decimals,
with identical medians. So the chain is complete and each link is measured:

| reading of the same wide frame | value |
|---|---|
| sunlit floor / stone, transmitted mean over mean, scene-linear | **0.706** (closed form 0.677) |
| … as a median over median, scene-linear | 0.673 |
| … display-linear off the PNG | 0.670 |
| … over **all** water rather than the sunlit floor | **0.395** |

**The four readings of one frame, hero, in one exposure:**

| | water / sunlit stone |
|---|---|
| transmitted column, mean / mean, scene-linear | **0.735** (closed form: 0.771) |
| + the reflected sky, glitter held out | 0.772 |
| median / median, scene-linear | 0.701 |
| median / median, display-linear off the PNG | 0.677 |

A note on the reflected column, because it makes any whole-pixel mean useless: its
mean over the sunlit floor is **18.12** against a median of **0.031**, a factor of
**577**, and all of it is sun glitter at `L_SUN = 3.6e5`. A mean taken over the
whole pixel is that factor's hostage.

### What *is* wrong, and it is two ~25% errors of opposite sign

The agreement above is not innocent. Measured at the bed, against the closed
form's own beam term — beam × `T_slant` × the closed series — the render is
**25.2% short in luminance** (0.887 / 0.734 / 0.635 per channel), and the sky the
form has no room for is worth **+21.5%** on the same bed. Neither is small and
they very nearly cancel. The short side decomposes exactly:

- **`cau` over the sunlit deep floor means 0.906** of the incident, not 1 — a
  factor **0.907**. The sail takes 5.1 m² and the 44.4° refracted beam walks
  1.37 m east, so its last 1.37 m lands on the **east wall**. That light is not
  lost — the wall gather reads it back — but it is not on the bed, and a closed
  form for an infinite basin has no wall to put it on. This is the *walls* entry
  on the finding's own list of simplifications, the one it said could move the
  prediction toward the render. It does, by 9.4%.
- **the trap is carried at one truncated bounce** — a factor **0.827**. It adds
  ×1.0217 in green where the closed series is ×1.2354. Three causes and all three
  are geometry the closed form has no room for: the cone taken is
  `1 − 1/n² = 0.4387` and not `R_int = 0.4762` (the partial Fresnel *inside* the
  cone is dropped), **58%** of that cone meets a wall before it reaches the
  surface, and the returning half is splatted onto walls as well as bed.

`0.907 × 0.827 = 0.750` against the 0.734 measured in green; the last 2% is the
liner's own mottle and the bed's ambient occlusion, which the closed form does not
carry either. And the sky that fills the hole is 22% of the green and 38% of the
blue that lights this floor.

So the answer to the brief's first named suspect — *is the trapped series applied
to the bed at all* — is **no: one term of it is, over the wrong cone, for the 42%
that reaches the surface.** The second suspect, a doubled `1/n²`, is not there:
`out_of_water` is applied exactly once on the bed's route to the eye and the
hemispherical row in `validate.py` still holds it to `1 − R_int`. The third — the
bed's sky — *is* there, and it is the term filling the trap's hole.

### Why the energy audit was blind, and what it does now

`validate.py`'s *"closed energy audit of the whole pool"* is nothing of the kind,
and reading what it borrows says why: **one name.** It computes its own `E_w` and
its own `L_w`, passes them through `out_of_water`, and integrates back. So:

- **it never asks render.py for the series.** It closes `1/(1 − ρ R_int)` itself,
  so a renderer that truncates the trap at one bounce over the wrong cone cannot
  register.
- **it has no absorption and no depth.** Every path length in it is exactly 1, so
  the up leg — the term the prediction was missing — cannot appear in it either
  way.
- **it has no basin.** No walls to take the beam, no sail.

It is a good unit test of one divisor wearing the title of an audit. Two rows now
go through the shipped chain instead, and it takes **both** because each is blind
where the other sees:

- **the lossless limit**, `R_ext(sun) + rho_water(1, a=0) == 1` — energy
  conservation, right-hand side the number 1, no constant of `render.py` in it.
  It pins the *shape* of the series.
- **a 400 000-photon walk** at the file's own `ABS`. A photon enters at the
  refracted angle, crosses to the bed, is redrawn from a cosine law, attenuates
  over its **own** `1/μ`, meets the exact internal Fresnel and either escapes or
  comes back. Nothing in it is an average of anything, which is the only way a
  *correlated* integral can be checked — a second quadrature would have shared the
  premise. It agrees with the closed form to **0.1%**.

Each guard was fired on the bug it was written for, by putting the bug back:

| bug reintroduced | rows that FAIL |
|---|---|
| drop the leading 2 in `2·E₃` | 7 |
| drop the up leg from the numerator | 2 — and **only the walk** sees it at nonzero absorption |
| one-way transmittance where the round trip belongs | 1 — **only the walk** |
| factorise `T_esc` back into `T_diff·(1 − R_int)` | 2 |

The lossless limit alone passes three of those four. That is the same blindness
the old audit had, caught this time before it shipped.

## Closed — the step unit's stripes, and the diagnosis that was wrong

Wave 13 marked `RIS_NT = 512` as the cause of the visible banding on the step unit
in `gauntlet/evidence/w13-underwater.png` — 18.4 mm arc bins, 26 output pixels
wide at 1.2 m, *"striped with the estimator's own noise"*, sized at ≈4×. The hero
was frozen then and it is not now, so the first thing this round did was spend it.

**It is not the cause.** Arc bins 512 → 2048 **and** the gather's directions
240 → 960 — 4× and 4×, both acting on `bnc` and on nothing else — moved the stripe
rms on that frame's own near riser from **1.372 to 1.363** encoded levels. A term
that can be quartered in noise without moving the artefact is not the artefact.

**What it is, measured.** `_riser_shade` now returns its four terms on request,
and they are measured along the outer nosing's own face — arc-scale rms, and the
spread *up* the face at fixed arc. A term with arc structure and **no z structure**
is a vertical comb, which is exactly what the eye was seeing:

| term | share of the face | arc rms | z rms | z/arc |
|---|---|---|---|---|
| direct sun, **before** | 30.8% | 41.1% | 0 by construction | **0** |
| direct sun, after | 50.6% | 62.4% | 58.7% | **0.941** |
| sky ambient | 12.4% | 4.3% | 2.8% | 0.658 |
| TIR return | 1.8% | 0.7% | 0.3% | 0.466 |
| bed bounce | 35.1% | 1.1% | 8.9% | 7.90 |

The caustic pass **drops** the rays that reach a riser — that is the unit's cast
shadow on the floor behind it — so no map is rasterised for these faces and the
bed's map stands in. It stood in at the face's own `(x, y)`, 30 mm radially out,
**with no dependence on height**: whatever the bed's 3 mm-texel pattern was doing
at that one point was smeared up the whole 240 mm of riser. A field with structure
at 3 mm and none at all in `z` is a comb.

**Where the read belongs, derived.** The refracted beam is one direction and flux
is conserved along it, so the point at height `z` is lit by the beam that, had the
face not been there, would have landed at

```
(x, y) + (z − z_foot) · TSUN_DIR_xy / (−TSUN_DIR_z)     — 249 mm of run on the tallest riser
```

which is a function of `z`. Reading there is not a smoothing of the artefact, it
is the removal of its cause; the `ndl / cos_t` beside it — flux per horizontal
area turned into flux per face area — was already right and is unchanged.

**Result: the stripe rms falls 1.372 → 0.816**, the term's z/arc goes from 0 to
0.941, and the face reads as a caustic net running at the beam's own angle instead
of as a comb.

**The cost, stated.** The two resolution changes are **kept** even though they did
not fix the tell, because they fix something else that is measured: the riser
map's cell-scale contrast falls from **11–18%** of the bed's own to **6–12%**, so
about 40% of what it was carrying was the estimator's noise, and the bilinear
read's crease at 26 output pixels was real. They cost the gather **9.2 s → 36.1 s**
(+27 s, **+7%** of a full render) and the maps 4.7 MB. The caustic-read fix costs
one `bed_z` call and two adds per riser sample, and is inside the timing noise.

`?` What is still a proxy: the bed map is focused at each texel's own depth, so
using it at the face's height ignores the focusing over that 0.25 m of run. The
folds move by less than their own width over it. The honest fix is to rasterise a
riser caustic map in the pass itself — `sid == 5` hits carry a cylinder index and
a height already — and that is a pass of its own, filed below.

## Measured — the submerged wall's whole hemisphere, and the ordering that did **not** emerge

The brief was the owner's one visible defect: *the submerged walls are lighter
than the dry liner band above them, on every side*. "Every side" is the
load-bearing word — no azimuth lights all four, so the mechanism cannot be direct
sun — and the ruling that came with it was explicit:

> *"Wat we niet willen is dat de wand onder water lichter wordt, omdat we zeggen
> dat dat zo moet zijn. Het moet komen door natuurkundige effecten."*

So the wall's hemisphere was computed properly — the sky through its **own** cone,
the bed, the opposite walls, and the surface's mirror carried to convergence
rather than truncated at one bounce — and whatever came out was reported. What
came out is this:

| north wall (averted, `cau` = 0.000), scene-linear luminance / dry band | wave 14 | wave 15 |
|---|---|---|
| wall, 0–100 mm below the line (through 11–144 mm of water) | 0.470 | **0.518** |
| wall, 100–250 mm (through 150–391 mm) | 0.581 | **0.616** |
| the dry band itself, absolute | 0.5724 | 0.5721 |
| what the observation requires | > 1 | > 1 |

**The ordering did not emerge.** The gap closed by 10% of itself and the
remaining factor is 1.9. That is the honest result and it is reported as one
rather than closed some other way. Three candidates for that factor are named
and *measured* below — all three on the **band**, none of them a receiver term,
and none of them moved.

**The band did not move, and that is the control.** It is fed by `SKY_DECK` and
`WBOUNCE`, neither of which the solve touches, and it reads 0.5721 against
0.5724 — three parts in ten thousand, which is the frame's own sampling. So the
whole of the change is in the numerator.

### The two halves, attributed separately

**The sky was over-given by ×1.96 and it is now derived.** A submerged vertical
face reaches the sky only through the Snell window, a 48.5° cone about the
**vertical** — the worst placement there is for a vertical receiver. The file
already owned both halves of the closed form:

```
E_vert(hemisphere)/E_bed(hemisphere) = tir_vert(0)              = 0.500
E_vert(cone t>tc)  /E_bed(cone t>tc) = TIR_VERT                 = 0.885
E_bed(cone)        /E_bed(hemisphere)= 1 − 1/n² = TIR_FRAC      = 0.439
=> the WINDOW's share of a vertical face, against the bed's:
   (0.5 − TIR_VERT·TIR_FRAC)·n²                                 = 0.1992
```

`SKY_VERT` ships at **0.2141 / 0.2032 / 0.1916**, not 0.1992, and the difference
is the *sky's own profile* put inside the integral instead of a constant: the
outer window is the air-side **horizon**, `SKY_HOR` is brighter than `SKY_TOP` in
red and green, and a vertical face weights exactly that outer part. The window's
transmission `1 − R_int(t)` is in the same integral, falling to zero at the rim.
What the wall used to get was `WALL_SKY × WAO = 0.5 × 0.78 = 0.390` of the bed's,
so the sky term falls by **2.5×** — `(0.218, 0.352, 0.553)` → `(0.120, 0.184,
0.272)` on the face.

**`WAO`'s `0.78` is gone, and the geometry says why.** It was marked *"the wall's
own sky visibility and has no derivation here"*, and it has none anywhere,
because the occluder it stands for is not there: the coping's bullnose has its
poolward extreme at `s = SLIP` — `ZLIP = ZCEN`, the arc's lowest point, at
`SBUL − BULR = SLIP` — which is the **wall plane itself**, and it recedes from
the pool going up. The stone overhangs the *water* by 20 mm and the *wall face*
by nothing. Worse, the term it multiplied is a cone about the vertical: a texel
`d` below the line sends its window rays out between 0 and `1.13 d` poolward, and
the only ones a zero overhang could catch are within `atan(0.020/(d + 0.12))` of
straight up — 9.5° at the waterline, falling with depth — which is the part of
the window a vertical face weights by `sin²t` and therefore weights least. Both
factors are gone; the wall's sky occlusion is now traced by the same lattice that
traces everything else. What is left unmodelled is **stated** rather than dialled:
the outer window looks at the air-side horizon, and in this scene that holds a
terrace and a house `sky()` does not have. That is section G's standing `?` — *"the
world above the water is `sky()` and nothing else"* — as one `?` in one place
instead of a 0.78 with no owner.

**The mirror was under-given by a factor of nineteen where it can be measured
directly, which is far more than the ×1.21 the closed series predicted.** The old term was the one-bounce shooting splat: the bed's
emission past the critical angle, with the 58% that meets a wall on the way up
*deleted*, splatted onto a coarse grid and then rescaled onto a vertical face by
`TIR_VERT`. Measured on the outer nosing's own face — `_riser_shade` returns its four terms
on request, so the diagnostic cannot drift from the shader — that term carried
**1.8% of a face whose mean was 0.7326**; the traced integral carries **25.0% of a
face whose mean is 1.0195**, i.e. 0.0132 → 0.2549. On the pool wall the mirror
and the far wall together are now `(0.031, 0.305, 0.524)` where `wallret` was of
the same order as `bedret`'s `(0.006, 0.054, 0.082)`.

The two do not cancel, but they very nearly do on the wall: the sky loses 0.168
in green and the mirror gains about 0.24, so the wall's own radiance rises
**+9.5% in green and +15.3% in blue and falls 6.2% in red**. On the risers, whose
sky share was smaller and whose mirror sees the bed at a metre rather than at
four, the same two changes give **+39% on the face**.

### What the return leg turned out to be worth

Filed for four rounds as *not modelled — the return leg, wall → bed*. It is built,
and it is the larger half of what moved:

| the bed's ambient on the deep floor, in the units `shade` calls `amb` | wave 14 | wave 15 |
|---|---|---|
| the window's sky | `(0.248, 0.629, 1.085)` | `(0.225, 0.521, 0.890)` |
| the mirror **and the wall** | `(0.006, 0.054, 0.082)` | `(0.046, 0.426, 0.720)` |
| together | `(0.254, 0.683, 1.167)` | `(0.271, 0.947, 1.610)` |

**+39% in green on the bed's ambient**, and the bed's own radiance rises
`(0.3139, 1.2652, 1.6208) → (0.3179, 1.4181, 1.9190)`, ×1.013 / 1.121 / 1.184.

**And the sky falls, which the file's own older framing did not predict
correctly.** That framing said *"the walls take 35.3% of the bed's hemisphere and
`SKY_AMB` is applied over the whole of it"*. The share is right and the reasoning
needed one more step, because the sky does not arrive over a hemisphere: it
arrives through a 48.5° cone about the vertical, and a wall near the horizon
cannot reach into that cone. What *does* reach into it is the basin's own
aspect ratio — a bed point at 1.40 m sends its window rays out to
`1.40 tan(48.5°) = 1.58 m` of horizontal run, so in an 8 × 4 m basin **87% of the
floor has part of its own window behind a wall**, and the part behind it is the
*outer* window, which a horizontal face weights by `cos t sin t` and therefore
weights most. That is why the sky term falls 17% in green rather than not at all.

`58%` of the trap meeting a wall is no longer a loss either: in a gather those
directions simply *are* wall hits and bring the wall's radiance back.

### What this did to the water/stone ratio, which the last round left level

It did not stay level, and the reason is that the two ~25% errors of opposite
sign that used to cancel no longer do. On the hero frame, transmitted column,
mean over mean, scene-linear:

| water / sunlit stone | wave 14 | wave 15 |
|---|---|---|
| the render | **0.735** | **0.836** |
| the corrected closed form beside it | 0.771 | 0.772 |
| apart | −4.8% | **+8.3%** |

The form is an *infinite basin under a beam alone*. It has no sky, which is worth
+21.5% on this bed, and it had a trap the render was carrying at ×1.0217 of its
×1.2354. Closing the trap removes most of the negative term and leaves the sky
uncancelled, so the render now sits **above** the form by about what the sky is
worth after the wall's absorption is taken out of it. That is arithmetic that was
already written down; what changed is which side of zero it lands on. **It moves
the frame toward what bar section J and the owner ask for** (*"the water is pale,
and it is pale nearly everywhere"*), and it is not a licence: if the sky term on
the bed is itself too large, this is now the place it shows.

### And the trap now closes against its own closed form

The pool's apparent albedo section has priced this every round: the render's trap
arrived at **×1.0217** where the closed geometric series gives **×1.2354**, over
the wrong cone (`1 − 1/n² = 0.4387` rather than `R_int = 0.4762`, i.e. the partial
Fresnel *inside* the window dropped) and at one bounce. All three are gone: the
reflectance is `r_int_at` per direction — the file's own external `fresnel` read
at the conjugate air-side angle, Stokes reversibility, exactly as `uw_interface`
reads it — the walls are emitters as well as receivers, and the solve is iterated.

It does **not** reach ×1.2354 and it should not: that series is an *infinite* basin
with no walls to absorb, and this one loses `(0.754, 0.352, 0.246)` of every
bounce to a liner over a third of a bed point's hemisphere. What it reaches is
printed each run beside both.

### Convergence, and the residual as a bound rather than an assumption

Six passes, each one full transfer in both directions, seeded from the wave-14
maps so that the first increment is the exact size of the defect:

| | bed, mean radiance | wall, mean radiance |
|---|---|---|
| seed (wave 14) | `(0.3139, 1.2652, 1.6208)` | `(0.1912, 0.8877, 1.2658)` |
| pass 1 | `(0.3186, 1.3978, 1.8579)` | `(0.1795, 0.9097, 1.3042)` |
| pass 3 | `(0.3179, 1.4143, 1.9027)` | `(0.1793, 0.9659, 1.4333)` |
| **pass 6** | `(0.3179, 1.4181, 1.9190)` | `(0.1793, 0.9722, 1.4590)` |

The operator's measured gain — the last increment over the one before — is
**0.335 / 0.442** on the bed and **0.378 / 0.475** on the wall (green / blue), so
the geometric tail past the last pass is bounded by `|d| r/(1−r)` = **0.012% and
0.033% of the converged level in green**. That is under the lattice's own
quadrature error, and it is printed rather than asserted. `NSOLVE = 6` is
guarded: `validate.py` runs the same operator for exactly `NSOLVE` passes from
black against the closed series, and at 1 and at 3 passes that row FAILs.

### One thing this round found on the way, and it was not what it was sent for

The file interpolated *both* of these terms **linearly** in the receiver's own
`Nz` — `SKY_AMB · ½(1 + Nz)` for the sky and `TIR_VERT + (1 − TIR_VERT)·Nz` for
the return — on the step risers' rolled nosings. Neither is linear, and the sky's
is not even close. `axial_share` now does the 2-D integral exactly, once, on a
grid in the tilt angle β, and prints it as a multiple of what a *vertical* face
collects:

| β off the vertical | 90° | 68° | 45° | 22° | 0° |
|---|---|---|---|---|---|
| the window's sky, exact | 1.000 | 2.138 | 3.480 | 4.544 | **4.919** |
| the same, as the file wrote it (`1 + cos β`) | 1.000 | 1.383 | 1.707 | 1.924 | **2.000** |
| the mirror, exact | 1.000 | 1.170 | 1.210 | 1.198 | **1.193** |
| the same, as the file wrote it | 1.000 | 1.050 | 1.092 | 1.120 | **1.130** |

A horizontal face collects **1/SKY_VERT = 4.92×** the window sky a vertical one
does, not 2×, because the window is a cone *about the vertical* and a horizontal
face owns the whole of it. `axial_share` is guarded by two rows: on a uniform
field it must give exactly 1 and exactly ½ (so the ratio is exactly 2), and on
the TIR cone it must reproduce `tir_vert(t_c)` — a closed form with an arctangent
in it and no integral at all, reached here by a completely different quadrature.

### What is still missing from the wall's hemisphere, and none of it is a factor of two

The upgoing half closes on 0.500 exactly by construction (a cosine-stratified
lattice) and the downgoing half closes on **0.447 of 0.500**, of which 4.9% is
rays dropped on a riser and 0.4% is the distance truncation. So the wall's
hemisphere is covered to **94.7%**, and the 5.3% that is not is *riser* — a
surface whose radiance is deliberately zero in both gathers, because the riser
map is built from the wall map and a fixed point in that direction is a pass of
its own. What is not in it:

- the **risers' own radiance** in both gathers (4.9% of the lower half, 1.4% of
  the upper) — `bed_wall_src` returns nothing for a riser hit, as it always has,
  because the riser map is built *from* the wall map;
- the **sail's** occlusion of the window;
- the **poolside** in the outer window, the `?` above;
- **waves on the mirror.** The underside is reflected in as the still plane
  `z = 0`. `?` The mirror leg is metres long against a slope rms of 0.053–0.12, so
  what the wave field does to a source that far away is smear it by a few degrees
  inside an integral that is already a hemisphere average — but it is an
  approximation and it is the reason the mirror reads as a lift and not as a
  second caustic net.

### Which term is responsible for the remaining factor, measured

The wall's receiver side is now traced and closed to 94.7% of one hemisphere, so
what is left is **not** a missing receiver term. All three remaining suspects are
on the **band**, all three are now measured, and none of them is moved:

> **All three were moved by the round after this one, by derivation rather than
> by calibration, and the first of them turned out to be misdiagnosed — see the
> illuminant section at the top of this file.** `SKY_DECK`'s aureole term was
> indeed in the wrong place, but the counterfactual below (0.518 → 0.78) does
> not survive: it subtracted one hand constant while keeping another that is
> itself **0.42×** the gradient's own cosine integral. Against the derived
> integral the band's sky half moves by 5% in green, not 34%, and the ratio ends
> at **0.513**.

1. **`SKY_DECK` on an averted vertical face.** The band's sky half is
   `SKY_DECK × 0.50`, and `SKY_DECK = SKY_AMB × 0.30 + SUN_COL × 0.075` is a
   *horizontal-deck* illuminant of which **68% in green** is that second term —
   the aureole and horizon band around a due-west sun. The band on this wall
   faces **south**; its normal has `N·L = −0.061` and `cos(azimuth to the sun) =
   −0.065`, i.e. the sun is behind its own plane. Dropping that term alone — which
   is **not done** — takes the band's irradiance to 66% of what it has and the
   ratio from 0.518 to **0.78**, still short of 1. It is left because `SKY_DECK`
   also lights the coping and the paving, and its calibration reference is a
   photograph this round does not have — the same ruling the `0.30` beside it is
   under, and the same one the `1/n²` round refused to break.
2. **The coping's overhang over the band is zero**, per the section above. The
   closed form for a vertical strip under an infinite ledge of width `w` at height
   `D` is `(α + sin α cos α)/π` with `α = atan(D/w)`, which is exactly 0.50 at
   `w = 0`. A 30 mm overhang would leave this band **94%** of its sky — worth
   about 3% on the ratio, so it is real and it is small. That is a *section*
   question — what `SLIP` means for the liner as against the coping — and it
   belongs with whoever owns the edge profile, not with the lighting.
3. **`WBOUNCE` is 30% high in green and 89% high in red, and the solve is what
   says so.** It is the pool's own upwelling on everything above the water, and
   it is a closed-form guess: `T_OUT_DIFFUSE × 0.74·LINER_TINT × (beam·e^{−a(slant+D)}
   + SKY_AMB × 0.8)`, with an undeclared `0.8` and with the escape *factorised*
   out of the attenuation — which is precisely the error the water/stone section
   above spent a round unpicking, and it is worth 47% in red on its own. The
   render now has a second route to the same quantity that shares no line with
   it: `slab_esc()` — one integral, both factors inside — times the **converged**
   deep floor. It reads `(0.097, 0.648, 0.950)` against `WBOUNCE`'s
   `(0.184, 0.840, 1.025)`, i.e. `(0.53, 0.77, 0.93)`. So the band's water half
   is *over*-given, the ratio above **understates** the wall, and correcting it
   would take 0.518 to about 0.58. **Not moved**, for the same reason as the
   other two: `WBOUNCE` lights the coping, the paving, the bead and the band, its
   blast radius is the whole above-water half, and this round's control is that
   nothing above the waterline moved. It is now measured every run with both
   numbers printed side by side, which it was not before.

**And the `n²` is still the whole price of the observation.** The submerged wall
is an in-water radiance seen from the air, so it takes `out_of_water`; the band
10 cm above it takes nothing. The wall has to be **1.78× brighter than the band
below the surface merely to draw level with it above the surface**, and the two
are one pigment — `tiles` is `0.82 × LINER_TINT` against `liner_band`'s `0.74 ×`
the same, so the wall is the *more* reflective by 11%. Nothing in this round
moved that, and nothing should.

**The path is still not the explanation, and the bins still say so in the wrong
direction.** Binned by the traced water leg the ratio *rises* — 0.306 → 0.422
over 11 mm to 391 mm — because a deeper texel sees more of the bed. The bins read
depth, not absorption; Beer–Lambert over the whole span is worth 0.971–0.995.

## What moved in the picture

The internal field is the light in every submerged pixel, so this round moves
more of the frame than the last two put together: **65.3% of the hero's pixels
moved, mean |Δ| 19.0 levels over those, worst 79**, mean encoded luminance
**132.85 → 140.96**. The underwater frame moves further — **86.5% of pixels, mean
|Δ| 15.9, worst 57, luminance 138.57 → 147.46** — because everything in it is
submerged.

| sRGB median, encoded luminance | wave 14 | wave 15 | why |
|---|---|---|---|
| riser face | (13, 86, 123) · 73.2 · sat 0.89 | **(16, 122, 162) · 102.4 · sat 0.90** | the mirror, ×19 on that face |
| floor, in shadow | (42, 98, 139) · 89.1 | **(42, 109, 156) · 98.1** | the return leg fills what a flat constant could not |
| floor, sunlit | (52, 151, 171) · 131.4 · sat 0.70 | **(53, 161, 184) · 139.7 · sat 0.71** | the trap, now closed |
| tread top | (72, 159, 180) · 142.0 | **(73, 169, 193) · 150.3** | the same |
| water in front of the wall | (66, 152, 174) · 135.3 | **(66, 157, 182) · 139.5** | the floor under it |
| wall, 0–100 mm | (22, 92, 124) · 79.4 · sat 0.82 | **(20, 97, 136) · 83.4 · sat 0.85** | the sky ÷2.5, the mirror up |
| wall, 100–250 mm | (33, 105, 142) · 92.4 | **(30, 109, 152) · 95.3** | the same |
| **freeboard, dry blue band** | **(45, 153, 173) · 131.5** | **(45, 153, 173) · 131.5** | **the control** |
| **coping stone** | **(180, 164, 139) · 165.6** | **(180, 164, 139) · 165.6** | **the control** |

**The band and the stone are the control and they did not move at all** — same
sRGB triple, same encoded luminance to the decimal. Nothing this round touches
can reach above the waterline, and the frame says so rather than the commit
message.

The **direction** is the one bar J and the owner have been asking for
(*"Ik verwacht gewoon licht water"*): every submerged surface is paler and none of
them is less saturated — the sunlit floor goes 0.70 → 0.71 while rising 8 levels,
the shadowed floor 0.70 → 0.73 while rising 9. The level rises *without* the
colour washing out, because the mirror and the return leg both carry the liner's
own tint where a flat blue ambient could not. The shadowed floor rising by more
than the sunlit one, in percent, is the prediction this backlog entry made:
*"caustic interiors on the deep floor come out too dark (nothing fills them from
the side)"*.

**The wide frame moves the same way.** `POOL_WIDE=1`, same code, same constants,
only the camera: water / sunlit stone, transmitted column, mean over mean,
scene-linear goes **0.706 → 0.796** against a closed form of 0.677 on that
geometry. Bar section J's *"the water is pale, and it is pale nearly everywhere"*
is a visual reading and this is not a claim to have met it; it is the direction,
from physics that was missing rather than from a constant.

Archived: `gauntlet/evidence/w15-hero-above.png`, `w15-wall-waterline.png` — the
**same crop of the north waterline in both renders, wave 14 above and wave 15
below**, which is the picture the whole round is about: coping, grey bead, dry
blue band, meniscus line, submerged liner, water — and the top three of those six
are identical between the halves — plus `w15-underwater.png`,
`w15-underwater-risers.png` and `w15-wide.png`. All five are re-rendered from the
shipped file; the wide one is reproducible with `POOL_WIDE=1` and is comparable
with `w12-wide.png` and `w14-wide.png`.

## Closed — the transmitted column now carries its `1/n²`

**Recorded as a known defect for several rounds; closed in the round that also
moved the wall planes.** Kept here in full, because how it survived a suite is
the transferable part.

`water_shade` composed `F(θ_v)·L_sky + (1 − F(θ_v))·L_bed`. `L_bed` comes out of
`shade()` as `albedo × irradiance`, and that irradiance is the beam *already
through the surface*, so `L_bed` is an **in-water** radiance. Radiance is not
conserved across a refracting interface — `L/n²` is, because a pencil's étendue
`n² dA dΩ` is — so what leaves the water is `T(θ_v)·L_bed/n²`, and the `/n²` was
not there. `n² = 1.774 / 1.782 / 1.796` on this file's three IORs; the divisor is
**0.827–0.844 stops**.

It was a **relative** error between the two columns of one pixel: the sky term is
air-side and was right, so the bed read ~1.78× bright against it — which is why no
exposure could ever have absorbed it, and why `EXPOSURE` has not moved.

**Why every Fresnel row passed throughout.** The suite had eleven rows on the
exact Fresnel equations, including one an approximation cannot reach. Not one of
them ever asked what happens to a **radiance**; they all asked what happens to a
**ratio**, and a ratio is exactly where this factor cancels. That is the shape of
the hole, and it is worth more than the fix.

**There is now one place in the file where a radiance leaves the water**, the
function `out_of_water`, and three call sites use it: `water_shade`'s transmitted
column, `_menis_under` (so the fillet's traced column and its flat baseline cross
the same interface, and the reflected/transmitted split stays a partition of
unity in the caller's units — which is what the meniscus closure row rests on),
and the water-out gather, where it cancels and is applied anyway.

### The calibration, and which constants moved

The trap was that `LINER_TINT`, the liner albedos and `EXPOSURE` were fitted
against a photograph **with the bug present**, so they might have been
compensating for it. Bar section B2b is what settles it without a free parameter:
the **dry liner band above the waterline is the same pigment with no water path
at all** — no absorption, no interface, no `n²` anywhere between it and the eye.
It is a direct readout of the liner albedo, and it is printed each run:

| | |
|---|---|
| dry band, radiance / its own irradiance | `(0.271, 0.727, 0.835)` |
| the file's `0.74 × LINER_TINT` | `(0.222, 0.585, 0.681)` |
| chapter 12's mid-blue PVC liner | `(0.24, 0.54, 0.70)` |
| apart | **−7% / +8% / −3%** |

If the pigment had been carrying the missing factor it would have to sit **1.78×**
off a published PVC. It sits inside 8%. **The factor was never in the pigment,
and `LINER_TINT` has not moved. Nor has `EXPOSURE`.** The dry band's own rendered
level confirms it from the other side: it moved by **one sRGB level**, (44,151,172)
to (45,153,173), while the water beside it fell 0.83 stops.

**One constant did move, and it was already the same factor written by hand.**
`WBOUNCE` — the pool's upwelling radiance on the stone at its edge — led with a
bare `0.5`. That number is the *diffuse* form of this transport, `1 − R_int =
(1 − R_ext)/n² = (0.5263, 0.5238, 0.5193)`, which the file already computes for
the wet-liner term. So the file **already had the `1/n²` on one route out of the
surface** — rounded down by 4.5% and with no derivation beside it — while the
camera's route went without: two paths out of the same interface disagreeing by
`n²`, and nothing compared them. `WBOUNCE` now takes `T_OUT_DIFFUSE` and the
number rises 4.8%.

### The guard, which shares no premise with any of it

Three rows, none of which can be written from the shading code:

- **Walsh's relation**, `n²(1 − R_int) = 1 − R_ext`, with **both** sides
  quadratured inside `validate.py` (the internal one the long way, through the
  whole TIR cone). It pins the **exponent**: at `n¹` and `n³` the two sides differ
  by 33% either way.
- **A closed energy audit.** A pool with a perfect white bed and no absorption
  must have an apparent albedo of **exactly 1**, and the right-hand side of that
  row is the number 1 — no constant of `render.py` enters it. Composed through
  `out_of_water` it is 1; composed as the file shipped, **1.723 / 1.730 / 1.742**;
  composed with `1/n` instead of `1/n²`, **1.310**.
- **The same audit off unity against `wet_albedo`**, which reaches the same
  physical quantity by summing a trapped geometric series and is itself already
  guarded against the Egan & Hilgeman fit.

### What it did to the picture

Nothing was compensated. The water column is darker by the factor, and that is
the answer:

| sRGB median | before | after |
|---|---|---|
| open water | (81,192,204) | (56,155,170) |
| floor, sunlit | (74,189,205) | (52,151,171) |
| tread top | (101,196,213) | (72,159,180) |
| riser face | (18,121,163) | (13,86,123) |
| **freeboard, dry blue band** | **(44,151,172)** | **(45,153,173)** |
| coping stone | (153,140,120) | (180,164,139) |

The band is the control and it did not move. The coping's change is a different
defect, below. Mean encoded luminance on the far water runs 152.7 → 131.5 and on
the near water 171.5 → 138.6. The frame reads as a deep saturated blue in a low
sun rather than a pale cyan; measured saturation on the sunlit floor rises 0.64 →
0.70, which is the tone curve rather than the physics.

## Closed — the submerged walls stood 20 mm outside the surface they met

**Recorded as a known defect, closed in the same round as the `1/n²`, because
both of them make the dry-band absorption regression be re-read.**

The water's plan boundary — the vertical face carrying the liner band, the line
the height field cliffs at, the line the meniscus climbs — stands at `s = SLIP =
−0.020`. `scene_hit` put the four submerged walls on the plan rectangle, `s = 0`,
which is the coping's bedding line and not a surface anything can see. Every
refracted camera ray therefore ran 20 mm too far before it met the liner and
landed about 5 mm too low on it, against a wall map whose coping-shade term has a
55 mm scale at the top.

The four planes are now `XW0, XW1, YW0, YW1`, at `s = SLIP`. Two consequences had
to come with them and neither was visible before:

- **A backward root is a miss.** The laid-stone wobble lets a water hit sit up to
  ~7 mm outside the wall plane it belongs to; such a ray travels *away* from that
  plane and never meets it. With the walls on the rectangle the root was zero, so
  it never mattered; with them moved in it is negative, and unguarded it would
  win the `argmin` and trace backwards through the eye.
- **The caustic launch grid spans the rectangle**, whose outer 20 mm is coping
  rather than water, so 1.5% of the sun rays were being launched off stone. Now
  masked on `pool_sdf < SLIP`.

Measured, on the meniscus's own traced column: the fillet's transmitted rays on
the north wall at *x* = 1.40 m used to land between −118.8 and −1.1 mm of the
still line over 29–175 mm of water; they now land between −45.7 and +3.8 mm over
0–67 mm. On the west wall, 20.4–44 mm of water becomes 0–17 mm.

**The guard is two constructions of one surface, and a march.** `scene_hit` does
not call `pool_sdf` and never has, so `validate.py` fires 6000 rays and asserts
every wall hit lands on `pool_sdf == SLIP` to float round-off (on the planes this
shipped with, that row reads 0.020 exactly), that no traced segment leaves the
boundary, and — independently — that a 1 mm march of the bed height field finds
the same first hit to within its own step.

## Closed — the wall map ran out above the still line

`_menis_under` carried a `?`: the fillet's steeper facets aim the transmitted ray
at the wall a millimetre or two **above** `z = 0`, and `sample` clamped that to
the map's top row. The bound is analytic — a refracted camera ray descends
everywhere (`t_z < 0` identically, which is the same algebra that refutes the
underside term), so a ray launched at most `MENIS_H` above the still line can only
land below that. The wall maps now run to `WTOP = MENIS_H = 3.85 mm`, which costs
one texel row out of 340.

The guard marches the fillet's whole transmitted fan — 128 304 wall hits over four
walls, five eye positions and contact angles 0–80° — and asserts the highest of
them is inside the map. It is **two-sided on purpose**: a map that stopped short
fails high, and a bound nothing reaches fails low, which is how a vacuous row is
caught. The march reaches 3.83 mm of the 3.85 mm bound.

## Closed — the near-wall fold is now enforced

`_menis_weights` priced the fold at `|Vm|·h` — at most 3.9 mm of projected area per
metre of waterline, signed negative — and observed that this frame never reaches
it. That was a comment, and a bound that nothing enforces is a comment.
`meniscus` now takes `guard=True` on every path that draws a pixel and **raises**
the moment a selected ray has `Vm < 0`, quoting the unresolved area; `_menis_probe`,
which deliberately walks the east and south waterlines to *report* the bound, is
the one caller that passes `guard=False`. The render prints the worst value each
path actually reached. `validate.py` holds both halves: that a north-wall
configuration renders, and that an east-wall one is refused.

## Closed — stone gets its direct sun back on two sides


`sun_vis` applied `coping_vis` to stone. `coping_vis` is a **water-surface** term —
the run from a water point to the lip, along the sun's azimuth, against the run
needed to clear `ZLIP`. Evaluated on a point that is *on* the stone rather than
under it, its numerator `SLIP − pool_sdf` is negative on every side whose outward
normal has a positive component toward the sun — the north and the west here — so
it returned a flat 0 and those two **copings and their paving** were lit by
`SKY_DECK` alone: no direct sun, no directional shading, no sheen, on stone the sun
is falling on. `liner_band` already sidestepped it through `sail_vis`; `paving` did
not. The owner ruled the *terrace* out of scope; bar section E keeps the **coping**,
so this was filed as *the coping loses its direct sun* and it is that which is
fixed. The terrace gets it back as well, because it is one bug and not two.

Stone now takes `stone_vis`, which is `sail_vis` and nothing else. That is a
claim about the scene, not a convenience: the coping is the highest thing in it
bar the sail, its own arris shades only what is below it (water and band, not
stone), and the far coping's shadow reaches `ZD/tan(21°) = 0.40 m`, which lands
on water on every side.

**The guard is a shadow march of the real height field.** `validate.py` steps
2 mm toward the sun from 672 points on the coping *top* of all four sides, tests
the ray against `edge_z(pool_sdf(·))`, and asserts `stone_vis` matches it exactly.
With the `sun_vis` it used to call, that row reads 1.0 on half the points. The
coping stone's median went (153,140,120) → (180,164,139) sRGB and the near coping
and paving now carry directional relief and the damp-stone sheen instead of
reading flat.

One thing the march found and the fix does **not** cover, recorded rather than
claimed away: on the sun-facing sides the bullnose shades its own foot, over the
lowest ~40% of the roll-over. It is worth nothing — those facets face the pool, so
the sun is behind them and their own `N·L` is negative — but it is real, it is
unmodelled, and a camera on the other side of the pool should not inherit it
silently. It is an `INFO` row.

## Closed — `render.py`'s header quoted an `F0` that follows from nothing

The docstring said `F0 = 0.0197`. The file's three IORs give
`((n−1)/(n+1))² = (0.02027, 0.02056, 0.02111)`; 0.0197 is what `n = 1.3265` would
give, and 1.3265 appears nowhere else. Docstring only — nothing computed from it —
but it is exactly the class this project cleans up: a stated constant that no
longer follows from the code beside it. It now quotes all three, and `validate.py`
already asserts `F0` against `IOR` so the pair cannot drift again in silence.

The file also printed `wrote pool.png` while writing `pool_final.png`, and
`pool_dispersion.png / pool_zoom.png` for `pool_final_dispersion.png /
pool_final_zoom.png`. Same class, one line.

## Open — the `0.30` on every above-water direct-sun term

> **Still open after the illuminant round, and now it is the ONLY thing above
> the water without a derivation — and it is visible.** `SKY_DECK` is derived;
> `WBOUNCE` is closed against the converged floor; the band has its own
> hemisphere. The `0.30` is what is left, and with a properly blue deck
> illuminant beside it the coping renders at saturation **0.05** against 0.23.
> The old `SKY_DECK`'s fake warmth was masking it. `render.py` prints the
> counterfactual — a horizontal coping facet in full sun goes from linear
> saturation 0.193 at `0.30` to **0.430** at `1.00`, with the sky's share of it
> falling from 47% to 21% — and does not apply it. The section below is the
> original finding, kept as written. Two things in it are now superseded: the
> `SKY_DECK` beside this constant is no longer "a derivation in the comment
> above it", and the *"removing it alone takes the ratio from 0.518 to 0.80"* at
> the end of it does not survive the derivation — the aureole was in the wrong
> place, but it was 12.7% of the deck illuminant and not 68%. What has not
> changed is the finding itself: two receivers in one frame get the same beam at
> a ratio of 3.33, with a derivation on one side and nothing on the other.

**Found while closing the six above; not fixed, and the reason matters.**

`_stone` and `liner_band` both write the direct beam as

    SUN_COL * (N·L * vis + ...) * 0.30

while `shade()` — the bed, the walls, the treads — writes it as
`SUN_COL * cos_i * TSUN * cau`, with no such factor. `SUN_COL` is `E/π` by the
file's own stated convention (`validate.py` asserts `E_SUN == π·SUN_COL`), so a
Lambertian facet in this beam has radiance `ρ·SUN_COL·(N·L)` and the stone is
getting **0.30 of it — 1.74 stops under** the same beam that lights the bed at full
strength. `SKY_DECK`'s own `SKY_AMB*0.30 + SUN_COL*0.075` carries a derivation in
the comment above it; this `0.30` carries none anywhere in the file.

It is left open, for three reasons stated rather than assumed:

- It is a **calibration** question, not a physics one, and the calibration
  reference is a photograph this round does not have. Moving it would be exactly
  the compensating move the `1/n²` round refused.
- Its blast radius is the whole above-water half — coping, paving, the freeboard
  band, and the `WBOUNCE`/`SKY_DECK` balance between them — and it is entangled
  with albedos that are themselves marked as visual readings (`?` on the
  sandstone, `?` on the bead).
- **The frame just changed underneath it, twice.** The water column fell 0.83
  stops and the north and west copings gained their direct sun, so the
  stone-to-water balance this constant was presumably dialled against has moved by
  more than the constant is worth. Whoever holds the photograph should look at it
  next, with the new frame, and not before.

What is not in doubt is that two receivers in one frame are being given the same
beam at a ratio of 3.33 with a derivation on one side and nothing on the other.

**The bed-onto-wall round moved the other side of this pair, and the direction
matters.** The `0.30` sits on the dry freeboard band; the wall gather sits on the
liner immediately below it, the *same sheet* seen through one water path. In the
picture the band did not move at all (131.5 in encoded luminance, unchanged to
the decimal) and the submerged liner under it went 77.1 → 79.4, so the gap the
photograph says is the wrong way round closed by 2.3 levels of 54. **The `0.30`
now has a same-material partner one centimetre away, measured every run.** If it
is too low, the band is *under*-lit and the closing this round achieved is an
underestimate of what a correct band would show; if it is right, the remaining
gap is a receiver problem and not a calibration one. That is a sharper handle
than the stone-to-water balance the constant was presumably dialled against —
same pigment, same frame, one path apart — and it did not exist before this
round. The constant still has no derivation and this round did not move it.

**And the round after it found that on the wall the observation actually pins,
`0.30` multiplies nothing — but its neighbour does.** The north wall's poolward
normal has `N·L = −0.061`, clipped to zero, so on the *averted* wall the band's
direct-beam term is absent and the `0.30` cannot be the reason the ratio is
short. What lights the band there is `SKY_DECK × 0.50 + WBOUNCE × 0.50`, and
**68% of `SKY_DECK` in green is `SUN_COL × 0.075`** — the aureole and horizon band
around a due-west sun, applied at half strength to a *south*-facing vertical strip
whose plane the sun is behind. That is the same class of error as the `0.30`, one
constant along, and it is bigger: removing it alone takes the band's irradiance to
65% of what it has and the wall/band ratio from 0.518 to 0.80. **Not moved, for the
same three reasons**, and now with a number on it. `SKY_DECK` is a horizontal-deck
illuminant and it is being asked to light a vertical face; whoever holds the
photograph should look at *both* halves of it.

## Closed — the camera is now under the water

    POOL_UNDERWATER=1 python3 render.py     # also writes pool_under.png

**Built this round.** It was the largest single inversion left in the model —
everything else is a view *into* the medium, this is a view *from inside* it —
and it is the last unrendered section of the bar (`gauntlet/bar/photo-spec.md`
section G). The numbers below were computed from the constants already in
`render.py` before it was built; what follows each of them now is what the frame
actually produced.

The pass is guarded by an environment variable and sits after the hero frame is
encoded and written, so `pool_final.png` is **bit-identical** with the switch
off — hashed either side of the change (`edfa13ae…`, unchanged). Two things
above the line moved, both factorings and neither arithmetic: the map lookup was
lifted out of `_menis_under` into `submerged_radiance`, so both cameras read the
bed, wall and riser maps through one function, and the in-scatter pair was named
(`INSCAT`, `INSCAT_K`). That sharing is the whole basis of the section's claim
that it is the **same water**: the mirrored twin at the waterline is the hero's
own wall buffer, read by the hero's own `scene_hit`, from the other side.

- **Snell's window.** The above-water world compresses into a cone of half angle
  `asin(1/n)` overhead — 48.5 deg green, 97 deg across. Outside that cone the
  surface is a **perfect mirror**: reflectance exactly 1 beyond the critical
  angle, so the camera sees the bed, the walls and the step unit folded back
  down. There is no partial regime out there.
  **Measured off the frame, flat water: 48.6560 / 48.5108 / 48.2729 deg**
  against `asin(1/n)` = 48.6554 / 48.5074 / 48.2618. The residual is not error:
  it is the **band integral**. A channel is a band, so nine wavelength strata
  refract at nine indices and the rendered rim is the mean of `asin(1/n(λ))`,
  which by convexity sits above `asin(1/n(λ̄))` — by 0.0006 deg in red, 0.0034 in
  green and 0.0110 in blue, in exactly the ratio of the three bands' `dn`
  (0.00239 / 0.00382 / 0.00670). The rim is a **band-averaged** critical angle,
  and the widest band is the one that shows it.
- **The rim is reached through `refract()`'s null return and `is_tir()`**, never
  through an angle comparison, and the assert at `water_shade`'s refraction —
  `the camera is above the water` — is the one this pass flips. `uw_interface`
  gets its reflectance from the file's own external `fresnel` evaluated at the
  **conjugate air-side angle**, which is Stokes reversibility and the same
  identity the wet liner already uses for `R_INT`. So the transmitted column
  fades to zero exactly where the square root changes sign, out of two
  computations that share no line. **Measured: R reaches 0.9983 on the last
  transmitting ray and exceeds 0.99 over the final 0.098 deg.** `validate.py`
  bisects the two against each other for all three bands and they agree to
  1e-4 deg, which is the scan's own grid.
- **The rim is dispersive.** With `IOR = 1.3320 / 1.3348 / 1.3400`, the critical
  angle runs 48.655 / 48.519 / 48.268 deg — a **0.39 deg** spread, red rim
  outside blue. **Measured off the frame: 0.3832 deg on flat water** (the 0.0041
  deficit is the band-integral bias above, which is largest in blue), **0.3873
  deg closed form.**
- **The sun sits just inside the rim.** 21.0 deg elevation is 69.0 deg from
  vertical in air, refracting to **44.4 deg** below the surface — only **4.1 deg**
  inside the window's edge. **Measured: the 2225 subsamples that blow an output
  pixel on their own have a median polar angle of 44.41 deg, i.e. 4.11 deg
  inside the green rim, against 4.15 deg closed form.** They are spread over
  42.6–45.8 deg, which is the wave field smearing the disc, not the disc.
- **Absorption becomes aerial perspective**, and measuring it off the frame
  needed a better instrument than the obvious one. `render.py` uses Pope & Fry
  (1997) averaged over its own channel bands, `a = (0.2617, 0.05299, 0.01022)/m`;
  red transmission runs 0.594 at this frame's median geometry distance (1.99 m)
  and 0.156 at its longest (7.10 m), so the frame goes cyan with distance as the
  chapter's numbers require.
  **The obvious instrument does not work, and the size of its failure is itself
  the finding.** Binning every floor hit by distance and watching the colour
  drift measures the *pool*, not the water: the bed's own radiance varies in
  colour across the basin — the bed-return map, the sky view factor, the sail's
  shadow swapping a golden illuminant for a blue one, the caustics — and one
  frame cannot separate that from the path. Restricted to sunlit open floor a
  metre off every wall it still lands **+13.2%** off `-(a_R - a_G)`.
  **The clean instrument is in the same frame, and it is the mirror.** Outside
  the window the surface reflects 1, so a floor texel is seen **twice** — once
  directly and once folded down off the underside — at two path lengths, same
  pigment, same light. Every confound cancels inside the pair. Binned on an 8 cm
  grid, **804 texels are seen both ways with their two paths at least 0.40 m
  apart, and they give `d ln(R/G)/ds = −0.19643 /m` against `−(a_R − a_G) =
  −0.20871` (−5.9%, inter-quartile −0.200 to −0.191) and `d ln(B/G)/ds =
  +0.04160` against `+0.04277` (−2.7%).** That the mirror is what makes
  Beer–Lambert measurable on a view leg is a consequence of the window, not a
  trick: it is the only way one frame contains the same surface at two ranges.
- **`b_b ~ 0` got its test here**, and it is what is left in that −5.9%. The
  residual in-scatter, hoisted out of `water_shade` and integrated as the broken
  path it is (eye → surface, then the reflected share through a second leg), is
  a source rather than a pigment: it does not attenuate, so it lifts the longer
  reading of each pair and *reduces* the apparent attenuation. `?` The sign and
  the order are right — a rough accounting gives about +0.02 /m against the
  measured +0.012 /m deficit — but the residual was not decomposed exactly.
- **The mirrored twin came free**, which was the point. Nothing in the pass
  mentions the waterline. Outside the window `R` is 1, the reflected ray is
  traced by the **existing downgoing `scene_hit`** from the surface point, and
  the wall's image folds down because the wall is where it is. **Measured on
  three stations of the north wall — the stretches the step unit and the bench
  lobe do not stand in front of — the image and the wall agree to 3% in green
  and blue, and the largest one-pixel step across the line is 5–10 sRGB levels,
  which is the wave wobble at the line and not a seam.** The tile grout lines
  run through the join and come back mirrored.
- **Real time:** the window is `refract` plus a Fresnel term and the mirror side
  is the existing reflection path. The pass costs **30 s** on top of the hero's
  own render at the same 2400 × 3600 × 3² — no path tracer, and cheaper than the
  hero's camera pass because the mirror leg is achromatic and needs one trace
  for three channels.

### The camera, and the one number in it that is a choice

Held to the standard of the `CAM_AZ` block. The eye is at **(6.60, 1.40, −0.70)**
looking at azimuth 145 deg, elevation +22 deg, through a **16 mm** lens on the
same 3:2 portrait frame the hero uses.

- **The lens is section H's**, the reference for the submerged half of an
  over-under. 16 mm on 36 × 24 mm gives 96.73 deg on the long axis — and the
  window is 2 asin(1/n) = **97.04 deg** across, so *the reference lens for this
  kind of frame is 0.31 deg too narrow to hold the thing the frame is about*.
  That near-miss is recorded rather than fixed.
- **It is not pointed at the zenith, and that is forced.** Holding the whole
  window *and* anything below the horizontal needs a half-field of at least
  90 deg, which no rectilinear projection has. The window's centre is the least
  compressed and least dispersive part of it and carries no test; the rim, the
  sun crowded against it, the twin, the step unit and the aerial perspective are
  all in the outer half or below it. So the aim tilts down and the centre goes
  out of shot at v = +2.4.
- **The port is a dome**, stated because a camera in water has one. A concentric
  dome is afocal for rays through its centre of curvature, so the in-water field
  is the lens's native one and no magnification enters. A flat port would narrow
  96.73 deg to 67.9 deg and magnify by `n` — a real and visible different
  choice, and section H is where it is tested.
- **`EXPOSURE` does not move.** A radiance in this frame and a radiance in the
  hero are the same number of stops, which is what makes the two comparable and
  is the one thing section H says may never be fudged between halves.
- **The depth is the only free number**, and it is bounded on one side: the rim
  lands at `d tan(theta_c) = 1.134 d` from the eye's vertical, so an unclipped
  window needs `d < 1.234 m` here. `? 0.70 m` is taken — half the basin's
  deepest depth, the eye equidistant from surface and bed, the rim clearing the
  nearest wall by 43%. It is marked `?` and its consequences are printed rather
  than assumed.

### What the view found, which is why it was built

Section G calls the submerged view the strongest verification instrument in the
project, on the grounds that every above-water shortcut that survives by being
invisible from a 33 deg downward view becomes visible from underneath. It did.

- **`riser_bounce`'s map is visibly banded at 1.2 m.** `RIS_NT = 512` arc
  samples per cylinder is 18.4 mm on the outer nosing; from this eye that is
  **26 output pixels wide**, and the map's bin-to-bin Monte-Carlo variation
  reads as hard vertical stripes over the whole step unit, with the bilinear
  interpolation's ridges visible as creases. From the hero's 3.4 m the same unit
  is 130 px tall and the same bins are under a pixel each, which is why six
  waves of work never saw it. **The bench lobe shows the same estimator as
  speckle** rather than stripes, because its face is more nearly normal to this
  view. Both are the *estimator's own noise*, made visible by a 3× closer look
  at the same buffer.
  **Not fixed, deliberately.** Raising `RIS_NT` or the gather's 240 directions
  changes the hero frame, and the hero frame is the bit-identity contract this
  round was built under. It is recorded here as the next round's work, with the
  number that sizes it: the map needs about 4× the arc resolution before its
  bins fall under an output pixel at 1.2 m.
- **The rim is not a hard edge, and it is not a step.** Section G calls it "the
  hardest edge in the scene". It is continuous in radiance: `R → 1` like
  `sqrt(theta_c - theta)`, so the transmitted column *fades* rather than being
  cut, and what is discontinuous there is the derivative. On top of that, the
  wave field smears it: **the 10–90 width of the rim's own crossing is 6.1–6.3
  deg**, because this eye sits 0.9 m from the jet's boil where the resolved
  slope rms is 0.076 (4.4 deg of normal tilt). The rim in this frame is a
  wrinkled band six degrees wide whose *mean* is `asin(1/n)` to 0.005 deg. That
  is a reading of the wave field from a third direction, and it is the one the
  split shot (section H) will want.
- **The window's brightest part is not its rim.** Section G's weaker,
  recollection-tier criterion says "the window's rim is the brightest thing in
  frame". Measured by polar angle, the window's median radiance runs 1.320
  (22–30 deg) → 1.485 (30–38) → **1.577 (38–44)** → 1.464 (44–47) → 1.312
  (47–48.5). The peak is **4–10 deg inside the rim**, because `(1 - R)` falls
  faster near the edge than the compressed horizon sky brightens, and the last
  degree of the window is *darker* than its middle. The brightest individual
  pixels in the frame are the sun (p99 2.58 at 44–47 deg) and the caustics seen
  in the mirror (p99 4.56 at 50–56 deg), not the rim. **This is a disagreement
  with the bar**, and it is filed as one: the criterion is marked *recollection
  of photographs in general*, and what the physics gives instead is a bright
  window (median 1.3–1.6) against dark geometry (median 0.396) with its peak
  inside the rim rather than on it.
- **The world above the water is `sky()` and nothing else.** A refracted ray
  leaving at `theta_a` near 90 deg points at the coping, the deck and the shade
  sail and gets sky. **Measured: that band is the outermost 0.205 deg of the
  window at `(1 - R) < 0.30`, and 0.107 deg at `(1 - R) < 0.10`** — so it is
  thin and weighted down, but it is a `?` and it is the reason the very rim
  reads as a soft blue line rather than as a ring of compressed poolside.
- **The unresolved slope variance feeds nothing here.** On the hero it becomes
  the reflection ellipse and the Bruneton masking term; the refracted lobe has
  no equivalent. **Measured: the surface is 0.74–7.08 m from this eye, the
  output pixel's footprint on it is 1.5–133 mm (median 2.9) against a 28 mm
  dominant wind wave, and the unresolved slope rms left over is 0.0108 — 0.6 deg
  of normal tilt.** Small, but `?` rather than zero, and near the rim the
  refraction amplifies it by `n cos(theta_w)/cos(theta_a)`, which diverges.
- **The mirror is a measuring instrument, not only a picture.** A frame taken
  from inside the medium contains the same floor texel at two ranges, and that
  is what makes Beer–Lambert on a *view* leg measurable at all. It was found by
  the naive measurement failing, and it is the sharpest new number this round
  produced (−5.9% and −2.7% against the two closed forms, on 804 texel pairs).
  Nothing above the water can do this: from above, every bed point is seen once.
- **`scene_hit` is downgoing-only, and now has a sibling.** `scene_hit_under`
  handles either sign of `tz`, adds the still surface as id 6, and generalises
  the cylinder entry to the ascending case. A sibling rather than an extension
  because extending would have put a new id into a function five call sites read
  positionally; `validate.py` fires both at the same 120 000 downgoing rays and
  asserts they agree **bit for bit**, and marches the upgoing half against a
  0.5 mm walk of the water body.

### The rows it added — 19, and what each pair does not share

`validate.py` was **215 pass, 0 FAIL, 43 info** at the end of that round (240 / 0
/ 48 now). The new rows are built to
the rule the `TIR_VERT` failure produced: *a test and the code it checks must not
share a premise*, and neither may two tests of the same number.

- **The window's half angle, off the frame's own geometry** (tier 1, three
  rows). The camera's own ray directions, flat water, through `uw_interface` —
  i.e. through `refract` and `is_tir`. The rim is bracketed between the steepest
  ray that still transmitted and the shallowest that did not, and `asin(1/n)`
  must lie inside. **The tolerance *is* the bracket** — the frame's angular
  sampling, 1.1e-4 deg — so it is not a free parameter and it shrinks if the
  frame is rendered finer. Plus the dispersive spread as a fourth row.
- **The onset of the mirror regime** (tier 1, three rows). A bisection on the
  pass's own null return against a 4 M-point scan of the exact water→air
  reflectance reaching 1. One solves for `cos t` and tests its sign; the other
  forms amplitude ratios. Neither contains `asin(1/n)`. They agree to 1e-4 deg,
  the scan's grid, in all three bands.
- **The mirror is total** (tier 1): every ray `is_tir` flags carries `R = 1`
  identically, no tolerance. Section G's "there is no partial regime out there",
  as an assertion.
- **Stokes reversibility** (tier 1): the shipped path — render.py's *external*
  `fresnel` read at the conjugate angle — against the water→air equations formed
  in `validate.py` from the two indices. 4e-14 over 20 001 angles. This is what
  buys the file having only one Fresnel implementation.
- **The `n²` radiance gain** (tier 1, three rows plus two identities). A uniform
  sky on flat water, and the transmitted irradiance counted twice: on the water
  side through the shipped `uw_interface` and `into_water` over the **window
  alone**, and on the air side through `validate.py`'s own `fresnel_exact` over
  the **whole hemisphere**. They are equal only for the square — at `n¹` the
  water side reads 0.75 of the air side and at `n³` 1.33 — so this is the first
  row in the suite that tests the *gaining* direction of `L/n²`, and it fails as
  loudly for a wrong exponent as for a missing factor. Plus
  `into_water(out_of_water(L)) == L` and `into_water(1) == n²` at one ulp.
- **The sibling tracer** (tier 1 × 2, tier 3 × 1): exact agreement with
  `scene_hit` on the downgoing half from two starting heights, and the p99.9 of
  a 0.5 mm march of the water body on the upgoing half against half a march
  step. The p100 is not used, and the row says why: a ray tangent to a riser at
  exactly the cap height is a measure-zero disagreement between two exact
  solids, and one ray in 36 000 finds one.
- **The eye** (tier 1 × 2): inside the water body, and `d tan(theta_c)` under
  the distance to the nearest wall, which is the one condition the depth is
  chosen against.

One caution about what these rows do *not* cover, in the spirit of the file's
own epilogue: **none of them renders a pixel.** They measure the rim off the
frame's ray *directions* and the interface off closed forms; what is checked
inside `render.py` itself, every underwater run, is the rim, the sun's position,
the twin's continuity and the absorption fit, each printed with the closed form
beside it. The mirror leg's *radiance* — that the twin reads the right wall map
at the right place — is still only checked by the frame's own twin measurement,
which is a consistency argument and not an external one.

## Closed — the walls now stand in the bed's light

**The defect.** `shade()` gave every submerged receiver exactly two terms: the
refracted sun times its caustic, and `SKY_AMB × ao` — a flat blue constant
applied over the *whole* hemisphere. For the pool walls that omits the largest
source they have. A vertical face beside a sunlit floor sees that floor across
the entire downgoing half of its hemisphere; the sky it was being given there
does not exist, because below the horizontal there is no sky, there is a floor.

**The estimator already existed, and is now shared rather than copied.**
`_riser_shade`'s gather was built in wave 3 for exactly this geometry and took
the step risers from saturation 0.16 to 0.89. It is now `bounce_gather`, called
by the risers *and* the four walls with the same lattice, the same closed-form
weight and the same closure, so the two receivers cannot drift apart. What is
per-receiver is only the grid, the outward normal, and where the foot is read
from — `bed_z` just outside the cylinder, or just inside the wall face.

**Nothing in it is fitted.** The round introduces exactly three numbers: the
partition `WALL_SKY = 0.5`, which is derived and asserted twice against unrelated
code, and the two grid resolutions `WB_NU, WB_NZ`, which are marked `?` and
cannot change the term's size — the estimator's weight integrates to the same
closure at any sample count. Every level in the result comes from radiances the
file already computed. The two judgement calls that were made after seeing a
number both moved the result **away** from the expected one and were kept:
excluding the buried texels took the printed reciprocity from +7.8% to −12.1%,
and splitting the wall band at 100 mm took the measured strip from 89.2 to 79.4.

**It was not a parameter change.** Four things had to be built around it:

- **The sky had to come out.** A face that gains the gather without losing the
  sky it stood in for is brighter by the whole of the new term instead of by the
  difference. `WALL_SKY = 0.5` — the upgoing half, the same ½ that
  `_ris_closure(h, 0, ∞)` and `tir_vert(0)` return — and `validate.py` asserts
  the two halves sum to one hemisphere.
- **The wall map has to be built twice.** A gather ray that crosses the basin
  lands on the far *wall*, whose radiance does not exist until the pass has run.
  First pass: the wall with its halved sky and its TIR return, no bounce. Second
  pass: the shipped map. What that truncates is exactly one bounce over the ~10%
  of the hemisphere that is another wall, and the share is printed.
- **The coping's overhang now shades only what it can shade.** `WAO` multiplies
  the sky term alone, which is a claim with content: an overhang at the top of a
  wall occludes the upgoing half and cannot occlude the floor. The largest
  relative change in the whole round is in the first centimetres under the lip,
  where the sky was halved *and* shaded and the bounce is neither.
- **Texels buried behind the step unit** get their ray origin lifted onto their
  own foot, so the map stays finite there; the unreachable liner is excluded
  from every wall statistic rather than averaged into it.

**What it delivers.** On the 28.3 m² of wetted wall the gather closes on 0.457
of the 0.500 a vertical face has by geometry (0.346 bed, 0.110 wall, 5.0%
dropped on risers) and adds `(0.077, 0.417, 0.584)` of irradiance against
`(0.279, 0.451, 0.710)` of sky on the same face — comparable in blue and green,
a quarter in red, because the bed's light crosses metres of water to reach a
wall. It carries **12–16% of the bed's own cell-scale contrast**, the same
11–17% the risers carry, so the wall shows the caustic net moving on it and not
a uniform lift.

**And the bed's shadows arrive as shadows.** The gather reads `bed_img` at each
traced hit, never an average, so structure of every scale is in it; what a
hemisphere integral does is low-pass it at a width equal to the height above the
foot. The sail's shadow lands on the floor at the east end, so the run reads it
off the east wall: 36 mm above the floor the wall's bounce is **6.29×** brighter
under the sun than under the shadow, where the bed itself runs **7.53×** — the
wall keeps **91%** of the shadow's depth in log terms. The closed form says why
that number is a function of height: at 36 mm up, 91% of the face's own
half-hemisphere is bed inside 300 mm, so an edge arrives as an edge; at 1.40 m
up only 9% is inside a metre, so the same edge arrives as a two-metre gradient.

**The conservation identity that guards it.** The bed → wall transfer is checked
against the exact rectangle view factor the file has printed since wave 5 — the
same 35.3% — through reciprocity, `A_bed·F(bed→wall) = A_wall·F(wall→bed)`. The
left side is Hottel's closed form over the floor; the right is 240 traced rays
per texel with a closed-form Jacobian, run with a unit radiance and an empty
box. They share nothing but the pool's dimensions, and they meet to **3.1%**
against the lattice's own 3.0% quadrature error at these heights.

**What it does not deliver, and the inequality that says it cannot.** The
photographs show the submerged wall lighter than both the dry band over it and
the water in front of it. This term does not produce that ordering on the wall
this frame can see, and no version of it could:

> A Lambertian floor's radiance does not depend on where it is viewed from, so a
> wall does not "catch" its light and "turn it toward the eye" — it re-emits what
> it absorbs, over half a hemisphere. `E_bounce ≤ ½·L_floor`, hence the bounce's
> own contribution is at most `½·alb_wall·L_floor` — **0.12 / 0.32 / 0.38** of
> the floor's radiance for this liner. The gather delivers **0.77 / 0.83 / 0.87**
> of that ceiling. There is no headroom left in the term.

The ordering in the photographs is a **directly lit** wall against shaded water,
and the render produces it — on the east wall, which carries the refracted sun
at `cau = 0.92` and reads **2.63 / 1.63 / 1.39 ×** the deep floor's radiance.
This frame is anti-solar and looks along the *north* wall, the one wall of four
the refracted sun never reaches (`cau = 0.000`, and it reads 0.34 / 0.57 / 0.72
of the same floor). That is a fact about which wall is in shot, and the run
prints all four so it can be read rather than argued.

**In the picture, measured the same way before and after** (sRGB medians on the
north wall west of the step unit, with encoded luminance):

| region | before | after |
|---|---|---|
| dry blue band, above the waterline | (45, 153, 173) · **131.5** | (45, 153, 173) · **131.5** |
| submerged wall, first 100 mm under the line | (26, 88, 120) · **77.1** | (22, 92, 124) · **79.4** |
| submerged wall, 100–250 mm down | (37, 103, 141) · **91.7** | (33, 106, 144) · **93.2** |
| open water 0.2–0.8 m out from that wall | (66, 152, 174) · **135.3** | (66, 152, 174) · **135.3** |

The wall gained 2.3 levels and **lost 15% of its red while gaining 5% of its
green** — saturation 0.78 → 0.82 — which is the term doing what it does on the
risers: moving the colour more than the level. The ordering the photographs
assert is not reached, and the inequality above says why. A third of that pixel
is reflected sky (38% → 35%), which no receiver term touches.

**The ordering is a prediction this mechanism makes, not a specification it was
built to meet**, and it is worth being explicit that it was not reached and was
not reached for. Every number above moved because a term that was physically
absent is now present; none moved because anything was tuned. If the reader
wants the ordering, the two places to look are the `0.30` open below — the dry
band's own calibration, which is the *other* side of the pair and has no
derivation — and the return leg, not this gather, which is at 0.77–0.87 of the
ceiling arithmetic allows it.

> **The next round took the return leg and the answer is in the section above.**
> It was worth +39% on the bed's ambient and +9.5% in green on the wall, and the
> ordering still did not emerge: 0.470 → 0.518 against the > 1 the observation
> requires. The `0.30` — or rather the `SKY_DECK` that sits beside it on the same
> band — is now the *measured* remaining suspect, worth a further 0.518 → 0.80 if
> it were moved, which it was not.
>
> **And the round after THAT moved it, by deriving it, and the 0.80 was wrong.**
> `SKY_DECK` is now the cosine integral of the file's own `sky()` minus the sun's
> disc; the band has its own hemisphere at its own azimuth; `WBOUNCE` is closed
> against the converged floor. The ratio ends at **0.513**, because the old
> constant was two errors that cancelled in green rather than one that did not.
> The remaining suspect is `SKY_AMB`, which the same integral prices at **1.34×**
> its derived value — and that one moves the *wall*, not the band.

**Everything else that moved, and why.** Three things read the wall maps, so
three things moved, and each is the wall map arriving somewhere rather than a
second change:

- The **meniscus line** brightened most of all — its transmitted column looks at
  that wall a few millimetres under the waterline, which is exactly where the
  coping's shade was halving the sky and never touched the bounce. The fillet's
  share of the first water pixel runs 0.40 → 0.64 at the near end of the north
  wall, and the water beside it 0.32 → 0.44.
- The **risers** brightened slightly (encoded luminance 73.2 → 73.9): a third of
  their own gather lands on a wall, and the walls are now brighter. Their
  cell-scale contrast is unchanged at 10–17%.
- The **deck and freeboard gathers** read `wall_img` through `_gather`, so the
  band's own irradiance moved in the third decimal.

The bed, the floor, the coping stone, the sail shadow and the sunlit-floor /
dry-band absorption regression are **identical to the digit**. Nothing was
rebalanced to accommodate the change.

## Not modelled yet — a caustic map for the risers

`_riser_shade` reads the **bed's** caustic map as a stand-in for the caustic on a
vertical face, because the caustic pass drops the rays that reach a riser. The
read is now in the right place — the refracted beam's continuation to the face's
own foot, which is a function of height and therefore not a comb — but it is still
a proxy, and it is **36.4%** of that face's light — down from 50.6%, not because
the caustic changed but because the mirror beside it grew by a factor of eight
when the return leg was built.

**Not taken this round, and the reason is the brief's own.** It was in scope *"if
the return leg makes it cheap"*, and it does not: the return leg's machinery is a
receiver-side **gather** over a hemisphere, and a riser caustic map is an
emitter-side **splat** in the caustic pass. They share the cylinder index and
nothing else — not the pass, not the estimator, not the kernel, not the texel
area. Building it would have been a second wave's worth of work displacing the
first, so it stays filed exactly as written below.

What it costs to do properly is one more map in the pass that already exists.
`box_hit` returns `sid == 5` with a cylinder index, and the splat needs
`(arc, height)` and a per-texel area instead of `(x, y)` and `bt`. The two things
to get right are both already solved for the bed: the texel area on a cylinder is
`R·dθ·dz`, and the density estimate needs the same `sig_at` kernel, because the
riser strip is about 2.7 m² catching perhaps 6% of the launch — roughly 34 rays
per 4.6 × 10 mm texel against the bed's 9, so the noise is comparable and so is
the smoothing that answers it. Doing it removes the last `?` on the step unit and
deletes the `ndl / cos_t` projection with it, since the arriving density would
then be measured on the face rather than converted onto it.

## Closed — the return leg, wall → bed, and the mirror with it

Filed here for four rounds as *not modelled*, with one blocker named: **wall → bed
needs an up-going intersector `scene_hit` is not**, and what replaces `SKY_AMB`
over the 35.3% of the bed's hemisphere that is wall has to be *directional*,
because the wall runs `(0.335, 0.920, 1.186)` at the waterline to
`(0.125, 0.759, 1.131)` at its foot.

**Both are now done, and it is one pass rather than two.** `scene_hit_under` —
built for the underwater camera, and moved four hundred lines up the file with
nothing in it changed — is the tracer; `up_gather` is the receiver side. The
integral is the upgoing half of any submerged face's hemisphere:

```
E_up/pi = (1/pi) INT_{w.n > 0, w_z > 0} L(w) cos(w.n) dw
```

with `L(w)` found by tracing: a solid before the surface returns its own map
(**that is the return leg**); the surface returns `(1 − R_int(t))` of the window's
sky plus `R_int(t)` of whatever the *reflected* ray finds (**that is the mirror**),
with the exact internal Fresnel per direction and no cone approximation anywhere.
The same function serves the bed, the four walls and the step risers, so the file
cannot hold two opinions about what is over a submerged face.

The section above reports what it delivered and what it did not. The three
symptoms this backlog entry predicted were right in sign and mixed in size:

| the prediction | what it turned out to be |
|---|---|
| the flat `SKY_AMB` over the wall share is wrong, by `_WSH·(L_wall − SKY_AMB·e^{−ad·1.55})` = `(−0.048, +0.059, +0.025)` | the traced answer over the whole bed is `(0.050, 0.437, 0.727)`, which also carries the mirror. The prediction used a mean wall against a mean share; the gather uses the wall each texel can see |
| *"caustic interiors on the deep floor come out too dark and the sail's shadow too bright — one missing mechanism, two symptoms"* | the bed's ambient rises 39% in green, and the sail's shadow on the east wall now arrives at **92%** of its own depth against 91% |
| *"the submerged wall reads 0.47 of the dry band where the owner's observation puts it over 1"* | **0.518**, and **0.513** after the round that derived the band's own illuminant. The receiver is complete, the source is derived, and the ordering still does not emerge |

**The cost, measured.** Six passes in **274 s** — the bed on a 200 × 100 lattice
× 576 directions, the four walls on 144 × 24 × 576, plus six downgoing wall
gathers — and the riser upper half at 4 × 256 × 12 × 576 in 7.7 s, run once
because a riser is a consumer and not an emitter. A full render goes from
**9m28s to 12m12s, +29%.**

**What is *still* not modelled here is one thing and it is named:** the wave
field on the mirror. `up_gather` reflects in the still plane `z = 0`.

## The meniscus, and the one term of it that was refuted

The waterline against a wall carries a thin bright line in every reference frame,
and the mechanism is certain rather than incidental. The static 2-D meniscus on a
vertical wall is `z = 2a·sin(φ/2)` with the capillary length `a = √(σ/ρg) =
2.72 mm`, so the water climbs `a√(2(1−sin θ_c))` — 3.85 mm at perfect wetting — and
the fillet decays over a couple of capillary lengths. Across those ~5 mm the tilt
runs continuously from 0 to 90°−θ_c, so the strip contains **every** facet
orientation.

Three transport terms were proposed for it. **Two are built and one is refuted.**

1. **External specular.** The facets mirror sky and sun to the eye. Fresnel is
   0.02–0.07 where this camera sees them, which is why it is faint. Its
   reachability rule needs the sun poolward of the wall's plane *and* the
   half-vector residual to pass through zero somewhere visible; on this frame the
   sun's branch is reachable only on the east wall and hidden there behind the
   near coping's arris, so what shows is the horizon's branch.
2. **Refraction through the fillet.** A facet turned toward the eye passes
   0.93–0.98 of what is behind it, so this column starts 15–50× ahead. It is
   **traced**, not looked up: on the north and west walls all 64 facets land on
   that wall's own liner, 1–119 mm under the waterline. It runs 2× the reflected
   column at the far end of the north wall and **70× at the near end**, which is
   what turns a bright patch that faded to nothing into a line along the whole
   wall.
3. **Total internal reflection off the fillet's underside — refuted.** Past 48.5°
   that underside is a perfect mirror, and the fillet holds every tilt, so the
   critical-angle condition is met by construction. It fails on *arrival*:
   writing `t = η i + f n`, `f = η cos_i − cos_t` is negative for every incidence
   whenever `η < 1`, and a camera above the water always has `η = 1/n`. With
   `n_z = cos φ ≥ 0` on any meniscus against a vertical wall, `t_z < 0`
   identically — the refracted camera ray descends everywhere, and cannot reach a
   surface above it. **The underside subtends exactly zero solid angle from any
   camera above the waterline.** `MENIS_TIR_REACH = 0.0` records it; three rows of
   `validate.py` hold it there. Reachability of a *tilt* is not reachability of a
   *position*.

The whole term is now guarded by 45 rows — a force balance on the tabulated
columns, an RK4 march of the Young–Laplace IVP, a projected-area identity, a
4000-ray brute-force march, a unit-radiance closure that integrates the shipped
deposit back to that identity, the two limits `a → 0` and `θ_c → 90°`, the
near-wall fold guard fired on both a far and a near wall, and a 128 000-hit march
of the transmitted fan against the wall map's top. The unit-radiance closure
survives the `1/n²` unchanged, and that is why the divisor went into
`_menis_under` rather than into its caller: the reflected and transmitted columns
stay a partition of unity in the caller's own units, which is the premise that
row rests on. Full
derivation and the test rationale in
`../references/12a-water-derivations.md` §3.

The contact angle is still **unmeasured** (`?`) and every row is run across its
whole plausible range rather than at one value.

## Not reachable from this file — per-band footprint filtering

The far water aliases: the 2.8 cm capillary band is sampled at a pixel footprint
that grows with distance and there is no distance-dependent narrowing of the
slope distribution, so it beats against the pixel grid as a coarse moiré. The
correct move is to **narrow the distribution, not blur the image** — a blur of
the shaded result loses the specular statistics, which are the whole point.

`render.py` cannot do it: it consumes `grad_points(x, y)` and gets one slope per
point with no knowledge of which band contributed what. What `field.py` would
have to expose is a footprint argument —

    grad_points(x, y, fp)   # fp = the pixel's footprint on the surface, metres

— with each band's contribution attenuated by its own `exp(−(k·fp)²/2)` before
the bands are summed, so a 2.8 cm band vanishes once the footprint passes it
while the 20 cm band survives. `render.py` already computes `FOOT` per ray and
would simply pass it.

## Not modelled yet — entrained air, which is **two** mechanisms

Raised with two references: surf breaking white over rocks, and a jacuzzi.

> **Corrected on the owner's objection.** This first treated them as one topic.
> They are not. They share an optics — the bubble constant below — and share
> nothing else: the air arrives by a different route, lives in a different place
> and dies on a different timescale, so they need different machinery.
>
> | | Surf on rock | Jacuzzi |
> |---|---|---|
> | Air enters | At the **surface**, folded in by a breaking crest | At **depth**, injected through an orifice under pressure |
> | Where it lives | A **skin** — a whitecap layer on top, optically thick within a few cm | A **volume** — a buoyant plume rising through the bulk |
> | Time | **Transient**: each breaker makes a patch that decays in seconds | **Steady** while the pump runs |
> | Bubble sizes | Very wide, microns to centimetres | Narrow, set by the nozzle and the shear |
> | Renders as | A **coverage mask on the surface** — you cannot see into it | A **participating medium** — you see partly through it |
> | Also present | **Spray**: droplets in air, a third medium (water in air, not air in water) | None |
>
> This scene has **neither**. Its return jet is submerged and pumps water, not
> air; a jacuzzi jet deliberately aspirates air, which is a different fitting.
> Recorded so a future round does not assume the pool's jet should foam.

Both are the **inverse of this whole model** and belong in their own pass, not
folded into the pool optics.

Everything here rests on `b_b ≈ 0`: treated water barely scatters, so it has no
body colour and the cyan comes from the liner. Aerated water is the opposite
extreme of the same equation — a dense cloud of bubbles is nothing *but*
scattering.

- **The number is one we already have.** An air bubble seen from the water side
  has the same critical angle as the surface seen from below, 48.5°, so the same
  `1 − 1/n² = 43.9%` of everything striking a bubble wall is totally reflected.
  One bubble is silvery; a cloud of them is white and opaque. That single constant
  runs the mirror outside Snell's window *and* the whiteness of foam — two
  phenomena that look nothing alike.
- **Why foam is white rather than tinted.** Absorption needs a long path:
  transmission over 5 mm of water is `(0.999, 1.000, 1.000)`. Between bubbles the
  paths are millimetres, so the scattered light never picks up the liner's or the
  water's colour. Foam is many short paths; blue water is one long one.
- **Fresh water and sea water differ, and a pool sits between them.** Clean fresh
  water drains and collapses its bubbles quickly; sea-water surfactants stabilise
  them, which is why surf foam persists on rock and a garden hose's does not. Pool
  water carries sunscreen and body oils — the same film the chapter already uses
  to damp the short wave band — so its foam is longer-lived than clean water's
  (`?`, not quantified).
- **It also makes the water opaque, not just white.** A jacuzzi hides its own
  floor. Any implementation that tints the surface white without killing the view
  of the bed has modelled the symptom.
- **Real time:** a participating-medium term with a high albedo and a strong
  forward-scattering phase function, plus a coverage mask driven by the forcing.
  It needs the `a`/`b`/`g` split the chapter demands from `liquidBody`, for the
  same reason the wall lights below do.

## Not modelled yet — submerged wall lights

Requested for a later pass. Worth writing down now because it is not a small
addition: it is the first light source in this whole model that sits **inside the
medium**, and several things the chapter asserts invert when it does.

- **The scattering term stops being negligible.** The chapter's pool optics rest
  on `b_b ≈ 0` — treated water barely scatters, so it has no body colour and the
  cyan comes from the liner. That holds for sunlight arriving through the surface.
  It fails for a bright lamp a metre away: single scattering close to a strong
  source is exactly the regime where a tiny `b` is the *only* thing you see, which
  is why a night pool glows and a day pool does not. The `a`/`b`/`g` split the
  chapter already demands from `liquidBody` is what makes this renderable —
  collapse it into one `sigma` and the glow is unreachable.
- **Snell's window runs in reverse.** Light reaching the surface from below at
  more than the 48.6° critical angle is totally internally reflected. So a wall
  lamp lights a bright disc of surface directly above it and the rest of the
  surface acts as a mirror over the pool. Same machinery as the underwater-camera
  section, used from the other side.
- **A second, independent caustic system.** The transmitted part refracts out and
  throws moving caustics onto the deck, the walls and people; the internally
  reflected part throws a second set back down onto the floor. Neither shares
  geometry with the sun's, and both come free from the existing caustic tier
  ladder by swapping the light position for the sun direction.
- **Placement matters to all of the above:** these fittings sit in the wall,
  typically 45–60 cm below the waterline, aimed along the pool rather than up.
- **Real time:** a point source in a homogeneous participating medium has an
  analytic single-scattering solution; the caustics are the existing caustic-map
  pass run from the lamp. Neither needs a path tracer.

Numbers this reproduces, each stated in the chapter:
sun-disc penumbra 6.8 mm on the bed; caustic offset 1.37 m at 44.4 deg refraction;
jet surface footprint peaking 0.91 m downstream; local rms slope 0.12 against
0.058 far field; wake energy fan +-19 deg against a +-78 deg wavevector fan.

A camera channel is a **band**, not a wavelength. `IOR = 1.3320/1.3348/1.3400`
at 620/545/460 nm turns out to be Cauchy-consistent to 5e-5, so `n(λ)` is
recovered from those three constants rather than added to them, and each channel
is integrated over the Voronoi cell of its own nominal wavelength (417.5–657.5 nm
tiled with no gap). This costs nothing — the sun's rays carry a jittered
wavelength, and the camera's `SS×SS` subsample grid carries a Latin square of
spectral strata, so the box filter does the spectral integral it was already
doing the spatial one. It matters because three delta wavelengths are a 3-point
quadrature: fine on a caustic fold, where the integrand is smooth over the
9.8 mm (2.1 output pixel) red-to-blue spread, and an aliasing comb on an opaque
silhouette, where the integrand is a step at exactly that scale.

Slope convention, everywhere in this directory and in the chapter: `s` is
`sqrt(<|grad h|^2>)`, the total mean-square slope, never the per-axis rms that is
smaller by sqrt(2). Two of the five bands were once normalised in the per-axis
convention while the rest used the total, which put two units on the two sides of
the slope budget; `field.rms_slope` exists so that cannot recur.
