---
okf_version: "0.2"
---
# terrain-renderer

An OKF v0.2 knowledge bundle. Every document below carries its own
`type`, `status` and provenance in frontmatter; the trust tier a
consumer derives from `verified` is deliberately **unverified** on
all but the documents a checker actually re-derives.

# Entry point

* [Terrain Renderer](SKILL.md) - Principal terrain-rendering authority for real-time worlds, across every paradigm: heightfield LOD (clipmaps, CDLOD, CBT), cluster/meshlet virtualized geometry (Nanite family), engine-native terrain (UE Landscape, Nanite Landscape, Mesh Terrain), blocky/smooth voxels (greedy meshing, marching cubes, Transvoxel, dual contouring), heightfield raymarching, tiled streaming, splatmaps and virtual texturing, GPU-driven culling, planetary precision, terrain lighting and shadows, water surfaces (Gerstner/FFT, the shore-wave band, rivers, the fullscreen-triangle pass, pass ordering, engine-native water) and real-time fluid sim (SPH/PBF, buoyancy), snow/weather state, auxiliary maps, vegetation/scatter, roads/decals/deformation, physics handoff, tool viewports. Use when drawing terrain, meshing chunks, fixing LOD seams, texturing at scale, putting water on a world, or streaming large worlds - even if 'terrain' is never said (heightmap renderer, Minecraft clone, planet renderer). Not for terrain generation (terrain-architect), BRDF math (physically-based-rendering), or the measured physics of water - optics, IOPs, glitter, caustics, foam, breaking, diffraction - which is water-physics.

# references

* [Auxiliary maps at runtime: consuming the generator's field registry](references/14-auxiliary-maps-runtime.md) - Auxiliary maps at runtime: consuming the generator field registry without re-deriving it in the sampling shader.
* [Blocky Voxel Rendering: The Minecraft Family](references/04-voxel-blocky.md) - Blocky voxel rendering: meshing, face culling, greedy merging and the streaming shape the Minecraft family settled on.
* [Cluster / Meshlet Virtualized Geometry for Terrain](references/02-cluster-virtualized-geometry.md) - Cluster and meshlet virtualized geometry applied to terrain, and where the Nanite family stops being the right answer.
* [Engine-Native Terrain: Unreal Landscape & Friends](references/03-engine-terrain-unreal.md) - Engine-native terrain systems: Unreal Landscape, Nanite Landscape and Mesh Terrain, and what each one fixes the shape of.
* [GPU-driven culling & submission](references/08-gpu-driven-culling.md) - GPU-driven culling and submission: the hierarchical depth pyramid, its mip selection rule, and indirect draw construction.
* [Heightfield LOD: from geomipmapping to CBT](references/01-heightfield-lod.md) - Heightfield level of detail from geomipmapping to concurrent binary trees, with the screen-space error metric that orders them.
* [Heightfield Ray Marching: from Voxel Space to Relief Mapping and Heightfield Ray Tracing](references/18-heightfield-raymarching.md) - Heightfield ray marching from Voxel Space to relief mapping, and the step-count arithmetic that decides whether it is affordable.
* [Lighting, shadows, and terrain integration](references/10-lighting-shadows.md) - Lighting, shadows and terrain integration: cascade snapping, the sky illuminant, receiver weights and the azimuth fold about solar noon.
* [Planetary Rendering & Numerical Precision](references/09-planetary-precision.md) - Planetary rendering and numerical precision: the float32 binade staircase, reversed-Z, camera-relative transforms and cube-sphere mappings.
* [Real-Time Fluid Simulation](references/19-fluid-simulation.md) - Real-time fluid simulation on terrain: shallow-water and pipe models, their stability limits, and what each one cannot represent.
* [Roads, decals, runtime modification, and the physics handoff](references/17-roads-decals-physics.md) - Roads, decals, runtime modification and the physics handoff, including the replayable stamp list that keeps them cache-safe.
* [Smooth Voxel Terrain: Isosurface Extraction & LOD](references/05-voxel-smooth-isosurface.md) - Smooth voxel terrain: isosurface extraction, the marching-cubes case count and its ambiguous faces, dual methods, and LOD across chunk seams.
* [Snow, weather, and dynamic surface state](references/13-snow-weather-surface-state.md) - Snow, weather and dynamic surface state as a runtime state machine: its storage, its writers and its readers.
* [Technique Index](references/00-index.md) - The technique index: every mechanism in this skill, its tier, and the chapter that owns it.
* [Terrain materials, splatting, and virtual texturing](references/07-materials-virtual-texturing.md) - Terrain materials, splatting and virtual texturing, including the cache-invalidation traps that runtime state walks into.
* [Tiled Worlds & Streaming](references/06-tiled-streaming.md) - Tiled worlds and streaming: residency budgets, prefetch radius, and the arithmetic that decides whether a tile arrives in time.
* [Tool Viewports: Interactive Preview Rendering for Terrain Authoring](references/16-tool-viewports.md) - Tool viewports: interactive preview rendering for terrain authoring, and why the editor path is not the runtime path.
* [Vegetation & scatter rendering](references/15-vegetation-scatter.md) - Vegetation and scatter rendering: instancing, impostors, density fields and the LOD boundary where a plant stops being geometry.
* [Verification, profiling & the failure catalogue](references/11-verification-failures.md) - Verification, profiling and the failure catalogue: how each mechanism in this skill is checked, and the symptoms that say it is not.
* [Water Rendering](references/12-water-rendering.md) - The render-side architecture of water: surface LOD, pass ordering, engine-native systems and shoreline integration. Routes to water-physics for every number it quotes.
