# Caustics

A caustic is light concentrated by specular focusing: the sunlight woven across a pool floor, the
bright cardioid in a coffee cup, the pool of light under a glass of wine. It gets its own file
because it is the one common lighting phenomenon that **breaks the standard Monte Carlo
estimator** — not "is expensive", but has a sampling probability of exactly zero under the
techniques every path tracer is built around. Understanding *why* is what separates "add more
samples" from picking an integrator that can render it at all.

Scope split: the theory, the offline-correct methods, and the production controls live here.
**Real-time water caustics** — caustic maps, the masking contract, the depth and shadow gates —
live in the `terrain-renderer` skill's `references/12-water-rendering.md`; that chapter routes its
theory here.

## Table of contents
1. What a caustic is: the ray map and its singularities
2. Path notation, and why NEE cannot sample a caustic
3. The SDS problem: what even BDPT cannot render
4. Photon mapping and its progressive forms
5. Manifold methods: the principled answer
6. What production renderers actually ship
7. Roughness is the off switch
8. Dispersion, reflective caustics, and TIR
9. Real-time approximations
10. Debugging caustics

---

## 1. What a caustic is: the ray map and its singularities

Refraction (or reflection) maps each point `p` on the specular surface to the point `q(p)` it
illuminates on a receiver. Flux is conserved along the ray tube, so receiver irradiance is the
inverse of how much that map stretches area:

```
E(q) = E_source / |det( ∂q/∂p )|
```

The **caustic is the fold set** — the locus where `det ∂q/∂p → 0` and the expression diverges.
This is not a metaphor; it is the definition, and it dictates the shape of every caustic you have
ever seen.

**The structure is classified, not arbitrary.** For a smooth map of the plane into the plane, the
only structurally stable singularities are **folds** (curves) and **cusps** (isolated points where
two fold branches meet tangentially) — Whitney's theorem, and the foundation of catastrophe optics
(Berry & Upstill 1980). Consequences worth holding onto:

- A caustic network is made of smooth bright curves that close, run off the receiver, or end in
  cusps. It has **no triple junctions**. Cell-noise fakes (Worley/Voronoi) produce exactly the
  triple junctions a caustic cannot have, which is the structural reason they read as cracked
  glass rather than focused light.
- Brightness varies strongly *along* a fold and blows up at cusps, because `det ∂q/∂p` varies
  along it. Uniform-brightness lines are a tell.
- Higher singularities (swallowtail, butterfly, umbilics) appear in one-parameter families —
  which is why an animated caustic shows cusps colliding and annihilating rather than lines
  simply sliding around.

In reality the `1/|det|` divergence is regularized by diffraction and by the source's finite
angular size; in a renderer it is regularized by the source solid angle and by clamping. An
infinitely sharp caustic from a point light is a modelling error, not a goal.

## 2. Path notation, and why NEE cannot sample a caustic

Heckbert's regular-expression notation for light paths: `L` light, `E` eye, `D` diffuse (or any
non-delta) scattering, `S` specular (delta) scattering. A caustic is any path of the form

```
L S+ D E          # light, one or more specular events, a diffuse receiver, the eye
```

**Next-event estimation cannot sample through `S`.** At a delta-specular vertex the BSDF is a
Dirac distribution: exactly one outgoing direction has non-zero value. A shadow connection picks
the direction to the light, which will essentially never be that direction, so the evaluated BSDF
is zero. You cannot "connect" through a mirror or a refractive interface. This is a structural
property of delta BSDFs, not a numerical accident.

So a unidirectional path tracer starting from the eye finds `LSDE` only by BSDF-sampling from the
receiver, refracting through the interface, and *happening to land on the light*. The probability
is the light's solid angle as seen after refraction. For the sun (0.53°, ~1/8000 of the
hemisphere) that is high variance. For an idealized **point or directional light it is exactly
zero**, and the caustic renders as pure black — a result many people first meet as "my pool floor
has no caustics no matter how many samples I throw at it".

**Bidirectional path tracing fixes `LSDE`.** Trace a subpath from the light: `L → S` (deterministic
refraction) `→ D` on the receiver. That `D` vertex is non-delta, so it can be connected to the eye
by an ordinary shadow ray. BDPT with MIS handles single-interface caustics well, and this is the
minimum bar for an integrator you expect to render a caustic at all.

## 3. The SDS problem: what even BDPT cannot render

Now put the observer *under the same interface* — the pool floor, lit by caustics through the
surface and **viewed through that same surface**:

```
L S D S E
```

Every BDPT connection strategy joins one light-subpath vertex to one eye-subpath vertex with a
deterministic shadow ray. Here the only non-delta vertex is the `D` in the middle, and it has a
specular vertex on *both* sides. Any strategy either

- connects at `D`, which requires evaluating an adjacent `S` BSDF at a direction it did not
  sample — zero; or
- generates the whole chain by sampling, which requires the eye subpath to refract through `S` and
  land exactly on the `D` that the light subpath also reached — a measure-zero coincidence.

So **SDS paths are unrenderable by unidirectional PT and by BDPT alike.** This is the canonical
hard case, and its two textbook examples are the pool bottom seen through the water surface and a
light-bulb filament inside its glass envelope. Anything that renders it does so by breaking the
delta — either by density estimation (§4) or by solving for the specular chain (§5).

## 4. Photon mapping and its progressive forms

**Photon mapping** (Jensen 1996) sidesteps the connection problem entirely. Trace particles from
the light; let them refract deterministically through `S`; store them where they land on `D`. Then
from the eye, refract through `S`, arrive at `D`, and estimate radiance by **density estimation**
over the nearby stored photons. The density estimate replaces the impossible connection with a
local average, so `SDS` is handled without difficulty.

The trade is bias: a finite kernel radius blurs the caustic — precisely the feature (sharp folds)
you were trying to render.

- **Progressive photon mapping** (Hachisuka, Ogaki & Jensen, SIGGRAPH Asia 2008) shrinks the
  radius across passes at a rate that keeps the estimator **consistent** — the result converges to
  ground truth with bounded memory. **Stochastic PPM** (Hachisuka & Jensen 2009) adds distributed
  effects (DOF, motion blur, glossy reflection) to the same scheme.
- **Vertex connection and merging / unified path sampling** (Georgiev et al. and Hachisuka et al.,
  both 2012) MIS-combines BDPT's connections with photon mapping's merges, so each mechanism
  covers what the other cannot. This is the practical high-water mark for a general integrator
  that must handle caustics among everything else.

Dedicating photons to caustics specifically — a separate caustic photon map with much higher
density than the global one — is the classic optimization and remains what most photon-based
production paths do.

## 5. Manifold methods: the principled answer

The other way out is to stop treating the specular chain as something to sample and start
**solving** for it. Given a light position, a receiver position, and a specular interface, the
admissible connecting paths form a low-dimensional manifold defined by the half-vector (Snell)
constraints at each specular vertex. Newton's method walks to a solution.

- **Metropolis light transport** (Veach & Guibas 1997) reaches caustics by mutating an existing
  path and staying in high-contribution regions once found — effective, but with the stratification
  and start-up quirks of MCMC.
- **Manifold exploration** (Jakob & Marschner, SIGGRAPH 2012) formalizes the specular manifold and
  makes the walk a first-class operator, sharply improving MLT on `SDS`.
- **Manifold next-event estimation** (Hanika, Droske & Fascione, *Computer Graphics Forum* 34(4),
  2015, 87–97) applies the walk to NEE itself: from a receiver point, deterministically solve for
  the refraction point on the interface that connects to the light. This makes ordinary NEE work
  *through* a refractive interface — exactly the pool case — and it does so outside a Markov chain.
- **Specular manifold sampling** (Zeltner, Georgiev & Jakob, *ACM TOG* 39(4), SIGGRAPH 2020) makes
  the solve stochastic and unbiased, with no precomputed seed paths, and unifies high-frequency
  caustics with glint rendering in one framework. This is the current state of the art to reach for
  when correctness matters.

## 6. What production renderers actually ship

Worth knowing, because it explains why so many production images have soft, weak caustics:

- **Opt-in caustic flags.** Per-light and per-object switches that enable caustic paths only where
  an artist asked for them. Caustics are off by default in most production configs.
- **Roughness clamping on secondary bounces.** Raise a floor under roughness after the first
  bounce, so the delta lobe becomes narrow-but-samplable and NEE starts working again. It removes
  the `SDS` singularity outright and is probably the single most common caustic treatment in
  production. It is a deliberate bias, and blurrier caustics are the price.
- **Firefly clamping, carefully.** Caustic paths carry large `throughput/pdf` ratios, so a naive
  radiance clamp deletes the caustic along with the outliers. Clamp per path-type, or clamp late,
  or accept the noise.
- **Denoising.** Caustics are high-frequency *lighting* on a low-frequency albedo, so
  albedo-demodulating denoisers handle them better than one might expect. The failure is temporal:
  a caustic moves independently of the receiver's motion vectors, so reprojection smears it. Feed
  the denoiser a separate caustic AOV or disable temporal accumulation for it.

## 7. Roughness is the off switch

Caustic contrast is a competition between two angular scales: the specular lobe width and the
angular width of the fold. As roughness rises the lobe smears the ray map, folds broaden and
overlap, and past a threshold the structure dissolves into a smooth glow with no lines at all.

Practical consequence: **caustics are a low-roughness phenomenon.** Above roughly `alpha ≈ 0.1–0.2`
GGX, expect a bright patch, not a pattern — and treat "my caustics vanished when I roughened the
glass" as correct behaviour rather than a bug. The same reasoning is why roughness clamping (§6)
works as a mitigation and why it costs you the sharpness.

## 8. Dispersion, reflective caustics, and TIR

- **Dispersion.** The fold set is wavelength-dependent because IOR is. In a spectral renderer the
  per-wavelength folds separate naturally and caustic *edges* pick up colour — the highest-contrast
  feature in the image is exactly where the separation shows. In an RGB renderer, refracting three
  channels with three IORs is the cheap approximation.
- **Reflective caustics (catacaustics)** are the same mathematics with reflection instead of
  refraction, and they are the most-seen caustic in the world: the bright cusped curve in a mug of
  coffee is the catacaustic of the cylindrical wall, complete with the cusp the classification
  predicts. It is *not* refractive, and modelling it as a refraction through the liquid gets it
  wrong.
- **Total internal reflection** adds specular vertices to the chain, producing secondary and
  tertiary caustics inside dielectrics — the structure inside a glass block or a wet sphere. These
  are `LSSSDE`-class paths and are precisely what makes brute-force approaches hopeless and
  manifold methods attractive.

## 9. Real-time approximations

Rasterized real time gives up on solving light transport and builds the ray map directly:

- **Caustic maps** — from the light's point of view, refract at the surface, compute where each ray
  lands, and rasterize/splat those receiver positions into a texture. Folds emerge for free
  wherever several rays accumulate in one texel. Shah, Konttinen & Pattanaik (IEEE TVCG 13(2),
  2007) and Wyman & Davis (I3D 2006) are the canonical formulations.
- **Ray-traced photon splatting** (DXR) — trace real photons through the surface, splat them into a
  caustic buffer, optionally resample. Correct fold structure including multi-branch and TIR
  caustics, at hero-asset cost.
- **Authored or procedural fakes** — scrolling textures, cell noise. Cheap and structurally wrong;
  see §1 for exactly why, and terrain-renderer `12` for when shipping one is nevertheless the right
  call.

For water specifically — the depth fade, the extinction along the light path, the sun-visibility
gate at the surface entry point, and the irradiance-not-albedo rule — go to terrain-renderer
`references/12-water-rendering.md`.

## 10. Debugging caustics

| Symptom | Cause |
|---|---|
| Caustics are pure black, at any sample count | Point or directional light (zero solid angle) with a unidirectional integrator. Give the light finite area, or switch to a caustic-capable integrator |
| Caustics render through a single interface but the floor seen *through* the surface stays black | The `SDS` case (§3). No amount of BDPT will fix it — needs photon mapping or a manifold method |
| Extreme fireflies concentrated on the receiver | Correct behaviour of an under-sampled caustic, not a bug. Clamping alone will delete the effect (§6) |
| Caustics far too soft in a renderer that should be exact | Secondary-bounce roughness clamping is on |
| Caustics disappeared when roughness was raised | Expected (§7) |
| Bright lines meet in three-way junctions | A cell-noise fake, not a caustic (§1) |
| Caustic smears or ghosts in animation | Temporal denoiser reprojecting caustics with the receiver's motion vectors (§6) |

## Sources

- Whitney, H., "On Singularities of Mappings of Euclidean Spaces I: Mappings of the Plane into the
  Plane", *Annals of Mathematics* 62 (1955) — fold/cusp stability. Attribution from model
  knowledge, not re-verified against the paper.
- Berry, M.V. & Upstill, C., "Catastrophe Optics: Morphologies of Caustics and Their Diffraction
  Patterns", in E. Wolf (ed.), *Progress in Optics* 18, North-Holland (1980), 257–346. Venue,
  volume and pages verified 2026-08.
- Heckbert, P., "Adaptive Radiosity Textures for Bidirectional Ray Tracing" (SIGGRAPH 1990) — the
  `L(D|S)*E` path notation.
- Jensen, H.W., "Global Illumination using Photon Maps" (Eurographics Rendering Workshop 1996);
  *Realistic Image Synthesis Using Photon Mapping* (2001).
- Hachisuka, T., Ogaki, S. & Jensen, H.W., "Progressive Photon Mapping" (SIGGRAPH Asia 2008);
  Hachisuka & Jensen, "Stochastic Progressive Photon Mapping" (SIGGRAPH Asia 2009).
- Georgiev, I., Křivánek, J., Davidovič, T. & Slusallek, P., "Light Transport Simulation with
  Vertex Connection and Merging" (SIGGRAPH Asia 2012); Hachisuka, Pantaleoni & Jensen, "A Path
  Space Extension for Robust Light Transport Simulation" (SIGGRAPH Asia 2012).
- Veach, E. & Guibas, L., "Metropolis Light Transport" (SIGGRAPH 1997).
- Jakob, W. & Marschner, S., "Manifold Exploration: A Markov Chain Monte Carlo Technique for
  Rendering Scenes with Difficult Specular Transport" (SIGGRAPH 2012).
- Hanika, J., Droske, M. & Fascione, L., "Manifold Next Event Estimation", *Computer Graphics
  Forum* 34(4) (EGSR 2015), 87–97. [Wiley](https://onlinelibrary.wiley.com/doi/abs/10.1111/cgf.12681)
  — authors, venue and pages verified 2026-08.
- Zeltner, T., Georgiev, I. & Jakob, W., "Specular Manifold Sampling for Rendering High-Frequency
  Caustics and Glints", *ACM TOG* 39(4) (SIGGRAPH 2020).
  [Project page](https://tizianzeltner.com/projects/Zeltner2020Specular/) — verified 2026-08.
- Shah, M.A., Konttinen, J. & Pattanaik, S.N., "Caustics Mapping: An Image-Space Technique for
  Real-Time Caustics", *IEEE TVCG* 13(2) (2007), 272–280.
  [IEEE Xplore](https://ieeexplore.ieee.org/document/4069236/) — verified 2026-08.
- Wyman, C. & Davis, S., "Interactive Image-Space Techniques for Approximating Caustics", I3D 2006,
  153–160. [ACM DL](https://dl.acm.org/doi/10.1145/1111411.1111439) — verified 2026-08.

Entries without a link were not web-checked in this pass; treat their author/year details as
believed-correct model knowledge. The roughness thresholds in §7 are practical ranges, not measured
constants.
