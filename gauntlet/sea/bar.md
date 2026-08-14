# The bar — sea and surf. Frozen at intake, never edited.

Five photographs, supplied by the project owner, of the Atlantic coast at Aljezur
(Portugal), 37.3167 N, 8.8000 W.

| | when | elevation | azimuth | air mass |
|---|---|---|---|---|
| **three surf frames**, from the beach | 2026-08-12 **18:08 WEST** | 27.17° | 268.31° (W) | 2.182 |
| **two coast frames**, from the cliff | 2026-08-11 **11:45 WEST** | 56.22° | 123.13° (SE) | 1.202 |

Positions computed here (NOAA/Meeus low order, Bennett refraction, Kasten–Young
air mass). Shadows in the surf frames run toward bearing 88.3° at 1.95 × height;
in the coast frames toward 303.1° at 0.67 ×. **Check the frames against those
before trusting anything else in this file** — a wrong quadrant leaves the
elevation correct and is otherwise silent.

> **The surf frames' illuminant is under a caveat and it is not small.** There was
> a solar eclipse on 12 August 2026, and 18:08 WEST is 17:08 UTC — roughly half an
> hour before its greatest phase. Whether the partial had begun at this longitude,
> and how deep it was, is **`?` and must be checked against a source, not
> assumed.** A partial eclipse cannot be corrected with a scale factor: limb
> darkening makes the flux loss outrun the obscured area, and — worse for this
> project specifically — **the source stops being a disc**, so shadow penumbrae go
> anisotropic and every quantity derived from the sun's angular radius moves. The
> frames carry their own test: a shadow edge that is differently soft in two
> directions means the eclipse was under way.
>
> Until that is settled, **the surf frames are evidence for geometry, mechanism
> and ordering, and not for absolute radiometry.** The coast frames, a day
> earlier, are clean.

## What may and may not be read off these frames

They are iPhone 16 Pro captures, and this project has already been burned three
ways by that (see the pool bar's J2, J2c, J2d). Restated here because a new loop
will otherwise rediscover them:

- **Automatic white balance** rescales the channels of a saturated subject toward
  neutral — worst exactly where the subject is most saturated. **Absolute channel
  triples are not evidence.**
- **A display-referred tone curve** deepens the toe, so a ratio between two levels
  does not survive it. Pairs *close in level* survive; a lit-versus-shadow ratio is
  the worst case and gives a bound, not a value.
- **Display P3 read as sRGB** takes 28–51% of the red out of a saturated cyan while
  barely moving a warm neutral. Convert, or compare only within one frame.

**The instrument that survives all three is a within-frame ratio between surfaces
close in level.** Use those. Where a criterion below needs a number, it is marked
as a number the render must produce and report — not one read off a photograph.

## The overriding bar

> A viewer should have to **wonder whether it is a photograph**.

Same standard as the pool. A single synthetic tell anywhere in frame fails it.

---

## A · The colour is the path, and one frame proves it

The strongest single criterion in this set, because it is a **falsification** and
needs no measurement.

- **A backlit wave face reads distinctly green while the same water two metres
  away reads grey-blue.** One liquid, two colours, one exposure. The colour is
  therefore the **path**, and a renderer that tints its water body has been
  falsified by this frame. *Photograph.*
- **It must vanish when the path does.** The green appears only where the column
  is thin *and* the sun is behind it. A sea that is green everywhere, or green in
  reflection, is wrong on its own terms. *Derived from the above.*
- **The face is a wedge, and therefore a variable-path cuvette** — thin at the lip,
  thick toward the trough, with the colour grading across it. The render must
  reproduce the *grade*, not merely the hue. *Derived.*
- **The hue is not pure water's.** Over 2 m, pure water transmits about
  `(0.59, 0.90, 0.98)` — a mild shift, not a saturated green.

  > **Corrected before the loop opened, and the correction matters.** This first
  > read *"CDOM and chlorophyll take the blue and leave a window near 550 nm"*,
  > written by the lead agent. The sibling skill `terrain-architect` chapter `28`
  > is sharper and the original conflated two opposite controls: **CDOM darkens,
  > sediment brightens.** CDOM is `a(λ) = a₄₄₀·exp[−S(λ−440)]`, rising steeply
  > into the blue and **scattering not at all** — it makes water *transparent and
  > dark*, tea to near-black, and leaves no green window. The window at
  > **550–570 nm** is **chlorophyll's**, which absorbs at 440 *and* 675.
  >
  > So this frame set holds **two different constituents**: the green wave face is
  > a **phytoplankton** signature, and the pale milky surf zone of section D is
  > **suspended mineral sediment**. A renderer with one turbidity slider cannot
  > hold both, and reaching for turbidity to make a tannin-stained water would give
  > mud instead.

- **The IOPs no longer have to be invented.** They were the one thing this scene
  could not inherit from the pool — Fresnel both sides, the critical angle,
  `L/n²`, Beer–Lambert, the trapped series and dispersion all transfer unchanged,
  but `b_b ≈ 0` does not. `terrain-architect` chapter `28` supplies the three
  constituents and a **concentration→optics bridge** (Babin et al. 2003):
  mineral-dominated suspended matter gives `b_p(555)/SPM ≈ 0.5 m²/g`, so **each
  mg/L of load adds ≈ 0.5 m⁻¹ to `b` at 555 nm**. That closes the chain from the
  wave field through the sediment flux to the optics. *Routed, `P`; the actual
  load at Aljezur is `?` and is what the cuvette inversion is for.*

## B · The bar and trough: breaking must be a prediction

- **Two breaking lines with calmer water between them**, in the first surf frame.
  That is a sandbar: break over the shallow, reform in the trough, break again
  inshore. *Photograph.*
- **This must emerge from the depth field alone.** `H/h` crosses the breaker index,
  un-crosses it in the trough, and crosses again — with **nothing in the scene
  saying *break here***. A monotone profile cannot distinguish a renderer that
  computes breaking from one that draws foam near the shore; a bar can. This is
  the section's whole value. *Derived.*
- **Four closed forms are available and all four must be reported**, against
  literature rather than against the render: shoaling as `H ∝ h^(−1/4)` (Green),
  refraction turning crests onto the depth contours (Snell with `c(h)`), the
  breaker index near `H/h ≈ 0.78`, and run-up scaling with the Iribarren number.
  *Derived; the constants are `P` and must be cited.*
- **Curved contours focus.** A bar's contours are not straight, so the wave focuses
  over it — which is why some breaks peak and others close out. Straight-contour
  refraction is a test that passes by construction; this one is not. *Derived.*

## C · Three whites, one constant, and they are not one mechanism

The most common way surf renders wrong is to make all of it particles. In these
frames all three are present and they are visibly different:

- **Surface foam** — the persistent white deck left after a break. A **coverage
  mask on the surface**: it floats, deforms with the flow, decays slowly.
- **Entrained air in the volume** — where the wave mouth goes white and opaque, and
  **the bed stops being visible through it.** A participating medium with high
  scattering albedo. If a renderer whitens without hiding what is behind, it has
  modelled the symptom.
- **Airborne spray** — droplets clear of the surface, backlit along the crest.
  **This is the particle one, and it is the smallest share of the white in frame.**

*All three photograph.* All three whiten from **`1 − 1/n² = 43.874%`** — a bubble
seen from the water side has the same critical angle as the surface seen from
below. One constant, three appearances, and the same one that runs the mirror
outside Snell's window. *Derived.*

## D · The surf zone is turbid, and the turbidity is a state variable

> Owner, present at the coast: *"Wat ik nog niet heb is de terugtrekkende golf die
> zand omhoog neemt. In de branding is het water troebeler."*

- **`b` is a field coupled to the wave field**, not a constant of the water body.
  Waves suspend the bed; the **backwash** is the erosive half of the swash cycle;
  turbidity therefore **pulses with each wave**. The pool's entire optics rests on
  `b_b ≈ 0` and that assumption does not survive here. *Owner observation, with the
  mechanism derived.*
- **A bar with a gap gives the sediment a transport mechanism, not just a source:**
  water piled behind the bar escapes as a **rip**, carrying sediment offshore.
  Driven by the same wave field that suspends it. *Derived.*
- **A confusable pair, and the render must distinguish them rather than blend
  them:**

  | | mechanism | signature |
  |---|---|---|
  | **shallow bottom** | the bed seen through the column | *reveals* structure, and it **stays put** |
  | **suspended sediment** | a scattering veil in the column | *hides* the bed, **moves with the water**, **pulses** with the wave |

  The cliff frame shows the first cleanly: teal over the submerged rock platform,
  deep blue where no bed is in reach. The surf frames show the second. *Photograph.*
- **The discriminator is motion**, and it is the same test that settled the pool's
  last open question: **watch it while the water moves.** *Method.*

## E · The cloud after a break on rock is two clouds

> Owner: *"Golven die na stukslaan op een rots een soort wolk achterlaten."*

- **Entrained air** rises and bursts in **seconds** — the bright plume that visibly
  shrinks.
- **Suspended sediment** settles over **minutes** and advects away.

They overlap in space and are separated by their **decay**, not their appearance.
One decay curve fits neither, and the tell is a plume that either vanishes too
fast to leave a stain or stays too white too long. *Owner observation; the two
timescales `?` and to be sourced.*

## F · Out of scope for the first passes, stated so it is not mistaken for a defect

- **The plunging lip.** In the second surf frame the lip is throwing forward, and
  at that instant the free surface is **multivalued** — air beneath water that
  hangs above other water. That breaks the height-field assumption under the wave
  field, the caustic pass and the surface intersection alike. **It is a different
  representation, not an extension**, and it is the last problem rather than the
  first. Everything up to the point of breaking is still a graph over the plane.
- **Individual spray droplets** beyond a statistical treatment.
- **Anything requiring the eclipse to be resolved**, until it is.

## G · What the reference set does not contain

Recorded so a critic does not credit the render for something unphotographed:

- **The backwash itself, loaded with sand.** Section D rests on an owner
  observation with no frame behind it. A photograph of the swash retreating down
  the beach face, visibly laden, would move D from testimony to evidence.
- **Any frame with a scale, a colour chart, or a neutral reference.**
- **Any underwater or split view.** The pool set has both; this one has neither, so
  every criterion here is from above the water.

---

## H · Five more frames: the platform, the bay, and the swash — added at intake+1

> Supplied by the owner before the first wave reported. **No time was given for
> these**, so their illuminant is `?` and they carry the same standing as the surf
> frames until one is supplied: evidence for **geometry, mechanism and ordering**,
> not for radiometry. *Times requested.*

Two of them close a gap this file recorded as open, and one of them corrects the
scene plan.

### H1 · It is a wave-cut platform, not scattered rock

Two frames show a **flat bench at sea level**, deeply pocketed, with **sand
infilling the hollows** and dark weed on the wet rock. That is a landform with a
formation mechanism, not scenery.

- **It must emerge from the coastal loop**, the same way the sandbar must emerge
  from the morphodynamic one: `terrain-architect` `12`'s **notch → collapse →
  deposit**, where the bench appears when the notch band is narrow and erosion is
  high. That chapter gives the diagnostic outright: *"if you're not getting one,
  `notchHeight` is too large."* **Cite it; do not re-derive it badly.**
- **The pocketing requires spatially varying hardness.** Chapter `12` is explicit
  that uniform rock yields a straight cliff and nothing else, and names it as the
  usual reason a coastal graph looks boring. The pockets in these frames are the
  evidence that this coast is not uniform.
- **This corrects the plan recorded in the backlog**, which had rocks as
  *"analytic solids"* placed in the scene. Same doctrine as the bar, one level up:
  **the rock is an output, not an object.** *Lead agent's error, corrected before
  the wave that would have inherited it.*
- **A sea stack is representable in a height field and an arch is not.** Chapter
  `12` flags this against `11`'s representation warning. Nothing in these frames
  needs an arch; recorded so nobody adds one.

### H2 · The swash is laden — the gap in section G is partly closed

Section G recorded that the set contained **no frame of the backwash carrying
sand**, and that section D therefore rested on owner testimony alone. Two frames
now show it:

- The retreating sheet is **visibly grey-brown, not clear** — suspended load in a
  film a few millimetres deep. *Photograph.* Section D's turbidity now has an
  image behind it, though the *concentration* remains `?` and is what
  `terrain-architect` `28`'s Babin bridge is for.
- **Foam is left behind as lace**, stranded by the retreating water rather than
  advected with it — two different residence times on one surface, and a mask that
  simply follows the water will not produce it. *Photograph.*
- **The gap is only partly closed:** these show the swash *and* the backwash
  together at a distance. A close frame of the backwash alone, where the load is
  legible against the sand, would still be worth having.

### H3 · The wet/dry sand boundary, and it transfers for free

**One of the strongest tonal edges in these frames is the waterline on the sand**,
and it is the same physics the pool already carries. Wet sand darkens because a
thin film traps light between the surface and the substrate — the trapped series,
which this project derived for the liner as `wet_albedo` and guarded against Egan
& Hilgeman. **It applies to sand unchanged.** The wet band also goes *specular*
where the dry sand is matte, so `base_color` and `specular_roughness` move
together, exactly as the pool's weathering section specifies. *Derived; transfers
without modification.*

### H4 · The bay, and what it offers that a straight coast does not

One frame shows the whole embayment from the cliff: headland, curved beach,
and **surf lines running parallel to the shore** all the way round the curve.

- **That is refraction, visible without instruments.** Crests turn onto the depth
  contours, and a curved bay makes the turn large enough to see. A straight-contour
  test passes by construction; this one does not. *Photograph, and it is the
  cheapest available check on the refraction closed form.*
- **Headlands and bays are the coastal loop's own signature** — headlands retreat
  faster than bays until the coast straightens, which chapter `12` calls
  self-reinforcing. A scene built with one straight beach cannot show it.

### H5 · One wave field, two breaker types — and the substrate decides

An eleventh frame: a wave meeting the **seaward edge of the rock platform**,
throwing a vertical plume of white water off the ledge, with churning foam beyond
carrying visible rotational structure. No time given; illuminant `?` as above.

**This is a *reflective* breaker, and the same set already contains an
*intermediate* one.** The surf frames show a bar-and-trough system on sand:
break, reform, break. This frame shows a near-vertical impact on rock: reflect,
and throw the water upward. **One offshore wave field, two breaker classes, and
the difference is entirely the substrate.**

- **`terrain-architect` `12` carries the classifier** — Wright & Short (1984)'s
  dimensionless fall velocity `Ω = H_b/(w_s·T)`, with `w_s` the sand settling
  velocity from grain size. Below 1 is **reflective** — *"steep, coarse, no bar,
  no rips; surging breakers at a beach step"*. 1–6 is the **bar–rip family**.
  Above 6 is **dissipative**. Cite it; the settling law is stated as the
  implementer's to supply.
- **The rock is the limit beyond the classifier, not a point on it.** `Ω` is
  defined for a sandy beach; a rock platform has no `w_s` and no mobile bed. What
  transfers is the *breaker type* argument — a steep impermeable face surges and
  reflects rather than spilling or plunging — and that must be said rather than
  quietly extrapolated. *Derived; the extrapolation marked.*
- **This sharpens section B again.** It is no longer only that breaking must emerge
  from the depth field. **The *type* of breaking must differ by substrate within
  one frame**, and the number that predicts which is already on the required-
  reporting list.

**A note on which number, because two are in play and they answer different
questions.** Section B's fourth closed form names the **Iribarren** number, which
classifies the *breaker* at a given slope; chapter `12` uses **`Ω`**, which
classifies the *beach state* and hence the bar–rip morphology. Both are real and
they are not substitutes. Report both, and say which is answering which — silently
picking one is how a reader inherits a conflation. *Recorded rather than resolved.*

**The plume is ballistic, and it is outside the representation.** Once the water
leaves the ledge it is projectile motion — height from `v²/2g`, checkable against
the wave's own momentum flux. But a vertical jet in air is not a graph over the
plane, so it joins the plunging lip in bar section F: **deferred, and for the same
structural reason rather than for effort.**

**The foam beyond it carries rotational structure**, not just coverage — visible
eddies with foam as the tracer. A coverage mask advected by a potential flow will
not produce it; it needs the vorticity the breaking itself generates. *Photograph;
recorded as a criterion for the foam wave, not this one.*

## I · The reform, photographed — and the barrel, from stand-ins

### I1 · The second breaking line exists at this coast. Owner's frame.

A twelfth owner photograph, from the cliff: **two clearly separated lines of
whitewater with a calm band between them**, birds over the trough. No time given;
illuminant `?`.

**This is section B's central criterion, photographed at the reference coast**, and
it lands while the implementation cannot produce it — wave 1 reported `H/d`
bottoming at 0.456 against the 0.40 needed, across four tide levels and three sea
states, and filed it `OPEN` rather than widening a tolerance. **That was the right
call and this frame confirms it was a real gap.**

The consequence binds every later wave: **no wave may resolve section B by
concluding that this coast does not reform.** It does; here it is. The failure is
the model's, and the finding must name what the model lacks.

### I2 · Three barrel frames, and they are stand-ins — say so

Three further images arrived with the above: a large wave with the lip throwing
and spray blown back off the crest, and two tube frames shot from the front and
the side. **They are plainly not the reference coast** — much larger surf, and
professional surf photography rather than the owner's cliff-top phone frames.

They carry the standing the pool bar gave its own stand-ins (the lagoon over-under
and the dome-versus-flat-port comparison): **evidence for a mechanism, never for
this coast, and never for radiometry.** A critic may not credit the render against
Aljezur on their strength. Marked, as those were.

What they do supply:

- **The definitive multivalued surface.** A barrel is the free surface wrapped over
  itself with air enclosed — not a steep graph, an *enclosed volume*. Bar section F
  defers this for a structural reason and these frames are what that reason looks
  like. *Photograph, stand-in.*
- **The interior is lit through its own wall.** Inside the tube the light does not
  arrive from the sky — it arrives through one to two metres of wave face, and it
  is Beer–Lambert filtered on the way in. That is why a barrel's interior reads
  **green** rather than blue or shadowed. It is the section-A path argument again,
  in its strongest form: **a room whose only window is the water.** A renderer that
  lights a tube interior with ambient sky has missed the whole mechanism.
  *Derived from the frames; the path length `?`.*
- **Two surface states on one wave, simultaneously.** The face is smooth and
  glassy while the lip is exploding, centimetres apart. Any model with a single
  roughness or a single foam threshold across the wave cannot hold both.
  *Photograph, stand-in.*
- **Spray blown back off the crest** — offshore wind against the wave's own motion,
  so the plume goes *backwards* relative to the break. A spray model advected only
  by the wave will send it the wrong way. *Photograph, stand-in.*

## J · The scene, in one frame — the defining overview

A thirteenth owner photograph, and the first that arrives upright: the whole
embayment from the cliff. Headland to headland, cliff behind, a curved sand
beach, and the surf running in **multiple lines that follow the curve all the way
round**. No time given; illuminant `?`. *Time requested — this is the frame most
worth having a sun for.*

**This is the scene brief in one image, and it is the frame a whole-scene render
must be judged against.** Everything else in this bar is a mechanism seen close;
this is what they have to add up to.

### What it establishes

- **The coast is an embayment, not a straight beach.** Cliff, headland, curve,
  headland. Section H4 recorded this from a weaker frame; this one settles it, and
  it means the scene's plan geometry is a **bay**, with the depth contours curving
  to match. A straight-shore scene cannot show what this frame shows.
- **Refraction is legible without instruments.** The breaking lines bend to stay
  parallel to the shore around the whole curve. That is crests turning onto the
  depth contours — one of the four required closed forms — and it is checkable **by
  eye against this frame**, which is the cheapest verification in the entire
  project. A render whose surf lines stay straight while the shore curves has
  failed a criterion a layman could catch. *Photograph.*
- **Three to four separated breaking lines** across the wider parts, not one. So
  the nearshore carries a **system** of bars rather than a single breakpoint bar,
  which raises the bar for section B again: the implementation currently produces
  one continuous surf zone, and this frame shows the coast producing several
  discrete ones. *Photograph.*
- **An offshore reef or rock outcrop** shows as a dark patch with white water over
  it, well seaward of the main surf. Breaking over an isolated hard high — a third
  break mechanism alongside the bar and the platform edge. *Photograph.*
- **The full colour ladder in one exposure**, which makes it a within-frame
  instrument and therefore usable despite the camera failures: deep blue offshore →
  teal over the shallows → white surf → saturated brown wet sand → pale ochre dry
  sand. **Five surfaces, one exposure**, with the wet/dry sand pair close in level
  and therefore the most trustworthy comparison of the set. *Photograph; the
  wet/dry pair is the measurable one.*

### What it does not license

It is a **distant** frame. Nothing in it resolves foam texture, spray, the
waterline's fine structure or the swash. Those stay with the close frames of
sections C, D and H2. A critic may not credit texture-scale work against this
image, and a builder may not read a small feature off it. *Recorded so the frame's
strength does not get borrowed by claims it cannot carry.*

## K · Open water and the glitter path — a fourteenth frame

Upright, from the cliff: a long crescent beach curving away to a headland and a
village, dune vegetation in the foreground, and **the whole open sea with the
sun's glitter path running from the horizon into the near field**. No time given;
illuminant `?`. *Time requested.*

### K1 · The glitter path is the strongest instrument in this set

The pool's glitter was a window a few metres across. **This is the same physics at
the scale where it actually bears weight**, and it carries a measurement nothing
else here does.

- **The path's angular width is a readout of the surface's mean square slope**, and
  therefore of the wind (Cox & Munk). It is not decoration — it is the one quantity
  in these photographs that reports on the *statistics* of the surface rather than
  on a single wave. **The render must produce the path and report its width**, and
  the width must come from the slope distribution rather than from a spread
  parameter chosen to look right. *Derived; the wind at the time is `?`.*
- **Its shape is diagnostic, not just its presence.** It narrows toward the horizon
  and spreads toward the observer, because the same slope distribution subtends a
  different range of specular directions at different incidences. A path of uniform
  width is wrong in a way that is obvious once stated and almost never modelled.
  *Derived.*
- **One frame holds the surface from grazing to moderate incidence.** The horizon
  is near 90°, the near field far from it, so the whole Fresnel ramp is in one
  exposure. That makes the *relative* behaviour across the frame a within-frame
  instrument — usable despite the camera failures — where any absolute value is
  not. **Report the trend across the frame, not a value at a point.**

### K2 · What else it establishes

- **A long crescent with multiple shore-parallel surf lines**, confirming section J
  rather than adding to it — but at a different beach and a different curvature,
  which makes the refraction criterion harder to satisfy by coincidence.
- **A sharp sea–sky horizon.** Trivial to render badly: the sea's radiance at
  grazing must approach the sky's reflected value continuously, and any seam there
  is a tell visible at a glance.
- **Dune vegetation and a village in frame.** Out of scope, and recorded as out of
  scope so nobody spends effort on them. Section E of the pool bar struck scenery
  for the same reason and that ruling carries.

### K3 · What it does not license

Like section J this is a **distant** frame: it resolves neither foam texture nor
the swash nor any waterline. And **the glitter path is exactly where a phone's
tone curve does its worst**, since it spans the brightest and darkest parts of the
frame. **Do not read a level off the path.** Read its *geometry* — width, shape,
extent — which survives the transfer function that its brightness does not.

---

## Arbitration · Section A is unreachable from a linear surface — a bar defect

**Lead agent's ruling, wave 4.** Section A calls the two-colour falsification *"the
sharpest single criterion in this set"*. It is, and it is also **not reachable from
the representation the loop is built on**, which makes it a **bar defect and not an
artifact defect** — the same class as the pool bar's section C, which asked for a
frame no deck could stand on.

**The geometry, measured.** A ray entering water is confined to the Snell cone, so
a sightline *along* a crest — the lengthwise path that makes a wave face read green
against grey-blue water metres away — requires a face steeper than **41.48°**. The
scene's linear surface reaches **8.21°**.

**So section A moves.** It sits with section F's plunging lip, and **one step
earlier in the chain**: the lengthwise path needs the nonlinear crest before the
overturning lip needs the multivalued surface. Section F already defers the lip for
a structural reason; A now shares it.

**What does not move.** The *physics* of section A was verified this wave and
stands on its own:

- The grade across a wedge is **1.355 backlit and 1.348 front-lit — identical**,
  measured on transmittance so the source spectrum cancels. **The grade is the
  path, and the path does not know where the sun is.**
- What separates the two is the **forward glow**, not the lighting: the derived
  Henyey–Greenstein lobe reads 0.6215 sr⁻¹ at 15.8° against 0.0019 at 159°, so the
  glow is 5.07% of the backlit pixel and **0.00%** of the front-lit one. Only the
  observer moved.
- And the bay shows the path law without any wedge at all: the colour ladder runs
  **0.961 deep → 1.014 at 2–5 m → 1.130 over the shallows** in one exposure from
  one set of coefficients.

**So the `waterColor` category error is still falsified**, by the bay rather than by
the wave face. Section A's *claim* survives; only its *instrument* was out of reach.

**Recorded so a critic does not re-open it:** a render may not be marked down for
failing to show a green wave face until the nonlinear crest exists. When it does,
section A is the first thing to check against it.
