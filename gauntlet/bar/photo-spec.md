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

### B2 · The edge, from a fourth photograph of the reference pool

> Supplied mid-run: a close frame of the coping meeting the water. Same status as
> A–F — this is the reference pool itself, not a stand-in — and it **settles a
> dispute** rather than adding a wish.

- **The waterline against the coping is a clean, straight, hard line.** No visible
  meniscus band, no damp band on the stone, no softening. A reviewer flagged the
  render's hard edge as a defect and I forwarded it; the photograph shows the
  reference pool doing exactly the same thing. **Do not soften this edge.** The
  meniscus and wet-band machinery belongs where the wall is visible, and there it
  already reads correctly. A future critic raising this again should be sent here.
- **The stone is warm sandstone — pink-tan, not grey.** The render's coping is a
  neutral grey-beige, which is a genuine mismatch against this frame. *Visual
  reading, not a measurement.*
- **The surface texture is finer and denser than the render's**, and carries a
  clear directional grain: many small wrinkles rather than a few large ones. The
  render currently reads coarser at the same apparent distance. *Visual reading.*
- **The caustics seen through that surface are softer and lower in contrast than
  the render's** — present and legible, but blended, with no hard bright lines.
  This is the same "most-missed property" as section B, now with a picture behind
  it. *Visual reading.*
- Overall the water reads **less saturated and greener** than the render's, which
  runs toward a purer cyan. *Visual reading; the lit-water red deficit already
  reported by three builders may be the same finding seen from the other side.*

### B3 · The meniscus line — a fifth photograph of the reference pool

> A frame looking steeply down at the wall. It refines B2 rather than reversing
> it: **two different edges are involved and they behave differently.**

- **The coping's arris stays hard** — B2 stands, unchanged.
- **The waterline against the wall carries a thin bright line**, running the whole
  length of the wall, sitting exactly at the junction and separating the shadowed
  near-water below from the lit water beyond.
- **The mechanism is the meniscus, and it is a certainty rather than a
  coincidence.** Water climbs a wetted wall to `h = a·√(2(1−sin θ))` with
  `a = √(σ/ρg) = 2.73 mm`: **3.86 mm** at perfect wetting, 2.7 mm at a 30°
  contact angle. The fillet is a few capillary lengths wide, so across roughly
  **5–10 mm** of surface the tilt runs continuously from 90° at the wall to 0° at
  the flat surface. That strip therefore contains **every** facet orientation, so
  the specular condition is satisfied somewhere in it for any light in the sky, at
  any sun elevation, on any day. *Derived.*
- **This is the one place on the surface where the glitter reachability test
  cannot fail.** A level eye and a 21° sun need a facet tilted ~34.5° to mirror
  the sun; the far-field rms slope is 0.058, i.e. 3.3°, which puts that tilt about
  **10σ** out — unreachable, exactly as section C says of the open surface. The
  meniscus reaches it by construction. Hence a bright waterline in essentially
  every pool photograph, including the ones where the open water is glassy.
  *Derived, and it explains a feature present in all five reference frames.*
- **What this asks of the render.** A meniscus term exists in the implementation
  but is applied as a dim ambient lift over a 10 mm scale. That is the wrong
  category: it should be a **specular** strip a few millimetres wide, catching sun
  and sky, and it should read as a *line* rather than as a softening. Getting it
  right also gets the sunlit-versus-shadowed split either side of it, which is
  what makes the edge read as a corner in three dimensions rather than a seam.

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

**Read from a supplied underwater reference** — a child on an inflatable, shot
from below looking up — and therefore stronger than the recollections above:

- **The sun is a blazing disc inside the window, not a gradient.** It reads as a
  small blown highlight with flare, sitting well inside the rim, while the rest of
  the window carries the compressed sky around it. *Photograph.*
- **Anything touching the surface from below carries a mirrored twin.** The
  inflatable and its reflection in the surface's underside meet along the
  waterline, corrugations and all, so the object reads as doubled about that line.
  For this pool the same must hold for the **wall and the coping seen from
  below**: the wall must meet its own mirror image at the waterline. It is the
  single most recognisable underwater cue after the window itself, and it comes
  free from the same surface. *Photograph.*
- **Bubbles are silvered spheres**, not pale dots — total internal reflection
  inside them mirrors the scene. Not needed for a still pool, but the mechanism is
  the same one that makes the surface a mirror outside the window, so a renderer
  that gets one and not the other has special-cased something. *Photograph.*
- **Translucent objects lit from above glow from within.** Out of scope here
  (nothing floats in this scene) but noted so it is not mistaken for a missing
  feature. *Photograph.*

## H · The split shot — lens half in, half out

> Added mid-run by owner ruling, as the intended final test.
>
> **Evidence upgraded.** Two reference photographs were supplied for this section
> after it was written: an over-under of an outrigger canoe in a shallow lagoon
> over white sand, shot ultra-wide behind a dome port; and a swimming-pool frame
> in which the camera sits just under the surface, so the air world arrives
> through Snell's window. Neither is the reference pool, so H stays weaker than
> A–F — but criteria below marked *photograph* are now read from an image rather
> than recalled, and one criterion was **falsified** by them and corrected.

This is the terminal test for this project, and the reason is structural rather
than aesthetic: it reads **one wave field three independent ways in one frame**,
and the three readings must agree or the frame falls apart.

1. **In profile**, as the wobbling boundary where the water crosses the lens.
2. **From underneath**, as the rim and the wrinkling of Snell's window.
3. **In projection**, as the caustic net those same slopes write on the bed.

No shortcut survives that. A surface that exists only as a normal map has no
profile; a caustic set that is not the Jacobian of that surface will not line up
with the window above it; a wave whose amplitude was tuned for the view from above
will read wrong in silhouette. The frame is self-checking in a way neither single
view is.

- **The split is a property of the port, not of the camera.** A mathematical point
  aperture at `z = 0` produces a straight split along the plane's projection —
  degenerate, and not what an over-under photograph looks like. A real front
  element of finite radius produces a **curve**: the waterline traced across the
  port, which undulates with the passing waves and rides up and down with them.
  That undulation is reading (1) above, and it is the reading a renderer cannot
  fake. **The port must therefore be modelled explicitly**, and which port is
  chosen must be stated. *Derived.*
- **Flat port versus dome port is a real, visible choice, and it shows up as
  magnification.** A flat port is a refracting interface, so the submerged half is
  magnified: apparent distance `d/n`, so objects read **25% closer and 33%
  larger**, and the field narrows from 46° in air to **34.0°** in water. The
  wavelength dependence puts a **0.105°** lateral chromatic spread at the frame
  edge — 0.5% of the half-field, so a coloured fringe in the corners and nothing
  at the centre. A dome port removes the magnification, at the price of a virtual
  image a few dome-radii in front of the glass that the lens must focus on; that
  is why over-under photographs are shot with a dome and a close-focus lens.
  *Derived.*
- **The dome is not free — it moves the cost to the air half.** A controlled
  reference was supplied for exactly this: the same 16 mm focal length shot
  through a 180 mm dome and an 82 mm flat port, same aperture, same shutter, same
  pool. The flat-port frame keeps the lens's native, very wide **air** field —
  palms on both sides, the whole building — while its submerged half is the
  narrowed, magnified one. The dome frame restores the submerged half and shows a
  visibly **narrower slice of the same air scene** at the same focal length,
  behaving as a strong negative meniscus in air. So there is no port that leaves
  both halves native, and a render claiming one has not chosen a port at all.
  *Read from the comparison photograph, not derived — the optics of a dome in air
  were not worked through here (`?`).*
- **Whichever port is modelled, the waterline is where it is proved.** With a flat
  port, anything crossing the boundary — the pool wall, a coping edge, the step
  unit's nosings — must **change scale across it**, by that same factor. With a
  dome, it must run through unbroken. A flat port whose halves match, or a dome
  that steps, is wrong on its own stated terms. This is the cheapest hard check in
  the whole bar: one straight edge crossing the waterline settles it. *Derived.*
- **The magnification is the interface, not the water.** A camera fully submerged
  with no port sees no magnification at all — the medium is uniform and nothing
  refracts between it and the subject. The same effect seen from the other side is
  the apparent-depth compression the step flight already demonstrates. One
  mechanism, three appearances; a renderer that produces them from three different
  pieces of code has not modelled it. *Derived.*
- **~~The submerged half is substantially darker~~ — falsified by the reference
  photographs, and the correction matters.** In the lagoon frame the underwater
  half is over white sand at one to two metres and reads *as bright as the sky
  half*, locally brighter. The darkness of a submerged half is not a property of
  being underwater; it is `bed albedo × exp(−a·path)`, and over pale sand at short
  path both factors are near one. The reference pool is a **blue liner at 1.40 m**,
  which is the opposite corner of both, so this render's halves genuinely will
  differ — but the render must produce that difference **from the liner and the
  path**, and never from an exposure fudge applied to one half. Measure the ratio
  off the render and report it. *Corrected against photograph; ratio not yet
  measured (`?`).*
- **A waterline band, not a waterline edge, and it is thick.** In the lagoon frame
  the boundary is a translucent greenish-white **wedge** — a large fraction of the
  frame height at one edge, tapering across — with visible internal structure, and
  partly see-through rather than opaque. It is the surface seen edge-on plus the
  meniscus riding the port, not a seam between two images. A clean boundary reads
  as CG immediately, and so does a boundary of uniform thickness. *Photograph.*
- **The band curves, and the curve carries two signals at once.** It arcs across
  the lagoon frame and rises toward one side: the dome's own curvature plus the
  wave riding up and down it. Separating those two is the point — the static part
  belongs to the port, the moving part is reading (1) of the wave field.
  *Photograph.*
- **Objects crossing run continuous in both references.** The mooring rope and the
  hull cross the boundary in the lagoon frame with no step in scale, which is the
  dome signature and confirms the port check above. *Photograph.*
- **A shadow on the bed is a reduction, not a hole.** The canoe's shadow on the
  sand is clearly darker, yet the caustic net stays legible *inside* it — the same
  claim section B makes for the shade sail, independently confirmed. *Photograph.*
- **The underside of the surface is a mirror at grazing incidence**, showing the
  bed folded back down, in both references — the top of the underwater half in the
  lagoon frame, and the upper band in the pool frame. It must be the same surface
  that writes the caustics below it. *Photograph.*
