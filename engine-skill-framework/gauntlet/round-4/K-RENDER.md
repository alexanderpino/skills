# K-RENDER findings (Rendering Critic, round 4)

### K-RENDER-1 · major · maturity-error
- Target: RND.PT.realtime, RND.GI.restir, RND.GI.rt-required, radar.json
- Finding: RND.PT.realtime ("Real-time path tracing (ReSTIR PT class)") is E, but RND.GI.restir ("ReSTIR GI & path-traced GI") is M and on the radar with fallback "Probe/radiance-cache GI". The same technique carries two maturity classes. Because E capabilities need no radar row, real-time PT has no revisit trigger and no fallback, and RND.GI.rt-required (consumer via path-tracing) inherits the false E.
- Evidence: Shipped PT modes (Cyberpunk 2077 RT Overdrive, Alan Wake 2, Black Myth) are vendor-tuned, top-end-GPU-only, and rely on proprietary ray-reconstruction denoisers (RND.RECON.ml-denoise is M). ReSTIR PT (Lin et al., SIGGRAPH 2022) is still evolving; no console-class shipped title runs it.
- Proposed change: set RND.PT.realtime to M; add a radar entry (evidence above, revisit "console-class budget fit without vendor-only denoiser", fallback RND.GI.hybrid/probes); keep RND.PT.reference and RND.PT.offline as E.

### K-RENDER-2 · major · missing-contract
- Target: atmosphere-weather, terrain, vegetation-foliage, C-SCENETEX, C-COLOR, C-RT, C-LIGHT
- Finding: atmosphere-weather owns WLD.ENV.media-integrator (froxel injection, cloud and aerial-perspective composition, ordering against translucency) and WLD.ENV.clouds/sky, but consumes neither C-SCENETEX (depth, HZB, velocity) nor C-COLOR (pre-exposure and the frame latency of exposure) nor C-GI. terrain consumes no C-LIGHT, C-GI, C-RT or C-SCENETEX; vegetation-foliage no C-SCENETEX or C-GI. check.py cannot see implicit use. Where terrain, water and vegetation take part in shadows, surface caches, TLAS and SDF scenes is unowned: RND.RT.instances and RND.RT.lod name only virtualized-geometry-lod, and terrain-render lists only geometry-pipeline as contributor.
- Evidence: Sky, cloud and froxel-fog passes must read scene depth and write pre-exposed scene color (Hillaire, "Physically based sky, atmosphere and cloud rendering in Frostbite"; UE Volumetric Cloud and Height Fog). Heightfield and clipmap terrain in a hybrid-GI/RT scene needs a BLAS or SDF path (UE Lumen landscape cards, Horizon Forbidden West terrain in the TLAS).
- Proposed change: add C-SCENETEX?, C-COLOR? and C-GI? to atmosphere-weather consumes; add C-LIGHT?, C-RT?, C-GI? and C-SCENETEX? to terrain; add C-SCENETEX? to vegetation-foliage and water-ocean (already has SCENETEX); add terrain, water-ocean and vegetation-foliage as contributors of RND.RT.instances and RND.RT.lod; add a capability WLD.ENV.terrain-rt (heightfield/clipmap to BLAS/SDF proxy, owner terrain, contributor ray-tracing-infrastructure).

### K-RENDER-3 · major · omission
- Target: RND.LOD (virtualized-geometry-lod), WLD.ENV.vegetation (vegetation-foliage), RND.GEO.instancing, C-GEOLOD
- Finding: No capability covers instance-level sharing inside a cluster hierarchy (hierarchical or assembly instancing of clustered meshes) nor dense masked/translucent foliage in the virtualized-geometry tier. vegetation-foliage owns "Vegetation instancing & rendering" while geometry-pipeline owns RND.GEO.instancing and virtualized-geometry-lod owns cluster LOD. C-GEOLOD is optional for vegetation and its summary says nothing about instanced clusters. Foliage is the most expensive content of open worlds and the case where a cluster tier breaks (alpha test, wind vertex motion, sub-pixel thin geometry).
- Evidence: UE 5.5-5.7 Nanite Assemblies and Nanite foliage (voxel-based foliage LOD, WPO with disable distances); Fortnite/Matrix Awakens instancing talks; Ubisoft GPU-driven foliage talks. C-MATIF already carries WPO and mask, so the material half exists but the geometry half has no owner.
- Proposed change: add RND.LOD.instanced-clusters (instance sharing, assemblies, per-instance bounds expansion for WPO) and RND.LOD.foliage (masked and thin-geometry LOD, voxel/impostor transition) owned by virtualized-geometry-lod with vegetation-foliage and geometry-pipeline as contributors; state in vegetation-foliage non-responsibilities that cluster LOD is not its own; make C-GEOLOD non-optional for vegetation on std3d.

### K-RENDER-4 · minor · missing-contract
- Target: C-SCENETEX, C-MATH, C-TEMPORAL, RND.ARCH.scene-textures
- Finding: Depth and projection conventions (reverse-Z, floating-point depth, infinite far plane, jitter application in clip space, pixel-center and Y-flip differences across D3D/Vulkan/Metal/WebGPU) have no capability. C-MATH has generic handedness/units conventions; C-SCENETEX lists depth and HZB without convention. Independent agents writing HZB culling, VSM, RT, TAA and vendor upscalers will diverge, and vendor SDKs require specific depth and jitter conventions.
- Evidence: Reversed-Z float depth is the de facto standard (Reed 2015; UE, Frostbite, Unity HDRP); DLSS/FSR/XeSS integration guides fix depth/motion-vector/jitter conventions.
- Proposed change: add RND.ARCH.depth-convention (owner render-architect, contributors math-simd-numerics, reconstruction-upscaling, xr-runtime) and mention it in C-SCENETEX; conformance case in render-validation.

### K-RENDER-5 · minor · scale-down
- Target: RND.SHADER (shader-system), RND.MAT.tiers, RND.GPU.tiers
- Finding: There is no numeric-precision policy for shaders (FP16/RelaxedPrecision/min16, packed math, integer precision, subgroup-size assumptions). C-MATH precision classes are CPU-side. On mobile, portable and console-class GPUs, half precision is a 2x ALU/register-pressure lever and a common source of visible banding and NaN bugs.
- Evidence: Arm/Qualcomm/Apple GPU best-practice guides (mediump/half throughput); PS5/Xbox packed-FP16; DXC 16-bit types and SM 6.2+ native FP16 tiers.
- Proposed change: add RND.SHADER.precision (mixed-precision policy per tier and pass, validation against FP32 reference via render-validation) owned by shader-system, contributors platform-mobile, material-system; gate through C-GPUTIER.

### K-RENDER-6 · minor · omission
- Target: RND.ARCH.multiview, RND.ARCH.editor-rendering, ui-architect, GAM.CAM.photo, QA.RENDER.final-frame
- Finding: Runtime offscreen render products are not owned as a feature: isolated render scenes with their own lighting environment and budget for 3D UI content (character creator, inventory preview, portraits, item icons), in-world render-to-texture (mirrors, security cameras, minimap), and player capture (photo mode high-resolution tiled capture, UI-less capture, HDR/SDR screenshot output, platform share-capture restrictions). RND.ARCH.multiview mentions "captures" only in passing, C-EDVIEW preview-world is editor-only, and QA.RENDER.final-frame is a test capture.
- Evidence: Common in shipped games (inventory previews in Diablo IV/Destiny, photo modes in Horizon and God of War with tiled capture and TAA/DoF overrides); console share-button and protected-content capture rules.
- Proposed change: add RND.ARCH.offscreen-scenes (isolated render world, output as texture to C-DRAW2D/C-VIDEO-like surfaces, budget class) and RND.ARCH.capture (screenshot/photo capture pipeline, HDR container output) owned by render-architect, contributors ui-architect, gameplay-camera, platform-services; add C-CERT entry for capture restrictions.

### K-RENDER-7 · minor · obsolete-assumption
- Target: RND.GEO.precomputed-visibility, legacy-patterns.json
- Finding: Baked PVS/portal-cell visibility is a Quake-era technique carried as an unscoped E capability with no profile tag and no legacy-catalogue entry stating when it is justified. Agents may reach for it on GPU-driven tiers where two-phase HZB culling (RND.GEO.culling) replaces it.
- Evidence: Modern usage is confined to mobile and low-end CPU-culled paths (Umbra-class occlusion, indoor cell/portal); GPU-driven tiers use HZB culling.
- Proposed change: tag the capability lite3d only (or via the CPU-submission tier), add a legacy pattern with default stance "GPU HZB culling; baked visibility only on CPU-culled tier by ADR" and stance_capabilities [RND.GEO.culling, RND.GEO.cpu-occlusion, RND.GEO.precomputed-visibility].

### K-RENDER-8 · minor · missing-contract
- Target: RND.RHI.pso, RND.SHADER.precache, RND.MAT.tiers, legacy L29
- Finding: L29's stance says "async creation with fallbacks" but no capability owns the fallback behavior when a PSO is not ready: skip the draw, hold the frame, draw a fallback material, or block. The choice is pass-dependent (depth and shadow passes cannot skip without visible errors, RT hit pipelines must be complete before TLAS use, gameplay-critical geometry must not vanish) and spans rhi-core, shader-system and material-system.
- Evidence: UE PSO precache policies (skip/delay draws) and Unity shader warmup; hitch versus pop-in tradeoff described in vendor PSO stutter guidance.
- Proposed change: add RND.MAT.pso-miss-policy (per pass and material domain policy table, telemetry hook to PRF.LOAD.hitch-gate) owned by material-system, contributors rhi-core, shader-system, render-architect; add it to L29 stance_capabilities.
