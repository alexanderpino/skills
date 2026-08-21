# s18-foam-coverage-before

**The coverage field alone, as an image, before.** Not a render -- the drawn
coverage buffer itself, 0 to 1 mapped to 0 to 255, so that the thing being
alpha-blended can be looked at without the sky, the glitter and the bed on top
of it.

**Provenance: measured**, from the same run as `s18-foam-edge-before`.

This is the owner's *strak witte lijnen* in their own right: a set of
perfectly smooth diagonal ribbons with continuous edges and no break-up at any
scale. It is not a rendering artefact and not a filter -- it is what
`1 - exp(-m)` looks like when `m` is a smooth function of position, which is
what an expectation is. The picture is the diagnosis.
