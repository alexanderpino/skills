# K-RENDER findings (round 5)

### K-RENDER-1 · major · other
- Target: RND.ARCH.scene-sync, C-RSCENE, L14, docs/00 principle "change-tracked extraction"
- Finding: the capability row describes the legacy pattern the framework bans: "per-frame mirrored copy of every scene object ... CPU cost O(scene objects)". C-RSCENE, L14 and docs/00 say change-tracked deltas, O(changes), no per-object proxy mirror. The row owner's SKILL.md is generated from the row, so an agent would implement the proxy mirror. L14 also lists this row as its stance capability.
- Evidence: UE FScene/proxy sync and Unity's per-frame culling-data rebuild are the pattern; Frostbite/UE5 GPU Scene and Nanite persistent instance data are delta-based (Wihlidal, GDC 2017/2018; UE5 GPU Scene).
- Proposed change: rewrite as "Simulation to render extraction as change-tracked deltas into the persistent instance scene (C-INSTANCES); CPU cost O(changes); no per-object proxy mirror". Add a check that no capability name contains "mirrored copy" or "O(scene objects)".

### K-RENDER-2 · major · other
- Target: RND.SHADER.neural, C-SHADER, radar "In-shader neural evaluation", L82
- Finding: the row says "no standalone-dispatch fallback". C-SHADER says the neural tier has a "mandatory standalone-dispatch fallback through C-MLGPU", and the radar fallback is "Standalone inference dispatch". Following the row produces a feature that cannot degrade on non-cooperative-vector hardware. That is the "neural by default" dogma (L82).
- Evidence: cooperative vectors/matrix are single-vendor previews (SM 6.9, VK_NV_cooperative_vector); the row's own X class requires a fallback.
- Proposed change: reword to "single-vendor cooperative-vector tier; mandatory standalone-dispatch fallback via C-MLGPU (accuracy/cost delta recorded in the ADR)".

### K-RENDER-3 · major · maturity-error
- Target: RND.GI.restir (E, std3d), radar "ReSTIR GI & path-traced GI" (class E), RND.PT.realtime (M), RND.LIGHT.stochastic (M)
- Finding: three rows share the same technique family and evidence (ReSTIR, "shipped PT modes"). ReSTIR DI is M, ReSTIR PT is M (radar entry with identical name and evidence), and ReSTIR GI is E and inside the default std3d baseline. The E row's own revisit trigger, "RT tier performance on console-class hardware", is a promotion trigger, not an established one. The radar rule is that M needs two shipped titles with postmortems. Shipped ReSTIR GI/PT is essentially path-traced showcase modes on high-end NVIDIA PC. The row also has no console evidence and no non-RT fallback.
- Evidence: Ouyang et al. HPG 2021; Wyman/Lin ReSTIR PT 2022; shipped only as RT-Overdrive-class modes; Lumen and DDGI-class probes are the established GI on consoles.
- Proposed change: set RND.GI.restir to M, add the aaa profile tag, and make RND.GI.hybrid the std3d default. Merge the two radar entries into one M entry with per-capability evidence.

### K-RENDER-4 · major · maturity-error
- Target: RND.LOD.instanced-clusters (E), RND.LOD.foliage (E), radar "Cluster/virtualized geometry refinements" (M lists only deforming and displacement)
- Finding: instance sharing/assemblies and Nanite-style voxel/masked foliage in the virtualized tier are marked E. The neighbours with the same evidence, deforming LOD and displacement, are M. Assemblies and foliage arrived later (UE 5.5 to 5.7, experimental/beta), so they are not more mature than skinning/tessellation. As E they enter std3d by default and skip the radar fallback.
- Evidence: UE 5.5 to 5.7 release notes list Nanite assemblies and Nanite foliage as experimental/beta. No shipped-title postmortems exist.
- Proposed change: set both to M and add them to the radar refinement entry. Fallback is discrete LOD plus HLOD/impostors (RND.LOD.discrete, RND.LOD.hlod) and instanced draws.

### K-RENDER-5 · major · scale-down
- Target: path-tracing, ray-tracing-infrastructure (skill profiles lite3d+std3d, targets client+tools), RND.PT.reference, RND.PT.offline, RND.RT.as, RND.RT.software, RND.RT.sdf-scene, RND.RT.pipelines, RND.RT.instances, RND.RT.lod
- Finding: capabilities with no profile tag inherit the owner's profiles. lite-3d-mobile-client and lite-3d-web-client therefore have `path-tracing` and `ray-tracing-infrastructure` in their client closure. `RND.PT.reference` is described as "dev-only" and is the oracle, so it belongs in tools/test builds only. Shipping it in a mobile client breaches L52 (dev surface in shipping). Consumers are gated (RND.LIGHT.rt-shadows, GI.hybrid are std3d) but the provider rows are not.
- Evidence: reference path tracers in AAA (Falcor, Lumen reference mode, RenderDoc-style offline) are tool/dev builds; mobile RT is limited to a few devices.
- Proposed change: give path-tracing a kind/targets split (client only for PT.offline if required, otherwise tools/test) and tag RND.PT.reference "tools". Tag RND.RT.as/instances/pipelines/lod/software/sdf-scene with std3d (or a new "rt" capability profile). Add check.py: a capability described as dev-only must not resolve into a client target.

### K-RENDER-6 · major · omission
- Target: RND.GI.baked, RND.GI.probes, RND.TOOL.lighting, RES.MGMT.arbitration, WLD.PART.activation
- Finding: no runtime capability covers cell-streamed baked lighting (lightmap atlases, probe volumes, reflection captures) or lighting-scenario switching and time-of-day blending of baked data. RND.TOOL.lighting authors "lighting scenarios", but no runtime row owns them. RND.GI.baked is the only GI path on lite3d and mobile open-world (configs lite-3d-mobile-openworld-*), and it has no streaming or residency owner. The arbiter list (textures, geometry pages, shadow pages, BVH...) omits lighting data.
- Evidence: UE Lightmass/Volumetric Lightmap streaming by level, Unity Adaptive Probe Volumes with lighting scenarios and disk streaming, Frostbite baked probe streaming.
- Proposed change: add RND.GI.baked-streaming (global-illumination, E, contributors world-architect, resource-streaming-architect, async-io-storage) covering cell-bound lighting data, scenario blend and a pool registered with RES.MGMT.arbitration. Add the pool to the arbiter's list and to C-GI.

### K-RENDER-7 · minor · maturity-error
- Target: RND.SHADER.autodiff (M), RND.SHADER.neural (X), radar entry "... (RND.SHADER.autodiff)"
- Finding: the M row's radar evidence is "SM 6.9 cooperative vectors (preview); Slang autodiff". Preview status contradicts M by the radar's own rule. Runtime differentiable shading has no shipped game; autodiff is used for offline training and tools. The radar entry copies the X entry's tech name with a different class.
- Evidence: Slang autodiff is used in research/tools (Falcor, Nvidia neural-shader SDKs).
- Proposed change: set to X (experimental profile) or split into a tool-side M "autodiff for offline training kernels" and an X runtime row. Give the radar entry a distinct tech name.

### K-RENDER-8 · minor · maturity-error
- Target: RND.SHADER.toolchain (E, lists Slang), RND.SHADER.slang (M), RND.RHI.webgpu (M) vs RND.RHI.webgpu-validation/-quirks (E), RND.ARCH.multiview-nview (M)
- Finding: the E toolchain row includes Slang while the Slang adoption row is M. The WebGPU backend is M while its validation and quirk rows are E. For the autostereo row, the radar evidence is only vendor SDKs (Samsung, SpatialLabs) with no engine or title, which does not meet the M rule.
- Evidence: radar rule "M requires at least two shipped titles with postmortems".
- Proposed change: remove Slang from the E toolchain text (or mark it "optional, RND.SHADER.slang"). Set the WebGPU children to M, or note that only the backend is M. Downgrade multiview-nview to X.

### K-RENDER-9 · minor · other
- Target: radar "Sampler-feedback streaming" (fallback), RND.TEX.feedback, RND.TEX.vt, RES.MGMT.gpu-requests
- Finding: the radar fallback for sampler feedback is "Mip streaming". The actual established fallback, and the only cross-API path, is a shader-written feedback buffer (VT/Nanite-style page requests via RES.MGMT.gpu-requests). Hardware sampler feedback exists only on D3D12 and some consoles; Vulkan and Metal lack it. Falling back to distance-heuristic mip streaming would regress quality on Vulkan/Metal.
- Evidence: D3D12 sampler feedback spec versus Vulkan/Metal feature sets; UE streaming VT feedback pass.
- Proposed change: set the fallback to "shader-written feedback buffer (RND.TEX.vt feedback pass) then mip streaming". State in the row that the feedback abstraction is per-backend.

### K-RENDER-10 · minor · overlap
- Target: RND.LOD.hlod vs WLD.PART.hlod; RND.GI.bake-pipeline
- Finding: two rows own "HLOD". The LOD row owns proxy meshes and impostors; the world row owns "generation orchestration (builder implemented as a C-COOK processor)". The docs' format-owner rule assigns the builder algorithm to the format owner, so the proxy-builder owner is unclear. RND.GI.bake-pipeline is owned by global-illumination but its text says orchestration "belongs to CNT.COOK.world-build", which reads as a mixed owner.
- Evidence: docs/00 "format owner vs pipeline host".
- Proposed change: RND.LOD.hlod = proxy/impostor formats, builders (cook processors) and runtime selection; WLD.PART.hlod = strategy, partition and invalidation only. Reword bake-pipeline as "lighting bake processors (GI-owned) hosted by CNT.COOK.world-build".
