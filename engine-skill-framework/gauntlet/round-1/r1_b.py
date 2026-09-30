"""G1 round-1 revision, part B: renames, rendering, physics, animation, audio, input."""

CLIENT_TOOLS = ["client", "tools"]
ALL_T = ["client", "headless-client", "server", "tools"]


def renames(ed):
    ed.rename_skill("gpu-driven-pipeline", "geometry-pipeline", tags="K-LEGACY-7")
    ed.rename_skill("platform-mobile-portable", "platform-mobile", tags="K-PLATFORM-12")
    ed.rename_skill("character-vehicle-physics", "character-physics", tags="K-SIM-10")
    ed.rename_skill("platform-online-services", "platform-services", tags="K-COMPLETE-1 K-PLATFORM-10 (split)")


def rendering(ed):
    # --- GPU platform lead and backend split
    ed.skill_add(id="gpu-platform-architect", name="GPU Platform Architect", tier="lead", parent="engine-architect",
                 profiles=["all"], kind="runtime", targets=CLIENT_TOOLS, workstream="rendering",
                 purpose="GPU platform architecture shared by every renderer tier: layering of RHI, GPU memory, render "
                         "graph, shader system, ray-query and inference infrastructure; the GPU feature-tier model "
                         "(binding, pipeline-state, queue, mesh, RT, tensor tiers) and API baselines per hardware tier; "
                         "task-based parallel command recording.",
                 non_responsibilities=[["Rendering pipeline and features", "render-architect"],
                                       ["Individual API backends", ["rhi-d3d12", "rhi-vulkan", "rhi-metal", "rhi-webgpu"]],
                                       ["Frames in flight / thread existence", "frame-orchestration"]],
                 consumes=["C-RHI", "C-PAL"],
                 expertise=["explicit graphics APIs", "GPU architecture across vendors", "API evolution tracking"],
                 tags="K-ARCH-7 K-PROD-13 K-RENDER-16 K-PLATFORM-4")
    ed.contract_add("C-GPUTIER", 2, "gpu-platform-architect", "GPU feature tiers",
                    "Named GPU feature tiers (binding model, pipeline-state model, queue topology, mesh/RT/tensor "
                    "support, memory model) and the API baseline each tier maps to; render features declare the "
                    "minimum tier they need.", ["C-RHI"], tags="K-FUTURE-7 K-PLATFORM-4")
    for s_ in ("rhi-core", "gpu-memory-resources", "render-graph-scheduling", "shader-system",
               "ray-tracing-infrastructure", "ml-inference-runtime"):
        ed.skill_set(s_, parent="gpu-platform-architect", tags="K-ARCH-7 K-ARCH-17")
    ed.area("RND.GPU", "GPU platform", tags="K-ARCH-7")
    ed.cap("RND.GPU.layering", "GPU platform layering & cross-backend architecture", "gpu-platform-architect",
           tags="K-ARCH-7")
    ed.cap("RND.GPU.tiers", "GPU feature-tier model & API baselines per hardware tier (C-GPUTIER)",
           "gpu-platform-architect", contrib=["rhi-core", "performance-architect"], tags="K-PLATFORM-4 K-FUTURE-7")
    ed.cap_move("RND.ARCH.threading", "RND.GPU.recording", tags="K-ARCH-7 K-LEGACY-4")
    ed.cap_set("RND.GPU.recording", name="Parallel command recording; render work as tasks (no dedicated render thread "
               "unless an API mandates affinity, by ADR)", owner="gpu-platform-architect", tags="K-LEGACY-4 K-SYSTEMS-3")

    ed.contract_set("C-RHI", needs_implementer=True, tags="K-FUTURE-7 K-PLATFORM-4 K-RENDER-10 K-SYSTEMS-8",
                    summary="Devices, queues and command recording, completion tokens, binding-model tier (bindless / "
                            "descriptor-buffer / bind-group), pipeline-state-model tier (monolithic PSO / libraries / "
                            "shader objects / state-object programs), GPU-generated work primitives, presentation, "
                            "implicit-sync backends; the RHI consumes C-PRESENT to report present feedback.")
    rhi = "rhi-core"
    ed.cap_del("RND.RHI.backends", tags="K-RENDER-16 K-PLATFORM-4 (split per backend)")
    ed.cap_move("RND.RHI.bindless", "RND.RHI.binding-tiers", tags="K-RENDER-10")
    ed.cap_set("RND.RHI.binding-tiers", name="Binding-model tiers: bindless (default where capable) and bounded "
               "bind-group/descriptor-set tier", add_contrib=["shader-system"],
               tags="K-RENDER-10 K-PLATFORM-5 K-LEGACY-8 K-FUTURE-7")
    ed.cap("RND.RHI.implicit-sync", "Implicit-synchronization backends (WebGPU): graph barrier output mapped or elided",
           rhi, contrib=["render-graph-scheduling"], tags="K-LEGACY-8")
    ed.cap_set("RND.RHI.pso", name="Pipeline-state models & caches (PSO, pipeline libraries, shader objects), async "
               "creation", tags="K-FUTURE-7")
    ed.cap_set("RND.RHI.crash", name="GPU fault instrumentation: breadcrumbs, markers, dump generation, device-lost "
               "recovery", tags="K-RENDER-20")
    ed.cap("RND.RHI.driver-policy", "Driver version policy: minimum/known-bad drivers, deny-lists, user handling", rhi,
           contrib=["crash-diagnostics"], tags="K-PLATFORM-7")
    ed.cap("RND.RHI.software-device", "Null/software GPU device for headless CI (WARP/lavapipe/SwiftShader class)",
           rhi, contrib=["render-validation"], tags="K-QUALITY-10")
    ed.cap("RND.RHI.capture-integration", "Programmatic GPU capture integration (PIX/RenderDoc class)", rhi,
           tags="K-RENDER-20")
    ed.cap("RND.RHI.gpu-work", "GPU-generated work primitives (indirect, device-generated commands, work-graph programs, "
           "backing memory)", rhi, contrib=["render-graph-scheduling", "geometry-pipeline"], tags="K-FUTURE-8")
    ed.cap("RND.RHI.conformance", "Backend conformance test suite", rhi, contrib=["render-validation"],
           tags="K-PLATFORM-4 K-QUALITY-6")
    ed.skill_set(rhi, consumes=["C-PAL", "C-SYNC", "C-PRESENT", "C-FRAME"],
                 non_responsibilities=[["GPU memory allocation", "gpu-memory-resources"],
                                       ["Barrier planning", "render-graph-scheduling"],
                                       ["Shader compilation", "shader-system"],
                                       ["Per-API backend code", ["rhi-d3d12", "rhi-vulkan", "rhi-metal", "rhi-webgpu", "platform-console"]]],
                 tags="K-SYSTEMS-8 K-RENDER-16")
    backends = [("rhi-d3d12", "D3D12 backend", ["pc"], "D3D12 (Agility SDK features: enhanced barriers, work graphs, "
                 "SM 6.x, GPU upload heaps)", ["D3D12", "Agility SDK", "DXGI"]),
                ("rhi-vulkan", "Vulkan backend", ["pc", "mobile", "xr-standalone"], "Vulkan (profiles incl. Android "
                 "Baseline, descriptor buffers/heaps, synchronization2, dynamic rendering)", ["Vulkan", "SPIR-V", "Android GPU drivers"]),
                ("rhi-metal", "Metal backend", ["pc", "mobile"], "Metal 3/4 (argument buffers, residency sets, MTL4 "
                 "command model)", ["Metal", "Apple GPU families"]),
                ("rhi-webgpu", "WebGPU backend", ["web"], "WebGPU (bind groups, implicit sync, limits tiers)",
                 ["WebGPU", "WGSL", "browser GPU processes"])]
    for sid, name, plats, scope, exp in backends:
        ed.skill_add(id=sid, name=f"RHI {name}", tier="expert", parent="gpu-platform-architect", profiles=["all"],
                     kind="runtime", targets=CLIENT_TOOLS, platforms=plats, workstream="rendering",
                     purpose=f"Implements C-RHI on {scope}; owns its validation-layer runs and vendor/driver quirks.",
                     non_responsibilities=[["RHI abstraction & capability model", "rhi-core"],
                                           ["Other API backends", "rhi-core"]],
                     consumes=["C-PAL", "C-SYNC", "C-GPUTIER"], implements=["C-RHI"], expertise=exp,
                     tags="K-RENDER-16 K-PLATFORM-4")
        key = sid.split("-")[1]
        ed.cap(f"RND.RHI.{key}", f"{name}: implementation of C-RHI", sid, tags="K-RENDER-16")
        ed.cap(f"RND.RHI.{key}-validation", f"{name}: validation layers & conformance runs", sid,
               contrib=["render-validation"], tags="K-PLATFORM-4")
        ed.cap(f"RND.RHI.{key}-quirks", f"{name}: vendor/driver quirk handling", sid, contrib=["rhi-core"],
               tags="K-PLATFORM-4")
    ed.cap_set("RND.RHI.webgpu", mat="M", tags="K-RENDER-19")

    # --- render graph, shaders, memory
    rg = "render-graph-scheduling"
    ed.contract_set("C-RG", tags="K-FUTURE-8 K-LEGACY-8",
                    summary="Pass/resource declaration, queues, history resources, readback, dynamic GPU-generated work "
                            "nodes; barrier output mapped or elided on implicit-sync backends.")
    ed.cap_set("RND.GRAPH.work-graphs", name="Scheduling, barriers & memory for GPU-generated work incl. work graphs",
               mat="X", tags="K-RENDER-14 K-FUTURE-8")
    ed.cap("RND.GRAPH.validation", "Render-graph access validation against executed commands & sync-validation layers",
           rg, contrib=["render-validation"], tags="K-QUALITY-8")
    sh = "shader-system"
    ed.contract_set("C-SHADER", tags="K-FUTURE-3 K-RENDER-10",
                    summary="Shader modules, permutations and budgets, binding layouts generated per binding tier, "
                            "interop headers, neural/tensor intrinsics tier.")
    ed.cap_set("RND.SHADER.language", name="Shading language & dialect policy (HLSL-class baseline)", tags="K-RENDER-19")
    ed.cap("RND.SHADER.slang", "Slang adoption (modules, generics, multi-target)", sh, mat="M", tags="K-RENDER-19")
    ed.cap("RND.SHADER.precache", "Load-time PSO precaching from loaded asset/material/pass combinations", sh,
           contrib=["material-system", "rhi-core", "resource-streaming-architect"], tags="K-PERF-14")
    ed.cap("RND.SHADER.permutation-budget", "Permutation & PSO-count budgets with cook-time enforcement", sh,
           contrib=["performance-architect"], tags="K-PERF-14")
    ed.cap_set("RND.SHADER.pso-lists", name="PSO coverage validation from play traces", tags="K-PERF-14")
    ed.cap("RND.SHADER.neural", "In-shader neural evaluation (cooperative-vector/tensor intrinsics, weight layout, "
           "fallbacks)", sh, mat="M", contrib=["ml-inference-runtime"], tags="K-FUTURE-3")
    ed.cap("RND.SHADER.autodiff", "Differentiable shader compilation (Slang-class autodiff)", sh, mat="M",
           tags="K-FUTURE-3")
    ed.cap("RND.SHADER.binding-abstraction", "Shader-side binding abstraction generated per binding tier", sh,
           contrib=["rhi-core"], tags="K-RENDER-10")
    ed.cap("RND.SHADER.gpu-debug-draw", "Shader-side debug draw for GPU-driven passes", sh,
           contrib=["visual-debugging-tools"], tags="K-RENDER-20")
    ed.cap("RND.SHADER.untrusted", "GPU-DoS limits for UGC-authored graphs/shaders", sh, contrib=["modding-ugc"],
           tags="K-QUALITY-11")
    ed.use(sh, "C-GPUTIER", "C-ML?", tags="K-FUTURE-3")
    ed.use(sh, "C-RELOAD?", tags="K-ARCH-5")
    ed.use("gpu-memory-resources", "C-GPUTIER", tags="K-FUTURE-7")

    # --- render architecture
    ra = "render-architect"
    ed.contract_set("C-RSCENE", tags="K-LEGACY-4 K-PERF-3 K-ARCH-2 K-FUTURE-9",
                    summary="Render features and views, render-scene data streams extracted as change-tracked deltas "
                            "(no per-object proxy mirror; CPU cost O(changes)), feature registration with minimum GPU "
                            "tier, non-mesh primitive kinds.")
    ed.cap_set("RND.ARCH.scene-sync", name="Simulation→render extraction: change-tracked, parallel, versioned delta "
               "streams (CPU cost O(changes))", add_contrib=["frame-orchestration"], tags="K-LEGACY-4 K-PERF-3")
    ed.cap("RND.ARCH.submission-strategy", "Submission strategy per hardware tier (GPU-driven vs CPU-culled batched), by "
           "ADR; TBDR suitability", ra, contrib=["geometry-pipeline", "platform-mobile"], tags="K-LEGACY-7")
    ed.cap("RND.ARCH.editor-rendering", "Editor render features: GPU picking, selection outline, editor primitives, "
           "preview scenes & thumbnails", ra, contrib=["world-editor-viewport", "editor-ui-framework"], tags="K-RENDER-13")
    ed.cap_set("RND.ARCH.multiview", name="Multi-view rendering: split-screen, PiP, captures, stereo/multiview and N-view "
               "(autostereo/light-field) outputs", add_contrib=["xr-runtime"], tags="K-RENDER-11 K-FUTURE-19")
    ed.cap_del("PLAT.XR.stereo", tags="K-RENDER-11 (moved into RND.ARCH.multiview)")
    ed.skill_set(ra, consumes=["C-RG", "C-SPATIAL", "C-MATIF", "C-FRAME", "C-FLOW", "C-VIEW", "C-GPUTIER", "C-ECS?",
                               "C-XRVIEW?", "C-INSTANCES?", "C-A11Y"],
                 non_responsibilities=[["API backends", "gpu-platform-architect"],
                                       ["Pass scheduling", "render-graph-scheduling"],
                                       ["Individual features (GI, shadows…)", "owning-skill"]],
                 tags="K-LEGACY-4 K-ARCH-20 K-ARCH-11")

    # --- geometry pipeline (formerly gpu-driven-pipeline): both submission paths first-class
    gp = "geometry-pipeline"
    ed.skill_set(gp, name="Geometry Submission Pipeline", profiles=["lite3d", "std3d"],
                 purpose="Instance scene and geometry submission for every 3D tier: persistent instance data with "
                         "batched delta updates, the CPU-culled batched/instanced path (first-class on TBDR/mobile and "
                         "lite3d), and the GPU-driven path (GPU culling, indirect/mesh shaders, visibility buffer) for "
                         "desktop/console tiers.",
                 consumes=["C-RSCENE", "C-RG", "C-SHADER", "C-GPUMEM", "C-GPUTIER", "C-GEOLOD?", "C-TEMPORAL?"],
                 tags="K-LEGACY-7 K-PERF-3")
    ed.contract_add("C-INSTANCES", 3, gp, "Instance scene",
                    "Persistent instance/primitive handles, batched add/remove/update with delta upload (cost "
                    "O(changes)), instance data layout shared with the ray-tracing instance builder; served by both "
                    "CPU and GPU submission paths.", ["C-RG", "C-GPUMEM"], tags="K-PERF-3 K-ARCH-2")
    ed.cap_move("RND.GEO.fallback", "RND.GEO.cpu-submission", tags="K-LEGACY-7")
    ed.cap_set("RND.GEO.cpu-submission", name="CPU-culled batched/instanced submission as a first-class tier path "
               "(own budgets and tests)", add_contrib=["platform-mobile"], tags="K-LEGACY-7")
    for cid in ("RND.GEO.culling", "RND.GEO.mesh-shaders", "RND.GEO.visbuffer"):
        ed.cap_set(cid, profiles=["std3d"], tags="K-LEGACY-7")
    ed.cap_set("RND.GEO.visbuffer", name="Visibility-buffer rasterization (TBDR suitability ADR required)",
               tags="K-LEGACY-7")
    ed.cap_set("RND.GEO.indirect", name="Indirect draws & dispatch (primitives provided by RND.RHI.gpu-work)",
               tags="K-FUTURE-8")
    ed.cap("RND.GEO.mesh-nodes", "Work-graph mesh-node geometry pipeline", gp, mat="X", profiles=["aaa"],
           tags="K-FUTURE-8")
    ed.cap("RND.GEO.dynamic-mesh", "Runtime-editable dynamic mesh representation & GPU upload", gp,
           contrib=["procedural-generation", "voxel-worlds"], tags="K-COMPLETE-8")
    ed.cap("RND.GEO.splats", "Gaussian-splat / radiance-field rendering, sorting, LOD & compositing", gp, mat="X",
           contrib=["ray-tracing-infrastructure", "asset-import-interchange"],
           tags="K-RENDER-15 K-FUTURE-9 K-COMPLETE-20")
    ed.cap("RND.GEO.splat-relight", "Relightable/dynamic splats & hybrid raster/RT composition", gp, mat="X",
           tags="K-FUTURE-9")

    # --- LOD, textures, lighting, GI, RT, PT
    vg = "virtualized-geometry-lod"
    ed.contract_add("C-GEOLOD", 3, vg, "Geometry LOD & page residency",
                    "Cluster/LOD selection and page residency for raster, shadow and ray-tracing consumers.",
                    ["C-RG"], tags="K-ARCH-2")
    for cid in ("RND.LOD.clusters", "RND.LOD.swraster", "RND.LOD.streaming", "RND.LOD.cluster-build"):
        ed.cap_set(cid, profiles=["std3d"], tags="K-LEGACY-7")
    ed.skill_set(vg, consumes=["C-RSCENE", "C-RG", "C-RES", "C-RT?", "C-INSTANCES"], tags="K-ARCH-2")
    tx = "texture-streaming-vt"
    ed.contract_add("C-VT", 3, tx, "Texture residency & virtual texturing",
                    "Texture residency requests, VT page tables/feedback and allocation for terrain, materials and "
                    "runtime-composited textures.", ["C-RG", "C-GPUMEM"], tags="K-ARCH-2")
    ed.skill_set(tx, profiles=["all"], consumes=["C-RES", "C-GPUMEM", "C-RG", "C-ML?", "C-MLGPU?"],
                 tags="K-RENDER-7")
    for cid in ("RND.TEX.feedback", "RND.TEX.vt"):
        ed.cap_set(cid, profiles=["std3d"], tags="K-RENDER-7")
    ed.cap_set("RND.TEX.ntc", mat="X", profiles=["aaa"], tags="K-RENDER-19 K-FUTURE-15")
    dl = "direct-lighting-shadows"
    ed.contract_add("C-LIGHT", 3, dl, "Direct lighting sampling",
                    "Light lists (clustered or stochastic), shadow lookups, light units, many-light sampling API for "
                    "any shading point incl. translucency, volumes and particles.", ["C-RSCENE"], tags="K-RENDER-1 K-ARCH-2")
    ed.cap("RND.LIGHT.channels", "Light linking / light channels", dl, tags="K-RENDER-12")
    for cid in ("RND.LIGHT.vsm", "RND.LIGHT.rt-shadows", "RND.LIGHT.stochastic"):
        ed.cap_set(cid, profiles=["std3d"], tags="K-RENDER-3")
    gi = "global-illumination"
    ed.contract_add("C-GI", 3, gi, "Indirect lighting sampling",
                    "Indirect diffuse/specular sampling for any shading point (incl. translucent and volumetric), "
                    "probes, sky/environment lighting.", ["C-RSCENE"], tags="K-RENDER-1 K-ARCH-2")
    ed.cap_move("RND.GI.sdf", "RND.RT.sdf-scene", tags="K-RENDER-4")
    ed.cap_set("RND.RT.sdf-scene", name="SDF/voxel tracing scene (software ray-query backend)",
               owner="ray-tracing-infrastructure", rm_contrib=["ray-tracing-infrastructure"], add_contrib=["global-illumination"],
               tags="K-RENDER-4")
    ed.cap("RND.GI.bake-pipeline", "Incremental/distributed lighting bake orchestration", gi,
           contrib=["content-pipeline-architect"], tags="K-RENDER-12")
    ed.cap("RND.GI.lightmap-uv", "Lightmap UV generation & atlas packing", gi, contrib=["asset-cook-processors"],
           tags="K-RENDER-12")
    ed.cap("RND.GI.neural-cache", "Neural radiance caching with online training", gi, mat="M",
           contrib=["ml-inference-runtime", "path-tracing"], profiles=["aaa"], tags="K-FUTURE-16 K-RENDER-15")
    for cid in ("RND.GI.hybrid", "RND.GI.restir"):
        ed.cap_set(cid, profiles=["std3d"], tags="K-RENDER-3")
    ed.skill_set(gi, consumes=["C-RSCENE", "C-RG", "C-RT?", "C-TEMPORAL", "C-LIGHT", "C-ATMOS?", "C-MLGPU?"],
                 tool_consumes=["C-COOK", "C-EDCMD", "C-EDHOST"], tags="K-RENDER-1 K-RENDER-12")
    ed.skill_set(dl, consumes=["C-RSCENE", "C-RG", "C-RT?", "C-TEMPORAL", "C-INSTANCES?", "C-GEOLOD?"],
                 tags="K-ARCH-2")
    rt = "ray-tracing-infrastructure"
    ed.skill_set(rt, profiles=["lite3d", "std3d"], consumes=["C-RSCENE", "C-RG", "C-GPUMEM", "C-INSTANCES", "C-GPUTIER"],
                 tags="K-RENDER-3 K-FUTURE-6 K-ARCH-14")
    ed.contract_set("C-RT", name="Ray queries", tags="K-RENDER-4",
                    summary="Ray-query contract with hardware and software (SDF/BVH compute) backends: acceleration "
                            "structures, instance data, hit/material binding, update policy.")
    ed.cap_set("RND.RT.software", name="Software ray-query backend (compute BVH/SDF traversal)", tags="K-RENDER-4")
    for cid in ("RND.RT.cluster-blas", "RND.RT.ser", "RND.RT.omm"):
        ed.cap_set(cid, profiles=["aaa"], tags="K-RENDER-3")
    pt = "path-tracing"
    ed.skill_set(pt, profiles=["lite3d", "std3d"], consumes=["C-RT?", "C-MATIF", "C-RSCENE", "C-LIGHT", "C-GI?"],
                 tags="K-RENDER-5 K-FUTURE-6")
    ed.cap_set("RND.PT.reference", name="Reference path tracer as ground-truth oracle (dev-only; compute fallback "
               "without HW RT)", tags="K-RENDER-5")
    ed.cap_set("RND.PT.realtime", profiles=["aaa"], tags="K-RENDER-5")

    # --- reconstruction, post, translucency, character, 2D, VFX, material
    rc = "reconstruction-upscaling"
    ed.skill_set(rc, profiles=["all"], consumes=["C-RG", "C-FRAME", "C-PRESENT", "C-MLGPU?"], tags="K-RENDER-9 K-ARCH-10")
    ed.contract_set("C-TEMPORAL", tags="K-RENDER-2",
                    summary="Motion vectors, jitter, history validity, reactive/transparency masks, resolution scaling; "
                            "motion-vector obligations for every moving/animated surface; UI/HUD separation for frame "
                            "generation; depth+motion submission for XR spacewarp.")
    ed.cap("RND.RECON.msaa", "MSAA incl. on-tile resolve & alpha-to-coverage", rc, tags="K-RENDER-9")
    ed.cap("RND.RECON.post-aa", "Post-process AA (SMAA/FXAA class)", rc, tags="K-RENDER-9")
    ed.cap("RND.RECON.specular-aa", "Specular/geometric anti-aliasing", rc, tags="K-RENDER-9")
    ed.cap("RND.RECON.foveation", "Foveated rendering implementation (VRS, fragment density maps, multi-res)", rc,
           mat="M", contrib=["xr-runtime"], tags="K-RENDER-11")
    ed.cap_del("PLAT.XR.foveation", tags="K-RENDER-11 (implementation moved to RND.RECON.foveation)")
    ed.cap_set("RND.RECON.framegen", mat="E", add_contrib=["frame-orchestration"], tags="K-FUTURE-15 K-ARCH-10")
    pc = "post-color-hdr"
    ed.cap_set("RND.POST.color", name="Color management pipeline (working space, display transforms, OCIO)",
               tags="K-RENDER-19")
    ed.cap("RND.POST.aces2", "ACES 2.0 output transforms", pc, mat="M", tags="K-RENDER-19")
    ed.cap_move("UI.A11Y.vision", "RND.POST.colorblind", tags="K-ARCH-8")
    ed.cap_set("RND.POST.colorblind", name="Colorblind & contrast modes (tonemap-stage passes)", owner=pc,
               rm_contrib=[pc], add_contrib=["accessibility"], tags="K-ARCH-8")
    ed.cap("RND.POST.stylized", "Outline, edge & stylized post effects", pc, tags="K-COMPLETE-19")
    ed.cap_set("RND.POST.hdr-output", name="HDR output (PQ, scRGB, metadata; platform calibration from C-PAL)",
               tags="K-PLATFORM-13")
    ed.use(pc, "C-A11Y", "C-PAL", tags="K-GAMEPLAY-6")
    ed.skill_set("translucency-decals", consumes=["C-RSCENE", "C-RG", "C-MATIF", "C-LIGHT", "C-GI?", "C-ATMOS?", "C-TEMPORAL"],
                 tags="K-RENDER-1 K-RENDER-2")
    cr = "character-rendering"
    ed.skill_set(cr, profiles=["lite3d", "std3d"], consumes=["C-RSCENE", "C-MATIF", "C-ANIM", "C-RG", "C-LIGHT", "C-GI?"],
                 tags="K-RENDER-8")
    ed.cap("RND.CHAR.hair-cards", "Hair cards (alpha-to-coverage/dithered, Marschner-class shading)", cr, tags="K-RENDER-8")
    ed.cap_set("RND.CHAR.hair", name="Strand hair & fur", profiles=["aaa"], tags="K-RENDER-8")
    ed.cap_set("RND.CHAR.skin", name="Skin subsurface scattering (pre-integrated → screen-space → ray/path-traced)",
               tags="K-RENDER-8")
    r2 = "render-2d-vector"
    ed.skill_set(r2, consumes=["C-RG", "C-SHADER", "C-TEXT", "C-TEMPORAL?", "C-A11Y"], tags="K-RENDER-2")
    ed.cap("RND.2D.atlas-cook", "Sprite atlas packing cook step", r2, contrib=["asset-cook-processors"],
           tags="K-TOOLS-11 K-GAMEPLAY-12")
    vfx = "vfx-particles"
    ed.cap("RND.VFX.volumes", "Sparse/heterogeneous volume rendering & lighting (NanoVDB class)", vfx, mat="M",
           contrib=["atmosphere-weather", "fluid-simulation"], tags="K-RENDER-17")
    ed.skill_set(vfx, consumes=["C-RSCENE", "C-RG", "C-PHYS?", "C-LIGHT?", "C-GI?", "C-ATMOS?", "C-TEMPORAL?", "C-ENV?",
                                "C-A11Y"], tool_consumes=["C-GRAPH", "C-EDCMD", "C-EDHOST"],
                 tags="K-RENDER-1 K-RENDER-2 K-SIM-13")
    at = "atmosphere-weather"
    ed.contract_add("C-ATMOS", 3, at, "Atmosphere & participating media",
                    "Aerial perspective, froxel/local media volumes, cloud shadows, weather-driven global material "
                    "parameters.", ["C-RSCENE"], tags="K-RENDER-1")
    mt = "material-system"
    ed.cap_set("RND.MAT.model", name="Layered PBR material model", tags="K-RENDER-19")
    ed.cap("RND.MAT.openpbr", "OpenPBR-class layered model adoption", mt, mat="M", tags="K-RENDER-19")
    ed.cap("RND.MAT.custom-lighting", "Custom/stylized lighting models across shading paths", mt,
           contrib=["render-architect"], tags="K-COMPLETE-19")
    ed.use(mt, "C-MLGPU?", "C-GPUTIER", tags="K-FUTURE-1")

    # --- video playback
    ed.skill_add(id="media-playback", name="Media & Video Playback", tier="expert", parent=ra, profiles=["all"],
                 kind="runtime", targets=CLIENT_TOOLS, workstream="rendering",
                 purpose="Pre-rendered video playback end to end: hardware/software decode backends, A/V sync against "
                         "the audio clock, video surfaces for UI, world and cinematics, HDR video, package streaming.",
                 non_responsibilities=[["Movie rendering (producing video)", "cinematics-sequencer"],
                                       ["Audio mixing", "audio-dsp-mixing"]],
                 consumes=["C-IO", "C-RES", "C-GPUMEM", "C-AUDIO", "C-FRAME", "C-RG"],
                 expertise=["video codecs (AV1/HEVC/H.264)", "hardware decoders", "A/V sync"],
                 tags="K-ARCH-15 K-COMPLETE-2")
    ed.contract_add("C-VIDEO", 3, "media-playback", "Video surfaces",
                    "Video playback sessions, surfaces as textures, timing against the audio clock.", ["C-RG"],
                    tags="K-ARCH-15")
    ed.area("RND.MEDIA", "Media playback", tags="K-ARCH-15")
    ed.cap("RND.MEDIA.decode", "Hardware & software video decode backends", "media-playback", tags="K-ARCH-15")
    ed.cap("RND.MEDIA.sync", "A/V sync against the audio clock", "media-playback", contrib=["audio-architect"],
           tags="K-ARCH-15")
    ed.cap("RND.MEDIA.surfaces", "Video surfaces for UI, world & cinematics", "media-playback", tags="K-ARCH-15")
    ed.cap("RND.MEDIA.hdr", "HDR video", "media-playback", contrib=["post-color-hdr"], tags="K-COMPLETE-2")
    ed.cap("RND.MEDIA.middleware", "Video middleware decision (Bink class vs platform decoders)", "media-playback",
           contrib=["engine-architect"], tags="K-COMPLETE-2")

    # --- rendering tool logic (domain-owned, hosted via C-EDHOST)
    ed.area("RND.TOOL", "Rendering authoring tools", tags="K-TOOLS-1")
    ed.cap("RND.TOOL.material-editor", "Material editor tool logic: preview, parameters, instances, live update", mt,
           contrib=["graph-editor-framework", "editor-ui-framework"], tags="K-TOOLS-1")
    ed.cap("RND.TOOL.vfx-editor", "VFX editor tool logic: emitter stack, preview, timeline, bounds", vfx,
           contrib=["graph-editor-framework"], tags="K-TOOLS-1 K-COMPLETE-7")
    ed.cap("RND.TOOL.lighting", "Lighting authoring: probe/capture placement, lighting scenarios, density "
           "visualization", gi, contrib=["world-editor-viewport"], tags="K-RENDER-12")
    ed.cap("RND.TOOL.mesh-lod", "Mesh/LOD setup & preview", vg, tags="K-COMPLETE-7")
    ed.cap("RND.TOOL.tilemap-sprite", "Tilemap painting, auto-tiling rules, sprite slicing & editing", r2,
           contrib=["world-editor-viewport"], tags="K-TOOLS-11 K-GAMEPLAY-12 K-PROD-5")
    for s_ in (mt, vg, r2):
        ed.use(s_, "C-EDCMD", "C-EDHOST", tool=True, tags="K-TOOLS-1")
    ed.use(mt, "C-GRAPH", tool=True, tags="K-TOOLS-1")


def physics(ed):
    pa = "physics-architect"
    ed.contract_set("C-PHYS", requires=["C-SPATIAL", "C-FRAME", "C-ID"],
                    tags="K-ARCH-3 K-SYSTEMS-10 K-LEGACY-1 K-SIM-6 K-PERF-5 K-SIM-12",
                    summary="Bodies, shapes, queries (handle-addressed, batched), contact events with budgets, stepping "
                            "phases, batch add/remove O(batch), snapshot/restore/resimulate participation, collider "
                            "history for rewind.")
    ed.skill_set(pa, profiles=["min2d", "lite3d", "std3d"],
                 consumes=["C-SPATIAL", "C-FRAME", "C-DET", "C-TASK", "C-ECS?", "C-WORLD?", "C-RES", "C-SIGNIF?",
                           "C-SNAPSHOT", "C-ENV?", "C-RG?"],
                 tags="K-ARCH-3 K-SIM-8 K-SIM-4 K-SIM-19 K-GAMEPLAY-14")
    for cid, name, contrib, t in [
            ("PHY.ARCH.rewind", "State snapshot/restore, partial resimulation, state hashing & collider history",
             ["rigid-body-dynamics", "prediction-rollback", "determinism-replay"], "K-SIM-6 K-NET-3"),
            ("PHY.ARCH.async", "Decoupled/async physics stepping with input marshalling & interpolation", [], "K-SIM-7"),
            ("PHY.ARCH.streaming", "Physics world streaming: per-cell activation, bulk/async insertion, "
             "collision-before-render", ["collision-detection", "world-architect"], "K-SIM-8"),
            ("PHY.ARCH.lwc", "Physics precision under large-world coordinates", ["spatial-transforms"], "K-SIM-8"),
            ("PHY.ARCH.middleware-layer", "Middleware/fork integration layer & upstream patch ownership", [], "K-SIM-11"),
            ("PHY.ARCH.events", "Contact/impact/slide event generation, filtering & budgets", [], "K-SIM-12"),
            ("PHY.ARCH.validation", "Physics oracle suite: analytic & reference scenes", ["test-architect"], "K-QUALITY-5")]:
        ed.cap(cid, name, pa, contrib=contrib, tags=t)
    ed.cap_set("PHY.ARCH.build-integrate", name="Physics engine build vs integrate decision (evidence: benchmark scenes, "
               "determinism, rewind, GPU path, license)", tags="K-SIM-11")
    cd = "collision-detection"
    ed.cap_move("PHY.COL.complex", "PHY.COL.mesh-heightfield", tags="K-SIM-17")
    ed.cap_set("PHY.COL.mesh-heightfield", name="Mesh & heightfield collision", tags="K-SIM-17")
    ed.cap("PHY.COL.sdf", "SDF collision", cd, mat="M", tags="K-SIM-17")
    ed.cap("PHY.COL.decomposition", "Convex decomposition & simple-collision generation", cd, tags="K-TOOLS-4")
    ed.skill_set(cd, profiles=["lite3d", "std3d"], consumes=["C-PHYS", "C-MATH", "C-DET", "C-ENV?"],
                 tool_consumes=["C-COOK"], tags="K-SIM-15")
    rb = "rigid-body-dynamics"
    ed.cap("PHY.DYN.dof-lock", "Planar / DOF-locked simulation (2.5D)", rb, tags="K-SIM-18")
    ed.cap("PHY.DYN.articulations", "Reduced-coordinate articulations", rb, tags="K-SIM-19")
    ed.cap_move("PHY.CTRL.buoyancy", "PHY.DYN.buoyancy", tags="K-SIM-9")
    ed.cap_set("PHY.DYN.buoyancy", owner=rb, add_contrib=["water-ocean"], tags="K-SIM-9")
    ed.skill_set(rb, profiles=["lite3d", "std3d"], consumes=["C-PHYS", "C-TASK", "C-DET", "C-ANIM?", "C-ENV?"],
                 tags="K-PERF-16 K-SIM-7")
    cp = "character-physics"
    ed.skill_set(cp, name="Character Physics", profiles=["lite3d", "std3d"],
                 purpose="Character controllers (kinematic and dynamic), moving platforms and physical interaction.",
                 consumes=["C-PHYS", "C-DET", "C-ENV?"],
                 non_responsibilities=[["Movement modes & networked movement", "character-movement"],
                                       ["Vehicles", "vehicle-physics"]], tags="K-SIM-10 K-SIM-2 K-SIM-15")
    ed.skill_add(id="vehicle-physics", name="Vehicle Physics", tier="expert", parent=pa, profiles=["vehicles"],
                 kind="runtime", targets=ALL_T, workstream="simulation",
                 purpose="Vehicle dynamics: wheeled vehicles (tires, suspension, drivetrain), aerodynamic surfaces and "
                         "flight models, orbital mechanics, watercraft hydrodynamics, vehicle-specific prediction and "
                         "force-feedback sources.",
                 non_responsibilities=[["Character controllers", "character-physics"],
                                       ["Generic buoyancy", "rigid-body-dynamics"],
                                       ["Netcode model", "prediction-rollback"]],
                 consumes=["C-PHYS", "C-DET", "C-ENV?", "C-DEVICE?", "C-PREDICT?"],
                 expertise=["tire models (Pacejka, brush)", "flight dynamics", "orbital mechanics"],
                 tags="K-SIM-10 K-COMPLETE-14 K-COMPLETE-17")
    ed.cap_set("PHY.CTRL.vehicles", owner="vehicle-physics", tags="K-SIM-10")
    ed.cap("PHY.CTRL.vehicle-net", "Vehicle prediction & replication specifics", "vehicle-physics",
           contrib=["prediction-rollback"], tags="K-SIM-10")
    ed.cap("PHY.CTRL.aero", "Aerodynamic surfaces & flight models", "vehicle-physics", tags="K-COMPLETE-14")
    ed.cap("PHY.CTRL.orbital", "Orbital/n-body mechanics with double-precision integration", "vehicle-physics",
           contrib=["math-simd-numerics"], tags="K-COMPLETE-14")
    ed.cap("PHY.CTRL.watercraft", "Watercraft hydrodynamics beyond buoyancy", "vehicle-physics",
           contrib=["water-ocean"], tags="K-COMPLETE-14")
    ed.skill_set("cloth-deformables", profiles=["lite3d", "std3d"], consumes=["C-PHYS", "C-ANIM", "C-RG?", "C-ENV?", "C-DET?", "C-ML?"],
                 tags="K-SIM-18 K-SIM-13 K-FUTURE-1")
    ed.skill_set("destruction-fracture", profiles=["std3d"],
                 consumes=["C-PHYS", "C-RSCENE?", "C-REP?", "C-NAV?", "C-AUDIO?", "C-INSTANCES?"],
                 tool_consumes=["C-COOK", "C-EDCMD", "C-EDHOST"], tags="K-SIM-16 K-SIM-1")
    for cid in ("PHY.DEST.runtime",):
        ed.cap_set(cid, name="Runtime fracture & debris management (large-scale runtime fracture per ADR)", tags="K-SIM-16")
    ed.skill_set("fluid-simulation", consumes=["C-PHYS", "C-RG?", "C-RSCENE?", "C-ENV?"], tags="K-SIM-1")
    ed.cap_set("PHY.FLUID.particles", mat="M", tags="K-SIM-17")
    ed.cap_set("PHY.FLUID.gpu", mat="M", tags="K-SIM-17")
    p2 = "physics-2d"
    ed.cap("PHY.2D.shape-gen", "2D collision-shape generation from sprites", p2, tags="K-GAMEPLAY-12")
    # physics tools
    ed.skill_add(id="physics-tools", name="Physics Tools", tier="expert", parent=pa, profiles=["min2d", "lite3d", "std3d"],
                 kind="tool", targets=["tools"], workstream="simulation",
                 purpose="Physics authoring and debugging tools: collision authoring, physics-asset/ragdoll and "
                         "constraint editors, the physics visual debugger/recorder, simulate-in-editor, vehicle and "
                         "controller tuning, 2D collision-shape editing.",
                 non_responsibilities=[["Collision algorithms", "collision-detection"],
                                       ["Editor host & transactions", "editor-architect"]],
                 consumes=["C-EDCMD", "C-EDHOST", "C-PHYS", "C-INSTR", "C-REPLAY?"],
                 expertise=["physics debugging", "tool UX", "ragdoll setup"], tags="K-SIM-3 K-TOOLS-4 K-COMPLETE-7")
    ed.area("PHY.TOOL", "Physics authoring tools", tags="K-SIM-3")
    for cid, name, contrib in [
            ("PHY.TOOL.collision-authoring", "Collision authoring (primitive fitting, convex decomposition UI)", ["collision-detection"]),
            ("PHY.TOOL.physics-asset", "Physics-asset / ragdoll body & constraint editor", ["ik-procedural-animation", "rigid-body-dynamics"]),
            ("PHY.TOOL.visual-debugger", "Physics visual debugger & recorder", ["visual-debugging-tools", "determinism-replay"]),
            ("PHY.TOOL.simulate-in-editor", "Simulate-in-editor & simulation-driven placement", ["editor-architect"]),
            ("PHY.TOOL.tuning", "Vehicle & controller tuning tools", ["vehicle-physics", "character-physics"]),
            ("PHY.TOOL.2d-shapes", "2D collision-shape editing", ["physics-2d"])]:
        ed.cap(cid, name, "physics-tools", contrib=contrib, tags="K-SIM-3 K-TOOLS-4 K-TOOLS-11")
    ed.cap_move("PHY.DEST.authoring", "PHY.TOOL.fracture", tags="K-TOOLS-1")


def animation(ed):
    aa = "animation-architect"
    ed.contract_set("C-ANIM", requires=["C-SPATIAL", "C-ID"], tags="K-ARCH-3 K-GAMEPLAY-8",
                    summary="Pose output and control input (parameters, action/montage requests, instance lifetime), "
                            "root motion, animation events, pose history for rewind, network-sync hooks, "
                            "physics/render hand-off.")
    ed.skill_set(aa, profiles=["min2d", "lite3d", "std3d"],
                 consumes=["C-SPATIAL", "C-FRAME", "C-TASK", "C-ECS?", "C-PHYS?", "C-NET?", "C-REP?", "C-SNAPSHOT",
                           "C-SIGNIF?"], tags="K-GAMEPLAY-8 K-SIM-4")
    ed.cap("ANM.ARCH.net", "Animation replication, prediction & server evaluation policy", aa,
           contrib=["replication", "prediction-rollback"], tags="K-GAMEPLAY-8 K-NET-5")
    ed.cap("ANM.ARCH.validation", "Animation oracle suite: pose/compression/retarget error metrics", aa,
           contrib=["test-architect"], tags="K-QUALITY-5")
    ed.cap_set("ANM.ARCH.sync", name="Animation-side obligations within the canonical simulation schedule; root-motion "
               "policy", add_contrib=["physics-architect", "frame-orchestration"], tags="K-SIM-7 K-PERF-16")
    ar = "animation-runtime"
    ed.cap("ANM.RT.pose-history", "Pose history buffer for rewind/lag compensation", ar,
           contrib=["prediction-rollback"], tags="K-GAMEPLAY-8")
    ed.cap("ANM.RT.2d-import", "2D skeletal import (Spine class) incl. IK & mesh constraints", ar,
           tags="K-GAMEPLAY-12")
    ed.skill_set(ar, profiles=["min2d", "lite3d", "std3d"], tags="K-GAMEPLAY-14")
    ds = "deformation-skinning"
    ed.cap("ANM.DEF.crowd", "Instanced crowd deformation: VAT, animation textures, animated impostors", ds,
           contrib=["crowd-simulation", "virtualized-geometry-lod"], tags="K-RENDER-18 K-COMPLETE-28 K-SIM-5")
    ed.cap("ANM.DEF.geometry-cache", "Geometry/point cache playback", ds, contrib=["asset-import-interchange"],
           tags="K-TOOLS-18")
    ed.use(ds, "C-ML?", "C-INSTANCES?", tags="K-FUTURE-1")
    ed.skill_set("animation-graphs", profiles=["min2d", "lite3d", "std3d"], tags="K-GAMEPLAY-14")
    ed.skill_set("motion-synthesis", profiles=["std3d"], tags="K-GAMEPLAY-13")
    ed.skill_set("ik-procedural-animation", profiles=["lite3d", "std3d"], tags="K-GAMEPLAY-13 K-SIM-18")
    ed.cap("ANM.IK.2d", "2D IK constraints", "ik-procedural-animation", tags="K-GAMEPLAY-12")
    ed.skill_set("ik-procedural-animation", profiles=["min2d", "lite3d", "std3d"], tags="K-GAMEPLAY-12")
    ed.skill_set("facial-animation", profiles=["lite3d", "std3d"],
                 consumes=["C-ANIM", "C-AUDIO?", "C-ML?", "C-DIALOGUE?"], tags="K-GAMEPLAY-13 K-GAMEPLAY-1")
    cs = "cinematics-sequencer"
    ed.skill_set(cs, profiles=["all"], targets=ALL_T,
                 consumes=["C-ANIM", "C-AUDIO?", "C-RSCENE?", "C-RES", "C-VIEW", "C-GAME?", "C-UI?", "C-LOC?", "C-REP?",
                           "C-VIDEO?", "C-DIALOGUE?", "C-A11Y"],
                 tool_consumes=["C-EDCMD", "C-EDHOST"], tags="K-GAMEPLAY-16 K-ARCH-11")
    ed.cap_set("ANM.CINE.sequencer", name="Timeline/sequencer (cinematic, gameplay & UI tracks)", tags="K-GAMEPLAY-16")
    ed.cap("ANM.CINE.gameplay-takeover", "Gameplay takeover, input blocking, skippable & blended cutscenes", cs,
           contrib=["gameplay-architect"], tags="K-GAMEPLAY-16")
    ed.cap("ANM.CINE.net-sync", "Synchronized & server-authoritative sequences", cs, contrib=["replication"],
           tags="K-GAMEPLAY-16")
    ed.area("ANM.TOOL", "Animation authoring tools", tags="K-TOOLS-4")
    for cid, name, owner, contrib, mat in [
            ("ANM.TOOL.asset-editor", "Skeleton, skeletal-mesh & clip editor (sockets, notifies, curves, montages, "
             "compression preview)", ar, [], "E"),
            ("ANM.TOOL.retarget-editor", "Retargeting rig & chain authoring", ar, [], "E"),
            ("ANM.TOOL.2d-rigging", "2D skeletal rigging & flipbook editing", ar, ["render-2d-vector"], "E"),
            ("ANM.TOOL.graph-editor", "Animation graph & blend-space editing and debugging", "animation-graphs",
             ["graph-editor-framework"], "E"),
            ("ANM.TOOL.rigging", "In-engine control rig & keyframe authoring", "ik-procedural-animation", [], "E"),
            ("ANM.TOOL.pose-db", "Pose-database / motion-matching inspector", "motion-synthesis",
             ["visual-debugging-tools"], "E"),
            ("ANM.TOOL.facial", "Facial rig & pose tools", "facial-animation", [], "E")]:
        ed.cap(cid, name, owner, mat=mat, contrib=contrib, tags="K-TOOLS-4 K-GAMEPLAY-9 K-COMPLETE-7")
    for s_ in (ar, "animation-graphs", "ik-procedural-animation", "motion-synthesis", "facial-animation"):
        ed.use(s_, "C-EDCMD", "C-EDHOST", tool=True, tags="K-TOOLS-1")
    ed.use("animation-graphs", "C-GRAPH", tool=True, tags="K-TOOLS-1")


def audio(ed):
    au = "audio-architect"
    ed.contract_set("C-AUDIO", requires=["C-SPATIAL", "C-ID"], tags="K-ARCH-3 K-GAMEPLAY-4 K-COMPLETE-18",
                    summary="Emitter/listener data (multiple listeners), event triggering, parameters, busses, the "
                            "sample-accurate audio clock exposed to gameplay.")
    ed.skill_set(au, consumes=["C-PAL", "C-TASK", "C-SPATIAL", "C-VIEW", "C-ECS?", "C-SIGNIF?"],
                 tags="K-ARCH-3 K-GAMEPLAY-4")
    for cid, name, contrib, t in [
            ("AUD.ARCH.listeners", "Multiple listeners & split-screen mixing", ["gameplay-architect"], "K-GAMEPLAY-4"),
            ("AUD.ARCH.clock", "Audio clock, output-latency measurement & A/V/input sync contract",
             ["frame-orchestration", "input-system"], "K-COMPLETE-18"),
            ("AUD.ARCH.validation", "Audio oracle suite: bit-exact offline render, loudness, glitch & latency",
             ["test-architect"], "K-QUALITY-5"),
            ("AUD.ARCH.offline-render", "Offline faster-than-real-time render & null audio device", [], "K-QUALITY-10")]:
        ed.cap(cid, name, au, contrib=contrib, tags=t)
    ed.cap_set("AUD.SPAT.panning", owner="audio-dsp-mixing", tags="K-GAMEPLAY-13")
    ed.cap_move("AUD.SPAT.panning", "AUD.DSP.panning", tags="K-GAMEPLAY-13")
    ed.skill_set("audio-dsp-mixing", consumes=["C-AUDIO", "C-RES", "C-MATH", "C-NETLINK?"], tags="K-NET-10")
    ed.skill_set("spatial-audio-acoustics", profiles=["lite3d", "std3d", "xr"],
                 consumes=["C-AUDIO", "C-PHYS?", "C-RT?", "C-ENV?"], tags="K-GAMEPLAY-13")
    ac = "audio-content-runtime"
    ed.cap_set("AUD.CONTENT.dialogue", name="VO playback & ducking for C-DIALOGUE lines", add_contrib=["narrative-dialogue"],
               tags="K-GAMEPLAY-1")
    ed.cap("AUD.CONTENT.licensed-music", "Licensed-music flags & streamer-safe playback", ac,
           contrib=["content-pipeline-architect"], tags="K-PROD-12 K-COMPLETE-13")
    ed.cap("AUD.CONTENT.speech", "Runtime neural TTS/ASR for gameplay dialogue", ac, mat="M",
           contrib=["ml-inference-runtime"], tags="K-FUTURE-5")
    ed.area("AUD.TOOL", "Audio authoring tools", tags="K-GAMEPLAY-9")
    ed.cap("AUD.TOOL.designer", "In-engine sound design & live mixing tool (own-audio path)", ac,
           contrib=["graph-editor-framework"], tags="K-GAMEPLAY-9")
    ed.skill_set(ac, consumes=["C-AUDIO", "C-ASSET", "C-LOC", "C-DIALOGUE?", "C-DEVICE?", "C-ML?", "C-A11Y"],
                 tool_consumes=["C-GRAPH", "C-EDCMD", "C-EDHOST"], tags="K-GAMEPLAY-2 K-GAMEPLAY-1 K-FUTURE-5")


def input_(ed):
    idv = "input-devices-haptics"
    ed.contract_add("C-DEVICE", 2, idv, "Input devices & haptics",
                    "Device enumeration, raw state and events with timestamps, device↔platform-user pairing, haptic, "
                    "trigger-effect and LED output, virtual device injection for automation.", ["C-PAL"],
                    tags="K-ARCH-12 K-GAMEPLAY-2 K-QUALITY-10")
    ed.skill_set(idv, consumes=["C-PAL"], tags="K-ARCH-12")
    for cid, name, contrib, t in [
            ("INP.DEV.haptic-assets", "Authored haptic & trigger-effect assets & playback", ["audio-content-runtime"], "K-GAMEPLAY-2"),
            ("INP.DEV.force-feedback", "Force-feedback devices (wheels, sticks) & effect model", ["vehicle-physics"], "K-COMPLETE-17"),
            ("INP.DEV.specialty", "Specialty/high-rate controllers (HOTAS, arcade, pedals, SOCD policy)", [], "K-COMPLETE-17"),
            ("INP.DEV.eye-tracking", "Eye tracking as an input device (desktop/laptop)", ["accessibility"], "K-FUTURE-19"),
            ("INP.DEV.injection", "Virtual input device injection for bots & tests", ["functional-automation-soak"], "K-QUALITY-10")]:
        ed.cap(cid, name, idv, contrib=contrib, tags=t)
    ed.cap_set("INP.DEV.hotplug", name="Hotplug & device↔platform-user pairing", tags="K-GAMEPLAY-17")
    isy = "input-system"
    ed.contract_set("C-INPUT", requires=["C-FRAME"], tags="K-NET-4 K-GAMEPLAY-3",
                    summary="Action definitions and values, tick-stamped input-command frames and their serialization "
                            "(all targets incl. server); device binding contexts are client-side.")
    ed.skill_set(isy, profiles=["all"], targets=ALL_T, consumes=["C-DEVICE?", "C-FRAME", "C-SER", "C-A11Y"],
                 tags="K-NET-4 K-GAMEPLAY-3 K-ARCH-12")
    ed.cap("INP.ACT.confirm-swap", "Regional confirm/cancel button conventions", isy, tags="K-GAMEPLAY-18")
    ed.cap("INP.ACT.calibration", "User latency calibration flow (A/V/input)", isy, contrib=["audio-architect"],
           tags="K-COMPLETE-18")
    ed.cap_set("INP.ACT.local-mp", name="Local-player ↔ device assignment", tags="K-GAMEPLAY-17")
    ed.cap_set("PLAT.CON.user-model", name="Console platform-user identity model", tags="K-GAMEPLAY-17")


def apply(ed):
    renames(ed)
    rendering(ed)
    physics(ed)
    animation(ed)
    audio(ed)
    input_(ed)
