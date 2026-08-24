---
okf_version: "0.2"
---
# water-physics

An OKF v0.2 knowledge bundle. Every document below carries its own
`type`, `status` and provenance in frontmatter; the trust tier a
consumer derives from `verified` is deliberately **unverified** on
all but the documents a checker actually re-derives.

# Entry point

* [Water Physics](SKILL.md) - The measured physics of water, for renderers: the air/water interface (exact Fresnel, the 1 - 1/n^2 partition, L/n^2 radiance transport, the critical angle and the Snell window), inherent optical properties and where a water body's colour actually comes from, sun glitter and the slope distribution behind it, caustics and their Jacobian, aerated water (foam, spray, whitecaps, bubble optics), the wind-wave spectrum derived from its forcing with Cox & Munk recovered as a limit, shoaling and refraction and depth-limited breaking, Sommerfeld diffraction and the fan a bay requires, the wave-height population and why a surf line breaks up, run-up and swash. Backed by three running reference implementations and their suites - a pool, an open coast, and a screen-space pass - so every number is checked against a closed form, a published measurement or an independent method. Use when a water number has to be right, defended, or re-derived at different constants: "why is my sea green everywhere", "what reflectance is foam", "how much light comes back up", "is this glitter path the right width", "where does the wave break". For the render-side architecture - LOD, passes, engine water systems - route terrain-renderer 12. For generating the bed, route terrain-architect.

# raster-impl

* [Generated frames](raster-impl/evidence/README.md) - Frames written by the screen-space raster pass.
* [Screen-space water — the raster reference](raster-impl/README.md) - The real-time screen-space pass, its LUT and its wave surface: the only place in this skill where approximation error can be measured at all.

# reference-impl

* [Generated frames](reference-impl/evidence/README.md) - Frames written by the pool renderer, kept as the visual record its suite rows refer to.
* [Generic reference set — nine openly-licensed photographs, and what each one is evidence for](reference-impl/photos/README.md) - Nine openly-licensed reference photographs and the full licence trail for each.
* [Pool reference implementation](reference-impl/README.md) - The pool: a 1.40 m domestic basin used as the cleanest available optics laboratory, its modules, and what its suite establishes.
* [The beach at Aljezur — bathymetry, the wave transform, and the bar](reference-impl/README-beach.md) - The open coast at Aljezur: bathymetry and the morphodynamic loop, the wave transform, diffraction, foam as a realisation, and the camera.

# references

* [The gap register: what was missing, and how each entry closed](references/12c-uncovered.md) - The six gaps this skill knew it had and how each closed: five by finding a missing axis, one by finding a missing source.
* [Water Physics](references/12-water-physics.md) - The mechanism side of water: the interface and its two Fresnel constants, where a body colour comes from, shoaling and breaking, foam as a covering measure, and the six axes the rest of the chapter is a point on.
* [Water Rendering — Derivations](references/12a-water-derivations.md) - The derivations behind every number the water chapter quotes in a line, each naming the test that guards it or stating that none does.
* [Water Rendering — Sources & Provenance](references/12b-water-provenance.md) - Every source, tier and unverified mark behind the water chapters, restated so it reads alone. Read before citing anything out of this skill.
