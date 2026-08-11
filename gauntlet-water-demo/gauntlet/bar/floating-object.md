# Bar — a floating object on the water (the ring)

Added mid-run, and **announced**: this is a new lane's bar, not an edit to
`water-fidelity.md`. The frozen bar stays frozen; this file covers a case that
one explicitly said it did not cover.

The situation: a brightly coloured inflatable ring floating on the water,
daylight, seen from a shallow-to-overhead angle. It is a small object with a
large amount of contact with the surface, which is exactly why it is a good
test — almost every way of getting water wrong shows up at a floating object's
waterline.

## Must be visibly true

1. **It sits on the wave surface, not on the datum.** The ring's height and
   tilt follow the same wave function the renderer displaces the surface with.
   A ring hovering over a trough or buried in a crest is the classic tell, and
   it is the one-evaluator rule from `19`: physics and renderer sample one
   evaluator at one time value, or the object floats above its own wave.
2. **The waterline on the object is soft and moving.** Where the ring meets
   water there is a depth-faded contact, not a hard polygonal cut, and the line
   rides up and down the ring's tube as waves pass.
3. **The submerged part is water-coloured.** Whatever is below the surface is
   seen *through* the water column: shifted toward the water's own hue, lower
   in contrast, and distorted by the surface normals above it. A ring that is
   the same flat yellow above and below the line is a sticker.
4. **It occludes and darkens the water beneath it.** A contact shadow, and no
   caustics on water the ring is covering.
5. **It disturbs the surface it sits in.** At minimum a small rim of ripples or
   a wake trailing its drift — a perfectly undisturbed surface around a
   floating object reads as a decal pasted on a photograph.
6. **It is lit by the same light as the water.** Same sun direction, same
   exposure, glossier where wet near the waterline.

## Must not be visibly true

- The ring rendered as a flat sprite/billboard ignoring the surface normal.
- A hard intersection line where object meets water.
- The ring perfectly still while the water animates, or drifting on a path
  unrelated to the flow.
- Its shadow falling in a different direction from the water's sun glitter.

## Severity

`major` — a viewer calls it out unprompted (hovering, hard cut, flat sticker).
`minor` — visible once pointed out (contact shadow too tight, ripple rim too
faint). `none` — nothing meaningful remains against this list.

## Scope

Judged from one 900×600 still at the default camera, together with the water
behind it. Not judged: the object's own material authoring quality (a
convincing inflatable-vinyl shader is a different lane), buoyancy dynamics over
time, or collision with the rocks.
