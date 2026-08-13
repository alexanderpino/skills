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
  `(0.59, 0.90, 0.98)` — a mild shift, not a saturated green. This green is a
  coastal-water signature: CDOM and chlorophyll take the blue and leave a window
  near 550 nm. **The IOPs are the one thing this scene cannot inherit from the
  pool work** — Fresnel both sides, the critical angle, `L/n²`, Beer–Lambert, the
  trapped series and dispersion all transfer unchanged; `b_b ≈ 0` does not.
  *Derived, with the coastal IOPs themselves `?`.*

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
