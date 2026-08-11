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

## 9b · What is actually in pool water, and which parts of it are visible

The chapter rests `b_b ≈ 0` on "treated water" without saying what the treatment
puts in or why it does not show. Asked directly, and worth answering in the text
because it is the first thing a sceptical reader will challenge.

- **Chlorine is a UV absorber, not a visible one.** Hypochlorite peaks at
  **292 nm** with `ε ≈ 300–378 M⁻¹cm⁻¹`; hypochlorous acid at 235 nm. At a pool
  dose of 1–3 mg/L that is an absorbance of **0.5–1.5 per metre in the UV** —
  real, and why chlorine burns off in sun — while at 450–610 nm the band has
  decayed to far below water's own `a(450) = 0.0092 /m`. Chlorine does not colour
  pool water at any dose you would swim in.
- **Dissolved calcium is colourless. *Precipitated* calcium is not.** Ca²⁺ and
  carbonate absorb nothing in the visible, but past about pH 7.8 the calcium comes
  out of solution as microscopic CaCO₃ that stays in suspension — the standard
  cause of a milky pool. That is **scattering**, and it is the one ordinary
  impurity that genuinely breaks `b_b ≈ 0`.
- **The visible difference between the two is the diagnostic**, and the chapter
  should give it: absorption only subtracts, so it darkens and shifts hue with
  path; scattering **adds** a veiling glow, lifts shadows, hazes distance, and
  **blurs caustics**. A pool that has gone cloudy loses its caustic net before it
  looks obviously milky.
- **So a photograph measures its own scattering.** Sharp caustics at 1.40 m put a
  ceiling on `b_b` directly: the net's blur is set by the sun-disc penumbra, 6.8 mm
  at this depth, and any scattering contributing more than that would be visible
  as a softer net. Every reference frame in this run has a crisp net, so the
  reference pool's water is genuinely in the `b_b ≈ 0` regime — measured off the
  artefact rather than assumed. Put a number on the bound if you can (`?`).
- **Two impurities that *would* change the colour by absorption**, worth naming so
  the exception is bounded: **dissolved copper**, from an algaecide or a corroding
  heat exchanger, which really does tint water blue-green; and **coloured dissolved
  organic matter**, which absorbs blue and pushes the water toward green-yellow.
  Neither is present in a well-run pool, and both are absorbers, so both fit the
  existing machinery — they change `a`, not `b`.

## 9c · Turbid water — the missing axis, not a missing feature

Asked for directly, and it is the single generalisation this whole model still
lacks: **`b` as a free parameter instead of a stated zero.** Four separate backlog
items — the jacuzzi plume, submerged wall lights, the underwater camera's aerial
perspective, and this — are all waiting on the same thing, which is the `a`/`b`/`g`
split the chapter already demands from `liquidBody` and which nothing here
exercises. Building it once serves all four.

**Author it as a visibility distance, not as a coefficient.** Nobody knows what
`b = 0.35 /m` looks like; everybody knows "you can just see the bottom". Secchi
depth `Z ≈ 1.44/(c + K_d)` inverts to `a` and `b` and is the control an artist can
actually set. Bracketed at green (`a = 0.0565 /m`), with `K_d` crude and marked
`?`:

| `b` /m | reads as | `ω₀` | Secchi | caustic contrast |
|---|---|---|---|---|
| 0 | this project's pool | 0.00 | 12.7 m | 1.00 |
| 0.15 | faintly hazy | 0.73 | 4.7 m | 0.75 |
| **0.35** | **caustics half gone** | 0.86 | 2.5 m | **0.50** |
| 0.90 | bottom lost at 1.40 m | 0.94 | 1.1 m | 0.17 |
| 3.0 | milky, jacuzzi | 0.98 | 0.4 m | 0.00 |

**The order the symptoms arrive is the doctrine**, and it is not the order a
reader expects. Caustic contrast falls as the unscattered fraction along the sun
path, `exp(−b·1.96 m)`, so it **halves at `b ≈ 0.35 /m`** — where the Secchi depth
is still 2.5 m and you can see the bottom of a 1.40 m pool perfectly well. So:

1. **the caustic net fades first**, while the water still looks clear;
2. then shadows lift, because scattering *adds* where absorption only subtracts;
3. then distance hazes and the bed loses contrast;
4. then the water acquires a body colour and reads milky rather than tinted;
5. and from below, Snell's window loses its rim.

A renderer that reaches for a white tint at step 4 has skipped the three steps
that actually sell it, and steps 1–3 are cheap: a contrast multiplier on the
existing caustic pass and a depth-dependent haze, no volumetric integration at
all. That is the low tier of the ladder; the high tier is the same
single-scattering machinery the wall lights need.

Note `ω₀` rises to 0.73 by the time the water is only *faintly* hazy. Scattering
takes over the light budget long before it takes over the look, which is why
"treated water barely scatters" is a statement about a **very** narrow regime and
should be written as one.

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
