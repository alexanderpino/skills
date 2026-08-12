# Pool reference implementation

A physically-motivated renderer for a 1.40 m domestic pool, written to check the
claims in `../references/12-water-rendering.md` against photographs. Every
doctrine statement in that chapter that carries a number was either derived here
or falsified here.

    python3 render.py          # writes pool.png, pool_dispersion.png, pool_zoom.png

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
| 1 · closed form | a disagreement is a bug in one of the two | exact Fresnel (F0, grazing, Brewster, s/p) — including the renderer's own `fresnel` against the closed-form Brewster value — Snell and the critical angles, TIR and the null return past it, Beer–Lambert, the sun-disc penumbra compression, **a single sinusoid's caustic against its analytic Jacobian**, a flat surface, the sun lobes' flux, the riser gather's closure and `tir_vert(0) = ½`, the meniscus's force balance and projected-area identity and its two collapse limits, and the sign that refutes the fillet's internal-reflection term |
| 2 · published measurement | a disagreement may be a bug or a different water | pure-water absorption vs Pope & Fry 1997 and Smith & Baker 1981, slope statistics vs Cox & Munk 1954, the round-jet constants S and B, capillary-gravity dispersion and c_min |
| 3 · independent method | a disagreement localises to one of the two methods | Monte-Carlo vs the reflected-slope ellipse, a 0.2 mm march vs the analytic cylinder, the separable GEMM vs the direct plane-wave sum, MC vs the exact rectangle view factor, MC vs TIR_FRAC and TIR_VERT, the empirical diffuse-Fresnel fit vs the file's quadrature, the eikonal solve against its own conserved Hamiltonian, an RK4 march of Young–Laplace vs the meniscus profile and a 4000-ray fan vs its projected area |

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

## Known defect — the transmitted column has no `1/n²`

Found while closing the eight above, **recorded rather than fixed**, because fixing
it is a round of its own and this one is not on the list.

`water_shade` composes `F(θ_v)·L_sky + (1 − F(θ_v))·L_bed`. `L_bed` comes out of
`shade()` as `albedo × irradiance`, and that irradiance is the beam *already
through the surface*, so `L_bed` is an **in-water** radiance. Radiance is not
conserved across a refracting interface — `L/n²` is — so what leaves the water is
`T(θ_v)·L_bed/n²`, and the `/n²` is not there. `n² = 1.774 / 1.782 / 1.796` on this
file's three IORs.

It is a **relative** error between the two columns of one pixel: the sky term is
air-side and right, so the bed reads ~1.78× bright against it, which is exactly what
the spec-C reflected-vs-transmitted diagnostic measures. The internal return
(`bedret`) is not the missing factor — that is the light which *failed* to escape,
coming back to re-light the bed, and it is already inside `L_bed`'s irradiance.

The meniscus's transmitted column, built after this was recorded, **inherits the
same omission and makes it more visible** — the transmitted column now carries the
waterline as well as the open field. It had to: what that term subtracts was drawn
without the factor, so correcting one side alone would put a 0.83-stop step across
the junction. Not compensated for anywhere else.

Not fixed here for two reasons, both worth stating: the absolute level is entangled
with `LINER_TINT`, the liner albedos and `EXPOSURE`, all fitted to a photograph with
this factor absent, so applying it darkens the water column by 0.83 stops and every
one of those has to be re-derived; and the claim needs its own guard that does not
come from the same derivation — the natural one is a closed energy audit of the pool
(apparent albedo against `T·ρ(1−R_int)/(1−ρ·R_int)`, which `R_EXT`/`R_INT` already
supply). Full statement in `../references/12a-water-derivations.md`, *What did not
reproduce*, item 5.

## Known defect — stone gets no direct sun on two sides

`sun_vis` applies `coping_vis` to stone. `coping_vis` is a **water-surface** term —
the run from a water point to the lip — and on a deck or coping point it returns 0
for any face whose outward normal has a positive component toward the sun. So the
north and west **copings and paving** are lit by `SKY_DECK` alone: no direct sun,
no directional shading. `liner_band` sidesteps it through `sail_vis`; `paving` does
not.

The owner has ruled the **terrace** out of scope, and it is. The **coping** is not:
bar section E keeps the coping, the wall thickness and the waterline in scope
precisely because that is where water meets stone. So this is filed as *the coping
loses its direct sun*, not as *the terrace is flat*, and should be picked up or
dismissed on that basis.

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

## Not modelled yet — the wall as a light carrier

The single largest unmodelled transfer in the daylight scene, and it is now
**measured rather than argued**. Two independent numbers say the same thing:

- **58%** of the bed's total-internal-reflection return meets a wall before it
  ever reaches the surface. Past 48.6° from vertical, 1.40 m of depth needs
  ≥1.59 m of horizontal run and the basin is 4 m across. Those rays are dropped.
- The **exact rectangle view factor** from a bed point to the water surface says
  the walls take a large share of the bed's cosine-weighted hemisphere (printed
  each run, mean and worst texel) — and `SKY_AMB` is currently applied over the
  whole of it. So the flat blue ambient is over-counted by exactly that share,
  and the directional term that should replace it is missing.

That pairing is why the errors have **opposite signs**: caustic interiors on the
deep floor come out too dark (nothing fills them from the side) while the sail's
shadow comes out too bright (a flat constant fills what should be shadowed).
One missing mechanism, two symptoms.

What does not exist is the **return leg**. The receiving half is already here —
`_riser_shade`'s gather is written for a vertical face and already reads
`wall_img` when a gather ray lands on a wall — but wall → bed needs an *up-going*
intersector, which `scene_hit` is not (it solves the first hit of a **downgoing**
ray). That is the whole of the work, and it is a pass of its own.

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

The whole term is now guarded by 39 rows — a force balance on the tabulated
columns, an RK4 march of the Young–Laplace IVP, a projected-area identity, a
4000-ray brute-force march, a unit-radiance closure that integrates the shipped
deposit back to that identity, and the two limits `a → 0` and `θ_c → 90°`. Full
derivation and the test rationale in
`../references/12a-water-derivations.md` §3.

The contact angle is still **unmeasured** (`?`) and every row is run across its
whole plausible range rather than at one value.

## Known defect — the submerged walls sit 20 mm outside the surface they meet

Found while tracing the meniscus's transmitted column, **recorded rather than
fixed.** The water's plan boundary — the vertical face carrying the liner band,
the line the height field cliffs at, the line the meniscus climbs — stands at
`s = SLIP = −0.020`. `scene_hit` puts the four submerged walls on the plan
rectangle, `s = 0`. A refracted camera ray therefore travels 20 mm further before
it meets the wall than the geometry above it says, and lands about **5 mm lower on
the liner**, against a wall map whose coping-shade term has a 55 mm scale at the
top. Elsewhere in a 1.40 m basin that is nothing; at the waterline it is the whole
gradient. It very nearly cancels inside the meniscus's own subtraction, since the
fillet's traced ray and its flat baseline are displaced alike. Fixing it means
moving the four planes in `scene_hit` and re-deriving the dry-band absorption
regression measured off the band immediately above them.

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
