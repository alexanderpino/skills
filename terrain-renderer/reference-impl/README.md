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

Numbers this reproduces, each stated in the chapter:
sun-disc penumbra 6.8 mm on the bed; caustic offset 1.37 m at 44.4 deg refraction;
jet surface footprint peaking 0.91 m downstream; local rms slope 0.09 against
0.053 far field; wake energy fan +-19 deg against a +-78 deg wavevector fan.
