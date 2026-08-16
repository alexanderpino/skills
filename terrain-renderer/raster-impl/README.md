# Screen-space water — the raster reference

The other half of `../references/12-water-rendering.md`. The offline reference in
`../reference-impl/` carries 285 guarded quantities on the pool and 173 on the
sea, and every one of them is a statement about an **integral**. The chapter's
real-time sections are statements about **what you are allowed to do to that
integral before the frame starts** — split it, table it, sample it, drop the
part that refracts — and the offline path cannot test any of them, structurally:
approximation error is invisible to a code path that does not approximate.

    python3 validate_raster.py        # 200 rows, three tiers, ~2 min, non-zero exit on FAIL
    python3 validate_raster.py -v     # every tolerance's justification
    python3 validate_raster.py --fast # skip the frame-level tiers (~15 s)
    python3 evidence.py               # the eight figures in gauntlet/raster/evidence/
    python3 evidence.py r2-           # just the wave set

| File | Owns |
|---|---|
| `lut.py` | The exit-transport table, baked **both ways**. `optics.slab_esc` / `slab_trap` on one side, the separated pair a table-builder writes on the other, and the half-texel discipline implemented correctly *and* incorrectly so the suite can measure the difference rather than assert it. |
| `scene.py` | The body (a shoaling shelf), the camera, the reversed-Z projection and its inverse, the opaque prepass that writes the two buffers the pass consumes, and `project_to_pixel` — the only thing a screen-space pass needs to re-sample a buffer somewhere other than at its own pixel. |
| `sswater.py` | **The pass.** The fullscreen triangle emitted from `SV_VertexID` and rasterized with a real coverage test; the chapter's four numbered pixel-shader steps in its own order; the composition, per leg; the helper-lane audit. |
| `offline.py` | The frame the pass is validated against. Same model, different machinery: analytic geometry, per-band refracted rays, `optics.slab_esc` / `slab_trap` evaluated at **every pixel's own three optical depths**. |
| `waves.py` | **The wave surface**, on the flat datum. `field.py` wired in: the narrowed slope field, the removed-variance tensor, the screen-space footprint the pass can actually form, the slope-covariance-to-lobe-covariance map, and the three filter paths the chapter's *Distance and filtering* is an argument between. Its own camera, and why. |
| `waveref.py` | The frame `waves.py` is validated against: the pixel's own footprint integral, by stratified sub-sampling of the **unfiltered** field. Two estimators, because the sun's disc defeats the obvious one. |
| `validate_raster.py` | 200 rows on `validate.py`'s harness. At least one absolute row per quantity. |
| `evidence.py` | The eight figures, every caption number formatted from the run that drew it. |

**Nothing here re-implements any physics.** `optics.py`, `atmosphere.py` and
`field.py` are imported across a path, never copied; `beach_plot.py` draws the figures;
`render.py` is not imported at all (8966 lines, minutes to run, prints on
import) and the two constants taken from it — the liner albedo and the paving
albedo — are quoted with their line number. The only physics **derived** in this
directory is three: the sky's entry leg, which has a photon walk on it; the
screen-space footprint, which has a closed form beside it; and the
slope-covariance-to-lobe-covariance map, which has a Monte-Carlo row and an
order check.

---

## What the chapter specifies, and what is mine

The chapter's *Screen-space water: the fullscreen-triangle pass* is unusually
implementable — it gives the vertex shader in HLSL and the pixel shader as four
numbered steps. All of that is reproduced literally:

| The chapter's | Where |
|---|---|
| `uv = float2((id << 1) & 2, id & 2)`, `pos = float4(uv.x*2-1, 1-uv.y*2, 0, 1)` | `sswater.fullscreen_triangle` — three verts, no vertex buffer, no index buffer |
| "one *triangle*, not a quad … redundant helper lanes twice along the seam" | `sswater.helper_lane_audit` — **counted**, see below |
| step 1, build `rayDir` from the camera basis and pixel NDC, camera-relative | `scene.ray_dirs` |
| step 2, `t = (h_water - camPos)/rayDir`, with guards on `\|rayDir\| < ε`, `t < 0`, and the below-datum sign flip | `sswater.water_pass`, all three explicit, all three fired in the suite |
| step 3, depth reject "using the frame's actual depth convention (reversed-Z, jitter)" | `scene.project_depth` / `unproject_depth`; the jitter trap is measured, not repeated |
| step 4, "traversal distance from scene depth vs `t` for absorption" | `traversal='straight'` — **and it is wrong; see below** |
| *What to pre-cook*: "Store `T_esc[τ]` and `G_rt[τ]` … one table, one fetch, two channels" | `lut.ExitLUT('joint')` |
| *Format, precision*: "sampled over `[0.5/N, 1 − 0.5/N]`" | `lut.fetch`, against `lut.fetch_halftexel_bug` |
| *Generating them*: a table "is finished when it reproduces the closed form at its sample points" and its interpolation error is bounded from the estimator's own error | tier 3, with the bound `h²/8·max\|f''\|` computed rather than quoted |

Mine, and stated so they can be argued with:

- **The body.** A shoaling shelf, 0 → 3.00 m, slope 0.55, so that **optical depth
  sweeps across the frame**. The chapter specifies no scene, and one depth
  cannot exhibit an error that is a function of depth. `τ_red` runs 0 → 0.785,
  which is the span of the chapter's own scaling table.
- **The camera**, the deck, the post, 560×315.
- **z is up** and the datum is `z = 0` — `render.py`'s convention, not the
  chapter's `camPos.y`. One axis renamed so every imported constant keeps its
  meaning.
- **The radiometric composition.** The chapter says "everything in *Shading and
  optics* applies unchanged at the hit point" and does not write it out. Each
  leg is named in `sswater.bed_radiance` and `water_shade`.
- **The two upwelling modes**, `directional` and `diffuse`. This is the
  experiment and it is discussed below.
- **`traversal='snell'` and `traversal='ssr'`**, which are not in the chapter and
  are the answer to the thing it got wrong.

### Not built, and marked rather than faked

| | Why not | What it would take |
|---|---|---|
| ~~Wave normal cascades~~ | **Built** — `waves.py`, `field.py`'s five analytic bands on the flat datum. Nothing authored, no noise, no texture. See *Distance and filtering* below. | — |
| Per-pixel raymarching of a **displaced** surface | The surface is now tilted but not displaced: `12`'s hierarchy is "displaced geometry near, normal detail mid, statistical BRDF far" and `waves.py` owns the second and third rungs only | Fixed steps + 4–6 binary refinements against a height field `field.py` does not expose — it answers slopes |
| Wave-perturbed **refraction** | The wave normal enters the transmitted half through the Fresnel split and not through the refracted direction, so the bed does not wobble. Omitted identically in the pass AND in the reference, so no path gains from it | `offline.py`'s per-band refracted trace, at the reference's sub-sample rate |
| The underwater branch (`camPos.z < h_water`) | The chapter says it is "the same triangle, different branch", and it is — but the branch is the whole underwater state machine | `water_pass` **raises `NotImplementedError`** rather than drawing the above-water branch upside down; the guard is a suite row |
| SSR / cubemap reflection | The reflected half here is `atmosphere.sky()` evaluated in the mirrored direction, which for a flat datum under an unoccluded sky is exact | A screen-space march of the same depth buffer |
| Multiple bodies at multiple elevations | One datum, one plane; the chapter's own "where it strains" | Per-body planes, screen bounds, and a nearest-surface-per-pixel sort |
| Cast shadows | Absent from **both** the pass and the offline frame, so neither gains | A shadow term on `bed_radiance`'s beam leg |
| Motion vectors | Nothing moves in this scene | The chapter's third named trap; nothing here can test it |

---

## The factorisation trap, measured

The claim: attenuation and escape are integrals over the same water-side cosine
and are correlated, so a bake that stores `2E₃(τ)` in one table and a Fresnel
constant in another and multiplies at runtime holds the **product of the means
where the mean of the product is wanted**, and the error is `r·CV_f·CV_g` — first
order in each factor's spread, and signed.

It reproduces. At the project's own pool, `d = 1.40 m`,
`τ = 0.3664 / 0.0742 / 0.0143`:

| Leg | Joint | Separated | | red | green | blue |
|---|---|---|---|---|---|---|
| `T_esc` | 0.3403 / 0.4795 / 0.5106 | `2E₃(τ)(1−R_int)` = 0.2850 / 0.4563 / 0.5050 | joint/sep − 1 | **+19.40 %** | +5.07 % | +1.10 % |
| `G_rt` | 0.0965 / 0.3277 / 0.4445 | `2E₃(τ)²·R_int` = 0.1389 / 0.3614 / 0.4546 | 1 − joint/sep | **−30.52 %** | −9.32 % | −2.21 % |
| | | | sep/joint − 1 | **+43.94 %** | +10.28 % | +2.26 % |
| `G_rt` | (same) | `2E₃(2τ)·R_int` = 0.1502 / 0.3650 / 0.4549 | 1 − joint/sep | **−35.74 %** | −10.24 % | −2.30 % |
| | | | sep/joint − 1 | **+55.63 %** | +11.41 % | +2.35 % |

The chapter prints **19.4 / 5.1 / 1.1** for the escape leg and **30.5 / 9.3 /
2.2** and **43.9 / 10.3 / 2.3** for the round trip, and every one of those is in
the table above to better than 0.04 pp.

### The 30%

`optics.py`'s own comment says the factorised round trip "OVERstates it by 30% in
red". A previous builder measured **55.6 / 11.4 / 2.4** at 1.40 m, could not
reconcile it, and reported that 30% is what red gives near 0.78 m. **Both are
right, and neither is the whole answer.** There are two independent ambiguities
and the chapter resolves neither:

1. **Which separated form.** The chapter names one separated *escape* leg and it
   is unambiguous. It never names a separated *round trip*, and two are natural:

   - `2E₃(2τ)·R_int` — one depth table, read at the round-trip optical depth.
     The direct analogue of the escape leg.
   - `2E₃(τ)²·R_int` — up leg × mirror × down leg, the product of the means
     taken **twice**.

   These differ by 12.4 pp in red at this depth. **The chapter's 1.40 m table is
   the second form and its τ-scaling table is the first.** The identification is
   not a guess: `2E₃(τ)²·R_int` gives 0.1389/0.3614/0.4546 against the chapter's
   printed 0.1389/0.3614/0.4546, and the other form gives 0.1502/0.3650/0.4549.
   Suite rows pin each.

   **The chapter moved under this directory while it was being built.** A
   parallel commit — `renderer 12: two separated round trips, and the more
   physical one is further off` — reached the same two-forms conclusion
   independently and the 1.40 m block now names both, printing
   `0.1502 / 0.3651 / 0.4549` and `+55.6 / +11.4 / +2.4 %`. Those are inside
   0.05 pp of what `lut.py` bakes, reached from a different direction, and they
   are now two more tier-2 rows. That commit adds something this directory did
   not have: `2E₃(2τ)` is the *direction-preserving* transmittance and therefore
   the better physics for a specular underside, and **it is the further off** —
   fixing the direction error alone moves red 8.1% away from the truth, because
   the squared form was getting part of its accuracy from a cancellation between
   two decorrelations.

   **What is still not labelled is the τ-scaling table.** It is the `2E₃(2τ)`
   form — every printed row lands inside that form's envelope and 5–9 pp away
   from the squared form's — sitting eight lines below a table that now leads
   with the squared form and names both. A reader takes the two blocks as one
   quantity and they are not.

2. **Which direction the ratio runs.** `1 − joint/sep` and `sep/joint − 1` are
   the same fact and different numbers, and at 44% the difference between them is
   13 pp.

So: `optics.py`'s 30% **does** reproduce — it is 30.52%, the `2E₃(τ)²` form read
as `1 − joint/sep`, at 1.40 m, which is exactly where the comment sits. The
previous builder's 55.6% also reproduces — the `2E₃(2τ)` form read as
`sep/joint − 1`. The four numbers are all in the table above and
`lut.factorisation_error` returns all four by name, because a project that has
confused two of them once will confuse them again.

### A third thing the chapter gets wrong about its own table

`12` presents the τ-scaling table as a function of **optical depth alone** — a
line the parallel chapter commit above did not touch. It is
not: the joint integrals carry `R_int(μ)`, which is per band, so the same τ gives
three different errors. The spread is **0.63 pp at τ = 2** and no single band
reproduces every printed row — green matches six of seven and the `0.37` entry is
red at this pool's own `τ_red = 0.36638`. The suite therefore checks each printed
number against an **envelope** over the two-decimal τ rounding the label allows
and over all three bands, and the finding is that the table needs a band label.

### What it costs in a frame — and the chapter is right that you cannot see it

`gauntlet/raster/evidence/r1-frame-factorisation.png`. Same geometry, same
camera, same table size; only the bake differs.

| upwelling | whole frame, red / green / blue | worst binned red |
|---|---|---|
| `diffuse` — the whole upwelling from a column table (`12`'s named temptation, `T[depth]·kExit`) | **−9.27 / −4.68 / −0.76 %** | **−17.5 %** |
| `directional` — each ray attenuated over its own path; the table read only for the sky's entry leg and the trap gain | **−0.84 / +0.65 / +0.58 %** | −2.1 % |

The **term** over that same τ range is wrong by up to **34% (escape)** and **49%
(round trip)**, with opposite signs, and the round trip sits in a denominator so
they partly cancel. `lut.composed_albedo` reproduces the chapter's own chain
number exactly: the composed albedo moves **−2.83% in luminance** at 1.40 m while
the escape term inside it is wrong by 19.4% in red. *Check the term, not the
chain* is correct, and it is now measured rather than repeated.

Two things the chapter does not say, both of which came out of building the pass:

- **How much of the error reaches the pixel is an architectural choice the
  chapter does not make for you.** A factor of 8 between the two rows above, from
  one decision about where the angular average sits. The chapter's list of "where
  the temptation arises" names the diffuse case; it does not say that the careful
  case is nearly immune, which is the actionable half.
- **The frame error is not monotone in τ.** It peaks near `τ_red = 0.4` and
  flattens, because the deepest water in this frame is also the most grazing and a
  grazing water pixel is mostly surface reflection. **Optical depth alone does not
  price this error; the view angle prices it too**, and `12` tabulates it against
  τ alone.

---

## Where the pass fails against the offline reference

`gauntlet/raster/evidence/r1-pass-vs-offline.png`. 157 641 water pixels, post
silhouette excluded, scene-linear, all three bands.

| traversal rule | median | p95 | max | median absolute |
|---|---|---|---|---|
| `straight` — **the chapter's step 4, literally** | 12.1 % | 46.5 % | 67.2 % | 7.7e-2 |
| `snell` — `d/μ_w`, one extra `sqrt` | 4.1e-5 | 33.1 % | 56.6 % | 5.9e-5 |
| `ssr` — refract, re-project, re-sample the depth buffer, 6 taps | **4.0e-5** | **1.6 %** | 13.5 % | **5.7e-5** |
| *floor*: the same pass handed the offline frame's own geometry | 1.3e-5 | — | 2.6e-4 | — |

The tolerance the pass reaches is therefore: **a median of 4×10⁻⁵ relative and
5.7×10⁻⁵ in radiance, which is 1/180 of one 8-bit code value at this frame's own
derived exposure** — the suite's bar, because it is the only externally-anchored
one available for a screen-space approximation. The **floor** row is the
important one: with the depth buffer taken out of the loop the pass and the
offline reference agree to 1.3×10⁻⁵ median and 2.6×10⁻⁴ worst. Everything above
the fifth decimal is the depth buffer, not the physics. **The pass and the
offline reference are one model, and that is the strongest statement in this
directory.**

### 1. The chapter's step 4 is wrong, and by a lot

> "traversal distance from scene depth vs `t` for absorption"

That is the **straight** ray, and the transmitted ray refracts. The two lengths
are `d/cos θ_a` and `d/μ_w`, and

    mu_w >= 1/n = 0.749     for every air-side angle, however grazing
    cos theta_a -> 0        at the horizon

so the straight-ray length **diverges** where the true one is bounded by `1.33 d`.
Over this frame the literal reading costs **12.1% median and 46.5% at p95**, and
it is fixed by one `sqrt`. This is not a subtlety about a hard case: it is the
whole far half of any water frame with a horizon in it.

The chapter is not unaware of refraction — the same step says "refraction from
the scene-color copy" one clause later — but the traversal *distance* sentence is
written for the straight ray and it is the sentence a shader author will
implement. **Suggested repair:** *"traversal distance `d/μ_w` with `μ_w` the
Snell cosine of the view angle — not `sceneDepth − t`, which is the straight
ray's length and diverges at grazing incidence where the refracted ray's does
not."*

### 2. Where even `ssr` breaks down, and it is not fixable in screen space

| | |
|---|---|
| **Grazing water over a sloping bed.** | The depth buffer answers "how far to the scene along *this* ray". On a slope the refracted ray lands on a different bed patch at a different depth, and no number of taps recovers the patch the straight ray never looked at. p95 1.6%, worst 13.5%, and the whole of it lives in the grazing fifth of the frame — at the median the `snell` and `ssr` rules are *indistinguishable* and both sit on the physics floor. **The screen-space depth error is a tail, not a level.** |
| **Occluder silhouettes.** | 1 838 pixels around the post are excluded from every number above and their worst error is **442%**. The refracted ray should sample the bed; the depth buffer at the re-projected position holds the post. This is not a bug and not a tolerance — screen-space refraction cannot see behind an occluder, and the only honest thing is to report the patch and its size. |
| **Re-sample aliasing.** | The stipple in the difference map is the re-tap landing on integer texels. A depth buffer **may not be bilinear-filtered** across a silhouette, so nearest is correct and the aliasing is real. |
| **TAA jitter.** | Half a pixel of jitter applied by the prepass and not by the shader moves the reconstructed water column by a median of **1.06 cm** and a worst case of **4.50 m** on this bed. The chapter lists it as a trap; here it is a number. |

---

## Three more things the running turned up

### The half-texel rule has two readings and only one of them is safe

> "A bilinear table must be sampled over `[0.5/N, 1 − 0.5/N]`, or its endpoints
> are wrong by half a texel."

Two table designs satisfy a sentence like that and they are not equivalent:

| design | endpoints | order |
|---|---|---|
| texels at centres `τmax(i+0.5)/n`, sample `x = nτ/τmax − 0.5`, clamp | half a texel **outside** the table; a clamped sampler returns a constant | **first** order at both ends, second in the interior — measured at 9.3e-3 on `T_esc` at τ → 0 with n = 64 against 2.6e-5 in the interior, a factor of 350 |
| texels at `linspace(0, τmax, n)`, sample `x = (τ/τmax)(n−1)`, i.e. `u ∈ [0.5/N, 1−0.5/N]` | exact | second order everywhere |

The chapter's own sentence means the second, and the second is what `lut.py`
builds — but only after the first was written, shipped and measured. The concentration
matters: the bad endpoint is at **τ → 0**, which is the shoreline, which is
exactly where the factorisation error goes to zero and a bad table would
manufacture one.

The **actual** half-texel bug is also implemented (`fetch_halftexel_bug`) and the
suite measures its **order**: it is first order in `1/n` (slope −1.00) where an
honest interpolation error is second (slope −2.03). *A table whose error only
halves when you double its resolution has a remap bug and not a resolution
problem* — diagnosable without reading the shader.

### One triangle rather than two: the mechanism is real, the size is 0.5%

| | 560×315 | 1920×1080 |
|---|---|---|
| 2×2 quads on screen | 44 240 | 518 400 |
| quad↔primitive pairs, one triangle | 44 240 | 518 400 |
| quad↔primitive pairs, two triangles | 44 450 | 519 120 |
| seam quads shaded **twice** | 210 | 720 |
| extra shaded lanes | **+0.47 %** | **+0.14 %** |

The chapter's mechanism is exactly as described and the cost is a few tenths of a
percent, falling with resolution because the seam is one-dimensional and the
frame is two. The load-bearing half of the chapter's argument is the other one —
no vertex buffer, no index buffer, one set of interpolants — and that one is
free. Worth saying plainly: *the quad-seam argument is true and it is not why you
should care.*

### A quadrature bias in the offline reference — 0.006%, reported not fixed

Insisting that `T_esc(0) = 1 − R_int` hold at machine precision found this.
`optics.slab_esc` integrates `2μ e^{−τ/μ}(1−R_int(μ))` over `μ ∈ (0,1]` with one
2000-node Gauss–Legendre rule, and `R_int(μ)` has a **square-root branch point at
the critical angle** — identically 1 below `μ_c`, reaching 1 with infinite slope
from above. Gauss–Legendre is spectral on smooth integrands and only algebraically
accurate across a branch point.

| τ | bias, red / green / blue |
|---|---|
| 0.0000 | +4.4e-5 / **+6.3e-5** / +3.1e-5 |
| 0.3664 | +3.9e-5 / +5.6e-5 / +2.7e-5 |
| 0.7850 | +3.4e-5 / +4.9e-5 / +2.4e-5 |

Which side is wrong is settled: `T_OUT_DIFFUSE` is built from the **air-side**
Fresnel, whose integrand has no branch point, and a rule split at `μ_c` agrees
with it to 2e-7 where the shipped rule is 3.3e-5 away. So `slab_esc` overstates
the escape by 6.3e-5 relative.

It is 0.006% and no picture moves. It is reported because three tier-1 identities
in this suite cannot be checked at machine precision because of it, and because
`12`'s "at τ → 0 both collapse to the diffuse constants" is exact in theory and
6.3e-5 in the code. **Not fixed here**: `reference-impl/` is another builder's and
this directory may read it and not edit it. The one-line repair is to split the
`_SQM` quadrature at `sqrt(1 − 1/n²)` per channel.

---

## Distance and filtering: the collapse, the fix, and the price of each

`../references/12-water-rendering.md`, *Distance and filtering: why far water
turns to plastic* and *Pick the kernel on purpose, and give the variance a
receiver*. Wave 1 closed with this section carrying zero lines of code anywhere
in the directory. `waves.py` and `waveref.py` close it.

**The claim, in the chapter's terms.** As distance grows the number of waves
inside a pixel footprint grows without bound, per-pixel normals converge to the
mean normal, "all the slope variance those waves carried is silently discarded",
the specular lobe collapses toward a Dirac, and the far water reads as plastic.
The fix is to *move* the variance rather than lose it: fold what leaves the
resolved field into a 2×2 tensor that widens the BRDF lobe.

**What is imported, and it is nearly all of it.** `field.grad_points(x, y, fp)`
is the narrowed field; `field.slope_var_points(x, y, fp)` is the removed-variance
tensor, which already exists there for exactly this purpose; `atmosphere.sky`'s
own `_lobe_shape` is the receiver, with one correction described below.
Two things are derived here and both sit beside themselves in `waves.py`: the
**footprint** a screen-space pass can actually form, and the chapter's
`C = J Σ Jᵀ`.

### This section needs its own camera, and that is a finding about the hero frame

`scene.py`'s camera looks down `+x`; `atmosphere.SUN_DIR` bears 176.25°. Over the
whole of the `r1-` frame's water the largest cosine between the mirror direction
and the sun is **−0.134** — the sun's reflection is *behind* that camera, and
`atmosphere.sky`'s disc contributes **exactly zero** to every one of its 159 479
water pixels (a tier-1 count, tolerance 0). A section whose entire claim is that
the specular response collapses cannot be tested on a frame with no specular
response in it.

So `waves.sun_prepass` turns the camera to the sun's own bearing and stands off:
same body, same FOV, same resolution, **same 3.00 m eye height**, eye at
`x = 400 m` so the water spans 4.6 m to 400 m against the deck's plane as a
horizon, elevation −12° so the disc itself is just outside the top edge. The eye
height is not a leftover: the sun's road runs from `h/tan θ_sun` out to about
`h/tan(θ_sun − 4σ_slope)`, i.e. 2.6 h to 11 h, and over that range the footprint
runs 0.0148 h to 0.129 h. At h = 3 m that is 0.044 → 0.39 m, which is exactly the
span of `field.py`'s bands (WIND 17–70 mm, REVERB 12–45 cm). Twice as high puts
the whole road inside the resolved regime; half puts all of it past the filter.

### The collapse, measured

`gauntlet/raster/evidence/r2-variance-vs-distance.png`. Absolute rms slopes at
the pass's own footprints, `s = sqrt(<|∇h|²>)` throughout — `field.py`'s one
convention, and every number below goes through `field.rms_slope` or
`field._plane_rms` rather than an expression written out here.

| distance | fp median | **total** | **resolved** | **removed** | quadrature / total |
|---|---|---|---|---|---|
| 4–8 m | 0.023 m | 0.04800 | 0.04371 | 0.01994 | 1.0010 |
| 8–16 m | 0.057 m | 0.04882 | 0.03679 | 0.03205 | 0.9994 |
| 16–32 m | 0.167 m | 0.04856 | **0.01799** | 0.04523 | 1.0023 |
| 32–64 m | 0.452 m | 0.04873 | **0.00262** | 0.04864 | 0.9996 |
| 64–128 m | 1.30 m | 0.04872 | **1.4e-6** | 0.04871 | 0.9999 |
| 128–256 m | 3.52 m | 0.04872 | **5.8e-24** | 0.04872 | 1.0000 |
| 256–520 m | 7.34 m | 0.04881 | **0** | 0.04880 | 0.9996 |

The surface keeps its slope at every distance and the shading normal stops
carrying it — by 128 m the resolved field is zero to 24 decimal places, which is
the chapter's sentence with no hedging left in it. The right-hand column is
`field.py`'s own conservation identity, **checked at raster footprints up to
18.5 m** — two orders past anything `render.py` asks of it — and it holds to
0.23%.

And what that does to the specular response. Scene-linear radiance, green band,
bin means, from two independent reference estimators:

| distance | reference (2° cone) | reference (brute force) | **naive** | **fix** |
|---|---|---|---|---|
| 4–8 m | 1.585 | 1.698 | 2.371 (**+50 %**) | 1.576 (−0.6 %) |
| 8–16 m | 4.526 | 4.878 | 10.014 (**+121 %**) | 5.035 (+11 %) |
| 16–32 m | 0.1451 | 0.0333 | **0.0000** | 0.2474 |
| 32–64 m | 0.00422 | 0 | **0.0000** | 0.00512 |
| 64–128 m | 0 | 0 | 0.0000 | 4.6e-4 |

(Percentages are against the cone column; against the brute-force column they are
+40% and +105%, and the gap between the two is the cone's own kernel bias,
quoted below.)

**The collapse is not a dimming, it is a redistribution.** On the road the naive
path is *twice too bright*, because a lobe that should be spread over several
degrees is being sampled once per pixel at its Dirac peak; past 16 m it is not
small but **identically zero at every pixel**, while the surface still returns
0.145. The fix is inside the cone estimator's own bias where the surface is
resolved and lands within a factor of 1.7 where it is not.

**Why there are two reference estimators.** The sun's disc is `cos^93493` — 0.53°
across, 6.72e-5 sr — and past 30 m a footprint scatters the reflected ray over
several degrees, so the probability that a sub-sample lands on the disc is ~1e-6.
196 sub-samples of 4 400 pixels collect about two hits: the brute-force mean is a
Poisson draw and its sample standard error, which is *zero* on every pixel that
drew nothing, is a lie. That is not a defect of the estimator — it **is** the
chapter's "one shading sample per pixel hits or misses it essentially at random",
arriving on the measurement side. So the disc term is also measured as
`S = L_sun · Ω_lobe · p_R(sun) · R`, with `p_R` the density of the reflected
direction at the sun, estimated by counting sub-samples inside a cone of
half-angle ε. At ε = 2° the acceptance is 57× the disc's own. Its bias is the
kernel width and it is *reported*, not assumed: the estimate is taken at 1° and
2° and the spread between them is the tolerance every row built on it may spend.
Where the brute force converges the two agree inside that spread: 0.933 against
a bias bracket of 0.122 at 4–8 m, and 0.928 against 0.084 at 8–16 m.

### The fix, priced

`gauntlet/raster/evidence/r2-error-and-cost.png`. Best of three runs, numpy on a
CPU: what transfers is the ratio and the operation count, not the milliseconds.

| path | ms / frame | µs / px | × naive | median frame error | p95 | absolute median |
|---|---|---|---|---|---|---|
| `point` — no filter at all | 267 | 2.21 | 0.87 | 0.517 % | 20.8 % | 2.5e-3 |
| `naive` — filtered, variance discarded | 306 | 2.53 | 1.00 | **0.155 %** | **6.38 %** | 7.8e-4 |
| `fix` — variance carried, exact Fresnel | 452 | 3.74 | **1.48** | 0.178 % | 8.69 % | 8.4e-4 |
| `fix` + `12`'s roughness-Fresnel | 459 | 3.80 | 1.50 | 0.983 % | 21.5 % | 4.3e-3 |
| `fix`, `atmosphere`'s shipped receiver | — | — | — | 0.201 % | **40.9 %** | 9.0e-4 |

**Carrying the variance costs 48% of the surface shading pass and buys nothing on
the median pixel.** 0.178% against 0.155% is not a win; it is a wash, and it is
a wash at every distance bin separately. That is not a failure of the fix, and it
is the most useful thing this wave found:

> **The size of the plastic failure is a property of the ENVIRONMENT's angular
> spectrum, not of the water.** A collapsing slope distribution can only lose the
> part of the environment that varies on its own angular scale. This sky is one
> 0.53° disc on a smooth horizon-to-zenith gradient, so the *only* thing lost is
> the disc — 2% of the water pixels — and the gradient survives a collapse to a
> mirror untouched. The chapter presents the failure as a whole-surface look
> failure ("a glossy, uniform dome", "a mirror-flat plastic sheet everywhere
> else") and never says what sets its size. Under a structured sky — broken
> cloud, a coastline, a sunset band — the same collapse would cost far more, and
> under an overcast dome it would cost almost nothing. **Nobody should buy this
> fix without first asking what their environment map looks like at 5°.**

### The doctrine's central promise, tested directly

If the removed variance is really *carried* rather than lost, the answer must not
depend on how much the kernel removes. Two kernels 29% apart in width —
`field.py`'s half-amplitude-at-Nyquist pinning (`σ = 0.3748 fp`) against the box's
second-moment match (`σ = 0.2887 fp`) — over the three bins the sun's road covers:

| kernel 1.0 vs 0.774 | 4–8 m | 8–16 m | 16–32 m |
|---|---|---|---|
| **`fix`**, change in the disc term | **0.18 %** | **0.31 %** | **0.58 %** |
| **`naive`**, same change | 8.2 % | 36.7 % | **100 %** |

That is the whole doctrine in one table. Widen the filter by a quarter and the
naive path's specular response changes by up to *everything it had*; the
variance-carrying path moves by half a percent. **The kernel choice stops being a
decision once the variance has a receiver** — which is a stronger statement than
*Pick the kernel on purpose* makes, and it is the actual reason to pay the 48%.

### Where the fix stops working

Wave 1's standard: a property, not a tolerance.

| | |
|---|---|
| **A scalar footprint cannot describe an oriented one.** | `field.py`'s kernel is isotropic by construction — "all a scalar `fp` with no orientation is entitled to assume" — and the real footprint is a parallelogram whose axis ratio runs from 3.6 at the median to **401** at the horizon. `pixel_footprint` returns the area-matched isotropic `fp = sqrt(\|det J\|)`, the geometric mean of the two axes, which is the only defensible scalar; along the view azimuth it under-filters by up to 20× and across it over-filters by the same. This is not tunable: it needs an *elliptical* removed-variance tensor, i.e. `slope_var_points` taking a 2×2 footprint instead of a scalar. A production pass would pass the full Jacobian and let the band weight be `exp(-½ kᵀ Σ_fp k)`. |
| **The far glitter lives 5σ out in a Gaussian tail.** | At 100 m the sun sits 19° from the mirror direction and the reflected spread is 3.95°, so the road's outer end is a 5σ event. The lobe convolution is a small-angle construction and the slope distribution is a sum of 64 sinusoids — **bounded**, so its true tail is thinner than Gaussian. Against a direct convolution over the same tensor the closed form is within 1% at 12 m, 56% at 20 m and **81% at 80 m**, all of it over-prediction. The `fix` column's 0.247 against a reference 0.145 at 16–32 m is that. Cox & Munk measured the non-Gaussianity of real slope statistics and the doctrine does not carry it. |
| **The horizon quad has no derivative.** | 560 of 120 960 water pixels sit in a 2×2 quad with one lane above the datum, so `ddx`/`ddy` of the water hit position is not a footprint there. They fall back to the closed form so the picture stays honest and are excluded from every number. That is a property of quad derivatives, not of this pass — a production shader has the same 560 pixels and usually does not know it. |
| **The roughness-Fresnel is a fit, and it is out of range here.** | See below. It is the one part of the doctrine that is not derived and it is the only part that measurably hurts. |
| **The reference itself stops converging before the water does.** | Past 30 m no affordable sub-sample count resolves the disc, so the *image* of the reference is speckle where the truth is smooth. Any team validating this fix by eye against a supersampled render will conclude the fix is over-blurring, and they will be wrong. |

### What `12` gets wrong, and what it leaves underspecified

**1. Bruneton's roughness-Fresnel is quoted with no lower bound and it needs
one.** The chapter gives

    F = R + (1-R)(1-cos θ_v)^5 · exp(-2.69 σ_v)/(1 + 22.7 σ_v^1.5)   "fitted for σ_v < 0.5"

Against `E[R]`, the **exact** mean of `optics.fresnel` over the footprint's own
slope distribution (taken from the reference's sub-samples, so it is a
measurement and not a model):

| distance | cos θ_a | E[R] exact | Fresnel at the filtered normal | `12`'s fix | do-nothing err | fix err |
|---|---|---|---|---|---|---|
| 4–8 m | 0.49 | 0.0673 | 0.0671 | 0.0636 | −0.3 % | −5.6 % |
| 16–32 m | 0.14 | 0.4390 | 0.4305 | 0.3530 | −1.9 % | −19.6 % |
| 32–64 m | 0.070 | 0.6623 | 0.6491 | 0.5212 | −2.0 % | **−21.3 %** |
| 128–256 m | 0.018 | 0.8691 | 0.8951 | 0.7168 | +3.0 % | −17.5 % |
| 256–520 m | 0.0086 | 0.8985 | 0.9458 | 0.7569 | +5.2 % | −15.8 % |

**Doing nothing is an order of magnitude closer to the truth than the chapter's
one-line fix**, at every distance in this frame. The reason is an order, not a
constant: microfacet masking is a second-order effect, so `E[R] − R(mean)` must
vanish as `σ_v²`, and the fit's `22.7 σ_v^1.5` term vanishes only as `σ_v^1.5`.
At this surface's `σ_v = 0.0344` the fit already removes **20%** of the grazing
rise above F0 where the truth removes 1–5%, and the correction even has the wrong
*sign* out to 64 m. It is right that masking eventually lowers the grazing
reflectance — the last two rows show the truth falling 3–5% below the smooth
curve — and it overshoots that by 3 to 5 times. **Suggested repair:** state the
range as `0.05 < σ_v < 0.5` and say that below it the smooth curve is the better
answer; a calm inland water body, a sheltered bay or any surface in a lee sits
under that floor. The chapter is right about the *mechanism* and wrong about
where to apply it.

**2. The chapter's own `C = J Σ Jᵀ` check does not extend to grazing.** `12`
reports "checked against 400k Monte-Carlo perturbed reflections to 4% on the
major axis and 8% on the minor". At its own stated camera (33° above the
horizontal, θ_v = 57°) that reproduces exactly — 1.6% and 0.2% here at the same
sample count, and the stated 1.8× stretch is 1/cos θ_v = 1.836. At θ_v = 78°,
which is where most of a water frame with a horizon in it lives, the major axis
is **5.1% out**. It is the linearisation and not a defect — the residual falls by
3.3× when the variance falls by 4, i.e. second order, and that is a suite row —
but the chapter states an agreement figure with no angle attached to it.

**3. The "practical trick" does not describe `field.slope_var_points`, and the
chapter presents it as if it did.** `12` writes: *"total variance for ALL waves on
the CPU, subtract the RESOLVED waves in the shader, so shader cost scales with
resolved wave count and is MINIMAL for distant views"*. `slope_var_points` sums
over **every** component at every footprint. Measured on 200 000 points, it costs
185 ms at `fp = 1 mm` and **243 ms at `fp = 10 m`** — 1.32× *more* at the
distance where the trick promises almost nothing, because at 10 m every term it
evaluates is the saturated constant `1 − 0` that the trick exists to skip.
Reported, not patched: the interface is right and the file is another lane's.

**4. The kernel section derives a scale that is not the pixel's own, and does not
say that this stops mattering.** `12` pins the Gaussian at half amplitude at the
Nyquist wavelength, `σ = 0.3748 fp`, deliberately 1.30× wider than the box the
pixel actually integrates. Under the naive path that choice is worth up to 100%
of the specular response (table above). Under the fix it is worth 0.6%. The
chapter argues the choice carefully and never says that the argument is only
load-bearing for the path it is telling you not to use.

**5. Numbers that do reproduce**, and they are checked as tier-2 rows rather than
trusted: `σ = fp/(2√3) = 0.2887 fp`; that Gaussian passing 0.663 at the Nyquist
wavenumber, i.e. 44% of the variance; `√(2 ln 2)/π = 0.3748`; "half gone when the
footprint reaches half its wavelength" (exactly, to float32); "94% gone at one
wavelength" (93.75%); the saturating variance form differing from `a²/2` by 0.25%
at `a = 0.1`; Monahan at both worked wind speeds (0.093% at 5 m/s, 3.93% at
15 m/s); the Brewster identity, which `optics.fresnel` reaches exactly and Schlick
misses by 23.8%; and Schlick's −22.8% / +14.3% / zero at 51.3° / 79° / 67.1°.

### What the shared modules turned up — reported, not patched

**`atmosphere._lobe_shape` creates energy for an anisotropic ellipse, by up to a
factor of 10 in this frame.** It writes the widened lobe back as `cos^n_eff` with

    n_eff = 1 / (u^T Q u)          -- the PROJECTION variance

where the convolved density along `u` wants `n_eff = u^T Q^-1 u`. The two are
identical for an isotropic `Q` and on either principal axis, which is why nothing
caught it; by Cauchy–Schwarz `1/(uᵀQu) ≤ uᵀQ⁻¹u` always, so the shipped lobe is
never too narrow, always too wide, and the peak factor `g = sqrt(det Q₀/det Q)` —
computed for the *correct* Gaussian — no longer normalises it. Integrated over
the sphere against the unwidened `2π/(n+1)`:

| ellipse axis ratio | 1 | 10 | 1e4 (this frame) |
|---|---|---|---|
| `_lobe_shape` as shipped | 1.009 | **1.682** | **10.374** |
| the inverted form | 1.009 | 1.004 | 1.000 |

The repair is the 2×2 adjugate and it is one line:
`u1²q22 − 2u1u2q12 + u2²q11`, over `|u|² det Q`. It is **not** applied to
`atmosphere.py`, which is shared; `waves.widened_lobes` carries the inverted form
and feeds it back through the shipped `sky()` as a per-pixel amplitude and
exponent, so the environment, the gradient, the 1.15 and the disc/aureole
partition all stay `atmosphere.py`'s. The shipped form is kept beside it as
`receiver='shipped'` so the suite can price it rather than assert it: over this
frame it is invisible on the median (9.7e-9) and worth **12.0× at p99** and 397
in absolute radiance at worst. `render.py` reads the same function at
`θ_v ≈ 57°`, where the ellipse ratio is about 3 and the gain is 1.2–1.7× — a
brightening of the pool's own glints that reads as taste.

**`field._norm_jets()` is not optional and nothing says so.**
`field._SC['near']` ships at 1.0 and `_norm_jets` sets it to **0.001011**, so a
consumer that imports `field` and calls `grad_points` without calling it first
gets the NEAR band at **989×** its calibrated amplitude — silently, with the
field's rms slope reading 0.99 instead of 0.049 and no exception anywhere.
`render.py` calls it at line 1228 and `validate.py` at line 4137, both by
convention. It cost this wave one full round of wrong measurements. The repair is
a one-line guard inside `grad_points`/`slope_var_points`, or a module-level call;
neither is applied here, by scope.

**A normal-map mip already carries the removed variance, and renormalising throws
it away.** Measured off the reference's own sub-samples, for free: the mean of the
unit normals over the footprint has length `|N̄| = 1 − s²/2`, and
`2(1 − |N̄|) / s² = 0.991` at 256–520 m. Toksvig's signal is exact to under 1% at
raster footprints. That is a cheaper route to the same tensor than
`slope_var_points` — one extra channel in a normal map, hardware-mipped — for
anyone who has a normal map rather than an analytic band sum. `12` names Toksvig
in its "unifying idea" paragraph and does not mention that the two are the same
number.


---

## The one piece of physics derived here

`sswater.bed_radiance` needs the diffuse transmittance of the column for
**skylight entering** it, and neither `optics.py` nor the chapter has it. It is
not a free choice: by Helmholtz reciprocity the flux entering the water at
water-side cosine `μ` is weighted by the same `(1 − R_int(μ))` that governs
escape, so

    T_dn(tau) = T_esc(tau) / (1 - R_int)

— the **same integral, read again**, which is why the sky leg carries the
factorisation error too and why `diffuse` mode carries it twice. Two consequences
worth stating: at `τ = 0` this gives exactly `1 − R_EXT`, so a lossless white bed
composes to an apparent albedo of exactly 1 (a tier-1 row, at 1e-12); and it is a
*new* claim in this project, so it gets a **4 000 000-photon walk** through the
exact Fresnel and Snell with each photon attenuated over its own `1/μ_w`. Four
depths, agreement inside 4 standard errors of the estimator, tolerance ~2e-4.

---

## Reading the suite

200 rows, three tiers, ~2 min (the wave tiers build a 196-sub-sample reference). The harness, the tier meanings and the rule that a
tolerance comes from the **estimator's** error and never from the measured
disagreement are `validate.py`'s, deliberately.

**Every quantity has at least one absolute row.** A ratio-only guard has been
blind four times in this project, once dividing 0/0 and raising, so: coverage is
a pixel *count* with tolerance 0; depth precision is *metres*; the LUT is checked
on its *values* before any ratio; the frame comparison carries a *radiance* row
beside every relative one; the factorisation error is reported as joint,
separated, and then four named ratios; slope is an *rms slope*, the removed
variance is a *tensor in s²*, the specular response is a *radiance*, the
footprint is *metres*, the widened lobe's flux is *steradians*, and the cost is
*milliseconds and microseconds per pixel* before it is ever a multiple.

Two tolerances in this file are not scientific constants and are labelled as
such:

- The traversal rows are anchored on **one 8-bit code value at the frame's own
  derived exposure** (1.04e-2 radiance) rather than on a percentage, because a
  percentage invented for a screen-space approximation is a percentage invented
  for it — the first writing of this suite did exactly that and the rows failed
  the moment the shelf moved.
- The two chapter τ-scaling tables are checked against **envelopes**, for the
  band-label reason above.

## Why 560×315

The offline frame calls `optics.slab_esc` and `optics.slab_trap` once per water
pixel at that pixel's own three optical depths — ~100 µs each, ~14 s a frame at
this resolution, and that cost is the *point*: it is precisely what a LUT exists
to remove. Exact duplicate depths are grouped by float equality, which is exact
and buys the flat shelf for one call. 16:9 with an odd number of 2×2 quad rows,
so the helper-lane audit is not run on a size that hides a parity bug.

## Evidence — `gauntlet/raster/evidence/`, `r1-` prefix

Every caption is burnt into its frame and every number in it is formatted from
the run that drew it: if a constant moves the caption moves with it, and if a
caption and its figure disagree the figure was not redrawn. The `r1-` five are regenerated by
`python3 evidence.py r1-` in about 40 s; the `r2-` three take about 100 s each
run because each builds the pixel-integral reference.

| Frame | What it settles |
|---|---|
| `r1-pass-vs-offline.png` | The pass beside the offline frame it is validated against, the difference map, and the error against both optical depth and view angle for all three traversal rules. **The chapter's step 4, priced.** |
| `r1-factorisation-vs-tau.png` | The factorisation error per band over `τ ∈ [0, 2]`, with **every number `12` prints drawn as a dot on the curve it is supposed to lie on** — which is how the two separated round-trip forms were told apart. The 1.40 m table beneath it, all four ratios. |
| `r1-frame-factorisation.png` | The same claim in pixels: two frames differing only in where the multiplication happens inside the bake, the red-band difference map, and the frame error against the term error on the same axis. |
| `r1-lut-quality.png` | The table audited before it is believed: interpolation error against the closed form, and the two error laws separated by their **order in 1/n**. |
| `r1-pass-anatomy.png` | What the pass is allowed to see — the two buffers, the reject mask, the output; reversed-Z against forward-Z in metres per f32 step; and the one-triangle-not-a-quad claim counted at two resolutions. |
| `r2-two-paths.png` | **The two paths side by side at the same framing**, with the pixel integral beside them and the sun's road at 3×. The naive path's fireflies, the fix's road, and the reference's own failure to converge on a `cos^93493` lobe. |
| `r2-variance-vs-distance.png` | The mechanism in absolute units: total / resolved / removed rms slope against distance, the conservation identity holding at raster footprints, the specular response from two independent estimators, and the footprint's anisotropy — which is where the fix runs out. |
| `r2-error-and-cost.png` | The error against the pixel integral per distance for all four paths, `E[R]` against `12`'s roughness-Fresnel fit, and the frame time of each. |

The frames are display-encoded through `render.py`'s own ACES + sRGB curve at an
exposure **solved** from the reference frame's 99th luminance percentile (0.5544
here, printed in the caption). No measurement anywhere in this directory passes
through it.

## Still open

- **The surface is tilted, not displaced.** `12`'s three-rung hierarchy is
  "displaced geometry near, normal detail mid, statistical BRDF far"; rungs two
  and three are built and priced, rung one is not, and neither is the *seam*
  between one and two, which is the half of Bruneton's argument this directory
  cannot reach. `field.py` answers slopes and has no height field.
- **The removed-variance tensor is fed a scalar footprint.** The real footprint
  reaches an axis ratio of 401 in this frame and the whole residual error of the
  fix tracks that ratio. The interface change is `slope_var_points` taking a 2×2
  footprint covariance; it is `field.py`'s and not this directory's.
- **The far glitter is a 5σ tail** and the doctrine's Gaussian is thinnest
  exactly there. Cox & Munk's measured non-Gaussianity is not carried by
  anything in this project.
- **Whitecaps.** `12`'s cause three — the erf-of-Jacobian prefilterable coverage
  — needs a Jacobian, which needs displacement. Its two published arithmetic
  values are checked; nothing else about it is.
- **A structured environment.** The single most useful thing to do next is to
  run the same two paths against a sky with angular structure at the scale of
  the removed slope distribution, because that is what decides whether the fix
  is worth its 48%. This one has a disc and a gradient and nothing between.
- **The underwater branch** raises instead of drawing.
- **`Transparency & pass ordering`** is exercised only in its simplest form: one
  water plane compositing over one opaque frame. The per-body sorting rule is not
  built and cannot be, with one datum.
- **The chapter's τ-scaling tables** are reproduced to inside a band envelope but
  the exact quadrature and band that produced them is not recoverable from the
  text. Marked, not closed.
- **`slab_esc`'s 6.3e-5 quadrature bias** is diagnosed and not fixed, by scope.
- **The 442% post-silhouette patch** is reported and excluded. It is a property
  of screen space, not a defect to be tuned out, but a production pass would need
  a fallback there and this one has none.
