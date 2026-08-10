# Water-rendering doc rubric — frozen at intake

Judges whether `terrain-renderer/references/12-water-rendering.md`'s **Caustics**
treatment (in "Shading and optics") gives a team enough to actually reproduce
two reference qualities:

1. **Tide-pool clarity**: bright, sharp, moving light-cell patterns dancing on
   a shallow, clear sandy/rocky bottom, visible on submerged rock as well as
   sand, changing with the sun.
2. **Stylized wake legibility** (arcade racer, e.g. Mario Kart-style jet skis):
   a bright, persistent white foam trail behind a moving vehicle, readable as
   a gameplay signal rather than photoreal spray.

Score each on the calibrated scale used elsewhere in this skill (9 =
indistinguishable from a shipped answer without measurement, 10 = beats the
bar, `major`/`minor`/`none` severity per the usual convention):

- Does the doc name a concrete real-time **mechanism** for caustics (not just
  "add a caustic texture"), with at least one baseline tier a team could ship
  this sprint?
- Does it explain **why** caustics need clear shallow water (ties to existing
  extinction/depth machinery) rather than asserting it?
- Does it correct the naive "caustics = decal on the seafloor" model (i.e.
  does it say caustics belong on any lit submerged surface)?
- Does it connect wake-trail stylization to an existing, named mechanism
  (the foam decay curve) rather than inventing a new system?
- Is there a Pitfalls entry and a provenance/citation entry, matching the
  chapter's own house style, so the addition doesn't stick out as thinner
  than its neighbors?

`major` — a team following the doc would ship a decal-caustic with no
sun/state coupling. `minor` — usable, but a reviewer would ask a clarifying
question. `none` — nothing left to tighten for this chapter's own bar.
