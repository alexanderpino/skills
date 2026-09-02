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
- **procedural-placement** `planned` — Scattering rocks, vegetation and debris from the masks, including blue-noise sampling. Load-bearing for a tool builder and not yet written.
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
- **full-3d-fluid** `out-of-scope` — Eulerian or particle 3D fluid is a general simulation subject with its own literature, and a terrain skill that half-covers it would be worse than one that points elsewhere. Height-field water is what this audience ships.

## Rendering

- **heightfield-lod** `planned` — How do you get a heightfield on screen at distance without cracks between tiles or popping between levels?
- **tiled-streaming** `planned` — How do you page terrain that does not fit in memory, without a hitch when the camera moves?
- **virtual-texturing** `planned` — How do you give terrain material detail at a resolution no single atlas can hold?
- **gpu-driven-culling** `planned` — How do you decide what to draw without a CPU round trip per object?
- **planetary-precision** `planned` — Where does float precision break at planetary scale, and what do you do about it?
- **water-rendering** `planned` — How do you draw the surface: reflection, refraction, depth colour, foam and the shoreline?
- **caustics** `planned` — How do you get focused light through a water surface, at each budget tier?
- **heightfield-raymarching** `planned` — How do you draw a heightfield by marching rays, for the near-real-time ray-traced tier?
- **lighting-and-shadows** `planned` — What is different about shadowing terrain specifically, including large-scale occlusion?
- **brdf-theory** `out-of-scope` — Microfacet models and the rendering equation belong to the `physically-based-rendering` skill; Gaia cites it rather than restating it.

## Architecture

- **node-graph-runtime** `planned` — How is a node graph executed, cached, invalidated and kept resolution-independent? The core architecture of a Gaea/World-Machine-class tool.
- **verification-failures** `planned` — What does each characteristic failure look like, and what is the minimal fix? One catalogue across all three axes.
- **output-contracts** `planned` — What does a terrain pipeline hand downstream, and what contract stops a heightfield meaning different things in two places?
