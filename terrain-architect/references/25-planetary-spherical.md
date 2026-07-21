# Planetary & Spherical Worlds

The **whole-globe altitude**. The skill already has one-landform (`00`), one-province (`20`),
one-multi-biome-world (`13`), and whole-generator (`23`) rungs; this is the missing one — *a planet*,
a finite sphere that closes on itself. It is a **consolidating** chapter: the hardest layer, the
spherical grid and its seams, is already specified in `08` and is not repeated here. This chapter owns
what changes *above* the grid — tectonics that move as rotations, climate that bands by latitude, a sea
level that is an equipotential, noise that must live on the sphere, and the precision/LOD reality of a
6371 km world — and routes each ingredient to its home chapter. Read it when the requested output is a
planet (Earth-like or alien), a globe, a spherical world, or planetary-scale terrain.

Contents: [The planetary frame](#the-planetary-frame) · [The grid is already decided in 08](#the-grid-is-already-decided-in-08) ·
[Tectonics on a sphere](#tectonics-on-a-sphere) ·
[Global circulation and the climate bands](#global-circulation-and-the-climate-bands) ·
[Ocean heat transport](#ocean-heat-transport) · [Sea level is an equipotential](#sea-level-is-an-equipotential) ·
[Noise on the sphere](#noise-on-the-sphere) · [Scale, precision, LOD, streaming](#scale-precision-lod-streaming) ·
[Alien planets: the regime knobs](#alien-planets-the-regime-knobs) · [Where the pieces live](#where-the-pieces-live) ·
[What to verify](#what-to-verify) · [Provenance](#provenance) · [Implementation contract](#implementation-contract)

## The planetary frame

A planet is not "a bigger heightfield". Three things change the moment the domain is a globe, and every
section below is a consequence of one of them:

1. **The domain closes on itself, and the terrain is a field on that closed surface.** There is no
   rectangular grid without a singularity; the grid decision is `08`'s cube-sphere-vs-HEALPix call, and
   everything that runs on it inherits seams and per-cell distortion. The height field is a function on
   the sphere `S²`, so it must be **continuous (ideally C¹) everywhere on the real surface**. The two
   **poles**, the **±180° meridian**, and the **cube-face edges** are *chart artifacts*; the **equator**
   is not even that — just a latitude line, a seam only if you wrongly split the sphere there. **None is a
   boundary**; the sphere has no special points, and a crease at any of them is a bug, not a feature.
2. **Direction is not constant.** "Down" is toward the centre, "north" rotates over the surface, and a
   straight line is a great circle. Plate motion, wind deflection (Coriolis), and sea level all depend
   on where you are on the sphere — they cannot be baked as global constants.
3. **Latitude is a first-class coordinate.** Insolation, and therefore temperature, circulation, and
   biome bands, are organised by latitude and axial tilt. On a flat map you *authored* a climate; on a
   planet the climate has a *structure* you can get right or wrong.

The doctrine of the flat pipeline still holds — heightfield (now on the sphere) as the solid truth,
process history, mass conservation, verify-don't-trust (`SKILL.md`, `09`). This chapter does not suspend
it the way the voxel/streaming paradigm does (`24`); it *extends* it onto a curved, finite, rotating
domain.

## The grid is already decided in 08

Do not re-derive it here. `08` "Planetary / spherical domains" specifies the two grid families and their
trade-offs, and this chapter assumes you have chosen one:

- **Cube-sphere** — six flat face-grids; the twelve cube edges are seams with a *rotation* between
  faces; flow routing crosses them with halo cells + per-face rotation tables (**F**; no canonical
  paper — say so). Six faces = six of `08`'s tiles.
- **Geodesic / HEALPix** — icosahedral hexagons + 12 pentagons, or HEALPix's exactly-equal-area pixels
  (`N_pix = 12·N_side²`, Górski et al. 2005); no face seams, non-rectangular neighbours. Real published
  flow routing exists (Liao et al. 2020, 2025).

The **one correction that leaks into every process below**: a fixed-resolution grid sampled through any
projection carries a per-cell scale factor `h` (Snyder 1987), and true ground distance is
`Δground = Δpixel / h`. Erosion, plate velocity, wind advection, and diffusion are all rates *per unit
ground distance* — divide gradients by `h` or the whole planet biases toward its high-distortion
regions, exactly as `normalize` breaks world units on the flat pipeline (`10`, `08`). Every rate in the
sections below is implicitly `/h`.

## Tectonics on a sphere

`02`'s uplift-and-flexure machinery is correct but **planar** — plates translate, flexure is a Fourier
`∇⁴` over a rectangle. On a sphere the kinematics change, and this is the single most distinctive
planetary process:

**Plates move as rigid rotations about an Euler pole, not translations.** By Euler's theorem, any motion
of a rigid cap on a sphere is a rotation about an axis through the centre; the axis pierces the surface
at the **Euler pole**. This is the founding result of plate tectonics — **McKenzie & Parker 1967** (*The
North Pacific: an example of tectonics on a sphere*, Nature 216; independently **Morgan 1968**). Two
load-bearing consequences for a generator:

- **Transform boundaries trace small circles about the Euler pole**, and **spreading rate ∝ sin(angular
  distance from the pole)** — zero at the pole, maximal 90° away. So a ridge does not open at a uniform
  rate along its length; get this and mid-ocean-ridge geometry falls out for free, miss it and the
  plate boundaries look authored.
- **Boundary type is set by the relative velocity across it:** convergent → subduction/collision
  (uplift, arcs, orogens → feed `02`/`04`), divergent → ridge (new crust, age-depth subsidence, `12`),
  transform → shear (offset, seismicity).

**The graphics realization is a real, citable paper:** **Cortial, Peytavie, Galin & Guérin 2019**
(*Procedural Tectonic Planets*, Computer Graphics Forum 38(2), Eurographics 2019) — it *approximates*
subduction and collision to deform the lithosphere under user-controlled plate motion, producing
continents, oceanic ridges, mountain ranges and island arcs, then amplifies with procedural or
real-elevation detail. This is the P-tier anchor for whole-planet tectonics; use it as the design, then
hand the resulting uplift field to the stream-power/erosion backbone (`04`) exactly as on the flat
pipeline. Related planet work: *River Networks for Instant Procedural Planets* and *Real-Time
Hyper-Amplification of Planets* (same LIRIS group) — verify authors/venue before citing.

```
tectonicPlanet(sphere, plates):
    for each plate p:  p.euler = (pole_axis, omega)          # a rotation, not a vector
    classify each boundary by relative velocity across it     # conv / div / transform
    for step:
        move plate caps by their Euler rotations              # small circles about each pole
        convergent → uplift + crustal thickening (02); ridge → new crust + age-depth (12)
    → global uplift field U  →  stream power + erosion (04)   # the flat backbone, on the sphere
```

## Global circulation and the climate bands

`13` models climate **locally** — lapse rate, orographic rain, aspect insolation — and takes a wind
direction as input. On a planet, that wind direction and the base temperature/precipitation field have a
**global structure** set by differential solar heating and rotation, and `13` should be *driven* by it,
not have it hand-waved. The structure is the three-cell circulation of each hemisphere:

| Latitude band | Cell / regime | Surface wind | Moisture → biome |
|---|---|---|---|
| ~0° (equator) | ITCZ, rising air | calm (doldrums) | wet → rainforest |
| ~0–30° | Hadley cell | **trade winds** (easterly) | drying poleward |
| ~30° (subtropics) | descending air, subtropical highs | calm (horse latitudes) | **dry → deserts** (Sahara, Australia) |
| ~30–60° | Ferrel cell | **westerlies** | wet mid-latitudes |
| ~60° | polar front, rising air | — | wet |
| ~60–90° | Polar cell | **polar easterlies** | cold-dry |

Two facts do most of the work: **deserts sit at ~30°** (subtropical descent), and **rainforest sits at
the equator** (ITCZ). **Coriolis** deflects the meridional flow into the zonal trade/westerly bands
(right in the northern hemisphere, left in the southern). This is textbook atmospheric science — the
Hadley cell is **Hadley 1735** — but its *terrain-generation realization is F*: author the banded base
wind and a latitude precipitation profile, then let `13`'s orographic model add rain shadows on top
(wet windward, dry lee). **Axial tilt** swings the bands seasonally (the ITCZ migrates toward the summer
hemisphere), which is where monsoons come from; for a static map, place the bands at annual-mean
latitudes and move on.

The payoff: biome placement stops being noise and becomes *structured* — a designer who puts a desert at
the equator or a rainforest at 30° is now visibly wrong, and the multi-biome doctrine of `13`/`20`
(one substrate, masks vary parameters) gets its masks from a physically-motivated field instead of an
arbitrary one.

## Ocean heat transport

A second-order but high-value correction to the bands above. Wind-driven **gyres** carry heat poleward on
**western boundary currents** (warm — Gulf Stream, Kuroshio: mild west-facing continental margins) and
equatorward on **eastern boundary currents** (cold, with coastal **upwelling**). The upwelling one is the
load-bearing case for terrain: cold water offshore suppresses rain and produces the **coastal fog
deserts** — the **Namib and Atacama** sit against cold currents at latitudes that are otherwise not
extreme. If a brief wants a desert *on a coast*, this is the mechanism; realize it as a cool, dry
modifier along the relevant margins (F for terrain use; the physics — Ekman transport, Sverdrup balance,
Stommel western intensification — is P but out of scope to simulate).

## Sea level is an equipotential

On the flat pipeline "sea level" is a constant height and flood-fill is trivial. On a planet it is an
**equipotential surface of the gravity+rotation field — the geoid** — not a constant radius:

- **Rotation makes the planet an oblate spheroid.** Earth's flattening is `f ≈ 1/298` (equatorial radius
  ~21 km larger than polar). Sea level is *further from the centre at the equator*; a "constant radius"
  ocean would pool at the poles. For most game planets, model the reference surface as the spheroid and
  measure height relative to it, not to a sphere.
- **Flood-fill still works, on potential not radius.** Fill from the ocean to a chosen equipotential;
  a spill happens where the *potential* (not the raw radius) crosses the threshold. In practice, at game
  fidelity, subtract the reference-spheroid radius from your height field first, then treat the residual
  like the flat case (`03` sea level, lakes). Say explicitly whether you modelled the spheroid or
  approximated it as a sphere — the approximation is fine for small worlds and visible on large ones.

## Noise on the sphere

Do **not** *generate* by sampling a 2D lat–long noise map and wrapping it — it pinches at the poles and
seams at the ±180° meridian, the noise-domain twin of the pole-pinch grid problem. Instead **evaluate 3D
noise at the surface point on the unit sphere** (`p = radius·normalize(...)`, feed `p` to 3D
Perlin/Simplex/OpenSimplex), so the field is seamless and pole-free by construction — `01` already
carries the 3D noise and the lattice-rotation caveat (a plane through 3D noise bands; the sphere avoids
that but watch axis-aligned sampling near faces). FBM, ridged, and domain warp all compose on the sphere
by warping the 3D sample point. For an *animated* planet (evolving continents, weather), use **4D noise**
with time as the fourth axis. This is folklore — **F**, no canonical paper — but it is the standard and
correct practice, and it is why planet renderers *generate* on 3D/4D noise rather than on an
equirectangular map.

Sampling the **3D surface point** is what buys continuity *everywhere on `S²` for free* — no pole, no
±180° seam, and crucially **no equator**. The classic way to break equatorial continuity is to generate
the two hemispheres separately (a north heightmap and a south heightmap), or to mirror one onto the
other — both leave a crease along the equator, and mirroring also makes an unrealistically symmetric
planet. The equator is not a boundary; do not build one there. If you want hemisphere symmetry, flip the
*climate forcing sign* across the equator (the insolation flip in `13`), never the terrain itself.

This bans equirectangular as a **generation/simulation grid**, not as a format. Equirectangular (plate
carrée) is the **standard planetary interchange and delivery raster** — real DEMs (Mars MOLA, Moon LOLA,
Earth SRTM/GEBCO) ship that way, and "generate a planet heightmap" usually means *deliver an
equirectangular one*. So the pipeline is: generate/simulate on the equal-area grid, then **resample to
equirectangular for output** (and resample imports the other way), with `cosφ` weighting and the ±180°
seam handled. The full I/O treatment — scale factor, pole rows, the resample rule — is in `08`.

## Scale, precision, LOD, streaming

A planet is ~6371 km; a 32-bit float has a 24-bit mantissa (~7 significant digits), so at Earth's radius
the representable step (ULP) is already **~0.5 m**, and compounded transform and normal-derivation error
pushes visible **vertex jitter and z-fighting into the metre range**. This is the same floating-origin
problem `08` flags, now unavoidable:

- **Compute per-patch in a local frame.** Translate each rendered patch to a local origin (camera-
  relative or patch-relative) and do the fine work in float32 there; keep the global position in
  float64 or integer world coordinates. (Floating origin is **F** — Thorne 2005; widely used, not a
  strong result.)
- **LOD is a quadtree per cube face** (or per HEALPix base pixel): chunked-LOD / CDLOD (`08`) subdividing
  toward the camera, with **horizon culling** — on a sphere, whole faces fall below the horizon and cost
  nothing. Crack-prevention across LOD levels and across face seams is the `08` seam problem again.
- **Streaming and hybrid generation** are `23`: bake the global process history (plates, drainage,
  climate bands) at coarse resolution, stream it, and synthesise deterministic local detail per patch —
  the same bargain as any infinite world, because a full-resolution global heightfield of a planet does
  not fit in memory. GLOBAL processes (plate motion, drainage) are baked or async-region; only LOCAL
  detail runs per patch.

## Alien planets: the regime knobs

`SKILL.md`'s "Off-Earth: mind the gravity and the missing water" doctrine is the selector, and `20`
Group L is the worked *surface* archetypes (lunar highlands, maria, Mars-type relict worlds). This
chapter adds the *global* consequences of turning the two knobs:

- **No liquid water → no fluvial backbone.** The erosion chapter (`04`) largely switches off; the surface
  is **impact cratering** (`11`) plus, with an atmosphere, **aeolian** (`05`, `16`). The climate bands
  above still exist if there is an atmosphere (Mars has Hadley circulation and dust storms), but they
  transport dust, not rain.
- **Gravity rescales the physics.** Crater size scales with `~1/g` (Melosh 1989 π-scaling; `11`), dune
  wavelength and saltation shift with gravity and air density (Kok et al. 2012; `05`, `16`), while the
  repose angle is nearly gravity-independent (talus still ~34° on Mars — a useful invariant).
- **Tidally-locked "eyeball" worlds** — a distinctive planetary regime: one face permanently sunlit, one
  dark. Circulation is a single substellar-to-antistellar cell, not latitude bands; a substellar ocean/
  ice-cap, a terminator ring, a frozen night side. The astronomy is real (exoplanet literature); the
  terrain realization is **F** — author the substellar-centred climate field instead of the
  latitude-banded one, then run the same erosion/aeolian machinery under it.

The rule is `SKILL.md`'s: **pick the dominant agent from the world, not from habit** — same operators,
different weights and constants.

## Where the pieces live

This chapter consolidates; it does not duplicate. Build each layer from its home:

| Planetary layer | Build it from |
|---|---|
| Spherical grid, seams, distortion `h`, flow across seams, DEM/output | `08` |
| Euler-pole plate motion → uplift field; then erosion backbone | this chapter + `02`, `04` |
| Local climate (lapse, orographic rain, snow line) driven by the global bands | `13` |
| Impact cratering, lithology, volcanism (dominant off-world) | `11`, `19` |
| Age-depth ocean-floor subsidence, coasts, reefs | `12` |
| 3D/4D noise on the sphere; FBM/ridged/warp | `01` |
| Equirectangular / real-DEM (MOLA, LOLA, SRTM, GEBCO) import & delivery — resample to/from the working grid | `08` |
| LOD (quadtree per face, CDLOD), floating-origin precision, streaming | `08`, `23` |
| Specific worlds — lunar, Mars, icy moons | `20` Group L |
| Regime selection (gravity / water) | `SKILL.md` doctrine |

## What to verify

The flat `09` oracles still apply *inside a face*; the planetary additions are:

- **Continuity everywhere on `S²` (the `08` check, generalised).** Height and drainage area `A` are
  continuous and resolution-consistent across every cube-face seam and the ±180° meridian;
  **single-valued and continuous *through* each pole** (every longitude agrees at the point, and the
  field passes over it — meridian λ continues as λ+180° — without a kink); and **no crease along the
  equator** (the tell-tale of hemisphere-separate generation). No pole pinch. Walk a great circle over
  each pole, and a meridian across the equator, and diff — a spike localises the seam.
- **Distortion neutrality.** Gradients divided by `h`; erosion and drainage do not bias toward
  high-distortion faces/regions (histogram drainage density per face — it should not spike where cells
  are largest).
- **Hypsometry is bimodal for an Earth-like world.** The area–altitude curve (Strahler 1952; `09`, `20`)
  has two modes — continents and abyssal plains — not the single mode of a noise planet. A unimodal
  hypsometry means you have a lumpy ball, not continents-and-oceans.
- **Climate bands are in the right place.** Deserts cluster near ±30°, wettest near the equator, ice
  toward the poles. If the desert mask lands on the equator, the circulation forcing is wrong.
- **Mass and area close globally.** Erosion/deposition balances over the whole sphere (`09`
  mass-conservation), and an equal-area check (HEALPix pixels, or `Σ cell_area = 4πR²`) confirms the grid
  isn't silently losing area at the poles.

## Provenance

Mixed-tier, and honest about which is which:

- **Spherical grids & distortion — P, and already in `08`:** cube-sphere/equiangular (Chan & O'Neill
  1975; Sadourny 1972; Ronchi et al. 1996), HEALPix (Górski et al. 2005), scale factor (Snyder 1987),
  DGGS flow routing (Liao et al. 2020, 2025). Cube-face-*seam* flow routing is **F**.
- **Tectonics on a sphere — P:** Euler-pole rigid-plate rotation (**McKenzie & Parker 1967**, Nature 216;
  **Morgan 1968**); the graphics realization is **Cortial, Peytavie, Galin & Guérin 2019**, *Procedural
  Tectonic Planets*, CGF 38(2) (Eurographics 2019). Verify the related planet papers before citing them.
- **Global circulation — P physics, F realization:** the three-cell model and Coriolis are textbook (the
  Hadley cell is Hadley 1735); the *terrain-generation* realization (authored bands + latitude
  precipitation profile) has no canonical graphics paper. Ocean-gyre heat transport is P physics
  (Ekman/Sverdrup/Stommel), F for terrain use.
- **Geoid / oblate spheroid — P geodesy:** standard; Earth `f ≈ 1/298`. The game-fidelity
  "subtract reference spheroid, then treat as flat" is an approximation — label it.
- **Sphere noise, floating origin, per-face LOD — F engineering:** 3D/4D noise on the sphere is standard
  practice with no paper; floating origin is Thorne 2005 (folklore); quadtree-per-face LOD is `08` engineering practice.
- **Alien regimes — doctrine + `20` L:** gravity/water selection (`SKILL.md`); tidally-locked climate is
  real exoplanet science, F for terrain.

Two traps this chapter guards, both `SKILL.md` discipline: **plate motion is a rotation, not a
translation** — a planet whose plates slide in straight lines is wrong at a glance; and **the circulation
bands are physics, not decoration** — placing biomes without them is the planetary version of "noise
alone never produces this".

## Implementation contract

Ship a planet only when every row holds:

- [ ] **Grid chosen and seam-clean.** Cube-sphere or HEALPix per `08`; height and `A` continuous across
      every seam, **through both poles, and across the equator** (no hemisphere-join crease); no pole
      pinch; slopes and areas metric-corrected for the projection scale factor `h` (`08`).
- [ ] **Plates rotate.** Motion is Euler-pole rotation (small circles about the pole; spreading
      rate ∝ sin(distance)), boundary type from relative velocity; the uplift field feeds the standard
      erosion backbone (`02`, `04`).
- [ ] **Climate is banded, then localised.** A latitude circulation field (trade/westerly/polar bands,
      deserts at ~30°, ITCZ at 0°) forces `13`'s local orographic model; biome masks derive from it.
- [ ] **Sea level is an equipotential.** Modelled on the reference spheroid, or the sphere approximation
      stated explicitly.
- [ ] **Noise lives on the sphere.** 3D (or 4D animated) noise sampled at surface points; no wrapped 2D
      map, no pole seam (`01`).
- [ ] **Precision and LOD are planet-scale.** Per-patch local origin in float32 over a float64/integer
      global frame; quadtree-per-face LOD with horizon culling; global processes baked/streamed, local
      detail per patch (`08`, `23`).
- [ ] **Regime picked from the world.** Gravity and liquid-water knobs set the dominant agent
      (fluvial / aeolian / impact), constants rescaled by gravity (`SKILL.md`, `11`, `05`, `20` L).
- [ ] **Verified on the sphere.** Bimodal hypsometry for Earth-like; bands in the right latitudes; global
      mass and area close; provenance recorded with tiers, no fabricated citations.
