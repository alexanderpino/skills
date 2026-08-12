# Pool reference implementation

A physically-motivated renderer for a 1.40 m domestic pool, written to check the
claims in `../references/12-water-rendering.md` against photographs. Every
doctrine statement in that chapter that carries a number was either derived here
or falsified here.

    python3 render.py          # writes pool_final.png, pool_final_dispersion.png,
                               #        pool_final_zoom.png

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
not written here, in three tiers, in about 35 seconds — no render, no PNG.

| Tier | Strength of evidence | Covers |
|---|---|---|
| 1 · closed form | a disagreement is a bug in one of the two | exact Fresnel (F0, grazing, Brewster, s/p) — including the renderer's own `fresnel` against the closed-form Brewster value — Snell and the critical angles, TIR and the null return past it, Beer–Lambert, the sun-disc penumbra compression, **a single sinusoid's caustic against its analytic Jacobian**, a flat surface, the sun lobes' flux, the riser gather's closure and `tir_vert(0) = ½` and `WALL_SKY` as the other half of that same hemisphere, the meniscus's force balance and projected-area identity and its two collapse limits, the sign that refutes the fillet's internal-reflection term, **Walsh's relation and a closed energy audit of the whole pool**, the four wall planes against `pool_sdf`, the analytic ceiling on the fillet's transmitted column, the near-wall fold guard fired both ways, and a shadow march of the coping |
| 2 · published measurement | a disagreement may be a bug or a different water | pure-water absorption vs Pope & Fry 1997 and Smith & Baker 1981, slope statistics vs Cox & Munk 1954, the round-jet constants S and B, capillary-gravity dispersion and c_min |
| 3 · independent method | a disagreement localises to one of the two methods | Monte-Carlo vs the reflected-slope ellipse, a 0.2 mm march vs the analytic cylinder, the separable GEMM vs the direct plane-wave sum, MC vs the exact rectangle view factor, **the bed ↔ wall transfer closed by reciprocity — the shipped gather's lattice against that same rectangle view factor**, the shipped 240-direction lattice against its own closed form over the wall's height range, MC vs TIR_FRAC and TIR_VERT, the empirical diffuse-Fresnel fit vs the file's quadrature, the eikonal solve against its own conserved Hamiltonian, an RK4 march of Young–Laplace vs the meniscus profile, a 4000-ray fan vs its projected area, a 1 mm march of the bed height field vs `scene_hit`'s five-plane solve, a 128 000-hit march of the fillet's transmitted fan vs the wall map's extent, and the pool's apparent albedo integrated ray by ray vs `wet_albedo`'s trapped series |

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

**It is now 196 rows and 0 FAIL, up from 169.** The 27 new ones are the guards on
the six defects closed below plus the four on the wall gather, and each was
checked the only way a guard can be: by putting the defect back. Reverting the
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

## Not modelled yet — the camera under the water

Requested for a later pass, and the largest single inversion left in the model:
everything above is a view *into* the medium, this is a view *from inside* it.
Numbers below are computed from the constants already in `render.py`, so the
feature is mostly a matter of building the view, not of finding new physics.

- **Snell's window.** The whole above-water world compresses into a cone of half
  angle `asin(1/n)` overhead — 48.5 deg green, so 97 deg across. Outside that cone
  the surface is a **perfect mirror**: reflectance is exactly 1 beyond the critical
  angle, so the camera sees the bed, the walls and the step unit folded back down.
  There is no partial regime out there, which makes the rim the hardest edge in
  the scene and the easiest thing to get visibly wrong.
- **`refract()` now has the branch this pass is built on.** Past the critical
  angle it returns the null vector `(0,0,0)`, and `is_tir(t)` is the predicate.
  It used to clamp the radicand at zero and hand back a horizontal vector of
  length `n·sin i > 1` — a direction that is not a direction, returned silently,
  which is precisely the failure this pass would have inherited on its first
  frame. Unreachable from every current call site (all five refract *into* the
  water, `eta = 1/n < 1`, where no critical angle exists); the two whose `eta` is
  computed rather than a literal assert which side of the interface they are on,
  and this pass is the one that will flip that assert. The
  suite bisects on `refract()`'s own output for the onset of the null return and
  checks it against the angle at which the exact Fresnel reflectance reaches 1 —
  two functions with no shared line of code, agreeing to 1e-4 deg.
- **The rim is dispersive, and by a measurable amount.** With the file's own
  `IOR = 1.3320 / 1.3348 / 1.3400`, the critical angle runs 48.655 / 48.519 /
  48.268 deg — a **0.39 deg** spread, red rim outside blue. Same three constants
  that already produce the fringing on the bed caustics, used on a hard edge
  instead of a soft one.
- **The sun sits just inside the rim, at this sun elevation.** 21.0 deg elevation
  is 69.0 deg from vertical in air, refracting to **44.4 deg** from vertical below
  the surface — only **4.1 deg** inside the window's edge. So the sun is not
  overhead in the window, it is crowded against its edge, which is where the
  window is most compressed and most dispersive.
- **Absorption becomes aerial perspective.** This is the first view in the model
  where the water column sits between the camera and the far geometry, so `a`
  acts along the *view* path. `render.py` uses Pope & Fry (1997) averaged over
  its own channel bands, `a = (0.2617, 0.05299, 0.01022) /m`; the chapter quotes
  the same table point-sampled at its own 610/550/450 nm,
  `a = (0.2644, 0.0565, 0.00922) /m`. **Same water, same table, two samplings of
  it** — not two candidate waters, and `validate.py` checks both against the
  published table so neither can drift. Transmission at 5 m is `(0.27, 0.77,
  0.95)` — the far wall loses nearly three quarters of its red and the scene
  goes cyan with distance. The chapter's "the colour is the bottom, not the water"
  is a statement about a view from above; from inside, the water genuinely does
  colour the image.
- **`b_b ~ 0` gets its real test here.** Backscatter that is negligible over a
  1.4 m round trip from above is what produces the visible beam structure and the
  contrast loss along an 8 m horizontal path. Same reason the wall lights below
  need the `a`/`b`/`g` split rather than one collapsed `sigma`.
- **Real time:** the window is a single `dot(N, V)` against the critical angle plus
  a Fresnel term, and the mirror side is the existing reflection path. Nothing
  here needs a path tracer.

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

## Not modelled yet — the return leg, wall → bed

The receiving half is now built (above). The **return leg** is not: the bed's
ambient is still `SKY_AMB` over the whole of its hemisphere, including the
**35.3%** of it that is wall, and the walls are now lit correctly enough for the
error to be priced sharply — the run prints it per channel and it is signed.

Two independent numbers say the transfer is large:

- **58%** of the bed's total-internal-reflection return meets a wall before it
  ever reaches the surface. Past 48.6° from vertical, 1.40 m of depth needs
  ≥1.59 m of horizontal run and the basin is 4 m across. Those rays are dropped.
- The exact rectangle view factor gives the wall's share of a bed point's
  cosine-weighted hemisphere directly (35.3% mean, 77% at the worst texel).

That pairing is why the residual errors have **opposite signs**: caustic
interiors on the deep floor come out too dark (nothing fills them from the side)
while the sail's shadow comes out too bright (a flat constant fills what should
be shadowed). One missing mechanism, two symptoms.

What blocks it is one thing: wall → bed needs an *up-going* intersector, which
`scene_hit` is not (it solves the first hit of a **downgoing** ray). And what
replaces `SKY_AMB` there has to be **directional** — the wall runs
`(0.335, 0.920, 1.186)` at the waterline to `(0.125, 0.759, 1.131)` at its foot.
That is a pass of its own.

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
