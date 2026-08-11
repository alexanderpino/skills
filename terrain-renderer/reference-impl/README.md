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
| `render.py`| Light: the caustic pass, liner and tile materials, Fresnel, sky, camera, tone map. |

Sun position is the measured one for the reference photograph (Aljezur, 37.319N
8.803W, 2026-08-10 18:41 WEST): elevation 21.0 deg, azimuth 273.75 deg.

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
  where the water column sits between the camera and the far geometry, so
  `a = (0.25, 0.0565, 0.0092) /m` acts along the *view* path. Transmission at 5 m
  is `(0.29, 0.75, 0.96)` — the far wall loses two thirds of its red and the scene
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

Slope convention, everywhere in this directory and in the chapter: `s` is
`sqrt(<|grad h|^2>)`, the total mean-square slope, never the per-axis rms that is
smaller by sqrt(2). Two of the five bands were once normalised in the per-axis
convention while the rest used the total, which put two units on the two sides of
the slope budget; `field.rms_slope` exists so that cannot recur.
