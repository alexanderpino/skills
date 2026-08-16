# Screen-space water — the raster reference

The other half of `../references/12-water-rendering.md`. The offline reference in
`../reference-impl/` carries 285 guarded quantities on the pool and 173 on the
sea, and every one of them is a statement about an **integral**. The chapter's
real-time sections are statements about **what you are allowed to do to that
integral before the frame starts** — split it, table it, sample it, drop the
part that refracts — and the offline path cannot test any of them, structurally:
approximation error is invisible to a code path that does not approximate.

    python3 validate_raster.py        # 95 rows, three tiers, ~26 s, non-zero exit on FAIL
    python3 validate_raster.py -v     # every tolerance's justification
    python3 validate_raster.py --fast # skip the two frame-level tiers
    python3 evidence.py               # the five r1- figures in gauntlet/raster/evidence/

| File | Owns |
|---|---|
| `lut.py` | The exit-transport table, baked **both ways**. `optics.slab_esc` / `slab_trap` on one side, the separated pair a table-builder writes on the other, and the half-texel discipline implemented correctly *and* incorrectly so the suite can measure the difference rather than assert it. |
| `scene.py` | The body (a shoaling shelf), the camera, the reversed-Z projection and its inverse, the opaque prepass that writes the two buffers the pass consumes, and `project_to_pixel` — the only thing a screen-space pass needs to re-sample a buffer somewhere other than at its own pixel. |
| `sswater.py` | **The pass.** The fullscreen triangle emitted from `SV_VertexID` and rasterized with a real coverage test; the chapter's four numbered pixel-shader steps in its own order; the composition, per leg; the helper-lane audit. |
| `offline.py` | The frame the pass is validated against. Same model, different machinery: analytic geometry, per-band refracted rays, `optics.slab_esc` / `slab_trap` evaluated at **every pixel's own three optical depths**. |
| `validate_raster.py` | 95 rows on `validate.py`'s harness. At least one absolute row per quantity. |
| `evidence.py` | The five `r1-` figures, every caption number formatted from the run that drew it. |

**Nothing here re-implements any physics.** `optics.py` and `atmosphere.py` are
imported across a path, never copied; `beach_plot.py` draws the figures;
`render.py` is not imported at all (8966 lines, minutes to run, prints on
import) and the two constants taken from it — the liner albedo and the paving
albedo — are quoted with their line number. The only physics **derived** in this
directory is one line, the sky's entry leg, and it has a photon walk on it.

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
| Wave normal cascades (the chapter's "two to four scrolling layers") | Every version needs a **noise-derived normal map**, and `render.py`'s header rule is *no texture, no Voronoi, no noise* | The chapter's own stated substitute — an analytic Gerstner normal sum — is `field.py`'s job, and wiring `field.py` into a flat-datum pass is a wave, not a paragraph |
| Per-pixel raymarching of a displaced surface | Needs the above first: there is nothing to march against | Fixed steps + 4–6 binary refinements against `field.py`'s summed cascades |
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

95 rows, three tiers, ~27 s. The harness, the tier meanings and the rule that a
tolerance comes from the **estimator's** error and never from the measured
disagreement are `validate.py`'s, deliberately.

**Every quantity has at least one absolute row.** A ratio-only guard has been
blind three times in this project, once dividing 0/0 and raising, so: coverage is
a pixel *count* with tolerance 0; depth precision is *metres*; the LUT is checked
on its *values* before any ratio; the frame comparison carries a *radiance* row
beside every relative one; and the factorisation error is reported as joint,
separated, and then four named ratios.

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
caption and its figure disagree the figure was not redrawn. All five are
regenerated by `python3 evidence.py` in about 40 s.

| Frame | What it settles |
|---|---|
| `r1-pass-vs-offline.png` | The pass beside the offline frame it is validated against, the difference map, and the error against both optical depth and view angle for all three traversal rules. **The chapter's step 4, priced.** |
| `r1-factorisation-vs-tau.png` | The factorisation error per band over `τ ∈ [0, 2]`, with **every number `12` prints drawn as a dot on the curve it is supposed to lie on** — which is how the two separated round-trip forms were told apart. The 1.40 m table beneath it, all four ratios. |
| `r1-frame-factorisation.png` | The same claim in pixels: two frames differing only in where the multiplication happens inside the bake, the red-band difference map, and the frame error against the term error on the same axis. |
| `r1-lut-quality.png` | The table audited before it is believed: interpolation error against the closed form, and the two error laws separated by their **order in 1/n**. |
| `r1-pass-anatomy.png` | What the pass is allowed to see — the two buffers, the reject mask, the output; reversed-Z against forward-Z in metres per f32 step; and the one-triangle-not-a-quad claim counted at two resolutions. |

The frames are display-encoded through `render.py`'s own ACES + sRGB curve at an
exposure **solved** from the offline frame's 99th luminance percentile (0.5544
here, printed in the caption). No measurement anywhere in this directory passes
through it.

## Still open

- **No waves.** The datum is flat in both paths. Every claim in *Ambient waves*,
  *Distance and filtering* and the whole variance/prefiltering doctrine is
  untouched by this directory, and the *Distance and filtering* section named in
  the brief is the one that remains with no code behind it — it needs slope
  variance, which needs a wave field, which needs `field.py` wired to a
  flat-datum pass.
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
