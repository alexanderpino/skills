# Bar — shallow water over rock, judged as acceptance criteria

The artifact is a single-file WebGL2 render of **shallow coastal water over a
rocky bottom, seen from above at a shallow angle**, in bright daylight. The
reference situation is the one in the intake photographs: dark wet rock ledges
breaking the surface, deep blue water offshore, and — the reason this bar
exists — the **pale milky cyan clouds of aerated water** where waves break on
the rock, spreading past the white froth and drifting with the backwash.

Every criterion below is checkable in a still screenshot. Each is drawn from
`terrain-renderer/references/12-water-rendering.md`, which is the external
authority here; the criterion text names the mechanism so a critic can look for
its *visible consequence*, not for source code.

## Must be visibly true

1. **Depth is the colour.** Water reads shallow-to-deep as a continuous ramp
   driven by bathymetry, not as one flat blue. Red is gone first: shallows over
   rock read cyan/green, deep water reads dark blue. Flat-coloured water fails.
2. **The subsurface plume exists.** Where water breaks against rock there is a
   *pale, milky, cyan-white region under the surface*, larger than the white
   froth on top, that brightens the water rather than darkening it. Foam alone
   on deep blue fails this outright.
3. **Foam does not reflect the sky.** Aerated regions read as scattering froth,
   not as glossy water: the specular/Fresnel response is suppressed underneath
   foam.
4. **Water is not chrome.** No mirror-bright horizon band and no single blown
   specular dot. Sun response is a *glitter path* of finite width, not a point.
5. **Detail sits in the right band.** Surface disturbance is visible as
   normal-scale wave detail; the silhouette is not a flat mirror. Waves must be
   generated, never a painted-on static pattern.
6. **The rock is wet, not painted.** Rock in contact with water is darker and
   more specular than dry rock above the line, with a transition rather than a
   hard cut.

## Must not be visibly true

- A hard polygonal intersection line where water meets rock (needs depth fade).
- Uniform noise standing in for waves.
- Aerated water rendered *darker* than clear water.
- A visible tiling repeat across the frame.

## Severity

`major` — a viewer would call it out unprompted (flat blue water, no plume,
chrome horizon). `minor` — visible once pointed out (plume too tight, glitter
slightly narrow, shore fade a little abrupt). `none` — nothing meaningful
remains against this list.

## Scope

Judged from one 900×600 screenshot at the default camera. Not judged: frame
time, animation quality over time, underwater camera, night lighting.
