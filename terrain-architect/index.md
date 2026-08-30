---
okf_version: "0.2"
---
# terrain-architect

An OKF v0.2 knowledge bundle. Every document below carries its own
`type`, `status` and provenance in frontmatter; the trust tier a
consumer derives from `verified` is deliberately **unverified** on
all but the documents a checker actually re-derives.

# Entry point

* [Terrain Architect](SKILL.md) - Principal terrain-generation architect, implementation guide, and citation oracle for procedural landscapes, heightfields, terrain node graphs, and their GPU/runtime substrate. Use as the self-contained terrain-algorithm source for advanced offline/pre-cooked, runtime, or hybrid game-engine/world generators: design, implement, review, debug, or attribute erosion, hydrology, geology, climate, biomes, materials, masks, scatter, tiling, LOD, square or hexagonal lattices (flat heightfields, hex maps, spherical planets), and realtime terrain. Real-world GIS/DEM/lidar data is a first-class pipeline input (base layer, hydro-enforcement, void-fill) — the tool is a generator, not a passive GIS viewer. Pre-grounds neutral pseudocode in pinned open-source behavior for engine-native runtime fit (CPU/GPU scheduling, streaming, determinism, serialisation). Do not use for generic geology teaching, standalone GIS plotting, hiking, real-world erosion control, non-terrain texturing, or generic fluid simulation.

# evals

* [terrain-architect evals](evals/README.md) - How the capability and trigger evals are structured and what each axis is meant to probe.

# reference-impl

* [Archetype compositions](reference-impl/ARCHETYPES.md) - The archetype compositions: which atoms each named landscape is built from, in order.
* [Are we using the best simulations? — a grounded SOTA audit](reference-impl/SIMULATION-AUDIT.md) - A per-process SOTA scorecard against both the commercial and the academic frontier, with the metrics that would settle each verdict.
* [Atomic-base coverage & scope](reference-impl/ATOM-COVERAGE.md) - Which atomic bases are implemented, which are documented but deliberately deferred, and the harness that keeps the list honest against the modules.
* [Canon Comparison — every atom vs its canonical online counterpart](reference-impl/CANON-COMPARISON.md) - Every atom judged side by side against a canonical published output of the same algorithm, with per-atom verdicts.
* [Capability‑Grid Review Brief (for an external AI reviewer, e.g. Gemini)](reference-impl/REVIEW-BRIEF.md) - The standing brief an external reviewer works from, and the capability grid it refers to.
* [Node-Parity Audit — Gaea vs World Machine vs Houdini vs our atoms](reference-impl/NODE-PARITY-AUDIT.md) - What Gaea, World Machine and Houdini ship node by node, and which atomic capabilities are genuinely missing here after composites are excluded.
* [Reference implementations](reference-impl/README.md) - The reference implementation: what each module owns, how the pieces compose into a generator, and which audit answers which question.
* [Sandbox grounding & provenance](reference-impl/GROUNDING.md) - Where each sandbox behaviour comes from and which cross-check covers it, node by node.
* [Toward hyperrealism — what each archetype would need](reference-impl/HYPERREALISM.md) - What each archetype would still need to read as real, and where the numpy sandbox honestly tops out.
* [Validity evidence ledger](reference-impl/VALIDATION.md) - The validity evidence ledger: five rungs from dimensional consistency to agreement with real DEMs, kept explicit about what each rung does and does not prove.
* [Visual reference gallery](reference-impl/GALLERY.md) - The committed visual reference montages and the script that regenerates each one.

# references

* [Advanced Terrain Generator Blueprint](references/23-generator-blueprint.md) - The whole pipeline assembled: pre-cooked and runtime paths, and the handoffs between them.
* [Algorithm Index](references/00-index.md) - The skill's map of its own knowledge: every mechanism, its provenance tier, and the chapter that owns it.
* [Analysis & Masks](references/06-analysis-masks.md) - Deriving slope, curvature, aspect and flow-based masks from a heightfield, and the estimator errors each one carries.
* [Archetype Blueprints](references/20-archetypes.md) - Named landscapes as ordered compositions of atoms, each with the geomorphology it still owes.
* [Arid & Desert Landforms](references/16-arid-desert.md) - Inselbergs, alluvial fans, evaporite crusts and wadis: the arid assemblage and what each one requires upstream.
* [Bibliography](references/99-papers.md) - Every source this skill cites, with the tier at which it was read.
* [Climate & Ecosystem](references/13-climate-ecosystem.md) - Insolation, moisture and temperature fields, and the biome assignment that reads them.
* [Engine Data Handoff & First-Class Auxiliary Maps](references/27-engine-data-handoff.md) - What the generator hands the renderer, as a registry with units and lifetimes rather than a folder of images.
* [Flow Routing](references/03-flow-routing.md) - Depression filling and the routing family — D8, D-infinity, MFD and the hybrid — with the concentration statistic that separates them and reverses at low relief.
* [GPU & Realtime](references/15-gpu-realtime.md) - What moves to the GPU and what cannot, and the determinism the runtime path has to preserve.
* [Geological Formation](references/11-geological.md) - Strata, lithology contrast, karst, duricrust and relief inversion: structure the erosion inherits rather than invents.
* [Glacial, Coastal & Marine](references/12-glacial-coastal.md) - Glacial carving on the shallow-ice approximation, and the coastal chain from radiation stress through nearshore currents to the bar and rip system.
* [Graph Runtime](references/14-graph-runtime.md) - The node graph as an executable object: evaluation order, the resolution pyramid, memory and scheduling.
* [Hexagonal Grids](references/26-hexagonal-grids.md) - The hexagonal working grid: two vertex classes, the rhombille tiling, the three meshes over one field, and what corner-only sampling costs.
* [Hydraulic Erosion](references/04-erosion-hydraulic.md) - Stream power, droplet and pipe erosion: what each one is a model OF, and which is right for a given scale.
* [Lava: Generation & Simulation](references/19-lava.md) - Lava as a Bingham fluid: the driving stress, the yield behaviour, and the flow-length limit that follows.
* [Liquids: Optical & Rheological Identity](references/28-liquids.md) - Per-body water identity from its causes: CDOM darkens and sediment brightens, and the constants a renderer needs follow from the catchment.
* [Macro Terrain & Tectonics](references/02-macro-tectonics.md) - Continental form before erosion: plate uplift, fault scarps and the isostatic response that decides what the erosion runs on.
* [Noise](references/01-noise.md) - Noise as the base layer: Perlin, value, simplex, Worley and Gabor, the fractal compositions over them, and the lattice pinch points that make lacunarity exactly 2 a defect.
* [Object Distribution](references/07-scatter.md) - Blue-noise and density-driven scatter, layer interactions, and why variable density is the hard case.
* [Open-Source Grounding Ledger](references/22-open-source-grounding.md) - Which open-source implementations each algorithm was checked against, and which remain port targets rather than reimplementations.
* [Output Contract](references/08-output-contract.md) - What a generator must export and in what units: the field registry, precision doctrine, and the tiling and seam rules.
* [Periglacial & Permafrost Landforms](references/17-periglacial.md) - Patterned ground, thermokarst and pingos, on the Kessler & Werner sorting model.
* [Planetary & Spherical Worlds](references/25-planetary-spherical.md) - Cube-sphere and geodesic parameterisations, their distortion, and what changes when the domain has no edges.
* [Primitives, Operators, Filters & Warps](references/10-primitives-ops-filters.md) - The SDF and gradient primitives, the combiners, and the three distinct roles a curve plays — the distinction that costs the most rebuilds when missed.
* [Reference-Informed, Engine-Native Implementation](references/21-clean-room-implementation.md) - How to reimplement these algorithms in an engine without copying source, and where the licence boundary actually sits.
* [Surface Materials](references/18-materials.md) - Deriving a material stack from slope, curvature and drainage rather than painting one.
* [Thermal & Aeolian Erosion](references/05-erosion-thermal-aeolian.md) - Talus and mass wasting by angle of repose, and the Bagnold-grounded aeolian transport that builds dunes.
* [Verification](references/09-verification.md) - How each mechanism is checked: the estimator ladder, the controls that make a metric evidence, and the lattice-anisotropy trap that scores a broken operator perfectly.
* [Voxel & Streaming Chunk Generation](references/24-voxel-streaming-generation.md) - Generation for volumetric worlds: chunk-local determinism, caves and overhangs as a separate paradigm from the heightfield.
