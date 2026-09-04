---
type: Coverage
title: Coverage map
description: "Every topic Gaia claims, whether it is written, planned, or deliberately out of scope."
tags: [coverage, routing]
status: draft
generated: { by: process:claude-code, at: 2026-09-02T00:00:00Z }
---
# Coverage map

**What this file is for.** "The skill is complete" is not a claim anyone can check unless the
skill first says what it is trying to cover. This is that denominator. `scripts/check.py`
enforces it in both directions: every `covered` topic must name a document that exists, and
every document must be claimed by exactly one topic. A document nobody planned and a plan
nobody wrote are both reported.

It is also how the skill grows without degrading. A new topic is added here **first**, as
`planned`, with the question it answers. That makes the gap visible before anyone writes
prose, and it stops growth from being whatever the last contributor happened to feel like
writing.

## Row format

```
- **topic-id** `state` — The question this topic answers. → document.md
```

`state` is one of:

| State | Meaning | Requires |
|---|---|---|
| `covered` | A document exists and answers it. | a `→ file.md` that exists |
| `planned` | A real gap. Named so it is visible. | a reason, after `—` |
| `out-of-scope` | Deliberately excluded, so nobody re-adds it by accident. | a reason, after `—` |

⚠️ **`out-of-scope` is a decision, not a shrug.** Writing it costs a sentence explaining why,
and that sentence is what stops the same topic being proposed every six months.

## Generation

- **flow-routing** `covered` — Where does each cell's water go, and what about depressions? → flow-routing.md
- **noise-and-warping** `covered` — Which noise, which constants, and how to warp it? → noise-and-warping.md
- **tectonic-uplift** `covered` — Where does relief come from before erosion touches it? → tectonic-uplift.md
- **hydraulic-erosion** `covered` — Droplet or pipe, and when does the answer change? → hydraulic-erosion.md
- **thermal-aeolian-erosion** `covered` — Talus, slab dunes, and episodic failure. → thermal-and-aeolian-erosion.md
- **stream-power** `covered` — The landscape-evolution law, and the solver that makes it tractable. → stream-power.md
- **terrain-analysis-masks** `covered` — Slope, curvature, occlusion, and selectors that compose. → terrain-analysis-masks.md
- **hydrology-lakes** `planned` — Where standing water sits at rest, lake level and outlet, before any wave is drawn. The bridge between flow routing and closed-water simulation, currently implied by both and stated by neither.
- **out-of-core-generation** `planned` — How do you *erode* terrain larger than memory? The runtime half is now written: node-graph-runtime.md gives the three tiling contracts, halo composition, and the per-tile boundary-summary result that makes a single global-ordered pass exact out of core. What remains is the **iterated** case, which that document explicitly leaves open — an erosion loop rebuilds the flow DAG every step, so the boundary digest must be recomputed and re-reduced per iteration, and no source here measures that. Also unwritten: how tile size and overlap are chosen in practice.
- **resolution-independence** `planned` — **Which parameter of each operator has to rescale with cell size, and how.** The *principle* is now covered three times over — terrain-analysis-masks.md for slope thresholds, node-graph-runtime.md for the runtime rule that a parameter in cells is a bug and resolution belongs in the cache key, layering-filters-and-masks.md for filter radii and placement in metres. What is still missing is the per-operator arithmetic: droplet count, brush radius, minSlope, pipe timestep, thermal pass count and stream-power K. No erosion document applies the principle to its own parameters, and that is the gap. The single most common complaint against tools in this class.
- **planet-scale-generation** `planned` — How do you route flow and erode on a cube-sphere? Routing across the 12 face seams and 8 corner singularities that planetary-precision.md establishes for rendering, and the fact that a global drainage solve has no tile decomposition on a sphere. The generation counterpart to a planetary rendering document that already exists.
- **procedural-placement** `planned` — Scattering rocks, vegetation and debris from the masks, including blue-noise sampling. Load-bearing for a tool builder and not yet written.
- **surface-and-scale-space** `covered` — How do you change a terrain's surface without destroying its silhouette? Band-split the heightfield, operate on the residual, recombine. The contract behind Gaea's eleven "Surface Nodes", and the machinery — multi-band decomposition with per-band gain — that several other operators are really instances of. → surface-and-scale-space.md
- **stratigraphy-and-lithology** `covered` — How do you author rock layers so erosion produces caprock, cuestas and mesas as outputs? Gaia already states the mechanism twice (layered erodibility K) and rejects the wrong one (height quantisation), but no document implements it: authoring a stratigraphic column, dipping it, and handing it to a solver as vertically varying K. → stratigraphy-and-lithology.md
- **mask-to-material** `covered` — How does a mask become a colour? The authoring half of materials — CLUT, palette and albedo assignment — which terrain-analysis-masks.md stops short of: it ends at material weights, and nothing on the generation axis mentions albedo at all. → mask-to-material.md
- **river-networks** `covered` — How do you synthesise a river network as an authoring operator rather than as an erosion by-product? Channel cross-section, width from discharge, valley widening, and the multi-thread braided and anastomosing planforms that a single-receiver network cannot express. → river-networks.md
- **impact-craters** `covered` — How do you place craters with the right depth-to-diameter law, rim, ejecta and superposition? Conspicuously absent next to planetary-precision.md, and cheaply groundable. → impact-craters.md
- **coastal-erosion** `covered` — How does a shoreline profile form and retreat? water-closed-vs-open.md covers the water surface; nothing covers what the waves do to the land. → coastal-erosion.md
- **mask-operators** `covered` — The two mask utilities other documents already assume: a distance transform (tectonic-uplift.md's "Use this" prescribes "a distance field from a spline" and never says how to compute one) and connected-component filtering to remove speckle without eroding real features. → mask-operators.md
- **sketch-based-authoring** `covered` — How does a user-drawn ridge line or river path become terrain that still obeys the erosion model? Constraint-based authoring, which is NOT inside the learned-and-example-based exclusion. → sketch-based-authoring.md
- **seamless-and-periodic** `covered` — How do you produce output that tiles without a seam? The easy half is periodic noise; the hard half is periodic erosion, where a simulation's boundary conditions decide whether the result can wrap at all. → seamless-and-periodic.md
- **learned-and-example-based** `out-of-scope` — Terrain synthesis from exemplars or networks is a live research area, but it does not tell someone building an engine what to implement this week, and this skill is opinionated about the classical pipeline it can source properly.
- **gis-and-real-dems** `out-of-scope` — Importing and conditioning real-world elevation data is a different job with different failure modes; the sibling skills cover ingestion, and mixing it in here dilutes the audience test.

## Simulation

- **simulation-time-budget** `covered` — Offline versus per-frame: what crossover decides every solver choice on this axis? → simulation-time-budget.md
- **water-closed-vs-open** `covered` — Pool and lake versus open sea: what differs in state, solver and boundary conditions? → water-closed-vs-open.md
- **wave-models** `covered` — Gerstner or FFT spectra, and what does the dispersion relation actually constrain? → wave-models.md
- **shallow-water** `covered` — Which solver for bounded interactive water, and where does the model stop being right? → shallow-water.md
- **water-optics** `covered` — Why does water look like water? Absorption with depth, refraction, total internal reflection. → water-optics.md
- **glacial-flow** `planned` — How do you move ice as a very slow fluid, and what exact benchmark proves the solver right? Deferred when this axis was narrowed to water; the sources are ready in terrain-architect `12`.
- **mass-wasting-runout** `planned` — Once a slope fails, where does the material actually come to rest? Deferred with the same narrowing; its space-integrated runout is the one mass-movement solver with no timestep.
- **snow-and-weather-state** `planned` — How do you carry surface state that changes while the heightfield does not? Deferred with the same narrowing.
- **sea-ice** `covered` — How does an ice sheet fracture into floes, and what moves them? Written because Gaea ships an `IceFloe` node; this row was previously recorded as the lowest-value one in this file, and the document states its own verdict on how much of the topic belongs here. → sea-ice.md
- **sky-and-weather-state** `covered` — **What atmospheric state does the world carry, and who else has to agree with it?** The simulation half of the sky: multiple-scattering LUT precomputation as an iterative solve rather than a lookup, one coverage field advected by the wind field `driver-fields.md` already produces, and time-of-day as evolving state rather than a per-frame parameter. Its load-bearing claim is **one sky state** — the same field shapes the clouds, drives the cloud-shadow term and sets weather intensity, so clouds, their shadows and the rain they imply agree. This row is *atmospheric* state; `snow-and-weather-state` below is *surface* state. They are the pair, and neither is the other. → sky-and-weather-state.md
- **full-3d-fluid** `out-of-scope` — Eulerian or particle 3D fluid is a general simulation subject with its own literature, and a terrain skill that half-covers it would be worse than one that points elsewhere. Height-field water is what this audience ships.

## Rendering

- **heightfield-lod** `covered` — How do you get a heightfield on screen at distance without cracks between tiles or popping between levels? → heightfield-lod.md
- **tiled-streaming** `covered` — How do you page terrain that does not fit in memory, without a hitch when the camera moves? → tiled-streaming.md
- **virtual-texturing** `covered` — How do you give terrain material detail at a resolution no single atlas can hold? → virtual-texturing.md
- **gpu-driven-culling** `covered` — How do you decide what to draw without a CPU round trip per object? → gpu-driven-culling.md
- **planetary-precision** `covered` — Where does float precision break at planetary scale, and what do you do about it? → planetary-precision.md
- **water-rendering** `covered` — How do you draw the water surface from both of its sides: reflection, refraction, depth colour, foam, the shoreline, and the view from underwater? → water-rendering.md
- **caustics** `covered` — How do you get focused light through a water surface, at each budget tier? → caustics.md
- **heightfield-raymarching** `covered` — How do you draw a heightfield by marching rays, for the near-real-time ray-traced tier? → heightfield-raymarching.md
- **mesh-extraction** `covered` — How do you get a mesh out, offline? heightfield-lod.md is entirely runtime; nothing covers TIN extraction, error-driven simplification, or the offline LOD chain a tool has to export. → mesh-extraction.md
- **atmosphere-and-aerial-perspective** `covered` — **How is the sky drawn, and how does every terrain pixel get its distance cue?** The sky is one fullscreen triangle drawn last and depth-tested — neither a dome nor a box, and a disk over the terrain is what compositing without a depth test looks like. Sampling the transmittance and sky-view LUTs and the aerial-perspective froxel volume; aerial perspective as *the* distance cue, without which a 40 km vista reads as a miniature; height fog as a bounded mood layer and never the world-scale distance model; the three-media rule that stops aerial perspective, height fog and froxel fog double-counting the same extinction; and the camera-relative frame, because a planet-absolute atmosphere shader jitters independently of jitter-free terrain. Closes a prescription `water-rendering.md` already makes and cannot route: share one atmosphere state with the sea, or the horizon splits at sunset. → atmosphere-and-aerial-perspective.md
- **volumetric-clouds** `covered` — **How do you draw a cloud deck that a mountain can pierce?** The analytic Perlin-Worley density model and the cheap/expensive two-level march, plus the three couplings that make this terrain's problem rather than general sky rendering: the cloud pass must read terrain depth and march to the nearer of cloud exit or terrain hit, or summits get cloud drawn over them; the ground-receiving cloud shadow, the cheapest large-scale life a vista buys; and the above-the-deck regime a summit forces. Its load-bearing claim is that **the famous 2015 lineage contains none of these three** — its own originator's 2023 scorecard says so — and that the density model is an artefact of a memory constraint that has since relaxed, so the crossover has a date and a direction, and the direction reverses. States plainly that what a typical 2026 team ships is not established by its sources. → volumetric-clouds.md
- **lighting-and-shadows** `planned` — What is different about shadowing terrain specifically, including large-scale occlusion? Cascaded and virtual shadow maps, heightfield-native self-shadowing, and the normal pipeline across LOD. ⚠️ This row used to be the corpus's only home for anything atmospheric, and its question never said so; sky *radiance* and aerial perspective now belong to `atmosphere-and-aerial-perspective`, so a reader picking this up writes a shadow document and leaves nothing behind.
- **brdf-theory** `out-of-scope` — Microfacet models and the rendering equation belong to the `physically-based-rendering` skill; Gaia cites it rather than restating it.

## Architecture

- **node-graph-runtime** `covered` — How is a node graph executed, cached, invalidated and kept resolution-independent? → node-graph-runtime.md
- **layering-filters-and-masks** `covered` — How are layering, filters and masks composed and executed, and what does masking cost the runtime? → layering-filters-and-masks.md
- **driver-fields** `covered` — What non-height fields does the graph carry — temperature, sun, shadow, water and wind flow — and how are they computed and shared? → driver-fields.md
- **verification-failures** `planned` — What does each characteristic failure look like, and what is the minimal fix? One catalogue across all three axes.
- **output-contracts** `planned` — What does a terrain pipeline hand downstream, and what contract stops a heightfield meaning different things in two places?
