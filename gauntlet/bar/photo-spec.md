# The bar — frozen at intake, never edited

Three photographs of the reference pool, Aljezur (Portugal), 2026-08-10 18:41 WEST.
Sun computed for that place and time: **elevation 21.0°, azimuth 273.75°** (due
west), air mass 2.77. Pool depth **1.40 m**, blue liner.

The critics cannot open the photographs — they exist only in the requesting
conversation. This file is therefore the bar **as specification**, written from
them by the lead agent. Judge against this text and log those rounds as
`--mode rubric`, never `--mode blind`. Where a figure below is a visual reading
rather than a measurement, it says so.

## The overriding bar

> A viewer should have to **wonder whether it is a photograph**.

That is the standard. Not "good render", not "physically plausible". A single
synthetic tell anywhere in frame fails it, and the tell is usually not the water.

## A · Water colour

- Sunlit water reads a **bright, saturated turquoise**; shaded water a deeper
  teal-blue. Visual reading of sRGB values: lit ≈ `(120, 215, 225)`, shaded
  ≈ `(70, 165, 185)`. Treat as ±20 per channel, not as measurements.
- The shaded region under the shade sail is **clearly luminous** — roughly half
  the lit value, not a dark hole. A binary occluder cannot produce this.
- Saturation comes from the **blue liner**, not from a tint control: the water
  column can only subtract.

## B · The caustic net on the bed

- Cell size of order **15–30 cm**. Finer than that reads, in the words of the
  reference observer, "as if there is a vibrator in the water".
  > **Corrected mid-run.** This originally read "perhaps 25–40 cells across the
  > visible water", which was a proxy for cell size written when the frame held
  > the whole pool. After the scope ruling reframed onto ~3 m of water, that count
  > became unreachable while the size was exactly on spec — a bar defect, not an
  > artifact defect. **Judge the size in metres, not the count in frame.** Measure
  > it by autocorrelation if you can rather than by eye.
- **Low contrast and soft-edged.** The bright lines are *not* blown to white over
  most of the area, and the cell interiors stay recognisably turquoise rather than
  dropping to navy. This is the single most-missed property.
- Faint **colour fringing** on the fold lines (dispersion), visible on the
  highest-contrast edges only.
- No caustics at all inside the sail's shadow.

## C · Surface sparkle

- A **compact patch of isolated bright points**, not a broad shimmering road.
  Sparse enough to count individual glints near its edge.
- It sits where the water is locally rougher — over the return jet — while the
  surrounding water is comparatively glassy.
- Everything else on the surface is smooth: at this sun elevation and this camera
  height the specular path is otherwise unreachable.

## D · The jet, from the close-up photograph

- **Curved crest trains** whose apparent origin is *out in the water*, roughly a
  metre off the wall, with quiet water between that origin and the fitting.
- Crests are **sheared and curled**, not clean concentric rings — the drift
  refracts them.
- Crest spacing in the visible bands: order **5–15 cm** (visual reading against an
  estimated 2.5 m frame width).
- The disturbance is **gone by mid-pool**.

## E · Everything that is not water — **struck by owner ruling, wave 1**

> Re-frozen mid-run. The project owner ruled scenery out of scope: *"we are not
> going to place things like parasols or bushes"*. Recorded here rather than
> silently edited, because a bar that quietly follows the artifact is not a bar.

The renderer verifies **water**. Props are a different project, and a garden built
to pass a photorealism test would teach the chapter nothing. So:

- **Out of scope:** lawn, planting, hedges, background scenery, horizon, deck
  dressing, and the shade sail *as an object*. Do not invest in them; remove what
  exists.
- **Still in scope, because it is water physics and not decoration:** the
  waterline where water meets the pool wall — coping edge, wall thickness, wet
  band, meniscus. The critic's "the pool is a decal" finding stands.
- **The sail survives only as an occluder**, because the shadow gate is a
  documented claim: caustics vanish beneath it while the water stays luminous. Its
  *shadow edge on the water* must be in frame; the fabric itself need not be.
- **Composition follows from this.** Judge a frame filled by water, as the
  reference close-up is. "Would a viewer wonder whether it is a photograph" now
  means a photograph *of water*, which is both a fairer test of this artifact and
  a harder one — there is nowhere for the water to hide.

## F · Light, globally

- Long shadows everywhere, consistent with a 21° sun from due west.
- Sun colour distinctly **warm/golden** (air mass 2.77), not neutral white.
- The image tolerates a phone's rendering: contrast and saturation slightly above
  a raw ACES curve is acceptable and expected; anything that only works *because*
  of that grade is not.

## G · From inside the water — **added mid-run by owner ruling**

> Re-frozen mid-run. The project owner extended the scope: *"it has to look as
> good underwater as above water"*. Recorded here rather than silently appended,
> because a bar that quietly follows the artifact is not a bar.
>
> **This section is weaker evidence than A–F and must be judged as such.** There
> is no underwater reference photograph. A–F were written from three photographs
> of the reference pool; G is written from physics and from what underwater
> photographs of pools generally show. Where a criterion below is a derivation it
> says so; where it is a recollection of photographs in general it says that too,
> and a critic may not treat the two alike.

The same overriding bar applies: a viewer should have to wonder whether it is a
photograph. The submerged view is judged on the **same scene, same code, same
water** — a second renderer tuned to look good from below would fail this section
by construction, because the point of the view is that it cannot be tuned
independently. It is the strongest verification instrument in the project: every
above-water shortcut that survives by being invisible from a 33° downward view
becomes visible from underneath.

- **Snell's window is the composition.** The above-water world compresses into a
  cone of half-angle `asin(1/n)` — 48.5° green, 97° across. Outside it the surface
  is a **perfect mirror**, reflectance exactly 1, showing the bed, the walls and
  the step unit folded back down. There is no partial regime out there. *Derived.*
- **The rim carries a dispersive fringe of 0.39°**: critical angle 48.655° red /
  48.519° green / 48.268° blue on the implementation's own IOR triple, red outside
  blue. *Derived — from constants already in `render.py`.*
- **The sun sits 4.1° inside the rim, not overhead.** 21.0° elevation is 69.0°
  from vertical in air, refracting to 44.4° below the surface. It is crowded
  against the window's edge, where compression and dispersion are greatest.
  *Derived.*
- **Absorption reads as aerial perspective.** The water column now lies between
  camera and geometry, so `a = (0.25, 0.0565, 0.0092) /m` acts along the view
  path: transmission `(0.29, 0.75, 0.96)` at 5 m. Far geometry loses two thirds of
  its red and the frame goes cyan with distance, with contrast falling as it does.
  *Derived.* Note this puts a limit on the chapter's "the colour is the bottom,
  not the water", which is a claim about a view from above.
- **The surface, seen from below, is a moving wrinkled mirror**, and the caustic
  net on the bed is seen obliquely rather than face-on. Both are the existing
  wave field viewed from a new side; neither may be a separate effect.
  *Derived.*
- **What underwater pool photographs generally show**, offered as weaker
  criteria: the window's rim is the brightest thing in frame; the bed keeps its
  caustics but at much lower contrast than from above; near-field water is close
  to clear while anything past a few metres is a cyan haze; and there is a visible
  loss of *contrast*, not merely a colour shift, with distance. *Recollection of
  photographs in general, not of the reference pool. Judge accordingly.*
