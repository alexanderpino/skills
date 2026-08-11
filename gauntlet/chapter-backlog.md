# What the run learned that the chapter does not yet say

Collected at the end of wave 6, for the chapter round the owner has asked for
next. Everything here was **derived or falsified inside this run** and currently
lives only in `reference-impl/` comments, `README.md` backlog entries, the bar, or
the commit log. The chapter was kept current on the doctrine it already covered;
this is the part that has no home yet.

Ordered by how general it is. The first six are doctrine for any water renderer.
The last four are narrower but each cost a wave to find, which is the usual sign
that a reader would pay the same.

---

## 1 · Per-channel refraction is a sampling scheme, and it aliases on silhouettes

Three IORs are **three delta wavelengths** standing in for three broad sensor
bands. Measured here: the red and blue images of the bed land 9.8 mm apart, 2.07
output pixels, and 0.33% of water rays disagree about which surface they hit.

- On a **caustic fold** the integrand is smooth over that spread, so a three-point
  quadrature is fine — which is why fold fringing always looks right and nobody
  suspects the scheme.
- On an **opaque silhouette** the integrand is a step at exactly that scale, so
  three deltas resolve it as a **comb**: three separately-placed edges, and the
  pixel between them carries one primary with the other two missing. That is the
  saturated blue-and-yellow speckle on every refracted edge.

The fix is not more rays. `n(λ)` is a two-parameter Cauchy fit through the three
`(λ, n)` pairs you already have, bands are the Voronoi cells of the three
nominals, and the camera integrates its band across the subsample grid by a Latin
square of spectral strata — **zero extra rays**. Worth stating as doctrine
because the failure only shows where dispersion meets geometry, which is exactly
where a reader will not be looking.

Corollary the chapter should carry: **the light path is band-integrated too.**
Blue folds are physically softer than red ones — 9.6 mm of extra smear against
3.4 mm at 1.40 m, on a 6.8 mm sun-disc penumbra — which three deltas cannot
express at all.

## 2 · Distance filtering: narrow the distribution, and pick the kernel on purpose

The chapter has "Distance and filtering" but not the argument that decides the
kernel. A pixel integrates over its footprint, so a component of wavevector `k`
survives as `a·W(k)` with `W` the kernel's transfer function. That is exact and
assumes nothing about the field, so **the only real choice is `w(r)`**:

- **Box** — the literal footprint — is `sinc(k·fp/2)`: zeros at `fp = λ` and
  negative lobes to −0.217, so a band fades, **returns phase-inverted**, and fades
  again as the footprint grows with distance. A slow beat against distance, i.e.
  a moiré generator, which is the defect being removed.
- **Tent** is positive but still zeroed, and decays only as `1/k²`.
- **Gaussian** because it is positive and monotone, it is the only kernel
  simultaneously separable *and* isotropic — all a scalar footprint with no
  orientation is entitled to assume — and it composes under convolution.

Scale it deliberately: a box of width `fp` has σ = 0.2887·fp but still passes
0.663 of the amplitude at the Nyquist wavenumber, 44% of the variance straight
into the fold. Pinning half-amplitude at the Nyquist wavelength gives
**σ = 0.3748·fp**, and the whole filter reduces to one checkable sentence:
**a component is half gone when the footprint reaches half its wavelength**, 94%
gone at one wavelength.

Three more rules, each of which cost something here:

- **Attenuate amplitude, not variance.** Averaging is linear on the field, so it
  acts on the field and the resolved variance falls as `W²` by itself.
- **Filter per component, not per band.** A band spanning 17–70 mm has no single
  `k`; one nominal switches the band off instead of narrowing it.
- **Pass the *output* pixel's footprint, not the subsample's.** Shading is
  nonlinear in slope, so a field merely at the subsample Nyquist still makes
  radiance harmonics above it.

## 3 · Filtering without a receiver trades moiré for plastic

The removed variance has to go somewhere, and the chapter should say where. What
is removed is **not isotropic** — a wind band is a spread about one azimuth, a
wake is directional — so it is a tensor, and a lobe widened by its trace alone is
visibly wrong across the wind.

The mapping is derivable and is **not** the identity. An in-plane slope
perturbation swings the reflected ray by `2δ`, an out-of-plane one by
`2δ·cos θ_v`, so `C = J Σ Jᵀ` with `J = diag(−2, −2cos θ_v)` in the view-azimuth
frame. Validated here against 400k Monte-Carlo perturbed reflections: 4% on the
major axis, 8% on the minor. **The reflected ellipse is not similar to the slope
ellipse** — at a 33° camera it is stretched 1.8× along the view azimuth, an
anisotropy the slope tensor never had.

Convolving that into a `cos^n` lobe is closed-form: two Gaussians convolve to a
Gaussian, covariance adds, the integral is conserved, and writing it back as a
**directional** `n_eff` degenerates bit-for-bit to the unfiltered expression at
zero variance.

## 4 · A sun that is not a disc cannot make glitter, and the tell is a road

The single biggest visual finding of the run. A `cos^n` "sun" fitted by eye is an
**aureole**, not a disc: here it peaked 1563× too dim over a solid angle 7.8× too
wide, and all three sky lobes together carried **0.695 against a direct beam of
24.1** — a factor 35 short. The symptom is not a dim sun; it is that glitter
comes out as a **broad pale smear** where the physics has small blinding points.

Constrain it so nothing is left to choose: with `n = 2/θ_s² − 1`, `2π/(n+1)`
equals `Ω_sun` identically, so peak, width and flux land on the sun at once.

Two rules to state alongside it:

- **The environment must be the atmosphere the beam came through.** Adding
  aerosol scattering to the sky without removing it from the beam **creates the
  light twice** — measured here as a frame at 245/255 with the shadow ratio
  inverted. And dimming the beam means changing the sun colour, which relights
  every diffuse surface, so the pair is one change or neither.
- **A sun colour already encodes its atmosphere.** `exp(−m·τ_Rayleigh)` at air
  mass 2.77 reproduced this project's hand-set sun colour to one part in 10⁴,
  which fixed the air mass, proved the reddening was physics rather than a grade,
  and pinned the aerosol optical depth it was written with at zero. Worth saying
  outright: *read your sun colour back before you invent a sky.*

## 5 · Glitter reachability is a constraint on where the camera may stand

The chapter has the reachability test as a property of the surface. It is also,
and more usefully, a **layout constraint**, because all specular structure lies on
**one line in plan** — the sun's bearing through the eye. So:

- The mirror point (`r = 0`) is the **mode of every slope distribution**, so a
  broad road there cannot be removed by roughness, filtering or amplitude. If it
  is in frame, it is in the picture.
- A patch of rough water only out-glints calm water past a threshold contrast
  ratio, which makes the reachable band **a window, not a point**: here
  `|θ_v − 21°|` between 15.3° and 18.5°, with a steep branch and a grazing one.
- Therefore *where a photographer may stand* is determined by the sun and the
  feature, to within about half a metre laterally. This is the difference between
  a criterion being satisfiable and not, and it is cheap to compute before
  building anything.

## 6 · Depth is a field, and constants derived at one depth do not travel

Two real bugs here came from the same habit. A sun-disc penumbra kernel was
derived once at the deepest point and applied at every depth, smearing a 205 mm
shallow with **7× too much blur**; and a wall attenuated every texel as if lit
through the full slant path, so a texel 200 mm under the waterline was dimmed as
if under 1.96 m.

State the rule: **if the scene has more than one depth, every depth-derived
quantity is a function, not a constant** — the extinction path, the slant, the
penumbra, and the focusing number all at once.

---

## 7 · Interiors too dark and shadows too bright at once means a missing directional bounce

A diagnostic worth naming. A single flat ambient standing in for inter-reflection
produces **errors of opposite sign in the same frame**: it under-fills where a
nearby bright surface should be bouncing (caustic cell interiors on the floor came
out too dark) and over-fills where nothing should be (the shade sail's shadow came
out too bright). Either symptom alone reads as a tuning problem; together they
identify the mechanism.

Priced here: the walls take **35.3% of the bed's cosine-weighted hemisphere on
average and 77% at the worst texel**, and a flat sky ambient was applied over all
of it. Also **58%** of the total-internal-reflection return meets a wall before
reaching the surface. And it cannot be fixed with a better constant — the wall
runs 2.2× in red from waterline to foot.

## 8 · The waterline is the one specular feature that cannot fail

Already added to the chapter this run, but the general form is worth keeping in
view for the rewrite: a meniscus fillet sweeps **every** tilt from 0° to 90°
across ~5 mm, so it satisfies the mirror condition for any light at any sun angle
— while the open surface at the same moment is 10σ short. And the family is the
**bevel highlight**, not inverse ambient occlusion: AO is about visibility,
this is about orientation, and the two are opposite signs of one quantity,
curvature.

## 9 · Two mechanisms called "aerated water", and one number that runs both

Not in the chapter at all. Surf entrains air **at the surface**, so it lives as a
skin, is transient, spans microns to centimetres, and renders as a coverage mask
you cannot see into — and it throws **spray**, a third medium, water in air. A
jacuzzi injects air **at depth**, so it lives as a buoyant plume in the volume, is
steady, has a narrow bubble size, and renders as a participating medium you see
partly through.

The optics they share: an air bubble seen from the water side has the same 48.5°
critical angle as the surface seen from below, so the same **`1 − 1/n² = 43.9%`**
of everything striking a bubble wall is totally reflected. One constant runs the
mirror outside Snell's window *and* the whiteness of foam. And foam is white
rather than tinted because absorption needs a long path — transmission over 5 mm
is 0.999 in red — so **foam is many short paths where blue water is one long one**.

## 10 · The view from inside, and the split shot

Scoped in `reference-impl/README.md` and in bar sections G and H, unbuilt, and
absent from the chapter. Snell's window at `asin(1/n)` with a **0.39°** dispersive
rim from the same three IORs; total internal reflection making the surface an
exact mirror outside the cone; absorption acting along the **view** path for the
first time, which puts a boundary on the chapter's "the colour is the bottom, not
the water" — true from above, false from inside.

For the split shot, the load-bearing point is that **the split is a property of
the port, not the camera**: a point aperture gives a straight degenerate line, and
a real front element gives the waterline traced across it as a curve that
undulates with the waves. A flat port magnifies the submerged half by `n` — 25%
closer, 33% larger, field 46° → 34.0° — while a dome restores it and narrows the
**air** half instead. **No port leaves both halves native**, so one straight edge
crossing the waterline says which port was modelled.

---

## Method notes, if the chapter wants them

- **Compare light to light.** A shadow ratio read off sRGB-encoded luminance
  against a claim about radiance was wrong by the encoding: 0.82 against a stated
  0.5, where the same two colours are 0.546 apart in linear light. Most of a
  reported defect was the units.
- **A ratio of targets is not a measurement.** Two figures in this
  implementation's own comments turned out to be one stated target divided by
  another, presented as measured.
- **Name the convention once, upstream of every consumer.** Two of five bands here
  normalised in the per-axis slope convention and three in the total, because
  both expressions divide by two and mean different things. It shipped for months
  and put two units on the two sides of one budget.
