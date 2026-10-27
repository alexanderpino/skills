"""Round-2 revision, part C: K-RENDER and K-SIM findings (render-feature contracts, RT split, water/fluids, simulation)."""


def _append(ed, cid, text, tags):
    c = ed.contract(cid)
    ed.contract_set(cid, summary=c["summary"].rstrip(".") + "; " + text, tags=tags)


def _addexp(ed, sid, items, tags):
    s = ed.skill(sid)
    ed.skill_set(sid, expertise=s["expertise"] + [x for x in items if x not in s["expertise"]], tags=tags)


def apply(ed):
    # ================================================================ RENDER
    t = "K-RENDER-1"
    ed.contract_add("C-SCENETEX", 3, "render-architect", "Per-view scene textures",
                    "Named per-view render-graph resources and their producer phases: depth, HZB, visibility IDs, "
                    "surface-attribute decode (visibility buffer and deferred), velocity, scene color, denoiser/upscaler "
                    "guide buffers; variants per shading path and tier.",
                    requires=["C-RG", "C-MATIF"], conformance=True, tags=t)
    ed.cap("RND.ARCH.scene-textures", "Per-view scene-texture layout & producer phases per shading path (C-SCENETEX)",
           "render-architect", contrib=["geometry-pipeline", "reconstruction-upscaling"], tags=t)
    for sid in ("geometry-pipeline", "direct-lighting-shadows", "global-illumination", "reconstruction-upscaling",
                "translucency-decals", "vfx-particles", "character-rendering", "post-color-hdr"):
        ed.use(sid, "C-SCENETEX", tags=t)
    ed.use("water-ocean", "C-SCENETEX?", tags=t)
    ed.use("render-validation", "C-SCENETEX", tags=t)

    t = "K-RENDER-2"   # seed S01; residual: post consumes temporal data
    ed.use("post-color-hdr", "C-TEMPORAL", tags=t)

    t = "K-RENDER-4"
    ed.contract_add("C-COLOR", 3, "post-color-hdr", "Color, exposure & display state",
                    "Working color space, per-view exposure and pre-exposure with its frame latency, output display "
                    "descriptor (SDR/HDR, transfer function, paper white, peak luminance, calibration), UI/video "
                    "composition rules.", requires=["C-RG", "C-PAL"], conformance=True, tags=t)
    ed.cap("RND.POST.display-state", "Exposure/pre-exposure & display-state publication (C-COLOR)", "post-color-hdr",
           contrib=["render-2d-vector", "media-playback", "xr-runtime"], tags=t)
    for sid in ("render-2d-vector", "vfx-particles", "direct-lighting-shadows", "global-illumination",
                "translucency-decals", "ui-architect"):
        ed.use(sid, "C-COLOR", tags=t)
    for sid in ("media-playback", "xr-runtime"):
        ed.use(sid, "C-COLOR?", tags=t)
    ed.use("post-color-hdr", "C-VIEW", tags=t)

    t = "K-RENDER-5"
    ed.contract_add("C-LIGHTENV", 3, "render-architect", "Per-frame lighting environment",
                    "Per-view environment block published in an early declared phase: sun/moon direction and "
                    "illuminance after atmospheric transmittance, sky irradiance, cloud-shadow and fog resources, "
                    "weather material scalars. Implemented by atmosphere-weather where present; a static default "
                    "otherwise.", requires=["C-RG"], conformance=True, tags=t)
    ed.skill("atmosphere-weather")["implements"].append("C-LIGHTENV")
    ed.cap("RND.ARCH.lighting-env", "Lighting-environment block & its early-phase publication (C-LIGHTENV; static "
           "default without atmosphere)", "render-architect", contrib=["atmosphere-weather", "direct-lighting-shadows"],
           tags=t)
    for sid in ("direct-lighting-shadows", "global-illumination", "translucency-decals"):
        ed.use(sid, "C-LIGHTENV", tags=t)
    for sid in ("material-system", "vfx-particles", "water-ocean"):
        ed.use(sid, "C-LIGHTENV?", tags=t)
    _append(ed, "C-ATMOS", "media sampling and injection only; sun/sky lighting inputs travel through C-LIGHTENV.", t)

    t = "K-RENDER-6"
    ed.cap("WLD.ENV.media-integrator", "Single participating-media integrator: froxel/grid injection, heterogeneous "
           "sparse volumes, composition order with fog and translucency (vfx and fluids inject via C-ATMOS)",
           "atmosphere-weather", contrib=["vfx-particles", "fluid-simulation", "translucency-decals"], tags=t)
    ed.cap_set("RND.VFX.volumes", name="Volume emitters injecting heterogeneous sparse media (NanoVDB class) into the "
               "media integrator via C-ATMOS", tags=t)
    ed.cap_set("RND.TRANS.lighting", name="Translucent-surface lighting, sampling media via C-ATMOS", tags=t)
    _append(ed, "C-ATMOS", "inject-media and sample-media API for the single media integrator.", t)

    t = "K-RENDER-7"
    ed.contract_add("C-TRANSLUCENT", 3, "translucency-decals", "Translucent & decal submission",
                    "Translucent surface submission (sort keys, OIT tier, composition pass before/after DOF and "
                    "upscale), refraction/distortion buffer, decal submission.",
                    requires=["C-RSCENE", "C-MATIF", "C-SCENETEX"], conformance=True, tags=t)
    for sid in ("vfx-particles", "water-ocean", "character-rendering", "geometry-pipeline", "ui-architect"):
        ed.use(sid, "C-TRANSLUCENT?", tags=t)
    ed.use("vfx-particles", "C-MATIF", tags=t)

    t = "K-RENDER-8"
    for sid in ("geometry-pipeline", "virtualized-geometry-lod"):
        ed.use(sid, "C-MATIF", tags=t)
    _append(ed, "C-MATIF", "raster-stage program (mask, world-position offset, displacement) and visibility-buffer/"
            "deferred resolve entry points.", t)
    ed.cap("RND.GEO.material-resolve", "Visibility-buffer material resolve (classification & shading bins, "
           "programmable raster variants)", "geometry-pipeline", contrib=["material-system"], profiles=["std3d"],
           tags=t)

    t = "K-RENDER-9 K-COMPLETE-3"
    ed.cap_set("RND.GEO.culling", name="GPU frustum & two-phase HZB occlusion culling (GPU-driven tier)", tags=t)
    ed.cap("RND.GEO.cpu-occlusion", "CPU frustum & occlusion culling for the CPU-submitted tier (software occluder "
           "rasterization)", "geometry-pipeline", contrib=["render-architect"], tags=t)
    ed.cap("RND.GEO.precomputed-visibility", "Precomputed visibility (portals/cells, baked PVS with cook step)",
           "geometry-pipeline", contrib=["world-data-model", "world-architect"], tags=t)

    t = "K-RENDER-10"
    ed.cap("RND.ARCH.invalidation", "Render-cache invalidation channel: GPU-deforming instance flags, dirty-region/page "
           "invalidation (shadow pages, surface caches), BLAS update requests", "render-architect",
           contrib=["vegetation-foliage", "terrain", "deformation-skinning", "water-ocean", "direct-lighting-shadows",
                    "global-illumination", "ray-tracing-infrastructure"], tags=t)
    _append(ed, "C-RSCENE", "GPU-deformation flags and a cache-invalidation channel (pages, surface caches, BLAS updates).", t)
    ed.use("vegetation-foliage", "C-MATIF?", "C-GEOLOD?", "C-RT?", "C-LIGHT?", tags=t)
    ed.use("terrain", "C-RG?", "C-GEOLOD?", "C-TEMPORAL?", tags=t)

    t = "K-RENDER-11"
    _append(ed, "C-TEMPORAL", "denoiser signal submission (signal class, hit distance, sample count, guide buffers "
            "from C-SCENETEX) with per-signal and joint ray-reconstruction modes.", t)
    ed.unuse("path-tracing", "C-GI", tags=t)
    ed.use("path-tracing", "C-TEMPORAL", "C-INSTANCES", "C-SCENETEX", tags=t)

    t = "K-RENDER-12 K-TOOLS-16"
    ed.cap("RND.TOOL.color-post", "Grading/LUT & post-volume authoring with color-managed HDR preview",
           "post-color-hdr", tags=t)
    ed.cap("RND.TOOL.groom", "Groom import, hair-card generation & digital-human preview", "character-rendering",
           profiles=["aaa"], tags=t)
    ed.cap("RND.TOOL.texture-inspect", "Texture/VT streaming inspection (residency heatmaps, mip bias, accuracy views)",
           "texture-streaming-vt", tags=t)
    ed.cap("RND.TOOL.decals", "Decal placement & projection tools", "translucency-decals", tags=t)
    ed.cap("RND.TOOL.scalability-preview", "Scalability/device-profile authoring & preview-on-tier",
           "render-architect", contrib=["runtime-scalability"], tags=t)
    ed.cap("RND.TOOL.frame-debugger", "In-engine frame / render-graph debugger (passes, resources, per-pass timings)",
           "render-graph-scheduling", contrib=["visual-debugging-tools"], tags=t)
    for sid in ("post-color-hdr", "character-rendering", "texture-streaming-vt", "translucency-decals",
                "render-architect", "render-graph-scheduling"):
        ed.use(sid, "C-EDCMD", "C-EDHOST", tool=True, tags=t)
    ed.cap("ED.WORLD.color-management", "Editor viewport/preview display transforms (OCIO views, HDR preview)",
           "world-editor-viewport", contrib=["post-color-hdr"], tags=t)
    ed.use("world-editor-viewport", "C-COLOR", tool=True, tags=t)

    t = "K-RENDER-14"
    ed.cap("RND.2D.world-sprites", "World-space sprites, billboards & cutouts lit and shadowed in a 3D scene (2.5D)",
           "render-2d-vector", profiles=["lite3d", "std3d"], tags=t)
    ed.use("render-2d-vector", "C-RSCENE?", "C-MATIF?", "C-LIGHT?", "C-VT", tags=t)
    sm = ed.doc["seed"]
    for sec in ("brief_domains", "brief_targets"):
        for k in list(sm[sec]):
            if k.startswith("2.5D"):
                sm[sec][k] = sorted(set(sm[sec][k] + ["RND.2D.world-sprites", "RND.ARCH.submission-strategy",
                                                      "RND.POST.stylized"]))
                ed.note(t, f"seed-map '{k}' remapped")

    t = "K-RENDER-15"   # seed S11; residual: hidden cycle through an optional edge
    ed.unuse("render-architect", "C-INSTANCES", tags=t)
    t = "K-LEGACY-15"
    _append(ed, "C-RSCENE", "one persistent instance scene (C-INSTANCES); features consume it and never mirror it.", t)

    t = "K-RENDER-16 K-ARCH-10"
    ed.contract_add("C-RTAS", 2, "ray-tracing-infrastructure", "Acceleration structures & ray queries",
                    "Acceleration-structure build/refit/compaction, instance and geometry inputs, ray-query API with "
                    "hardware and software backends; independent of the render scene.",
                    requires=["C-RHI", "C-GPUMEM"], conformance=True, gated=True, tags=t)
    ed.contract_set("C-RT", name="Render-scene ray tracing", requires=["C-RSCENE", "C-RTAS"],
                    summary="Render-side binding over C-RTAS: TLAS population from C-INSTANCES/C-RSCENE, hit/material "
                            "binding, RT LOD, update policy.", tags=t)
    s = ed.skill("ray-tracing-infrastructure")
    base = ["C-RHI", "C-GPUMEM", "C-GPUTIER", "C-RES"]
    ed.skill_set("ray-tracing-infrastructure", consumes=base + ["C-RSCENE@C-RT", "C-RG@C-RT", "C-INSTANCES@C-RT",
                 "C-MATIF@C-RT", "C-GEOLOD?@C-RT"], tags=t)
    ed.unuse("spatial-audio-acoustics", "C-RT", tags=t)
    ed.use("spatial-audio-acoustics", "C-RTAS?", tags=t)

    t = "K-RENDER-17"
    ed.cap_set("RND.GEO.splats", name="Static Gaussian-splat / radiance-field rendering, sorting, LOD & compositing",
               mat="M", tags=t)

    t = "K-RENDER-18"
    ed.use("character-rendering", "C-TEMPORAL", "C-RT?", "C-INSTANCES?", tags=t)
    ed.cap("RND.RT.curves", "Hardware ray-traced curve primitives (linear swept spheres) for strands",
           "ray-tracing-infrastructure", "X", contrib=["character-rendering"], profiles=["aaa"], tags=t)
    ed.cap("RND.LOD.dgf", "Hardware-decodable dense geometry formats (DGF class)", "virtualized-geometry-lod", "X",
           contrib=["ray-tracing-infrastructure"], profiles=["aaa"], tags=t)
    ed.doc["radar"]["entries"] += [
        {"tech": "HW ray-traced curve primitives (LSS)", "class": "X", "capabilities": ["RND.RT.curves"],
         "owner": "ray-tracing-infrastructure", "evidence": "Blackwell LSS; DXR/Vulkan extensions 2025",
         "revisit": "Cross-vendor API support", "fallback": "Hair cards or tube proxies in the BLAS"},
        {"tech": "Hardware-decodable dense geometry (DGF)", "class": "X", "capabilities": ["RND.LOD.dgf"],
         "owner": "virtualized-geometry-lod", "evidence": "AMD DGF (2025) specification",
         "revisit": "Hardware decode on two vendors", "fallback": "Engine cluster compression"}]
    ed.note(t, "radar += LSS curves, DGF")

    t = "K-RENDER-19"
    ed.cap_set("RND.RECON.specular-aa", owner="material-system", add_contrib=["reconstruction-upscaling"], tags=t)

    t = "K-RENDER-20 K-FUTURE-7"
    ed.skill_set("ml-inference-runtime", parent="core-runtime-architect", profiles=["all"], workstream="foundation",
                 tags=t)
    ed.nonresp_add("ml-inference-runtime", "GPU queue/budget arbitration of C-MLGPU work", "gpu-platform-architect",
                   tags=t)

    # ================================================================ SIM
    t = "K-SIM-2 K-ARCH-14 K-GAMEPLAY-20"
    ed.cap_del("PHY.FLUID.shallow", tags=t)
    ed.cap_set("WLD.ENV.water-interaction", name="Interactive shallow-water / heightfield water simulation (local "
               "surface waves, wakes, flooding)", tags=t)
    s = ed.skill("water-ocean")
    ed.nonresp("water-ocean", [["Buoyancy dynamics", "rigid-body-dynamics"],
                               ["Volumetric & particle fluid solvers", "fluid-simulation"]], tags=t)
    ed.cap_set("WLD.ENV.buoyancy", name="Water query service (C-ENV provider: height, velocity, depth, body id)",
               rm_contrib=["character-physics"], add_contrib=["rigid-body-dynamics", "vehicle-physics"], tags=t)

    t = "K-SIM-3"
    ed.skill_set("fluid-simulation", profiles=["aaa", "sandbox", "massim"], tags=t)
    ed.cap("PHY.FLUID.cellular", "Grid/cellular material & fluid simulation (falling sand, liquid/gas/heat grids), "
           "2D-capable, deterministic", "fluid-simulation", contrib=["physics-2d"], tags=t)
    ed.doc["skill"]["configurations"]["sandbox-2d-client"] = {"profiles": ["min2d", "sandbox"], "target": "client",
                                                              "platforms": ["pc"]}
    ed.note(t, "configuration sandbox-2d-client (min2d + sandbox) added")

    t = "K-SIM-4 K-TOOLS-5"
    ed.skill_set("procedural-generation", profiles=["min2d", "lite3d", "std3d"], tags=t)
    ed.contract_add("C-PCG", 3, "procedural-generation", "Procedural generation requests",
                    "Seeded, deterministic generation requests per cell/chunk/level, headless-capable; results as "
                    "entity/instance batches.", requires=["C-DET", "C-SPATIAL"], conformance=True, tags=t)
    ed.use("voxel-worlds", "C-PCG", tags=t)
    for sid in ("terrain", "vegetation-foliage"):
        ed.use(sid, "C-PCG?", tags=t)
    ed.unuse("procedural-generation", "C-WORLD", tags=t)
    ed.use("procedural-generation", "C-WORLD?", "C-SPATIAL", tags=t)
    ed.cap("WLD.VOX.generation", "Voxel world generation at chunk stream-in (via C-PCG)", "voxel-worlds",
           contrib=["procedural-generation"], tags=t)
    ed.cap_set("WLD.PCG.scatter", profiles=["lite3d", "std3d"], tags=t)

    t = "K-SIM-5 K-GAMEPLAY-11"
    ed.use("crowd-simulation", "C-DET", "C-SIGNIF", "C-TASK", "C-PHYS?", "C-SNAPSHOT?", "C-INSTANCES?", "C-ANIM?",
           "C-AIAGENT?", "C-REP?", tags=t)

    t = "K-SIM-6"
    ed.cap("PHY.ARCH.multi-world", "Multiple physics worlds per process (match instances, preview worlds, server "
           "density), handle scoping, per-world budgets", "physics-architect",
           contrib=["dedicated-server", "world-data-model"], tags=t)
    ed.cap("PHY.ARCH.local-frames", "Moving local simulation spaces (physics grids): body/controller transitions "
           "between frames, LWC interplay", "physics-architect", "M",
           contrib=["vehicle-physics", "character-physics", "spatial-transforms", "prediction-rollback"], tags=t)
    ed.doc["radar"]["entries"].append({"tech": "Moving local physics frames (physics grids)", "class": "M",
                                       "capabilities": ["PHY.ARCH.local-frames"], "owner": "physics-architect",
                                       "evidence": "Sea of Thieves ship interiors; Star Citizen physics grids",
                                       "revisit": "Two shipped titles with published designs",
                                       "fallback": "Kinematic platforms with controller riding (PHY.CTRL.platforms)"})
    _append(ed, "C-PHYS", "world instances and local simulation spaces.", t)

    t = "K-SIM-7"
    ed.contract_add("C-VEHICLE", 3, "vehicle-physics", "Vehicle control & telemetry",
                    "Control inputs (throttle, brake, steer, collective…), seat/occupant attachment points, telemetry "
                    "stream (RPM, load, slip, contacts), force-feedback torque source, simulation-tier hand-off "
                    "(physics ↔ kinematic ↔ abstract).", requires=["C-PHYS"], conformance=True, tags=t)
    for sid in ("character-movement", "crowd-simulation", "audio-content-runtime", "ai-behavior-perception"):
        ed.use(sid, "C-VEHICLE?", tags=t)
    s = ed.skill("character-physics")
    ed.skill_set("character-physics", expertise=[x for x in s["expertise"]
                                                 if x not in ("vehicle dynamics", "tire models")], tags=t)

    t = "K-SIM-8 K-COMPLETE-10"
    ed.cap("GAM.SYS.projectiles", "Projectile & ballistics simulation (batched sweeps, drag/gravity, penetration/"
           "ricochet by physics material, predicted projectiles, server-side rewind validation)",
           "gameplay-systems-toolkit", contrib=["collision-detection", "prediction-rollback", "physics-architect",
                                                "anti-cheat-integrity"], tags=t)
    ed.nonresp_add("collision-detection", "Projectile & ballistics logic", "gameplay-systems-toolkit", tags=t)

    t = "K-SIM-9"
    ed.area("GAM.SIM", "Systems simulation", tags=t)
    ed.skill_add(tags=t, id="systems-simulation", name="Systems Simulation", tier="expert", parent="gameplay-architect",
                 profiles=["massim", "sandbox"], kind="runtime", targets=["client", "headless-client", "server", "tools"],
                 workstream="gameplay",
                 purpose="Simulation substrates of colony, city, factory and sandbox games: grid/field simulation, flow "
                         "networks, time acceleration with budgeted catch-up, and snapshot/save of very large "
                         "simulation state; deterministic for lockstep.",
                 non_responsibilities=[["Mass agents & traffic", "crowd-simulation"],
                                       ["Cellular fluids", "fluid-simulation"],
                                       ["Game rules", "external:game"]],
                 expertise=["cellular automata & diffusion", "graph flow solvers", "incremental simulation"],
                 consumes=["C-DET", "C-ECS", "C-TASK", "C-FRAME", "C-SIGNIF?", "C-SNAPSHOT?", "C-SAVE?"])
    ed.cap("GAM.SIM.fields", "Grid/field simulation substrates (diffusion, influence, cellular spread), SIMD/GPU-"
           "capable, deterministic", "systems-simulation", tags=t)
    ed.cap("GAM.SIM.networks", "Flow networks (power, fluid, logistics, conveyors) with incremental solve",
           "systems-simulation", tags=t)
    ed.cap("GAM.SIM.time-accel", "Time acceleration with budgeted multi-tick catch-up", "systems-simulation",
           contrib=["frame-orchestration"], tags=t)
    ed.cap("GAM.SIM.scale-save", "Large simulation-state snapshot & save", "systems-simulation",
           contrib=["persistence-save"], tags=t)
    for k in ed.doc["critic"]["critics"]:
        if k["id"] in ("K-SIM", "K-GAMEPLAY") and "systems-simulation" not in k["scope"]:
            k["scope"].append("systems-simulation")
    for sec in ("brief_domains", "brief_targets"):
        for k in list(sm[sec]):
            if "large-scale simulation" in k.lower():
                sm[sec][k] = sorted(set(sm[sec][k] + ["GAM.SIM.fields", "GAM.SIM.networks", "GAM.SIM.time-accel"]))
                ed.note(t, f"seed-map '{k}' += GAM.SIM.*")

    t = "K-SIM-10"
    _append(ed, "C-SIGNIF", "tier-transition protocol: per-domain promote/demote handlers, state hand-off records, "
            "spawn-in validity (depenetration, grounding), hysteresis.", t)
    ed.cap("PHY.ARCH.tier-transitions", "Physics participation in simulation-tier promotion/demotion",
           "physics-architect", contrib=["vehicle-physics", "character-physics", "crowd-simulation"], tags=t)
    for sid in ("vehicle-physics", "character-physics"):
        ed.use(sid, "C-SIGNIF?", tags=t)

    t = "K-SIM-11"
    ed.cap("PHY.COL.runtime-build", "Runtime/incremental collision generation for edited geometry (voxel chunks, "
           "deformed heightfields, debris, UGC), async and budgeted", "collision-detection",
           contrib=["voxel-worlds", "terrain", "destruction-fracture", "modding-ugc"], tags=t)
    ed.unuse("voxel-worlds", "C-PHYS", tags=t)
    ed.use("voxel-worlds", "C-PHYS", tags=t)

    t = "K-SIM-12 K-GAMEPLAY-17"
    ed.cap("PHY.DEST.structural", "Structural integrity / load-path evaluation & collapse", "destruction-fracture",
           contrib=["gameplay-systems-toolkit", "voxel-worlds"], tags=t)
    ed.cap_set("GAM.SYS.building", name="Player construction (snapping, sockets; stability via PHY.DEST.structural)",
               add_contrib=["destruction-fracture"], tags=t)
    ed.skill_set("destruction-fracture", profiles=["lite3d", "std3d"], tags=t)

    t = "K-SIM-13"
    ed.cap("PHY.ARCH.fields", "Gravity & force fields (volumes, radial/non-uniform gravity, impulse/explosion fields) "
           "applied to bodies, controllers and cloth", "physics-architect",
           contrib=["character-physics", "vehicle-physics"], tags=t)
    ed.cap_set("PHY.CTRL.character", name="Character controllers (kinematic & dynamic; arbitrary up-vector / "
               "non-uniform gravity)", tags=t)

    t = "K-SIM-14"
    c = ed.contract("C-PHYS")
    ed.contract_set("C-PHYS", requires=c["requires"] + ["C-SNAPSHOT", "C-DET"], tags=t)
    _append(ed, "C-PHYS", "conformance: restore + resimulate N ticks reproduces the state hash at the declared "
            "determinism level.", t)

    t = "K-SIM-16 K-LEGACY-2"
    ed.cap_set("CORE.FRAME.sim-schedule", name="Canonical simulation dependency order (partial order over declared "
               "access; total order only where C-DET requires it)", add_contrib=["character-movement",
               "gameplay-architect"], tags=t)
    ed.contract_set("C-FRAME", name="Frame schedule, phases & time", tags=t)

    t = "K-SIM-17"
    ed.cap_set("PHY.FLUID.grid", name="Real-time interactive grid smoke & fire", mat="M", tags=t)
    ed.cap("RND.VFX.volume-playback", "Baked/volume-cache smoke & fire playback (VDB/flipbook)", "vfx-particles",
           tags=t)
    for e in ed.doc["radar"]["entries"]:
        if "PHY.FLUID.particles" in e.get("capabilities", []):
            e["capabilities"].append("PHY.FLUID.grid")
            e["fallback"] = "Baked volume/flipbook playback (RND.VFX.volume-playback)"
            ed.note(t, "radar particle/GPU fluids += grid; fallback baked playback")

    t = "K-SIM-18"
    for cid, name, con in [
            ("QA.SIM.vehicles", "Vehicle-dynamics validation runs (reference manoeuvres, tire-model correlation)",
             ["vehicle-physics"]),
            ("QA.SIM.deformables", "Cloth & soft-body stability validation runs", ["cloth-deformables"]),
            ("QA.SIM.mass-agents", "Mass-agent throughput & determinism validation runs",
             ["crowd-simulation", "determinism-replay"]),
            ("QA.SIM.controllers", "Character-controller edge-case validation runs (step, slope, ledge, platforms)",
             ["character-physics", "character-movement"])]:
        ed.cap(cid, name, "simulation-validation", contrib=con, tags=t)
