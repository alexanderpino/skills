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
jet surface footprint peaking 0.91 m downstream; local rms slope 0.09 against
0.053 far field; wake energy fan +-19 deg against a +-78 deg wavevector fan.
